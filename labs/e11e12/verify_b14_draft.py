"""Verify a B14 file handoff without claiming to have run its Docker image."""
import argparse
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path


PROJECT_FILES = ("main.c", "config.h", "feature.h", "Makefile")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(bundle, repo, commit):
    bundle, repo = Path(bundle).resolve(), Path(repo).resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Complete target commit required")
    listed = {}
    for line in (bundle / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\\]+)", line)
        if not match:
            raise ValueError("Invalid SHA256SUMS entry")
        expected, relative = match.groups()
        path = (bundle / relative).resolve()
        if relative in listed or not path.is_relative_to(bundle) or path.is_symlink() or not path.is_file():
            raise ValueError("Duplicate, unsafe or missing file: " + relative)
        if digest(path.read_bytes()) != expected:
            raise ValueError("Hash mismatch: " + relative)
        listed[relative] = expected
    required = {"image.tar", "manifest.json", "candidate.Dockerfile", "build.log",
                "verify.log", "save.log", "README.md", *("project/" + name for name in PROJECT_FILES)}
    if set(listed) != required:
        raise ValueError("Unexpected or missing handoff files")

    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if manifest["archive"]["sha256"] != listed["image.tar"]:
        raise ValueError("Archive digest differs from manifest")
    if manifest["dockerfile"]["sha256"] != listed["candidate.Dockerfile"]:
        raise ValueError("Dockerfile digest differs from manifest")
    if not manifest["passed"] or not manifest["output_matches"] or manifest["actual_output"] != "12\n":
        raise ValueError("DRAFT verification did not pass with exact output 12")
    if manifest["build"]["exit_code"] or manifest["verify"]["exit_code"] or manifest["archive"]["save"]["exit_code"]:
        raise ValueError("DRAFT command failed")
    for name in PROJECT_FILES:
        relative = "project/" + name
        if manifest["project"]["inputs"][name] != listed[relative]:
            raise ValueError("Project digest differs from manifest: " + name)
        source = subprocess.run(["git", "show", f"{commit}:e3/fixtures/commits/project/{name}"],
                                cwd=repo, capture_output=True, check=True).stdout
        if digest(source) != listed[relative]:
            raise ValueError("B14 project differs from C1: " + name)

    image_id = manifest["image"]["id"]
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("Invalid image ID")
    with tarfile.open(bundle / "image.tar", "r") as archive:
        member = archive.extractfile("blobs/sha256/" + image_id.removeprefix("sha256:"))
        if member is None or digest(member.read()) != image_id.removeprefix("sha256:"):
            raise ValueError("OCI index digest absent or mismatched")

    return {
        "status": "B14_DRAFT_BYTES_VERIFIED",
        "execution_status": "NOT_RUN_ON_A14",
        "schema": manifest["schema"],
        "job_id": manifest["job_id"],
        "trace_id": manifest["trace_id"],
        "configuration_id": manifest["configuration_id"],
        "target_commit": commit,
        "expected_output": "12",
        "b14_recorded_output": manifest["actual_output"].strip(),
        "image_id": image_id,
        "image_repo_digest": manifest["image"]["repo_digest"],
        "archive_sha256": listed["image.tar"],
        "checked_files": listed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.bundle, args.repo, args.target)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
