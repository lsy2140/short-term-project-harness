# -*- coding: utf-8 -*-
"""규칙 1개 = 테스트 1개 템플릿 (unittest, pytest 불필요, Python 3.9)
실행: python3 -m unittest -v
원칙: 완료 조건 1개 = 테스트 1개 / 이름은 업무 규칙을 문장으로 / 실패 경로가 정상 경로보다 많게 / 새 규칙은 먼저 FAIL을 본다.
5분류: 정상 경로 · 업무 규칙("이건 나오면 안 돼") · 경계값 · 실패 경로(명시적 거부) · 계약(결정성·입력 불변·직렬화) · 보안·문서 계약
과제를 받으면 ENTRY를 실제 진입 함수(scaffold 뼈대면 core.pipeline.solve)로 바꾸고, 예시 테스트를 지우며 규칙 테스트를 채운다. 맨 아래 보안·문서 계약 절은 그대로 둔다.
"""
import copy
import json
import os
import re
import sys
import tempfile
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


# ---------------------------------------------------------------- 예시 로직 (과제 코드로 교체)
def ENTRY(payload):
    """입력 dict → 출력 dict. 과제의 진입 함수(solve 등)로 바꾼다. 입력을 변형하지 않는다."""
    rows = payload.get('rows')
    if rows is None:
        raise ValueError('필수 키 없음: rows')
    limit = payload.get('limit', 100)
    out, excluded = [], {'missing_value': 0}
    for r in rows:
        if r.get('value') is None:
            excluded['missing_value'] += 1
            continue
        out.append({'id': r['id'], 'alert': r['value'] >= limit})
    out.sort(key=lambda x: (not x['alert'], x['id']))  # 정렬·tie-break 명시
    return {'items': out, 'metadata': {'total': len(rows), 'kept': len(out), 'excluded_counts': excluded}}


SAMPLE = {'limit': 100, 'rows': [{'id': 'B', 'value': 100}, {'id': 'A', 'value': 99}, {'id': 'C', 'value': None}]}


# ---------------------------------------------------------------- 정상 경로
class TestHappyPath(unittest.TestCase):
    def test_sample_runs_and_returns_items(self):
        out = ENTRY(copy.deepcopy(SAMPLE))
        self.assertIn('items', out)
        self.assertEqual(out['metadata']['total'], 3)


# ---------------------------------------------------------------- 업무 규칙 ("이건 나오면 안 돼")
class TestBusinessRules(unittest.TestCase):
    def test_missing_value_row_is_excluded_and_counted(self):
        out = ENTRY(copy.deepcopy(SAMPLE))
        self.assertNotIn('C', [i['id'] for i in out['items']])
        self.assertEqual(out['metadata']['excluded_counts']['missing_value'], 1)

    def test_total_is_conserved(self):
        """입력 건수 == 통과 + 제외 (합계 보존 불변량)"""
        out = ENTRY(copy.deepcopy(SAMPLE))
        self.assertEqual(out['metadata']['total'], out['metadata']['kept'] + sum(out['metadata']['excluded_counts'].values()))


# ---------------------------------------------------------------- 경계값
class TestBoundary(unittest.TestCase):
    """임계값과 정확히 같은 값 / ±1 / 빈 목록 / 원소 1개 / 시각 양 끝 / 대소문자 다른 같은 값 / 중복 ID / 음수와 0"""

    def test_equal_to_limit_is_alert_when_inclusive(self):
        out = ENTRY({'limit': 100, 'rows': [{'id': 'B', 'value': 100}]})
        self.assertTrue(out['items'][0]['alert'])

    def test_one_below_limit_is_not_alert(self):
        out = ENTRY({'limit': 100, 'rows': [{'id': 'A', 'value': 99}]})
        self.assertFalse(out['items'][0]['alert'])

    def test_empty_rows_gives_empty_items_not_crash(self):
        out = ENTRY({'limit': 100, 'rows': []})
        self.assertEqual(out['items'], [])


# ---------------------------------------------------------------- 실패 경로 (명시적 거부)
class TestFailurePath(unittest.TestCase):
    """오염 입력은 ValueError(메시지에 필드명)로 명시적으로 거부한다. KeyError/TypeError로 터지면 미처리 크래시다."""

    def test_missing_required_key_is_rejected_explicitly(self):
        with self.assertRaises(ValueError) as ctx:
            ENTRY({'limit': 100})
        self.assertIn('rows', str(ctx.exception))


# ---------------------------------------------------------------- 계약 (과제와 무관하게 항상 넣는 3개)
class TestContract(unittest.TestCase):
    def test_same_input_gives_same_output(self):
        a = ENTRY(copy.deepcopy(SAMPLE))
        b = ENTRY(copy.deepcopy(SAMPLE))
        self.assertEqual(json.dumps(a, sort_keys=True, default=str), json.dumps(b, sort_keys=True, default=str))

    def test_does_not_mutate_input(self):
        payload = copy.deepcopy(SAMPLE)
        snapshot = copy.deepcopy(payload)
        ENTRY(payload)
        self.assertEqual(payload, snapshot)

    def test_output_is_json_serializable(self):
        json.dumps(ENTRY(copy.deepcopy(SAMPLE)), ensure_ascii=False, default=str)


# ---------------------------------------------------------------- 보안·문서 계약 (제출 전 1회)
STATUS_RE = re.compile(r'^Status:\s*`?\s*([A-Za-z]+)')


def task_status(root=ROOT):
    """TASK.md 의 Status 값 = 'Status:' 뒤 첫 단어(백틱 안). 같은 줄 안내 문구 '(… 제출 전 `FROZEN`)' 속 단어는 무시한다."""
    p = os.path.join(root, 'TASK.md')
    if not os.path.exists(p):
        return ''
    with open(p, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            m = STATUS_RE.match(line)
            if m:
                return m.group(1).upper()
    return ''


class TestSubmissionContract(unittest.TestCase):
    """제출 전 1회: TASK.md 의 Status 가 FROZEN 일 때만 검사한다(동결 전에는 skip — 진입점·README 가 아직 없을 수 있다)."""

    def setUp(self):
        if task_status() != 'FROZEN':
            self.skipTest('동결 전(TASK.md Status 가 FROZEN 이 아님) — 제출 계약 검사는 동결 후에')

    def test_no_template_phrases_in_submission_docs(self):
        bad = re.compile(r'\bT' 'BD\b|미' '구현|TEMPLATE 상태')  # 조각으로 나눈 이유: preflight 자체 스캔 오탐 방지
        for name in ('README.md', 'PLAN.md'):
            p = os.path.join(ROOT, name)
            if os.path.exists(p):
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    self.assertIsNone(bad.search(fh.read()), '%s 에 템플릿 문구가 남아 있음' % name)

    def test_readme_run_command_entrypoint_exists(self):
        """README 코드블록의 `python3 <파일>` 진입점 파일이 실제로 존재한다 (문서↔코드 일치)."""
        p = os.path.join(ROOT, 'README.md')
        if not os.path.exists(p):
            self.skipTest('README 없음')
        with open(p, encoding='utf-8', errors='ignore') as fh:
            text = fh.read()
        if text.startswith('# short-term-project-harness'):
            self.skipTest('하네스 자체 README (과제 README가 아님)')
        for m in re.finditer(r'python3?\s+([\w./-]+\.py)', text):
            path = os.path.join(ROOT, m.group(1))
            if '<' in m.group(1):
                continue
            self.assertTrue(os.path.exists(path), 'README 가 가리키는 진입점 없음: %s' % m.group(1))


class TestStatusGuard(unittest.TestCase):
    """제출 계약 검사가 동결 전에 돌지 않게: Status 값만 읽고 안내 문구 속 FROZEN 은 무시한다."""

    def status_of(self, line):
        with tempfile.TemporaryDirectory() as d:
            if line is not None:
                with open(os.path.join(d, 'TASK.md'), 'w', encoding='utf-8') as fh:
                    fh.write('# TASK\n\n%s\n' % line)
            return task_status(d)

    def test_status_reads_only_its_own_value(self):
        guide = '  (시작하면 `ACTIVE`, 제출 전 `FROZEN`)'
        self.assertEqual(self.status_of('Status: `TEMPLATE`' + guide), 'TEMPLATE')
        self.assertEqual(self.status_of('Status: `ACTIVE`' + guide), 'ACTIVE')
        self.assertEqual(self.status_of('Status: `FROZEN`' + guide), 'FROZEN')
        self.assertEqual(self.status_of('Status: frozen'), 'FROZEN')
        self.assertEqual(self.status_of(None), '')


if __name__ == '__main__':
    unittest.main()
