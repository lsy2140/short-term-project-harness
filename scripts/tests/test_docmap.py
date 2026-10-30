# -*- coding: utf-8 -*-
"""scripts/docmap.py 테스트 (unittest, Python 3.9). 실행: python3 -m unittest discover -s scripts/tests -p test_docmap.py -v
고정하는 것: 과제 코드만 찾음(하네스 폴더 제외) · 설명문 없음/입력·출력 줄 없음 검출 · 던더·함수 안 함수 제외 ·
클래스 메서드 포함 · exit 코드(0 문제 없음 / 1 --check 문제 / 2 과제 코드 없음) · 긴 함수 표시 · 문법 오류 보고."""
import io
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
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import docmap  # noqa: E402

GOOD = '''def solve(rows):
    """행을 처리한다.

    입력: rows — 행 목록
    출력: 결과 행 목록
    규칙: 값이 기준 이상이면 포함(D02)
    """
    def inner(x):
        return x
    return [inner(r) for r in rows]
'''

BAD = '''def no_doc(rows):
    return rows


def no_io(rows):
    """설명만 있고 입력·출력 줄이 없다."""
    return rows


class Handler:
    def __init__(self):
        pass

    def do_GET(self):
        return 1
'''


def write(base, rel, text):
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


class TestDocmap(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='docmap_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        p = subprocess.run([sys.executable, os.path.join(SCRIPTS, 'docmap.py'), '--root', self.tmp] + list(args),
                           capture_output=True, encoding='utf-8', errors='replace',
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'), timeout=60)
        return p.returncode, p.stdout + p.stderr

    def test_finds_task_code_but_not_harness_folders(self):
        write(self.tmp, 'run.py', GOOD)
        write(self.tmp, 'core/rules.py', GOOD)
        for d in ('scripts', 'tests', 'design-kit', 'docs', 'data', 'out', '.tmp', 'submission/pkg'):
            write(self.tmp, d + '/x.py', BAD)
        self.assertEqual(docmap.find_task_files(self.tmp), [os.path.join('core', 'rules.py'), 'run.py'])

    def test_good_docstring_has_no_problems_and_inner_function_is_skipped(self):
        write(self.tmp, 'run.py', GOOD)
        info = docmap.scan_file(self.tmp, 'run.py')
        self.assertEqual([f['name'] for f in info['functions']], ['solve'])
        self.assertEqual(info['functions'][0]['problems'], [])
        self.assertEqual(info['functions'][0]['rule'], '값이 기준 이상이면 포함(D02)')

    def test_detects_missing_docstring_and_missing_io_lines_including_methods(self):
        write(self.tmp, 'app.py', BAD)
        funcs = {f['name']: f['problems'] for f in docmap.scan_file(self.tmp, 'app.py')['functions']}
        self.assertEqual(funcs['no_doc'], ['설명문 없음'])
        self.assertEqual(funcs['no_io'], ['입력: 줄 없음', '출력: 줄 없음'])
        self.assertEqual(funcs['Handler.do_GET'], ['설명문 없음'])
        self.assertNotIn('Handler.__init__', funcs)

    def test_english_input_output_labels_are_accepted(self):
        write(self.tmp, 'run.py', 'def f(a):\n    """Do it.\n\n    Args: a\n    Returns: b\n    """\n    return a\n')
        self.assertEqual(docmap.scan_file(self.tmp, 'run.py')['functions'][0]['problems'], [])

    def test_check_exit_codes(self):
        self.assertEqual(self.run_cli('--check')[0], 2)            # 과제 코드 없음
        write(self.tmp, 'run.py', GOOD)
        code, out = self.run_cli('--check')
        self.assertEqual(code, 0, out)
        write(self.tmp, 'app.py', BAD)
        code, out = self.run_cli('--check')
        self.assertEqual(code, 1, out)
        self.assertIn('app.py:1 no_doc — 설명문 없음', out)

    def test_map_mode_exits_0_even_with_problems_and_shows_summary(self):
        write(self.tmp, 'app.py', BAD)
        code, out = self.run_cli()
        self.assertEqual(code, 0, out)
        self.assertIn('함수 3개 · 설명문 문제 3건', out)

    def test_long_function_is_listed(self):
        body = 'def long_one(x):\n    """긴 함수.\n\n    입력: x\n    출력: x\n    """\n' + '    x += 1\n' * 45 + '    return x\n'
        write(self.tmp, 'run.py', body)
        data = docmap.build(self.tmp)
        self.assertEqual(len(data['long_functions']), 1)
        self.assertIn('long_one', data['long_functions'][0])

    def test_syntax_error_is_reported_not_raised(self):
        write(self.tmp, 'run.py', 'def broken(:\n    pass\n')
        data = docmap.build(self.tmp)
        self.assertIn('문법 오류', data['files'][0]['error'])
        self.assertEqual(data['n_problems'], 1)


if __name__ == '__main__':
    unittest.main()
