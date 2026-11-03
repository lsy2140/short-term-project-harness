#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eda_bootstrap.py — 데이터 첫 파악 (표준 라이브러리만). 큰 파일을 Codex에 통째로 읽히지 말고 이 요약을 읽힌다.

사용: python3 scripts/eda_bootstrap.py data/a.csv [data/b.json ...] [--max-rows 200000] [--out eda_summary.md]
출력: 화면 + eda_summary.md (파일별 행/열, 열 타입 추정, 결측, 고유값, 수치 요약, 날짜 파싱, 중복 행, 키 후보, 상위 빈도값)
      끝에 '## 담당자 질문 후보' 절 — 단위 혼재 / 완전 중복 행 / 시각 형식 혼재 / 자정 넘김 / 식별자가 범주 열(fab·line 등)과
      조합해야 유일한지, 각 1줄(해당 없으면 '없음'). 담당자에게 보낼지는 docs/stakeholder_interview.md 의 제외 목록으로 거른다.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass
from collections import Counter

DATE_FORMATS = ['%Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%dT%H:%M:%S', '%m/%d/%Y', '%Y.%m.%d',
                '%Y/%m/%d %H:%M', '%Y/%m/%d %H:%M:%S', '%Y.%m.%d %H:%M']


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


def summarize(path, rows, cols, info=None):
    """파일 하나의 요약 줄 목록. info(dict)를 주면 질문 후보 계산용으로 shown·rows·cols·types·dup 을 채운다."""
    n = len(rows)
    try:
        shown = os.path.relpath(path)
    except ValueError:  # Windows: 다른 드라이브의 파일은 relpath 불가
        shown = path
    lines = ['## %s' % shown, '', '- 행 %d · 열 %d' % (n, len(cols)), '- 열: %s' % ', '.join(cols), '']
    if info is not None:
        info.update({'shown': shown, 'rows': rows, 'cols': cols, 'types': {}, 'dup': 0})
    if n == 0:
        lines.append('(행이 없습니다)')
        return lines
    dup = n - len({tuple(str(r.get(c, '')) for c in cols) for r in rows})
    lines.append('- 완전 중복 행: %d' % dup)
    if info is not None:
        info['dup'] = dup
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
        if info is not None:
            info['types'][c] = typ
    lines.append('')
    lines.append('- 키 후보(고유값 = 행 수): %s' % (', '.join(key_cands) if key_cands else '없음 → 복합 키 또는 중복 확인 필요'))
    lines.append('- 확인할 것: 결측 처리 규칙 / 경계값 포함 여부 / 시간대 / 단위 / 중복 행 처리 / 정렬·tie-break')
    lines.append('')
    return lines


UNIT_RE = re.compile(r'^[-+]?\d[\d,]*(?:\.\d+)?\s*([A-Za-z%°µ℃℉㎛가-힣][A-Za-z%°µ℃℉㎛/²³가-힣]*)$')
PLAIN_NUM_RE = re.compile(r'^[-+]?\d[\d,]*(?:\.\d+)?$')
UNIT_WORDS = {'mm', 'cm', 'm', 'km', 'um', 'µm', '㎛', 'nm', 'g', 'kg', 'mg', 't', 's', 'ms', 'sec', 'min', 'h', 'hr', '%',
              '°c', '℃', 'c', '°f', '℉', 'f', 'k', 'v', 'mv', 'a', 'ma', 'w', 'kw', 'pa', 'kpa', 'mpa', 'bar', 'psi',
              'hz', 'khz', 'mhz', 'gb', 'mb', 'kb', 'ea', 'pcs', 'l', 'ml', '개', '원', '초', '분', '시간', '일', '회', '장', '매', '건'}
TIME_ONLY_RE = re.compile(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$')
HAS_CLOCK_RE = re.compile(r'\d{1,2}:\d{2}')
DATEISH_RE = re.compile(r'^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{1,2}:\d{2})')
ID_HINT_RE = re.compile(r'(^|_)(id|no|code|name)$|_id$|^id_|eqp|equip|tool|machine|chamber|device|sensor|장비|번호|코드|이름', re.I)
CAT_HINT_RE = re.compile(r'(^|_)(fab|line|site|area|plant|bay|zone|region|shop|factory|building|location|loc)\d*($|_)|팹|라인|공장|지역', re.I)
PROBE_MAX = 5000      # 열마다 보는 값 수(단위·형식)
PAIR_ROWS = 20000     # 자정·식별자 검사에 쓰는 앞쪽 행 수
NULLS = ('null', 'none', 'nan', 'na')


def _probe_values(rows, c, limit=PROBE_MAX):
    out = []
    for r in rows:
        v = r.get(c)
        v = '' if v is None else str(v).strip()
        if v and v.lower() not in NULLS:
            out.append(v)
            if len(out) >= limit:
                break
    return out


def _dateish(vals):
    """값의 절반 이상이 날짜·시각 모양이면 True(파싱 실패 형식이 섞여 타입이 str 로 잡힌 열도 잡는다)."""
    return bool(vals) and sum(1 for v in vals if DATEISH_RE.match(v)) >= 0.5 * len(vals)


def _unit_mix(vals):
    """값 목록 → 단위 혼재면 '단위×수' 목록, 아니면 []. 단위 단어(UNIT_WORDS)만 단위로 본다(1A·2B 같은 코드는 제외)."""
    units, plain = Counter(), 0
    for v in vals:
        m = UNIT_RE.match(v)
        if m and m.group(1).lower() in UNIT_WORDS:
            units[m.group(1)] += 1
        elif PLAIN_NUM_RE.match(v):
            plain += 1
    if len(units) >= 2 or (units and plain):
        return ['%s×%d' % kv for kv in units.most_common(3)] + (['단위 없음×%d' % plain] if plain else [])
    return []


def _clock_cols(rows, cols, types):
    """시각이 든 열 → {열: 'time'(HH:MM) | 'datetime'} (열 순서 유지)."""
    out = {}
    for c in cols:
        vals = _probe_values(rows, c, 500)
        if not vals:
            continue
        if sum(1 for v in vals if TIME_ONLY_RE.match(v)) >= 0.95 * len(vals):
            out[c] = 'time'
        elif (types.get(c) == 'date' or _dateish(vals)) and sum(1 for v in vals if HAS_CLOCK_RE.search(v)) >= 0.5 * len(vals):
            out[c] = 'datetime'
    return out


def _clock_value(v, kind):
    """kind 'time' → 하루 안의 초, 'datetime' → datetime(시각이 적힌 값만). 못 읽으면 None."""
    v = '' if v is None else str(v).strip()
    if kind == 'time':
        m = TIME_ONLY_RE.match(v)
        if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
            return None
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0)
    return parse_date(v) if HAS_CLOCK_RE.search(v) else None


def _midnight(name, rows, cols, types):
    """하루 경계 단서: 한 열에 23시·0시 값이 함께 있음 / 이웃한 시각 열에서 뒤 열이 앞 열보다 이른 행 /
    이웃한 날짜·시각 열(datetime)에서 뒤 열의 날짜가 앞 열보다 뒤인 행(23:50 → 다음 날 00:20 처럼 자정을 넘긴 기록)."""
    found = []
    clocks = _clock_cols(rows, cols, types)
    names = list(clocks)[:3]
    parsed = {c: [_clock_value(r.get(c), clocks[c]) for r in rows[:PAIR_ROWS]] for c in names}
    for c in names:
        hours = [(x // 3600 if clocks[c] == 'time' else x.hour) for x in parsed[c] if x is not None]
        late, early = hours.count(23), hours.count(0)
        if late and early:
            found.append('%s %s 23시 %d·0시 %d' % (name, c, late, early))
    for a, b in zip(names, names[1:]):
        if clocks[a] != clocks[b]:
            continue
        back = crossed = 0
        for x, y in zip(parsed[a], parsed[b]):
            try:
                if x is None or y is None:
                    continue
                if y < x:
                    back += 1
                elif clocks[a] == 'datetime' and y.date() > x.date():
                    crossed += 1
            except TypeError:  # tz 있음/없음 혼재는 비교하지 않는다
                continue
        if back:
            found.append('%s %s→%s 뒤 열이 앞 열보다 이른 행 %d' % (name, a, b, back))
        if crossed:
            found.append('%s %s→%s 날짜가 바뀐 행 %d' % (name, a, b, crossed))
    return found


def _id_needs_category(name, rows, cols, types):
    """식별자 열(이름 단서) 값이 범주 열(fab·line 등) 2개 이상에 나타나면 (식별자, 범주) 조합 후보."""
    found = []
    probe = rows[:PAIR_ROWS]
    id_cols = [c for c in cols if ID_HINT_RE.search(c) and types.get(c) != 'date']
    cat_cols = [c for c in cols if CAT_HINT_RE.search(c)]
    if not cat_cols:  # 이름 단서가 없으면 고유값이 적은 문자열 열
        cat_cols = [c for c in cols if types.get(c) == 'str'
                    and 2 <= len(set(_probe_values(probe, c, len(probe)))) <= min(20, len(probe) // 2)]
    for ic in id_cols:
        for cc in cat_cols:
            if ic == cc:
                continue
            seen = {}
            for r in probe:
                iv, cv = str(r.get(ic) or '').strip(), str(r.get(cc) or '').strip()
                if iv and cv:
                    seen.setdefault(iv, set()).add(cv)
            multi = sorted((k, s) for k, s in seen.items() if len(s) >= 2)
            if multi:
                k, s = multi[0]
                found.append('%s %s×%s %d개(예 %s: %s)' % (name, ic, cc, len(multi), k[:16], '·'.join(sorted(s)[:3])))
    return found


def question_candidates(infos):
    """파일 요약들 → '## 담당자 질문 후보' 절(항목마다 1줄, 해당 없으면 '없음').
    입력: infos — summarize 가 채운 [{'shown', 'rows', 'cols', 'types', 'dup'}] / 출력: 줄 목록(docs/stakeholder_interview.md C·D 행 후보)"""
    units, dups, shapes, midnight, idcat = [], [], [], [], []
    for f in infos:
        rows, cols, types, name = f.get('rows') or [], f.get('cols') or [], f.get('types') or {}, f.get('shown', '?')
        if not rows:
            continue
        if f.get('dup'):
            dups.append('%s %d행' % (name, f['dup']))
        clocks = _clock_cols(rows, cols, types)
        for c in cols:
            vals = _probe_values(rows, c)
            if c in clocks or types.get(c) == 'date' or _dateish(vals):
                kinds = Counter(re.sub(r'\d', '9', v) for v in vals)
                if len(kinds) >= 2:
                    shapes.append('%s %s %d종(%s)' % (name, c, len(kinds), ' · '.join('%s×%d' % kv for kv in kinds.most_common(2))))
                continue
            mix = _unit_mix(vals)
            if mix:
                units.append('%s %s(%s)' % (name, c, '·'.join(mix)))
        midnight += _midnight(name, rows, cols, types)
        idcat += _id_needs_category(name, rows, cols, types)

    def one(label, items, ask):
        if not items:
            return '- %s: 없음' % label
        more = (' 외 %d' % (len(items) - 3)) if len(items) > 3 else ''
        return '- %s: %s%s → %s' % (label, ' / '.join(items[:3]), more, ask)
    return ['## 담당자 질문 후보', '',
            '(데이터 단서만 적는다. 표기 차이는 데이터로 정하고, 업무 규칙이 걸린 것만 C·D 행 질문으로 바꾼다)',
            one('단위 혼재', units, '단위가 다른 값은 환산하나요, 따로 보나요?'),
            one('완전 중복 행', dups, '같은 기록이 두 번 있으면 한 번으로 세나요?'),
            one('시각 형식 혼재', shapes, '표기는 데이터로 맞추고, 시간대가 섞였을 때만 묻는다'),
            one('자정 넘김', midnight, '자정을 넘긴 기록은 어느 날짜로 세나요?'),
            one('식별자가 범주 열과 조합해야 유일한지', idcat, '같은 이름이 다른 팹·라인에도 있나요?'),
            '']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--max-rows', type=int, default=200000)
    ap.add_argument('--out', default='eda_summary.md')
    args = ap.parse_args()
    out = ['# EDA 요약 (%s)' % dt.datetime.now().strftime('%Y-%m-%d %H:%M'), '']
    infos = []
    for p in args.paths:
        rows, cols = load_rows(p, args.max_rows)
        info = {}
        out += summarize(p, rows, cols, info)
        infos.append(info)
    out += question_candidates(infos)
    text = '\n'.join(out)
    print(text)
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)   # --out .tmp/eda.md 처럼 없는 폴더도 만든다
    with open(args.out, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print('\n→ 저장: %s (Codex에는 이 파일만 읽힐 것)' % args.out)


if __name__ == '__main__':
    main()
