#!/bin/bash
# Build report PDF: pandoc -> HTML (report.css) -> Chrome Page.printToPDF via the local cdpd daemon.
set -euo pipefail
cd "$(dirname "$0")"
pandoc REPORT_DRAFT.md -s --metadata pagetitle="Same Facts, Softer Words" -c report.css -o report_preview.html
API=http://127.0.0.1:9333
curl -s -m 20 -X POST $API/cdp -d "{\"method\":\"Target.createTarget\",\"params\":{\"url\":\"file://$PWD/report_preview.html\",\"background\":true}}" >/dev/null
sleep 4
curl -s -m 60 -X POST $API/cdp -d '{"match":"report_preview.html","method":"Page.printToPDF","params":{"printBackground":true,"preferCSSPageSize":true}}' \
  | python3 -c "import json,sys,base64;d=json.load(sys.stdin);open('${1:-report.pdf}','wb').write(base64.b64decode(d['data']))"
curl -s -m 20 -X POST $API/cdp -d '{"match":"report_preview.html","method":"Page.close","params":{}}' >/dev/null || true
python3 -c "import re;b=open('${1:-report.pdf}','rb').read();print('pages',len(re.findall(rb'/Type\s*/Page[^s]',b)))"
