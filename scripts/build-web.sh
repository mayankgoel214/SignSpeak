#!/usr/bin/env bash
# Assemble the static site: the page fetches the model and the measured figures
# from ./models/, and both are generated artefacts that live at the repository
# root. Copying rather than committing them twice keeps one source of truth.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p web/models
for f in models/signspeak.weights.json models/labels.json models/metadata.json models/hand_landmarker.task; do
  [ -f "$f" ] || { echo "missing $f -- run ml/train.py and ml/export_web_model.py first" >&2; exit 1; }
  cp "$f" web/models/
done
[ -f eval/results.json ] || { echo "missing eval/results.json -- run ml/evaluate.py first" >&2; exit 1; }
cp eval/results.json web/models/results.json
# Optional: the page degrades to hiding the calibration card if this is absent.
[ -f eval/calibration.json ] && cp eval/calibration.json web/models/calibration.json

# Stamp the real uncompressed byte sizes so the page can show honest download
# progress. Content-Length is the *compressed* length on the wire, so using it as
# a denominator would run the progress bar past 100%.
python3 - <<'PY'
import json, os
names = ["hand_landmarker.task", "signspeak.weights.json"]
sizes = {n: os.path.getsize(os.path.join("web/models", n)) for n in names}
with open("web/models/assets.json", "w") as f:
    json.dump(sizes, f)
print("  assets.json " + ", ".join(f"{n}={v}" for n, v in sizes.items()))
PY

echo "web/ is ready:"
ls -lh web/models | awk 'NR>1 {print "  " $9 " " $5}'
