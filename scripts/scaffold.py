#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scaffold.py — 과제 코드 뼈대 만들기: 얇은 입구 run.py + 단계별 모듈 패키지 (표준 라이브러리, Python 3.9)

사용:
  python3 scripts/scaffold.py --stages clean,rules,intervals   # run.py + core/(config·load·pipeline·report + 단계 모듈)
  python3 scripts/scaffold.py --package alarm --stages clean,rules
  python3 scripts/scaffold.py --dry-run --stages clean           # 만들 파일만 출력

규칙(AGENTS.md 4절 코드 구조): PLAN.md 4번 단계 하나 = 모듈 하나(core/<단계>.py) = tests/test_<단계>.py.
읽기(load.py)·쓰기(report.py)는 계산과 분리하고, 상수는 config.py 에 출처와 함께 둔다.
이미 있는 파일은 덮어쓰지 않는다(건너뛴 파일을 출력). 만든 직후 `python3 run.py` 가 data/*.csv 를 읽어
out/result.csv·out/summary.json 을 쓴다 — 과제 README 의 출력 이름·열로 config.py 와 report.py 를 맞춘다.

exit 0 성공(건너뛴 파일 포함) / 1 이름이 잘못됨
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

NAME_RE = re.compile(r'^[a-z][a-z0-9_]*$')
RESERVED = {'config', 'load', 'pipeline', 'report', 'test', 'tests', 'scripts', 'data', 'out'}

RUN_PY = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""명령 한 줄 입구: 입력 폴더를 읽어 파이프라인을 돌리고 결과 파일을 쓴다.

실행: python3 run.py [--input-dir data] [--out-dir out]
계산은 {pkg}/ 패키지에 있다(단계 하나 = 모듈 하나). 이 파일은 인자 읽기 → solve() → 쓰기만 한다.
"""
import argparse
import sys

from {pkg} import config, load, pipeline, report


def main(argv=None):
    """명령행 인자를 읽어 한 번 실행한다.

    입력: argv — 명령행 인자 목록(None 이면 sys.argv)
    출력: 종료 코드 — 0 성공(빈 결과 포함), 1 입력 오류(메시지는 stderr)
    실패: 입력 폴더·파일·열 문제는 ValueError/OSError 를 받아 다음 행동 한 줄과 함께 1을 돌려준다
    """
    ap = argparse.ArgumentParser(description='입력 폴더 → 결과 파일')
    ap.add_argument('--input-dir', default=config.INPUT_DIR)
    ap.add_argument('--out-dir', default=config.OUT_DIR)
    args = ap.parse_args(argv)
    try:
        inputs = load.read_inputs(args.input_dir, config.REQUIRED_COLUMNS)
    except (OSError, ValueError) as e:
        print('입력 오류: %s → --input-dir 경로와 파일·열 이름을 확인하세요' % e, file=sys.stderr)
        return 1
    result = pipeline.solve(inputs)
    paths = report.write_outputs(result, args.out_dir)
    print('status=%s items=%d → %s' % (result['metadata']['status'], len(result['items']), ', '.join(paths)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
'''

INIT_PY = '''"""과제 로직 패키지. 단계 하나 = 모듈 하나(PLAN.md 4번 단계 = {pkg}/<단계>.py = tests/test_<단계>.py)."""
'''

CONFIG_PY = '''"""상수를 한곳에 둔다. 값마다 출처(README 줄 · 담당자 답변 번호 · 결정 ID)를 주석으로 단다."""

INPUT_DIR = 'data'            # 출처: README 제공 데이터 위치
OUT_DIR = 'out'               # 출처: README 안내 "출력은 out/ 아래"
OUTPUT_FILE = 'result.csv'    # 출처: README 제출물 표의 파일 이름으로 바꾼다
SUMMARY_FILE = 'summary.json'  # 집계·사유별 건수(입력 = 통과 + 제외)
OUTPUT_COLUMNS = []           # 출력 열 화이트리스트(순서 고정). 비어 있으면 첫 결과 행의 열 순서
REQUIRED_COLUMNS = {{}}         # {{표 이름: [필수 열]}} — 표 이름은 data/ 의 CSV 파일 이름(확장자 제외)
'''

LOAD_PY = '''"""입력 읽기와 열 검증(입출력 단계). 계산은 하지 않는다."""
import csv
import os


def read_csv(path, required=()):
    """CSV 한 파일을 행 목록으로 읽고 필수 열을 확인한다.

    입력: path — CSV 경로(UTF-8, BOM 허용), required — 반드시 있어야 할 열 이름들
    출력: 행 목록 — 열 이름 → 문자열 값 dict
    실패: 필수 열이 없으면 ValueError('필수 열 없음: <열> (<파일>)')
    """
    with open(path, encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError('필수 열 없음: %s (%s)' % (', '.join(missing), path))
        return [dict(row) for row in reader]


def read_inputs(input_dir, required=None):
    """입력 폴더의 CSV 를 모두 읽는다.

    입력: input_dir — 입력 폴더, required — {{표 이름: 필수 열 목록}}(없으면 열 검사 안 함)
    출력: {{표 이름(파일 이름에서 확장자 제외): 행 목록}}
    실패: 폴더가 없거나 CSV 가 하나도 없으면 ValueError
    """
    if not os.path.isdir(input_dir):
        raise ValueError('입력 폴더 없음: %s' % input_dir)
    names = sorted(f for f in os.listdir(input_dir) if f.lower().endswith('.csv'))
    if not names:
        raise ValueError('CSV 없음: %s' % input_dir)
    required = required or {{}}
    tables = {{}}
    for name in names:
        key = os.path.splitext(name)[0]
        tables[key] = read_csv(os.path.join(input_dir, name), required.get(key, ()))
    return tables
'''

PIPELINE_PY = '''"""단계 순서만 정하는 순수 함수. 파일을 읽거나 쓰지 않는다(입출력은 load.py · report.py)."""
{imports}
# (단계 이름, 함수) — PLAN.md 4번 단계 순서와 같게. 새 단계는 {pkg}/<단계>.py 의 apply 를 여기에 더한다.
STAGES = [{stages}]


def solve(inputs):
    """입력 표들을 단계 순서대로 처리해 결과 행과 집계를 만든다.

    입력: inputs — {{표 이름: 행 목록}} (load.read_inputs 결과)
    출력: {{'items': 결과 행 목록, 'metadata': {{'status', 'input_counts', 'stage_counts'}}}}
    규칙: 주 데이터는 이름순 첫 표다(과제에 맞게 바꾼다). 단계마다 남은 행 수를 stage_counts 에 남긴다
    """
    main_table = sorted(inputs)[0] if inputs else None
    rows = list(inputs.get(main_table, [])) if main_table else []
    stage_counts = {{}}
    for name, func in STAGES:
        rows = func(rows, inputs)
        stage_counts[name] = len(rows)
    metadata = {{
        'status': 'ok',
        'input_counts': {{k: len(v) for k, v in sorted(inputs.items())}},
        'stage_counts': stage_counts,
    }}
    return {{'items': rows, 'metadata': metadata}}
'''

STAGE_PY = '''"""{stage} 단계: PLAN.md 4번 '{stage}' 단계가 하는 일을 한 줄로 적는다."""


def apply(rows, inputs):
    """{stage} 단계를 적용한다. 단계를 구현하기 전에는 행을 그대로 넘긴다.

    입력: rows — 앞 단계의 행 목록, inputs — 전체 입력 표(기준표 조회용)
    출력: 이 단계를 거친 행 목록
    규칙: 구현할 때 규칙 문장과 결정 ID(예: D03)·담당자 답변 번호를 적는다
    테스트: tests/test_{stage}.py
    """
    return list(rows)
'''

REPORT_PY = '''"""결과 파일 쓰기(입출력 단계). 계산은 하지 않는다."""
import csv
import json
import os

from . import config


def write_csv(rows, path, columns):
    """행 목록을 지정한 열 순서로 CSV 에 쓴다.

    입력: rows — 결과 행 목록, path — 출력 경로, columns — 열 이름 순서(화이트리스트)
    출력: 쓴 행 수
    규칙: columns 밖의 열은 쓰지 않는다. UTF-8, 줄바꿈 LF
    """
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(columns), extrasaction='ignore', lineterminator='\\n')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


def write_outputs(result, out_dir):
    """solve() 결과를 출력 파일들로 쓴다.

    입력: result — {{'items', 'metadata'}}, out_dir — 출력 폴더
    출력: 쓴 파일 경로 목록
    """
    items = result['items']
    columns = config.OUTPUT_COLUMNS or (list(items[0].keys()) if items else [])
    csv_path = os.path.join(out_dir, config.OUTPUT_FILE)
    write_csv(items, csv_path, columns)
    summary_path = os.path.join(out_dir, config.SUMMARY_FILE)
    with open(summary_path, 'w', encoding='utf-8') as fh:
        json.dump(result['metadata'], fh, ensure_ascii=False, indent=2, sort_keys=True)
    return [csv_path, summary_path]
'''


def plan_files(pkg, stages):
    """만들 파일과 내용을 정한다.

    입력: pkg — 패키지 이름, stages — 단계 모듈 이름 목록(순서 = 실행 순서)
    출력: [(상대 경로, 내용)] 목록
    """
    imports = ''.join('from . import %s\n' % s for s in stages)
    stage_list = ', '.join("('%s', %s.apply)" % (s, s) for s in stages)
    files = [
        ('run.py', RUN_PY.format(pkg=pkg)),
        (os.path.join(pkg, '__init__.py'), INIT_PY.format(pkg=pkg)),
        (os.path.join(pkg, 'config.py'), CONFIG_PY.format()),
        (os.path.join(pkg, 'load.py'), LOAD_PY.format()),
        (os.path.join(pkg, 'pipeline.py'), PIPELINE_PY.format(pkg=pkg, imports=imports, stages=stage_list)),
        (os.path.join(pkg, 'report.py'), REPORT_PY.format()),
    ]
    for s in stages:
        files.append((os.path.join(pkg, '%s.py' % s), STAGE_PY.format(stage=s)))
    return files


def validate(pkg, stages):
    """패키지·단계 이름을 검사한다.

    입력: pkg — 패키지 이름, stages — 단계 이름 목록
    출력: 문제 문자열 목록(비어 있으면 통과)
    """
    errors = []
    if not NAME_RE.match(pkg) or pkg in RESERVED:
        errors.append('패키지 이름은 소문자·숫자·밑줄, 예약어(%s) 제외: %r' % (', '.join(sorted(RESERVED)), pkg))
    for s in stages:
        if not NAME_RE.match(s) or s in RESERVED:
            errors.append('단계 이름은 소문자·숫자·밑줄, 예약어 제외: %r' % s)
    if len(set(stages)) != len(stages):
        errors.append('단계 이름이 중복됨: %s' % ', '.join(stages))
    return errors


def write_files(root, files, dry_run=False):
    """파일을 만든다. 이미 있으면 건너뛴다.

    입력: root — 작업 폴더, files — [(상대 경로, 내용)], dry_run — True 면 쓰지 않고 목록만
    출력: (만든 경로 목록, 건너뛴 경로 목록)
    """
    made, skipped = [], []
    for rel, body in files:
        path = os.path.join(root, rel)
        if os.path.exists(path):
            skipped.append(rel)
            continue
        made.append(rel)
        if dry_run:
            continue
        os.makedirs(os.path.dirname(path) or root, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(body)
    return made, skipped


def main(argv=None):
    """명령행 진입점.

    입력: argv — 명령행 인자(None 이면 sys.argv)
    출력: 종료 코드 0(성공, 건너뛴 파일 포함) / 1(이름 오류)
    """
    ap = argparse.ArgumentParser(description='과제 코드 뼈대(run.py + 단계별 모듈) 만들기 — 있는 파일은 덮어쓰지 않음')
    ap.add_argument('--package', default='core', help='계산 패키지 이름(기본 core)')
    ap.add_argument('--stages', default='', help='PLAN 4번 단계 모듈 이름, 쉼표로(예: clean,rules,intervals)')
    ap.add_argument('--root', default='.', help='작업 폴더(기본: 현재 폴더)')
    ap.add_argument('--dry-run', action='store_true', help='만들 파일만 출력')
    args = ap.parse_args(argv)
    stages = [s.strip() for s in args.stages.split(',') if s.strip()]
    errors = validate(args.package, stages)
    if errors:
        for e in errors:
            print('오류: ' + e, file=sys.stderr)
        return 1
    made, skipped = write_files(args.root, plan_files(args.package, stages), args.dry_run)
    verb = '만들 파일' if args.dry_run else '만든 파일'
    print('%s %d개: %s' % (verb, len(made), ', '.join(p.replace(os.sep, '/') for p in made) or '없음'))
    if skipped:
        print('이미 있어 건너뜀 %d개: %s' % (len(skipped), ', '.join(p.replace(os.sep, '/') for p in skipped)))
        if os.path.join(args.package, 'pipeline.py') in skipped and stages:
            print('  → %s/pipeline.py 의 STAGES 에 새 단계를 직접 더하세요: %s' % (
                args.package, ', '.join("('%s', %s.apply)" % (s, s) for s in stages)))
    if not args.dry_run and made:
        print('다음: python3 run.py → out/ 확인 · config.py 의 출력 이름·열을 README 에 맞춤 · '
              'tests/test_template.py 의 ENTRY 를 %s.pipeline.solve 로' % args.package)
    return 0


if __name__ == '__main__':
    sys.exit(main())
