#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""refs/pick.py — 화면 유형·키워드로 참고 DESIGN.md 후보를 고른다 (표준 라이브러리, Python 3.9).

  python3 design-kit/refs/pick.py 대시보드            # 유형 단어 → 그 유형 태그가 있는 md 상위 5개
  python3 design-kit/refs/pick.py 모바일 금융 차분     # 유형 + 자유 키워드(서비스·분위기·색·서체 칸에서 찾는다)
  python3 design-kit/refs/pick.py                    # 유형 5개와 사용법

입력: 같은 폴더의 INDEX.md 표(첫 칸이 `ko/…` 또는 `awesome/…` 인 행, 칸 8개).
점수: 유형 단어 = 그 태그가 첫 태그면 3, 뒤 태그면 2 / 다른 키워드 = 맞는 칸마다 1.
정렬: 점수 높은 순 → 같은 점수면 한국 서비스(ko/) 먼저 → INDEX 순서.
출력: `경로 · 서비스 · 유형 · 분위기 · 크기` 한 줄씩(경로는 지금 폴더 기준). 맞는 후보가 없으면 exit 1, INDEX.md 를 못 읽으면 exit 2.
"""
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(HERE, 'INDEX.md')
TOP = 5
# (태그, REFERENCE.md 유형 번호, 같은 뜻으로 받는 단어)
TYPES = [
    ('모니터링', 1, ('모니터링', '대시보드', '현황', '현황판', '관제', '제조', '설비', '공정', 'dashboard', 'monitoring')),
    ('조회', 2, ('조회', '검색', '목록', '상세', '필터', '탐색', '도구', 'search', 'tool')),
    ('콘솔', 3, ('콘솔', '운영', '운영자', '관리', '관리자', '설정', '등록', '승인', 'admin', 'console')),
    ('모바일', 4, ('모바일', '앱', '현장', '한손', 'mobile', 'app')),
    ('홈', 5, ('홈', '포털', '랜딩', '소개', '첫화면', 'home', 'portal', 'landing')),
]
ROW_PATH = re.compile(r'^(ko|awesome)/[\w.\-]+\.md$')
TEXT_COLS = ('service', 'mood', 'color', 'font')


def load_rows(path=INDEX):
    """INDEX.md 표에서 참고 md 행을 읽는다.
    입력: INDEX.md 경로.
    출력: [{'path','service','tags','mood','color','font','kb','license','order'}] (INDEX 순서).
    규칙: 첫 칸이 ko/ 또는 awesome/ 로 시작하는 8칸 행만, 태그는 쉼표로 나눈다.
    실패: 파일이 없으면 OSError."""
    rows = []
    with open(path, 'r', encoding='utf-8') as fh:
        for line in fh:
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 8 or not ROW_PATH.match(cells[0].strip('`')):
                continue
            rows.append({'path': cells[0].strip('`'), 'service': cells[1],
                         'tags': [t.strip() for t in cells[2].split(',') if t.strip()],
                         'mood': cells[3], 'color': cells[4], 'font': cells[5],
                         'kb': cells[6], 'license': cells[7], 'order': len(rows)})
    return rows


def type_of(word):
    """유형 단어면 태그 이름, 아니면 None."""
    w = word.strip().lower()
    for tag, _, words in TYPES:
        if w in words:
            return tag
    return None


def score(row, words):
    """한 행의 점수. 규칙: 유형 단어는 첫 태그 3·뒤 태그 2, 다른 단어는 맞는 칸마다 1."""
    total = 0
    for word in words:
        tag = type_of(word)
        if tag:
            total += 3 if row['tags'][:1] == [tag] else 2 if tag in row['tags'] else 0
        else:
            w = word.strip().lower()
            total += sum(1 for col in TEXT_COLS if w and w in row[col].lower())
    return total


def pick(rows, words, top=TOP):
    """점수 > 0 인 행을 점수 높은 순(같으면 ko/ 먼저 → INDEX 순서)으로 top 개."""
    scored = [(score(r, words), r) for r in rows]
    scored = [x for x in scored if x[0] > 0]
    scored.sort(key=lambda x: (-x[0], 0 if x[1]['path'].startswith('ko/') else 1, x[1]['order']))
    return [r for _, r in scored[:top]]


def shown(rel):
    """refs 안 경로를 지금 폴더 기준 경로로(다른 드라이브면 절대 경로)."""
    full = os.path.join(HERE, *rel.split('/'))
    try:
        out = os.path.relpath(full)
    except ValueError:
        out = full
    return out.replace(os.sep, '/')


def usage():
    print('사용법: python3 design-kit/refs/pick.py <유형|키워드 …>  → 후보 상위 %d개(경로 · 서비스 · 유형 · 분위기 · 크기)' % TOP)
    print('유형 5개 (REFERENCE.md 번호 · 같은 뜻으로 받는 단어):')
    for tag, num, words in TYPES:
        print('  %d %s — %s' % (num, tag, '·'.join(w for w in words[1:] if not w.isascii())))
    print('예: pick.py 대시보드 / pick.py 모바일 금융 / pick.py 조회 차분')
    print('다음: 후보 2~3개만 열어 후보마다 시안 1개(INDEX.md 쓰는 법 2)')


def main(argv=None):
    words = [a for a in (sys.argv[1:] if argv is None else argv) if a.strip()]
    if not words:
        usage()
        return 0
    try:
        rows = load_rows()
    except OSError as e:
        print('INDEX.md 를 읽지 못함: %s' % e, file=sys.stderr)
        return 2
    found = pick(rows, words)
    if not found:
        print('맞는 후보 없음: %s — 유형 단어(모니터링·조회·콘솔·모바일·홈)나 INDEX 의 분위기 단어로 다시' % ' '.join(words),
              file=sys.stderr)
        return 1
    types = [t for t in (type_of(w) for w in words) if t]
    rest = [w for w in words if not type_of(w)]
    print('후보 %d개 — 유형: %s · 키워드: %s' % (len(found), ', '.join(types) or '-', ' '.join(rest) or '-'))
    for r in found:
        print('%s · %s · %s · %s · %sKB' % (shown(r['path']), r['service'], ', '.join(r['tags']), r['mood'], r['kb']))
    print('다음: 2~3개만 열어 후보마다 시안 1개(INDEX.md 쓰는 법 2)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
