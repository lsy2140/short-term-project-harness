# -*- coding: utf-8 -*-
"""규칙 1개 = 테스트 1개 템플릿 (unittest, pytest 불필요, Python 3.9)
실행: python3 -m unittest -v
원칙: 완료 조건 1개 = 테스트 1개 / 이름은 업무 규칙을 문장으로 / 실패 경로가 정상 경로보다 많게 / 새 규칙은 먼저 FAIL을 본다.
분류: 정상 경로 · 업무 규칙("이건 나오면 안 돼") · 경계값 · 실패 경로(명시적 거부) · 계약(결정성·입력 불변·직렬화) · 보안·문서 계약
과제를 받으면 ENTRY를 실제 진입 함수(scaffold 뼈대면 core.pipeline.solve)로 바꾸고, 예시 테스트를 지우며 규칙 테스트를 채운다. 맨 아래 보안·문서 계약 절은 그대로 둔다.
ENTRY 를 core.pipeline.solve 로 바꾸면 SAMPLE 도 solve 입력 모양({표 이름: [행…]}, 출력 metadata 는 status·input_counts·stage_counts)으로
바꾸고 예시 테스트(정상·업무 규칙·경계·실패)는 지운다. TestContract 3개는 SAMPLE 만 바꿔 그대로 둔다.
보안·문서 계약은 TASK.md 머리 2행 Status 가 FROZEN 일 때만 돈다: TASK·PLAN·DECISIONS·HANDOFF·PRD·README 의 템플릿 문구·'아직 전송하지 않음'·'HH:MM'·'__:__'·'__/__'·'exit __'·'___' 잔존·README 진입점.
TASK.md 머리 2행 형식(Status·시작·마감 키)은 늘 검사한다 — status.py 와 동결 검사가 이 줄을 읽는다(status.py 출력 줄을 붙여넣지 않는다).
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
HEAD_KEYS_RE = (re.compile(r'시작\s*[:：]'), re.compile(r'마감\s*[:：]'))   # status.py 가 남은 분을 계산하는 키
LEFTOVER_FILES = ('TASK.md', 'PLAN.md', 'DECISIONS.md', 'HANDOFF.md', 'PRD.md', 'README.md')
# 템플릿 자리표시: 시각 'HH:MM'·'__:__'(PRD 승인·갱신 포함) / 숫자 '__/__'·'exit __' / 빈칸 '___'(TASK 한 문장 목표·PRD 출처 수) / DECISIONS 0 PRD 송부 '아직 전송하지 않음'
LEFTOVER_PHRASES = ('아직 전송하지 않음', 'HH:MM', '__:__', '__/__', 'exit __', '___')
COMMENT_RE = re.compile(r'<!--.*?-->', re.S)


def task_status(root=ROOT):
    """TASK.md 의 Status 값을 읽는다.
    입력: root — TASK.md 가 있는 폴더
    출력: 'Status:' 뒤 첫 단어(백틱 안)를 대문자로, 파일·줄이 없으면 ''
    규칙: 같은 줄 뒤쪽 '· 시작: …' 이나 안내 문구 '(… 제출 전 `FROZEN`)' 속 단어는 무시한다.
    """
    p = os.path.join(root, 'TASK.md')
    if not os.path.exists(p):
        return ''
    with open(p, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            m = STATUS_RE.match(line)
            if m:
                return m.group(1).upper()
    return ''


def leftover_phrases(root=ROOT):
    """제출 문서에 남은 자리표시를 찾는다.
    입력: root — 제출 문서가 있는 폴더
    출력: [(파일 이름, 문구)] — LEFTOVER_FILES 안의 LEFTOVER_PHRASES('아직 전송하지 않음'·'HH:MM'·'__:__'·'__/__'·'exit __'·'___')
    규칙: HTML 주석(<!-- -->) 안은 템플릿 안내문이라 보지 않는다. 없는 파일은 건너뛴다.
    """
    hits = []
    for name in LEFTOVER_FILES:
        p = os.path.join(root, name)
        if not os.path.exists(p):
            continue
        with open(p, encoding='utf-8', errors='ignore') as fh:
            text = COMMENT_RE.sub('', fh.read())
        hits.extend((name, phrase) for phrase in LEFTOVER_PHRASES if phrase in text)
    return hits


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

    def test_no_unsent_or_unfilled_time_left(self):
        """'아직 전송하지 않음'·'HH:MM'·머리줄 자리표시('__:__'·'__/__'·'exit __'·'___')가 제출 문서에 남지 않는다
        (PRD 송부·회신·승인 시각과 숫자 머리줄을 비운 채 동결한 감점의 반복 방지)."""
        self.assertEqual(leftover_phrases(), [], '시각·숫자·회신 원문으로 바꾸거나 해당 줄을 지운다')

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
    """제출 계약 검사가 동결 전에 돌지 않게: Status 값만 읽고 같은 줄의 다른 값·안내 문구 속 FROZEN 은 무시한다."""

    def status_of(self, line):
        with tempfile.TemporaryDirectory() as d:
            if line is not None:
                with open(os.path.join(d, 'TASK.md'), 'w', encoding='utf-8') as fh:
                    fh.write('# TASK — 과제 계약\n%s\n[끝] -\n' % line)
            return task_status(d)

    def test_status_reads_only_its_own_value(self):
        guide = '  (시작하면 `ACTIVE`, 제출 전 `FROZEN`)'
        self.assertEqual(self.status_of('Status: `TEMPLATE`' + guide), 'TEMPLATE')
        self.assertEqual(self.status_of('Status: `ACTIVE`' + guide), 'ACTIVE')
        self.assertEqual(self.status_of('Status: `FROZEN`' + guide), 'FROZEN')
        self.assertEqual(self.status_of('Status: frozen'), 'FROZEN')
        self.assertEqual(self.status_of(None), '')

    def test_status_reads_head_line_format(self):
        """TASK.md 머리 2행 형식(Status · 시작 · 마감 · 갱신 · CP)에서도 Status 값만 읽는다."""
        self.assertEqual(self.status_of('Status: `TEMPLATE` · 시작: __:__ · 마감: __:__ · 갱신: __:__ · CP: -'), 'TEMPLATE')
        self.assertEqual(self.status_of('Status: `ACTIVE` · 시작: 09:00 · 마감: 13:00 · 갱신: 10:12 · CP: CP1'), 'ACTIVE')
        self.assertEqual(self.status_of('Status: `FROZEN` · 시작: 09:00 · 마감: 13:00 · 갱신: 12:40 · CP: CP3'), 'FROZEN')

    def test_task_md_status_line_is_readable(self):
        """작업 폴더의 TASK.md Status 가 TEMPLATE·ACTIVE·FROZEN 중 하나로 읽힌다(status.py 와 동결 검사가 이 값에 기댄다)."""
        if not os.path.exists(os.path.join(ROOT, 'TASK.md')):
            self.skipTest('TASK.md 없음')
        self.assertIn(task_status(), ('TEMPLATE', 'ACTIVE', 'FROZEN'))

    def test_task_md_head_line_keeps_start_and_deadline_keys(self):
        """TASK.md 의 Status 줄(2행)에 '시작:'·'마감:' 키가 남아 있다 — status.py 줄('상태: … · 남은 N분')로 덮으면 남은 분이 사라진다."""
        p = os.path.join(ROOT, 'TASK.md')
        if not os.path.exists(p):
            self.skipTest('TASK.md 없음')
        with open(p, encoding='utf-8', errors='ignore') as fh:
            line = next((x for x in fh if STATUS_RE.match(x)), '')
        self.assertTrue(line, "TASK.md 에 'Status: `X` · 시작: · 마감: · 갱신: · CP:' 줄이 없다 — 2행 형식을 되돌린다")
        for key in HEAD_KEYS_RE:
            self.assertRegex(line, key, "TASK.md 머리 2행에 %s 키가 없다 — 형식은 그대로 두고 값만 고친다" % key.pattern)

    def test_head_line_overwritten_by_status_output_is_caught(self):
        """먼저 FAIL 확인: 2행을 status.py 출력으로 덮은 TASK.md 는 Status 값을 잃는다."""
        self.assertEqual(self.status_of('상태: ACTIVE · 남은 120분 · task 0/3 · debug 기록 없음 · 대기 없음 · PRD v1'), '')


class TestLeftoverGuard(unittest.TestCase):
    """동결 검사가 실제로 잡는지(먼저 FAIL 확인): 임시 폴더의 문서로 본다. 동결 전에도 돈다."""

    def hits_of(self, files):
        with tempfile.TemporaryDirectory() as d:
            for name, text in files.items():
                with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
                    fh.write(text)
            return leftover_phrases(d)

    def test_unsent_and_unfilled_time_are_caught(self):
        hits = self.hits_of({'DECISIONS.md': '- PRD 송부: 아직 전송하지 않음\n- 담당자 회신: HH:MM "원문"\n'})
        self.assertEqual(sorted(hits), [('DECISIONS.md', 'HH:MM'), ('DECISIONS.md', '아직 전송하지 않음')])

    def test_comments_filled_times_and_other_files_pass(self):
        hits = self.hits_of({
            'DECISIONS.md': '<!-- 보내기 전 송부 줄은 아직 전송하지 않음, HH:MM -->\n- PRD 송부: 10:42\n',
            'PRD.md': '버전: `v1` · 승인: 10:50 · 갱신: 11:20 · 출처: README 12줄 · 답변 7개 · 가정 3개 · 열린 질문 0개\n',
            'AGENTS.md': '반영하면 `[x] 반영 HH:MM`\n',
        })
        self.assertEqual(hits, [])

    def test_unfilled_head_lines_are_caught(self):
        """PLAN·HANDOFF 숫자 머리줄과 TASK 시각·한 문장 빈칸이 남으면 잡는다. 채운 줄은 통과한다."""
        hits = self.hits_of({
            'PLAN.md': 'task __/__ PASS · 테스트 __/__ PASS · check_contract exit __ · 갱신 __:__\n',
            'TASK.md': 'Status: `FROZEN` · 시작: 09:00 · 마감: 13:00 · 갱신: __:__ · CP: CP3\n> 나는 ___ 와 ___ 를 자동화한다.\n',
        })
        self.assertEqual(sorted(hits), [('PLAN.md', '__/__'), ('PLAN.md', '__:__'), ('PLAN.md', 'exit __'),
                                        ('TASK.md', '__:__'), ('TASK.md', '___')])
        filled = self.hits_of({
            'PLAN.md': 'task 9/9 PASS · 테스트 41/41 PASS · check_contract exit 0 · 갱신 12:40\n',
            'HANDOFF.md': 'python3 scripts/preflight.py --require out/result.csv    # exit 0\n',
        })
        self.assertEqual(filled, [])

    def test_unapproved_prd_head_is_caught(self):
        """PRD.md 도 제출 문서다: 승인·갱신 시각(__:__)과 출처 수(___)를 비운 채 동결하면 잡는다."""
        hits = self.hits_of({'PRD.md': ('버전: `v0` · 승인: __:__ · 갱신: __:__ · 출처: README ___줄 · 답변 ___개\n'
                                        '<!-- 승인 뒤 10절에 __:__ 한 줄 -->\n| v1 | __:__ | 최초 승인 | 사람 | - |\n')})
        self.assertEqual(sorted(hits), [('PRD.md', '__:__'), ('PRD.md', '___')])


if __name__ == '__main__':
    unittest.main()
