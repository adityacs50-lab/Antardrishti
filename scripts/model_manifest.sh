#!/usr/bin/env bash
# Record checksums for whatever model artefacts are present.
# Run once after training + export; verify_offline.sh then enforces them.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO/models"

LINES=""
FOUND=0
for f in prahari.onnx tokenizer.json prahari-fp32.onnx export_report.json; do
  [ -f "$f" ] || continue
  LINES="${LINES}$(sha256sum "$f")"$'\n'
  FOUND=$((FOUND+1))
done

if [ "$FOUND" -eq 0 ]; then
  echo "No model artefacts in ./models — nothing to record."
  echo "The keyword fallback is a supported demo path. To switch to ONNX:"
  echo "  python -m prahari.ml.training.train_lora"
  echo "  python -m prahari.ml.training.export_onnx"
  echo "  make model-manifest"
  exit 0
fi

printf '%s' "$LINES" > MANIFEST.sha256
echo "Recorded $FOUND artefact(s) in models/MANIFEST.sha256:"
sed 's/^/  /' MANIFEST.sha256
