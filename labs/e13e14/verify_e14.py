"""Check five-stage provenance, recovery and the saved service logs."""
import argparse
import json
from pathlib import Path

from orchestrate import digest, host_path

STAGES = ('draft', 'full-check', 'incremental-check', 'repair', 'recheck')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_artifacts(folder, result):
    count = 0
    for item in result['artifacts']:
        path = (folder / item['uri']).resolve()
        require(path.is_relative_to(folder.resolve()) and path.is_file(), 'Artifact path mismatch')
        require(path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], 'Artifact hash mismatch')
        count += 1
    require(count > 0, 'Missing artifact manifest')
    return count


def verify(folder, logs):
    request = read(folder / 'request.json')
    result = read(folder / 'result.json')
    require(result['status'] == 'SUCCEEDED', 'Failed E14 job')
    require(result['base_commit'] == request['base'] and result['target_commit'] == request['target'], 'Commit mismatch')
    job, trace = result['job_id'], result['trace_id']
    require(tuple(x['name'] for x in result['stages']) == STAGES, 'Stage sequence mismatch')
    envelopes = {}
    for name, item in zip(STAGES, result['stages']):
        entry = folder / f'{name}.json'
        require(item['artifact'] == {'uri': entry.name, 'sha256': digest(entry)}, 'Stage hash mismatch')
        envelope = read(entry)
        expected_commit = request['base'] if name == 'full-check' else request['target']
        require((envelope['name'], envelope['job_id'], envelope['trace_id'], envelope['status'], envelope['commit'])
                == (name, job, trace, 'SUCCEEDED', expected_commit), 'Stage identity mismatch')
        envelopes[name] = envelope['data']
    repair = envelopes['repair']
    increment = envelopes['incremental-check']
    original_report = host_path(increment['report'])
    require(original_report.is_relative_to(folder.resolve()), 'Report escapes job directory')
    origin = repair['input_report']
    require(origin == {'path': increment['report'], 'sha256': digest(original_report),
                       'job_id': job, 'trace_id': trace}, 'Repair did not consume this exact report')
    patch = host_path(repair['patch'])
    require(patch.is_relative_to(folder.resolve()) and repair['sha256'] == digest(patch)
            and repair['validation']['accepted'], 'Patch mismatch or failed validation')
    final = envelopes['recheck']['result']['result']
    require(final['status'] == 'SUCCEEDED' and not any(i['type'] == 'MISSING' for i in final['findings']),
            'Dynamic recheck failed')
    require((folder / 'final-full/verify.log').read_text().strip() == request.get('expected_output','1'),
            'Recheck output mismatch')
    expected_logs = {('draft', 'draft'), ('buildchecker', 'full-check'), ('buildchecker', 'target-oracle'),
                     ('echecker', 'incremental-check'), ('mdfixer', 'repair'), ('buildchecker', 'recheck')}
    require(expected_logs <= {(x['role'], x['stage']) for x in logs if x.get('job_id') == job
                             and x.get('trace_id') == trace and x.get('status') == 'SUCCEEDED'
                             and isinstance(x.get('elapsed_ms'), int)}, 'Service trace missing')
    return {'job_id': job, 'trace_id': trace, 'artifact_count': check_artifacts(folder, result),
            'target': request['target'], 'repair_report_sha256': origin['sha256'],
            'patch_sha256': repair['sha256'], 'output': request.get('expected_output','1'),
            'remaining_missing': 0}


def verify_timeout(folder, logs, recovered):
    result = read(folder / 'result.json')
    draft = read(folder / 'draft-build/result.json')
    response = read(folder / 'draft-response.json')
    require(result['status'] == 'FAILED' and draft['status'] == 'TIMED_OUT'
            and response.get('error_code') == 'TIMEOUT' and not result['stages'], 'Timeout not isolated')
    records = list((folder / 'draft-build').rglob('*.timeout.json'))
    require(len(records) == 1, 'Missing Docker client process observation')
    process = read(records[0])
    require(process['returncode'] < 0 and process['process_group_alive_after_wait'] is False
            and not (folder / 'draft-build/verify-container-id.txt').exists(), 'Timed out client or container remains')
    require(result['job_id'] != recovered['job_id'] and result['trace_id'] != recovered['trace_id'],
            'Recovery reused failed job identity')
    require(any(x.get('job_id') == result['job_id'] and x.get('trace_id') == result['trace_id']
                and x.get('stage') == 'draft' and x.get('error_code') == 'TIMEOUT' for x in logs),
            'Timeout log missing')
    return {'job_id': result['job_id'], 'trace_id': result['trace_id'], 'process': process,
            'artifact_count': check_artifacts(folder, result)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixed', required=True, type=Path)
    parser.add_argument('--a14', required=True, type=Path)
    parser.add_argument('--timeout', required=True, type=Path)
    parser.add_argument('--recovery', required=True, type=Path)
    parser.add_argument('--logs', required=True, type=Path)
    args = parser.parse_args()
    events = [json.loads(line[line.index('{'):]) for line in args.logs.read_text().splitlines()
              if '{"role":' in line]
    recovery = verify(args.recovery, events)
    print(json.dumps({'fixed_sample': verify(args.fixed, events), 'a14_project': verify(args.a14, events),
                      'timeout': verify_timeout(args.timeout, events, recovery), 'recovery': recovery}, indent=2))
