"""Create a hash-checked ZIP for a file-based A14/B14 evidence handoff."""
import argparse
import hashlib
import zipfile
from pathlib import Path


def package(folder, archive):
    folder, archive = Path(folder).resolve(), Path(archive).resolve()
    if archive.is_relative_to(folder) or not (folder / "session.json").is_file():
        raise ValueError("Archive must be outside a handoff folder with session.json")
    checksum_file = folder / "SHA256SUMS.txt"
    files = sorted((p for p in folder.rglob("*") if p.is_file() and p != checksum_file),
                   key=lambda p: p.relative_to(folder).as_posix())
    if any(p.is_symlink() for p in files):
        raise ValueError("Symlinks are not supported in the handoff")
    checksums = [(hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(folder).as_posix())
                 for p in files]
    checksum_file.write_text(
        "".join(f"{digest}  {relative}\n" for digest, relative in checksums), encoding="utf-8")
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for p in [*files, checksum_file]:
            output.write(p, arcname=(Path(folder.name) / p.relative_to(folder)).as_posix())
    with zipfile.ZipFile(archive) as check:
        expected = {f"{folder.name}/{relative}" for _, relative in checksums}
        expected.add(f"{folder.name}/SHA256SUMS.txt")
        if set(check.namelist()) != expected or len(check.namelist()) != len(expected):
            raise ValueError("ZIP entries differ from checksum list")
        for value, relative in checksums:
            if hashlib.sha256(check.read(f"{folder.name}/{relative}")).hexdigest() != value:
                raise ValueError("ZIP hash mismatch: " + relative)
    return {"archive": str(archive), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": len(files), "bytes": archive.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    print(package(args.folder, args.archive))


if __name__ == "__main__":
    main()
