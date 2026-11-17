import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import a_track
import recheck
sys.path.insert(0, str(a_track.ROOT / "validator"))
from validate import schema_check


class ATrackContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.makefile = self.root / "Makefile"
        self.makefile.write_text("main.o: main.c unused.h\n\tgcc -c main.c -o main.o\n", encoding="utf-8")
        self.repo = "https://example.invalid/a14/project.git"
        self.cfg = "cfg-gcc-locked"

    def test_finding_identity_survives_commit_change_and_md_filter(self):
        findings = [{"type": "MISSING", "target": "main.o", "dependency": "config.h"},
                    {"type": "REDUNDANT", "target": "main.o", "dependency": "unused.h"}]
        first = a_track.report(self.repo, "a" * 40, self.cfg, "job-1", findings,
                               self.makefile, "DYNAMIC_TRACE", ("main.o",))
        second = a_track.report(self.repo, "b" * 40, self.cfg, "job-2", findings,
                                self.makefile, "STATIC_INFERENCE", ("main.o",))
        self.assertEqual({f["finding_id"] for f in first["findings"]},
                         {f["finding_id"] for f in second["findings"]})
        md = [f for f in second["findings"] if f["type"] == "MISSING"]
        self.assertEqual(len(md), 1)
        self.assertEqual(md[0]["location"], {"path": "Makefile", "line": 1})
        self.assertEqual(md[0]["commit"], "b" * 40)
        schema_check({**second, "findings": md}, "Report")

    def test_bundle_detects_tampering(self):
        manifest = {}
        record = a_track.publish(self.root, "job-1", "md.json", "ERROR_REPORT",
                                 {"findings": []}, self.repo, "a" * 40, self.cfg, manifest)
        a_track.save(self.root / "manifest.json", {"schema_version": "1.0", "artifacts": manifest})
        self.assertEqual(a_track.verify_bundle(self.root), 1)
        path = self.root / manifest[record["uri"]]["path"]
        path.write_text(json.dumps({"findings": ["changed"]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            a_track.verify_bundle(self.root)

    def test_bundle_rejects_path_escape(self):
        a_track.save(self.root / "manifest.json", {"artifacts": {
            "artifact://a14-check/job-1/md.json": {"path": "../outside.json",
                "artifact": {"uri": "artifact://a14-check/job-1/md.json", "sha256": "0" * 64}}
        }})
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            a_track.verify_bundle(self.root)

    def test_e3_single_object_include_change_adds_md(self):
        (self.root / "main.c").write_text('#include "config.h"\nint main(void) {return 0;}\n')
        (self.root / "config.h").write_text("#define BASE 1\n")
        self.makefile.write_text("CFLAGS = -O0\nmain.o: main.c config.h\n\tcc -c main.c -o main.o\n")

        def fake_command(*args, cwd):
            if args[:2] == ("cc", "--version"):
                return "cc 1.0"
            if args[:2] == ("cc", "-O0"):
                return "main.o: main.c config.h feature.h" if (cwd / "feature.h").exists() else "main.o: main.c config.h"
            if args[:3] == ("git", "rev-parse", "HEAD"):
                return "b" * 40 if (cwd / "feature.h").exists() else "a" * 40
            raise AssertionError(args)

        with patch.object(a_track, "command", side_effect=fake_command):
            baseline = a_track.scan_project(self.root)
            self.assertEqual(baseline["findings"], [])
            (self.root / "feature.h").write_text("#define FEATURE 2\n")
            (self.root / "main.c").write_text('#include "config.h"\n#include "feature.h"\nint main(void) {return 0;}\n')
            changed = a_track.scan_project(self.root, baseline)
        self.assertEqual(changed["added"], [["MISSING", "main.o", "feature.h"]])
        self.assertEqual(changed["refreshed"], ["main.o"])
        self.assertEqual(changed["reused"], [])

    def test_recheck_rejects_stale_report_and_changed_patch(self):
        finding = [{"type": "MISSING", "target": "main.o", "dependency": "feature.h"}]
        report = a_track.report(self.repo, "a" * 40, self.cfg, "job-1", finding,
                                self.makefile, "STATIC_INFERENCE", ("main.o",))
        self.assertEqual(recheck.check_md_report(report, self.repo, "a" * 40, self.cfg),
                         {("main.o", "feature.h")})
        with self.assertRaisesRegex(ValueError, "STALE_REPORT"):
            recheck.check_md_report(report, self.repo, "b" * 40, self.cfg)
        patch_file = self.root / "fix.patch"
        patch_file.write_text("diff --git a/Makefile b/Makefile\n--- a/Makefile\n+++ b/Makefile\n"
                              "@@ -1 +1 @@\n-main.o: main.c unused.h\n+main.o: main.c unused.h feature.h\n")
        with self.assertRaisesRegex(ValueError, "ARTIFACT_HASH_MISMATCH"):
            recheck.check_patch(patch_file, "0" * 64, Path("Makefile"))


if __name__ == "__main__":
    unittest.main()
