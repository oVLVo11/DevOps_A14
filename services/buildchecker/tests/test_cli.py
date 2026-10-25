"""E4 骨架的单元测试。"""

from unittest.mock import patch

from buildchecker import __version__
from buildchecker.cli import build_parser, main
from buildchecker.smoke import files_opened


def test_version(capsys):
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == f"buildchecker {__version__}"


def test_smoke_default_fixture():
    assert build_parser().parse_args(["smoke"]).fixture == "fixtures/md-rd"


def test_files_opened_matches_relative_and_absolute_paths():
    trace = "\n".join(
        [
            '101 openat(AT_FDCWD, "config.h", O_RDONLY|O_NOCTTY) = 4',
            '101 openat(AT_FDCWD, "/tmp/x/config.h", O_RDONLY) = 5',
            '101 newfstatat(AT_FDCWD, "unused.h", {st_mode=S_IFREG|0644, ...}, 0) = 0',
            '101 openat(AT_FDCWD, "myconfig.h", O_RDONLY) = 6',
        ]
    )
    assert len(files_opened(trace, "config.h")) == 2
    assert files_opened(trace, "unused.h") == []


def test_full_check_findings_are_successful_analysis_but_fail_optional_gate(capsys):
    """A detected MD is a successful FULL_CHECK, even when the CLI gate rejects it."""
    report = {
        "status": "SUCCEEDED",
        "findings": [{"type": "MISSING", "target": "main.o", "dependency": "config.h"}],
    }
    with patch("buildchecker.cli.full_check", return_value=report) as check:
        assert main(["full-check", "--out", "work/report"]) == 0
        assert main(["full-check", "--out", "work/report", "--fail-on-findings"]) == 1
    assert check.call_count == 2
    assert '"status": "SUCCEEDED"' in capsys.readouterr().out
