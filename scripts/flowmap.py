#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flowmap.py — docs/flow.json(단계·입출력·규칙·발동 건수·결정·검증) → out/report.html 1파일 (표준 라이브러리만, Python 3.9)

  python3 scripts/flowmap.py                                        # docs/flow.json → out/report.html
  python3 scripts/flowmap.py --spec docs/flow.json --out out/report.html
  python3 scripts/flowmap.py --check                                # 스펙 검증만 (파일을 만들지 않음)
  python3 scripts/flowmap.py --spec docs/flow.example.json --out .tmp/report.html   # 예시로 모양 보기

내용: 인라인 SVG 파이프라인(640px 이하 세로 배치) · 합계 보존 띠(입력 = 통과 + 사유별 제외) · 규칙표(발동 건수·테스트)
      · 결정 목록 · 검증 결과 배지(PASS/FAIL/NOT_RUN/HUMAN_CHECK) · 링크. 숫자는 전부 스펙에서 읽고 암산하지 않는다.
exit 0 생성 성공 / 1 스펙 오류 또는 합계 불일치(불일치는 'FAIL: 합계 불일치' 를 띠에 찍은 HTML 을 만든 뒤 1) / 2 스펙 파일 없음
CSS 는 design-kit/tokens.css 값을 읽어 rgb() 로 바꿔 인라인 복사한다(외부 파일 참조 0 → 미리보기·제출물에서 단독으로 열림,
ui_check 의 raw hex 검사도 통과). 모든 문자열은 html.escape. 생성 시각을 넣지 않아 같은 스펙이면 같은 HTML 이 나온다.
미리보기(사람이 다른 터미널에서 실행): python3 design-kit/serve.py $PORT --dir out --index report.html  → 미리보기 탭에서 /report.html
"""
import argparse
import html
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUSES = ('PASS', 'FAIL', 'NOT_RUN', 'HUMAN_CHECK')
STATUS_CLASS = {'PASS': 'ok', 'FAIL': 'bad', 'NOT_RUN': 'off', 'HUMAN_CHECK': 'warn'}
HEX_RE = re.compile(r'(?<![\w-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])')
TOKEN_RE = re.compile(r'(--[\w-]+)\s*:\s*([^;]+);')
EXCL_CLASSES = ('x0', 'x1', 'x2', 'x3', 'x4')   # 제외 사유 색 순환: bad → warn → off → info → brand-deep

# design-kit/tokens.css 를 못 읽을 때 쓰는 사본(2026-10-28 값, hex 는 rgb() 로 변환). 페이지 CSS 가 쓰는 토큰은 전부 여기 있어야 한다.
FALLBACK_TOKENS = [
    ('--paper', 'rgb(247, 248, 245)'), ('--panel', 'rgb(255, 255, 255)'), ('--ink', 'rgb(28, 36, 32)'),
    ('--ink-2', 'rgb(67, 77, 71)'), ('--muted', 'rgb(95, 105, 99)'), ('--line', 'rgb(227, 232, 227)'),
    ('--line-strong', 'rgb(207, 214, 207)'), ('--brand', 'rgb(11, 122, 83)'), ('--brand-rgb', '11, 122, 83'),
    ('--brand-deep', 'rgb(8, 92, 63)'), ('--brand-soft', 'rgb(228, 244, 236)'),
    ('--ok', 'rgb(21, 128, 61)'), ('--ok-bg', 'rgb(236, 253, 243)'), ('--warn', 'rgb(180, 83, 9)'), ('--warn-bg', 'rgb(255, 247, 230)'),
    ('--bad', 'rgb(185, 28, 28)'), ('--bad-bg', 'rgb(254, 242, 242)'), ('--info', 'rgb(29, 78, 216)'), ('--info-bg', 'rgb(239, 246, 255)'),
    ('--off', 'rgb(91, 100, 112)'), ('--off-bg', 'rgb(241, 243, 245)'),
    ('--r-sm', '8px'), ('--r-md', '12px'), ('--r-lg', '18px'), ('--r-pill', '999px'),
    ('--shadow-1', '0 1px 2px rgba(20, 40, 30, .04), 0 8px 24px -12px rgba(20, 40, 30, .14)'),
    ('--brand-ring', 'rgba(var(--brand-rgb), .10)'), ('--ring', '0 0 0 1px var(--brand-ring)'),
    ('--s-1', '4px'), ('--s-2', '8px'), ('--s-3', '12px'), ('--s-4', '16px'), ('--s-5', '24px'), ('--s-6', '32px'), ('--s-7', '48px'), ('--s-8', '64px'),
    ('--font', '-apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", Roboto, Helvetica, Arial, sans-serif'),
    ('--mono', 'ui-monospace, SFMono-Regular, Menlo, Consolas, "D2Coding", monospace'),
    ('--surface-2', 'rgb(250, 251, 249)'), ('--hover', 'rgb(243, 246, 243)'), ('--focus', 'rgba(var(--brand-rgb), .35)'),
    ('--glow-1', 'rgba(var(--brand-rgb), .10)'), ('--glow-2', 'rgba(120, 170, 60, .08)'),
    ('--warn-line', 'rgba(180, 83, 9, .25)'), ('--bad-line', 'rgba(185, 28, 28, .25)'), ('--ok-line', 'rgba(21, 128, 61, .25)'), ('--info-line', 'rgba(29, 78, 216, .25)'),
]

# 페이지 CSS: raw hex 0, var() 만. 고정 width ≥1000px·min-width ≥400px 없음(ui_check·smoke_web 규칙).
PAGE_CSS = """
*, *::before, *::after { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--paper); color: var(--ink); font: 14px/1.55 var(--font); word-break: keep-all; overflow-wrap: anywhere;
  background-image: radial-gradient(58% 44% at 82% -4%, var(--glow-1), transparent 60%), radial-gradient(46% 40% at 4% 6%, var(--glow-2), transparent 62%);
  background-repeat: no-repeat; min-height: 100vh; }
a { color: var(--brand-deep); text-decoration-thickness: 1px; text-underline-offset: 2px; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.container { max-width: 1120px; margin: 0 auto; padding: 0 var(--s-4) var(--s-8); }
.top { padding: var(--s-6) 0 var(--s-2); }
h1 { font-size: clamp(24px, 4vw, 34px); font-weight: 800; line-height: 1.1; letter-spacing: -.02em; margin: 0 0 var(--s-2); }
h2 { font-size: 20px; font-weight: 800; letter-spacing: -.02em; line-height: 1.2; margin: 0 0 var(--s-2); display: flex; align-items: center; gap: var(--s-3); }
h2::before { content: ""; width: 6px; height: 22px; border-radius: var(--r-pill); background: linear-gradient(var(--brand), var(--brand-deep)); flex: none; }
.section { margin-top: var(--s-6); }
.why { font-size: 13px; color: var(--muted); padding-left: 18px; margin: 0 0 var(--s-3); max-width: 720px; }
.meta { font-size: 12px; color: var(--muted); margin: 0; }
.num { font-variant-numeric: tabular-nums; }
.id { font-family: var(--mono); font-size: 12px; }
.card { background: var(--panel); border-radius: var(--r-lg); box-shadow: var(--ring), var(--shadow-1); padding: var(--s-4); }
.kpi { display: grid; gap: var(--s-3); grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-top: var(--s-4); }
.kpi .card { display: grid; gap: 4px; padding: 14px 16px; }
.kpi .label { font-size: 12px; color: var(--muted); }
.kpi .value { font-size: 26px; font-weight: 800; letter-spacing: -.02em; font-variant-numeric: tabular-nums; line-height: 1.1; }
.kpi .value small { font-size: 12px; font-weight: 600; color: var(--muted); margin-left: 2px; letter-spacing: 0; }
.badge { display: inline-flex; align-items: center; gap: 6px; height: 22px; padding: 0 9px; border-radius: var(--r-pill); font-size: 11px; font-weight: 700; white-space: nowrap; background: var(--off-bg); color: var(--off); line-height: 1; }
.badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
.badge.ok { background: var(--ok-bg); color: var(--ok); }
.badge.warn { background: var(--warn-bg); color: var(--warn); }
.badge.bad { background: var(--bad-bg); color: var(--bad); }
.badge.info { background: var(--info-bg); color: var(--info); }
.badge.off { background: var(--off-bg); color: var(--off); }
.table-wrap { overflow-x: auto; border-radius: var(--r-md); box-shadow: var(--ring); background: var(--panel); }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { background: var(--surface-2); text-align: left; font-weight: 600; color: var(--ink-2); height: 40px; padding: 0 var(--s-3); border-bottom: 1px solid var(--line); white-space: nowrap; }
td { padding: 10px var(--s-3); border-bottom: 1px solid var(--line); vertical-align: top; overflow-wrap: normal; }
td:not(.num):not(.id) { min-width: 140px; }
tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: var(--hover); }
tbody tr.row-warn { background: var(--warn-bg); }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
td.id { white-space: nowrap; }
tfoot td { font-weight: 700; background: var(--surface-2); }
.banner { border-radius: var(--r-md); padding: var(--s-3) var(--s-4); font-size: 13px; background: var(--info-bg); color: var(--info); border: 1px solid var(--info-line); margin-bottom: var(--s-3); }
.banner.ok { background: var(--ok-bg); color: var(--ok); border-color: var(--ok-line); }
.banner.bad { background: var(--bad-bg); color: var(--bad); border-color: var(--bad-line); font-weight: 700; }
.pipe { width: 100%; height: auto; display: block; }
.pipe rect { fill: var(--panel); stroke: var(--line-strong); stroke-width: 1.5; }
.pipe text { font-family: var(--font); fill: var(--ink); }
.pipe .s-id { font-size: 11px; fill: var(--muted); font-family: var(--mono); }
.pipe .s-name { font-size: 15px; font-weight: 700; }
.pipe .s-meta { font-size: 12px; fill: var(--ink-2); }
.pipe .edge { stroke: var(--line-strong); stroke-width: 2; fill: none; }
.pipe .arrow { fill: var(--line-strong); }
.pipe.v { display: none; }
.band { display: flex; height: 28px; border-radius: var(--r-pill); overflow: hidden; box-shadow: var(--ring); background: var(--off-bg); }
.band .seg { display: block; min-width: 3px; height: 100%; }
.band.fail { outline: 3px solid var(--bad); outline-offset: 2px; }
.seg-pass { background: var(--ok); }
.seg-x0 { background: var(--bad); }
.seg-x1 { background: var(--warn); }
.seg-x2 { background: var(--off); }
.seg-x3 { background: var(--info); }
.seg-x4 { background: var(--brand-deep); }
.legend { display: flex; gap: var(--s-2) var(--s-4); flex-wrap: wrap; font-size: 12px; color: var(--ink-2); margin-top: var(--s-3); }
.legend .sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.links { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--s-2); }
.links li { display: flex; gap: var(--s-3); align-items: baseline; flex-wrap: wrap; }
.foot { margin-top: var(--s-7); }
@media (max-width: 640px) {
  .container { padding: 0 var(--s-3) var(--s-7); }
  .section { margin-top: var(--s-5); }
  .pipe.h { display: none; }
  .pipe.v { display: block; max-width: 320px; margin: 0 auto; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""


# ---------------------------------------------------------------- 공용
def err(msg):
    print(msg, file=sys.stderr)


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(n):
    return '{:,}'.format(int(n))


def clip(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + '…'


def hex_to_rgb(h):
    """'#rrggbb' / '#rgb' / '#rrggbbaa' → 'rgb(r, g, b)' 또는 'rgba(...)'. 단독 HTML 에 raw hex 를 남기지 않기 위한 변환."""
    s = h.lstrip('#')
    if len(s) in (3, 4):
        s = ''.join(c * 2 for c in s)
    r, g, b = (int(s[i:i + 2], 16) for i in (0, 2, 4))
    if len(s) == 8:
        return 'rgba(%d, %d, %d, %.3g)' % (r, g, b, int(s[6:8], 16) / 255.0)
    return 'rgb(%d, %d, %d)' % (r, g, b)


def read_tokens():
    """design-kit/tokens.css 의 --이름: 값 목록. hex 는 rgb() 로. 파일이 없으면 FALLBACK_TOKENS."""
    for base in (ROOT, os.getcwd()):
        path = os.path.join(base, 'design-kit', 'tokens.css')
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            css = re.sub(r'/\*.*?\*/', '', fh.read(), flags=re.S)
        toks = [(m.group(1), HEX_RE.sub(lambda h: hex_to_rgb(h.group(0)), ' '.join(m.group(2).split())))
                for m in TOKEN_RE.finditer(css)]
        if toks:
            return toks
    return list(FALLBACK_TOKENS)


# ---------------------------------------------------------------- 스펙 읽기·검증
def load_spec(path):
    """(spec, None) / (None, 'missing') / (None, '오류 메시지')."""
    if not os.path.exists(path):
        return None, 'missing'
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh), None
    except ValueError as e:
        return None, 'JSON 파싱 실패: %s' % e
    except OSError as e:
        return None, '읽기 실패: %s' % e


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def validate(spec):
    """구조 오류 목록(비어 있으면 유효). 합계 보존은 conservation_delta 가 따로 본다."""
    errs = []
    if not isinstance(spec, dict):
        return ['최상위는 객체({})여야 함']

    def need_str(obj, key, where, required=True):
        v = obj.get(key)
        if v is None:
            if required:
                errs.append('%s.%s 없음' % (where, key))
            return ''
        if not isinstance(v, str):
            errs.append('%s.%s 문자열이어야 함 (값: %r)' % (where, key, v))
            return ''
        return v

    def need_list(obj, key, where, required=False):
        v = obj.get(key)
        if v is None:
            if required:
                errs.append('%s.%s 없음 (배열)' % (where, key))
            return []
        if not isinstance(v, list):
            errs.append('%s.%s 배열이어야 함' % (where, key))
            return []
        return v

    def need_count(obj, key, where):
        if not _is_count(obj.get(key)):
            errs.append('%s.%s 0 이상 정수여야 함 (값: %r)' % (where, key, obj.get(key)))

    need_str(spec, 'title', 'spec')
    need_str(spec, 'as_of', 'spec', required=False)
    stages = need_list(spec, 'stages', 'spec', required=True)
    if isinstance(spec.get('stages'), list) and not stages:
        errs.append('spec.stages 가 비어 있음 (단계 1개 이상)')
    seen = set()
    for i, st in enumerate(stages):
        w = 'stages[%d]' % i
        if not isinstance(st, dict):
            errs.append('%s 객체여야 함' % w)
            continue
        sid = need_str(st, 'id', w)
        if sid and sid in seen:
            errs.append('%s.id 중복: %s' % (w, sid))
        seen.add(sid)
        need_str(st, 'name', w)
        for key in ('inputs', 'outputs'):
            for j, x in enumerate(need_list(st, key, w)):
                if not isinstance(x, str):
                    errs.append('%s.%s[%d] 문자열이어야 함' % (w, key, j))
        for j, r in enumerate(need_list(st, 'rules', w)):
            rw = '%s.rules[%d]' % (w, j)
            if not isinstance(r, dict):
                errs.append('%s 객체여야 함' % rw)
                continue
            need_str(r, 'name', rw)
            need_count(r, 'fired', rw)
            need_str(r, 'test', rw, required=False)
        need_str(st, 'notes', w, required=False)
    cons = spec.get('conservation')
    if not isinstance(cons, dict):
        errs.append('spec.conservation 객체 없음 ({input, passed, excluded:{사유: 건수}})')
    else:
        need_count(cons, 'input', 'conservation')
        need_count(cons, 'passed', 'conservation')
        exc = cons.get('excluded')
        if not isinstance(exc, dict):
            errs.append('conservation.excluded 는 {사유: 건수} 객체여야 함')
        else:
            for k, v in exc.items():
                if not _is_count(v):
                    errs.append('conservation.excluded[%r] 0 이상 정수여야 함 (값: %r)' % (k, v))
    for i, d in enumerate(need_list(spec, 'decisions', 'spec')):
        w = 'decisions[%d]' % i
        if not isinstance(d, dict):
            errs.append('%s 객체여야 함' % w)
            continue
        need_str(d, 'where', w)
        need_str(d, 'what', w)
    for i, v in enumerate(need_list(spec, 'verification', 'spec')):
        w = 'verification[%d]' % i
        if not isinstance(v, dict):
            errs.append('%s 객체여야 함' % w)
            continue
        need_str(v, 'name', w)
        status = need_str(v, 'status', w)
        if status and status not in STATUSES:
            errs.append('%s.status 는 %s 중 하나 (값: %r)' % (w, '/'.join(STATUSES), status))
        need_str(v, 'evidence', w, required=False)
    for i, l in enumerate(need_list(spec, 'links', 'spec')):
        w = 'links[%d]' % i
        if not isinstance(l, dict):
            errs.append('%s 객체여야 함' % w)
            continue
        need_str(l, 'label', w)
        need_str(l, 'path', w)
    return errs


def conservation_delta(spec):
    """(입력, 통과, 제외 합, 차이). 차이 = 입력 − 통과 − 제외 합 (0 이면 보존)."""
    c = spec['conservation']
    excluded = sum(c['excluded'].values())
    return c['input'], c['passed'], excluded, c['input'] - c['passed'] - excluded


# ---------------------------------------------------------------- HTML 조각
def svg_pipeline(stages, vertical):
    """단계 상자 + 화살표 SVG. 가로(h)와 세로(v) 두 벌을 만들고 CSS 가 640px 에서 바꿔 보여 준다."""
    bw, bh = 180, 88
    gap = 36 if vertical else 40
    n = len(stages)
    if vertical:
        w, h = bw + 16, n * bh + (n - 1) * gap + 16
    else:
        w, h = n * bw + (n - 1) * gap + 16, bh + 16
    kind = 'v' if vertical else 'h'
    label = '파이프라인 %d단계 순서: %s' % (n, ', '.join(str(s.get('name', '')) for s in stages))
    out = ['<svg class="pipe %s" viewBox="0 0 %d %d" role="img" aria-label="%s" style="max-width:%dpx">' % (kind, w, h, esc(label), w)]
    out.append('<defs><marker id="arrow-%s" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="8" markerHeight="8" orient="auto">'
               '<path class="arrow" d="M0,0 L8,4 L0,8 z"/></marker></defs>' % kind)
    for i, st in enumerate(stages):
        rules = st.get('rules') or []
        fired = sum(r.get('fired', 0) for r in rules)
        x = 8 if vertical else 8 + i * (bw + gap)
        y = 8 + i * (bh + gap) if vertical else 8
        out.append('<g class="stage">')
        out.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12"/>' % (x, y, bw, bh))
        out.append('<text class="s-id" x="%d" y="%d">%s</text>' % (x + 12, y + 22, esc(clip('%d/%d %s' % (i + 1, n, st.get('id', '')), 20))))
        out.append('<text class="s-name" x="%d" y="%d">%s</text>' % (x + 12, y + 47, esc(clip(st.get('name', ''), 10))))
        out.append('<text class="s-meta" x="%d" y="%d">%s</text>' % (x + 12, y + 71, esc('규칙 %d개, 발동 %s건' % (len(rules), fmt(fired)))))
        out.append('</g>')
        if i < n - 1:
            if vertical:
                x1, y1, x2, y2 = x + bw // 2, y + bh, x + bw // 2, y + bh + gap - 2
            else:
                x1, y1, x2, y2 = x + bw, y + bh // 2, x + bw + gap - 2, y + bh // 2
            out.append('<line class="edge" x1="%d" y1="%d" x2="%d" y2="%d" marker-end="url(#arrow-%s)"/>' % (x1, y1, x2, y2, kind))
    out.append('</svg>')
    return '\n'.join(out)


def band_html(spec):
    """합계 보존 띠 + 범례 + 합계 문장. 불일치면 'FAIL: 합계 불일치' 배너와 빨간 외곽선."""
    total, passed, excluded, delta = conservation_delta(spec)
    reasons = list(spec['conservation']['excluded'].items())
    base = max(total, passed + excluded, 1)

    def pct(c):
        return 100.0 * c / base

    segs = ['<span class="seg seg-pass" style="width:%.2f%%" title="%s"></span>' % (pct(passed), esc('통과 %s (%.1f%%)' % (fmt(passed), pct(passed))))]
    legend = ['<span><i class="sw seg-pass"></i>통과 %s (%.1f%%)</span>' % (fmt(passed), pct(passed))]
    for i, (reason, count) in enumerate(reasons):
        cls = 'seg-' + EXCL_CLASSES[i % len(EXCL_CLASSES)]
        segs.append('<span class="seg %s" style="width:%.2f%%" title="%s"></span>' % (cls, pct(count), esc('%s %s (%.1f%%)' % (reason, fmt(count), pct(count)))))
        legend.append('<span><i class="sw %s"></i>%s %s (%.1f%%)</span>' % (cls, esc(reason), fmt(count), pct(count)))
    parts = []
    if delta != 0:
        msg = 'FAIL: 합계 불일치 — 입력 %s ≠ 통과 %s + 제외 %s = %s (차이 %+d)' % (fmt(total), fmt(passed), fmt(excluded), fmt(passed + excluded), delta)
        parts.append('<div class="banner bad" role="alert">%s</div>' % esc(msg))
        aria = msg
    else:
        msg = '입력 %s = 통과 %s + 제외 %s' % (fmt(total), fmt(passed), fmt(excluded))
        parts.append('<div class="banner ok">보존 확인: %s</div>' % esc(msg))
        aria = '합계 보존 띠: ' + msg
    parts.append('<div class="band%s" role="img" aria-label="%s">%s</div>' % (' fail' if delta else '', esc(aria), ''.join(segs)))
    parts.append('<div class="legend">%s</div>' % ''.join(legend))
    rows = ['<tr><td>통과</td><td class="num">%s</td><td class="num">%.1f%%</td></tr>' % (fmt(passed), pct(passed))]
    for reason, count in reasons:
        rows.append('<tr><td>제외: %s</td><td class="num">%s</td><td class="num">%.1f%%</td></tr>' % (esc(reason), fmt(count), pct(count)))
    foot = '<tr><td>입력 합계%s</td><td class="num">%s</td><td class="num">100%%</td></tr>' % (
        '' if delta == 0 else ' (스펙 input=%s)' % fmt(total), fmt(passed + excluded))
    parts.append('<div class="table-wrap" style="margin-top:var(--s-4)"><table><thead><tr><th>구분</th><th class="num">건수</th><th class="num">비율</th></tr></thead>'
                 '<tbody>%s</tbody><tfoot>%s</tfoot></table></div>' % (''.join(rows), foot))
    return '\n'.join(parts), delta


def stages_table(stages):
    rows = []
    for i, st in enumerate(stages):
        rows.append('<tr><td class="id">%d. %s</td><td><b>%s</b></td><td>%s</td><td>%s</td><td class="num">%d</td><td>%s</td></tr>' % (
            i + 1, esc(st.get('id', '')), esc(st.get('name', '')),
            '<br>'.join(esc(x) for x in st.get('inputs') or []) or '—',
            '<br>'.join(esc(x) for x in st.get('outputs') or []) or '—',
            len(st.get('rules') or []), esc(st.get('notes') or '')))
    return ('<div class="table-wrap"><table><thead><tr><th>단계</th><th>이름</th><th>입력</th><th>출력</th><th class="num">규칙</th><th>비고</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % ''.join(rows))


def rules_table(stages):
    rows, total, zero = [], 0, 0
    for st in stages:
        for r in st.get('rules') or []:
            fired = r.get('fired', 0)
            total += fired
            cls = ''
            cell = fmt(fired)
            if fired == 0:
                zero += 1
                cls = ' class="row-warn"'
                cell = '0 <span class="badge warn">0건, 엣지 입력으로 재확인</span>'
            rows.append('<tr%s><td>%s</td><td>%s</td><td class="num">%s</td><td class="id">%s</td></tr>' % (
                cls, esc(st.get('name', '')), esc(r.get('name', '')), cell, esc(r.get('test') or '—')))
    if not rows:
        rows.append('<tr><td colspan="4">규칙이 없습니다 — stages[].rules 에 규칙 1개 = 테스트 1개로 적습니다</td></tr>')
    foot = '<tr><td colspan="2">발동 합계 (규칙 %d개%s)</td><td class="num">%s</td><td></td></tr>' % (
        len(rows), ', 0건 %d개' % zero if zero else '', fmt(total))
    return ('<div class="table-wrap"><table><thead><tr><th>단계</th><th>규칙</th><th class="num">발동 건수</th><th>테스트</th></tr></thead>'
            '<tbody>%s</tbody><tfoot>%s</tfoot></table></div>' % (''.join(rows), foot)), total, zero


def decisions_table(decisions):
    if not decisions:
        return '<div class="banner">결정 항목 없음 — <code>grep -rn "결정:" .</code> 결과를 decisions[] 에 {where, what} 로 옮깁니다</div>'
    rows = ['<tr><td class="num">%d</td><td class="id">%s</td><td>%s</td></tr>' % (i + 1, esc(d.get('where', '')), esc(d.get('what', '')))
            for i, d in enumerate(decisions)]
    return ('<div class="table-wrap"><table><thead><tr><th class="num">#</th><th>위치</th><th>결정 (무엇 / 왜 / 버린 대안)</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % ''.join(rows))


def verification_table(items):
    counts = dict((s, 0) for s in STATUSES)
    rows = []
    for v in items:
        status = v.get('status', '')
        counts[status] = counts.get(status, 0) + 1
        rows.append('<tr><td>%s</td><td><span class="badge %s">%s</span></td><td>%s</td></tr>' % (
            esc(v.get('name', '')), STATUS_CLASS.get(status, 'off'), esc(status), esc(v.get('evidence') or '—')))
    if not rows:
        rows.append('<tr><td colspan="3">검증 항목 없음 — 테스트·check_contract·preflight·HUMAN_CHECK 를 verification[] 에 적습니다</td></tr>')
    summary = ', '.join('%s %d' % (s, counts[s]) for s in STATUSES)
    table = ('<div class="table-wrap"><table><thead><tr><th>항목</th><th>상태</th><th>근거(명령·파일:줄·테스트)</th></tr></thead>'
             '<tbody>%s</tbody></table></div>' % ''.join(rows))
    return table, summary, counts


def links_list(links, out_path):
    if not links:
        return '<p class="meta">링크 없음</p>'
    out_dir = os.path.dirname(os.path.abspath(out_path))
    items = []
    for l in links:
        path = l.get('path', '')
        href = path
        if not (path.startswith(('http://', 'https://')) or os.path.isabs(path)):
            try:
                href = os.path.relpath(os.path.abspath(path), out_dir).replace(os.sep, '/')
            except ValueError:  # 드라이브가 다르면 상대경로를 만들 수 없다 → 원래 경로
                href = path
        items.append('<li><a href="%s">%s</a><span class="id">%s</span></li>' % (esc(href), esc(l.get('label', '')), esc(path)))
    return '<ul class="links">%s</ul>' % ''.join(items)


def build_html(spec, out_path, spec_label='docs/flow.json', tokens=None):
    """스펙 → HTML 문자열. (html, delta) 를 돌려준다. delta≠0 이면 합계 불일치."""
    tokens = tokens if tokens is not None else read_tokens()
    stages = spec.get('stages') or []
    total, passed, excluded, delta = conservation_delta(spec)
    band, _ = band_html(spec)
    rules, fired_total, zero = rules_table(stages)
    ver_table, ver_summary, counts = verification_table(spec.get('verification') or [])
    n_rules = sum(len(st.get('rules') or []) for st in stages)
    n_pass, n_ver = counts.get('PASS', 0), len(spec.get('verification') or [])
    kpi = [
        ('입력', fmt(total), '건'), ('통과', fmt(passed), '건'),
        ('제외', fmt(excluded), '건 (사유 %d)' % len(spec['conservation']['excluded'])),
        ('규칙 발동', fmt(fired_total), '건 (규칙 %d)' % n_rules),
        ('검증 PASS', '%d<small>/%d</small>' % (n_pass, n_ver), ''),
    ]
    kpi_html = ''.join('<div class="card"><span class="label">%s</span><span class="value num">%s<small>%s</small></span></div>' % (esc(k), v, esc(u))
                       for k, v, u in kpi)
    css = ':root {\n' + '\n'.join('  %s: %s;' % (k, v) for k, v in tokens) + '\n}\n' + PAGE_CSS
    status_line = 'FAIL: 합계 불일치 (차이 %+d)' % delta if delta else '합계 보존 확인'
    doc = [
        '<!doctype html>', '<html lang="ko">', '<head>', '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>%s</title>' % esc(spec.get('title', '')),
        '<style>%s</style>' % css, '</head>', '<body>', '<main class="container">',
        '<header class="top"><h1>%s</h1><p class="meta">기준 %s / 스펙 %s / 생성 scripts/flowmap.py / %s</p></header>' % (
            esc(spec.get('title', '')), esc(spec.get('as_of') or '—'), esc(spec_label), esc(status_line)),
        '<div class="kpi">%s</div>' % kpi_html,
        '<section class="section"><h2>파이프라인</h2><p class="why">입력이 어떤 단계를 지나 출력이 되는지. 상자 안 숫자는 그 단계의 규칙 수와 발동 건수 합이다.</p>',
        svg_pipeline(stages, False), svg_pipeline(stages, True),
        '<div style="margin-top:var(--s-4)">%s</div></section>' % stages_table(stages),
        '<section class="section"><h2>합계 보존</h2><p class="why">입력 건수 = 통과 + 사유별 제외. 맞지 않으면 어딘가에서 행이 조용히 사라지거나 두 번 세어진 것이다.</p>%s</section>' % band,
        '<section class="section"><h2>규칙 발동</h2><p class="why">규칙 1개 = 테스트 1개. 발동 0건인 규칙은 작동 증거가 없으므로 엣지 입력(scripts/make_edge_cases.py)으로 다시 확인한다.</p>%s</section>' % rules,
        '<section class="section"><h2>결정</h2><p class="why">지시받지 않고 정한 것과 그 위치(<code># 결정:</code> 주석). DECISIONS.md 1절과 같아야 한다.</p>%s</section>' % decisions_table(spec.get('decisions') or []),
        '<section class="section"><h2>검증</h2><p class="why">%s</p>%s</section>' % (esc(ver_summary), ver_table),
        '<section class="section"><h2>링크</h2><p class="why">출력 파일·근거 문서. 경로는 이 파일 위치 기준 상대경로로 연결했다.</p>%s</section>' % links_list(spec.get('links') or [], out_path),
        '<footer class="foot"><p class="meta">이 보고서의 숫자는 전부 %s 에서 왔고, 스펙의 숫자는 실행 결과(out/audit.json·테스트 출력)에서 옮긴다. 암산한 숫자는 넣지 않는다.</p></footer>' % esc(spec_label),
        '</main>', '</body>', '</html>', '',
    ]
    return '\n'.join(doc), delta


def summary_line(spec, out_path, delta):
    stages = spec.get('stages') or []
    total, passed, excluded, _ = conservation_delta(spec)
    n_rules = sum(len(st.get('rules') or []) for st in stages)
    fired = sum(r.get('fired', 0) for st in stages for r in st.get('rules') or [])
    ver = spec.get('verification') or []
    n_pass = sum(1 for v in ver if v.get('status') == 'PASS')
    cons = ('입력 %s = 통과 %s + 제외 %s' % (fmt(total), fmt(passed), fmt(excluded))) if delta == 0 else \
        ('FAIL 합계 불일치: 입력 %s ≠ 통과 %s + 제외 %s (차이 %+d)' % (fmt(total), fmt(passed), fmt(excluded), delta))
    return '%s — 단계 %d · 규칙 %d · 발동 %s건 · %s · 검증 PASS %d/%d' % (out_path, len(stages), n_rules, fmt(fired), cons, n_pass, len(ver))


# ---------------------------------------------------------------- 진입
def main(argv=None):
    ap = argparse.ArgumentParser(description='docs/flow.json → out/report.html (파이프라인 도식·합계 보존 띠·규칙 발동·결정·검증). 표준 라이브러리만.')
    ap.add_argument('--spec', default=os.path.join('docs', 'flow.json'), help='흐름 스펙 JSON (기본 docs/flow.json, 예시 docs/flow.example.json)')
    ap.add_argument('--out', default=os.path.join('out', 'report.html'), help='생성할 HTML (기본 out/report.html)')
    ap.add_argument('--check', action='store_true', help='스펙 검증만 하고 파일을 만들지 않음')
    a = ap.parse_args(argv)

    spec, problem = load_spec(a.spec)
    if problem == 'missing':
        err('스펙 파일이 없습니다: %s' % a.spec)
        err('다음 행동: cp docs/flow.example.json docs/flow.json 로 시작해 단계·규칙·건수를 실행 결과(out/audit.json)로 채우세요')
        return 2
    if problem:
        err('%s: %s' % (a.spec, problem))
        err('다음 행동: JSON 문법을 고치세요 (python3 -m json.tool %s 로 위치 확인)' % a.spec)
        return 1
    errs = validate(spec)
    if errs:
        err('스펙 오류 %d건 (%s):' % (len(errs), a.spec))
        for e in errs:
            err('  - ' + e)
        err('다음 행동: docs/flow.example.json 의 모양에 맞춰 위 항목을 고치세요')
        return 1
    total, passed, excluded, delta = conservation_delta(spec)
    if a.check:
        if delta:
            err('FAIL: 합계 불일치 — 입력 %s ≠ 통과 %s + 제외 %s (차이 %+d)' % (fmt(total), fmt(passed), fmt(excluded), delta))
            err('다음 행동: conservation 의 input/passed/excluded 를 out/audit.json 의 실제 건수로 맞추세요')
            return 1
        print('OK: 스펙 유효 — ' + summary_line(spec, a.spec, 0))
        return 0
    text, delta = build_html(spec, a.out, spec_label=a.spec)
    out_dir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(out_dir, exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    print(summary_line(spec, a.out, delta))
    print('미리보기(사람이 다른 터미널에서 실행): python3 design-kit/serve.py $PORT --dir %s --index %s  → 미리보기 탭에서 /%s' % (
        os.path.dirname(a.out) or '.', os.path.basename(a.out), os.path.basename(a.out)))
    if delta:
        err('FAIL: 합계 불일치 — 입력 %s ≠ 통과 %s + 제외 %s (차이 %+d). 띠에 표시한 채 생성했습니다.' % (fmt(total), fmt(passed), fmt(excluded), delta))
        err('다음 행동: conservation 의 input/passed/excluded 를 out/audit.json 의 실제 건수로 맞추고 다시 실행하세요')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
