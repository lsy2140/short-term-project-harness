# -*- coding: utf-8 -*-
"""scripts/debug_dir.py 디버그 폴더 정책 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_debug_dir -v
분류: 생성·멱등 / 이름 형식 거부 / 폴더당 5 초과 경고(exit 0, --strict exit 1) / 허용 외 이름 나열
      / --check 금지 패턴 4종 / 총 40 경계(40 → 0, 41 → 1) / --decisions 파일 생성 / preflight debug-dir 연동·스캔 제외."""
import os
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

import debug_dir  # noqa: E402

DEBUG_DIR_PY = os.path.join(SCRIPTS, 'debug_dir.py')
PREFLIGHT_PY = os.path.join(SCRIPTS, 'preflight.py')
MARK = debug_dir.DECISION_MARK  # 이 테스트 파일 자체가 --decisions 에 잡히지 않도록 리터럴 대신 상수를 쓴다


def run_py(script, args, cwd):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run([sys.executable, script] + list(args), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', env=env, timeout=120)


def touch(path, text='x\n'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


class TmpRootCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='dbgdir_')
        self.debug = os.path.join(self.tmp, 'out', 'debug')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def stage(self, name):
        return os.path.join(self.debug, name)

    def cli(self, *args):
        return run_py(DEBUG_DIR_PY, args, self.tmp)


# ---------------------------------------------------------------- 생성
class TestCreate(TmpRootCase):
    def test_creates_stage_dir_and_second_call_keeps_it(self):
        done = self.cli('01_첫완주')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(os.path.isdir(self.stage('01_첫완주')))
        self.assertIn('생성', done.stdout)
        touch(os.path.join(self.stage('01_첫완주'), 'red.txt'))
        again = self.cli('01_첫완주')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('있음', again.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.stage('01_첫완주'), 'red.txt')))  # 기존 내용은 건드리지 않는다
        self.assertEqual(again.stderr.strip(), '')  # 허용 파일 1개뿐이면 경고 없음

    def test_name_without_nn_prefix_is_rejected(self):
        for bad in ('첫완주', '1_첫완주', '01 첫완주', '../01_x'):
            done = self.cli(bad)
            self.assertEqual(done.returncode, 1, bad)
            self.assertIn('NN_단계명', done.stderr)
        self.assertFalse(os.path.exists(self.debug))

    def test_more_than_five_files_warns_but_exit0_and_strict_exit1(self):
        for i in range(6):
            touch(os.path.join(self.stage('02_규칙_tz'), 'dump%d.log' % i))
        done = self.cli('02_규칙_tz')
        self.assertEqual(done.returncode, 0)
        self.assertIn('6개 > 5', done.stderr)
        self.assertIn('.tmp/', done.stderr)
        strict = self.cli('02_규칙_tz', '--strict')
        self.assertEqual(strict.returncode, 1)

    def test_non_allowed_names_are_listed_and_allowed_are_not(self):
        touch(os.path.join(self.stage('03_x'), 'red.txt'))
        touch(os.path.join(self.stage('03_x'), 'dump.log'))
        touch(os.path.join(self.stage('03_x'), 'sub', 'trace.txt'))
        done = self.cli('03_x')
        self.assertEqual(done.returncode, 0)
        self.assertIn('허용 외 파일 2개', done.stderr)
        self.assertIn('dump.log', done.stderr)
        self.assertIn('sub/trace.txt', done.stderr)
        self.assertNotIn('red.txt', done.stderr)
        self.assertIn('파일 3/5', done.stdout)


# ---------------------------------------------------------------- --check
class TestCheck(TmpRootCase):
    def test_no_debug_dir_is_exit0(self):
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('out/debug 없음', done.stdout)

    def test_clean_stages_exit0(self):
        for s in ('01_첫완주', '02_규칙_tz'):
            for f in ('red.txt', 'green.txt', 'verify.json'):
                touch(os.path.join(self.stage(s), f))
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('RESULT: exit 0', done.stdout)
        self.assertIn('총 6파일', done.stdout)
        self.assertEqual(done.stderr.strip(), '')

    def test_each_forbidden_pattern_is_detected(self):
        touch(os.path.join(self.tmp, 'data', 'input.csv'))
        touch(os.path.join(self.stage('01_a'), 'result_before.csv'))
        touch(os.path.join(self.stage('02_b'), 'state_protected_before.json'))
        touch(os.path.join(self.stage('03_c'), 'chrome_profile', 'Default', 'Cookies'))
        touch(os.path.join(self.stage('04_d'), 'input.csv'))
        touch(os.path.join(self.stage('05_e_before'), 'red.txt'))
        info = debug_dir.scan(self.tmp)
        reasons = {reason for _, reason in info['forbidden']}
        self.assertEqual(reasons, {'*_before', '*_protected_before*', 'chrome_profile', 'data/ 입력 복사본'})
        paths = [p for p, _ in info['forbidden']]
        self.assertIn('01_a/result_before.csv', paths)
        self.assertIn('03_c/chrome_profile/', paths)
        self.assertIn('05_e_before/', paths)
        self.assertEqual(info['total'], 5)
        done = self.cli('--check')
        self.assertEqual(done.returncode, 1)
        self.assertIn('금지 패턴 5건', done.stdout)
        self.assertIn('freeze_1', done.stdout)

    def test_allowed_name_in_data_dir_is_not_a_copy(self):
        touch(os.path.join(self.tmp, 'data', 'note.md'))
        touch(os.path.join(self.stage('01_a'), 'note.md'))
        self.assertEqual(debug_dir.scan(self.tmp)['forbidden'], [])

    def test_total_40_is_exit0_and_41_is_exit1(self):
        for i in range(40):
            touch(os.path.join(self.stage('%02d_s' % (i // 5)), 'f%d.txt' % i))
        ok = self.cli('--check')
        self.assertEqual(ok.returncode, 0, ok.stdout)
        self.assertIn('총 40파일', ok.stdout)
        touch(os.path.join(self.stage('09_last'), 'red.txt'))
        over = self.cli('--check')
        self.assertEqual(over.returncode, 1)
        self.assertIn('총 41파일 > 40', over.stdout)

    def test_per_folder_over_five_is_warning_only_unless_strict(self):
        for i in range(6):
            touch(os.path.join(self.stage('01_a'), 'f%d.txt' % i))
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0)
        self.assertIn('폴더당 5 초과: 01_a', done.stderr)
        self.assertIn('<- 5 초과', done.stdout)
        self.assertEqual(self.cli('--check', '--strict').returncode, 1)


# ---------------------------------------------------------------- --decisions
class TestDecisions(TmpRootCase):
    def test_writes_grep_like_lines_from_code_dirs_and_top_level_only(self):
        touch(os.path.join(self.tmp, 'src', 'calc.py'), 'x = 1\n# %s 최대 이탈률 / 담당자 요청 / 평균\n' % MARK)
        touch(os.path.join(self.tmp, 'scripts', 'run.py'), 'y = 2  # %s 정렬 id 오름차순 / 결정성 / 없음\n' % MARK)
        touch(os.path.join(self.tmp, 'tests', 'test_a.py'), '# %s 샘플 3행 / 짧게 / 10행\n' % MARK)
        touch(os.path.join(self.tmp, 'app', 'server.py'), '# %s 포트 8000 / README / 3000\n' % MARK)
        touch(os.path.join(self.tmp, 'main.py'), '# %s 진입점 main / 단순 / 패키지\n' % MARK)
        touch(os.path.join(self.tmp, 'other', 'skip.py'), '# %s 대상 밖\n' % MARK)
        touch(os.path.join(self.tmp, 'src', 'README.md'), '# %s md 는 대상 밖\n' % MARK)
        touch(os.path.join(self.tmp, 'src', '__pycache__', 'calc.py'), '# %s 캐시\n' % MARK)
        done = self.cli('--decisions', '02_규칙_tz')
        self.assertEqual(done.returncode, 0, done.stderr)
        out = os.path.join(self.stage('02_규칙_tz'), 'decisions.txt')
        self.assertTrue(os.path.exists(out))
        with open(out, 'r', encoding='utf-8') as fh:
            lines = fh.read().splitlines()
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], 'src/calc.py:2:# %s 최대 이탈률 / 담당자 요청 / 평균' % MARK)
        self.assertIn('main.py:1:# %s 진입점 main / 단순 / 패키지' % MARK, lines)
        joined = '\n'.join(lines)
        self.assertNotIn('other/', joined)
        self.assertNotIn('README.md', joined)
        self.assertNotIn('__pycache__', joined)
        self.assertIn('5줄', done.stdout)

    def test_no_hits_still_writes_empty_file_and_exit0(self):
        done = self.cli('--decisions', '01_첫완주')
        self.assertEqual(done.returncode, 0, done.stderr)
        out = os.path.join(self.stage('01_첫완주'), 'decisions.txt')
        self.assertEqual(os.path.getsize(out), 0)
        self.assertIn('0줄', done.stdout)


# ---------------------------------------------------------------- preflight 연동
class TestPreflightIntegration(TmpRootCase):
    def preflight_line(self, done, name):
        for line in done.stdout.splitlines():
            if line.startswith(name + ' '):
                return line
        self.fail('%s 줄 없음:\n%s' % (name, done.stdout))

    def test_no_debug_dir_is_pass(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        done = run_py(PREFLIGHT_PY, [], self.tmp)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('PASS', self.preflight_line(done, 'debug-dir'))

    def test_forbidden_pattern_warns_and_points_to_check(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        touch(os.path.join(self.stage('01_a'), 'x_protected_before.json'))
        # 스캔 제외 확인: .tmp/ 의 비밀값 모양과 out/debug 의 할 일 마커는 preflight 가 보지 않아야 한다.
        # (이 테스트 파일도 preflight 가 스캔하므로 패턴 문자열은 이어 붙여 만든다.)
        touch(os.path.join(self.tmp, '.tmp', 'leak.py'), 'pass' + 'word = "' + 'hunter2' * 3 + '"\n')
        touch(os.path.join(self.stage('01_a'), 'note.md'), 'TO' + 'DO 나중에\n')
        done = run_py(PREFLIGHT_PY, [], self.tmp)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        line = self.preflight_line(done, 'debug-dir')
        self.assertIn('WARN', line)
        self.assertIn('debug_dir.py --check', line)
        self.assertIn('*_protected_before*', line)
        # 스캔에 걸렸다면 WARN/FAIL 상세에 파일 이름이 찍힌다. 두 이름이 없으면 .tmp/ 와 out/debug 를 건너뛴 것이다.
        self.assertNotIn('leak.py', done.stdout)
        self.assertNotIn('note.md', done.stdout)


if __name__ == '__main__':
    unittest.main()
