# -*- coding: utf-8 -*-
"""scripts/next.py 계약 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_next -v
분류: 구간 경계 == timer.PHASES / 대기 중 문구 == RUN.md 구간표 마지막 열 / 시작 없음 안내 /
80분·100~120분·144분 추천 규칙 / 기록 경과·NOT_RUN 규칙 이름 / 규칙표 파싱 / --json / timer --once."""
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
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, 'scripts')
# 'scripts' 라는 이름은 다른 설치 패키지와 겹칠 수 있어 폴더를 직접 경로에 넣고 모듈 이름으로 가져온다.
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import timer  # noqa: E402
import next as nextmod  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING='utf-8')
PLAN_WITH_STATUS = """# PLAN

## 3. 접근
1. 데이터 파악

## 4. 규칙·로직 (규칙 1개 = 테스트 1개)
| # | 규칙 | 출처 | 경계 처리 | 테스트 | 발동 건수 | 상태 |
|---|---|---|---|---|---|---|
| 1 | 중복 제거 | README | 같은 ID 2건 | `test_dup_removed` | 11 | PASS |
| 2 | tz 보정 | 담당자 답변 2 | +0900 콜론 없음 | `test_tz_fix` |  | NOT_RUN |
| 3 | 결측 제외 | README | value 없음 | `test_missing_excluded` | 3 | FAIL |
| 4 |  |  |  | `test_` |  |  |

## 5. 검증 결과 (숫자만)
| 검증 | 명령 | 결과(숫자) | 증거 좌표 |
|---|---|---|---|
| 테스트 | `python3 -m unittest -v` | __ PASS / __ FAIL |  |
"""


def run_cli(*args):
    cmd = [sys.executable, os.path.join(SCRIPTS, 'next.py')] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, timeout=30)


def run_md_waiting_column():
    """RUN.md 구간표(헤더에 '대기 중 사람이 할 일')의 첫 열 → 마지막 열."""
    with open(os.path.join(ROOT, 'RUN.md'), encoding='utf-8') as fh:
        lines = fh.read().splitlines()
    rows, in_table = {}, False
    for line in lines:
        if line.startswith('|') and '대기 중 사람이 할 일' in line:
            in_table = True
            continue
        if in_table and not line.startswith('|'):
            break
        if in_table:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if cells and not re.match(r'^:?-+:?$', cells[0]):
                rows[cells[0]] = cells[-1]
    return rows


class _TmpRoot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='next_test_')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, name, text):
        with open(os.path.join(self.root, name), 'w', encoding='utf-8') as fh:
            fh.write(text)


# ---------------------------------------------------------------- 구간 경계 == timer.PHASES
class TestPhasesMatchTimer(unittest.TestCase):
    def test_next_uses_the_same_phase_table_object_as_timer(self):
        self.assertIs(nextmod.PHASES, timer.PHASES)
        self.assertEqual([(a, b) for a, b, _ in nextmod.PHASES],
                         [(0, 10), (10, 30), (30, 63), (63, 110), (110, 120), (120, 130), (130, 144), (144, 165), (165, 170), (170, 999)])

    def test_every_phase_has_waiting_text_and_default_todo(self):
        for a, b, _ in timer.PHASES:
            key = nextmod.phase_key(a, b)
            self.assertIn(key, nextmod.WAITING, key)
            self.assertIn(key, nextmod.PHASE_TODO, key)
            self.assertEqual(len(nextmod.PHASE_TODO[key]), 3, key)

    def test_phase_boundaries_agree_with_timer_phase_of(self):
        for elapsed in (0, 9, 10, 62, 63, 109, 110, 119, 120, 143, 144, 164, 165, 169, 170, 200):
            key, name, _, _ = nextmod.current_phase(elapsed)
            self.assertEqual(name, timer.phase_of(elapsed)[0], elapsed)
            a, b = (int(x) for x in key.split('–')) if '–' in key else (int(key), 999)
            self.assertTrue(a <= elapsed < b, '%d분 → %s' % (elapsed, key))


# ---------------------------------------------------------------- 대기 중 문구 == RUN.md 구간표 마지막 열
class TestWaitingMatchesRunMd(unittest.TestCase):
    def test_run_md_table_was_found(self):
        rows = run_md_waiting_column()
        self.assertGreaterEqual(len(rows), 10)
        for key in ('30–63', '63–110', '144–165'):
            self.assertIn(key, rows)

    def test_waiting_text_is_identical_to_run_md_last_column(self):
        rows = run_md_waiting_column()
        compared = 0
        for key, text in nextmod.WAITING.items():
            self.assertIn(key, rows, 'RUN.md 구간표에 %r 행이 없음' % key)
            self.assertEqual(text, rows[key], 'RUN.md 와 next.py 의 대기 중 문구가 다름: %s' % key)
            compared += 1
        self.assertGreaterEqual(compared, 3)

    def test_three_named_rows_match_literally(self):
        rows = run_md_waiting_column()
        self.assertEqual(nextmod.WAITING['63–110'], rows['63–110'])
        self.assertEqual(nextmod.WAITING['30–63'], rows['30–63'])
        self.assertEqual(nextmod.WAITING['144–165'], rows['144–165'])
        self.assertIn('DECISIONS 4번', rows['63–110'])


# ---------------------------------------------------------------- 시작 시각
class TestStart(_TmpRoot):
    def test_no_start_gives_guidance_and_exit_0(self):
        data = nextmod.build(self.root, use_records=False)
        self.assertIsNone(data['start'])
        self.assertIn('시작 시각 없음', data['lines'][0])
        self.assertIn("TASK.md 머리에 '시작: HH:MM'", data['lines'][0])
        done = run_cli('--root', self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('시작 시각 없음', done.stdout)

    def test_start_is_read_from_task_md_head(self):
        self.write('TASK.md', '# TASK\n\n시작: 09:05\n\nStatus: `ACTIVE`\n')
        self.assertEqual(nextmod.read_start(self.root), '09:05')
        data = nextmod.build(self.root, now='10:19', use_records=False)
        self.assertEqual(data['elapsed_min'], 74)

    def test_start_beyond_line_20_is_ignored(self):
        self.write('TASK.md', '# TASK\n' + '\n' * 25 + '시작: 09:00\n')
        self.assertIsNone(nextmod.read_start(self.root))

    def test_bad_start_format_is_rejected_with_exit_2(self):
        done = run_cli('--root', self.root, '--start', '9시')
        self.assertEqual(done.returncode, 2)
        self.assertIn('HH:MM', done.stderr)

    def test_start_over_midnight_adds_a_day(self):
        self.assertEqual(nextmod.elapsed_minutes('23:30', nextmod.dt.datetime(2026, 10, 31, 0, 15)), 45)


# ---------------------------------------------------------------- 추천 규칙
class TestRecommendations(_TmpRoot):
    def lines_at(self, now):
        return nextmod.build(self.root, start='09:00', now=now, use_records=False)

    def test_74_min_has_no_new_approach_warning_and_counts_down_to_first_freeze(self):
        data = self.lines_at('10:14')
        self.assertEqual(data['elapsed_min'], 74)
        self.assertNotIn('새 접근', data['lines'][1])
        self.assertIn('1차 동결까지 36분', data['lines'][0])
        self.assertTrue(data['lines'][0].startswith('지금: ⑤ '))

    def test_85_min_includes_no_new_approach(self):
        data = self.lines_at('10:25')
        self.assertEqual(data['elapsed_min'], 85)
        self.assertIn('새 접근 금지', data['lines'][1])
        self.assertTrue(data['no_new_approach'])

    def test_112_min_first_recommendation_is_first_freeze(self):
        data = self.lines_at('10:52')
        self.assertEqual(data['elapsed_min'], 112)
        self.assertIn('동결', data['recommendations'][0])
        self.assertIn('(1) 1차 동결', data['lines'][1])
        self.assertEqual(data['lines'][2], '대기 중 할 일(사람): ' + nextmod.WAITING['110–120'])

    def test_105_min_already_puts_first_freeze_first(self):
        data = self.lines_at('10:45')
        self.assertTrue(data['recommendations'][0].startswith('1차 동결'))

    def test_150_min_first_recommendation_is_stop_features_and_docs(self):
        data = self.lines_at('11:30')
        self.assertTrue(data['recommendations'][0].startswith('기능 추가 중단'))
        self.assertIn('문서', data['recommendations'][0])
        self.assertIn('새 접근 금지', data['lines'][1])

    def test_record_older_than_20_min_recommends_record(self):
        rules = nextmod.read_rules(self.root)
        tests = nextmod.read_tests(self.root)
        with_old = nextmod.recommend(70, '63–110', rules, tests, record_age=21)
        self.assertTrue(any('기록' in r and '21분 전' in r for r in with_old))
        fresh = nextmod.recommend(70, '63–110', rules, tests, record_age=20)
        self.assertFalse(any('21분 전' in r or '20분 전' in r for r in fresh))

    def test_not_run_rule_is_recommended_by_name(self):
        self.write('PLAN.md', PLAN_WITH_STATUS)
        data = self.lines_at('10:14')
        self.assertIn('tz 보정', data['lines'][1])
        self.assertIn('결측 제외', data['lines'][1])  # FAIL 규칙도 이름으로
        self.assertEqual(data['rules']['not_run_names'], ['tz 보정'])

    def test_always_exactly_three_recommendations(self):
        for now in ('09:05', '09:20', '09:45', '10:14', '10:52', '11:05', '11:20', '11:30', '11:47', '12:30'):
            data = self.lines_at(now)
            self.assertEqual(len(data['recommendations']), 3, now)
            self.assertRegex(data['lines'][1], r'^다음 추천: \(1\) .+ \(2\) .+ \(3\) .+')
            self.assertTrue(data['lines'][2].startswith('대기 중 할 일(사람): '), now)


# ---------------------------------------------------------------- 규칙표·테스트 신호 파싱
class TestInputs(_TmpRoot):
    def test_rule_table_counts_pass_fail_not_run_and_skips_empty_rows(self):
        self.write('PLAN.md', PLAN_WITH_STATUS)
        rules = nextmod.read_rules(self.root)
        self.assertTrue(rules['found'])
        self.assertEqual((rules['total'], rules['pass'], rules['fail'], rules['not_run']), (3, 1, 1, 1))
        data = nextmod.build(self.root, start='09:00', now='10:14', use_records=False)
        self.assertIn('규칙 1/3', data['lines'][0])

    def test_rule_table_without_status_column_treats_rows_as_not_run(self):
        self.write('PLAN.md', '## 4. 규칙\n| # | 규칙 | 테스트 |\n|---|---|---|\n| 1 | 단위 통일 | `test_unit` |\n')
        rules = nextmod.read_rules(self.root)
        self.assertEqual((rules['total'], rules['not_run']), (1, 1))

    def test_missing_rule_table_is_reported(self):
        self.write('PLAN.md', '# PLAN\n## 1. 문제 정의\n- 목표:\n')
        self.assertFalse(nextmod.read_rules(self.root)['found'])
        data = nextmod.build(self.root, start='09:00', now='10:14', use_records=False)
        self.assertIn('규칙표 없음', data['lines'][0])

    def test_tests_arg_and_debug_signal(self):
        self.assertEqual(nextmod.read_tests(self.root, '5/7')['label'], '테스트 5/7')
        with self.assertRaises(ValueError):
            nextmod.read_tests(self.root, '5 of 7')
        for stage, files in (('01_첫완주', ('red.txt', 'green.txt')), ('02_규칙_tz', ('red.txt',))):
            os.makedirs(os.path.join(self.root, 'out', 'debug', stage))
            for f in files:
                self.write(os.path.join('out', 'debug', stage, f), 'x')
        tests = nextmod.read_tests(self.root)
        self.assertEqual((tests['pass'], tests['total'], tests['red_open']), (1, 2, ['02_규칙_tz']))
        data = nextmod.build(self.root, start='09:00', now='10:14', use_records=False)
        self.assertIn('02_규칙_tz', data['lines'][1])

    def test_no_records_shows_none(self):
        data = nextmod.build(self.root, start='09:00', now='10:14', use_records=False)
        self.assertIsNone(data['last_record_min'])
        self.assertIn('기록 없음', data['lines'][0])


# ---------------------------------------------------------------- --json 과 timer --once
class TestCli(_TmpRoot):
    def test_json_output_parses_and_matches_lines(self):
        self.write('TASK.md', '# TASK\n시작: 09:00\n')
        done = run_cli('--root', self.root, '--now', '10:25', '--json')
        self.assertEqual(done.returncode, 0, done.stderr)
        data = json.loads(done.stdout)
        self.assertEqual(data['elapsed_min'], 85)
        self.assertEqual(len(data['lines']), 3)
        self.assertEqual(len(data['recommendations']), 3)
        self.assertEqual(data['phase']['key'], '63–110')
        self.assertEqual(data['waiting'], nextmod.WAITING['63–110'])
        self.assertIn('새 접근 금지', data['lines'][1])

    def test_plain_output_is_three_lines(self):
        done = run_cli('--root', self.root, '--start', '09:00', '--now', '10:14')
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout.strip().splitlines()
        self.assertEqual(len(out), 3)
        self.assertTrue(out[0].startswith('지금: ') and out[1].startswith('다음 추천: ') and out[2].startswith('대기 중 할 일(사람): '))

    def test_help_exits_0(self):
        self.assertEqual(run_cli('--help').returncode, 0)

    def test_timer_once_prints_once_and_appends_next_lines(self):
        cmd = [sys.executable, os.path.join(SCRIPTS, 'timer.py'), '--start', '09:00', '--once', '--loop', '300']
        done = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.count('구간 끝 3질문'), 1)
        self.assertIn('지금: ', done.stdout)
        self.assertIn('다음 추천: ', done.stdout)
        self.assertIn('대기 중 할 일(사람): ', done.stdout)


if __name__ == '__main__':
    unittest.main()
