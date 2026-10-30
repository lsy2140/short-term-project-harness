#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eda_bootstrap.py — 데이터 첫 파악 (표준 라이브러리만). 큰 파일을 Codex에 통째로 읽히지 말고 이 요약을 읽힌다.

사용: python3 scripts/eda_bootstrap.py data/a.csv [data/b.json ...] [--max-rows 200000] [--out eda_summary.md]
출력: 화면 + eda_summary.md (파일별 행/열, 열 타입 추정, 결측, 고유값, 수치 요약, 날짜 파싱, 중복 행, 키 후보, 상위 빈도값)
"""
import argparse
import csv
import datetime as dt
import json
import os
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass
from collections import Counter

DATE_FORMATS = ['%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y', '%Y.%m.%d']


def parse_num(s):
    try:
        return float(s.replace(',', ''))
    except Exception:
        return None


def parse_date(s):
    for f in DATE_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except Exception:
            pass
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def load_rows(path, max_rows):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.csv':
        with open(path, 'r', encoding='utf-8-sig', errors='replace', newline='') as fh:
            sample = fh.read(4096)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t|')
            except Exception:
                dialect = csv.excel
            reader = csv.DictReader(fh, dialect=dialect)
            rows = []
            for i, r in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(r)
            return rows, reader.fieldnames or []
    if ext in ('.json', '.jsonl'):
        with open(path, 'r', encoding='utf-8-sig', errors='replace') as fh:
            if ext == '.jsonl':
                data = [json.loads(l) for l in fh if l.strip()]
            else:
                data = json.load(fh)
        if isinstance(data, dict):
            # 가장 긴 리스트 값을 레코드로 간주
            lists = [v for v in data.values() if isinstance(v, list)]
            data = max(lists, key=len) if lists else [data]
        rows = [r if isinstance(r, dict) else {'value': r} for r in data[:max_rows]]
        cols = []
        for r in rows:
            for k in r:
                if k not in cols:
                    cols.append(k)
        return rows, cols
    raise SystemExit('지원하지 않는 형식: %s' % path)


def summarize(path, rows, cols):
    n = len(rows)
    try:
        shown = os.path.relpath(path)
    except ValueError:  # Windows: 다른 드라이브의 파일은 relpath 불가
        shown = path
    lines = ['## %s' % shown, '', '- 행 %d · 열 %d' % (n, len(cols)), '- 열: %s' % ', '.join(cols), '']
    if n == 0:
        lines.append('(행이 없습니다)')
        return lines
    dup = n - len({tuple(str(r.get(c, '')) for c in cols) for r in rows})
    lines.append('- 완전 중복 행: %d' % dup)
    key_cands = []
    lines.append('')
    lines.append('| 열 | 타입 | 결측 | 고유 | 요약 | 샘플 |')
    lines.append('|---|---|---|---|---|---|')
    for c in cols:
        vals = [str(r.get(c, '')).strip() if r.get(c) is not None else '' for r in rows]
        nonempty = [v for v in vals if v != '' and v.lower() not in ('null', 'none', 'nan', 'na')]
        missing = n - len(nonempty)
        uniq = len(set(nonempty))
        if uniq == n and n > 1:
            key_cands.append(c)
        nums = [parse_num(v) for v in nonempty]
        nums = [x for x in nums if x is not None]
        probe = nonempty[:500]
        dates = [x for x in (parse_date(v) for v in probe) if x is not None]
        if nonempty and len(nums) >= 0.95 * len(nonempty):
            typ = 'int' if all(float(x).is_integer() for x in nums) else 'float'
            summ = 'min %s / med %s / max %s / mean %.3g' % (min(nums), statistics.median(nums), max(nums), statistics.mean(nums))
        elif nonempty and len(dates) >= 0.95 * len(probe):
            typ = 'date'
            all_dates = [x for x in (parse_date(v) for v in nonempty) if x is not None]  # 범위는 전체 값으로
            naive = sum(1 for x in all_dates if x.tzinfo is None)
            aware = len(all_dates) - naive

            def _key(x):  # naive/aware 혼재 시 min/max 가 TypeError → 비교 키만 UTC 로 통일(값은 바꾸지 않음)
                return x.replace(tzinfo=dt.timezone.utc) if x.tzinfo is None else x
            summ = '%s ~ %s (파싱 실패 %d)' % (min(all_dates, key=_key).isoformat(), max(all_dates, key=_key).isoformat(), len(nonempty) - len(all_dates))
            if naive and aware:
                summ += ' · 시간대 혼재: tz 없음 %d / 있음 %d' % (naive, aware)
        else:
            typ = 'str'
            top = Counter(nonempty).most_common(3)
            summ = '상위: ' + ', '.join('%s(%d)' % (k[:12], v) for k, v in top)
        sample = ' / '.join(nonempty[:3])[:40]
        lines.append('| %s | %s | %d | %d | %s | %s |' % (c, typ, missing, uniq, summ, sample))
    lines.append('')
    lines.append('- 키 후보(고유값 = 행 수): %s' % (', '.join(key_cands) if key_cands else '없음 → 복합 키 또는 중복 확인 필요'))
    lines.append('- 확인할 것: 결측 처리 규칙 / 경계값 포함 여부 / 시간대 / 단위 / 중복 행 처리 / 정렬·tie-break')
    lines.append('')
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--max-rows', type=int, default=200000)
    ap.add_argument('--out', default='eda_summary.md')
    args = ap.parse_args()
    out = ['# EDA 요약 (%s)' % dt.datetime.now().strftime('%Y-%m-%d %H:%M'), '']
    for p in args.paths:
        rows, cols = load_rows(p, args.max_rows)
        out += summarize(p, rows, cols)
    text = '\n'.join(out)
    print(text)
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('\n→ 저장: %s (Codex에는 이 파일만 읽힐 것)' % args.out)


if __name__ == '__main__':
    main()
