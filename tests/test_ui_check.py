# -*- coding: utf-8 -*-
"""design-kit/ui_check.py 의 Floor 규칙 5개(WARN) 테스트 (unittest, Python 3.9).
실행: python3 -m unittest tests.test_ui_check -v
규칙마다 양성(걸려야 함)·음성(걸리면 안 됨) HTML 조각 + 키트 5페이지(kit.html·templates 4종)를 파일 경로 모드로 FAIL 0 · Floor 5규칙 PASS.
ui_check.py 는 'design-kit'(하이픈) 폴더에 있어 import 문으로 못 읽으므로 importlib 로 파일에서 읽는다.
"""
import importlib.util
import os
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
KIT = os.path.join(ROOT, 'design-kit')
PAGES = ['kit.html', os.path.join('templates', 'dashboard.html'), os.path.join('templates', 'console.html'),
         os.path.join('templates', 'landing.html'), os.path.join('templates', 'mobile.html')]
FLOOR = ['no transition all', 'no 100vw width', 'uppercase tracked label', 'no middot meta', 'no card in card']


def load_ui_check():
    spec = importlib.util.spec_from_file_location('ui_check', os.path.join(KIT, 'ui_check.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


UI = load_ui_check()

SKELETON = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"><title>검사용</title>'
            '<style>%s</style></head><body><h1>제목</h1>%s</body></html>')


def run_fragment(css='', body=''):
    """CSS·본문 조각을 최소 페이지에 넣어 파일 모드로 검사하고 {검사 이름: (상태, 상세)} 를 돌려준다."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, 'page.html')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(SKELETON % (css, body))
        results, _ = UI.check_page(path)
    return {name: (status, detail) for name, status, detail in results}


class FloorBase(unittest.TestCase):
    def assertFloor(self, name, expected, css='', body=''):
        got = run_fragment(css, body)
        self.assertIn(name, got, '검사 %s 가 결과에 없음' % name)
        self.assertEqual(got[name][0], expected, '%s: %s' % (name, got[name][1]))


# ---------------------------------------------------------------- 규칙 1: transition 에 all·width·height·top·left
class TestTransitionAll(FloorBase):
    NAME = 'no transition all'

    def test_transition_all_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', css='.a { transition: all .2s ease; }')

    def test_transition_property_all_and_layout_props_are_warned(self):
        self.assertFloor(self.NAME, 'WARN', css='.a { transition-property: all; }')
        self.assertFloor(self.NAME, 'WARN', css='.b { transition: opacity .3s, width .3s; }')
        self.assertFloor(self.NAME, 'WARN', body='<div style="transition: height .3s">x</div>')

    def test_transform_opacity_transition_passes(self):
        self.assertFloor(self.NAME, 'PASS', css='.a { transition: transform .25s, box-shadow .25s; } .b { transition: none; }')

    def test_max_height_is_not_height(self):
        self.assertFloor(self.NAME, 'PASS', css='.a { transition: max-height .3s; }')


# ---------------------------------------------------------------- 규칙 2: width/min-width 의 100vw
class TestViewportWidth(FloorBase):
    NAME = 'no 100vw width'

    def test_width_100vw_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', css='.hero { width: 100vw; }')

    def test_min_width_calc_100vw_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', css='.band { min-width: calc(100vw - 10px); }')

    def test_max_width_100vw_passes(self):
        """max-width 는 뷰포트보다 넓어질 수 없어 가로 스크롤을 만들지 않는다(키트 .toast 가 쓴다)."""
        self.assertFloor(self.NAME, 'PASS', css='.toast { max-width: calc(100vw - 40px); width: 100%; }')


# ---------------------------------------------------------------- 규칙 3: 같은 블록의 uppercase + 양수 letter-spacing
class TestUppercaseTrackedLabel(FloorBase):
    NAME = 'uppercase tracked label'

    def test_uppercase_and_tracking_in_one_block_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', css='.label { text-transform: uppercase; letter-spacing: .08em; }')

    def test_inline_style_block_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', body='<span style="letter-spacing:1px;text-transform:uppercase">tag</span>')

    def test_small_caps_counts_as_caps(self):
        self.assertFloor(self.NAME, 'WARN', css='.cap { font-variant: small-caps; letter-spacing: .1em; }')

    def test_separate_blocks_pass(self):
        """uppercase 와 letter-spacing 이 다른 블록이면 추적 라벨이 아니다(예전 느슨한 검사의 오탐)."""
        self.assertFloor(self.NAME, 'PASS', css='.a { text-transform: uppercase; } .b { letter-spacing: .06em; }')

    def test_negative_or_zero_tracking_passes(self):
        self.assertFloor(self.NAME, 'PASS', css='.h { text-transform: uppercase; letter-spacing: -.02em; } .v { letter-spacing: 0; }')


# ---------------------------------------------------------------- 규칙 4: 띄어쓴 가운뎃점(A · B) 메타 문자열 3개 요소 이상
class TestMiddotMeta(FloorBase):
    NAME = 'no middot meta'
    META = '<p class="meta">5분 전 · 1월 12일 · 설계</p>'

    def test_three_elements_are_warned(self):
        self.assertFloor(self.NAME, 'WARN', body=self.META * 3)

    def test_two_elements_pass(self):
        self.assertFloor(self.NAME, 'PASS', body=self.META * 2)

    def test_korean_unspaced_list_passes(self):
        """한국어 가운뎃점 나열(수율·가동률)은 띄어 쓰지 않으므로 메타 문자열이 아니다."""
        self.assertFloor(self.NAME, 'PASS', body='<p>수율·가동률·WIP</p>' * 4)

    def test_nested_element_counts_once(self):
        """<div><span>5분</span> · <span>설계</span></div> 는 가장 안쪽 일치 1개로 센다(조상 중복 집계 없음)."""
        body = '<section><div class="meta"><span>5분 전</span> · <span>설계</span></div></section>' * 3
        got = run_fragment(body=body)
        self.assertEqual(got[self.NAME][0], 'WARN', got[self.NAME][1])
        self.assertIn('3개', got[self.NAME][1])


# ---------------------------------------------------------------- 규칙 5: .card 안의 .card
class TestCardInCard(FloorBase):
    NAME = 'no card in card'

    def test_nested_card_is_warned(self):
        self.assertFloor(self.NAME, 'WARN', body='<div class="card"><h2>바깥</h2><div class="card">안쪽</div></div>')

    def test_sibling_cards_pass(self):
        self.assertFloor(self.NAME, 'PASS', body='<div class="grid"><div class="card">a</div><div class="card">b</div></div>')

    def test_flat_inner_card_is_allowed(self):
        """kit.html 의 .card.flat 은 '중첩 카드용'(링만)이라 허용한다."""
        self.assertFloor(self.NAME, 'PASS', body='<div class="card"><div class="card flat">안쪽</div></div>')

    def test_cardlike_names_are_not_card(self):
        self.assertFloor(self.NAME, 'PASS', body='<div class="bezel"><div class="core"><div class="card">x</div></div></div>'
                                                 '<div class="cards"><div class="card">y</div></div>')


# ---------------------------------------------------------------- 키트 5페이지 (템플릿은 수정하지 않았다)
class TestKitPagesStayClean(unittest.TestCase):
    def test_kit_and_templates_have_zero_fail(self):
        for page in PAGES:
            results, _ = UI.check_page(os.path.join(KIT, page))
            fails = [r for r in results if r[1] == 'FAIL']
            self.assertEqual(fails, [], '%s: %s' % (page, fails))

    def test_floor_rules_pass_on_kit_pages(self):
        for page in PAGES:
            got = {n: (s, d) for n, s, d in UI.check_page(os.path.join(KIT, page))[0]}
            for name in FLOOR:
                self.assertIn(name, got, '%s: %s 없음' % (page, name))
                self.assertEqual(got[name][0], 'PASS', '%s: %s %s' % (page, name, got[name][1]))

    def test_existing_fail_rule_still_fires(self):
        """회귀: 기존 FAIL 규칙(raw hex)이 Floor 추가 뒤에도 잡힌다."""
        got = run_fragment(css='.a { color: #123456; }')
        self.assertEqual(got['no raw hex in page'][0], 'FAIL')


if __name__ == '__main__':
    unittest.main()
