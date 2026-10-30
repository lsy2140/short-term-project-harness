#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""timer.py — 경과·남은 시간과 현재 구간 표시.
사용: python3 scripts/timer.py --start 10:00 [--total 180] [--loop 300] [--once]
  --loop N  N초마다 반복 출력 (0이면 1회)
  --once    1회 출력 후 종료 (--loop 무시)
매 출력 끝에 scripts/next.py 의 보고 꼬리 3줄(지금 / 다음 추천 / 대기 중 할 일)을 같이 찍는다.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

PHASES = [
    (0, 10, '① 읽기 — README·파일·형식 (코드 금지)'),
    (10, 30, '② 계약·인터뷰 — TASK.md, 담당자 질문, 합의문'),
    (30, 63, '④ 첫 완주 — 가장 작은 end-to-end + 첫 기록(out/debug/01_첫완주)'),
    (63, 110, '⑤ 규칙·검증 — 규칙 1개 = 테스트 1개, 엣지케이스, 디버그 폴더 기록 (80분 이후 새 접근 금지)'),
    (110, 120, '1차 동결 — 지금 제출해도 되는 상태: preflight 0 · README 명령 실행 · preflight --freeze 복구본'),
    (120, 130, '⑤ 규칙·검증 계속 — 설명할 수 있는 것만 추가'),
    (130, 144, '점검 — preflight FAIL 0, 심사자 시뮬레이션, PLAN 초안'),
    (144, 165, '⑥ 동결 — 문서 정리(증거 좌표), HANDOFF.md, 한계 기록, /review'),
    (165, 170, '최종 — 증거 좌표 재점검, preflight 재실행, 저장 상태 확인'),
    (170, 999, '제출 — 제출하고 문제풀기 → 확정'),
]


def phase_of(elapsed):
    for a, b, name in PHASES:
        if a <= elapsed < b:
            return name, b
    return PHASES[-1][2], 999


def next_lines(start):
    """scripts/next.py 의 꼬리 3줄 (같은 시계·같은 구간표). next.py 가 실패해도 타이머는 멈추지 않는다."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import next as next_report  # noqa: E402  (scripts/next.py)
        return next_report.build(os.getcwd(), start=start)['lines']
    except Exception as e:  # noqa
        return ['next.py 실행 실패: %s → python3 scripts/next.py --start %s 로 직접 확인' % (e, start)]


def main():
    ap = argparse.ArgumentParser(description='경과·남은 시간·현재 구간 + next.py 꼬리 3줄')
    ap.add_argument('--start', required=True, help='HH:MM (과제 시작 시각)')
    ap.add_argument('--total', type=int, default=180)
    ap.add_argument('--loop', type=int, default=0, help='초 단위 반복 출력(0이면 1회)')
    ap.add_argument('--once', action='store_true', help='1회 출력 후 종료(--loop 무시)')
    args = ap.parse_args()
    try:
        h, m = map(int, args.start.split(':'))
        assert 0 <= h < 24 and 0 <= m < 60
    except (ValueError, AssertionError):
        print('--start 형식 오류: %r → HH:MM (예 10:05)' % args.start, file=sys.stderr)
        sys.exit(2)
    start = dt.datetime.now().replace(hour=h, minute=m, second=0, microsecond=0)
    while True:
        now = dt.datetime.now()
        elapsed = (now - start).total_seconds() / 60
        remain = args.total - elapsed
        name, until = phase_of(elapsed)
        print('[%s] 경과 %3d분 · 남음 %3d분 · 현재: %s · 다음 구간 %s' % (
            now.strftime('%H:%M'), int(elapsed), int(remain), name, ('%d분' % until) if until != 999 else '-'))
        if remain <= 15:
            print('   !! 제출 준비: 필수 파일·저장 상태·preflight 확인')
        print('   구간 끝 3질문: preflight 통과하나 / 지금 제출하면 몇 점인가 / 직전 30분 코드를 설명할 수 있나')
        for line in next_lines(args.start):
            print('   ' + line)
        if args.once or not args.loop:
            break
        time.sleep(args.loop)


if __name__ == '__main__':
    main()
