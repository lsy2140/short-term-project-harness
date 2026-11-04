# -*- coding: utf-8 -*-
"""scripts/status.py 계약 테스트 (unittest, Python 3.9). 실행: python3 -m unittest discover -s scripts/tests -p test_status.py -v
분류: 1줄 형식(임시 폴더 fixture) / 마감 미기록·파일 없음도 exit 0 / --json 1줄(fixture 1KB 이하) /
      입력 파싱(task 표·생략·--tests·debug·pending — decide.py 미답 판정과 같음·에이전트·PRD 버전) /
      시각(자정 넘김) / 시간에 따라 달라지는 것은 '남은 N분' 숫자뿐(분기·추천·독촉 0) / CLI(--help·인자 오류 exit 2)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # scripts/tests → 작업 폴더
SCRIPTS = os.path.join(ROOT, 'scripts')
# 'scripts' 라는 이름은 다른 설치 패키지와 겹칠 수 있어 폴더를 직접 경로에 넣고 모듈 이름으로 가져온다.
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import status  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING='utf-8')

TASK_HEAD = ('# TASK — 과제 계약\n'
             'Status: `ACTIVE` · 시작: 09:00 · 마감: 13:00 · 갱신: 10:20 · CP: 1\n'
             '[끝] 계약 고정 · 더미 렌더\n[남음] 판정 04\n[대기] D07\n\n## 한 문장\n')
PLAN_TASKS = """# PLAN

## 1. 문제 정의
- 목표:

## 4. task 표
| # | task | 담당 | 검증 | 입력 | 산출 파일 | 완료 조건 | 의존 | 분 | 상태 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 계약 고정 | A | C | README | work/contract.md | `test_contract_cols` | - | 15 | PASS |
| 2 | 더미 렌더 | B | 사람 | contract | static/index.html | HUMAN_CHECK | 1 | 20 | PASS |
| 3 | 중복 제거 | A | C | data/a.csv | out/result.csv | `test_dup_removed` | 1 | 20 | PASS(10:15) |
| 4 | 판정 04 | A | C | out/result.csv | out/result.csv | `test_judge` | 3 | 30 | FAIL |
| 5 | 엣지 입력 | C | - | data/edge | out/report/stage_08.md | `test_edge` | 3 | 15 | NOT_RUN |
| 6 | 화면 최종 | B | 사람 | data.json | static/ | HUMAN_CHECK | 2 | 25 | HUMAN_CHECK |
| 7 |  |  |  |  |  | `test_` |  |  | NOT_RUN |

## 5. 검증 결과
| 검증 | 명령 | 결과 |
|---|---|---|
"""
PENDING = (
    '# 결정 대기함\n미답 3건(담당자 확인 2)\n\n'
    '## D00 (예시, 삭제 가능) 계산식   (영향: 정렬 | 담당자 확인: 필요)\n- [ ] A. 가 (추천)\n- [ ] B. 나\n메모:\n\n'
    '## D07 계산식   (영향: 정렬 | 담당자 확인: 필요)\n- [ ] A. 최대 (추천)\n- [ ] B. 평균\n담당자 질문: 무엇을 먼저 보시나요?\n메모:\n\n'
    '## D08 반올림   (영향: 출력 | 담당자 확인: 불필요 — 기술 선택)\n- [ ] A. 둘째 자리 (추천)\n- [ ] B. 정수\n메모:\n\n'
    '## D09 시간대   (영향: 시각 | 담당자 확인: 필요)\n- [ ] A. UTC\n- [x] 반영 10:35 B. KST (추천)\n메모:\n\n'
    '## D41 빈 화면 문구   (영향: 화면 | 담당자 확인: 필요)\n- [ ] A. 안내 문장 (추천)\n- [ ] B. 빈 표\n담당자 질문: 데이터가 없으면 무엇을 보여야 하나요?\n메모:\n')
AGENT_A = '# A_core — 핵심기술\n상태: 판정 04 구현 중 · 갱신 10:20\n\n## ① 역할\n'
AGENT_B = '# B_web — 웹서비스\n상태: 더미 렌더 완료 · 갱신 10:05\n'
AGENT_TEMPLATE = '# <이름> — <역할 한 줄>\n상태: <한 줄> · 갱신 HH:MM\n'
PRD_HEAD = '# PRD — 제품 요구 문서 (요구사항의 단일 원본)\n버전: `v1` · 승인: 09:40 · 갱신: 09:40 · 출처: README 12줄\n'
FORBIDDEN_IN_LINE = ('추천', '독촉', '해야', '하세요', '지금 바로', '동결', 'freeze', '구간', '다음 할 일')


def run_cli(*args):
    cmd = [sys.executable, os.path.join(SCRIPTS, 'status.py')] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, timeout=30)


class _TmpRoot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='status_test_')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path) or self.root, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)

    def full_fixture(self):
        self.write('TASK.md', TASK_HEAD)
        self.write('PLAN.md', PLAN_TASKS)
        self.write(os.path.join('decisions', 'pending.md'), PENDING)
        for stage, files in (('01_계약', ('red.txt', 'green.txt')), ('02_규칙_tz', ('red.txt',)), ('05_더미렌더', ('green.txt',))):
            for f in files:
                self.write(os.path.join('out', 'debug', stage, f), 'x\n')
        self.write(os.path.join('work', 'agents', '_template.md'), AGENT_TEMPLATE)
        self.write(os.path.join('work', 'agents', 'A_core.md'), AGENT_A)
        self.write(os.path.join('work', 'agents', 'B_web.md'), AGENT_B)
        self.write('PRD.md', PRD_HEAD)


# ---------------------------------------------------------------- 1줄 형식
class TestOneLine(_TmpRoot):
    def test_full_fixture_gives_exactly_one_line_in_contract_shape(self):
        self.full_fixture()
        done = run_cli('--root', self.root, '--now', '11:26', '--tests', '24/24')
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = done.stdout.splitlines()
        self.assertEqual(len(lines), 1, done.stdout)
        self.assertEqual(done.stdout.count('\n'), 1)
        line = lines[0]
        self.assertEqual(line, '상태: ACTIVE · 남은 94분 · task 3/6 · 테스트 24/24 · debug green 2/3 · '
                               '대기 D07·D08·D41(담당자 D07·D41) · A_core: 판정 04 구현 중 · B_web: 더미 렌더 완료 · PRD v1')
        self.assertNotIn('갱신', line)                      # 에이전트 줄의 갱신 시각은 떼어 낸다
        self.assertNotIn('<이름>', line)                    # _template.md 는 세지 않는다
        for word in FORBIDDEN_IN_LINE:
            self.assertNotIn(word, line, word)

    def test_without_tests_arg_the_test_slot_is_absent(self):
        self.full_fixture()
        line = status.build(self.root, now='11:26')['line']
        self.assertNotIn('테스트', line)
        self.assertIn('남은 94분 · task 3/6 · debug green 2/3', line)

    def test_only_the_remaining_minutes_change_with_the_clock(self):
        """시간은 숫자 하나만 바꾼다 — 시작 전·중간·마감 뒤 어느 시각에도 나머지 문구는 글자 그대로 같다."""
        self.full_fixture()
        seen = set()
        for now in ('08:30', '09:00', '10:14', '11:26', '12:59', '13:00', '13:45', '23:59'):
            line = status.build(self.root, now=now)['line']
            parts = line.split(' · ')
            self.assertRegex(parts[1], r'^(남은 \d+분|마감 지남 \d+분)$', now)
            seen.add(' · '.join(parts[:1] + parts[2:]))
        self.assertEqual(len(seen), 1, seen)
        self.assertIn('남은 270분', status.build(self.root, now='08:30')['line'])
        self.assertIn('남은 0분', status.build(self.root, now='13:00')['line'])
        self.assertIn('마감 지남 45분', status.build(self.root, now='13:45')['line'])


# ---------------------------------------------------------------- 마감 미기록 · 파일 없음
class TestMissingInputs(_TmpRoot):
    def test_no_deadline_shows_unrecorded_and_exit_0(self):
        self.write('TASK.md', '# TASK — 과제 계약\nStatus: `TEMPLATE` · 시작: __:__ · 마감: __:__ · 갱신: __:__ · CP: -\n')
        done = run_cli('--root', self.root, '--now', '10:00')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), '상태: TEMPLATE · 마감 미기록 · task 표 없음 · debug 기록 없음 · 대기 없음 · PRD 없음')
        data = status.build(self.root, now='10:00')
        self.assertIsNone(data['start'])
        self.assertIsNone(data['deadline'])
        self.assertIsNone(data['cp'])

    def test_empty_folder_still_prints_one_line_and_exit_0(self):
        done = run_cli('--root', self.root, '--now', '10:00')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), '상태: 미기록 · 마감 미기록 · task 표 없음 · debug 기록 없음 · 대기 없음 · PRD 없음')

    def test_start_without_deadline_gives_elapsed_in_json_only(self):
        self.write('TASK.md', '# TASK\nStatus: `ACTIVE` · 시작: 09:05 · 마감: __:__\n')
        data = status.build(self.root, now='10:19')
        self.assertEqual(data['elapsed_min'], 74)
        self.assertIsNone(data['remaining_min'])
        self.assertIn('마감 미기록', data['line'])
        self.assertNotIn('74', data['line'])

    def test_start_and_deadline_without_colon_are_read(self):
        self.write('TASK.md', '# TASK\nStatus: `ACTIVE` · 시작 09:00 · 마감 13:00 · 갱신: __:__ · CP: -\n')
        head = status.read_task_head(self.root)
        self.assertEqual((head['start'], head['deadline']), ('09:00', '13:00'))
        self.assertIn('남은 94분', status.build(self.root, now='11:26')['line'])

    def test_head_values_beyond_line_20_are_ignored(self):
        self.write('TASK.md', '# TASK\n' + '\n' * 25 + 'Status: `ACTIVE` · 시작: 09:00 · 마감: 13:00\n')
        head = status.read_task_head(self.root)
        self.assertEqual(head, {'status': None, 'start': None, 'deadline': None, 'cp': None})


# ---------------------------------------------------------------- --json
class TestJson(_TmpRoot):
    def test_json_is_one_line_under_1kb_and_matches_plain_line(self):
        self.full_fixture()
        done = run_cli('--root', self.root, '--now', '11:26', '--tests', '24/24', '--json')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(done.stdout.splitlines()), 1)
        self.assertLessEqual(len(done.stdout.encode('utf-8')), 1024, len(done.stdout.encode('utf-8')))
        data = json.loads(done.stdout)
        plain = run_cli('--root', self.root, '--now', '11:26', '--tests', '24/24').stdout.strip()
        self.assertEqual(data['line'], plain)
        self.assertEqual((data['status'], data['start'], data['deadline'], data['cp'], data['now']), ('ACTIVE', '09:00', '13:00', '1', '11:26'))
        self.assertEqual((data['elapsed_min'], data['remaining_min']), (146, 94))
        self.assertEqual(data['tasks'], {'found': True, 'total': 6, 'pass': 3, 'fail': 1, 'not_run': 1, 'human_check': 1,
                                         'skipped': 0})
        self.assertEqual(data['tests'], {'pass': 24, 'total': 24})
        self.assertEqual(data['debug'], {'green': 2, 'total': 3, 'red_open': ['02_규칙_tz']})
        self.assertEqual(data['pending'], {'open': ['D07', 'D08', 'D41'], 'ask': ['D07', 'D41'], 'open_n': 3, 'ask_n': 2})
        self.assertEqual(data['agents'], {'A_core': '판정 04 구현 중', 'B_web': '더미 렌더 완료'})
        self.assertEqual(data['prd'], 'v1')
        for key in ('recommendations', 'phase', 'waiting', 'milestone'):
            self.assertNotIn(key, data)


# ---------------------------------------------------------------- 입력 파싱
class TestInputs(_TmpRoot):
    def test_task_table_counts_and_skips_template_rows(self):
        self.write('PLAN.md', PLAN_TASKS)
        tasks = status.read_tasks(self.root)
        self.assertEqual(tasks, {'found': True, 'total': 6, 'pass': 3, 'fail': 1, 'not_run': 1, 'human_check': 1, 'skipped': 0})

    def test_skipped_rows_are_counted_apart_from_not_run(self):
        """'생략(사유)' 은 전체에 넣고 따로 센다 — 미실행(NOT_RUN)과 구분돼 끝까지 n/n 이 안 차는 이유가 보인다."""
        self.write('PLAN.md', '## 4. task 표\n| # | task | 상태 |\n|---|---|---|\n| 1 | 계약 | PASS |\n'
                              '| 2 | 화면 고도화 | 생략(범위 밖) |\n| 3 | 엣지 | NOT_RUN(생략: 입력 없음) |\n| 4 | 판정 | NOT_RUN |\n')
        tasks = status.read_tasks(self.root)
        self.assertEqual((tasks['total'], tasks['pass'], tasks['skipped'], tasks['not_run']), (4, 1, 2, 1))
        self.assertIn('task 1/4(생략 2) · ', status.build(self.root, now='10:00')['line'])
        self.write('PLAN.md', '## 4. task 표\n| # | task | 상태 |\n|---|---|---|\n| 1 | 계약 | PASS |\n')
        self.assertIn('task 1/1 · ', status.build(self.root, now='10:00')['line'])   # 생략이 없으면 괄호도 없다

    def test_task_table_without_status_column_counts_rows_as_not_run(self):
        self.write('PLAN.md', '## 4. task\n| # | task | 담당 |\n|---|---|---|\n| 1 | 단위 통일 | A |\n')
        tasks = status.read_tasks(self.root)
        self.assertEqual((tasks['found'], tasks['total'], tasks['not_run']), (True, 1, 1))

    def test_missing_task_table_or_task_column_is_reported(self):
        self.write('PLAN.md', '# PLAN\n## 1. 문제 정의\n- 목표:\n')
        self.assertFalse(status.read_tasks(self.root)['found'])
        self.assertIn('task 표 없음', status.build(self.root, now='10:00')['line'])
        self.write('PLAN.md', '## 4. 규칙\n| # | 규칙 | 상태 |\n|---|---|---|\n| 1 | 중복 | PASS |\n')
        self.assertFalse(status.read_tasks(self.root)['found'])

    def test_tests_arg_format(self):
        self.assertEqual(status.read_tests('5/7'), {'pass': 5, 'total': 7})
        self.assertIsNone(status.read_tests(None))
        with self.assertRaises(ValueError):
            status.read_tests('5 of 7')

    def test_debug_signal_counts_folders_not_files(self):
        self.assertEqual(status.read_debug(self.root), {'exists': False, 'green': 0, 'total': 0, 'red_open': []})
        for stage, files in (('01_계약', ('red.txt', 'green.txt', 'verify.json', 'note.md')), ('02_규칙_tz', ('red.txt',)), ('03_x', ())):
            os.makedirs(os.path.join(self.root, 'out', 'debug', stage))
            for f in files:
                self.write(os.path.join('out', 'debug', stage, f), 'x')
        debug = status.read_debug(self.root)
        self.assertEqual((debug['green'], debug['total'], debug['red_open']), (1, 3, ['02_규칙_tz']))

    def test_read_pending_skips_example_and_answered(self):
        self.write(os.path.join('decisions', 'pending.md'), PENDING)
        p = status.read_pending(self.root)
        self.assertEqual(p, {'open': ['D07', 'D08', 'D41'], 'ask': ['D07', 'D41']})
        self.assertEqual(status.read_pending(os.path.join(self.root, 'nowhere')), {'open': [], 'ask': []})

    def test_read_pending_bare_applied_line_is_not_an_answer_and_other_sections(self):
        """고른 후보 줄(`- [x] A.` · `- [x] 반영 HH:MM A.`)만 답이다. 후보 없이 따로 쓴 `[x] 반영 HH:MM` 은 무엇을 골랐는지
        없어 미답으로 남는다(decide.py 폼에도 미답으로 뜬다). 다른 '## ' 절의 체크는 앞 항목에 섞이지 않는다."""
        text = ('# 대기함\n\n## D10 가   (영향: x | 담당자 확인: 필요)\n- [ ] A. 하나 (추천)\n[x] 반영 10:20\n\n'
                '## D11 나   (영향: y | 담당자 확인: 필요)\n- [ ] A. 둘 (추천)\n메모:\n\n'
                '## D12 다   (영향: z | 담당자 확인: 필요)\n- [ ] A. 셋\n- [x] B. 넷 (추천) 반영 10:40\n\n## 참고\n- [x] 다른 절의 체크\n')
        self.write(os.path.join('decisions', 'pending.md'), text)
        self.assertEqual(status.read_pending(self.root), {'open': ['D10', 'D11'], 'ask': ['D10', 'D11']})
        data = status.build(self.root, now='10:00')
        self.assertEqual((data['pending']['open_n'], data['pending']['ask_n']), (2, 2))

    def test_open_ids_match_decide_unanswered(self):
        """status 의 '대기' 와 decide.py 의 미답(폼·--list)이 같은 항목을 가리킨다 — 예시·답한 항목·따로 쓴 반영 줄 모두."""
        import decide  # scripts/ 는 위에서 sys.path 에 넣었다
        texts = [PENDING,
                 '## D10 가   (영향: x | 담당자 확인: 필요)\n- [ ] A. 하나 (추천)\n[x] 반영 10:20\n',
                 '## D20 라   (영향: x | 담당자 확인: 불필요 — 기술 선택)\n- [x] 반영 11:02 A. 하나 (추천)\n- [ ] B. 둘\n',
                 '## D00 (예시, 삭제 가능) 견본   (영향: x | 담당자 확인: 필요)\n- [ ] A. 가 (추천)\n- [ ] B. 나\n']
        with open(os.path.join(ROOT, 'decisions', 'pending.md'), encoding='utf-8') as fh:
            texts.append(fh.read())                       # 키트에 든 실제 파일(내용은 시험 중 바뀌어도 두 판정은 같아야 한다)
        for text in texts:
            self.write(os.path.join('decisions', 'pending.md'), text)
            want = [it['id'] for it in decide.unanswered(decide.parse_pending(text))]
            self.assertEqual(status.read_pending(self.root)['open'], want, text[:60])

    def test_many_open_ids_are_truncated_with_plus_count(self):
        blocks = ''.join('## D%02d 항목   (영향: x | 담당자 확인: 필요)\n- [ ] A. 가 (추천)\n메모:\n\n' % i for i in range(1, 10))
        self.write(os.path.join('decisions', 'pending.md'), blocks)
        line = status.build(self.root, now='10:00')['line']
        self.assertIn('대기 D01·D02·D03·D04·D05·D06+3(담당자 D01·D02·D03+6)', line)

    def test_prd_version_is_read_from_head_and_shown_last(self):
        """PRD.md 머리 5줄의 `버전: `vN`` → 줄 끝 'PRD vN'. 파일이 없으면 'PRD 없음', 버전 줄이 없으면 'PRD 버전 미기록'.
        표시만 한다 — v0 이어도 추천·독촉 문구는 없다."""
        self.assertIsNone(status.read_prd(self.root))
        self.assertTrue(status.build(self.root, now='10:00')['line'].endswith(' · PRD 없음'))
        for head, want in (('버전: `v0` · 승인: __:__ · 갱신: __:__', 'v0'), ('버전: `v1` · 승인: 09:40', 'v1'),
                           ('버전: V1.2 · 승인: 09:40 · 갱신: 11:05', 'v1.2')):
            self.write('PRD.md', '# PRD — 제품 요구 문서\n%s\n<!-- 안내 -->\n' % head)
            self.assertEqual(status.read_prd(self.root), want)
            line = status.build(self.root, now='10:00')['line']
            self.assertTrue(line.endswith(' · PRD ' + want), line)
            for word in FORBIDDEN_IN_LINE:
                self.assertNotIn(word, line, word)
        self.write('PRD.md', '# PRD\n' + '\n' * 8 + '버전: `v1`\n')       # 머리 5줄 밖은 읽지 않는다
        self.assertEqual(status.read_prd(self.root), '')
        self.assertTrue(status.build(self.root, now='10:00')['line'].endswith(' · PRD 버전 미기록'))
        kit_prd = os.path.join(ROOT, 'PRD.md')
        if os.path.exists(kit_prd):                       # 키트 템플릿 2행 형식이 status.py 와 맞물려 있다(값은 시험 중 바뀐다)
            self.assertRegex(status.read_prd(ROOT) or '', r'^v\d')

    def test_agents_read_status_line_and_skip_template(self):
        self.write(os.path.join('work', 'agents', '_template.md'), AGENT_TEMPLATE)
        self.write(os.path.join('work', 'agents', 'C_verify.md'), '# C_verify — 기술검증\n상태: ' + 'ㄱ' * 60 + ' · 갱신 11:00\n')
        self.write(os.path.join('work', 'agents', 'A_core.md'), AGENT_A)
        self.write(os.path.join('work', 'agents', 'B_web.md'), '# B_web — 웹서비스\n(상태 줄 없음)\n')
        agents = status.read_agents(self.root)
        self.assertEqual([a for a, _ in agents], ['A_core', 'C_verify'])
        self.assertEqual(dict(agents)['A_core'], '판정 04 구현 중')
        self.assertEqual(len(dict(agents)['C_verify']), 40)


# ---------------------------------------------------------------- 연결 신호
LINK_PLAN = PLAN_TASKS + """
## 4-2 연결 표
| # | 신호(어느 담당의 task N 끝) | 받는 담당 | 가져오는 것 | 하는 일 | 끝 신호 | 비고 |
|---|---|---|---|---|---|---|
| 1 | A 01 계약 끝 | B · C | work/contract.md | 더미 렌더 | B 05 green | |
| 2 | B 05 시안 보고 | 사람 | static/draft/ | 시안 선택 | 사람 선택 | |

## 6. 끝
"""
AGENT_A_SIG = AGENT_A + '-\n\n## ⑤ 진행 로그\n| 시각 | task | 한 줄 | 근거 |\n|---|---|---|---|\n\n## ⑦ 요청\n- 연결 1: 01 계약 끝 · work/contract.md\n- 연결 2: 05 시안 보고 · static/draft/\n'
AGENT_B_SIG = AGENT_B + '\n## ⑤ 진행 로그\n| 10:10 | 05 | 연결 1 반영 · 더미 렌더 | static/ |\n\n## ⑦ 요청\n- 연결 #: <번호> · <끝난 task>\n'


class TestSignals(_TmpRoot):
    def test_pending_receivers_appear_after_the_decision_slot(self):
        self.full_fixture()
        self.write('PLAN.md', LINK_PLAN)
        self.write(os.path.join('work', 'agents', 'A_core.md'), AGENT_A_SIG)
        self.write(os.path.join('work', 'agents', 'C_verify.md'), '# C_verify — 기술검증\n상태: 대기 · 갱신 10:00\n')
        line = status.build(self.root, now='11:26')['line']
        self.assertIn('대기 D07·D08·D41(담당자 D07·D41) · 연결 대기 1(→B·C) · A_core:', line)
        self.write(os.path.join('work', 'agents', 'B_web.md'), AGENT_B_SIG)
        data = status.build(self.root, now='11:26')
        self.assertIn(' · 연결 대기 1(→C) · ', data['line'])
        self.assertEqual(data['signals'], {'pending': [{'n': '1', 'from': ['A'], 'to': ['C']}], 'pending_n': 1})
        self.write(os.path.join('work', 'agents', 'C_verify.md'), '# C_verify — 기술검증\n상태: 점검 · 갱신 10:20\n\n## ⑤\n연결 1 반영\n')
        data = status.build(self.root, now='11:26')
        self.assertNotIn('연결 대기', data['line'])                 # 받는 담당이 사람뿐인 2번은 세지 않는다
        self.assertEqual(data['signals'], {'pending': [], 'pending_n': 0})

    def test_numbered_requests_in_section_7_are_counted_until_marked(self):
        self.full_fixture()
        self.write('PLAN.md', LINK_PLAN)
        self.write(os.path.join('work', 'agents', 'C_verify.md'), '# C_verify — 기술검증\n상태: 점검 · 갱신 10:20\n\n## ⑦ 요청\n- @A C1: 02 재계산 12 vs 10\n- @B C2: 표 헤더 다름\n- @A: 번호 없음\n- @사람: 없음\n')
        data = status.build(self.root, now='11:26')
        self.assertIn(' · 요청 대기 C1(→A)·C2(→B) · A_core:', data['line'])
        self.assertEqual(data['requests'], {'open': [{'id': 'C1', 'from': 'C', 'to': 'A'}, {'id': 'C2', 'from': 'C', 'to': 'B'}], 'open_n': 2})
        self.write(os.path.join('work', 'agents', 'A_core.md'), AGENT_A + '-\n\n## ⑤ 진행 로그\n| 10:30 | 02 | C1 반영 | core/judge.py |\n')
        self.write(os.path.join('work', 'agents', 'B_web.md'), AGENT_B + '\n## ⑤\n| 10:31 | 05 | C2 반영 | static/ |\n')
        data = status.build(self.root, now='11:26')
        self.assertNotIn('요청 대기', data['line'])
        self.assertEqual(data['requests'], {'open': [], 'open_n': 0})

    def test_no_signal_section_means_no_slot(self):
        self.full_fixture()
        data = status.build(self.root, now='11:26')
        self.assertNotIn('연결', data['line'])
        self.assertNotIn('요청', data['line'])
        self.assertEqual(data['signals']['pending_n'], 0)
        self.assertEqual(data['requests']['open_n'], 0)
        self.assertEqual(status.read_links(self.root), {})
        self.assertEqual(status.read_signals(self.root)['sent'], {})


# ---------------------------------------------------------------- 시각
class TestClock(unittest.TestCase):
    def test_remaining_over_midnight_adds_a_day(self):
        self.assertEqual(status.minutes_until('00:30', status.dt.datetime(2026, 10, 31, 23, 50)), 40)
        self.assertEqual(status.minutes_until('13:00', status.dt.datetime(2026, 10, 31, 11, 26)), 94)
        self.assertEqual(status.minutes_until('13:00', status.dt.datetime(2026, 10, 31, 13, 45)), -45)

    def test_elapsed_over_midnight_adds_a_day(self):
        self.assertEqual(status.minutes_from('23:30', status.dt.datetime(2026, 10, 31, 0, 15)), 45)

    def test_bad_hhmm_is_rejected(self):
        for bad in ('9시', '25:00', '10:60', ''):
            with self.assertRaises(ValueError):
                status.parse_hhmm(bad)


# ---------------------------------------------------------------- CLI
class TestCli(_TmpRoot):
    def test_help_exits_0_and_mentions_no_time_rules(self):
        done = run_cli('--help')
        self.assertEqual(done.returncode, 0)
        self.assertNotIn('추천', done.stdout)

    def test_bad_now_or_tests_format_is_exit_2(self):
        self.assertEqual(run_cli('--root', self.root, '--now', '10시').returncode, 2)
        done = run_cli('--root', self.root, '--tests', '5 of 7')
        self.assertEqual(done.returncode, 2)
        self.assertIn('N/M', done.stderr)

    def test_source_has_no_phase_table_or_recommendation_logic(self):
        with open(os.path.join(SCRIPTS, 'status.py'), encoding='utf-8') as fh:
            src = fh.read()
        for name in ('PHASES', 'WAITING', 'PHASE_TODO', 'MILESTONES', 'recommend(', 'FIRST_FREEZE'):
            self.assertNotIn(name, src, name)
        self.assertFalse(re.search(r'elapsed\s*[<>]=?\s*\d', src), '경과 분으로 분기하는 코드가 있다')
        self.assertFalse(re.search(r'remaining\s*[<>]=?\s*\d+(?!\s*else)', src.replace('remaining >= 0', '')), '남은 분으로 분기하는 코드가 있다')


if __name__ == '__main__':
    unittest.main()
