# -*- coding: utf-8 -*-
"""scripts/flowmap.py 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_flowmap -v
분류: 예시 스펙 생성(h1 1개·svg·단계 수·숫자) / 합계 불일치 → exit 1 + FAIL 띠 / 스펙 없음 → exit 2 / --check / 스펙 오류 거부
      / 문자열 이스케이프 / 토큰 정의 / 0건 규칙 표시 / design-kit/ui_check.py 파일 모드 FAIL 0 (서브프로세스)"""
import copy
import json
import os
import re
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
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import flowmap  # noqa: E402

EXAMPLE = os.path.join(ROOT, 'docs', 'flow.example.json')
FLOWMAP = os.path.join(SCRIPTS, 'flowmap.py')
UI_CHECK = os.path.join(ROOT, 'design-kit', 'ui_check.py')
TOKENS = os.path.join(ROOT, 'design-kit', 'tokens.css')
H1_RE = re.compile(r'<h1[\s>]')


def run(args, script=FLOWMAP):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    return subprocess.run([sys.executable, script] + list(args), cwd=ROOT, capture_output=True,
                          text=True, encoding='utf-8', errors='replace', env=env)


def load_example():
    with open(EXAMPLE, 'r', encoding='utf-8') as fh:
        return json.load(fh)


def write_spec(tmp, spec, name='flow.json'):
    path = os.path.join(tmp, name)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(spec, fh, ensure_ascii=False)
    return path


# ---------------------------------------------------------------- 정상 경로: 예시 스펙으로 생성
class TestExampleReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = os.path.join(cls.tmp.name, 'report.html')
        cls.proc = run(['--spec', EXAMPLE, '--out', cls.out])
        cls.spec = load_example()
        cls.html = ''
        if os.path.exists(cls.out):
            with open(cls.out, 'r', encoding='utf-8') as fh:
                cls.html = fh.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_exit_0_and_file_written(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        self.assertTrue(os.path.exists(self.out))
        self.assertIn('35,496', self.proc.stdout)

    def test_h1_exactly_one(self):
        self.assertEqual(len(H1_RE.findall(self.html)), 1)

    def test_svg_pipeline_has_every_stage_twice(self):
        """가로·세로 SVG 두 벌이라 단계 상자는 2 × 단계 수. 둘 다 role=img + aria-label."""
        n = len(self.spec['stages'])
        self.assertIn('<svg', self.html)
        self.assertEqual(self.html.count('class="stage"'), 2 * n)
        self.assertEqual(self.html.count('role="img"'), 3)  # 가로 svg + 세로 svg + 합계 띠
        for st in self.spec['stages']:
            self.assertIn(st['name'], self.html)

    def test_numbers_from_spec_are_in_report(self):
        for s in ('35,496', '30,312', '5,184', '4,642', '408', '134'):
            self.assertIn(s, self.html)
        self.assertIn('입력 35,496 = 통과 30,312 + 제외 5,184', self.html)
        self.assertNotIn('합계 불일치', self.html)

    def test_sections_and_badges(self):
        for h2 in ('파이프라인', '합계 보존', '규칙 발동', '결정', '검증', '링크'):
            self.assertIn('<h2>%s</h2>' % h2, self.html)
        self.assertIn('badge ok">PASS', self.html)
        self.assertIn('badge warn">HUMAN_CHECK', self.html)
        self.assertIn('badge off">NOT_RUN', self.html)

    def test_single_file_no_external_resources_no_script(self):
        self.assertIsNone(re.search(r'(src|href)=["\']https?://', self.html))
        self.assertNotIn('<link', self.html)
        self.assertNotIn('<script', self.html)
        self.assertIn('name="viewport"', self.html)

    def test_zero_fired_rule_is_flagged(self):
        self.assertIn('row-warn', self.html)
        self.assertIn('0건, 엣지 입력으로 재확인', self.html)

    def test_same_spec_gives_same_html(self):
        a, _ = flowmap.build_html(self.spec, self.out, spec_label='x')
        b, _ = flowmap.build_html(copy.deepcopy(self.spec), self.out, spec_label='x')
        self.assertEqual(a, b)


# ---------------------------------------------------------------- 업무 규칙: 합계 보존
class TestConservation(unittest.TestCase):
    def test_mismatch_writes_fail_band_and_exits_1(self):
        spec = load_example()
        spec['conservation']['passed'] += 4
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'r.html')
            proc = run(['--spec', write_spec(tmp, spec), '--out', out])
            self.assertEqual(proc.returncode, 1)
            self.assertIn('합계 불일치', proc.stderr)
            with open(out, 'r', encoding='utf-8') as fh:
                text = fh.read()
        self.assertIn('FAIL: 합계 불일치', text)
        self.assertIn('class="band fail"', text)
        self.assertIn('차이 -4', text)

    def test_check_mode_reports_mismatch_without_writing(self):
        spec = load_example()
        spec['conservation']['excluded']['완전 중복(duplicate)'] -= 1
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'r.html')
            proc = run(['--check', '--spec', write_spec(tmp, spec), '--out', out])
            self.assertEqual(proc.returncode, 1)
            self.assertIn('합계 불일치', proc.stderr)
            self.assertFalse(os.path.exists(out))

    def test_delta_helper(self):
        spec = load_example()
        self.assertEqual(flowmap.conservation_delta(spec), (35496, 30312, 5184, 0))


# ---------------------------------------------------------------- 실패 경로: 스펙 없음·오류
class TestSpecErrors(unittest.TestCase):
    def test_missing_spec_exits_2_with_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'r.html')
            proc = run(['--spec', os.path.join(tmp, 'none.json'), '--out', out])
            self.assertEqual(proc.returncode, 2)
            self.assertIn('flow.example.json', proc.stderr)
            self.assertFalse(os.path.exists(out))

    def test_check_passes_example_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'r.html')
            proc = run(['--check', '--spec', EXAMPLE, '--out', out])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('OK', proc.stdout)
            self.assertFalse(os.path.exists(out))

    def test_invalid_status_is_rejected_with_field_name(self):
        spec = load_example()
        spec['verification'][0]['status'] = 'OK'
        with tempfile.TemporaryDirectory() as tmp:
            proc = run(['--check', '--spec', write_spec(tmp, spec)])
            self.assertEqual(proc.returncode, 1)
            self.assertIn('verification[0].status', proc.stderr)

    def test_structural_errors_are_listed_by_field(self):
        spec = load_example()
        spec['stages'][0]['rules'][0]['fired'] = 'many'
        spec['stages'][1]['id'] = spec['stages'][0]['id']
        del spec['conservation']['excluded']
        errs = flowmap.validate(spec)
        joined = '\n'.join(errs)
        self.assertIn('stages[0].rules[0].fired', joined)
        self.assertIn('stages[1].id 중복', joined)
        self.assertIn('conservation.excluded', joined)
        self.assertEqual(flowmap.validate([]), ['최상위는 객체({})여야 함'])

    def test_malformed_json_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'bad.json')
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('{"title": ')
            proc = run(['--check', '--spec', path])
            self.assertEqual(proc.returncode, 1)
            self.assertIn('JSON', proc.stderr)


# ---------------------------------------------------------------- 계약: 이스케이프·토큰
class TestEscapeAndTokens(unittest.TestCase):
    def test_every_string_is_html_escaped(self):
        spec = load_example()
        spec['title'] = '<b>굵게</b> & "따옴표"'
        spec['stages'][0]['name'] = '<i>정제</i>'
        spec['stages'][0]['rules'][0]['name'] = '<script>x</script>'
        spec['decisions'][0]['what'] = '</td><td>탈출'
        spec['links'][0]['label'] = '<img>'
        text, _ = flowmap.build_html(spec, os.path.join(ROOT, 'out', 'r.html'))
        self.assertIn('&lt;b&gt;굵게&lt;/b&gt; &amp; &quot;따옴표&quot;', text)
        self.assertIn('&lt;i&gt;정제&lt;/i&gt;', text)
        self.assertNotIn('<b>굵게</b>', text)
        self.assertNotIn('<script>', text)
        self.assertNotIn('</td><td>탈출', text)
        self.assertNotIn('<img>', text)

    def test_every_var_used_is_defined_even_with_fallback_tokens(self):
        """design-kit 이 없어도 페이지 CSS 가 쓰는 토큰은 전부 FALLBACK_TOKENS 에 있어야 한다."""
        text, _ = flowmap.build_html(load_example(), os.path.join(ROOT, 'out', 'r.html'), tokens=flowmap.FALLBACK_TOKENS)
        used = set(re.findall(r'var\(\s*(--[A-Za-z0-9_-]+)', text))
        defined = set(re.findall(r'(--[A-Za-z0-9_-]+)\s*:', text))
        self.assertTrue(used, '토큰을 하나도 안 씀')
        self.assertEqual(sorted(used - defined), [])

    def test_no_raw_hex_in_generated_css(self):
        text, _ = flowmap.build_html(load_example(), os.path.join(ROOT, 'out', 'r.html'))
        self.assertEqual(flowmap.HEX_RE.findall(text), [])

    def test_hex_to_rgb(self):
        self.assertEqual(flowmap.hex_to_rgb('#0b7a53'), 'rgb(11, 122, 83)')
        self.assertEqual(flowmap.hex_to_rgb('#fff'), 'rgb(255, 255, 255)')
        self.assertEqual(flowmap.hex_to_rgb('#00000080'), 'rgba(0, 0, 0, 0.502)')


# ---------------------------------------------------------------- 보안·문서 계약: design-kit/ui_check.py 파일 모드
class TestUiCheck(unittest.TestCase):
    def test_generated_report_passes_ui_check_with_zero_fail(self):
        if not os.path.exists(UI_CHECK):
            self.skipTest('design-kit/ui_check.py 없음')
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'report.html')
            gen = run(['--spec', EXAMPLE, '--out', out])
            self.assertEqual(gen.returncode, 0, gen.stderr)
            proc = run([out, '--tokens', TOKENS, '--no-tree'], script=UI_CHECK)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        m = re.search(r'RESULT: (\d+) PASS / (\d+) WARN / (\d+) FAIL', proc.stdout)
        self.assertIsNotNone(m, proc.stdout)
        self.assertEqual(m.group(3), '0', proc.stdout)


if __name__ == '__main__':
    unittest.main()
