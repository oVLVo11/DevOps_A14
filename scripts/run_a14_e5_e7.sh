#!/usr/bin/env bash
# Run the A14 teaching acceptance sequence on the group's Linux Docker host.
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
if [[ $# -ne 1 ]]; then
  echo "Usage: bash scripts/run_a14_e5_e7.sh <unique-run-id>" >&2
  exit 2
fi
if [[ ! "$1" =~ ^[A-Za-z0-9_-]+$ ]]; then
  echo "Usage: bash scripts/run_a14_e5_e7.sh <unique-run-id>" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Commit the source first: evidence must name an exact, clean Git revision." >&2
  exit 2
fi
student_id="$(git config --local user.name)"
if [[ ! "$student_id" =~ ^[0-9]+$ ]]; then
  echo "Set the repository-local Git user.name to your student ID." >&2
  exit 2
fi

out="work/a14-e5e7-$1"
if [[ -e "$out" ]]; then
  echo "Evidence directory already exists: $out" >&2
  exit 2
fi
mkdir -p "$out"
image="a14-buildchecker:$student_id"
git rev-parse HEAD > "$out/source-commit.txt"
printf '%s\n' "$image" > "$out/service-image-tag.txt"

run_stage() {
  local name="$1" expected="$2" actual
  shift 2
  echo "[$name] $*"
  set +e
  "$@" > "$out/$name.log" 2>&1
  actual=$?
  set -e
  printf '%s\n' "$actual" > "$out/$name.exit-code.txt"
  if [[ "$actual" -ne "$expected" ]]; then
    echo "[$name] expected exit $expected, got $actual; inspect $out/$name.log" >&2
    exit 1
  fi
}

run_stage doctor 0 python3 scripts/doctor.py --out "$out/environment.json"
run_stage build 0 python3 scripts/lab_cloud.py build --image "$image" --out "$out/build" --build-timeout 1200
run_stage e5 0 python3 scripts/lab_cloud.py e5 --image "$image" --out "$out/e5"
run_stage e5-verify 0 python3 scripts/verify_e5_evidence.py "$out/e5/evidence"
run_stage e6-before 1 python3 scripts/lab_cloud.py e6 --image "$image" --out "$out/e6-before"
run_stage e6-after 0 python3 scripts/lab_cloud.py e6 --image "$image" --fixed --out "$out/e6-after"
run_stage e6-verify 0 python3 scripts/verify_e6_evidence.py \
  --before "$out/e6-before/evidence/findings.json" \
  --after "$out/e6-after/evidence/findings.json"
run_stage oracle 0 python3 -m unittest discover -s tests/e7 -v
run_stage e7-gate 0 python3 scripts/lab_cloud.py gate --image "$image" --out "$out/e7"
run_stage secret-scan 0 python3 scripts/secret_scan.py . --history --image "$image"

OUT_DIR="$out" python3 - <<'PY'
import hashlib
import os
from pathlib import Path

root = Path(os.environ["OUT_DIR"])
lines = []
for path in sorted(root.rglob("*")):
    if path.is_file() and path.name != "SHA256SUMS.txt":
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}")
(root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"PASS: {len(lines)} evidence files; manifest at {root / 'SHA256SUMS.txt'}")
PY

echo "A14 E5-E7 evidence: $out"
