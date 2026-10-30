#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ui_check.py — 브라우저 없이 HTML 화면의 구조·접근성·토큰 준수·대비를 점검한다 (표준 라이브러리만, Python 3.9).

  python3 design-kit/ui_check.py http://127.0.0.1:8000/kit.html
  python3 design-kit/ui_check.py http://127.0.0.1:8000/templates/dashboard.html http://127.0.0.1:8000/templates/mobile.html
  python3 design-kit/ui_check.py design-kit/templates/landing.html          # 파일 경로도 된다
  python3 design-kit/ui_check.py URL --tokens design-kit/tokens.css          # 토큰 파일을 직접 지정

검사 항목 (결과 PASS / WARN / FAIL, FAIL 이 하나라도 있으면 exit 1)
  구조   viewport meta · <html lang> · <title> · h1 정확히 1개 · 제목 단계 건너뜀(h2→h4) 없음 · 제목 트리 출력
  접근성 img alt · button/a 텍스트(또는 aria-label) · input/select/textarea 의 label(for·감싸기·aria-label) · table 의 thead · 인라인 svg 의 role/aria
  토큰   raw hex 가 tokens.css 밖(인라인 style·<style>·링크된 다른 CSS)에 쓰였는지 · var(--x) 가 정의돼 있는지
  문구   금지어(lorem·ipsum·미완성 표식) · AI 티(전부 대문자 제목·버튼/링크 꼬리 '→')
  반응형 고정 width ≥ 1000px · min-width ≥ 400px (max-width 는 제외)
  Floor  Hallmark "The Floor" 정적 5규칙 — 모두 WARN, 기준은 .agents/skills/ui-audit/references/hallmark-floor.md
         transition 에 all·width·height·top·left · width/min-width 의 100vw(max-width 는 제외) ·
         같은 선언 블록의 uppercase(또는 small-caps)+양수 letter-spacing · 띄어쓴 가운뎃점(A · B)으로 이은 메타 문자열이
         3개 요소 이상(한국어 나열 '수율·가동률'은 띄지 않아 제외) · .card 안의 .card(.card.flat 안쪽은 허용)
  외부   http(s) 자원(link/script/img/iframe/source, CSS url()) → FAIL, <a href=http> → WARN
  대비   tokens.css 의 글자/배경 쌍 WCAG 상대휘도 대비 ≥ 4.5 PASS / ≥ 3.0 WARN / 미만 FAIL (hex 토큰만 계산)
한계: JS 로 렌더되는 DOM 은 보지 못한다(템플릿의 정적 골격만 검사). 시각 확인은 HUMAN_CHECK 로 보완한다.
"""
import argparse
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
HEX_RE = re.compile(r'(?<![\w-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])')
VAR_USE_RE = re.compile(r'var\(\s*(--[A-Za-z0-9_-]+)')   # 토큰 이름은 ASCII 만(본문의 "var(--토큰)" 같은 설명문은 제외)
VAR_DEF_RE = re.compile(r'(--[A-Za-z0-9_-]+)\s*:')
DECL_BODY_RE = re.compile(r'\{([^{}]*)\}')
WIDTH_RE = re.compile(r'(?<![\w-])(?<!max-)(min-)?width\s*:\s*(\d+(?:\.\d+)?)px', re.I)
URL_RE = re.compile(r'url\(\s*["\']?(https?://[^)"\']+)', re.I)
# Floor 규칙(ui-audit): 선언 블록 단위로 본다. Hallmark sloplint.mjs 의 10a·34·67·63·4 정적 검사와 같은 기준.
CAPS_RE = re.compile(r'text-transform\s*:\s*uppercase|font-variant(?:-caps)?\s*:\s*[^;]*small-caps', re.I)
TRACK_RE = re.compile(r'letter-spacing\s*:\s*\+?(\d*\.?\d+)\s*(?:em|rem|px|ch|%)', re.I)   # 양수만(-.02em 은 제목 자간 조임)
VW_RE = re.compile(r'(?<![\w.-])100vw(?![\w-])', re.I)
RULE_RE = re.compile(r'([^{}]*)\{([^{}]*)\}')            # (선택자, 선언 본문) — 가장 안쪽 블록만
COMMENT_RE = re.compile(r'/\*.*?\*/', re.S)
MIDDOT_RE = re.compile(r'\S\s[·•]\s\S')               # 'A · B' 처럼 띄어쓴 가운뎃점만(한국어 나열 '수율·가동률' 은 제외)
TRANSITION_LAYOUT = ('all', 'width', 'height', 'top', 'left')
# 금지어 — preflight.py 의 자체 스캔에 잡히지 않도록 조각을 이어 붙여 만든다.
BANNED_FAIL = ['lorem', 'ipsum', 'TO' + 'DO', 'FIX' + 'ME', '미' + '구현', 'T' + 'BD', 'place' + 'holder text']
BANNED_WARN = ['여기에 내용', '샘플 텍스트', 'coming soon', 'under construction']
CONTRAST_PAIRS = [
    ('--ink', '--paper'), ('--ink', '--panel'), ('--ink-2', '--panel'), ('--muted', '--panel'), ('--muted', '--paper'),
    ('--ok', '--ok-bg'), ('--warn', '--warn-bg'), ('--bad', '--bad-bg'), ('--info', '--info-bg'), ('--off', '--off-bg'),
    ('--brand-deep', '--brand-soft'), ('--brand-deep', '--panel'), ('--on-brand', '--brand'), ('--on-ink', '--ink'),
]


class Page(HTMLParser):
    """한 페이지의 구조를 모은다. 텍스트는 열려 있는 모든 조상 요소에 누적한다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # [tag, attrs(dict), text_parts(list)]
        self.lang = None
        self.title = ''
        self.viewport = None
        self.headings = []       # (level, text)
        self.imgs = []           # attrs
        self.svgs = []           # attrs
        self.buttons = []        # (attrs, text)
        self.anchors = []        # (attrs, text)
        self.fields = []         # (tag, attrs, wrapped_in_label)
        self.label_for = set()
        self.tables = []         # has_thead
        self.inline_styles = []  # (tag, style)
        self.style_blocks = []
        self.script_blocks = []
        self.stylesheets = []    # href
        self.external = []       # (tag, url)
        self.ext_links = []      # a href http
        self.text_parts = []     # 본문 텍스트(스크립트·스타일 제외)
        self.middot = []         # 띄어쓴 가운뎃점 메타 문자열을 가진 요소(가장 안쪽 1개만)
        self.nested_cards = []   # .card 안의 .card(.flat 제외)
        self._in_raw = None

    def _attrs(self, attrs):
        return {k.lower(): (v if v is not None else '') for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = self._attrs(attrs)
        if tag in ('style', 'script'):
            self._in_raw = tag
            if tag == 'script' and a.get('src', '').startswith(('http://', 'https://')):
                self.external.append((tag, a['src']))
        if tag == 'html':
            self.lang = a.get('lang')
        elif tag == 'meta' and a.get('name', '').lower() == 'viewport':
            self.viewport = a.get('content', '')
        elif tag == 'link':
            href = a.get('href', '')
            if href.startswith(('http://', 'https://')):
                self.external.append((tag, href))
            elif 'stylesheet' in a.get('rel', '').lower():
                self.stylesheets.append(href)
        elif tag in ('img', 'iframe', 'source', 'video', 'audio', 'embed'):
            if a.get('src', '').startswith(('http://', 'https://')):
                self.external.append((tag, a['src']))
            if tag == 'img':
                self.imgs.append(a)
        elif tag == 'svg':
            # 조상이 aria-hidden 이거나 글자가 있는 button/a 안의 장식 svg 는 접근성 이름이 필요 없다
            decorative = any(s[1].get('aria-hidden') == 'true' or s[0] in ('button', 'a') for s in self.stack)
            if not decorative:
                self.svgs.append(a)
        elif tag == 'label' and a.get('for'):
            self.label_for.add(a['for'])
        elif tag in ('input', 'select', 'textarea'):
            wrapped = any(s[0] == 'label' for s in self.stack)
            self.fields.append((tag, a, wrapped))
        elif tag == 'table':
            self.tables.append(False)
        elif tag == 'thead' and self.tables:
            self.tables[-1] = True
        elif tag == 'a' and a.get('href', '').startswith(('http://', 'https://')):
            self.ext_links.append(a['href'])
        if a.get('style'):
            self.inline_styles.append((tag, a['style']))
        classes = a.get('class', '').split()
        if 'card' in classes and 'flat' not in classes and any('card' in s[1].get('class', '').split() for s in self.stack):
            # .card.flat 은 키트가 중첩용으로 둔 변형(kit.html '.card.flat — 링만. 중첩 카드용')이라 제외한다
            self.nested_cards.append('%s.%s' % (tag, '.'.join(classes)[:30]))
        if tag in VOID:
            return
        self.stack.append([tag, a, [], False])   # [태그, 속성, 텍스트 조각, 자손이 가운뎃점 메타로 집계됨]

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ('style', 'script'):
            self._in_raw = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for k in range(len(self.stack) - 1, i - 1, -1):   # 안쪽부터 닫아야 가운뎃점 메타가 조상에 중복 집계되지 않는다
                    self._close(self.stack[k], self.stack[k - 1] if k > 0 else None)
                del self.stack[i:]
                return

    def close(self):
        super().close()
        while self.stack:   # 닫는 태그가 없는 채 끝난 요소도 집계한다
            el = self.stack.pop()
            self._close(el, self.stack[-1] if self.stack else None)

    def _close(self, el, parent=None):
        tag, a, parts, seen = el
        text = re.sub(r'\s+', ' ', ''.join(parts)).strip()
        if not seen and tag != 'title' and MIDDOT_RE.search(text):
            cls = a.get('class', '').split()
            self.middot.append('%s%s: %s' % (tag, ('.' + cls[0]) if cls else '', text[:30]))
            seen = True
        if seen and parent is not None:
            parent[3] = True
        if tag == 'title':
            self.title = text
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.headings.append((int(tag[1]), text))
        elif tag == 'button':
            self.buttons.append((a, text))
        elif tag == 'a':
            self.anchors.append((a, text))

    def handle_data(self, data):
        if self._in_raw == 'style':
            self.style_blocks.append(data)
            return
        if self._in_raw == 'script':
            self.script_blocks.append(data)
            return
        self.text_parts.append(data)
        for el in self.stack:
            el[2].append(data)


# ---------------------------------------------------------------- 입력 읽기
def read_target(target, timeout=5):
    """URL 또는 파일 경로 → (텍스트, base). base 는 상대 경로 해석용(URL 이면 URL, 파일이면 폴더)."""
    if target.startswith(('http://', 'https://')):
        with urllib.request.urlopen(target, timeout=timeout) as r:
            return r.read().decode('utf-8', 'replace'), target
    with open(target, 'r', encoding='utf-8', errors='replace') as fh:
        return fh.read(), os.path.dirname(os.path.abspath(target))


def read_relative(base, href, timeout=5):
    """페이지 기준 상대 경로의 CSS 를 읽는다. 못 읽으면 None."""
    try:
        if base.startswith(('http://', 'https://')):
            url = urllib.parse.urljoin(base, href)
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read().decode('utf-8', 'replace')
        path = os.path.normpath(os.path.join(base, href))
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            return fh.read()
    except Exception:  # noqa
        return None


# ---------------------------------------------------------------- 대비 계산 (WCAG 2.x 상대휘도)
def hex_to_rgb(h):
    h = h.lstrip('#')
    if len(h) in (3, 4):
        h = ''.join(c * 2 for c in h[:3])
    h = h[:6]
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def luminance(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(hex_a, hex_b):
    la, lb = luminance(hex_to_rgb(hex_a)), luminance(hex_to_rgb(hex_b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def token_values(css_text):
    """tokens.css 에서 --이름: 값 을 뽑는다(값은 ; 까지)."""
    out = {}
    for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;]+);', css_text):
        out[m.group(1)] = m.group(2).strip()
    return out


def css_blocks(page, other_css):
    """Floor 규칙용 (선택자, 선언 본문) 목록: 인라인 style 각각 + <style>·링크 CSS(tokens.css 제외)의 { } 블록 각각. 주석은 지운다."""
    out = [('<%s style>' % tag, s) for tag, s in page.inline_styles]
    for name, txt in [('<style>', b) for b in page.style_blocks] + list(other_css):
        for m in RULE_RE.finditer(COMMENT_RE.sub(' ', txt)):
            sel = m.group(1).strip().split('\n')[-1].strip()   # 직전 } 이후의 선택자만
            out.append(('%s %s' % (name, sel[-40:]), m.group(2)))
    return out


def declarations(body):
    """선언 본문 → (속성 소문자, 값). 첫 ':' 에서만 나눈다(url(http://…) 보호)."""
    for d in body.split(';'):
        if ':' in d:
            prop, val = d.split(':', 1)
            yield prop.strip().lower(), val.strip()


# ---------------------------------------------------------------- 검사
def check_page(target, tokens_override=None):
    results = []

    def rec(name, status, detail=''):
        results.append((name, status, detail))

    try:
        html_text, base = read_target(target)
    except Exception as e:  # noqa
        rec('fetch', 'FAIL', '%s 를 읽지 못함: %s' % (target, e))
        return results, []
    p = Page()
    p.feed(html_text)
    p.close()

    # --- 구조
    rec('viewport meta', 'PASS' if p.viewport and 'width=device-width' in p.viewport else 'FAIL', p.viewport or '없음')
    rec('html lang', 'PASS' if p.lang else 'FAIL', p.lang or '없음 (lang="ko" 권장)')
    rec('title', 'PASS' if p.title else 'FAIL', p.title or '비어 있음')
    h1s = [t for lv, t in p.headings if lv == 1]
    rec('h1 exactly one', 'PASS' if len(h1s) == 1 else 'FAIL', '%d개: %s' % (len(h1s), ' | '.join(h1s[:3])))
    skips, prev = [], 0
    for lv, t in p.headings:
        if prev and lv > prev + 1:
            skips.append('h%d→h%d(%s)' % (prev, lv, t[:20]))
        prev = lv
    rec('heading no skip', 'PASS' if not skips else 'WARN', ', '.join(skips[:3]) if skips else '%d개 제목' % len(p.headings))
    empty_h = [lv for lv, t in p.headings if not t]
    if empty_h:
        rec('heading empty', 'WARN', 'JS 로 채우는 빈 제목 %d개 (렌더 후 HUMAN_CHECK)' % len(empty_h))
    caps = []
    for lv, t in p.headings:
        words = re.findall(r'[A-Za-z]{2,}', t)
        # 라틴 단어 2개 이상이 전부 대문자이고 한글이 없으면 '추적 대문자 라벨' 로 본다 (KPI·SPC 같은 약어 1개는 제외)
        if len(words) >= 2 and all(w.isupper() for w in words) and not re.search(r'[가-힣]', t):
            caps.append(t)
    rec('no all-caps headings', 'PASS' if not caps else 'WARN', ', '.join(caps[:3]) if caps else 'AI 티(대문자 추적 라벨) 없음')

    # --- 접근성
    noalt = [a.get('src', '')[:40] for a in p.imgs if 'alt' not in a]
    rec('img alt', 'PASS' if not noalt else 'FAIL', ', '.join(noalt[:3]) if noalt else '%d개 img' % len(p.imgs))
    bad_svg = [a for a in p.svgs if a.get('aria-hidden') != 'true' and not a.get('aria-label') and a.get('role') != 'img']
    rec('svg role/aria', 'PASS' if not bad_svg else 'WARN', '%d개 svg 에 aria-hidden 도 aria-label 도 없음' % len(bad_svg) if bad_svg else '%d개 svg' % len(p.svgs))
    nobtn = [a.get('id') or a.get('class', '')[:20] for a, t in p.buttons if not t and not a.get('aria-label')]
    rec('button text', 'PASS' if not nobtn else 'FAIL', ', '.join(nobtn[:3]) if nobtn else '%d개 button' % len(p.buttons))
    noa = [a.get('href', '')[:30] for a, t in p.anchors if not t and not a.get('aria-label')]
    rec('a text', 'PASS' if not noa else 'FAIL', ', '.join(noa[:3]) if noa else '%d개 a' % len(p.anchors))
    nohref = [t[:20] for a, t in p.anchors if 'href' not in a]
    if nohref:
        rec('a href', 'WARN', 'href 없는 a %d개 (버튼이면 <button>)' % len(nohref))
    arrow = [t for a, t in p.buttons + p.anchors if t.rstrip().endswith(('→', '->', '>>'))]
    rec("no '→' tail", 'PASS' if not arrow else 'WARN', ', '.join(arrow[:3]) if arrow else "AI 티('→' 꼬리) 없음")
    unlabeled = []
    for tag, a, wrapped in p.fields:
        typ = a.get('type', 'text').lower()
        if tag == 'input' and typ in ('hidden', 'submit', 'button', 'reset', 'image'):
            continue
        ok = wrapped or (a.get('id') and a['id'] in p.label_for) or a.get('aria-label') or a.get('aria-labelledby') or a.get('title')
        if not ok:
            unlabeled.append('%s#%s' % (tag, a.get('id') or a.get('name') or '?'))
    rec('input label', 'PASS' if not unlabeled else 'FAIL', ', '.join(unlabeled[:4]) if unlabeled else '%d개 필드' % len(p.fields))
    nothead = sum(1 for t in p.tables if not t)
    rec('table thead', 'PASS' if not nothead else 'FAIL', '%d개 table 에 thead 없음' % nothead if nothead else '%d개 table' % len(p.tables))

    # --- CSS 수집: 인라인 style, <style>, 링크된 CSS(tokens.css 분리)
    tokens_css = None
    other_css = []   # (이름, 텍스트)
    for href in p.stylesheets:
        txt = read_relative(base, href)
        name = os.path.basename(href)
        if txt is None:
            rec('css load', 'FAIL', '%s 를 읽지 못함' % href)
            continue
        if name == 'tokens.css':
            tokens_css = txt
        else:
            other_css.append((name, txt))
    if tokens_override:
        with open(tokens_override, 'r', encoding='utf-8', errors='replace') as fh:
            tokens_css = fh.read()
    if tokens_css is None:
        rec('tokens.css linked', 'WARN', 'tokens.css 가 링크돼 있지 않음 (토큰·대비 검사 생략)')
    inline_decl = '\n'.join(s for _, s in p.inline_styles)
    style_decl = '\n'.join(' '.join(DECL_BODY_RE.findall(b)) for b in p.style_blocks)
    page_decl = inline_decl + '\n' + style_decl
    hexes = sorted(set(HEX_RE.findall(page_decl)))
    rec('no raw hex in page', 'PASS' if not hexes else 'FAIL', ', '.join(hexes[:6]) if hexes else 'inline style·<style> 에 hex 없음 (var 만 사용)')
    css_hex = []
    for name, txt in other_css:
        body = ' '.join(DECL_BODY_RE.findall(txt))
        hs = sorted(set(HEX_RE.findall(body)))
        if hs:
            css_hex.append('%s: %s' % (name, ', '.join(hs[:4])))
    rec('no raw hex in linked css', 'PASS' if not css_hex else 'WARN', ' / '.join(css_hex[:3]) if css_hex else '%d개 CSS 모두 var 만 사용' % len(other_css))
    defined = set(VAR_DEF_RE.findall((tokens_css or '') + '\n' + '\n'.join(t for _, t in other_css) + '\n' + '\n'.join(p.style_blocks) + '\n' + inline_decl))
    used = set(VAR_USE_RE.findall(html_text)) | set(VAR_USE_RE.findall('\n'.join(t for _, t in other_css)))
    missing = sorted(used - defined)
    rec('var() defined', 'PASS' if not missing else 'FAIL', ', '.join(missing[:6]) if missing else '%d개 토큰 사용, 미정의 0' % len(used))

    # --- 문구
    body_text = ' '.join(p.text_parts)
    low = body_text.lower()
    hits = [w for w in BANNED_FAIL if w.lower() in low]
    rec('banned words', 'PASS' if not hits else 'FAIL', ', '.join(hits) if hits else '없음')
    whits = [w for w in BANNED_WARN if w.lower() in low]
    if whits:
        rec('filler words', 'WARN', ', '.join(whits))
    # 선언 본문만 모은다(@media 프렐류드의 min-width, 선택자의 #id 가 섞이지 않게)
    all_css = page_decl + '\n' + '\n'.join(' '.join(DECL_BODY_RE.findall(t)) for _, t in other_css)

    # --- 반응형
    wide = ['%s%spx' % (m.group(1) or '', m.group(2)) for m in WIDTH_RE.finditer(all_css)
            if (m.group(1) and float(m.group(2)) >= 400) or (not m.group(1) and float(m.group(2)) >= 1000)]
    rec('no fixed/min width', 'PASS' if not wide else 'WARN', ', '.join(sorted(set(wide))[:5]) if wide else 'width≥1000 · min-width≥400 없음')

    # --- Floor (Hallmark The Floor 정적 5규칙, 모두 WARN — .agents/skills/ui-audit/references/hallmark-floor.md)
    trans, vw, caps = [], [], []
    for sel, body in css_blocks(p, other_css):
        for prop, val in declarations(body):
            if prop in ('transition', 'transition-property'):
                for item in val.split(','):
                    tok = item.strip().split()
                    if tok and tok[0].lower() in TRANSITION_LAYOUT:
                        trans.append('%s {%s: %s}' % (sel, prop, item.strip()[:24]))
            elif prop in ('width', 'min-width', 'inline-size', 'min-inline-size') and VW_RE.search(val):
                vw.append('%s {%s: %s}' % (sel, prop, val[:24]))
        m = TRACK_RE.search(body)
        if CAPS_RE.search(body) and m and float(m.group(1)) > 0:
            caps.append(sel)
    rec('no transition all', 'PASS' if not trans else 'WARN',
        ', '.join(trans[:3]) if trans else 'transition 에 all·width·height·top·left 없음 (시간만 적은 transition: .25s 는 보지 않음)')
    rec('no 100vw width', 'PASS' if not vw else 'WARN', ', '.join(vw[:3]) if vw else 'width/min-width 에 100vw 없음 (max-width 는 제외)')
    rec('uppercase tracked label', 'PASS' if not caps else 'WARN',
        (', '.join(caps[:3]) + ' — 같은 블록에 uppercase/small-caps + 양수 letter-spacing (AI 티: 라벨은 본문 서체·문장체)') if caps
        else '같은 블록의 uppercase + letter-spacing 없음')
    rec('no middot meta', 'PASS' if len(p.middot) < 3 else 'WARN',
        '띄어쓴 가운뎃점(A · B) 메타 문자열 %d개 요소%s' % (len(p.middot), (': ' + ' | '.join(p.middot[:3])) if p.middot else " (한국어 나열 '수율·가동률' 은 제외)"))
    rec('no card in card', 'PASS' if not p.nested_cards else 'WARN',
        ('.card 안에 .card %d개: %s' % (len(p.nested_cards), ', '.join(p.nested_cards[:3]))) if p.nested_cards else '.card 중첩 없음 (.card.flat 안쪽은 허용)')

    # --- 외부 자원
    ext = ['%s:%s' % (t, u[:50]) for t, u in p.external] + ['css:%s' % u[:50] for u in URL_RE.findall(all_css)]
    rec('no external asset', 'PASS' if not ext else 'FAIL', ', '.join(ext[:3]) if ext else '외부 http(s) 자원 없음')
    if p.ext_links:
        rec('external links', 'WARN', '%d개 <a href=http> (시험장에서 열리지 않음)' % len(p.ext_links))

    # --- 대비
    if tokens_css:
        vals = token_values(tokens_css)
        worst, statuses, details = None, [], []
        for fg, bg in CONTRAST_PAIRS:
            a, b = vals.get(fg, ''), vals.get(bg, '')
            if not (HEX_RE.fullmatch(a) and HEX_RE.fullmatch(b)):
                details.append('%s/%s 생략(hex 아님)' % (fg, bg))
                continue
            c = contrast(a, b)
            st = 'PASS' if c >= 4.5 else 'WARN' if c >= 3.0 else 'FAIL'
            statuses.append(st)
            if st != 'PASS':
                details.append('%s/%s %.2f %s' % (fg, bg, c, st))
            if worst is None or c < worst[0]:
                worst = (c, fg, bg)
        status = 'FAIL' if 'FAIL' in statuses else 'WARN' if 'WARN' in statuses else 'PASS'
        rec('contrast (tokens)', status, ('최저 %.2f %s/%s' % worst if worst else '계산 가능한 쌍 없음') + (' · ' + ', '.join(details[:4]) if details else ' · 전 쌍 4.5:1 이상'))

    tree = ['%s%s %s' % ('  ' * (lv - 1), 'h%d' % lv, t or '(JS 렌더)') for lv, t in p.headings]
    return results, tree


def main():
    ap = argparse.ArgumentParser(description='HTML 화면 점검 (표준 라이브러리)')
    ap.add_argument('targets', nargs='+', help='URL 또는 HTML 파일 경로')
    ap.add_argument('--tokens', default=None, help='tokens.css 경로를 직접 지정')
    ap.add_argument('--no-tree', action='store_true', help='제목 트리 출력 생략')
    a = ap.parse_args()
    any_fail = False
    for t in a.targets:
        results, tree = check_page(t, a.tokens)
        print('=== %s' % t)
        print('%-28s %-5s %s' % ('CHECK', 'RESULT', 'DETAIL'))
        for n, st, d in results:
            print('%-28s %-5s %s' % (n, st, d))
        n_fail = sum(1 for r in results if r[1] == 'FAIL')
        n_warn = sum(1 for r in results if r[1] == 'WARN')
        print('RESULT: %d PASS / %d WARN / %d FAIL' % (len(results) - n_fail - n_warn, n_warn, n_fail))
        if tree and not a.no_tree:
            print('--- heading tree')
            print('\n'.join(tree))
        print()
        any_fail = any_fail or n_fail > 0
    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
