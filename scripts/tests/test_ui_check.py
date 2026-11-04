# -*- coding: utf-8 -*-
"""design-kit/ui_check.py 와 디자인 키트 파일 테스트 (unittest, Python 3.9 표준 라이브러리).
실행: python3 -m unittest discover -s scripts/tests -p test_ui_check.py -v  (또는 python3 scripts/tests/test_ui_check.py)
- Floor 5규칙(WARN) 양성·음성 조각
- 그림 자리 --final(초안 .figure 가 남으면 FAIL) · 점 배지 >8 WARN · .why 잔존 WARN · 지운 장식 클래스 WARN
- 외부 판정은 http(s) 주소만(로컬 img·svg·icons.svg 허용)
- 로컬 자원(script·use·img·K.load)은 페이지 위치 기준으로 풀어 404·없는 파일이면 FAIL(파일 경로·임시 URL 서버 둘 다)
- 키트 4페이지(kit.html·templates 3종) FAIL 0, 템플릿 구조(kit.js·data.json·와이어 주석·템플릿 간 링크 없음), icons.svg 심볼
- 문서 상한·안내: DESIGN.md ≤ 9,000B · web-ui SKILL.md ≤ 5,120B(description ≤ 200자) · refs/INDEX.md·시안 안내 · 옛 고지 파일명·절대 분 지시 0
ui_check.py 는 'design-kit'(하이픈) 폴더에 있어 import 문으로 못 읽으므로 importlib 로 파일에서 읽는다.
"""
import functools
import http.server
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))  # scripts/tests → 작업 폴더
KIT = os.path.join(ROOT, 'design-kit')
TEMPLATES = ['dashboard.html', 'tool.html', 'mobile.html']
PAGES = ['kit.html'] + [os.path.join('templates', t) for t in TEMPLATES]
FLOOR = ['no transition all', 'no 100vw width', 'uppercase tracked label', 'no middot meta', 'no card in card']
DECOR = ['dot badges <= 8', 'no .why line', 'no removed class']


def load_ui_check():
    sys.dont_write_bytecode = True   # design-kit 안에 __pycache__ 를 만들지 않는다
    spec = importlib.util.spec_from_file_location('ui_check', os.path.join(KIT, 'ui_check.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


UI = load_ui_check()

SKELETON = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"><title>검사용</title>'
            '<style>%s</style></head><body><h1>제목</h1>%s</body></html>')


def read(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


def run_fragment(css='', body='', final=False):
    """CSS·본문 조각을 최소 페이지에 넣어 파일 모드로 검사하고 {검사 이름: (상태, 상세)} 를 돌려준다."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'page.html')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(SKELETON % (css, body))
        results, _ = UI.check_page(path, final=final)
    return {name: (status, detail) for name, status, detail in results}


class Base(unittest.TestCase):
    def assertRule(self, name, expected, css='', body='', final=False):
        got = run_fragment(css, body, final)
        self.assertIn(name, got, '검사 %s 가 결과에 없음' % name)
        self.assertEqual(got[name][0], expected, '%s: %s' % (name, got[name][1]))
        return got[name][1]


# ---------------------------------------------------------------- Floor 5규칙
class TestFloorRules(Base):
    def test_transition_all_and_layout_props_are_warned(self):
        self.assertRule('no transition all', 'WARN', css='.a { transition: all .2s ease; }')
        self.assertRule('no transition all', 'WARN', css='.b { transition: opacity .3s, width .3s; }')
        self.assertRule('no transition all', 'WARN', body='<div style="transition: height .3s">x</div>')

    def test_transform_and_max_height_transition_pass(self):
        self.assertRule('no transition all', 'PASS', css='.a { transition: transform .25s, max-height .3s; } .b { transition: none; }')

    def test_100vw_width_is_warned_but_max_width_passes(self):
        self.assertRule('no 100vw width', 'WARN', css='.hero { width: 100vw; }')
        self.assertRule('no 100vw width', 'WARN', css='.band { min-width: calc(100vw - 10px); }')
        self.assertRule('no 100vw width', 'PASS', css='.toast { max-width: calc(100vw - 40px); width: 100%; }')

    def test_uppercase_tracking_same_block_only(self):
        self.assertRule('uppercase tracked label', 'WARN', css='.label { text-transform: uppercase; letter-spacing: .08em; }')
        self.assertRule('uppercase tracked label', 'WARN', css='.cap { font-variant: small-caps; letter-spacing: .1em; }')
        self.assertRule('uppercase tracked label', 'PASS', css='.a { text-transform: uppercase; } .b { letter-spacing: .06em; }')
        self.assertRule('uppercase tracked label', 'PASS', css='.h { text-transform: uppercase; letter-spacing: -.02em; }')

    def test_spaced_middot_meta_three_elements(self):
        meta = '<p class="meta">어제 · 1월 12일 · 설계</p>'
        self.assertRule('no middot meta', 'WARN', body=meta * 3)
        self.assertRule('no middot meta', 'PASS', body=meta * 2)
        self.assertRule('no middot meta', 'PASS', body='<p>수율·가동률·WIP</p>' * 4)

    def test_card_in_card(self):
        self.assertRule('no card in card', 'WARN', body='<div class="card"><h2>바깥</h2><div class="card">안쪽</div></div>')
        self.assertRule('no card in card', 'PASS', body='<div class="card"><div class="card flat">안쪽</div></div>')
        self.assertRule('no card in card', 'PASS', body='<div class="cards"><div class="card">a</div><div class="card">b</div></div>')


# ---------------------------------------------------------------- 그림 자리 --final
class TestFigureFinal(Base):
    DRAFT = '<figure class="figure" data-ratio="16/9"><figcaption>어떤 그림: 웨이퍼 흐름, 2색</figcaption></figure>'

    def test_draft_passes_without_final_and_reports_count(self):
        detail = self.assertRule('figure final', 'PASS', body=self.DRAFT)
        self.assertIn('초안 1개', detail)

    def test_draft_fails_with_final(self):
        detail = self.assertRule('figure final', 'FAIL', body=self.DRAFT * 2, final=True)
        self.assertIn('초안 2개', detail)
        self.assertIn('어떤 그림', detail)

    def test_final_img_svg_and_mask_pass(self):
        body = ('<figure class="figure is-final"><img src="img/01.png" alt="웨이퍼"></figure>'
                '<figure class="figure is-final"><svg role="img" aria-label="그림"><circle r="4"/></svg></figure>'
                '<figure class="figure is-final mask" style="--mask: url(illustrations/01-empty.svg)"><i></i></figure>')
        detail = self.assertRule('figure final', 'PASS', body=body, final=True)
        self.assertIn('초안 0개', detail)

    def test_is_final_without_media_still_fails(self):
        self.assertRule('figure final', 'FAIL', body='<figure class="figure is-final"><figcaption>x</figcaption></figure>', final=True)

    def test_plain_figure_tag_is_not_a_slot(self):
        self.assertRule('figure final', 'PASS', body='<figure><figcaption>표 설명</figcaption></figure>', final=True)

    def test_cli_final_exit_code(self):
        tool = os.path.join(KIT, 'templates', 'tool.html')
        cmd = [sys.executable, '-B', os.path.join(KIT, 'ui_check.py'), tool, '--no-tree']
        env = dict(os.environ, PYTHONIOENCODING='utf-8')
        plain = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        final = subprocess.run(cmd + ['--final'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.assertEqual(plain.returncode, 0, plain.stdout.decode('utf-8', 'replace')[-400:])
        self.assertEqual(final.returncode, 1)
        out = final.stdout.decode('utf-8', 'replace')
        self.assertEqual(len(re.findall(r'^\S[^\n]*? FAIL  ', out, re.M)), 1, out[-600:])   # 검사 줄만(RESULT 요약 줄 제외)


# ---------------------------------------------------------------- 장식 잔재
class TestDecorRules(Base):
    def test_dot_badges_over_eight_warn(self):
        self.assertRule('dot badges <= 8', 'WARN', body='<span class="badge ok live">실시간</span>' * 9)
        self.assertRule('dot badges <= 8', 'PASS', body='<span class="badge ok live">실시간</span>' * 8 + '<span class="badge">x</span>' * 20)

    def test_inner_dot_counts(self):
        self.assertRule('dot badges <= 8', 'WARN', body='<span class="badge"><i class="dot"></i>가동</span>' * 9)

    def test_why_line_warns(self):
        self.assertRule('no .why line', 'WARN', body='<h2>설비</h2><p class="why">왜 이 섹션인가</p>')
        self.assertRule('no .why line', 'PASS', body='<h2>설비</h2><p class="meta">기준 09:00</p>')

    def test_removed_classes_warn(self):
        detail = self.assertRule('no removed class', 'WARN', body='<div class="bezel"><span class="pill">x</span></div>')
        self.assertIn('bezel', detail)
        self.assertRule('no removed class', 'PASS', body='<div class="panel"><span class="badge">x</span></div>')


# ---------------------------------------------------------------- 외부 판정: http(s) 만
class TestExternal(Base):
    NAME = 'no external asset'

    def test_local_img_svg_icons_pass(self):
        body = ('<img src="img/01.png" alt="a"><img src="../illustrations/02-no-alerts.svg" alt="b">'
                '<svg class="ico" aria-hidden="true"><use href="../icons.svg#i-bell"/></svg>')
        self.assertRule(self.NAME, 'PASS', css='.x { background: url(illustrations/01-empty.svg); }', body=body)

    def test_remote_img_use_import_fail(self):
        self.assertRule(self.NAME, 'FAIL', body='<img src="https://example.com/a.png" alt="a">')
        self.assertRule(self.NAME, 'FAIL', body='<svg aria-hidden="true"><use href="http://example.com/i.svg#a"/></svg>')
        self.assertRule(self.NAME, 'FAIL', css='@import "https://example.com/x.css";')
        self.assertRule(self.NAME, 'FAIL', css='.x { background: url(https://example.com/a.png); }')

    def test_raw_hex_rule_still_fires(self):
        self.assertRule('no raw hex in page', 'FAIL', css='.a { color: #123456; }')


# ---------------------------------------------------------------- 로컬 자원: 페이지 위치 기준 404
class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class TestLocalAsset(unittest.TestCase):
    """템플릿을 static/index.html 로 옮긴 뒤 ../kit.js·../icons.svg·../data.json 이 남으면 잡는다(CSS 만 고친 드라이런 사고)."""
    NAME = 'local asset'
    BODY = ('<script src="../kit.js"></script><svg class="ico" aria-hidden="true"><use href="../icons.svg#i-bell"/></svg>'
            '<img src="data:image/png;base64,AAAA" alt="점"><svg aria-hidden="true"><use href="#i-local"/></svg>'
            "<script>K.load('../data.json', {});</script>")

    def page(self, d, rel='static/index.html', body=None):
        path = os.path.join(d, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(SKELETON % ('', self.BODY if body is None else body))
        return path

    def touch_assets(self, d):
        for name in ('kit.js', 'icons.svg', 'data.json'):
            with open(os.path.join(d, name), 'w', encoding='utf-8') as fh:
                fh.write('x')

    def result(self, target):
        return {n: (s, dt) for n, s, dt in UI.check_page(target)[0]}[self.NAME]

    def test_file_mode_missing_then_present(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.page(d)
            st, detail = self.result(path)
            self.assertEqual(st, 'FAIL', detail)
            for name in ('../kit.js', '../icons.svg', '../data.json'):
                self.assertIn(name, detail)
            self.touch_assets(d)
            self.assertEqual(self.result(path)[0], 'PASS')

    def test_file_mode_skips_root_paths_data_uri_and_fragments(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.page(d, 'page.html', '<script src="/static/app.js"></script><img src="data:image/gif;base64,R0" alt="a">'
                                             '<svg aria-hidden="true"><use href="#i-x"/></svg>')
            st, detail = self.result(path)
            self.assertEqual(st, 'PASS', detail)
            self.assertIn('건너뜀', detail)

    def test_url_mode_resolves_like_a_browser(self):
        with tempfile.TemporaryDirectory() as d:
            self.page(d)
            srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_QuietHandler, directory=d))
            th = threading.Thread(target=srv.serve_forever, daemon=True)
            th.start()
            try:
                url = 'http://127.0.0.1:%d/static/index.html' % srv.server_address[1]
                st, detail = self.result(url)
                self.assertEqual(st, 'FAIL', detail)              # ../kit.js → /kit.js 404
                self.assertIn('../kit.js', detail)
                self.touch_assets(d)
                self.assertEqual(self.result(url)[0], 'PASS')
            finally:
                srv.shutdown()
                srv.server_close()
                th.join(5)


# ---------------------------------------------------------------- 키트 파일
class TestKitPages(unittest.TestCase):
    def test_pages_have_zero_fail_and_clean_floor_decor(self):
        for page in PAGES:
            got = {n: (s, d) for n, s, d in UI.check_page(os.path.join(KIT, page))[0]}
            fails = {n: v for n, v in got.items() if v[0] == 'FAIL'}
            self.assertEqual(fails, {}, page)
            for name in FLOOR + DECOR:
                self.assertEqual(got[name][0], 'PASS', '%s: %s %s' % (page, name, got[name][1]))

    def test_templates_structure(self):
        for t in TEMPLATES:
            html = read(os.path.join(KIT, 'templates', t))
            head = html.split('-->', 1)[0]
            self.assertIn('390', head, '%s: 머리 와이어 주석' % t)
            self.assertIn('834', head, '%s: 머리 와이어 주석 태블릿 줄' % t)
            self.assertIn('src="../kit.js"', html, t)
            self.assertIn("K.load('../data.json'", html, t)
            self.assertIn('K.setStatus(', html, t)
            others = [o for o in TEMPLATES if o != t]
            for o in others + ['console.html', 'landing.html']:
                self.assertNotIn('href="%s' % o, html, '%s: 템플릿 간 링크 %s' % (t, o))
                self.assertNotIn('href="../templates/%s' % o, html, t)

    def test_tool_template_has_one_draft_figure(self):
        got = {n: (s, d) for n, s, d in UI.check_page(os.path.join(KIT, 'templates', 'tool.html'), final=True)[0]}
        self.assertEqual(got['figure final'][0], 'FAIL')
        self.assertEqual([n for n, v in got.items() if v[0] == 'FAIL'], ['figure final'])

    def test_kit_js_exports(self):
        js = read(os.path.join(KIT, 'kit.js'))
        for fn in ('esc', 'fmt', 'kv', 'hhmm', 'badge', 'chips', 'toast', 'setStatus', 'load', 'spark', 'hbar'):
            self.assertIn('K.%s = function' % fn, js)

    def test_icons_svg_symbols_and_references(self):
        root = ET.parse(os.path.join(KIT, 'icons.svg')).getroot()
        syms = [el for el in root.iter() if el.tag.endswith('symbol')]
        self.assertTrue(20 <= len(syms) <= 32, len(syms))
        ids = set()
        for el in syms:
            self.assertTrue(el.get('id', '').startswith('i-'), el.get('id'))
            self.assertEqual(el.get('viewBox'), '0 0 24 24', el.get('id'))
            self.assertEqual((el.get('fill'), el.get('stroke')), ('none', 'currentColor'), el.get('id'))
            ids.add(el.get('id'))
        for page in PAGES:
            for ref in re.findall(r'icons\.svg#(i-[\w-]+)', read(os.path.join(KIT, page))):
                self.assertIn(ref, ids, '%s: %s' % (page, ref))

    def test_kit_docs_limits_and_design_flow_pointers(self):
        """DESIGN.md·web-ui SKILL 크기 상한, 참고 md·시안 안내가 있고, 옛 고지 파일명·절대 분 지시가 없다(refs 원문 제외)."""
        skill = os.path.join(ROOT, '.agents', 'skills', 'web-ui', 'SKILL.md')
        self.assertLessEqual(os.path.getsize(os.path.join(KIT, 'DESIGN.md')), 9000)
        self.assertLessEqual(os.path.getsize(skill), 5120)
        desc = re.search(r'^description: (.*)$', read(skill), re.M).group(1)
        self.assertLessEqual(len(desc), 200)
        for path, words in ((os.path.join(KIT, 'DESIGN.md'), ('refs/pick.py', 'DESIGN_과제', 'sian_N', 'tablet.png', '834')),
                            (os.path.join(KIT, 'REFERENCE.md'), ('refs/INDEX.md', '834')),
                            (os.path.join(KIT, 'illustrations', 'PROMPTS.md'), ('## 시안 틀', 'sian_$N.css', '배치', 'for N in 1 2 3 4 5')),
                            (skill, ('pick.py', 'DESIGN_과제.md', '시안 선택 전 본 화면', '동시 요청', '834'))):
            for w in words:
                self.assertIn(w, read(path), '%s: %s' % (os.path.basename(path), w))
        hits = []
        docs = [skill] + [os.path.join(dp, f) for dp, _, fs in os.walk(KIT) for f in fs
                          if f.endswith('.md') and os.sep + 'refs' + os.sep + 'ko' not in dp + os.sep
                          and os.sep + 'refs' + os.sep + 'awesome' not in dp + os.sep]
        for p in docs:
            for i, line in enumerate(read(p).splitlines(), 1):
                if re.search(r'THIRD[_]PARTY|사람이 (띄|연다)|[0-9]+분 (이후|에|부터)', line):
                    hits.append('%s:%d' % (os.path.relpath(p, ROOT), i))
        self.assertEqual(hits, [])

    def test_base_css_tablet_rule(self):
        """base.css 의 태블릿 구간(max-width: 1024px) 안에 .cols-3 2열 규칙이 있고, components.css 에 상단 띠 비율 21/9 가 있다."""
        base = read(os.path.join(KIT, 'base.css'))
        m = re.search(r'@media \(max-width: 1024px\) \{(.*?)\n\}', base, re.S)
        self.assertIsNotNone(m, 'base.css: @media (max-width: 1024px) 블록')
        self.assertIn('.cols-3', m.group(1), 'base.css: 태블릿 블록의 .cols-3 2열')
        self.assertIn('repeat(2, minmax(0, 1fr))', m.group(1))
        self.assertIn('data-ratio="21/9"', read(os.path.join(KIT, 'components.css')))

    def test_three_viewports_everywhere(self):
        """사람·Codex 문서에 태블릿 834 가 있고, 키트 문서(refs 원문·과제 중 생기는 문서 제외)에 옛 2뷰포트·시안 2~3개·그림 3장 문구가 없다."""
        skill = os.path.join(ROOT, '.agents', 'skills', 'web-ui', 'SKILL.md')
        missing = []
        for p in (os.path.join(ROOT, 'RUN.md'), os.path.join(ROOT, 'docs', 'prompts.md'), os.path.join(ROOT, 'HANDOFF.md'),
                  os.path.join(KIT, 'DESIGN.md'), skill):
            if '834' not in read(p):
                missing.append(os.path.relpath(p, ROOT))
        self.assertEqual(missing, [], '834 없음')
        old = ('screenshots/ 2장', '시안 2~3', '후보 2~3', '3장 이하')
        hits = []

        def mds(d):
            return [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith('.md')]
        # 키트가 들고 가는 문서만(과제 중 생기는 PRD·work/agents·out/report 의 일반 문장은 검사하지 않는다)
        kit_docs = ([os.path.join(ROOT, n) for n in ('AGENTS.md', 'README.md', 'RUN.md', 'HANDOFF.md', 'TASK.md', 'PLAN.md', 'DECISIONS.md', 'PRD.md')]
                    + mds(os.path.join(ROOT, 'docs')) + mds(os.path.join(ROOT, 'work')) + mds(KIT) + mds(os.path.join(KIT, 'illustrations'))
                    + [os.path.join(KIT, 'refs', 'INDEX.md'), os.path.join(KIT, 'refs', '_DESIGN_과제.template.md')])
        for p in kit_docs:
            if not os.path.exists(p):
                continue
            for i, line in enumerate(read(p).splitlines(), 1):
                for w in old:
                    if w in line:
                        hits.append('%s:%d %s' % (os.path.relpath(p, ROOT), i, w))
        for i, line in enumerate(read(skill).splitlines(), 1):
            for w in old:
                if w in line:
                    hits.append('%s:%d %s' % (os.path.relpath(skill, ROOT), i, w))
        self.assertEqual(hits, [])

    def test_no_remote_url_in_kit_code(self):
        """페이지·CSS·JS 에 http(s) 주소가 없다(icons.svg 는 xmlns 이름공간 선언 1줄만 허용)."""
        hits = []
        for dirpath, _, files in os.walk(KIT):
            for f in files:
                if f.endswith(('.html', '.css', '.js', '.json', '.svg')):
                    for i, line in enumerate(read(os.path.join(dirpath, f)).splitlines(), 1):
                        if re.search(r'https?://', line) and 'xmlns="http://www.w3.org/2000/svg"' not in line:
                            hits.append('%s:%d' % (f, i))
        self.assertEqual(hits, [])


if __name__ == '__main__':
    unittest.main()
