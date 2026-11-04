# -*- coding: utf-8 -*-
"""scripts/wait_signal.py 계약 테스트 (unittest, Python 3.9). 실행: python3 -m unittest discover -s scripts/tests -p test_wait_signal.py -v
분류: --once(받을 신호 있음 exit 0 / 없음 exit 3) / 받은 표시 `연결 N 반영` 뒤에는 안 깨움 / 보낸 쪽은 자기 신호에 안 깨움 /
      PLAN 행 없는 번호는 모두에게 / --decision 답(answers.md·pending [x]) / FROZEN exit 4 / 기다리는 중 신호가 오면 깨움 /
      시간 안에 없으면 exit 3 / CLI 인자 오류 exit 2 / 출력에 추천·독촉 없음."""
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(ROOT, 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import status  # noqa: E402
import wait_signal  # noqa: E402

ENV = dict(os.environ, PYTHONIOENCODING='utf-8')

PLAN = """# PLAN

## 4. task 표
| # | task | 담당 | 검증 | 입력 | 산출 파일 | 완료 조건 | 의존 | 분 | 상태 |
|---|---|---|---|---|---|---|---|---|---|
| 01 | 계약 | A | C | README | work/contract.md | `test_contract` | - | 10 | PASS |

## 4-2 연결 표
| # | 신호(어느 담당의 task N 끝) | 받는 담당 | 가져오는 것(파일·계약·숫자) | 하는 일 | 끝 신호 | 비고 |
|---|---|---|---|---|---|---|
| 1 | A 01 계약 끝 | B · C | `work/contract.md` 열·샘플 2행 | 더미 렌더 | B 05 green | |
| 2 | B 05 시안 보고 | 사람 | static/draft/ | 시안 선택 | 사람 선택 | |
| 3 | B 05 초안 끝 | C | 포트 | 점검 | C 08 green | |

## 5. 검증 결과
"""
A_CORE = ('# A_core — 핵심기술\n상태: 01 끝 · 갱신 10:00\n\n## ① 역할\n-\n\n## ⑤ 진행 로그\n| 시각 | task | 한 줄 | 근거 |\n|---|---|---|---|\n'
          '| 10:00 | 01 | 연결 0 반영 · 계약 고정 | work/contract.md |\n\n## ⑥ 막힌 것\n-\n\n## ⑦ 요청\n'
          '- 연결 1: 01 계약 끝 · work/contract.md 열 9개·샘플 2행\n- @사람: 없음\n')
B_WEB = '# B_web — 웹서비스\n상태: 대기 · 갱신 09:50\n\n## ⑤ 진행 로그\n| 시각 | task | 한 줄 | 근거 |\n|---|---|---|---|\n\n## ⑦ 요청\n- 연결 #: <번호> · <끝난 task>\n'
C_VERIFY = '# C_verify — 기술검증\n상태: 대기 · 갱신 09:50\n\n## ⑦ 요청\n-\n'
TASK_ACTIVE = '# TASK\nStatus: `ACTIVE` · 시작: 09:00 · 마감: 12:00 · 갱신: 10:00 · CP: CP0\n'
TASK_FROZEN = '# TASK\nStatus: `FROZEN` · 시작: 09:00 · 마감: 12:00 · 갱신: 11:50 · CP: CP3\n'
PENDING = ('# 결정 대기함\n\n## D03 반올림   (영향: 출력 | 담당자 확인: 불필요)\n- [ ] A. 둘째 자리 (추천)\n- [ ] B. 정수\n메모:\n\n'
           '## D04 단위   (영향: 출력 | 담당자 확인: 필요)\n- [x] A. 개수 (추천) 반영 10:30\n- [ ] B. box\n메모:\n')
FORBIDDEN = ('추천', '독촉', '해야', '하세요', '지금 바로')


def run_cli(*args, timeout=60):
    cmd = [sys.executable, os.path.join(SCRIPTS, 'wait_signal.py')] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=ENV, timeout=timeout)


class _Root(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix='wait_signal_test_')
        self.write('TASK.md', TASK_ACTIVE)
        self.write('PLAN.md', PLAN)
        self.write(os.path.join('work', 'agents', 'A_core.md'), A_CORE)
        self.write(os.path.join('work', 'agents', 'B_web.md'), B_WEB)
        self.write(os.path.join('work', 'agents', 'C_verify.md'), C_VERIFY)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path) or self.root, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)


class TestOnce(_Root):
    def test_receiver_sees_the_signal_and_its_plan_row(self):
        done = run_cli('--me', 'B', '--once', '--root', self.root)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.count('\n'), 1, done.stdout)
        self.assertIn('연결 1 · 보낸 A · PLAN 4-2: A 01 계약 끝 | B · C', done.stdout)
        for word in FORBIDDEN:
            self.assertNotIn(word, done.stdout)
        self.assertEqual(run_cli('--me', 'C', '--once', '--root', self.root).returncode, 0)

    def test_sender_is_not_woken_by_its_own_signal(self):
        done = run_cli('--me', 'A', '--once', '--root', self.root)
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertIn('신호 없음', done.stdout)

    def test_applied_mark_consumes_the_signal_only_for_that_receiver(self):
        self.write(os.path.join('work', 'agents', 'B_web.md'), B_WEB.replace('|---|---|---|---|\n', '|---|---|---|---|\n| 10:10 | 05 | 연결 1 반영 · 더미 렌더 | static/ |\n'))
        self.assertEqual(run_cli('--me', 'B', '--once', '--root', self.root).returncode, 3)
        self.assertEqual(run_cli('--me', 'C', '--once', '--root', self.root).returncode, 0)
        self.assertEqual(status.read_signals(self.root)['pending'], [{'n': '1', 'from': ['A'], 'to': ['C'], 'row': 'A 01 계약 끝 | B · C | `work/contract.md` 열·샘플 2행 | 더미 렌더 | B 05 green | '}])

    def test_template_placeholder_and_human_only_rows_are_not_signals(self):
        # B 의 ⑦ 에는 숫자 없는 템플릿 줄만 있다 → 신호 아님. PLAN 2행(받는 담당 사람)은 대기로 세지 않는다
        self.write(os.path.join('work', 'agents', 'B_web.md'), B_WEB + '- 연결 2: 05 시안 보고 · static/draft/\n')
        sig = status.read_signals(self.root)
        self.assertEqual(sig['sent'], {'1': ['A'], '2': ['B']})
        self.assertEqual([p['n'] for p in sig['pending']], ['1'])

    def test_signal_without_plan_row_goes_to_everyone_else(self):
        self.write(os.path.join('work', 'agents', 'C_verify.md'), C_VERIFY + '- 연결 9: 08 점검 끝 · stages.md\n')
        self.assertIn('연결 9 · 보낸 C · PLAN 4-2: 행 없음', run_cli('--me', 'B', '--once', '--root', self.root).stdout)
        self.assertIn('1(→B·C)·9(→?)', status.build(self.root, now='10:30')['line'])

    def test_decision_answer_wakes_from_answers_md_or_pending_check(self):
        self.write(os.path.join('decisions', 'pending.md'), PENDING)
        self.assertEqual(run_cli('--me', 'A', '--once', '--decision', 'D03', '--root', self.root).returncode, 3)
        done = run_cli('--me', 'A', '--once', '--decision', 'D03', 'D04', '--root', self.root)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn('D04 답: pending.md 에 고른 후보 [x] 있음', done.stdout)
        self.write(os.path.join('decisions', 'answers.md'), '형식: ...\nD03: B (메모: 정수) @10:40\n')
        done = run_cli('--me', 'A', '--once', '--decision', 'D03', '--root', self.root)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn('D03 답: D03: B (메모: 정수) @10:40', done.stdout)

    def test_numbered_request_wakes_the_addressee_until_it_is_marked(self):
        self.write(os.path.join('work', 'agents', 'C_verify.md'), C_VERIFY + '- @A C1: 02 판정 재계산 12건 vs out 10건 (입력 X 에서 갈림)\n- @B: 번호 없는 줄\n- @사람: 없음\n')
        done = run_cli('--me', 'A', '--once', '--root', self.root)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(done.stdout.strip(), '요청 C1 · 보낸 C · @A: 02 판정 재계산 12건 vs out 10건 (입력 X 에서 갈림)')
        self.assertEqual(run_cli('--me', 'B', '--once', '--root', self.root).returncode, 0)   # B 는 연결 1 때문에 깨고
        self.assertNotIn('요청', run_cli('--me', 'B', '--once', '--root', self.root).stdout)  # 번호 없는 @B 줄은 요청이 아니다
        self.assertIn(' · 요청 대기 C1(→A) · ', status.build(self.root, now='10:30')['line'])
        self.write(os.path.join('work', 'agents', 'A_core.md'), A_CORE.replace('| 10:00 | 01 |', '| 10:20 | 02 | C1 반영 · 갈림 입력 거부 | core/judge.py:40 |\n| 10:00 | 01 |'))
        self.assertEqual(run_cli('--me', 'A', '--once', '--root', self.root).returncode, 3)
        self.assertNotIn('요청 대기', status.build(self.root, now='10:30')['line'])

    def test_request_closed_by_sender_resolution_mark(self):
        self.write(os.path.join('work', 'agents', 'C_verify.md'), C_VERIFY + '- @A C1: 헤더 열 이름 다름 — C1 해결 10:40\n')
        self.assertEqual(status.read_signals(self.root)['requests'], [])
        self.assertEqual(run_cli('--me', 'A', '--once', '--root', self.root).returncode, 3)

    def test_frozen_exits_4_without_waiting(self):
        self.write('TASK.md', TASK_FROZEN)
        done = run_cli('--me', 'B', '--root', self.root, '--interval', '1', '--minutes', '1')
        self.assertEqual(done.returncode, 4, done.stdout)
        self.assertIn('FROZEN', done.stdout)


class TestWaiting(_Root):
    def test_wakes_when_the_signal_arrives_during_the_wait(self):
        self.write(os.path.join('work', 'agents', 'A_core.md'), A_CORE.replace('- 연결 1: 01 계약 끝 · work/contract.md 열 9개·샘플 2행\n', ''))
        self.assertEqual(run_cli('--me', 'B', '--once', '--root', self.root).returncode, 3)

        def later():
            time.sleep(1.5)
            self.write(os.path.join('work', 'agents', 'A_core.md'), A_CORE)
        t = threading.Thread(target=later)
        t.start()
        t0 = time.monotonic()
        done = run_cli('--me', 'B', '--root', self.root, '--interval', '0.5', '--minutes', '0.5')
        t.join()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertLess(time.monotonic() - t0, 25)
        self.assertIn('기다림 시작', done.stdout.splitlines()[0])
        self.assertIn('연결 1 · 보낸 A', done.stdout)

    def test_times_out_with_exit_3(self):
        self.write(os.path.join('work', 'agents', 'A_core.md'), A_CORE.replace('- 연결 1: 01 계약 끝 · work/contract.md 열 9개·샘플 2행\n', ''))
        done = run_cli('--me', 'B', '--root', self.root, '--interval', '0.2', '--minutes', '0.02')
        self.assertEqual(done.returncode, 3, done.stdout)
        self.assertIn('신호 없음 (0.02분)', done.stdout)

    def test_direct_check_function(self):
        self.assertEqual(wait_signal.check(self.root, 'B', []), ['연결 1 · 보낸 A · PLAN 4-2: A 01 계약 끝 | B · C | `work/contract.md` 열·샘플 2행 | 더미 렌더 | B 05 green | '])
        self.assertEqual(wait_signal.check(self.root, 'A', []), [])


class TestCli(unittest.TestCase):
    def test_bad_me_or_interval_is_exit_2(self):
        self.assertEqual(run_cli('--me', 'X', '--once').returncode, 2)
        self.assertEqual(run_cli('--me', 'B', '--once', '--interval', '0').returncode, 2)

    def test_help_mentions_no_recommendation(self):
        done = run_cli('--help')
        self.assertEqual(done.returncode, 0)
        for word in FORBIDDEN:
            self.assertNotIn(word, done.stdout)


if __name__ == '__main__':
    unittest.main()
