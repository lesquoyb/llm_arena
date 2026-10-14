#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python -m arena doctor
python -m unittest discover -s tests -v
OUT="${1:-runs/linux-validation-$(date -u +%Y%m%dT%H%M%S)-$$}"
python -m arena verify examples/strategies/rush examples/strategies/single-shot --out "$OUT/verify"
python -m arena tournament examples/tournament.json --out "$OUT/tournament"
python - "$OUT/tournament" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
report = json.loads((root / 'report.json').read_text())
assert report['completed'] == 18 and report['failed'] == report['pending'] == 0, report
(root.parent / 'resume-before.json').write_text(json.dumps({
    str(p.relative_to(root)): [p.stat().st_mtime_ns, p.stat().st_size]
    for p in root.glob('matches/*/attempt-*/*') if p.is_file()
}))
PY
python -m arena tournament examples/tournament.json --out "$OUT/tournament" --resume
python - "$OUT/tournament" <<'PY'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
before = json.loads((root.parent / 'resume-before.json').read_text())
after = {str(p.relative_to(root)): [p.stat().st_mtime_ns, p.stat().st_size]
         for p in root.glob('matches/*/attempt-*/*') if p.is_file()}
assert before == after, 'Resume changed match artifacts or created a new attempt'
print('18 matches completed; resume reused every match.')
PY
