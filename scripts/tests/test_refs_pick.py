# -*- coding: utf-8 -*-
"""design-kit/refs(서비스별 참고 DESIGN.md)와 refs/pick.py 테스트 (unittest, Python 3.9 표준 라이브러리).
실행: python3 -m unittest discover -s scripts/tests -p test_refs_pick.py -v
- INDEX.md 표 행 = refs/ko·refs/awesome 의 md 파일(빠짐·남음 0), 칸 8개, 크기KB·라이선스·유형 태그가 실제와 맞음, refs 합계 ≤ 3.5MB
- pick.py 대시보드 → 모니터링 태그 후보 1~5줄, 첫 경로가 실제 파일 / 인자 없음 → 유형 5개·사용법 / 맞는 후보 없음 → exit 1
- 같은 점수면 한국 서비스(ko/) 먼저, 첫 태그가 뒤 태그보다 앞
pick.py 는 'design-kit'(하이픈) 폴더에 있어 import 문으로 못 읽으므로 importlib 로 파일에서 읽는다.
"""
import importlib.util
import os
import re
import subprocess
import sys
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # scripts/tests → 작업 폴더
REFS = os.path.join(ROOT, 'design-kit', 'refs')
PICK = os.path.join(REFS, 'pick.py')
TAGS = {'모니터링', '조회', '콘솔', '모바일', '홈'}
LICENSE_BY_FOLDER = {'ko': 'CC BY 4.0', 'awesome': 'MIT'}
REFS_MAX_BYTES = 3500000   # refs 폴더 합계 상한(바이트)


def load_pick():
    sys.dont_write_bytecode = True   # design-kit 안에 __pycache__ 를 만들지 않는다
    spec = importlib.util.spec_from_file_location('refs_pick', PICK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PK = load_pick()


def run_pick(*args):
    done = subprocess.run([sys.executable, PICK] + list(args), cwd=ROOT, capture_output=True, timeout=60)
    return done.returncode, done.stdout.decode('utf-8', 'replace'), done.stderr.decode('utf-8', 'replace')


def lf_size(path):
    """줄끝을 LF 로 센 크기(Windows 에서 CRLF 로 풀려도 같은 값)."""
    with open(path, 'rb') as fh:
        return len(fh.read().replace(b'\r\n', b'\n'))


class TestIndexMatchesFiles(unittest.TestCase):
    def test_rows_equal_files_and_cells_are_true(self):
        rows = PK.load_rows()
        files = sorted('%s/%s' % (d, f) for d in LICENSE_BY_FOLDER
                       for f in os.listdir(os.path.join(REFS, d)) if f.endswith('.md'))
        self.assertGreaterEqual(len(files), 50)
        self.assertEqual(sorted(r['path'] for r in rows), files, 'INDEX 표 행과 refs 파일이 다르다')
        self.assertEqual(len(rows), len(set(r['path'] for r in rows)), '같은 파일 행이 두 번')
        for r in rows:
            folder = r['path'].split('/')[0]
            size = lf_size(os.path.join(REFS, *r['path'].split('/')))
            self.assertEqual(int(r['kb']), int(size / 1024.0 + 0.5), '%s 크기KB' % r['path'])
            self.assertEqual(r['license'], LICENSE_BY_FOLDER[folder], r['path'])
            self.assertTrue(r['tags'] and set(r['tags']) <= TAGS, '%s 태그 %s' % (r['path'], r['tags']))
            self.assertEqual(len(r['mood'].split('·')), 3, '%s 분위기 3단어' % r['path'])
            self.assertTrue(r['service'] and r['color'] and r['font'], r['path'])
        total = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(REFS) for f in fs)
        self.assertLessEqual(total, REFS_MAX_BYTES)
        with open(os.path.join(REFS, 'INDEX.md'), encoding='utf-8') as fh:
            head = fh.read().split('## 표 읽는 법')[0]
        self.assertIn('pick.py', head)
        self.assertEqual(len(re.findall(r'(?m)^(?:\d\.|-) ', head)), 7, '쓰는 법 1~6 + 옮기는 것 1줄')


class TestPickCli(unittest.TestCase):
    def test_dashboard_lists_monitoring_candidates(self):
        code, out, err = run_pick('대시보드')
        self.assertEqual(code, 0, err)
        lines = [ln for ln in out.splitlines() if ln.startswith('design-kit/refs/')]
        self.assertTrue(1 <= len(lines) <= 5, out)
        for ln in lines:
            parts = ln.split(' · ')
            self.assertEqual(len(parts), 5, ln)            # 경로 · 서비스 · 유형 · 분위기 · 크기
            self.assertIn('모니터링', parts[2], ln)
            self.assertRegex(parts[4], r'^\d+KB$')
        self.assertTrue(os.path.isfile(os.path.join(ROOT, *lines[0].split(' · ')[0].split('/'))), lines[0])

    def test_usage_and_no_match(self):
        code, out, _ = run_pick()
        self.assertEqual(code, 0)
        self.assertIn('사용법', out)
        for tag in TAGS:
            self.assertIn(tag, out)
        code, out, err = run_pick('없는낱말xyz')
        self.assertEqual(code, 1)
        self.assertIn('맞는 후보 없음', err)


class TestPickOrder(unittest.TestCase):
    def test_korean_first_on_tie_and_first_tag_beats_later_tag(self):
        def row(path, tags, order):
            return {'path': path, 'service': 's', 'tags': tags, 'mood': 'a·b·c', 'color': '-', 'font': '-',
                    'kb': '1', 'license': '-', 'order': order}
        rows = [row('awesome/a.md', ['모바일'], 0), row('awesome/b.md', ['홈', '모바일'], 1),
                row('ko/c.md', ['모바일'], 2), row('ko/d.md', ['콘솔'], 3)]
        got = [r['path'] for r in PK.pick(rows, ['앱'])]
        self.assertEqual(got, ['ko/c.md', 'awesome/a.md', 'awesome/b.md'])
        self.assertEqual(PK.score(rows[1], ['모바일', 's']), 2 + 1)   # 뒤 태그 2 + 서비스 칸 1


if __name__ == '__main__':
    unittest.main()
