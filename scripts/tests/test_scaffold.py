# -*- coding: utf-8 -*-
"""scripts/scaffold.py 테스트 (unittest, Python 3.9). 실행: python3 -m unittest discover -s scripts/tests -p test_scaffold.py -v
고정하는 것: 뼈대 파일 목록 · 만든 직후 `python3 run.py` 가 data/*.csv → out/ 을 씀 · 단계 모듈이 pipeline 순서에 들어감 ·
있는 파일은 덮어쓰지 않음 · 만든 코드는 docmap --check 통과 · 잘못된 이름은 exit 1 · --dry-run 은 쓰지 않음."""
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


def run(args, cwd, timeout=60):
    p = subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, encoding='utf-8',
                       errors='replace', env=ENV, timeout=timeout)
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


if __name__ == '__main__':
    unittest.main()
