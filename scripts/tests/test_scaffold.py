# -*- coding: utf-8 -*-
"""scripts/scaffold.py 테스트 (unittest, Python 3.9). 실행: python3 -m unittest discover -s scripts/tests -p test_scaffold.py -v
고정하는 것: 뼈대 파일 목록 · 만든 직후 `python3 run.py` 가 data/*.csv → out/ 을 씀 · 단계 모듈이 pipeline 순서에 들어감 ·
있는 파일은 덮어쓰지 않음 · 만든 코드는 docmap --check 통과 · 잘못된 이름은 exit 1 · --dry-run 은 쓰지 않음 ·
단계 이름은 공백·쉼표 둘 다, 한글 모듈 이름도 됨 · run.py 는 환경변수 INPUT_DIR 을 기본 입력 폴더로 읽음 ·
check_contract.py 와의 규약: M층이 변형 입력을 실제로 읽음 / INPUT_DIR 을 안 읽는 run.py 는 FAIL M-noop / 코드가 없으면 exit 2."""
import io
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
ENV = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
ENV.pop('INPUT_DIR', None)   # 바깥 셸의 INPUT_DIR 이 run.py 기본 입력 폴더를 바꾸지 않게

# check_contract.py 의 '과제마다 바꾸는 부분'을 테스트 과제에 맞게 덮어쓴 뒤 main() 을 부르는 입구(임시 폴더에 쓴다)
CC_RUNNER = '''import sys
sys.path.insert(0, %r)
import check_contract as cc
cc.INPUTS = ['data/sensor.csv']
cc.OUTPUT = 'out/result.csv'
cc.RUN_CMD = [sys.executable, 'run.py']
cc.REQUIRED_COLUMNS = ['id', 'value']
cc.KEY_COLUMNS = ['id']
cc.SORT_KEYS = []
cc.ALLOWED = {}
cc.RULES = []
cc.METAMORPHIC = {'shuffle_rows': True, 'drop_future_rows': None, 'disable_model': None}
sys.argv = ['check_contract.py']
cc.main()
''' % SCRIPTS


def run(args, cwd, timeout=60, env=None):
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, encoding='utf-8',
                       errors='replace', env=env or ENV, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


class TestScaffold(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='scaffold_')
        os.makedirs(os.path.join(self.tmp, 'data'))
        with io.open(os.path.join(self.tmp, 'data', 'sensor.csv'), 'w', encoding='utf-8') as fh:
            fh.write('id,value\nA,1\nB,2\n')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scaffold(self, *args):
        return run([os.path.join(SCRIPTS, 'scaffold.py'), '--root', self.tmp] + list(args), cwd=self.tmp)

    def test_creates_thin_entry_and_stage_modules(self):
        code, out = self.scaffold('--stages', 'clean,rules')
        self.assertEqual(code, 0, out)
        for rel in ('run.py', 'core/__init__.py', 'core/config.py', 'core/load.py', 'core/pipeline.py',
                    'core/report.py', 'core/clean.py', 'core/rules.py'):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, rel)), rel)
        with io.open(os.path.join(self.tmp, 'core', 'pipeline.py'), encoding='utf-8') as fh:
            self.assertIn("STAGES = [('clean', clean.apply), ('rules', rules.apply)]", fh.read())

    def test_generated_run_py_works_end_to_end(self):
        self.scaffold('--stages', 'clean')
        code, out = run(['run.py'], cwd=self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn('status=ok items=2', out)
        with io.open(os.path.join(self.tmp, 'out', 'result.csv'), encoding='utf-8') as fh:
            self.assertEqual(fh.read().splitlines(), ['id,value', 'A,1', 'B,2'])
        with io.open(os.path.join(self.tmp, 'out', 'summary.json'), encoding='utf-8') as fh:
            meta = json.load(fh)
        self.assertEqual(meta['stage_counts'], {'clean': 2})
        self.assertEqual(meta['input_counts'], {'sensor': 2})

    def test_missing_input_dir_exits_1_with_next_action(self):
        self.scaffold()
        code, out = run(['run.py', '--input-dir', 'nope'], cwd=self.tmp)
        self.assertEqual(code, 1)
        self.assertIn('입력 폴더 없음', out)
        self.assertIn('--input-dir', out)

    def test_existing_files_are_not_overwritten(self):
        with io.open(os.path.join(self.tmp, 'run.py'), 'w', encoding='utf-8') as fh:
            fh.write('# mine\n')
        code, out = self.scaffold()
        self.assertEqual(code, 0, out)
        self.assertIn('이미 있어 건너뜀 1개: run.py', out)
        with io.open(os.path.join(self.tmp, 'run.py'), encoding='utf-8') as fh:
            self.assertEqual(fh.read(), '# mine\n')
        code, out = self.scaffold('--stages', 'extra')
        self.assertIn('STAGES 에 새 단계를 직접 더하세요', out)

    def test_generated_code_passes_docmap_check(self):
        self.scaffold('--stages', 'clean,rules')
        code, out = run([os.path.join(SCRIPTS, 'docmap.py'), '--root', self.tmp, '--check'], cwd=self.tmp)
        self.assertEqual(code, 0, out)

    def test_bad_names_exit_1_and_dry_run_writes_nothing(self):
        self.assertEqual(self.scaffold('--package', 'Core')[0], 1)
        self.assertEqual(self.scaffold('--stages', 'load')[0], 1)      # 예약어
        self.assertEqual(self.scaffold('--stages', 'a,a')[0], 1)       # 중복
        code, out = self.scaffold('--dry-run', '--stages', 'clean')
        self.assertEqual(code, 0, out)
        self.assertIn('만들 파일 7개', out)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, 'run.py')))
        for bad in ('Judge', '규칙-tz', '_hidden', '1st', 'class'):      # 대문자·하이픈·밑줄 시작·숫자 시작·키워드
            code, out = self.scaffold('--dry-run', '--stages', bad)
            self.assertEqual(code, 1, bad)
            self.assertIn('예 judge · 판정 · rule_tz', out)            # 오류 문구에 이름 예시

    def test_space_or_comma_separated_and_korean_stage_names(self):
        code, out = self.scaffold('--stages', '계약', '판정')
        self.assertEqual(code, 0, out)
        for rel in ('core/계약.py', 'core/판정.py'):
            self.assertTrue(os.path.exists(os.path.join(self.tmp, rel)), rel)
        with io.open(os.path.join(self.tmp, 'core', 'pipeline.py'), encoding='utf-8') as fh:
            self.assertIn("STAGES = [('계약', 계약.apply), ('판정', 판정.apply)]", fh.read())
        code, out = run(['run.py'], cwd=self.tmp)                     # 한글 모듈을 import 해서 끝까지 돈다
        self.assertEqual(code, 0, out)
        with io.open(os.path.join(self.tmp, 'out', 'summary.json'), encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['stage_counts'], {'계약': 2, '판정': 2})
        code, out = run([os.path.join(SCRIPTS, 'docmap.py'), '--root', self.tmp, '--check'], cwd=self.tmp)
        self.assertEqual(code, 0, out)
        code, out = self.scaffold('--dry-run', '--stages', '계약, 판정,rule_tz')   # 쉼표·공백 섞어도 같은 이름
        self.assertEqual(code, 0, out)
        self.assertIn('이미 있어 건너뜀', out)
        self.assertIn('core/rule_tz.py', out)

    def test_generated_run_py_reads_input_dir_env_and_flag_wins(self):
        self.scaffold('--stages', 'clean')
        os.makedirs(os.path.join(self.tmp, 'alt'))
        with io.open(os.path.join(self.tmp, 'alt', 'other.csv'), 'w', encoding='utf-8') as fh:
            fh.write('id,value\nX,9\n')
        env = dict(ENV, INPUT_DIR='alt')
        code, out = run(['run.py'], cwd=self.tmp, env=env)
        self.assertEqual(code, 0, out)
        with io.open(os.path.join(self.tmp, 'out', 'summary.json'), encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['input_counts'], {'other': 1})
        code, out = run(['run.py', '--input-dir', 'data'], cwd=self.tmp, env=env)   # 인자가 환경변수보다 우선
        self.assertEqual(code, 0, out)
        with io.open(os.path.join(self.tmp, 'out', 'summary.json'), encoding='utf-8') as fh:
            self.assertEqual(json.load(fh)['input_counts'], {'sensor': 2})


class TestCheckContractInputDir(unittest.TestCase):
    """check_contract.py M층 ↔ scaffold run.py 의 INPUT_DIR 규약(변형 입력을 안 읽은 '출력 동일' 거짓 PASS 방지)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='cc_')
        os.makedirs(os.path.join(self.tmp, 'data'))
        with io.open(os.path.join(self.tmp, 'data', 'sensor.csv'), 'w', encoding='utf-8') as fh:
            fh.write('id,value\n' + ''.join('%s,%d\n' % (k, i) for i, k in enumerate('ABCDEFGH')))
        code, out = run([os.path.join(SCRIPTS, 'scaffold.py'), '--root', self.tmp, '--stages', 'clean'], cwd=self.tmp)
        self.assertEqual(code, 0, out)
        with io.open(os.path.join(self.tmp, 'cc_run.py'), 'w', encoding='utf-8') as fh:
            fh.write(CC_RUNNER)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_m_layer_reads_shuffled_input_through_input_dir(self):
        """뼈대 파이프라인은 입력 순서를 그대로 내보낸다 → 셔플 입력을 실제로 읽으면 '입력 순서 의존' 으로 잡힌다."""
        code, out = run(['cc_run.py'], cwd=self.tmp)
        self.assertIn('M 가드: RUN_CMD 가 INPUT_DIR 을 읽음', out)
        self.assertIn('[FAIL] M-shuffle_rows', out)
        self.assertEqual(code, 1, out)
        with io.open(os.path.join(self.tmp, 'out', 'result.csv'), encoding='utf-8') as fh:   # 끝나면 기준 출력으로 복원
            self.assertEqual(fh.read().splitlines()[1:3], ['A,0', 'B,1'])

    def test_run_py_ignoring_input_dir_is_m_noop_fail_not_pass(self):
        path = os.path.join(self.tmp, 'run.py')
        with io.open(path, encoding='utf-8') as fh:
            src = fh.read()
        self.assertIn("os.environ.get('INPUT_DIR') or config.INPUT_DIR", src)
        with io.open(path, 'w', encoding='utf-8') as fh:            # 옛 run.py 처럼 INPUT_DIR 을 무시하게 되돌린다
            fh.write(src.replace("os.environ.get('INPUT_DIR') or config.INPUT_DIR", 'config.INPUT_DIR'))
        code, out = run(['cc_run.py'], cwd=self.tmp)
        self.assertIn('[FAIL] M-noop', out)
        self.assertNotIn('M shuffle_rows: 출력 동일', out)
        self.assertEqual(code, 1, out)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, 'out', 'result.csv')))      # 가드가 기준 출력을 지우지 않는다

    def test_no_task_code_yet_is_exit_2_not_fail(self):
        empty = tempfile.mkdtemp(prefix='cc_empty_')
        try:
            code, out = run([os.path.join(SCRIPTS, 'check_contract.py')], cwd=empty)
        finally:
            shutil.rmtree(empty, ignore_errors=True)
        self.assertEqual(code, 2, out)
        self.assertIn('RUN_CMD 의 run.py 없음', out)
        self.assertIn('RESULT: exit 2', out)


if __name__ == '__main__':
    unittest.main()
