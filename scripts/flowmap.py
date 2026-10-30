#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""flowmap.py — 보고서 스펙 JSON → 단독 HTML 보고서 1파일 (표준 라이브러리만, Python 3.9)

  python3 scripts/flowmap.py                                        # docs/flow.json → out/report.html
  python3 scripts/flowmap.py --spec out/report/stage_01-03.json --out out/report/stage_01-03.html
  python3 scripts/flowmap.py --spec docs/flow.json --stages 1-3 --out out/report/stage_01-03.html   # 단계 1~3 만
  python3 scripts/flowmap.py --index out/report                     # 폴더의 stage_*.json/html 을 모아 index.html
  python3 scripts/flowmap.py --check                                # 스펙 검증만 (파일을 만들지 않음)
  python3 scripts/flowmap.py --spec docs/flow.example.json --out .tmp/report.html   # 예시로 모양 보기

내용(위에서 아래로, 결론 먼저): 요약 3줄 · KPI · 단계 상태 스트립(한눈) · 파이프라인 SVG · 합계 보존 띠 · 전역 차트
      · 단계별 상세(역할 → 구현 파일:줄 → 방법 → 결과 숫자 → 차트 → 입력→출력 샘플 → 테스트 → 결정) · 규칙표 · 결정 · 검증 · 링크
차트: bar · hbar · compare(전/후) · stacked · line · hist · matrix — 전부 인라인 SVG/HTML, 값 라벨 필수, 아래에 데이터 표(details).
스펙 v1(단계·규칙·합계·결정·검증·링크)은 그대로 유효하고 v2 키(summary·stages[].role/implemented/method/results/samples/tests/charts·charts·status)는 선택이다.
exit 0 생성 성공 / 1 스펙 오류 또는 합계 불일치(불일치는 'FAIL: 합계 불일치' 를 띠에 찍은 HTML 을 만든 뒤 1) / 2 스펙 파일 없음
CSS 는 design-kit/tokens.css 값을 읽어 rgb() 로 바꿔 인라인 복사한다(외부 파일 참조 0 → 미리보기·제출물에서 단독으로 열림,
ui_check 의 raw hex 검사도 통과). 모든 문자열은 html.escape. 생성 시각을 넣지 않아 같은 스펙이면 같은 HTML 이 나온다.
미리보기(사람이 다른 터미널에서 실행): python3 design-kit/serve.py $PORT --dir out/report --index index.html
"""
import argparse
import glob
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
CHART_TYPES = ('bar', 'hbar', 'compare', 'stacked', 'line', 'hist', 'matrix')
HEX_RE = re.compile(r'(?<![\w-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![\w-])')
TOKEN_RE = re.compile(r'(--[\w-]+)\s*:\s*([^;]+);')
EXCL_CLASSES = ('x0', 'x1', 'x2', 'x3', 'x4')   # 제외 사유 색 순환: bad → warn → off → info → brand-deep
PALETTE = ('c0', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6')   # 차트 범주 색 순환: brand → info → warn → bad → off → brand-deep → ok

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

# 페이지 CSS: raw hex 0, var() 만. 고정 width ≥1000px·min-width ≥400px 없음(ui_check·smoke_web 규칙). 카드 안에 카드 없음(안쪽은 .mini/.scard).
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
h3 { font-size: 16px; font-weight: 700; margin: 0 0 var(--s-2); }
h4 { font-size: 13px; font-weight: 700; margin: var(--s-4) 0 var(--s-2); color: var(--ink-2); }
.section { margin-top: var(--s-6); }
.why { font-size: 13px; color: var(--muted); padding-left: 18px; margin: 0 0 var(--s-3); max-width: 720px; }
.meta { font-size: 12px; color: var(--muted); margin: 0; }
.num { font-variant-numeric: tabular-nums; }
.id { font-family: var(--mono); font-size: 12px; }
.card { background: var(--panel); border-radius: var(--r-lg); box-shadow: var(--ring), var(--shadow-1); padding: var(--s-4); }
.summary { margin-top: var(--s-4); }
.summary ol { margin: 0; padding-left: 22px; font-size: 15px; line-height: 1.6; }
.summary li + li { margin-top: 4px; }
.kpi { display: grid; gap: var(--s-3); grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-top: var(--s-4); }
.kpi .card { display: grid; gap: 4px; padding: 14px 16px; }
.kpi .label { font-size: 12px; color: var(--muted); }
.kpi .value { font-size: 26px; font-weight: 800; letter-spacing: -.02em; font-variant-numeric: tabular-nums; line-height: 1.1; }
.kpi .value small { font-size: 12px; font-weight: 600; color: var(--muted); margin-left: 2px; letter-spacing: 0; }
.strip { display: grid; gap: var(--s-3); grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); }
.scard { background: var(--panel); border-radius: var(--r-md); box-shadow: var(--ring); padding: 12px 14px; display: grid; gap: 6px; border-left: 4px solid var(--off); }
.scard.ok { border-left-color: var(--ok); } .scard.bad { border-left-color: var(--bad); } .scard.warn { border-left-color: var(--warn); }
.scard .st-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.scard .st-name { font-weight: 700; }
.scard .st-key { font-size: 22px; font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: -.02em; line-height: 1.1; }
.scard .st-key small { font-size: 11px; font-weight: 600; color: var(--muted); margin-left: 3px; }
.scard .st-role { font-size: 12px; color: var(--ink-2); }
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
td.cell-ok { background: var(--ok-bg); color: var(--ok); font-weight: 700; }
td.cell-bad { background: var(--bad-bg); color: var(--bad); font-weight: 700; }
td.cell-warn { background: var(--warn-bg); color: var(--warn); font-weight: 700; }
td.cell-off { background: var(--off-bg); color: var(--off); }
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
.c0 { fill: var(--brand); background: var(--brand); } .c1 { fill: var(--info); background: var(--info); } .c2 { fill: var(--warn); background: var(--warn); }
.c3 { fill: var(--bad); background: var(--bad); } .c4 { fill: var(--off); background: var(--off); } .c5 { fill: var(--brand-deep); background: var(--brand-deep); }
.c6 { fill: var(--ok); background: var(--ok); }
.charts { display: grid; gap: var(--s-4); grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); margin-top: var(--s-3); }
.chart { margin: 0; background: var(--panel); border-radius: var(--r-md); box-shadow: var(--ring); padding: 12px 14px; min-width: 0; }
.chart figcaption { font-weight: 700; font-size: 13px; margin-bottom: 6px; }
.chart .note { font-size: 12px; color: var(--muted); margin: 0 0 6px; }
.chart svg { width: 100%; height: auto; display: block; font-family: var(--font); }
.chart svg text { fill: var(--ink-2); font-size: 11px; }
.chart svg text.val { fill: var(--ink); font-weight: 700; font-variant-numeric: tabular-nums; }
.chart svg .axis { stroke: var(--line-strong); stroke-width: 1; }
.chart svg .grid { stroke: var(--line); stroke-width: 1; }
.chart svg .ln { fill: none; stroke-width: 2; }
.chart svg .ln.c0 { stroke: var(--brand); } .chart svg .ln.c1 { stroke: var(--info); } .chart svg .ln.c2 { stroke: var(--warn); }
.chart svg .ln.c3 { stroke: var(--bad); } .chart svg .ln.c4 { stroke: var(--off); } .chart svg .ln.c5 { stroke: var(--brand-deep); } .chart svg .ln.c6 { stroke: var(--ok); }
.chart details { margin-top: 6px; font-size: 12px; }
.chart summary { cursor: pointer; color: var(--brand-deep); }
.chart details table { font-size: 12px; margin-top: 6px; }
.chart details th, .chart details td { height: auto; padding: 4px 8px; min-width: 0; }
.stage { background: var(--panel); border-radius: var(--r-lg); box-shadow: var(--ring), var(--shadow-1); padding: var(--s-4); margin-top: var(--s-4); }
.stage .st-top { display: flex; justify-content: space-between; align-items: center; gap: var(--s-3); flex-wrap: wrap; }
.stage .st-top h3 { margin: 0; }
.stage .role { font-size: 14px; color: var(--ink-2); margin: 6px 0 0; }
.stage ol.method { margin: 0; padding-left: 22px; }
.stage ol.method li + li { margin-top: 2px; }
.mini { display: grid; gap: var(--s-2); grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); }
.mini div { background: var(--surface-2); border-radius: var(--r-sm); padding: 8px 10px; }
.mini .label { font-size: 11px; color: var(--muted); display: block; }
.mini .value { font-size: 18px; font-weight: 800; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.mini .value small { font-size: 11px; font-weight: 600; color: var(--muted); margin-left: 2px; }
.mini .note { font-size: 11px; color: var(--ink-2); display: block; }
.links { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--s-2); }
.links li { display: flex; gap: var(--s-3); align-items: baseline; flex-wrap: wrap; }
.foot { margin-top: var(--s-7); }
.index { display: grid; gap: var(--s-3); grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: var(--s-4); }
.index .card { display: grid; gap: 6px; }
.index .card a { font-weight: 700; font-size: 15px; }
@media (max-width: 640px) {
  .container { padding: 0 var(--s-3) var(--s-7); }
  .section { margin-top: var(--s-5); }
  .pipe.h { display: none; }
  .pipe.v { display: block; max-width: 320px; margin: 0 auto; }
  .charts { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""


# ---------------------------------------------------------------- 공용
def err(msg):
    print(msg, file=sys.stderr)


def esc(s):
    return html.escape(str(s), quote=True)


def fmt(n):
    if isinstance(n, bool):
        return str(n)
    if isinstance(n, int):
        return '{:,}'.format(n)
    if isinstance(n, float):
        return '{:,.4g}'.format(n) if abs(n) < 1000 else '{:,.0f}'.format(n)
    return str(n)


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


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_count(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


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


def _validate_chart(ch, w, errs):
    if not isinstance(ch, dict):
        errs.append('%s 객체여야 함' % w)
        return
    t = ch.get('type')
    if t not in CHART_TYPES:
        errs.append('%s.type 은 %s 중 하나 (값: %r)' % (w, '/'.join(CHART_TYPES), t))
        return
    if not isinstance(ch.get('title'), str) or not ch.get('title'):
        errs.append('%s.title 없음' % w)
    data = ch.get('data')
    if t == 'line':
        series = ch.get('series')
        if not isinstance(series, list) or not series:
            errs.append('%s.series 배열 필요 ([{name, points:[{x, y}]}])' % w)
        else:
            for j, s in enumerate(series):
                pts = s.get('points') if isinstance(s, dict) else None
                if not isinstance(pts, list) or not pts:
                    errs.append('%s.series[%d].points 배열 필요' % (w, j))
                    continue
                for k, p in enumerate(pts):
                    if not isinstance(p, dict) or not _num(p.get('y')):
                        errs.append('%s.series[%d].points[%d].y 숫자여야 함' % (w, j, k))
        return
    if t == 'matrix':
        if not isinstance(ch.get('cols'), list) or not isinstance(ch.get('rows'), list):
            errs.append('%s.rows/cols 배열 필요 (rows: [{label, cells:[{value, status}]}])' % w)
        return
    if not isinstance(data, list) or not data:
        errs.append('%s.data 배열 필요' % w)
        return
    for j, d in enumerate(data):
        if not isinstance(d, dict) or 'label' not in d:
            errs.append('%s.data[%d] 는 {label, ...} 객체여야 함' % (w, j))
            continue
        if t in ('bar', 'hbar', 'hist') and not _num(d.get('value')):
            errs.append('%s.data[%d].value 숫자여야 함' % (w, j))
        if t == 'compare' and not (_num(d.get('before')) and _num(d.get('after'))):
            errs.append('%s.data[%d].before/after 숫자여야 함' % (w, j))
        if t == 'stacked' and not isinstance(d.get('parts'), dict):
            errs.append('%s.data[%d].parts 는 {이름: 숫자} 객체여야 함' % (w, j))


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

    def need_status(obj, key, where, required=True):
        v = obj.get(key)
        if v is None:
            if required:
                errs.append('%s.%s 없음' % (where, key))
            return
        if v not in STATUSES:
            errs.append('%s.%s 는 %s 중 하나 (값: %r)' % (where, key, '/'.join(STATUSES), v))

    need_str(spec, 'title', 'spec')
    need_str(spec, 'as_of', 'spec', required=False)
    need_str(spec, 'stage_range', 'spec', required=False)
    summary = spec.get('summary')
    if summary is not None and not (isinstance(summary, list) and all(isinstance(x, str) for x in summary)):
        errs.append('spec.summary 는 문자열 배열(결론 1~3줄)이어야 함')
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
        need_status(st, 'status', w, required=False)
        for key in ('role', 'notes', 'evidence'):
            need_str(st, key, w, required=False)
        for key in ('inputs', 'outputs', 'method'):
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
        for j, it in enumerate(need_list(st, 'implemented', w)):
            iw = '%s.implemented[%d]' % (w, j)
            if not isinstance(it, dict):
                errs.append('%s 객체여야 함' % iw)
                continue
            need_str(it, 'file', iw)
            need_str(it, 'what', iw)
            need_str(it, 'symbol', iw, required=False)
            need_str(it, 'lines', iw, required=False)
        for j, r in enumerate(need_list(st, 'results', w)):
            rw = '%s.results[%d]' % (w, j)
            if not isinstance(r, dict):
                errs.append('%s 객체여야 함' % rw)
                continue
            need_str(r, 'label', rw)
            if 'value' not in r:
                errs.append('%s.value 없음' % rw)
            need_str(r, 'unit', rw, required=False)
            need_str(r, 'note', rw, required=False)
        for j, s in enumerate(need_list(st, 'samples', w)):
            sw = '%s.samples[%d]' % (w, j)
            if not isinstance(s, dict) or 'before' not in s or 'after' not in s:
                errs.append('%s 는 {before, after, note?} 객체여야 함' % sw)
        for j, t in enumerate(need_list(st, 'tests', w)):
            tw = '%s.tests[%d]' % (w, j)
            if not isinstance(t, dict):
                errs.append('%s 객체여야 함' % tw)
                continue
            need_str(t, 'name', tw)
            need_status(t, 'status', tw)
            need_str(t, 'evidence', tw, required=False)
        for j, ch in enumerate(need_list(st, 'charts', w)):
            _validate_chart(ch, '%s.charts[%d]' % (w, j), errs)
    for j, ch in enumerate(need_list(spec, 'charts', 'spec')):
        _validate_chart(ch, 'charts[%d]' % j, errs)
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
        need_str(d, 'stage', w, required=False)
    for i, v in enumerate(need_list(spec, 'verification', 'spec')):
        w = 'verification[%d]' % i
        if not isinstance(v, dict):
            errs.append('%s 객체여야 함' % w)
            continue
        need_str(v, 'name', w)
        need_status(v, 'status', w)
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


# ---------------------------------------------------------------- --stages 범위
def parse_range(text, n):
    """'1-3' / '2' / '1,3,5' / 'all' → 0-based 인덱스 목록(순서 유지). 범위 밖이면 ValueError."""
    text = (text or 'all').strip().lower()
    if text in ('', 'all', '*'):
        return list(range(n))
    picked = []
    for part in text.replace(' ', '').split(','):
        if not part:
            continue
        m = re.fullmatch(r'(\d+)(?:-(\d+))?', part)
        if not m:
            raise ValueError('--stages 형식 오류: %r (예: 1-3, 2, 1,3, all)' % text)
        a = int(m.group(1))
        b = int(m.group(2) or a)
        if a < 1 or b < a or b > n:
            raise ValueError('--stages 범위 밖: %s (단계는 1~%d)' % (part, n))
        picked.extend(i for i in range(a - 1, b) if i not in picked)
    return picked


def filter_spec(spec, text):
    """--stages 로 단계 일부만 남긴 사본. stage_range 와 제목 꼬리를 붙인다. 'all' 이면 원본 그대로."""
    stages = spec.get('stages') or []
    idx = parse_range(text, len(stages))
    if idx == list(range(len(stages))):
        return spec
    out = dict(spec)
    out['stages'] = [stages[i] for i in idx]
    ids = set(st.get('id') for st in out['stages'])
    decisions = spec.get('decisions') or []
    if any(isinstance(d, dict) and d.get('stage') for d in decisions):
        out['decisions'] = [d for d in decisions if not d.get('stage') or d.get('stage') in ids]
    label = '%d-%d' % (idx[0] + 1, idx[-1] + 1) if idx == list(range(idx[0], idx[-1] + 1)) else ','.join(str(i + 1) for i in idx)
    out['stage_range'] = label
    return out


# ---------------------------------------------------------------- 차트 (인라인 SVG + 데이터 표)
def _data_table(headers, rows):
    th = ''.join('<th%s>%s</th>' % (' class="num"' if i else '', esc(h)) for i, h in enumerate(headers))
    body = ''.join('<tr>%s</tr>' % ''.join('<td%s>%s</td>' % (' class="num"' if i else '', esc(c)) for i, c in enumerate(r)) for r in rows)
    return '<details><summary>데이터 표</summary><div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div></details>' % (th, body)


def _figure(ch, svg, table, aria):
    note = '<p class="note">%s</p>' % esc(ch['note']) if ch.get('note') else ''
    unit = (' (%s)' % esc(ch['unit'])) if ch.get('unit') else ''
    return '<figure class="chart"><figcaption>%s%s</figcaption>%s<div role="img" aria-label="%s">%s</div>%s</figure>' % (
        esc(ch.get('title', '')), unit, note, esc(aria), svg, table)


def _nice_max(v):
    if v <= 0:
        return 1
    mag = 10 ** (len(str(int(v))) - 1)
    for k in (1, 2, 2.5, 5, 10):
        if v <= k * mag:
            return k * mag
    return v


def chart_bar(ch, horizontal=False, hist=False):
    data = ch['data']
    if not horizontal and len(data) > 12 and not hist:
        horizontal = True   # 범주가 많으면 가로 막대가 읽기 쉽다
    vals = [float(d['value']) for d in data]
    vmax = _nice_max(max(vals))
    hl = set(ch.get('highlight') or [])
    rows = [(d['label'], fmt(d['value'])) for d in data]
    if horizontal:
        rh, lw, w = 26, 170, 640
        h = 12 + rh * len(data) + 8
        out = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (w, h)]
        for i, d in enumerate(data):
            y = 12 + i * rh
            bw = max(2, (w - lw - 70) * float(d['value']) / vmax)
            cls = 'c3' if d['label'] in hl else PALETTE[0]
            out.append('<text x="%d" y="%d" text-anchor="end">%s</text>' % (lw - 8, y + 17, esc(clip(d['label'], 18))))
            out.append('<rect class="%s" x="%d" y="%d" width="%.1f" height="%d" rx="3"/>' % (cls, lw, y + 4, bw, rh - 8))
            out.append('<text class="val" x="%.1f" y="%d">%s</text>' % (lw + bw + 6, y + 17, esc(fmt(d['value']))))
        out.append('</svg>')
    else:
        w, h, pad_b, pad_t, pad_l = 640, 240, 44, 24, 8
        n = len(data)
        slot = (w - pad_l * 2) / n
        bw = slot * (0.96 if hist else 0.62)
        out = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (w, h)]
        for k in range(1, 4):
            gy = pad_t + (h - pad_t - pad_b) * (1 - k / 4.0)
            out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, gy, w - pad_l, gy))
        out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (pad_l, h - pad_b, w - pad_l, h - pad_b))
        for i, d in enumerate(data):
            v = float(d['value'])
            bh = (h - pad_t - pad_b) * v / vmax
            x = pad_l + i * slot + (slot - bw) / 2
            y = h - pad_b - bh
            cls = 'c3' if d['label'] in hl else PALETTE[0]
            out.append('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3"/>' % (cls, x, y, bw, bh))
            out.append('<text class="val" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (x + bw / 2, y - 5, esc(fmt(d['value']))))
            out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x + bw / 2, h - pad_b + 16, esc(clip(d['label'], 10 if n <= 8 else 6))))
        out.append('</svg>')
    aria = '%s: %s' % (ch.get('title', ''), ', '.join('%s %s' % (l, v) for l, v in rows))
    return _figure(ch, '\n'.join(out), _data_table([ch.get('xlabel') or '항목', ch.get('ylabel') or ch.get('unit') or '값'], rows), aria)


def chart_compare(ch):
    data = ch['data']
    names = ch.get('names') or ['전', '후']
    vmax = _nice_max(max(max(float(d['before']), float(d['after'])) for d in data))
    w, h, pad_b, pad_t, pad_l = 640, 240, 44, 24, 8
    n = len(data)
    slot = (w - pad_l * 2) / n
    bw = slot * 0.3
    out = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (w, h)]
    for k in range(1, 4):
        gy = pad_t + (h - pad_t - pad_b) * (1 - k / 4.0)
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, gy, w - pad_l, gy))
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (pad_l, h - pad_b, w - pad_l, h - pad_b))
    rows = []
    for i, d in enumerate(data):
        base = pad_l + i * slot + (slot - 2 * bw - 4) / 2
        for j, key in enumerate(('before', 'after')):
            v = float(d[key])
            bh = (h - pad_t - pad_b) * v / vmax
            x = base + j * (bw + 4)
            y = h - pad_b - bh
            out.append('<rect class="%s" x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3"/>' % ('c4' if j == 0 else 'c0', x, y, bw, bh))
            out.append('<text class="val" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (x + bw / 2, y - 5, esc(fmt(d[key]))))
        out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (base + bw + 2, h - pad_b + 16, esc(clip(d['label'], 10 if n <= 6 else 6))))
        rows.append((d['label'], fmt(d['before']), fmt(d['after']), ('%+g' % (float(d['after']) - float(d['before'])))))
    out.append('</svg>')
    legend = '<div class="legend"><span><i class="sw c4"></i>%s</span><span><i class="sw c0"></i>%s</span></div>' % (esc(names[0]), esc(names[1]))
    aria = '%s: %s' % (ch.get('title', ''), ', '.join('%s %s→%s' % (r[0], r[1], r[2]) for r in rows))
    return _figure(ch, '\n'.join(out) + legend, _data_table(['항목', names[0], names[1], '차이'], rows), aria)


def chart_stacked(ch):
    data = ch['data']
    parts = []
    for d in data:
        for k in d['parts']:
            if k not in parts:
                parts.append(k)
    totals = [sum(float(v) for v in d['parts'].values()) for d in data]
    vmax = max(totals) or 1
    rh, lw, w = 26, 150, 640
    h = 12 + rh * len(data) + 8
    out = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (w, h)]
    rows = []
    for i, d in enumerate(data):
        y = 12 + i * rh
        x = lw
        out.append('<text x="%d" y="%d" text-anchor="end">%s</text>' % (lw - 8, y + 17, esc(clip(d['label'], 16))))
        for j, k in enumerate(parts):
            v = float(d['parts'].get(k, 0))
            bw = (w - lw - 70) * v / vmax
            if bw > 0:
                out.append('<rect class="%s" x="%.1f" y="%d" width="%.1f" height="%d"/>' % (PALETTE[j % len(PALETTE)], x, y + 4, bw, rh - 8))
            x += bw
        out.append('<text class="val" x="%.1f" y="%d">%s</text>' % (x + 6, y + 17, esc(fmt(int(totals[i]) if totals[i] == int(totals[i]) else totals[i]))))
        rows.append([d['label']] + [fmt(d['parts'].get(k, 0)) for k in parts] + [fmt(int(totals[i]) if totals[i] == int(totals[i]) else totals[i])])
    out.append('</svg>')
    legend = '<div class="legend">%s</div>' % ''.join('<span><i class="sw %s"></i>%s</span>' % (PALETTE[j % len(PALETTE)], esc(k)) for j, k in enumerate(parts))
    aria = '%s: %s' % (ch.get('title', ''), ', '.join('%s 합계 %s' % (r[0], r[-1]) for r in rows))
    return _figure(ch, '\n'.join(out) + legend, _data_table(['항목'] + parts + ['합계'], rows), aria)


def chart_line(ch):
    series = ch['series']
    all_pts = [p for s in series for p in s['points']]
    ys = [float(p['y']) for p in all_pts]
    ymax, ymin = _nice_max(max(ys)), min(0.0, min(ys))
    n = max(len(s['points']) for s in series)
    w, h, pad_b, pad_t, pad_l, pad_r = 640, 240, 36, 20, 44, 12
    out = ['<svg viewBox="0 0 %d %d" aria-hidden="true">' % (w, h)]
    for k in range(0, 5):
        gy = pad_t + (h - pad_t - pad_b) * (1 - k / 4.0)
        out.append('<line class="grid" x1="%d" y1="%.1f" x2="%d" y2="%.1f"/>' % (pad_l, gy, w - pad_r, gy))
        out.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (pad_l - 6, gy + 4, esc(fmt(ymin + (ymax - ymin) * k / 4.0))))
    out.append('<line class="axis" x1="%d" y1="%d" x2="%d" y2="%d"/>' % (pad_l, h - pad_b, w - pad_r, h - pad_b))

    def sx(i, cnt):
        return pad_l + (w - pad_l - pad_r) * (i / float(max(cnt - 1, 1)))

    def sy(v):
        return h - pad_b - (h - pad_t - pad_b) * ((v - ymin) / float(ymax - ymin or 1))

    labels = [str(p.get('x', i)) for i, p in enumerate(series[0]['points'])]
    step = max(1, (len(labels) + 9) // 10)
    for i, lab in enumerate(labels):
        if i % step == 0 or i == len(labels) - 1:
            out.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (sx(i, len(labels)), h - pad_b + 16, esc(clip(lab, 8))))
    for j, s in enumerate(series):
        pts = s['points']
        cls = PALETTE[j % len(PALETTE)]
        coords = ' '.join('%.1f,%.1f' % (sx(i, len(pts)), sy(float(p['y']))) for i, p in enumerate(pts))
        out.append('<polyline class="ln %s" points="%s"/>' % (cls, coords))
        for i, p in enumerate(pts):
            out.append('<circle class="%s" cx="%.1f" cy="%.1f" r="3"/>' % (cls, sx(i, len(pts)), sy(float(p['y']))))
            if len(pts) <= 12:
                out.append('<text class="val" x="%.1f" y="%.1f" text-anchor="middle">%s</text>' % (sx(i, len(pts)), sy(float(p['y'])) - 7, esc(fmt(p['y']))))
    out.append('</svg>')
    legend = '<div class="legend">%s</div>' % ''.join('<span><i class="sw %s"></i>%s</span>' % (PALETTE[j % len(PALETTE)], esc(s.get('name', '계열 %d' % (j + 1)))) for j, s in enumerate(series))
    headers = [ch.get('xlabel') or 'x'] + [s.get('name', '계열 %d' % (j + 1)) for j, s in enumerate(series)]
    rows = []
    for i in range(n):
        row = [labels[i] if i < len(labels) else str(i)]
        for s in series:
            row.append(fmt(s['points'][i]['y']) if i < len(s['points']) else '')
        rows.append(row)
    aria = '%s: %d개 계열, %d개 점, 최대 %s' % (ch.get('title', ''), len(series), n, fmt(max(ys)))
    return _figure(ch, '\n'.join(out) + legend, _data_table(headers, rows), aria)


def chart_matrix(ch):
    cols = ch['cols']
    head = '<tr><th>%s</th>%s</tr>' % (esc(ch.get('corner') or ''), ''.join('<th>%s</th>' % esc(c) for c in cols))
    rows = []
    for r in ch['rows']:
        cells = []
        for c in (r.get('cells') or []):
            if isinstance(c, dict):
                status = c.get('status')
                cls = (' class="cell-%s"' % STATUS_CLASS[status]) if status in STATUS_CLASS else ''
                cells.append('<td%s>%s</td>' % (cls, esc(c.get('value', status or ''))))
            else:
                cells.append('<td>%s</td>' % esc(c))
        rows.append('<tr><td><b>%s</b></td>%s</tr>' % (esc(r.get('label', '')), ''.join(cells)))
    table = '<div class="table-wrap"><table><thead>%s</thead><tbody>%s</tbody></table></div>' % (head, ''.join(rows))
    note = '<p class="note">%s</p>' % esc(ch['note']) if ch.get('note') else ''
    return '<figure class="chart"><figcaption>%s</figcaption>%s%s</figure>' % (esc(ch.get('title', '')), note, table)


def chart_html(ch):
    t = ch.get('type')
    if t == 'bar':
        return chart_bar(ch)
    if t == 'hbar':
        return chart_bar(ch, horizontal=True)
    if t == 'hist':
        return chart_bar(ch, hist=True)
    if t == 'compare':
        return chart_compare(ch)
    if t == 'stacked':
        return chart_stacked(ch)
    if t == 'line':
        return chart_line(ch)
    if t == 'matrix':
        return chart_matrix(ch)
    return ''


def charts_block(charts):
    if not charts:
        return ''
    return '<div class="charts">%s</div>' % ''.join(chart_html(c) for c in charts)


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


def stage_status(st):
    """단계 상태: 명시된 status > tests 에 FAIL 있으면 FAIL > tests 가 전부 PASS 면 PASS > 그 외 NOT_RUN."""
    if st.get('status') in STATUSES:
        return st['status']
    tests = st.get('tests') or []
    if any(t.get('status') == 'FAIL' for t in tests):
        return 'FAIL'
    if tests and all(t.get('status') == 'PASS' for t in tests):
        return 'PASS'
    if any(t.get('status') == 'HUMAN_CHECK' for t in tests):
        return 'HUMAN_CHECK'
    return 'NOT_RUN'


def stage_key_number(st):
    """스트립 카드에 보일 숫자 1개: results[0] > 규칙 발동 합 > 출력 수."""
    res = st.get('results') or []
    if res:
        return fmt(res[0].get('value')), res[0].get('unit') or '', res[0].get('label') or ''
    rules = st.get('rules') or []
    if rules:
        return fmt(sum(r.get('fired', 0) for r in rules)), '건', '규칙 발동'
    return str(len(st.get('outputs') or [])), '개', '출력'


def stage_strip(stages):
    cards = []
    for i, st in enumerate(stages):
        status = stage_status(st)
        val, unit, label = stage_key_number(st)
        cards.append('<div class="scard %s"><div class="st-head"><span class="st-name">%d. %s</span><span class="badge %s">%s</span></div>'
                     '<span class="st-key num">%s<small>%s</small></span><span class="meta">%s</span><span class="st-role">%s</span></div>' % (
                         STATUS_CLASS[status], i + 1, esc(st.get('name', '')), STATUS_CLASS[status], esc(status),
                         esc(val), esc(unit), esc(label), esc(clip(st.get('role') or st.get('notes') or '', 80))))
    return '<div class="strip">%s</div>' % ''.join(cards)


def stages_table(stages):
    rows = []
    for i, st in enumerate(stages):
        rows.append('<tr><td class="id">%d. %s</td><td><b>%s</b></td><td>%s</td><td>%s</td><td class="num">%d</td><td>%s</td></tr>' % (
            i + 1, esc(st.get('id', '')), esc(st.get('name', '')),
            '<br>'.join(esc(x) for x in st.get('inputs') or []) or '—',
            '<br>'.join(esc(x) for x in st.get('outputs') or []) or '—',
            len(st.get('rules') or []), esc(st.get('role') or st.get('notes') or '')))
    return ('<div class="table-wrap"><table><thead><tr><th>단계</th><th>이름</th><th>입력</th><th>출력</th><th class="num">규칙</th><th>역할</th></tr></thead>'
            '<tbody>%s</tbody></table></div>' % ''.join(rows))


def _rules_rows(stages, with_stage=True):
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
            stage_cell = '<td>%s</td>' % esc(st.get('name', '')) if with_stage else ''
            rows.append('<tr%s>%s<td>%s</td><td class="num">%s</td><td class="id">%s</td></tr>' % (
                cls, stage_cell, esc(r.get('name', '')), cell, esc(r.get('test') or '—')))
    return rows, total, zero


def rules_table(stages):
    rows, total, zero = _rules_rows(stages)
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


def stage_detail(st, i, decisions):
    """단계 카드: 역할 → 구현(파일:줄) → 방법 → 결과 숫자 → 차트 → 샘플 → 테스트 → 결정."""
    status = stage_status(st)
    parts = ['<article class="stage" id="stage-%d"><div class="st-top"><h3>%d. %s</h3><span class="badge %s">%s</span></div>' % (
        i + 1, i + 1, esc(st.get('name', '')), STATUS_CLASS[status], esc(status))]
    if st.get('role'):
        parts.append('<p class="role">%s</p>' % esc(st['role']))
    io_rows = '<tr><td>입력</td><td>%s</td></tr><tr><td>출력</td><td>%s</td></tr>' % (
        '<br>'.join(esc(x) for x in st.get('inputs') or []) or '—', '<br>'.join(esc(x) for x in st.get('outputs') or []) or '—')
    parts.append('<h4>입력 → 출력</h4><div class="table-wrap"><table><thead><tr><th>구분</th><th>내용</th></tr></thead><tbody>%s</tbody></table></div>' % io_rows)
    impl = st.get('implemented') or []
    if impl:
        rows = ''.join('<tr><td class="id">%s%s</td><td class="id">%s</td><td>%s</td></tr>' % (
            esc(it.get('file', '')), (':' + esc(it['lines'])) if it.get('lines') else '', esc(it.get('symbol') or '—'), esc(it.get('what', ''))) for it in impl)
        parts.append('<h4>구현 위치</h4><div class="table-wrap"><table><thead><tr><th>파일:줄</th><th>함수·클래스</th><th>무엇을 하나</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    method = st.get('method') or []
    if method:
        parts.append('<h4>방법 (순서대로)</h4><ol class="method">%s</ol>' % ''.join('<li>%s</li>' % esc(m) for m in method))
    results = st.get('results') or []
    if results:
        cells = ''.join('<div><span class="label">%s</span><span class="value num">%s<small>%s</small></span>%s</div>' % (
            esc(r.get('label', '')), esc(fmt(r.get('value'))), esc(r.get('unit') or ''),
            ('<span class="note">%s</span>' % esc(r['note'])) if r.get('note') else '') for r in results)
        parts.append('<h4>결과 숫자</h4><div class="mini">%s</div>' % cells)
    rules = st.get('rules') or []
    if rules:
        rows, total, zero = _rules_rows([st], with_stage=False)
        parts.append('<h4>규칙 발동 (규칙 %d개, 합계 %s건%s)</h4><div class="table-wrap"><table><thead><tr><th>규칙</th><th class="num">발동 건수</th><th>테스트</th></tr></thead><tbody>%s</tbody></table></div>' % (
            len(rules), fmt(total), (', 0건 %d개' % zero) if zero else '', ''.join(rows)))
    charts = st.get('charts') or []
    if charts:
        parts.append('<h4>차트</h4>' + charts_block(charts))
    samples = st.get('samples') or []
    if samples:
        rows = ''.join('<tr><td class="id">%s</td><td class="id">%s</td><td>%s</td></tr>' % (esc(s.get('before', '')), esc(s.get('after', '')), esc(s.get('note') or '')) for s in samples)
        parts.append('<h4>입력 → 출력 샘플</h4><div class="table-wrap"><table><thead><tr><th>입력(전)</th><th>출력(후)</th><th>비고</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    tests = st.get('tests') or []
    if tests:
        rows = ''.join('<tr><td class="id">%s</td><td><span class="badge %s">%s</span></td><td>%s</td></tr>' % (
            esc(t.get('name', '')), STATUS_CLASS.get(t.get('status'), 'off'), esc(t.get('status', '')), esc(t.get('evidence') or '—')) for t in tests)
        parts.append('<h4>테스트</h4><div class="table-wrap"><table><thead><tr><th>테스트</th><th>상태</th><th>근거</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    mine = [d for d in decisions if d.get('stage') == st.get('id')]
    if mine:
        rows = ''.join('<tr><td class="id">%s</td><td>%s</td></tr>' % (esc(d.get('where', '')), esc(d.get('what', ''))) for d in mine)
        parts.append('<h4>이 단계의 결정</h4><div class="table-wrap"><table><thead><tr><th>위치</th><th>결정</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    if st.get('evidence'):
        parts.append('<p class="meta">근거 폴더: <span class="id">%s</span></p>' % esc(st['evidence']))
    parts.append('</article>')
    return '\n'.join(parts)


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


def _head(title, css):
    return ['<!doctype html>', '<html lang="ko">', '<head>', '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<title>%s</title>' % esc(title), '<style>%s</style>' % css, '</head>', '<body>', '<main class="container">']


def build_html(spec, out_path, spec_label='docs/flow.json', tokens=None):
    """스펙 → HTML 문자열. (html, delta) 를 돌려준다. delta≠0 이면 합계 불일치."""
    tokens = tokens if tokens is not None else read_tokens()
    stages = spec.get('stages') or []
    decisions = spec.get('decisions') or []
    total, passed, excluded, delta = conservation_delta(spec)
    band, _ = band_html(spec)
    rules, fired_total, zero = rules_table(stages)
    ver_table, ver_summary, counts = verification_table(spec.get('verification') or [])
    n_rules = sum(len(st.get('rules') or []) for st in stages)
    n_pass, n_ver = counts.get('PASS', 0), len(spec.get('verification') or [])
    st_status = [stage_status(st) for st in stages]
    kpi = [
        ('단계', '%d<small>/%d PASS</small>' % (st_status.count('PASS'), len(stages)), ''),
        ('입력', fmt(total), '건'), ('통과', fmt(passed), '건'),
        ('제외', fmt(excluded), '건 (사유 %d)' % len(spec['conservation']['excluded'])),
        ('규칙 발동', fmt(fired_total), '건 (규칙 %d)' % n_rules),
        ('검증 PASS', '%d<small>/%d</small>' % (n_pass, n_ver), ''),
    ]
    kpi_html = ''.join('<div class="card"><span class="label">%s</span><span class="value num">%s<small>%s</small></span></div>' % (esc(k), v, esc(u))
                       for k, v, u in kpi)
    css = ':root {\n' + '\n'.join('  %s: %s;' % (k, v) for k, v in tokens) + '\n}\n' + PAGE_CSS
    status_line = 'FAIL: 합계 불일치 (차이 %+d)' % delta if delta else '합계 보존 확인'
    title = spec.get('title', '')
    if spec.get('stage_range'):
        title = '%s (%s단계)' % (title, spec['stage_range'])
    summary = spec.get('summary') or []
    summary_html = ('<div class="card summary"><ol>%s</ol></div>' % ''.join('<li>%s</li>' % esc(s) for s in summary)) if summary else ''
    doc = _head(title, css) + [
        '<header class="top"><h1>%s</h1><p class="meta">기준 %s / 스펙 %s / 생성 scripts/flowmap.py / %s</p></header>' % (
            esc(title), esc(spec.get('as_of') or '—'), esc(spec_label), esc(status_line)),
        summary_html,
        '<div class="kpi">%s</div>' % kpi_html,
        '<section class="section"><h2>단계 한눈에</h2><p class="why">단계마다 상태와 핵심 숫자 1개. 빨간 왼쪽 띠가 FAIL, 회색이 아직 검증 안 함이다. 아래 단계별 상세로 내려가 확인한다.</p>%s</section>' % stage_strip(stages),
        '<section class="section"><h2>파이프라인</h2><p class="why">입력이 어떤 단계를 지나 출력이 되는지. 상자 안 숫자는 그 단계의 규칙 수와 발동 건수 합이다.</p>',
        svg_pipeline(stages, False), svg_pipeline(stages, True),
        '<div style="margin-top:var(--s-4)">%s</div></section>' % stages_table(stages),
        '<section class="section"><h2>합계 보존</h2><p class="why">입력 건수 = 통과 + 사유별 제외. 맞지 않으면 어딘가에서 행이 조용히 사라지거나 두 번 세어진 것이다.</p>%s</section>' % band,
    ]
    if spec.get('charts'):
        doc.append('<section class="section"><h2>전체 차트</h2><p class="why">숫자가 맞는지 한눈에 보는 그림. 막대 위 값은 스펙의 숫자 그대로이고, 각 차트 아래 데이터 표를 펼쳐 확인한다.</p>%s</section>' % charts_block(spec['charts']))
    doc.append('<section class="section"><h2>단계별 상세</h2><p class="why">단계마다 역할 → 구현 위치(파일:줄) → 방법 → 결과 숫자 → 차트 → 입력→출력 샘플 → 테스트 → 결정 순서로. 코드를 열지 않고도 무엇을 어떻게 했고 무엇이 나왔는지 읽히게 한다.</p>%s</section>' % ''.join(
        stage_detail(st, i, decisions) for i, st in enumerate(stages)))
    doc += [
        '<section class="section"><h2>규칙 발동</h2><p class="why">규칙 1개 = 테스트 1개. 발동 0건인 규칙은 작동 증거가 없으므로 엣지 입력(scripts/make_edge_cases.py)으로 다시 확인한다.</p>%s</section>' % rules,
        '<section class="section"><h2>결정</h2><p class="why">지시받지 않고 정한 것과 그 위치(<code># 결정:</code> 주석). DECISIONS.md 1절과 같아야 한다.</p>%s</section>' % decisions_table(decisions),
        '<section class="section"><h2>검증</h2><p class="why">%s</p>%s</section>' % (esc(ver_summary), ver_table),
        '<section class="section"><h2>링크</h2><p class="why">출력 파일·근거 문서. 경로는 이 파일 위치 기준 상대경로로 연결했다.</p>%s</section>' % links_list(spec.get('links') or [], out_path),
        '<footer class="foot"><p class="meta">이 보고서의 숫자는 전부 %s 에서 왔고, 스펙의 숫자는 실행 결과(out/debug/NN/verify.json·out/audit.json·테스트 출력)에서 옮긴다. 암산한 숫자는 넣지 않는다.</p></footer>' % esc(spec_label),
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
    n_charts = len(spec.get('charts') or []) + sum(len(st.get('charts') or []) for st in stages)
    return '%s — 단계 %d · 규칙 %d · 발동 %s건 · 차트 %d · %s · 검증 PASS %d/%d' % (out_path, len(stages), n_rules, fmt(fired), n_charts, cons, n_pass, len(ver))


# ---------------------------------------------------------------- 인덱스
def build_index(dir_path, tokens=None):
    """폴더의 *.json 스펙(같은 이름의 .html 이 있는 것)을 모아 index.html 문자열을 만든다. (html, n) 반환."""
    tokens = tokens if tokens is not None else read_tokens()
    css = ':root {\n' + '\n'.join('  %s: %s;' % (k, v) for k, v in tokens) + '\n}\n' + PAGE_CSS
    cards = []
    for path in sorted(glob.glob(os.path.join(dir_path, '*.json'))):
        base = os.path.splitext(os.path.basename(path))[0]
        html_name = base + '.html'
        if not os.path.exists(os.path.join(dir_path, html_name)):
            continue
        spec, problem = load_spec(path)
        if problem or validate(spec):
            cards.append('<div class="card"><a href="%s">%s</a><span class="badge bad">스펙 오류</span></div>' % (esc(html_name), esc(base)))
            continue
        stages = spec.get('stages') or []
        st_status = [stage_status(st) for st in stages]
        _, _, _, delta = conservation_delta(spec)
        worst = 'FAIL' if ('FAIL' in st_status or delta) else ('PASS' if st_status and all(s == 'PASS' for s in st_status) else 'HUMAN_CHECK' if 'HUMAN_CHECK' in st_status else 'NOT_RUN')
        title = spec.get('title', base)
        if spec.get('stage_range'):
            title = '%s (%s단계)' % (title, spec['stage_range'])
        first = (spec.get('summary') or [''])[0]
        cards.append('<div class="card"><a href="%s">%s</a><span><span class="badge %s">%s</span> <span class="meta">단계 %d, PASS %d</span></span><span class="meta">%s</span><span class="id">%s</span></div>' % (
            esc(html_name), esc(title), STATUS_CLASS[worst], esc(worst), len(stages), st_status.count('PASS'), esc(clip(first, 120)), esc(html_name)))
    body = '<div class="index">%s</div>' % ''.join(cards) if cards else '<div class="banner">보고서가 없습니다. python3 scripts/flowmap.py --spec <스펙.json> --out %s/<이름>.html 로 만든 뒤 다시 --index 하세요</div>' % esc(dir_path)
    doc = _head('보고서 목록', css) + [
        '<header class="top"><h1>보고서 목록</h1><p class="meta">폴더 %s / 생성 scripts/flowmap.py --index</p></header>' % esc(dir_path),
        '<section class="section"><h2>단계 보고서</h2><p class="why">끝난 단계 묶음마다 한 장. 최신 묶음부터 읽고, 전체 보고서(all)가 있으면 그것이 제출용이다.</p>%s</section>' % body,
        '</main>', '</body>', '</html>', '',
    ]
    return '\n'.join(doc), len(cards)


# ---------------------------------------------------------------- 진입
def main(argv=None):
    ap = argparse.ArgumentParser(description='보고서 스펙 JSON → 단독 HTML 보고서(요약·단계 스트립·파이프라인·합계 보존·차트·단계별 상세·규칙·결정·검증). 표준 라이브러리만.')
    ap.add_argument('--spec', default=os.path.join('docs', 'flow.json'), help='보고서 스펙 JSON (기본 docs/flow.json, 예시 docs/flow.example.json)')
    ap.add_argument('--out', default=os.path.join('out', 'report.html'), help='생성할 HTML (기본 out/report.html)')
    ap.add_argument('--stages', default='all', help="단계 범위: 1-3 / 2 / 1,3 / all (기본 all). 제목에 '(1-3단계)' 가 붙는다")
    ap.add_argument('--check', action='store_true', help='스펙 검증만 하고 파일을 만들지 않음')
    ap.add_argument('--index', metavar='DIR', help='DIR 의 *.json+*.html 보고서를 모아 DIR/index.html 생성(다른 옵션 무시)')
    a = ap.parse_args(argv)

    if a.index:
        if not os.path.isdir(a.index):
            err('폴더가 없습니다: %s' % a.index)
            return 2
        text, n = build_index(a.index)
        out = os.path.join(a.index, 'index.html')
        with open(out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text)
        print('%s — 보고서 %d개' % (out, n))
        print('미리보기(사람이 다른 터미널에서 실행): python3 design-kit/serve.py $PORT --dir %s --index index.html  → 미리보기 탭에서 /index.html' % a.index)
        return 0

    spec, problem = load_spec(a.spec)
    if problem == 'missing':
        err('스펙 파일이 없습니다: %s' % a.spec)
        err('다음 행동: cp docs/flow.example.json docs/flow.json 로 시작해 단계·규칙·건수를 실행 결과(out/debug/NN/verify.json·out/audit.json)로 채우세요')
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
    try:
        spec = filter_spec(spec, a.stages)
    except ValueError as e:
        err(str(e))
        return 2
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
