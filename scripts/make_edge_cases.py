#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_edge_cases.py — 아무 CSV 에서 "내가 상상 못 한 입력" 변형을 만든다 (표준 라이브러리, 결정적).

  python3 scripts/make_edge_cases.py data/input.csv --out data/edge/
생성: empty.csv(헤더만) / dirty.csv(결측·NA·공백·대소문자·쉼표숫자·Z시각 섞음) / dup.csv(중복 행 5%)
      / shuffled.csv(행 순서 섞음) / extra_col.csv(모르는 열 추가) / header_only_diff.csv(열 순서 변경)
용도: 내 프로그램을 각 파일로 돌려 "안 터지는지 / 조용히 틀리지 않는지" 확인한다. 규칙 테스트(verify)와 짝으로 쓴다.
"""
import argparse
import csv
import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass
import random
import re

ISO_RE = re.compile(r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$')
NUM_RE = re.compile(r'^-?\d+(\.\d+)?$')


def load(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    return rows[0], rows[1:]


def save(path, header, rows):
    with open(path, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def dirty(header, rows, rnd, rate=0.03):
    out = []
    for r in rows:
        r = list(r)
        for i, v in enumerate(r):
            x = rnd.random()
            if x < rate * 0.3:
                r[i] = ''
            elif x < rate * 0.5:
                r[i] = rnd.choice(['NA', 'N/A', 'null', '-', 'NaN'])
            elif x < rate * 0.65:
                r[i] = ' %s ' % v
            elif x < rate * 0.8 and v and not NUM_RE.match(v):
                r[i] = v.swapcase() if v.isascii() else v
            elif x < rate * 0.9 and NUM_RE.match(v) and '.' not in v and len(v) > 3:
                r[i] = '{:,}'.format(int(v))
            elif x < rate and ISO_RE.match(v):
                r[i] = v.replace(' ', 'T') + 'Z'
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--out', default='data/edge')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--rate', type=float, default=0.03)
    a = ap.parse_args()
    rnd = random.Random(a.seed)
    header, rows = load(a.csv)
    os.makedirs(a.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(a.csv))[0]
    save(os.path.join(a.out, base + '.empty.csv'), header, [])
    save(os.path.join(a.out, base + '.dirty.csv'), header, dirty(header, rows, rnd, a.rate))
    dup = list(rows)
    for r in rnd.sample(rows, max(1, len(rows) // 20)) if rows else []:
        dup.insert(rnd.randrange(len(dup) + 1), list(r))
    save(os.path.join(a.out, base + '.dup.csv'), header, dup)
    sh = list(rows)
    rnd.shuffle(sh)
    save(os.path.join(a.out, base + '.shuffled.csv'), header, sh)
    save(os.path.join(a.out, base + '.extra_col.csv'), header + ['unexpected'], [r + ['x'] for r in rows])
    perm = list(range(len(header)))
    rnd.shuffle(perm)
    save(os.path.join(a.out, base + '.colorder.csv'), [header[i] for i in perm], [[r[i] for i in perm] for r in rows])
    print('생성: %s/%s.{empty,dirty,dup,shuffled,extra_col,colorder}.csv  (원본 %d행)' % (a.out, base, len(rows)))
    print('다음: 각 파일로 프로그램을 실행해 "터지지 않고, 결측·중복을 보고하고, 열 순서에 의존하지 않는지" 확인')


if __name__ == '__main__':
    main()
