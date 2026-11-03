#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decide.py — 결정 대기함(decisions/pending.md)을 브라우저 폼으로 답하고 answers.md 에 기록한다 (표준 라이브러리, Python 3.9).

  python3 scripts/decide.py                 # 0.0.0.0:8010 에 폼. 미리보기에서 8010 을 연다(PORT 환경변수는 보지 않는다 — 앱 8000 과 겹치지 않게)
  python3 scripts/decide.py --port 8011     # 포트 지정(8010 이 막혔을 때)
  python3 scripts/decide.py --list          # 미답 항목 표만 터미널에 (서버 없음)
  python3 scripts/decide.py --apply         # answers.md 의 답(손으로 쓴 줄·복수 ID 포함)을 pending.md 의 고른 후보 [x] 로 옮긴다 (서버 없음)
  python3 scripts/decide.py --dry-run       # pending.md 파싱 결과를 JSON 으로 (서버 없음)

동작  GET /            미답(`- [ ]`) 항목마다 제목·영향·담당자 확인(필요하면 담당자 질문)·후보 라디오(기타는 텍스트 칸)·메모. 답한 항목은 '답변됨' 으로 접어 보인다.
                       제목에 '(예시' 가 든 견본 항목은 세지도 띄우지도 않는다(status.py 와 같은 규칙).
                       answers.md 에 답이 있는데 pending 에 [x] 가 없는 항목은 위쪽 카드에 모으고(옮기기 버튼) 그 항목 카드에도 표시한다.
      POST /answer     answers.md 에 `D07: A (메모: …) @HH:MM` 한 줄 append + pending.md 의 그 후보를 `[x]` 로(다른 줄은 그대로).
      POST /apply      answers.md 의 답을 pending.md 의 고른 후보 `[x]` 로 옮긴다(--apply 와 같음). 다른 후보가 이미 [x] 면 충돌로 알리고 바꾸지 않는다.
      GET /design-kit/ design-kit 의 *.css 만 정적 제공(tokens·base·components).
거부  없는 ID·빈 선택·이미 답한 항목·폼이 아닌 본문 → 400 과 메시지 / 루트 밖 경로(..) → 403 / 64KB 넘는 본문 → 413.
형식  pending.md 항목(AGENTS.md 5절): `## D07 제목   (영향: … | 담당자 확인: 필요)` + `- [ ] A. 후보 — 근거 (추천)` 2~4개 + `담당자 질문: …`(필요할 때) + `메모:`.
      결정은 항상 사람이 한다 — 기본값·시간 경과로 대신 정하는 필드는 없다(옛 형식의 `기본값`·`안 정하면` 은 읽고 무시한다).
      answers.md 한 줄에 복수 ID `D12,D71: A (메모: …) @HH:MM` 도 읽는다(각 ID 에 같은 답). 폼은 항목마다 한 줄씩 쓴다.
종료 코드  0 정상 / 1 pending.md 없음·포트 열기 실패·--apply 충돌 또는 오류 / 2 인자 오류.
순수 함수  parse_pending · parse_answers · format_answer_line · append_answer · mark_answered · apply_answers
          (파일을 만지지 않는다; scripts/tests/test_decide.py 가 검증).
"""
import argparse
import datetime as dt
import html
import http.server
import json
import os
import re
import sys
import threading
import urllib.parse

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_PENDING = os.path.join(ROOT, 'decisions', 'pending.md')
DEFAULT_ANSWERS = os.path.join(ROOT, 'decisions', 'answers.md')
DEFAULT_KIT = os.path.join(ROOT, 'design-kit')
DEFAULT_PORT = 8010
EXAMPLE_MARK = '(예시'   # 제목에 이 표시가 든 항목은 형식 견본 — 미답·폼·목록에서 뺀다(status.py 와 같은 규칙)
# 결정: 본문 상한 64KB / 메모 500자·기타 200자면 충분하고 실수로 파일을 올리는 사고를 막는다 / 무제한
MAX_BODY = 64 * 1024
ANSWERS_HEADER = (
    '# 결정 답변 (answers) — 사람이 쓰고 Codex 가 task 끝·CP 에서 읽는다\n'
    '형식: `D07: A (메모: …) @HH:MM` 한 줄 = 답 하나 (복수 ID `D12,D71: A (메모: …) @HH:MM` 는 각 ID 에 같은 답, '
    '기타를 고르면 `D07: C (기타: 내용) (메모: …) @HH:MM`). '
    'decide.py 가 append 하고 손으로 써도 된다. 손으로 쓴 줄은 `decide.py --apply` 로 pending 의 고른 후보에 `[x]` 를 옮기고, Codex 는 반영한 뒤 그 후보 줄을 `- [x] A. … 반영 HH:MM` 으로 바꾼다(별도 줄 금지).\n'
)

ID_RE = re.compile(r'^## (D\d+)\b\s*(.*?)\s*$')
META_RE = re.compile(r'^(.*?)\s*\(([^()]*(?:영향|담당자 확인|기본값|안 정하면)[^()]*)\)\s*$')
CAND_RE = re.compile(r'^- \[([ xX])\]\s*(?:반영\s*(\d\d:\d\d)\s*)?([A-Za-z0-9])[.)]\s*(.*?)\s*$')
TAIL_APPLIED_RE = re.compile(r'\s*반영\s*(\d\d:\d\d)\s*$')
RECOMMEND_RE = re.compile(r'\s*\(추천\)\s*')
OTHER_RE = re.compile(r'^기타\s*[:：]?\s*(.*)$')
MEMO_RE = re.compile(r'^메모:\s*(.*?)\s*$')
QUESTION_RE = re.compile(r'^담당자 질문:\s*(.*?)\s*$')
ANSWER_RE = re.compile(r'^(D\d+(?:\s*,\s*D\d+)*):\s*(\S+)(?:\s+\(기타:\s*(.*?)\))?(?:\s+\(메모:\s*(.*?)\))?\s*@(\d\d:\d\d)\s*$')


# ---------------------------------------------------------------- 순수 함수: 파싱
def parse_pending(text):
    """pending.md 본문 → 항목 목록. 항목은 `## Dnn …` 부터 다음 제목 전까지. 줄 번호(line_no)는 mark_answered 가 쓴다.
    항목 dict: id·title·impact·ask·question·memo·candidates[]·answered·answer·applied·line_no
    ask: '필요' / '불필요 — …' / '' (담당자 확인), question: 담당자에게 보낼 질문 한 줄
    후보 dict: key·text·recommended·other·checked·applied·line_no"""
    items, cur = [], None
    for no, raw in enumerate(text.split('\n')):
        line = raw.rstrip('\r')
        m = ID_RE.match(line)
        if m:
            cur = {'id': m.group(1), 'title': '', 'impact': '', 'ask': '', 'question': '', 'memo': '',
                   'candidates': [], 'answered': False, 'answer': '', 'applied': '', 'line_no': no}
            rest = m.group(2)
            mm = META_RE.match(rest)
            if mm:
                cur['title'] = mm.group(1).strip()
                for part in mm.group(2).split('|'):
                    key, _, val = part.partition(':')
                    key, val = key.strip(), val.strip()
                    if key == '영향':
                        cur['impact'] = val
                    elif key == '담당자 확인':
                        cur['ask'] = val
                    # 결정: 옛 형식의 기본값·안 정하면 은 무시 / 결정은 항상 사람이 한다(사용자 지시 10/30) / 기본값으로 자동 진행
            else:
                cur['title'] = rest.strip()
            items.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith('#'):          # 다른 제목이 나오면 항목이 끝난다
            cur = None
            continue
        mc = CAND_RE.match(line)
        if mc:
            text_part = mc.group(4)
            applied = mc.group(2) or ''
            mt = TAIL_APPLIED_RE.search(text_part)
            if mt:
                applied, text_part = mt.group(1), text_part[:mt.start()].rstrip()
            recommended = bool(RECOMMEND_RE.search(text_part))
            text_part = RECOMMEND_RE.sub(' ', text_part).strip()
            mo = OTHER_RE.match(text_part)
            other = bool(mo)
            if mo:
                filled = mo.group(1).strip().strip('_').strip()
                text_part = '기타' + (': ' + filled if filled else '')
            cur['candidates'].append({'key': mc.group(3), 'text': text_part, 'recommended': recommended, 'other': other,
                                      'checked': mc.group(1) != ' ', 'applied': applied, 'line_no': no})
            continue
        mq = QUESTION_RE.match(line)
        if mq:
            cur['question'] = mq.group(1)
            continue
        mm2 = MEMO_RE.match(line)
        if mm2:
            cur['memo'] = mm2.group(1)
    for it in items:
        checked = [c for c in it['candidates'] if c['checked']]
        it['answered'] = bool(checked)
        it['answer'] = '·'.join(c['key'] for c in checked)
        it['applied'] = next((c['applied'] for c in checked if c['applied']), '')
    return items


def parse_answers(text):
    """answers.md 본문 → {id: {choice, other, memo, time}}. 같은 ID 가 여러 줄이면 마지막 줄이 이긴다.
    한 줄에 복수 ID(`D12,D71: A (메모: …) @HH:MM`)면 각 ID 에 같은 답을 따로 넣는다."""
    out = {}
    for raw in (text or '').split('\n'):
        m = ANSWER_RE.match(raw.strip())
        if m:
            for item_id in re.split(r'\s*,\s*', m.group(1)):
                out[item_id] = {'choice': m.group(2), 'other': m.group(3) or '', 'memo': m.group(4) or '', 'time': m.group(5)}
    return out


def is_example(it):
    """제목에 '(예시' 가 든 형식 견본 항목인가. 견본은 세지도 폼에 띄우지도 않는다(status.py 와 같은 규칙)."""
    return EXAMPLE_MARK in (it.get('title') or '')


def unanswered(items):
    """고른 후보(`[x]`)가 없는 항목. 예시 항목은 뺀다."""
    return [it for it in items if not it['answered'] and not is_example(it)]


def answered_items(items):
    """고른 후보가 있는 항목. 예시 항목은 뺀다."""
    return [it for it in items if it['answered'] and not is_example(it)]


def waiting_answers(items, answers):
    """answers.md 에 답이 있는데 pending 에 [x] 가 없는 미답 항목 → [(항목, 답 dict)] (pending 순서)."""
    return [(it, answers[it['id']]) for it in unanswered(items) if it['id'] in (answers or {})]


def answer_text(item_id, ans):
    """answers.md 답 dict → 'D01: A (기타: …) @11:40' 한 줄(표시용)."""
    other = (' (기타: %s)' % ans['other']) if ans.get('other') else ''
    return '%s: %s%s @%s' % (item_id, ans.get('choice', ''), other, ans.get('time', ''))


def find_item(items, item_id):
    item_id = (item_id or '').strip()
    if not item_id:
        raise ValueError('결정 ID 가 비었음 — 폼의 id(예: D07) 가 빠졌다')
    for it in items:
        if it['id'] == item_id:
            return it
    known = '·'.join(it['id'] for it in items) or '(항목 없음)'
    raise ValueError('없는 ID: %s — pending.md 의 제목(## D..)과 맞춘다. 현재: %s' % (item_id, known))


def pick_candidate(item, choice, other=''):
    """항목에서 후보를 고른다. 빈 선택·없는 후보·이미 답한 항목·기타 내용 없음은 ValueError."""
    if item['answered']:
        raise ValueError('이미 답한 항목: %s (답: %s) — 바꾸려면 pending.md 의 [x] 를 [ ] 로 되돌린다' % (item['id'], item['answer']))
    choice = (choice or '').strip()
    if not choice:
        raise ValueError('후보를 고르지 않음: %s — 라디오에서 하나를 고른다' % item['id'])
    keys = '·'.join(c['key'] for c in item['candidates'])
    for c in item['candidates']:
        if c['key'] == choice:
            if c['other'] and not (other or '').strip():
                raise ValueError('기타 내용이 비었음: %s %s — 기타 칸에 내용을 적는다' % (item['id'], choice))
            return c
    raise ValueError('없는 후보: %s %s — 가능한 후보: %s' % (item['id'], choice, keys or '(없음)'))


def _one_line(s, limit):
    s = re.sub(r'\s*[\r\n]+\s*', ' / ', (s or '').strip())
    return s[:limit]


# ---------------------------------------------------------------- 순수 함수: 기록
def format_answer_line(item_id, choice, other='', memo='', hhmm=''):
    """`D07: A (기타: …) (메모: …) @HH:MM`. 기타·메모는 있을 때만 붙는다."""
    parts = ['%s: %s' % (item_id, choice)]
    other, memo = _one_line(other, 200), _one_line(memo, 500)
    if other:
        parts.append('(기타: %s)' % other)
    if memo:
        parts.append('(메모: %s)' % memo)
    parts.append('@%s' % (hhmm or dt.datetime.now().strftime('%H:%M')))
    return ' '.join(parts)


def append_answer(answers_text, item_id, choice, other='', memo='', hhmm=''):
    """answers.md 본문 끝에 답 한 줄을 붙인 새 본문을 돌려준다. 비어 있으면 머리 2줄부터 쓴다."""
    text = answers_text or ''
    if not text.strip():
        text = ANSWERS_HEADER
    if not text.endswith('\n'):
        text += '\n'
    return text + format_answer_line(item_id, choice, other, memo, hhmm) + '\n'


def mark_answered(pending_text, item_id, choice, other=''):
    """pending.md 본문에서 해당 후보 줄만 `[x]` 로 바꾼 새 본문을 돌려준다(기타면 `____` 자리에 내용). 다른 줄은 그대로.
    없는 ID·없는 후보·빈 선택·이미 답한 항목은 ValueError."""
    items = parse_pending(pending_text)
    item = find_item(items, item_id)
    cand = pick_candidate(item, choice, other)
    lines = pending_text.split('\n')
    line = lines[cand['line_no']]
    line = line.replace('[ ]', '[x]', 1)
    if cand['other']:
        other = _one_line(other, 200)
        line = line.replace('____', other, 1) if '____' in line else line.rstrip() + ' ' + other
    lines[cand['line_no']] = line
    return '\n'.join(lines)


def apply_answers(pending_text, answers):
    """answers.md 의 답(parse_answers 결과)을 pending 본문의 고른 후보 `[x]` 로 옮긴 새 본문과 결과를 돌려준다(파일은 만지지 않는다).
    같은 후보가 이미 `[x]` 면 건너뛰고(same), 다른 후보가 `[x]` 면 충돌(conflict)로 남기고 바꾸지 않는다.
    없는 ID·없는 후보·기타 내용 없음은 error. 옮긴 줄은 폼의 기록과 같은 모양(`- [x] A. …`)이다 — `반영 HH:MM` 은 Codex 가 붙인다.
    출력: (새 본문, {'applied': [(id, 후보)], 'same': [id], 'conflict': [(id, pending 답, answers 답)], 'error': [(id, 메시지)]})"""
    text = pending_text
    res = {'applied': [], 'same': [], 'conflict': [], 'error': []}
    order = [it['id'] for it in parse_pending(text)]
    ids = [i for i in order if i in answers] + sorted(i for i in answers if i not in order)
    for item_id in ids:
        ans = answers[item_id]
        try:
            item = find_item(parse_pending(text), item_id)
            if item['answered']:
                if item['answer'] == ans['choice']:
                    res['same'].append(item_id)
                else:
                    res['conflict'].append((item_id, item['answer'], ans['choice']))
                continue
            text = mark_answered(text, item_id, ans['choice'], ans.get('other', ''))
        except ValueError as e:
            res['error'].append((item_id, str(e)))
            continue
        res['applied'].append((item_id, ans['choice']))
    return text, res


def summarize_apply(res):
    """apply_answers 결과 → (한 줄 요약, 충돌·오류 줄 목록)."""
    moved = ', '.join('%s=%s' % kv for kv in res['applied'])
    head = '옮김 %d건%s · 이미 같음 %d · 충돌 %d · 오류 %d' % (
        len(res['applied']), (' (%s)' % moved) if moved else '', len(res['same']), len(res['conflict']), len(res['error']))
    problems = ['충돌 %s: pending [x] %s · answers.md %s → 한쪽을 고친 뒤 다시 옮긴다' % c for c in res['conflict']]
    problems += ['오류 %s: %s' % e for e in res['error']]
    return head, problems


# ---------------------------------------------------------------- 파일 I/O
_LOCK = threading.Lock()


def read_text(path):
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


def write_text(path, text):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)


def record_answer(pending_path, answers_path, item_id, choice, other='', memo='', hhmm=None):
    """두 파일을 함께 갱신한다. 검증이 먼저라 실패하면 아무 파일도 바뀌지 않는다. 기록한 줄을 돌려준다."""
    hhmm = hhmm or dt.datetime.now().strftime('%H:%M')
    with _LOCK:
        pending = read_text(pending_path)
        new_pending = mark_answered(pending, item_id, choice, other)
        answers = read_text(answers_path) if os.path.exists(answers_path) else ''
        new_answers = append_answer(answers, item_id, choice, other, memo, hhmm)
        write_text(pending_path, new_pending)
        write_text(answers_path, new_answers)
    return new_answers.rstrip('\n').split('\n')[-1]


def apply_file(pending_path, answers_path):
    """answers.md 를 읽어 pending.md 의 고른 후보를 [x] 로 옮긴다(폼 기록과 같은 잠금). 바뀐 것이 있을 때만 pending 을 쓴다.
    출력: apply_answers 의 결과 dict. answers.md 는 바꾸지 않는다."""
    with _LOCK:
        pending = read_text(pending_path)
        answers = parse_answers(read_text(answers_path)) if os.path.exists(answers_path) else {}
        new_pending, res = apply_answers(pending, answers)
        if new_pending != pending:
            write_text(pending_path, new_pending)
    return res


# ---------------------------------------------------------------- 화면 (design-kit 토큰만, 외부 URL 0, JS 0)
PAGE_HEAD = '''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>결정 대기함</title>
<link rel="stylesheet" href="/design-kit/tokens.css">
<link rel="stylesheet" href="/design-kit/base.css">
<link rel="stylesheet" href="/design-kit/components.css">
<style>
  .hdr { padding: var(--s-5) 0 var(--s-3); }
  fieldset { border: 0; padding: 0; margin: 0; min-width: 0; }
  legend { padding: 0; }
  .kv { display: grid; grid-template-columns: max-content 1fr; gap: var(--s-1) var(--s-3); margin: 0 0 var(--s-2); font-size: 13px; }
  .kv dt { color: var(--muted); font-weight: 600; }
  .kv dd { margin: 0; }
  .choices { display: grid; gap: var(--s-2); }
  .check span { flex: 1; }
  .check .badge { flex: none; font-size: 11px; margin-left: var(--s-2); }
  details { padding: var(--s-2) var(--s-3); }
  summary { cursor: pointer; font-weight: 600; min-height: 44px; display: flex; align-items: center; gap: var(--s-2); flex-wrap: wrap; }
  .done-list { margin: var(--s-2) 0 0; padding-left: var(--s-5); font-size: 13px; color: var(--ink-2); }
  .done-list li { margin-bottom: var(--s-1); }
</style>
</head>
<body>
'''


def _kv(label, value):
    e = html.escape
    return '<dt>%s</dt><dd>%s</dd>' % (e(label), e(value) if value else '-')


def render_form(it, ans=None):
    """미답 항목 카드. ans(answers.md 의 이 항목 답)가 있으면 '반영 전' 표시를 붙인다."""
    e = html.escape
    iid = it['id']
    h = ['<section class="card" aria-labelledby="h-%s">' % e(iid),
         '<form class="form" method="post" action="/answer">',
         '<input type="hidden" name="id" value="%s">' % e(iid),
         '<h2 id="h-%s"><span class="id">%s</span> %s</h2>' % (e(iid), e(iid), e(it['title']) or '(제목 없음)'),
         '<dl class="kv">' + _kv('영향', it['impact']) + _kv('담당자 확인', it['ask']) + '</dl>',
         ('<div class="banner info"><b>담당자에게 먼저 물어보기</b><span>%s</span></div>' % e(it['question'])) if it['question'] else '',
         ('<div class="banner warn"><b>answers.md 에 답 있음</b><span>%s — pending 에는 아직 [x] 가 없다. 같은 답이면 위의 '
          '옮기기 버튼을 누른다. 여기서 다른 답을 고르면 새 줄이 쌓이고 나중 줄이 이긴다.</span></div>' % e(answer_text(iid, ans))) if ans else '',
         '<fieldset class="field"><legend class="label">후보 (하나를 고른다)</legend><div class="choices">']
    has_other = False
    for c in it['candidates']:
        has_other = has_other or c['other']
        label = '%s. %s' % (c['key'], c['text'] + (' (아래 칸에 적는다)' if c['other'] else ''))
        badge = '<span class="badge brand plain">추천</span>' if c['recommended'] else ''
        # 결정: 라디오 / 결정 하나 = 답 하나이고 answers 줄 형식 `D07: A` 가 단일 선택이다 / 체크박스(복수 선택)
        h.append('<label class="check"><input type="radio" name="choice" value="%s" required><span>%s</span>%s</label>' % (e(c['key']), e(label), badge))
    if not it['candidates']:
        h.append('<p class="meta">후보 줄(`- [ ] A. …`)이 없다. pending.md 형식을 확인한다.</p>')
    h.append('</div></fieldset>')
    if has_other:
        h.append('<div class="field"><label for="%s-other">기타 내용 (기타를 골랐을 때)</label>'
                 '<input type="text" id="%s-other" name="other" maxlength="200"></div>' % (e(iid), e(iid)))
    h.append('<div class="field"><label for="%s-memo">메모 (선택)</label>'
             '<textarea id="%s-memo" name="memo" rows="2" maxlength="500"></textarea>'
             '<span class="help">고른 이유나 조건을 한 줄로. answers.md 에 함께 남는다.</span></div>' % (e(iid), e(iid)))
    h.append('<div class="btn-row"><button class="btn brand" type="submit">%s 답 기록</button></div>' % e(iid))
    h.append('</form></section>')
    return '\n'.join(h)


def render_done(it, ans):
    e = html.escape
    badge = '<span class="badge ok">답변됨 %s</span>' % e(it['answer'])
    if it['applied']:
        badge += '<span class="badge info plain">반영 %s</span>' % e(it['applied'])
    h = ['<details class="card flat">',
         '<summary><span class="id">%s</span> %s %s</summary>' % (e(it['id']), e(it['title']), badge),
         '<ul class="done-list">']
    for c in it['candidates']:
        h.append('<li>%s %s. %s%s</li>' % ('[x]' if c['checked'] else '[ ]', e(c['key']), e(c['text']), ' (추천)' if c['recommended'] else ''))
    h.append('</ul>')
    memo = (ans or {}).get('memo') or it['memo']
    when = (ans or {}).get('time', '')
    if memo or when:
        h.append('<p class="meta">%s%s</p>' % (('메모: ' + e(memo)) if memo else '', (' @' + e(when)) if when else ''))
    h.append('</details>')
    return '\n'.join(h)


def render_page(items, answers=None, notice=None):
    """items(parse_pending) + answers(parse_answers) → HTML 문자열. notice=(kind, message) 는 상단 배너."""
    e = html.escape
    answers = answers or {}
    open_items, done_items = unanswered(items), answered_items(items)
    waiting = waiting_answers(items, answers)
    h = [PAGE_HEAD, '<main class="container narrow">',
         '<header class="hdr"><div class="row between"><h1>결정 대기함</h1><a class="btn sm" href="/">다시 읽기</a></div>',
         '<p class="lead">decisions/pending.md 의 미답 항목에 답한다. 기록하면 answers.md 에 한 줄이 쌓이고 Codex 가 task 끝·CP 에서 읽는다. '
         '결정은 항상 사람이 하며 Codex 는 답이 올 때까지 이 결정에 기대는 작업을 하지 않는다. 파란 상자가 있는 항목은 담당자에게 그 질문을 먼저 보내고 답을 메모에 적는다.</p>',
         '<p class="meta">미답 %d건 · 답변됨 %d건 · 파일 decisions/pending.md</p></header>' % (len(open_items), len(done_items))]
    if notice:
        kind, msg = notice
        head = {'ok': '기록됨', 'bad': '기록 안 됨'}.get(kind, '알림')
        h.append('<div class="banner %s" role="status"><b>%s</b><span>%s</span></div>' % (e(kind), e(head), e(msg)))
    if waiting:
        h.append('<section class="card" aria-labelledby="h-apply" style="margin-top: var(--s-4)">'
                 '<form class="form" method="post" action="/apply"><h2 id="h-apply">answers.md 에 답이 있는 미답 %d건</h2>'
                 '<p class="meta">%s — pending.md 의 고른 후보를 [x] 로 옮긴다(answers.md 는 그대로, 손으로 쓴 줄·복수 ID 줄 포함).</p>'
                 '<div class="btn-row"><button class="btn brand" type="submit">pending 에 옮기기</button></div></form></section>'
                 % (len(waiting), e(', '.join('%s=%s' % (it['id'], a['choice']) for it, a in waiting))))
    if open_items:
        h.append('<div class="stack" style="margin-top: var(--s-4)">')
        h.extend(render_form(it, answers.get(it['id'])) for it in open_items)
        h.append('</div>')
    else:
        h.append('<div class="empty" style="margin-top: var(--s-4)"><b>미답 항목이 없습니다</b>'
                 'Codex 가 pending.md 에 새 결정을 적으면 여기에 나타난다. 다시 읽기를 누르면 갱신된다.</div>')
    if done_items:
        h.append('<section class="section"><h2>답변됨 %d건</h2><div class="stack tight">' % len(done_items))
        h.extend(render_done(it, answers.get(it['id'])) for it in done_items)
        h.append('</div></section>')
    h.append('</main>\n</body>\n</html>\n')
    return '\n'.join(h)


# ---------------------------------------------------------------- 서버
def clean_path(raw):
    """요청 경로를 디코드해 돌려준다. `..` 세그먼트나 역슬래시가 있으면 None(→ 403)."""
    path = urllib.parse.unquote(urllib.parse.urlsplit(raw).path or '/')
    if '\\' in path or any(seg == '..' for seg in path.split('/')):
        return None
    return path


class DecideHandler(http.server.BaseHTTPRequestHandler):
    server_version = 'decide/1.0'
    protocol_version = 'HTTP/1.0'

    def log_message(self, fmt, *args):  # 진단은 stderr 한 줄
        sys.stderr.write('[decide] %s %s\n' % (self.address_string(), fmt % args))
        sys.stderr.flush()

    def _send(self, status, body, ctype='text/html; charset=utf-8'):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def _text(self, status, msg):
        self._send(status, msg + '\n', 'text/plain; charset=utf-8')

    def _page(self, status, notice=None):
        cfg = self.server.cfg
        try:
            items = parse_pending(read_text(cfg['pending']))
            answers = parse_answers(read_text(cfg['answers'])) if os.path.exists(cfg['answers']) else {}
        except OSError as e:
            return self._text(500, 'pending.md 를 읽지 못함: %s — 경로를 확인한다' % e)
        self._send(status, render_page(items, answers, notice))

    def _static(self, path):
        kit = os.path.realpath(self.server.cfg['kit'])
        rel = path[len('/design-kit/'):]
        if not rel.endswith('.css'):
            return self._text(404, '정적 파일은 design-kit 의 *.css 만 제공한다: %s' % path)
        full = os.path.realpath(os.path.join(kit, rel))
        if not full.startswith(kit + os.sep):
            return self._text(403, '루트 밖 경로는 열 수 없다: %s' % path)
        if not os.path.isfile(full):
            return self._text(404, '없는 파일: %s' % path)
        with open(full, 'rb') as fh:
            self._send(200, fh.read(), 'text/css; charset=utf-8')

    def _apply(self):
        cfg = self.server.cfg
        try:
            res = apply_file(cfg['pending'], cfg['answers'])
        except OSError as e:
            return self._text(500, '파일을 쓰지 못함: %s — decisions/ 폴더 권한을 확인한다' % e)
        head, problems = summarize_apply(res)
        kind = 'ok' if not problems else ('warn' if res['applied'] else 'bad')
        self._page(200, (kind, ' / '.join([head] + problems)))

    def do_GET(self):
        path = clean_path(self.path)
        if path is None:
            return self._text(403, '루트 밖 경로는 열 수 없다: %s' % self.path)
        if path == '/':
            return self._page(200)
        if path.startswith('/design-kit/'):
            return self._static(path)
        self._text(404, '없는 경로: %s — 폼은 / 에 있다' % path)

    def do_POST(self):
        path = clean_path(self.path)
        if path is None:
            return self._text(403, '루트 밖 경로는 열 수 없다: %s' % self.path)
        if path not in ('/', '/answer', '/apply'):
            return self._text(404, '없는 경로: %s — 답은 POST /answer, answers.md 옮기기는 POST /apply 로 보낸다' % path)
        try:
            length = int(self.headers.get('Content-Length') or '0')
        except ValueError:
            return self._page(400, ('bad', 'Content-Length 가 숫자가 아님'))
        if length > MAX_BODY:
            return self._text(413, '본문이 너무 큼: %d bytes (상한 %d) — 메모를 줄인다' % (length, MAX_BODY))
        body = self.rfile.read(length).decode('utf-8', 'replace') if length > 0 else ''
        if path == '/apply':
            return self._apply()
        ctype = self.headers.get('Content-Type', '')
        if 'application/x-www-form-urlencoded' not in ctype.lower():
            return self._page(400, ('bad', '폼 본문이 아님(Content-Type=%s) — 페이지의 폼으로 보낸다' % (ctype or '없음')))
        form = urllib.parse.parse_qs(body, keep_blank_values=True)

        def first(name):
            return (form.get(name) or [''])[0]

        cfg = self.server.cfg
        try:
            line = record_answer(cfg['pending'], cfg['answers'], first('id'), first('choice'), first('other'), first('memo'))
        except ValueError as e:
            return self._page(400, ('bad', str(e)))
        except OSError as e:
            return self._text(500, '파일을 쓰지 못함: %s — decisions/ 폴더 권한을 확인한다' % e)
        # 결정: 기록 후 같은 응답에 페이지(200) / 미리보기에서 리다이렉트 1회를 아끼고 결과 배너를 바로 본다 / 303 리다이렉트
        self._page(200, ('ok', '%s 를 decisions/answers.md 에 적었다. Codex 가 task 끝·CP 에서 반영한다.' % line))


def make_server(host, port, pending_path, answers_path, kit_dir):
    """설정을 server.cfg 에 실어 ThreadingHTTPServer 를 만든다(serve_forever 는 호출자가). 포트 실패는 OSError."""
    http.server.ThreadingHTTPServer.allow_reuse_address = os.name != 'nt'
    srv = http.server.ThreadingHTTPServer((host, port), DecideHandler)
    srv.daemon_threads = True
    srv.cfg = {'pending': os.path.abspath(pending_path), 'answers': os.path.abspath(answers_path), 'kit': os.path.abspath(kit_dir)}
    return srv


# ---------------------------------------------------------------- 터미널 출력
def print_list(items, answers=None):
    answers = answers or {}
    rows = unanswered(items)
    done = len(answered_items(items))
    if not rows:
        print('미답 항목 없음 (답변됨 %d건)' % done)
        return
    print('ID | 제목 | 영향 | 담당자 확인 | 후보')
    for it in rows:
        cands = '·'.join('%s%s%s' % (c['key'], '(추천)' if c['recommended'] else '', ' 기타' if c['other'] else '') for c in it['candidates'])
        print(' | '.join([it['id'], it['title'] or '-', it['impact'] or '-', it['ask'] or '-', cands or '-']))
        if it['question']:
            print('   └ 담당자 질문: %s' % it['question'])
        if it['id'] in answers:
            print('   └ answers.md 에 답 있음: %s → pending 반영 전(python3 scripts/decide.py --apply)'
                  % answer_text(it['id'], answers[it['id']]))
    n_wait = sum(1 for it in rows if it['id'] in answers)
    print('미답 %d건 · 답변됨 %d건%s' % (len(rows), done, (' · answers.md 에 답 있음 %d건(--apply 로 옮긴다)' % n_wait) if n_wait else ''))


def main():
    ap = argparse.ArgumentParser(description='결정 대기함 폼 서버 (decisions/pending.md ↔ answers.md)',
                                 epilog='서버는 Ctrl+C 로 끝낸다. 답은 answers.md 에 쌓이고 pending.md 의 후보가 [x] 로 바뀐다.')
    ap.add_argument('--port', type=int, default=DEFAULT_PORT,
                    help='포트 (기본 %d — PORT 환경변수는 보지 않는다: 앱 서버 8000 과 겹치지 않게)' % DEFAULT_PORT)
    ap.add_argument('--host', default='0.0.0.0', help='바인드 주소 (기본 0.0.0.0)')
    ap.add_argument('--pending', default=DEFAULT_PENDING, help='pending.md 경로 (기본 decisions/pending.md)')
    ap.add_argument('--answers', default=DEFAULT_ANSWERS, help='answers.md 경로 (기본 decisions/answers.md, 없으면 만든다)')
    ap.add_argument('--kit', default=DEFAULT_KIT, help='design-kit 폴더 (CSS 정적 제공, 기본 design-kit/)')
    ap.add_argument('--list', action='store_true', help='미답 항목 표만 출력하고 끝낸다')
    ap.add_argument('--apply', action='store_true',
                    help='answers.md 의 답(손으로 쓴 줄·복수 ID 포함)을 pending.md 의 고른 후보 [x] 로 옮기고 끝낸다(충돌·오류면 exit 1)')
    ap.add_argument('--dry-run', action='store_true', help='pending.md 파싱 결과를 JSON 으로 출력하고 끝낸다')
    a = ap.parse_args()
    if not os.path.isfile(a.pending):
        print('pending.md 없음: %s — Codex 에게 결정 항목을 적게 하거나 decisions/pending.md 를 만든다' % a.pending, file=sys.stderr)
        return 1
    if a.apply:
        head, problems = summarize_apply(apply_file(a.pending, a.answers))
        print('apply: ' + head)
        for line in problems:
            print('  ' + line)
        return 1 if problems else 0
    items = parse_pending(read_text(a.pending))
    if a.dry_run:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if a.list:
        print_list(items, parse_answers(read_text(a.answers)) if os.path.exists(a.answers) else {})
        return 0
    port = a.port
    try:
        srv = make_server(a.host, port, a.pending, a.answers, a.kit)
    except OSError as e:
        print('포트 %d 를 열지 못함: %s — 다른 --port 를 쓰거나 점유한 프로세스를 끝낸다' % (port, e), file=sys.stderr)
        return 1
    print('decide: %s (미답 %d · 답변됨 %d)' % (a.pending, len(unanswered(items)), len(answered_items(items))), flush=True)
    print('http://%s:%d/  (local: http://127.0.0.1:%d/)  Ctrl+C 로 종료' % (a.host, port, port), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
