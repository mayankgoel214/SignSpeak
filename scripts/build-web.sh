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

echo "web/ is ready:"
ls -lh web/models | awk 'NR>1 {print "  " $9 " " $5}'
