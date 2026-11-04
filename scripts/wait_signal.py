#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wait_signal.py — 내 몫의 연결 신호(또는 결정 답)가 올 때까지 기다린다 (표준 라이브러리, Python 3.9). 판단·추천은 없다.

사용(에이전트가 자기 창에서 돌린다):
  python3 scripts/wait_signal.py --me B --once               # task 끝마다: 지금 받을 것이 있나 한 번만 확인
  python3 scripts/wait_signal.py --me B                      # 할 task 가 없을 때: 30초 간격으로 최대 20분 기다린다
  python3 scripts/wait_signal.py --me A --decision D03 D04   # 연결 신호 또는 D03/D04 의 답이 오면 깨운다
  --interval 30 (초) · --minutes 20 · --root DIR (TASK.md·PLAN.md·work/·decisions/ 가 있는 폴더)

읽는 것(status.py 와 같은 규칙, 읽기만):
  work/agents/*.md ⑦ 의 `연결 N`(보낸 담당) · 각 파일의 `연결 N 반영`(받은 담당) · PLAN.md 4-2 표의 받는 담당
  work/agents/*.md ⑦ 의 `@A C1: 내용`(나에게 온 번호 붙은 요청) · 어느 파일이든 `C1 반영`·`C1 해결` 이 있으면 닫힌 것
  decisions/answers.md 의 `Dnn:` 줄 또는 pending.md 의 고른 후보 `[x]` (--decision 을 줬을 때만)
  TASK.md 머리 Status: FROZEN 이면 기다리지 않는다
출력: 신호마다 `연결 N · 보낸 A · PLAN 4-2: <행 요약>` / 요청마다 `요청 C1 · 보낸 C · @A: <내용>` / 답마다 `D03 답: <answers.md 줄>` / 없으면 `신호 없음 (N분)`
exit 0 신호·답 있음 / 3 시간 안에 없음 / 4 Status FROZEN / 2 인자 오류
명령 시간 제한에 걸리면 같은 명령을 다시 돌리면 된다(상태는 파일에만 있다).
"""
import argparse
import datetime as dt
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import status  # noqa: E402

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

ANSWER_LINE_PAT = re.compile(r'(?m)^(D\d+(?:\s*,\s*D\d+)*)\s*[:：]\s*(.+)$')


def my_signals(root, me):
    """내가(me = A/B/C) 아직 받지 않은 연결 신호 목록 — status.read_signals 의 pending 중 to 에 me 또는 '?' 가 든 것."""
    found = []
    for p in status.read_signals(root)['pending']:
        if me in p['to'] or '?' in p['to']:
            found.append(p)
    return found


def my_requests(root, me):
    """나에게 온 번호 붙은 요청(`@A C1: …`) 중 아직 닫히지 않은 것."""
    return [r for r in status.read_signals(root)['requests'] if r['to'] == me]


def answered(root, ids):
    """[(Dnn, 답 줄)] — answers.md 의 `Dnn: …` 줄이 있거나 pending.md 에서 고른 후보가 있는 것만."""
    out = []
    if not ids:
        return out
    lines = {}
    path = os.path.join(root, 'decisions', 'answers.md')
    if os.path.exists(path):
        with open(path, encoding='utf-8', errors='replace') as fh:
            for m in ANSWER_LINE_PAT.finditer(fh.read()):
                for d in re.findall(r'D\d+', m.group(1)):
                    lines[d] = m.group(0).strip()
    open_ids = set(status.read_pending(root)['open'])
    for d in ids:
        if d in lines:
            out.append((d, lines[d]))
        elif d not in open_ids and os.path.exists(os.path.join(root, 'decisions', 'pending.md')):
            out.append((d, 'pending.md 에 고른 후보 [x] 있음'))
    return out


def check(root, me, decisions):
    """한 번 확인 → 출력 줄 목록(없으면 빈 목록)."""
    out = []
    for p in my_signals(root, me):
        out.append('연결 %s · 보낸 %s · PLAN 4-2: %s' % (p['n'], '·'.join(p['from']), p['row'] or '행 없음'))
    for r in my_requests(root, me):
        out.append('요청 %s · 보낸 %s · @%s: %s' % (r['id'], r['from'], r['to'], r['text']))
    for d, line in answered(root, decisions):
        out.append('%s 답: %s' % (d, line))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='내 몫의 연결 신호·결정 답을 기다린다 (파일을 읽기만 하고 아무 판단도 하지 않는다)')
    ap.add_argument('--me', required=True, help='내 담당 글자 A / B / C (work/agents/<글자>_*.md)')
    ap.add_argument('--once', action='store_true', help='지금 한 번만 확인하고 끝낸다')
    ap.add_argument('--decision', nargs='*', default=[], metavar='Dnn', help='이 결정의 답이 와도 깨운다')
    ap.add_argument('--interval', type=float, default=30.0, help='확인 간격(초, 기본 30)')
    ap.add_argument('--minutes', type=float, default=20.0, help='최대 기다리는 분(기본 20)')
    ap.add_argument('--root', default=os.getcwd(), help='작업 폴더(기본 현재 폴더)')
    args = ap.parse_args(argv)
    me = (args.me or '').strip().upper()[:1]
    if me not in ('A', 'B', 'C'):
        sys.stderr.write('wait_signal.py: --me 는 A / B / C 중 하나 (받음: %r)\n' % args.me)
        return 2
    if args.interval <= 0 or args.minutes < 0:
        sys.stderr.write('wait_signal.py: --interval 은 0 보다 크고 --minutes 는 0 이상이어야 합니다\n')
        return 2
    decisions = [d.strip().upper() for d in args.decision if d.strip()]
    if not args.once:
        print('기다림 시작 %s · 대상 %s · %g초 간격 · 최대 %g분%s' % (
            dt.datetime.now().strftime('%H:%M'), me, args.interval, args.minutes,
            (' · 결정 ' + '·'.join(decisions)) if decisions else ''))
        sys.stdout.flush()
    end = time.monotonic() + args.minutes * 60.0
    while True:
        if status.read_task_head(args.root)['status'] == 'FROZEN':
            print('Status FROZEN — 기다리지 않는다')
            return 4
        lines = check(args.root, me, decisions)
        if lines:
            print('\n'.join(lines))
            return 0
        if args.once or time.monotonic() >= end:
            print('신호 없음 (%g분)' % (0 if args.once else args.minutes))
            return 3
        time.sleep(min(args.interval, max(0.0, end - time.monotonic())) or 0.01)


if __name__ == '__main__':
    sys.exit(main())
