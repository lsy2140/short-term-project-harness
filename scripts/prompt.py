#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prompt.py — docs/프롬프트_예시.md 의 프롬프트 템플릿을 터미널에 찍는다(복사용 · 토큰 0).
사용:
  python3 scripts/prompt.py              # 목록: 번호 · 제목 · 구간
  python3 scripts/prompt.py 11           # 11번 본문만 (복사해서 Codex 에 붙여넣는다)
  python3 scripts/prompt.py 트레이스백     # 키워드(제목·키워드·구간) 검색: 1개면 본문, 여러 개면 후보 목록
  python3 scripts/prompt.py --all        # 전체 본문 (번호·제목 머리 포함)
  python3 scripts/prompt.py --file 경로  # 다른 md 파일을 읽는다 (기본: docs/프롬프트_예시.md)
문서 쪽 형식(tests/test_prompt.py 가 고정):
  ## N. 제목 / - 구간: … / - 키워드: a, b / ```본문``` / - 막는 실수: … / - 출처: …
  번호 없는 `## 절` 은 예시로 세지 않는다. 본문은 예시 안의 첫 코드 블록이다.
종료 코드: 0 성공(목록·후보 목록 포함) / 1 해당 없음·파일 없음 / 2 파싱 결과 0건(통과 아님)
"""
import argparse
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DOC = os.path.join(ROOT, 'docs', '프롬프트_예시.md')

HEAD_RE = re.compile(r'^## (\d+)\. (.+?)\s*$')
OTHER_HEAD_RE = re.compile(r'^#{1,2} ')
FIELD_RE = re.compile(r'^- (구간|키워드|막는 실수|출처):\s*(.*)$')
FIELD_KEYS = {'구간': 'section', '키워드': 'keywords', '막는 실수': 'mistake', '출처': 'source'}


def parse_examples(text):
    """md 본문 → 예시 목록(문서 순서). 각 항목: num·title·section·keywords(list)·body·mistake·source."""
    examples = []
    cur = None
    in_fence = False
    body_lines = None  # 현재 코드 블록이 '이 예시의 본문'일 때만 list
    for raw in text.splitlines():
        line = raw.rstrip('\r')
        if in_fence:
            if line.strip().startswith('```'):
                in_fence = False
                if body_lines is not None and cur is not None:
                    cur['body'] = '\n'.join(body_lines).strip('\n')
                body_lines = None
            elif body_lines is not None:
                body_lines.append(line)
            continue
        if line.strip().startswith('```'):
            in_fence = True
            body_lines = [] if (cur is not None and cur['body'] is None) else None
            continue
        m = HEAD_RE.match(line)
        if m:
            cur = {'num': int(m.group(1)), 'title': m.group(2).strip(), 'section': '',
                   'keywords': [], 'body': None, 'mistake': '', 'source': ''}
            examples.append(cur)
            continue
        if OTHER_HEAD_RE.match(line):
            cur = None  # 번호 없는 절(사용법·출처 목록·의견)은 예시가 아니다
            continue
        if cur is None:
            continue
        f = FIELD_RE.match(line)
        if f:
            key = FIELD_KEYS[f.group(1)]
            val = f.group(2).strip()
            if key == 'keywords':
                cur['keywords'] = [k.strip() for k in val.split(',') if k.strip()]
            else:
                cur[key] = val
    for ex in examples:
        if ex['body'] is None:
            ex['body'] = ''
    return examples


def find(examples, query):
    """번호(또는 'N번')면 정확히 그 예시, 아니면 제목·키워드·구간에 부분 일치(대소문자 무시)하는 예시들."""
    q = query.strip()
    if q.endswith('번') and q[:-1].isdigit():
        q = q[:-1]
    if q.isdigit():
        return [e for e in examples if e['num'] == int(q)]
    ql = q.lower()
    if not ql:
        return []
    hits = []
    for e in examples:
        if ql in e['title'].lower() or ql in e['section'].lower() or any(ql in k.lower() for k in e['keywords']):
            hits.append(e)
    return hits


def fmt_list(examples):
    """구간별로 묶은 목록 문자열."""
    lines = []
    cur = None
    for e in examples:
        if e['section'] != cur:
            cur = e['section']
            lines.append('[%s]' % cur)
        lines.append('  %2d. %s' % (e['num'], e['title']))
    return '\n'.join(lines)


def fmt_all(examples):
    parts = []
    for e in examples:
        parts.append('### %d. %s [%s]\n%s' % (e['num'], e['title'], e['section'], e['body']))
    return '\n\n'.join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description='docs/프롬프트_예시.md 의 템플릿을 번호나 키워드로 찾아 본문만 출력한다(복사용).',
        epilog='예: python3 scripts/prompt.py 11 | python3 scripts/prompt.py 트레이스백 | python3 scripts/prompt.py --all')
    ap.add_argument('query', nargs='?', help='번호(11, 11번) 또는 키워드(제목·키워드·구간). 없으면 목록')
    ap.add_argument('--all', action='store_true', help='전체 본문을 번호·제목 머리와 함께 출력')
    ap.add_argument('--file', default=DEFAULT_DOC, help='읽을 md 파일 (기본 docs/프롬프트_예시.md)')
    args = ap.parse_args(argv)

    try:
        with open(args.file, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except OSError as e:
        print('파일을 열 수 없음: %s (%s) → docs/프롬프트_예시.md 가 있는지 확인하거나 --file 로 경로 지정' % (args.file, e),
              file=sys.stderr)
        return 1
    examples = parse_examples(text)
    if not examples:
        print('예시 0건 — "## N. 제목" 형식을 확인. 0건은 통과가 아니다', file=sys.stderr)
        return 2

    if args.all:
        print(fmt_all(examples))
        return 0
    if not args.query:
        print(fmt_list(examples))
        print('본문: python3 scripts/prompt.py <번호|키워드> · 전체: --all', file=sys.stderr)
        return 0
    hits = find(examples, args.query)
    if not hits:
        print('해당 없음: %r → python3 scripts/prompt.py 로 목록을 보고 번호나 키워드를 다시 지정' % args.query, file=sys.stderr)
        return 1
    if len(hits) > 1:
        print(fmt_list(hits))
        print('후보 %d개 — 번호로 다시 지정: python3 scripts/prompt.py <번호>' % len(hits), file=sys.stderr)
        return 0
    print(hits[0]['body'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
