"""Pin the A14 course-derived project without embedding a machine's paths in Git."""
import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def prepare(root):
    descriptor = json.loads((ROOT / 'e13/projects/a14-exchange.json').read_text(encoding='utf-8'))
    folder = ROOT / 'data/e13-a14'
    folder.mkdir(parents=True)
    repo = folder / 'repo.git'
    subprocess.run(['git', 'clone', '--bare', '--no-hardlinks', str(ROOT), str(repo)], check=True)
    candidate = folder / 'candidate.Dockerfile'
    project = descriptor['project_path']
    candidate.write_bytes(subprocess.check_output([
        'git', '-C', str(repo), 'show', f"{descriptor['target']}:{project}/candidate.Dockerfile"
    ]))
    request = {key: descriptor[key] for key in ('base', 'target', 'project_path', 'header_probe')}
    request.update(mode='e12', repo=f'{root}/data/e13-a14/repo.git',
                   candidate=f'{root}/data/e13-a14/candidate.Dockerfile',
                   expected_output=descriptor['target_output'], build_timeout=600)
    (folder / 'e12.json').write_text(json.dumps(request, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', default='/course')
    prepare(parser.parse_args().runtime_root)
