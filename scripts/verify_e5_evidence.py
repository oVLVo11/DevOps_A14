"""Check the saved E5 raw observations without rerunning the build."""

import argparse
import json
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    root = args.evidence
    try:
        declaration = (root / "Makefile").read_text(encoding="utf-8")
        database = (root / "make-db.txt").read_text(encoding="utf-8")
        output = (root / "program-output.txt").read_text(encoding="utf-8").strip()
        if not re.search(r"^main\.o:\s+main\.c\s+unused\.h\s*$", declaration, re.MULTILINE):
            raise ValueError("Source Makefile does not contain the expected faulty declaration")
        if not re.search(r"^main\.o:\s+main\.c\s+unused\.h\s*$", database, re.MULTILINE):
            raise ValueError("Make database does not contain the expected faulty declaration")
        if output != "1":
            raise ValueError(f"Program output differs from expected 1: {output!r}")
        matches = []
        for path in sorted((root / "trace").glob("t.*")):
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r'\bopen(?:at|at2)?\([^\n]*"config\.h"[^\n]*\)\s+=\s+\d+', line):
                    matches.append({"trace_file": path.name, "line": number, "event": line})
        if not matches:
            raise ValueError("No successful config.h open in the raw per-process trace")
        result = {"passed": True, "program_output": output,
                  "declared": ["main.c", "unused.h"],
                  "observed_config_open": matches,
                  "manual_conclusion": ["MISSING main.o -> config.h", "REDUNDANT main.o -> unused.h"],
                  "scope": "Saved raw observations; E6 supplies process attribution and full graphs"}
    except (OSError, ValueError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
