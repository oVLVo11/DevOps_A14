"""Prepare the pinned B14 exchange bundle for E13 cross testing."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prepare(bundle: Path, runtime_root: str = '/course') -> Path:
    descriptor = json.loads((ROOT / 'e13/projects/b14-exchange.json').read_text(encoding='utf-8'))
    bundle = bundle.resolve(strict=True)
    actual = hashlib.sha256(bundle.read_bytes()).hexdigest()
    if actual != descriptor['bundle_sha256']:
        raise ValueError(f'B14 bundle SHA-256 mismatch: {actual}')
    folder = ROOT / 'data/e13-b14'
    if folder.exists():
        raise ValueError(f'Use a fresh workspace; refusing to overwrite {folder}')
    folder.mkdir(parents=True)
    repo = folder / 'repo.git'
    subprocess.run(['git', 'clone', '--bare', '--no-hardlinks', str(bundle), str(repo)], check=True)
    for key in ('base', 'target'):
        actual_commit = subprocess.check_output(
            ['git', '-C', str(repo), 'rev-parse', f"{descriptor[key]}^{{commit}}"], text=True
        ).strip()
        if actual_commit != descriptor[key]:
            raise ValueError(f'{key} commit mismatch: {actual_commit}')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor',
                    descriptor['base'], descriptor['target']], check=True)
    candidate_bytes = subprocess.check_output([
        'git', '-C', str(repo), 'show',
        f"{descriptor['target']}:{descriptor['project_path']}/candidate.Dockerfile"
    ])
    if hashlib.sha256(candidate_bytes).hexdigest() != descriptor['candidate_sha256']:
        raise ValueError('B14 candidate.Dockerfile SHA-256 mismatch')
    candidate = folder / 'candidate.Dockerfile'
    candidate.write_bytes(candidate_bytes)
    request = {key: descriptor[key] for key in
               ('base', 'target', 'project_path', 'header_probe', 'expected_output')}
    request.update(mode='e12', repo=f'{runtime_root}/data/e13-b14/repo.git',
                   candidate=f'{runtime_root}/data/e13-b14/candidate.Dockerfile',
                   build_timeout=600)
    (folder / 'e12.json').write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')
    (folder / 'input-provenance.json').write_text(json.dumps({
        'bundle_sha256': actual, 'source_repository': descriptor['source_repository'],
        'candidate_sha256': descriptor['candidate_sha256'],
        'base': descriptor['base'], 'target': descriptor['target'],
    }, indent=2) + '\n', encoding='utf-8')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--runtime-root', default='/course')
    args = parser.parse_args()
    print(prepare(args.bundle, args.runtime_root))
