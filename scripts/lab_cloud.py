"""A14 cloud-host E5–E7 entry point; Docker experiments run on Linux."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
SERVICE = 'buildchecker'
STUDENT_ID = subprocess.run(['git', 'config', '--local', 'user.name'], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
IMAGE = f'a14-buildchecker:{STUDENT_ID}' if STUDENT_ID.isdigit() else 'a14-buildchecker:local'

def execute(command, folder, timeout=1800):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'command.json').write_text(json.dumps(command, indent=2), encoding='utf-8')
    with (folder / 'stdout.log').open('w', encoding='utf-8') as out, (folder / 'stderr.log').open('w', encoding='utf-8') as err:
        try:
            code = subprocess.run(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 124
            if '--cidfile' in command:
                cid_file = Path(command[command.index('--cidfile') + 1])
                if cid_file.is_file():
                    cid = cid_file.read_text().strip()
                    if len(cid) == 64 and all(c in '0123456789abcdef' for c in cid):
                        try:
                            subprocess.run(['docker', 'rm', '-f', cid], stdout=err, stderr=err, timeout=20)
                        except (OSError, subprocess.TimeoutExpired):
                            err.write('\nCleanup incomplete; inspect saved service container ID.\n')
    (folder / 'exit-code.json').write_text(json.dumps({'exit_code': code}), encoding='utf-8')
    for name in ('stdout.log', 'stderr.log'):
        lines = (folder / name).read_text(encoding='utf-8', errors='replace').splitlines()
        print('\n'.join(lines[-35:]))
    return code

def container(extra=()):
    return ['docker', 'run', '--rm', '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp', *extra]

def main(argv=None):
    parser = argparse.ArgumentParser(description='A14 BuildChecker cloud lab')
    parser.add_argument('stage', choices=['doctor', 'build', 'e5', 'e6', 'gate'])
    parser.add_argument('--out', help='Fresh output directory, relative to this repository or absolute')
    parser.add_argument('--image', default=IMAGE)
    parser.add_argument('--fixed', action='store_true', help='Repair the declaration in an isolated E6 copy')
    parser.add_argument('--build-timeout', type=int, default=600)
    args = parser.parse_args(argv)
    if sys.platform != 'linux':
        parser.error('Run after SSH login on the Linux cloud host; Windows is not the experiment host')
    if args.build_timeout <= 0:
        parser.error('Build timeout must be positive')
    if args.fixed and args.stage != 'e6':
        parser.error('--fixed is for e6 only')
    if args.stage == 'doctor':
        return subprocess.run([sys.executable, 'scripts/doctor.py'], cwd=ROOT).returncode
    output = (ROOT / args.out).resolve() if args.out else ROOT / 'work' / f'{args.stage}-{datetime.now().strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}'
    if output != ROOT / 'work' and ROOT / 'work' not in output.parents:
        parser.error('Keep evidence below this repository work/ directory')
    if output == ROOT / 'work' or (output.exists() and any(output.iterdir())):
        parser.error('Use a fresh directory below work/; previous evidence is preserved')
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout.strip()
    changes = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    meta = {'track': 'A', 'stage': args.stage, 'time_utc': datetime.now(timezone.utc).isoformat(),
            'image': args.image, 'source_commit': commit, 'source_dirty': bool(changes),
            'entrypoint': 'a14-e5-e7'}
    (output / 'invocation.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    print(f'EVIDENCE_DIR={output}', flush=True)
    if args.stage == 'build':
        code = execute(['docker', 'build', '--progress=plain', '-f', f'services/{SERVICE}/Dockerfile', '-t', args.image, '.'], output / 'build', args.build_timeout)
        if code:
            return code
        if execute(['docker', 'image', 'inspect', args.image], output / 'image', 30):
            return 1
        return execute(['docker', 'run', '--rm', '--network', 'none', args.image,
                        'python3', '-m', 'pytest'], output / 'unit-tests', 180)
    if args.stage == 'gate':
        command = [sys.executable, 'scripts/run_e7_a_gate.py', '--image', args.image, '--out', str(output / 'gate')]
        return execute(command, output / 'driver', 12 * args.build_timeout + 1200)
    if args.stage == 'e5':
        shell = 'set -eu\ncp -R /app/fixtures/md-rd/. /evidence/\ncd /evidence\nmkdir trace\nmake clean\nstrace -ff -s 4096 -o trace/t -e trace=%file,%process make -p app > make-db.txt 2> build-stderr.log\n./app > program-output.txt\ngrep -n config.h trace/t.*\ngrep -n "^main.o:" make-db.txt\ncat program-output.txt\n'
        evidence = output / 'evidence'
        evidence.mkdir()
        return execute(container(['--network', 'none', '--cap-add', 'SYS_PTRACE', '--cidfile', str(output / 'service-container-id.txt'), '--mount', f'type=bind,src={evidence},dst=/evidence']) + [args.image, 'bash', '-c', shell], output / 'runner', 180)
    fixture = output / 'fixture'
    shutil.copytree(ROOT / 'fixtures/md-rd', fixture)
    if args.fixed:
        path = fixture / 'Makefile'
        text = path.read_text(encoding='utf-8')
        if 'main.o: main.c unused.h' not in text:
            raise ValueError('Review changed fixture before applying teaching repair')
        path.write_text(text.replace('main.o: main.c unused.h', 'main.o: main.c config.h'), encoding='utf-8')
    evidence = output / 'evidence'
    evidence.mkdir()
    return execute(container(['--network', 'none', '--cap-add', 'SYS_PTRACE', '--cidfile', str(output / 'service-container-id.txt'), '--mount', f'type=bind,src={fixture},dst=/fixture,readonly', '--mount', f'type=bind,src={evidence},dst=/evidence']) + [args.image, 'python3', '-m', 'buildchecker', 'full-check', '--fixture', '/fixture', '--out', '/evidence', '--fail-on-findings'], output / 'runner', 180)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit(f'ERROR: {exc}')
