"""Run the visible E13 matrix against a pinned request and preserve the evidence."""
import argparse
from contextlib import redirect_stdout
import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'labs/e11e12'))
from pipeline import execute, save, command
from server import create_server
from lab import validate
from handoff_a_to_b import make_handoff, digest, checked_artifact
from scan_runtime_logs import main as scan_logs


def require(condition, message):
    if not condition:
        raise ValueError(message)


def http(url, body=None, *, raw=False):
    request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read() if raw else json.load(response), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error), dict(error.headers)


def check_idempotency(original, output):
    with create_server(port=0, work_root=output / 'jobs') as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        url = f'http://127.0.0.1:{server.server_port}/v1/jobs'
        try:
            request = {'input': original, 'idempotency_key': 'e13-visible-c8'}
            one = http(url, request)
            two = http(url, request)
            three = http(url, dict(request, input=dict(original, target='0'*40)))
            save(output / 'responses.json', [one, two, three])
            require(one[0] == two[0] == 202 and one[1]['job_id'] == two[1]['job_id'], 'Identical requests yielded different jobs')
            require(three[0] == 409 and three[1]['error'] == 'IDEMPOTENCY_CONFLICT', 'Conflicting input was accepted')
            job = one[1]['job_id']
            for _ in range(240):
                current = http(f'{url}/{job}')
                if current[1]['status'] not in ('RUNNING','QUEUED'):
                    break
                time.sleep(.5)
            save(output / 'final-state.json', current)
            require(current[0] == 200 and current[1]['status'] == 'SUCCEEDED', 'API job did not succeed')
            artifacts = http(f'{url}/{job}/artifacts')
            report = http(f'{url}/{job}/files/incremental-check.json', raw=True)
            sha = digest(output / 'jobs' / job / 'evidence/incremental-check.json')
            require(artifacts[0] == report[0] == 200 and report[2].get('X-Content-SHA256') == sha
                    and hashlib.sha256(report[1]).hexdigest() == sha, 'API report hash mismatch')
            save(output / 'download-verification.json', {'job_id': job, 'sha256': sha, 'headers': report[2]})
            require(list(server.jobs.jobs) == [job], 'Duplicate job was created')
        finally:
            server.shutdown()
            worker.join()
            server.jobs.pool.shutdown()


def run(request, output):
    output.mkdir(parents=True)
    input_area = ROOT / 'data' / output.name
    input_area.mkdir()
    summary = {}

    def record(case, **evidence):
        summary[case] = evidence
        save(output / 'matrix.json', summary)

    a_request = dict(request, mode='e11-a')
    checked = execute(a_request, output / 'C1-a')
    require(checked['status'] == 'SUCCEEDED', 'A live check failed')
    handoff = make_handoff(output / 'C1-a/result.json', request['target'])
    handoff_path = input_area / 'fixed-md.json'
    save(handoff_path, handoff)
    save(output / 'fixed-md.json', handoff)
    b_request = dict(request, mode='e11-b', fixed_report=str(handoff_path),
                     fixed_report_sha256=digest(handoff_path))
    repaired = execute(b_request, output / 'C1-b')
    require(repaired['status'] == 'SUCCEEDED', 'Reference B consumer failed')
    require((output / 'C1-b/fixed-md-input.json').read_bytes() == handoff_path.read_bytes(), 'B report copy changed')
    record('C1', a_job=checked['job_id'], b_job=repaired['job_id'], handoff_sha256=digest(handoff_path),
           consumer='course reference B pipeline on A input')

    def reject(case, payload, expected):
        result = execute(payload, output / case)
        require(result['status'] == 'FAILED' and result['error']['code'] == expected
                and not result['stages'], f'{case} did not reject before building')
        record(case, job_id=result['job_id'], error_code=expected)

    stale = input_area / 'stale.json'
    save(stale, {**handoff, 'commit': request['base'],
                 'data': {**handoff['data'], 'commit': request['base']}})
    (output / 'stale-input.json').write_bytes(stale.read_bytes())
    reject('C2', dict(b_request, fixed_report=str(stale), fixed_report_sha256=digest(stale)), 'STALE_REPORT')
    changed = input_area / 'changed.json'
    changed.write_bytes(handoff_path.read_bytes() + b'\n')
    (output / 'changed-input.json').write_bytes(changed.read_bytes())
    reject('C3', dict(b_request, fixed_report=str(changed)), 'ARTIFACT_HASH_MISMATCH')
    record('C3', original_sha256=digest(handoff_path), changed_sha256=digest(changed),
           error_code='ARTIFACT_HASH_MISMATCH')

    timeout = execute(dict(b_request, build_timeout=.01), output / 'C4')
    inner = json.loads((output / 'C4/draft-build/result.json').read_text())
    observations = list((output / 'C4/draft-build').rglob('*.timeout.json'))
    require(len(observations) == 1, 'C4 needs one process-group observation')
    process = json.loads(observations[0].read_text())
    require(timeout['status'] == 'FAILED' and inner['status'] == 'TIMED_OUT' and not timeout['stages']
            and process['returncode'] < 0 and not process['process_group_alive_after_wait']
            and not (output / 'C4/draft-build/verify-container-id.txt').exists(), 'C4 timeout or cleanup did not work')
    record('C4', job_id=timeout['job_id'], process=process)

    case5 = output / 'C5'
    case5.mkdir()
    project = output / 'C1-a/target-project' / request.get('project_path', '.')
    before = (project / 'Makefile').read_bytes()
    source = Path(request['repo'])
    commit_arg = f"{request['target']}^{{commit}}"
    tree_arg = f"{request['target']}^{{tree}}"
    commit_before = command(['git', 'rev-parse', '--verify', commit_arg], source,
                            case5 / 'source-commit-before.log')
    tree_before = command(['git', 'rev-parse', '--verify', tree_arg], source,
                          case5 / 'source-tree-before.log')
    good = output / 'C1-b/candidate.patch'
    wrong = case5 / 'wrong.patch'
    lines = good.read_text().splitlines(keepends=True)
    changed_line = next(i for i, line in enumerate(lines) if line.startswith('+') and not line.startswith('+++'))
    lines[changed_line] = lines[changed_line].rstrip('\n') + ' deliberately-absent-e13.h\n'
    wrong.write_text(''.join(lines), encoding='utf-8')
    config = {'expected_output': request.get('expected_output','1'), 'header_probe': request.get('header_probe')}
    verdict = validate(project, wrong, case5 / 'wrong', **config)
    commit_after = command(['git', 'rev-parse', '--verify', commit_arg], source,
                           case5 / 'source-commit-after.log')
    tree_after = command(['git', 'rev-parse', '--verify', tree_arg], source,
                         case5 / 'source-tree-after.log')
    require(not verdict['accepted'] and verdict['rollback'] and verdict['source_unchanged']
            and commit_before == commit_after == request['target']
            and tree_before == tree_after and before == (project / 'Makefile').read_bytes()
            and verdict['checks'].get('patch_applies') and not verdict['checks'].get('build'),
            'C5 wrong patch did not fail the build or left modifications')
    record('C5', rollback=True, source_commit_before=commit_before,
           source_commit_after=commit_after, source_tree_before=tree_before,
           source_tree_after=tree_after, patch_sha256=digest(wrong))

    case6 = output / 'C6'
    case6.mkdir()
    probe = case6 / 'probe.log'
    probe.write_text('api_' + 'key = "s' + 'k-' + 'fictitiousE13' * 2 + '"\n', encoding='utf-8')
    before_sha256 = digest(probe)
    with (case6 / 'hit-scan.txt').open('w', encoding='utf-8') as log, redirect_stdout(log):
        hit = scan_logs([str(probe)])
    probe.write_text('probe completed; clean content\n', encoding='utf-8')
    after_sha256 = digest(probe)
    with (case6 / 'clean-scan.txt').open('w', encoding='utf-8') as log, redirect_stdout(log):
        clean = scan_logs([str(probe)])
    require((hit, clean) == (1, 0), 'C6 did not block and recover')
    save(case6 / 'probe-hashes.json', {'before_sha256': before_sha256, 'after_sha256': after_sha256})
    record('C6', hit_exit=hit, clean_exit=clean,
           before_sha256=before_sha256, after_sha256=after_sha256)

    failed = execute(dict(a_request, base='0'*40), output / 'C7-failed')
    success = execute(a_request, output / 'C7-success')
    require(failed['status']=='FAILED' and success['status']=='SUCCEEDED'
            and failed['job_id']!=success['job_id'] and failed['trace_id']!=success['trace_id'],
            'C7 failure polluted successful task')
    for item in success['artifacts']:
        checked_artifact(output / 'C7-success', item, success['job_id'])
    record('C7', failed_job=failed['job_id'], succeeded_job=success['job_id'], artifacts=len(success['artifacts']))

    check_idempotency(a_request, output / 'C8')
    record('C8', response_statuses=[202, 202, 409])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    root = args.out.resolve()
    require(root != ROOT/'work' and root.is_relative_to(ROOT/'work'), 'Output must be below work/')
    run(json.loads(args.request.read_text(encoding='utf-8')), root)
