"""Run independent judge calls. No network unless --live is explicitly present."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

if __package__:
    from .prompts import (TASKS, CONDITIONS, PROMPT_VERSION, judge_messages,
                          deeuphemize_messages, parse_answer, parse_rewrite, render_rewrite)
else:
    from prompts import (TASKS, CONDITIONS, PROMPT_VERSION, judge_messages,
                         deeuphemize_messages, parse_answer, parse_rewrite, render_rewrite)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "harness" / "results"


class BackendFailure(Exception):
    """Safe error code plus response evidence; never an HTTP exception string."""
    def __init__(self, code, attempts):
        super().__init__(code)
        self.attempts = attempts


class MockBackend:
    """Toy text heuristic, not a real judge. Independent of condition labels."""
    def complete(self, messages, repeat):
        passage = json.loads(messages[-1]["content"])["passage"]
        instruction = messages[0]["content"]
        if "Rewrite the passage" in instruction:
            text = passage
            for soft, plain in (
                ("performed an operational adjustment by dropping", "dropped"),
                ("facilitated information sharing by publishing", "published"),
                ("enacted a service adjustment by switching", "switched"),
            ):
                text = text.replace(soft, plain)
            answer = {"actor": "the toy company", "action": "UNKNOWN",
                      "affected_party": "UNKNOWN", "consequence": "UNKNOWN",
                      "other_facts": text}
        else:
            lowered = passage.lower()
            soft = any(s in lowered for s in ("operational adjustment", "information sharing",
                                              "service adjustment"))
            harm = "serious injury" in lowered or "serious harm" in lowered
            consent = "with consent" in lowered
            if "How morally wrong" in instruction:
                value = (8 if harm else 3) - (2 if consent else 0) - (2 if soft else 0)
                jitter = (hashlib.sha256((passage + str(repeat)).encode()).digest()[0] % 3 - 1) * .25
                answer = {"answer": max(0, min(10, value + jitter))}
            elif "fixed claim" in instruction:
                answer = {"answer": ("UNCLEAR" if soft else "TRUE") if harm else "FALSE"}
            else:
                value = (4 if harm else 2) - int(consent) - int(soft)
                answer = {"answer": max(1, min(5, value))}
        text = json.dumps(answer)
        return {"text": text, "response": {"mock": True, "content": text},
                "attempts": [{"status": "mock"}]}


class AdaptionBackend:
    """Adaption Labs hosted models via its SDK (responses.create). Key from ADAPTION_API_KEY."""

    def __init__(self, model, max_tokens=8192, retries=3, timeout=120, token_param="max_tokens"):
        if not os.environ.get("ADAPTION_API_KEY"):
            raise ValueError("Missing live configuration: ADAPTION_API_KEY")
        self.model = model or os.environ.get("MODEL", "")
        if not self.model:
            raise ValueError("Missing live configuration: MODEL")
        self.max_tokens, self.retries, self.timeout = max_tokens, retries, timeout
        self._client = None
        self.key = os.environ["ADAPTION_API_KEY"]

    def redact(self, value):
        if isinstance(value, str):
            return value.replace(self.key, "[REDACTED]")
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, dict):
            return {str(k).replace(self.key, "[REDACTED]"): self.redact(v) for k, v in value.items()}
        return value

    def complete(self, messages, repeat):
        from adaption import Adaption  # Imported only after explicit --live.
        if self._client is None:
            self._client = Adaption()
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        user = "\n\n".join(m["content"] for m in messages if m.get("role") != "system")
        attempts, failures = [], 0
        while True:
            gap = float(os.environ.get("MIN_INTERVAL", "0") or 0)
            wait = gap - (time.monotonic() - getattr(self, "_last_call", 0.0))
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                kwargs = {"model": self.model, "input": user}
                if system:
                    kwargs["instructions"] = system
                r = self._client.responses.create(**kwargs)
                text = getattr(r, "output_text", "") or ""
                usage = getattr(r, "usage", None)
                body = {"id": getattr(r, "id", None), "status": getattr(r, "status", None),
                        "usage": usage.model_dump() if hasattr(usage, "model_dump") else str(usage)}
                attempts.append({"status": "ok", "response": body})
                return {"text": text, "response": body, "attempts": attempts,
                        "finish_reason": getattr(r, "status", None), "refusal": False}
            except Exception as exc:  # SDK raises typed errors; record class only, never the key
                attempts.append({"error": type(exc).__name__, "message": str(exc)[:300]})
                if failures >= self.retries:
                    raise BackendFailure("adaption_" + type(exc).__name__, attempts)
            time.sleep(min(2 ** failures, 30))
            failures += 1


class AnthropicBackend:
    """Claude via the official SDK. Key from ANTHROPIC_API_KEY. No refusal fallback on purpose:
    a fallback would silently swap the judge model, so a refusal is recorded as a failure."""

    def __init__(self, model, max_tokens=4000, retries=3, timeout=120, token_param="max_tokens"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("Missing live configuration: ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens, self.retries, self.timeout = max_tokens, retries, timeout
        self.effort = os.environ.get("ANTHROPIC_EFFORT", "low")
        self.key = os.environ["ANTHROPIC_API_KEY"]
        self._client = None

    def redact(self, value):
        if isinstance(value, str):
            return value.replace(self.key, "[REDACTED]")
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, dict):
            return {str(k).replace(self.key, "[REDACTED]"): self.redact(v) for k, v in value.items()}
        return value

    def complete(self, messages, repeat):
        import anthropic  # Imported only after explicit --live.
        if self._client is None:
            self._client = anthropic.Anthropic(timeout=self.timeout, max_retries=self.retries)
        system = "\n\n".join(m["content"] for m in messages if m.get("role") == "system")
        convo = [m for m in messages if m.get("role") != "system"]
        gap = float(os.environ.get("MIN_INTERVAL", "0") or 0)
        wait = gap - (time.monotonic() - getattr(self, "_last_call", 0.0))
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        try:
            r = self._client.messages.create(model=self.model, max_tokens=self.max_tokens,
                                             system=system or anthropic.NOT_GIVEN, messages=convo,
                                             output_config={"effort": self.effort})
        except (anthropic.BadRequestError, anthropic.AuthenticationError,
                anthropic.PermissionDeniedError, anthropic.NotFoundError) as exc:
            raise BackendFailure("anthropic_" + type(exc).__name__, [{"error": type(exc).__name__, "message": str(exc)[:300]}])
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            raise BackendFailure("anthropic_" + type(exc).__name__, [{"error": type(exc).__name__, "message": str(exc)[:300]}])
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        u = r.usage
        body = {"id": r.id, "model": r.model, "stop_reason": r.stop_reason,
                "usage": {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}}
        return {"text": text, "response": body, "attempts": [{"status": "ok", "response": body}],
                "finish_reason": "length" if r.stop_reason == "max_tokens" else r.stop_reason,
                "refusal": r.stop_reason == "refusal"}


def make_backend(model, *args, **kwargs):
    if model and model.startswith("anthropic:"):
        return AnthropicBackend(model.split(":", 1)[1], *args, **kwargs)
    # "adaption:<model>" routes one role to Adaption while others use BASE_URL.
    if model and model.startswith("adaption:"):
        return AdaptionBackend(model.split(":", 1)[1], *args, **kwargs)
    if os.environ.get("BACKEND", "").lower() == "adaption":
        return AdaptionBackend(model, *args, **kwargs)
    return LiveBackend(model, *args, **kwargs)


class LiveBackend:
    def __init__(self, model, max_tokens=8192, retries=3, timeout=120,
                 token_param="max_tokens"):
        values = {k: os.environ.get(k, "").strip() for k in ("BASE_URL", "API_KEY", "MODEL")}
        if model:
            values["MODEL"] = model
        missing = [k for k, v in values.items() if not v]
        if missing:
            raise ValueError("Missing live configuration: " + ", ".join(missing))
        parts = urlsplit(values["BASE_URL"])
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("BASE_URL must be an HTTP(S) URL without credentials, query, or fragment")
        self.url = values["BASE_URL"].rstrip("/")
        if not self.url.endswith("/chat/completions"):
            self.url += "/chat/completions"
        self.key, self.model = values["API_KEY"], values["MODEL"]
        self.max_tokens, self.retries, self.timeout = max_tokens, retries, timeout
        self.token_param = token_param
        self.temperature = True

    def redact(self, value):
        if isinstance(value, str):
            return value.replace(self.key, "[REDACTED]")
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, dict):
            return {str(k).replace(self.key, "[REDACTED]"): self.redact(v) for k, v in value.items()}
        return value

    def complete(self, messages, repeat):
        import requests  # Imported only after explicit --live.
        attempts = []
        failures = 0
        while True:
            payload = {"model": self.model, "messages": messages,
                       self.token_param: self.max_tokens}
            if self.temperature:
                payload["temperature"] = 0
            effort = os.environ.get("REASONING_EFFORT", "").strip()
            if effort and "gpt-oss" in self.model:
                payload["reasoning_effort"] = effort
            # Optional pacing for free tiers (e.g. Groq ~30 req/min): MIN_INTERVAL seconds between calls.
            gap = float(os.environ.get("MIN_INTERVAL", "0") or 0)
            wait = gap - (time.monotonic() - getattr(self, "_last_call", 0.0))
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()
            try:
                response = requests.post(self.url, headers={"Authorization": "Bearer " + self.key},
                                         json=payload, timeout=self.timeout)
            except requests.RequestException:
                attempts.append({"error": "transport_error"})
                if failures >= self.retries:
                    raise BackendFailure("transport_error", attempts)
            else:
                try:
                    body = self.redact(response.json())
                except ValueError:
                    body = {"non_json_body": self.redact(response.text)}
                attempts.append({"http_status": response.status_code, "response": body,
                                 "temperature": 0 if self.temperature else None,
                                 "token_param": self.token_param, "max_tokens": self.max_tokens})
                error_text = json.dumps(body).lower()
                # Capability negotiation is bounded to at most two changes per backend.
                if response.status_code in (400, 422):
                    if self.temperature and "temperature" in error_text and any(
                            word in error_text for word in ("unsupported", "not support", "only", "not allowed")):
                        self.temperature = False
                        continue
                    if self.token_param == "max_tokens" and "max_completion_tokens" in error_text:
                        self.token_param = "max_completion_tokens"
                        continue
                if 200 <= response.status_code < 300:
                    try:
                        choice = body["choices"][0]
                        message = choice["message"]
                        text = message.get("content") or ""
                        if not isinstance(text, str):
                            text = ""
                        return {"text": text, "response": body, "attempts": attempts,
                                "finish_reason": choice.get("finish_reason"),
                                "refusal": bool(message.get("refusal"))}
                    except (KeyError, IndexError, TypeError, AttributeError):
                        raise BackendFailure("malformed_api_response", attempts)
                if response.status_code not in (408, 409, 429) and response.status_code < 500:
                    raise BackendFailure("http_" + str(response.status_code), attempts)
                if failures >= self.retries:
                    raise BackendFailure("http_" + str(response.status_code), attempts)
            retry_after = 0.0
            try:
                retry_after = float(response.headers.get("retry-after", 0) or 0)
            except (NameError, ValueError, AttributeError):
                retry_after = 0.0
            time.sleep(max(min(2 ** failures, 30), min(retry_after, 60)))
            failures += 1


def query(backend, messages, task, repeat):
    try:
        result = backend.complete(messages, repeat)
    except BackendFailure as exc:
        return {"raw_text": "", "status": "INVALID", "answer": None,
                "error": str(exc), "attempts": exc.attempts}
    text = result.get("text", "")
    answer = parse_rewrite(text) if task == "deeuphemize" else parse_answer(task, text)
    error = None
    if not isinstance(text, str) or not text.strip():
        error = "empty_output"
    elif result.get("refusal"):
        error = "refusal"
    elif result.get("finish_reason") in ("length", "content_filter"):
        error = "finish_" + result["finish_reason"]
    elif answer is None:
        error = "unparseable_output"
    return {"raw_text": text, "status": "INVALID" if error else "VALID",
            "answer": None if error else answer, "error": error,
            "raw_response": result.get("response"), "attempts": result.get("attempts", []),
            "finish_reason": result.get("finish_reason")}


def read_pairs(path):
    required = ("pair_id", "domain", "incident", "soft_text", "plain_text", "contrast_text",
                "source_soft", "source_plain")
    pairs, seen = [], set()
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                pair = json.loads(line)
                if not isinstance(pair, dict) or any(not isinstance(pair.get(k), str) or not pair[k].strip() for k in required):
                    raise ValueError("required fields must be nonempty strings")
                if pair["pair_id"] in seen:
                    raise ValueError("duplicate pair_id")
            except (ValueError, TypeError) as exc:
                raise ValueError("Invalid pair on line " + str(line_no) + ": " + str(exc)) from None
            pairs.append(pair)
            seen.add(pair["pair_id"])
    if not pairs:
        raise ValueError("Pairs file contains no pairs")
    return pairs


def model_filename(model):
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", model)[:100]
    if safe != model:
        safe += "_" + hashlib.sha256(model.encode()).hexdigest()[:8]
    return "raw_" + safe + ".jsonl"


def record_key(record):
    return tuple(record[k] for k in ("pair_id", "condition", "repeat", "task", "stage"))


def replace_records(path, records):
    """Keep the previous file intact until its replacement is fully written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp",
                                         delete=False) as output:
            temporary = Path(output.name)
            for record in records:
                output.write(json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_resume(path, model, digest, pairs, n, live):
    records, repair = {}, False
    if not path.exists():
        return records, repair
    expected = {(p["pair_id"], c, i, t, "rewrite" if t == "deeuphemize" else "judge")
                for p in pairs for c in CONDITIONS for i in range(n)
                for t in TASKS + (("deeuphemize",) if c.endswith("_deeuph") else ())}
    metadata = {"model": model, "pairs_sha256": digest, "n": n,
                "pair_count": len(pairs), "prompt_version": PROMPT_VERSION,
                "backend": "live" if live else "mock"}
    run_id = None
    with path.open("rb") as source:
        for line_no, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                if not line.endswith(b"\n"):
                    repair = True  # A disk-full write can leave an unfinished last record.
                    break
                raise ValueError("Cannot resume: malformed record on line " + str(line_no)) from None
            if (not isinstance(record, dict)
                    or any(record.get(k) != v for k, v in metadata.items())
                    or not isinstance(record.get("run_id"), str) or not record["run_id"]):
                raise ValueError("Cannot resume: incompatible run metadata on line " + str(line_no))
            if run_id is None:
                run_id = record["run_id"]
            try:
                key = record_key(record)
                valid_key = key in expected
            except (KeyError, TypeError):
                valid_key = False
            if (not valid_key or record["run_id"] != run_id
                    or record.get("status") not in ("VALID", "INVALID")):
                raise ValueError("Cannot resume: unexpected query or mixed runs on line " + str(line_no))
            if (record["stage"] == "rewrite" and record["status"] == "VALID"
                    and parse_rewrite(json.dumps(record.get("answer"))) is None):
                raise ValueError("Cannot resume: invalid stored rewrite answer")
            repair |= key in records or not line.endswith(b"\n")
            records[key] = record
    return records, repair


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Deterministic offline mock (default)")
    mode.add_argument("--live", action="store_true", help="Explicitly enable API calls")
    parser.add_argument("--pairs", type=Path, default=ROOT / "data" / "pairs.jsonl")
    parser.add_argument("--models", nargs="+", help="Model IDs; live default is env MODEL")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--conditions", nargs="+", choices=CONDITIONS, default=None,
                        help="Subset of conditions to run (default: all); saves calls on free tiers")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    existing = parser.add_mutually_exclusive_group()
    existing.add_argument("--overwrite", action="store_true", help="Replace selected existing raw files")
    existing.add_argument("--resume", action="store_true", help="Continue selected raw files, preserving completed queries")
    parser.add_argument("--retry-invalid", action="store_true", help="With --resume, re-query INVALID records")
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--token-param", choices=("max_tokens", "max_completion_tokens"), default="max_tokens")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args(argv)
    if args.retry_invalid and not args.resume:
        parser.error("--retry-invalid requires --resume")
    if args.n < 1 or args.max_tokens < 2048 or args.retries < 0 or args.timeout <= 0:
        parser.error("n >= 1, max-tokens >= 2048, retries >= 0, timeout > 0 required")
    try:
        pairs = read_pairs(args.pairs)
        digest = hashlib.sha256(args.pairs.read_bytes()).hexdigest()
        if args.live:
            models = args.models or [os.environ.get("MODEL", "")]
            backends = [make_backend(m, args.max_tokens, args.retries, args.timeout, args.token_param) for m in models]
        else:
            models = ["mock"] if not args.models else ["mock:" + m for m in args.models]
            backends = [MockBackend() for _ in models]
        if len(set(models)) != len(models):
            raise ValueError("Model IDs must be unique")
        args.results_dir.mkdir(parents=True, exist_ok=True)
        paths = [args.results_dir / model_filename(m) for m in models]
        if not args.overwrite and not args.resume and any(p.exists() for p in paths):
            raise ValueError("Raw output already exists; use --resume, --overwrite or a new --results-dir")
        saved_runs = [load_resume(p, m, digest, pairs, args.n, args.live) if args.resume else ({}, False)
                      for m, p in zip(models, paths)]
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    run_id = str(uuid.uuid4())
    for model, backend, path, (records, repair) in zip(models, backends, paths, saved_runs):
        model_run_id = next(iter(records.values()))["run_id"] if records else run_id
        if repair:
            replace_records(path, records.values())
        if not args.resume or not path.exists():
            path.write_text("", encoding="utf-8")
        count, invalid = 0, 0
        def emit(pair, condition, repeat, task, messages, result, **metadata):
            nonlocal count, invalid
            record = {"schema_version": 1, "prompt_version": PROMPT_VERSION,
                      "run_id": model_run_id, "created_at": datetime.now(timezone.utc).isoformat(),
                      "model": model, "backend": "live" if args.live else "mock",
                      "pair_id": pair["pair_id"], "pair": pair, "domain": pair["domain"],
                      "condition": condition, "repeat": repeat, "task": task,
                      "stage": "rewrite" if task == "deeuphemize" else "judge",
                      "messages": messages, "n": args.n, "pair_count": len(pairs),
                      "conditions": list(CONDITIONS), "pairs_sha256": digest,
                      **metadata, **result}
            if args.live:
                record = backend.redact(record)
            key = record_key(record)
            if key in records:
                updated = {**records, key: record}
                replace_records(path, updated.values())
            else:
                with path.open("a", encoding="utf-8") as output:
                    output.write(json.dumps(record, ensure_ascii=True, allow_nan=False) + "\n")
                    output.flush()
            records[key] = record
            count += 1
            invalid += result["status"] == "INVALID"

        def saved(pair, condition, repeat, task):
            stage = "rewrite" if task == "deeuphemize" else "judge"
            record = records.get((pair["pair_id"], condition, repeat, task, stage))
            if record is not None and (record["status"] == "VALID" or not args.retry_invalid):
                return record
            return None
        for pair in pairs:
            for repeat in range(args.n):
                texts = {c: pair[c + "_text"] for c in ("soft", "plain", "contrast")}
                selected = [c for c in CONDITIONS if not args.conditions or c in args.conditions]
                for base in ("soft", "plain", "contrast"):
                    if base + "_deeuph" not in selected:
                        continue  # budget: skip rewrites no selected condition needs
                    messages = deeuphemize_messages(texts[base])
                    condition = base + "_deeuph"
                    result = saved(pair, condition, repeat, "deeuphemize")
                    if result is None:
                        result = query(backend, messages, "deeuphemize", repeat)
                        emit(pair, condition, repeat, "deeuphemize", messages, result)
                    texts[condition] = render_rewrite(result["answer"]) if result["status"] == "VALID" else None
                for condition in selected:
                    for task in TASKS:
                        if saved(pair, condition, repeat, task) is not None:
                            continue
                        text = texts[condition]
                        messages = judge_messages(task, text) if text is not None else []
                        result = (query(backend, messages, task, repeat) if text is not None else
                                  {"raw_text": "", "answer": None, "status": "INVALID",
                                   "error": "invalid_rewrite", "attempts": []})
                        emit(pair, condition, repeat, task, messages, result, evaluated_text=text)
        # Do not print user-controlled model IDs or remote error bodies.
        print(("LIVE" if args.live else "TOY MOCK") + ": " + str(count) +
              " records, " + str(invalid) + " INVALID; " + str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
