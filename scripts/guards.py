#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""guards.py — 생성 문구·데이터 처리의 공통 방어막 (표준 라이브러리만, Python 3.9).

이전 대회 실제 과제(규칙 불일치 46건·금지어·근거 없는 문구)에서 반복된 함정을 함수 6개로 고정한다.
  normalize_for_check(text)            NFC + 소문자 + [0-9a-z가-힣] 만 남김 (공백·기호·zero-width 제거)
  normalize_hangul_only(text)          한글만 남김 (영문·숫자 사이에 끼워 넣은 우회 대비)
  check_banned(text, words) -> hits    두 정규화 모두로 부분 문자열 검사. 걸린 금지어 목록(원문 표기, 중복 제거, 입력 순서)
  check_grounded(text, vocab, evidence) -> missing
                                       text 에 등장한 vocab 단어 중 evidence(근거 데이터 문자열)에 없는 것 = 근거 없는 주장
  exclude_with_reason(rows, rules) -> (kept, excluded_with_reason, counts)
                                       rules=[(reason, predicate)] 순서대로 검사, 첫 위반 1개만 사유로. 합계 보존 len(rows)==len(kept)+len(excluded)
  with_timeout_fallback(fn, fallback, sec) -> (value, status)
                                       status: 'ok' | 'timeout' | 'error'. fn 이 늦거나 예외면 fallback 을 돌려주고 숨기지 않는다
  mask_pii(text, name_pat=None, emp_id_pat=None, phone_pat=None) -> 마스킹된 문자열
                                       전화·사번·(패턴을 주면) 이름을 [전화] [사번] [이름] 으로 치환. 로그·대화에 PII 를 남기지 않기 위한 마지막 관문

사용 예
    from scripts.guards import check_banned, exclude_with_reason
    hits = check_banned(copy, ['무결점', '100% 보장'])            # ['무결점'] 이면 발행 차단
    kept, excluded, counts = exclude_with_reason(products, [
        ('out_of_stock', lambda r: r.get('stock', 0) <= 0),
        ('missing_price', lambda r: r.get('price') is None),
    ])
테스트: python3 -m unittest tests.test_guards -v
"""
import re
import threading
import time
import unicodedata

_ZERO_WIDTH = re.compile(u'[​‌‍⁠﻿­]')
_KEEP_ALNUM_HANGUL = re.compile(u'[^0-9a-z가-힣]')
_KEEP_HANGUL = re.compile(u'[^가-힣]')

DEFAULT_PHONE_PAT = r'(?<!\d)0\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)'          # 010-1234-5678, 02 123 4567, 01012345678
DEFAULT_EMP_ID_PAT = r'(?<![A-Za-z0-9])(?:[A-Z]{1,2}-?\d{6,8}|\d{8})(?![A-Za-z0-9])'  # E123456, AB-20231234, 20231234


def normalize_for_check(text):
    """NFC 정규화 → 소문자 → 숫자·영문 소문자·한글 음절만 남긴다. None 은 빈 문자열."""
    if text is None:
        return ''
    s = unicodedata.normalize('NFC', str(text))
    s = _ZERO_WIDTH.sub('', s)
    s = s.lower()
    return _KEEP_ALNUM_HANGUL.sub('', s)


def normalize_hangul_only(text):
    """한글 음절만 남긴다(영문·숫자·기호 사이에 끼워 넣은 우회 대비)."""
    if text is None:
        return ''
    s = unicodedata.normalize('NFC', str(text))
    return _KEEP_HANGUL.sub('', s)


def check_banned(text, words):
    """금지어 검사. 두 정규화(알파벳+한글 / 한글만) 중 하나라도 부분 문자열로 걸리면 hit.
    부분 문자열 기준이라 보수적이다(과차단 가능). 반환은 words 의 원문 표기, 입력 순서, 중복 제거."""
    if not words:
        return []
    n1 = normalize_for_check(text)
    n2 = normalize_hangul_only(text)
    hits, seen = [], set()
    for w in words:
        if w is None:
            continue
        key = str(w)
        if key in seen:
            continue
        w1 = normalize_for_check(w)
        w2 = normalize_hangul_only(w)
        hit = False
        if w1 and w1 in n1:
            hit = True
        elif w2 and w2 == w1 and len(w2) >= 2 and w2 in n2:
            # 한글만으로 된 금지어에만 한글-only 경로를 쓴다('100% 보장' 이 '보장' 으로 줄어 과차단되는 것을 막는다)
            hit = True
        if hit:
            hits.append(key)
            seen.add(key)
    return hits


def check_grounded(text, vocab, evidence):
    """text 에 등장한 vocab 단어 가운데 evidence 에 없는 것을 돌려준다(= 근거 없는 주장).
    evidence 는 문자열 또는 문자열 목록(상품 필드·데이터 행 등). 비교는 normalize_for_check 기준."""
    nt = normalize_for_check(text)
    if isinstance(evidence, (list, tuple, set)):
        ne = ' '.join(normalize_for_check(e) for e in evidence)
    else:
        ne = normalize_for_check(evidence)
    missing, seen = [], set()
    for v in vocab or []:
        key = str(v)
        nv = normalize_for_check(v)
        if not nv or key in seen:
            continue
        if nv in nt and nv not in ne:
            missing.append(key)
            seen.add(key)
    return missing


def exclude_with_reason(rows, rules):
    """rows 를 rules=[(reason, predicate)] 순서로 검사해 첫 위반 사유 1개로 제외한다.
    반환: (kept, excluded_with_reason[(row, reason)], counts{reason: n}) — counts 는 모든 사유를 0 으로 초기화해 둔다.
    불변량: len(rows) == len(kept) + len(excluded). 입력 rows 와 row 객체는 수정하지 않는다."""
    kept, excluded = [], []
    counts = {reason: 0 for reason, _ in rules}
    for row in rows:
        reason_hit = None
        for reason, pred in rules:
            try:
                bad = bool(pred(row))
            except Exception:  # 조건식 자체가 터지는 행은 그 사유로 제외한다(조용히 통과시키지 않는다)
                bad = True
            if bad:
                reason_hit = reason
                break
        if reason_hit is None:
            kept.append(row)
        else:
            excluded.append((row, reason_hit))
            counts[reason_hit] += 1
    assert len(rows) == len(kept) + len(excluded), '합계 보존 실패'
    return kept, excluded, counts


def with_timeout_fallback(fn, fallback, sec):
    """fn() 을 별도 스레드로 실행해 sec 초 안에 끝나면 (값, 'ok'), 늦으면 (fallback, 'timeout'), 예외면 (fallback, 'error').
    timeout 뒤에도 스레드는 백그라운드에서 끝까지 돌 수 있다(데몬) — 부작용 있는 fn 은 멱등하게 만든다.
    fallback 이 callable 이면 호출해서 값을 만든다."""
    box = {}

    def run():
        try:
            box['value'] = fn()
        except Exception as e:  # noqa
            box['error'] = e

    t = threading.Thread(target=run)
    t.daemon = True
    t0 = time.time()
    t.start()
    t.join(max(0.0, float(sec)))
    fb = fallback() if callable(fallback) else fallback
    if t.is_alive():
        return fb, 'timeout'
    if 'error' in box:
        return fb, 'error'
    _ = time.time() - t0
    return box.get('value'), 'ok'


def mask_pii(text, name_pat=None, emp_id_pat=DEFAULT_EMP_ID_PAT, phone_pat=DEFAULT_PHONE_PAT):
    """전화번호 → [전화], 사번 → [사번], 이름(패턴을 준 경우만) → [이름].
    이름은 범용 패턴이 없어 기본 None 이다. 예: name_pat=r'(김|이|박)[가-힣]{1,2}' 또는 '|'.join(map(re.escape, names)).
    순서: 전화 → 사번 → 이름 (사번·전화 안의 숫자가 이름 패턴에 먹히지 않게)."""
    if text is None:
        return ''
    s = str(text)
    if phone_pat:
        s = re.sub(phone_pat, '[전화]', s)
    if emp_id_pat:
        s = re.sub(emp_id_pat, '[사번]', s)
    if name_pat:
        s = re.sub(name_pat, '[이름]', s)
    return s


if __name__ == '__main__':
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:  # noqa
        pass
    sample = '이 제품은 무 결 점 입니다. 담당 김철수 010-1234-5678, 사번 E123456'
    print('banned :', check_banned(sample, ['무결점', '100% 보장']))
    print('masked :', mask_pii(sample, name_pat=r'김[가-힣]{2}'))
    print('ground :', check_grounded('비타민C 함유 보습 크림', ['비타민C', '보습', '미백'], ['name: 보습 크림', 'tags: 수분']))
