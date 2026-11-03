# -*- coding: utf-8 -*-
"""scripts/debug_dir.py 디버그 폴더 정책 + preflight 연동 테스트 (unittest, Python 3.9).
실행: python3 -m unittest discover -s scripts/tests -p test_debug_dir.py -v
분류: 생성·멱등 / 이름 형식 거부 / 허용 4종·총량 상한 없음 / 폴더당 5 초과 경고(exit 0, --strict exit 1) / 허용 외 이름 나열
      / --check 금지 패턴 4종 exit 1 / 12폴더×4파일 exit 0 / --decisions → verify.json "decisions" 병합(과제 패키지 core/ 포함)
      / preflight: debug-dir 판정·스캔 제외(.tmp·out/debug, work 는 할 일 표시 스캔만) / --harness-tests 옵트인 / --freeze 번호 증가 / --env."""
import json
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
MARK = debug_dir.DECISION_MARK  # 리터럴 대신 상수를 쓴다(이 파일이 결정 주석으로 잡히지 않게)
FOUR = ('red.txt', 'green.txt', 'verify.json', 'note.md')
TODO_CHECK = 'to' + 'do-scan'  # preflight 가 이 파일을 스캔해도 걸리지 않게 이어 붙인다


def run_py(script, args, cwd):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run([sys.executable, script] + list(args), cwd=cwd, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', env=env, timeout=180)


def touch(path, text='x\n'):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def read_json(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)


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

    def fill_stages(self, n, files=FOUR):
        for i in range(1, n + 1):
            for f in files:
                touch(os.path.join(self.stage('%02d_s' % i), f))


# ---------------------------------------------------------------- 생성
class TestCreate(TmpRootCase):
    def test_policy_constants_are_four_files_and_no_total_cap(self):
        self.assertEqual(debug_dir.ALLOWED, FOUR)
        self.assertEqual(debug_dir.MAX_PER_DIR, 5)
        self.assertFalse(hasattr(debug_dir, 'MAX_' + 'TOTAL'))

    def test_creates_stage_dir_and_second_call_keeps_it(self):
        done = self.cli('01_계약')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(os.path.isdir(self.stage('01_계약')))
        self.assertIn('생성', done.stdout)
        self.assertIn('허용 파일: red.txt green.txt verify.json note.md', done.stdout)
        touch(os.path.join(self.stage('01_계약'), 'red.txt'))
        again = self.cli('01_계약')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('있음', again.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.stage('01_계약'), 'red.txt')))  # 기존 내용은 건드리지 않는다
        self.assertEqual(again.stderr.strip(), '')  # 허용 파일 1개뿐이면 경고 없음

    def test_name_without_nn_prefix_is_rejected(self):
        for bad in ('계약', '1_계약', '01 계약', '../01_x'):
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
        touch(os.path.join(self.stage('03_x'), 'decisions.txt'))  # 옛 5번째 파일도 이제 허용 외
        touch(os.path.join(self.stage('03_x'), 'sub', 'trace.txt'))
        done = self.cli('03_x')
        self.assertEqual(done.returncode, 0)
        self.assertIn('허용 외 파일 2개', done.stderr)
        self.assertIn('decisions.txt', done.stderr)
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
        for s in ('01_계약', '02_규칙_tz'):
            for f in ('red.txt', 'green.txt', 'verify.json'):
                touch(os.path.join(self.stage(s), f))
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('RESULT: exit 0 — 2폴더 6파일', done.stdout)
        self.assertEqual(done.stderr.strip(), '')

    def test_twelve_stages_of_four_files_is_exit0(self):
        self.fill_stages(12)
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('RESULT: exit 0 — 12폴더 48파일, 금지 패턴 없음', done.stdout)
        self.assertNotIn('상한', done.stdout)
        self.assertEqual(done.stderr.strip(), '')

    def test_forbidden_pattern_is_exit1_even_in_a_small_tree(self):
        touch(os.path.join(self.stage('09_동결'), 'green.txt'))
        touch(os.path.join(self.stage('09_동결'), 'out_before.csv'))
        done = self.cli('--check')
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn('금지 패턴 1건', done.stdout)

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
        self.assertIn('.tmp/freeze_N/', done.stdout)

    def test_allowed_name_in_data_dir_is_not_a_copy(self):
        touch(os.path.join(self.tmp, 'data', 'note.md'))
        touch(os.path.join(self.stage('01_a'), 'note.md'))
        self.assertEqual(debug_dir.scan(self.tmp)['forbidden'], [])

    def test_six_files_in_one_folder_is_warning_only_exit0(self):
        self.fill_stages(3)
        for i in range(6):
            touch(os.path.join(self.stage('04_a'), 'f%d.txt' % i))
        done = self.cli('--check')
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn('폴더당 5 초과: 04_a', done.stderr)
        self.assertIn('<- 5 초과(경고)', done.stdout)
        self.assertIn('RESULT: exit 0', done.stdout)
        self.assertEqual(self.cli('--check', '--strict').returncode, 1)


# ---------------------------------------------------------------- --decisions
class TestDecisions(TmpRootCase):
    def test_merges_grep_like_lines_into_verify_json_skipping_harness_tools(self):
        touch(os.path.join(self.tmp, 'src', 'calc.py'), 'x = 1\n# %s 최대 이탈률 / 담당자 요청 / 평균\n' % MARK)
        touch(os.path.join(self.tmp, 'scripts', 'run.py'), 'y = 2  # %s 정렬 id 오름차순 / 결정성 / 없음\n' % MARK)
        touch(os.path.join(self.tmp, 'scripts', 'check_contract.py'), '# %s 재계산 기준 / 독립 검증 / 없음\n' % MARK)
        touch(os.path.join(self.tmp, 'scripts', 'decide.py'), '# %s 하네스 도구 주석\n' % MARK)
        touch(os.path.join(self.tmp, 'scripts', 'tests', 'test_h.py'), '# %s 하네스 테스트 주석\n' % MARK)
        touch(os.path.join(self.tmp, 'tests', 'test_a.py'), '# %s 샘플 3행 / 짧게 / 10행\n' % MARK)
        touch(os.path.join(self.tmp, 'app', 'server.py'), '# %s 포트 8000 / README / 3000\n' % MARK)
        touch(os.path.join(self.tmp, 'main.py'), '# %s 진입점 main / 단순 / 패키지\n' % MARK)
        touch(os.path.join(self.tmp, 'other', 'skip.py'), '# %s 대상 밖\n' % MARK)
        touch(os.path.join(self.tmp, 'src', 'README.md'), '# %s md 는 대상 밖\n' % MARK)
        touch(os.path.join(self.tmp, 'src', '__pycache__', 'calc.py'), '# %s 캐시\n' % MARK)
        done = self.cli('--decisions', '02_규칙_tz')
        self.assertEqual(done.returncode, 0, done.stderr)
        verify = os.path.join(self.stage('02_규칙_tz'), 'verify.json')
        lines = read_json(verify)['decisions']
        self.assertEqual(len(lines), 6, lines)
        self.assertEqual(lines[0], 'src/calc.py:2:# %s 최대 이탈률 / 담당자 요청 / 평균' % MARK)
        self.assertIn('scripts/run.py:1:y = 2  # %s 정렬 id 오름차순 / 결정성 / 없음' % MARK, lines)
        self.assertIn('main.py:1:# %s 진입점 main / 단순 / 패키지' % MARK, lines)
        joined = '\n'.join(lines)
        for absent in ('other/', 'README.md', '__pycache__', 'decide.py', 'test_h.py'):
            self.assertNotIn(absent, joined)
        self.assertIn('scripts/check_contract.py', joined)
        self.assertIn('6줄', done.stdout)
        self.assertFalse(os.path.exists(os.path.join(self.stage('02_규칙_tz'), 'decisions.txt')))

    def test_task_package_core_is_scanned_and_tests_not_doubled(self):
        """scaffold 기본 패키지 core/(와 --package 로 바꾼 이름)의 '결정:' 도 모은다 — __init__.py 가 있는 최상위 폴더만."""
        touch(os.path.join(self.tmp, 'core', '__init__.py'), '')
        touch(os.path.join(self.tmp, 'core', 'rules.py'), 'x = 1\n# %s 경계 포함 / 담당자 답 B2 / 미포함\n' % MARK)
        touch(os.path.join(self.tmp, '판정', '__init__.py'), '')
        touch(os.path.join(self.tmp, '판정', '규칙.py'), '# %s 한글 패키지 / --package / 없음\n' % MARK)
        touch(os.path.join(self.tmp, 'tests', '__init__.py'), '')
        touch(os.path.join(self.tmp, 'tests', 'test_rules.py'), '# %s 테스트 쪽 / 한 번만 / 두 번\n' % MARK)
        touch(os.path.join(self.tmp, 'notpkg', 'x.py'), '# %s 패키지 아님\n' % MARK)
        touch(os.path.join(self.tmp, '.hidden', '__init__.py'), '')
        touch(os.path.join(self.tmp, '.hidden', 'h.py'), '# %s 숨김 폴더\n' % MARK)
        done = self.cli('--decisions', '04_rules')
        self.assertEqual(done.returncode, 0, done.stderr)
        lines = read_json(os.path.join(self.stage('04_rules'), 'verify.json'))['decisions']
        self.assertIn('core/rules.py:2:# %s 경계 포함 / 담당자 답 B2 / 미포함' % MARK, lines)
        self.assertIn('판정/규칙.py:1:# %s 한글 패키지 / --package / 없음' % MARK, lines)
        self.assertEqual(sum(1 for x in lines if x.startswith('tests/test_rules.py:')), 1, lines)   # tests 는 한 번만
        joined = '\n'.join(lines)
        self.assertNotIn('notpkg/', joined)
        self.assertNotIn('.hidden/', joined)
        self.assertEqual(len(lines), 3, lines)
        self.assertIn('core/', done.stdout)                 # 찾은 곳을 안내 줄에 적는다
        self.assertEqual(debug_dir.decision_dirs(self.tmp), ['tests', 'core', '판정'])

    def test_existing_verify_keys_are_kept_and_decisions_replaced(self):
        verify = os.path.join(self.stage('01_계약'), 'verify.json')
        touch(verify, json.dumps({'tests': '24/24', 'decisions': ['옛 줄']}, ensure_ascii=False))
        touch(os.path.join(self.tmp, 'main.py'), '# %s 새 결정\n' % MARK)
        done = self.cli('--decisions', '01_계약')
        self.assertEqual(done.returncode, 0, done.stderr)
        data = read_json(verify)
        self.assertEqual(data['tests'], '24/24')
        self.assertEqual(data['decisions'], ['main.py:1:# %s 새 결정' % MARK])

    def test_no_hits_creates_verify_json_with_empty_list(self):
        done = self.cli('--decisions', '09_동결')
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(read_json(os.path.join(self.stage('09_동결'), 'verify.json')), {'decisions': []})
        self.assertIn('0줄', done.stdout)

    def test_broken_verify_json_is_exit1_and_left_untouched(self):
        verify = os.path.join(self.stage('01_계약'), 'verify.json')
        touch(verify, '{깨진 json\n')
        done = self.cli('--decisions', '01_계약')
        self.assertEqual(done.returncode, 1)
        self.assertIn('덮어쓰지 않음', done.stderr)
        with open(verify, 'r', encoding='utf-8') as fh:
            self.assertEqual(fh.read(), '{깨진 json\n')


# ---------------------------------------------------------------- preflight 연동
class TestPreflightIntegration(TmpRootCase):
    def preflight(self, *args):
        return run_py(PREFLIGHT_PY, args, self.tmp)

    def line(self, done, name):
        for line in done.stdout.splitlines():
            if line.startswith(name + ' '):
                return line
        self.fail('%s 줄 없음:\n%s' % (name, done.stdout))

    def test_no_debug_dir_is_pass(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        done = self.preflight()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('PASS', self.line(done, 'debug-dir'))

    def test_many_stages_pass_and_over_five_is_detail_only(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        self.fill_stages(12)
        for i in range(6):
            touch(os.path.join(self.stage('13_x'), 'f%d.txt' % i))
        done = self.preflight()
        line = self.line(done, 'debug-dir')
        self.assertIn('PASS', line)
        self.assertIn('13폴더 54파일', line)
        self.assertIn('폴더당 5 초과', line)

    def test_forbidden_pattern_warns_and_points_to_check(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        touch(os.path.join(self.stage('01_a'), 'x_protected_before.json'))
        # 스캔 제외 확인: .tmp/ 의 비밀값 모양과 out/debug 의 할 일 마커는 preflight 가 보지 않아야 한다.
        # (이 테스트 파일도 preflight 가 스캔하므로 패턴 문자열은 이어 붙여 만든다.)
        touch(os.path.join(self.tmp, '.tmp', 'leak.py'), 'pass' + 'word = "' + 'hunter2' * 3 + '"\n')
        touch(os.path.join(self.stage('01_a'), 'note.md'), 'TO' + 'DO 나중에\n')
        done = self.preflight()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        line = self.line(done, 'debug-dir')
        self.assertIn('WARN', line)
        self.assertIn('debug_dir.py --check', line)
        self.assertIn('*_protected_before*', line)
        self.assertNotIn('leak.py', done.stdout)
        self.assertNotIn('note.md', done.stdout)

    def test_work_folder_is_out_of_todo_scan_but_in_secret_scan(self):
        touch(os.path.join(self.tmp, 'work', 'agents', 'A_core.md'), '# A_core\n상태: ' + 'TO' + 'DO 다음 task\n')
        touch(os.path.join(self.tmp, 'core.py'), 'x = 1  # ' + 'TO' + 'DO\n')
        touch(os.path.join(self.tmp, 'work', 'leak.md'), 'pass' + 'word = "' + 'hunter2' * 3 + '"\n')
        touch(os.path.join(self.tmp, 'static', 'index.html'), '<input type="search" place' + 'holder="검색">\n')
        done = self.preflight()
        scan_line = self.line(done, TODO_CHECK)
        self.assertIn('core.py', scan_line)
        self.assertNotIn('A_core.md', scan_line)
        self.assertNotIn('index.html', scan_line)  # 입력칸 속성은 미완성 표시가 아니다
        secret = self.line(done, 'secret-scan')
        self.assertIn('FAIL', secret)
        self.assertIn('leak.md', secret)
        self.assertEqual(done.returncode, 1)

    def test_harness_tests_run_only_when_asked(self):
        touch(os.path.join(self.tmp, 'scripts', 'tests', 'test_dummy.py'),
              'import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n')
        default = self.preflight()
        line = self.line(default, 'harness-tests')
        self.assertIn('SKIP', line)
        self.assertIn('--harness-tests', line)
        asked = self.preflight('--harness-tests')
        self.assertIn('PASS', self.line(asked, 'harness-tests'))
        self.assertIn('1 run', self.line(asked, 'harness-tests'))
        self.assertNotIn('skip-harness', default.stdout + asked.stdout)

    def test_freeze_numbers_increase_and_copy_includes_work(self):
        touch(os.path.join(self.tmp, 'README.md'), '# demo\n')
        touch(os.path.join(self.tmp, 'tests', 'test_a.py'), 'import unittest\n')
        touch(os.path.join(self.tmp, 'work', 'agents', 'A_core.md'), '# A_core\n')
        touch(os.path.join(self.tmp, 'data', 'in.csv'), 'a\n1\n')
        touch(os.path.join(self.stage('01_계약'), 'red.txt'))
        first = self.preflight('--freeze')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertIn('.tmp/freeze_1/', first.stdout)
        second = self.preflight('--freeze')
        self.assertIn('.tmp/freeze_2/', second.stdout)
        f1, f2 = (os.path.join(self.tmp, '.tmp', 'freeze_%d' % n) for n in (1, 2))
        self.assertTrue(os.path.isdir(f1))  # 이전 복구본은 지우지 않는다
        self.assertTrue(os.path.exists(os.path.join(f2, 'work', 'agents', 'A_core.md')))
        self.assertTrue(os.path.exists(os.path.join(f2, 'tests.sha256.json')))
        self.assertFalse(os.path.exists(os.path.join(f2, 'data', 'in.csv')))
        self.assertFalse(os.path.exists(os.path.join(f2, 'out', 'debug')))
        self.assertFalse(os.path.exists(os.path.join(f2, '.tmp')))
        for text in (first.stdout, second.stdout):
            self.assertNotIn('1차', text)
            self.assertNotRegex(text, r'\d+분')
        touch(os.path.join(self.tmp, 'tests', 'test_a.py'), 'import unittest  # 바뀜\n')
        check = self.preflight('--check-freeze')
        line = self.line(check, 'freeze-tests')
        self.assertIn('WARN', line)
        self.assertIn('freeze_2', line)

    def test_env_reports_python_tools_and_iso_probes_without_running_tests(self):
        touch(os.path.join(self.tmp, 'tests', 'test_never.py'), 'raise SystemExit("--env 는 테스트를 돌리지 않는다")\n')
        done = self.preflight('--env')
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for name in ('python', 'iso:Z', 'iso:+0900', 'iso:space', 'stdlib', 'optional-packages', 'tools', 'env-vars'):
            self.line(done, name)
        self.assertIn('codex=', self.line(done, 'tools'))
        self.assertIn('값은 출력하지 않음', self.line(done, 'env-vars'))
        self.assertNotIn('\ntests ', done.stdout)


if __name__ == '__main__':
    unittest.main()
