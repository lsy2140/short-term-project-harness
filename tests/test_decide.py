# -*- coding: utf-8 -*-
"""scripts/decide.py 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_decide -v
분류: 파싱(제목·영향·기본값·시각·후보 3개·추천·기타·답변됨) / 기록(pending [x]·answers 줄 형식·기타 채움·이미 답한 항목·없는 ID·빈 선택) /
      파일 계약(키트의 decisions/pending.md·answers.md) / 서버(임시 포트: GET / 200 · POST 200 · 깨진 POST 400 · 경로 탈출 403 · CSS 200)."""
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, 'scripts')
KIT = os.path.join(ROOT, 'design-kit')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import decide  # noqa: E402

# AGENTS.md 5절의 예시 그대로 + 이미 답한 항목 1개 + 제목에 괄호가 든 항목 1개
SAMPLE = '''# 결정 대기함
형식 설명 줄 — 항목 밖의 `- [ ]` 는 무시된다.

## D07 심한 정도 계산식   (영향: 정렬·상위5 | 기본값: A | 안 정하면: 63분에 A 로 진행)
- [ ] A. 최대 이탈률 — 담당자 "많이 벗어난 것부터"에 가장 가까움 (추천)
- [ ] B. 평균 이탈률 — 튀는 값에 둔감하지만 짧은 위험을 낮게 봄
- [ ] C. 기타: ____
메모:

## D08 시간대 처리   (영향: 모든 시각 열 | 기본값: B | 안 정하면: 70분에 B 로 진행)
- [ ] A. UTC 로 통일
- [x] 반영 10:35 B. KST 로 통일 (추천)
메모: 담당자가 KST 라고 답함

## D09 (예시) 반올림 자리   (영향: 출력 숫자 | 기본값: A | 안 정하면: 80분에 A 로 진행)
- [ ] A. 소수 둘째 자리 (추천)
- [ ] B. 정수
메모:
'''


def _get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read().decode('utf-8', 'replace')


def _post(url, body, ctype='application/x-www-form-urlencoded'):
    req = urllib.request.Request(url, data=body.encode('utf-8'), headers={'Content-Type': ctype}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


# ---------------------------------------------------------------- 파싱
class TestParsePending(unittest.TestCase):
    def setUp(self):
        self.items = decide.parse_pending(SAMPLE)
        self.by_id = {it['id']: it for it in self.items}

    def test_three_items_found_and_header_lines_ignored(self):
        self.assertEqual([it['id'] for it in self.items], ['D07', 'D08', 'D09'])

    def test_title_impact_default_fallback(self):
        it = self.by_id['D07']
        self.assertEqual(it['title'], '심한 정도 계산식')
        self.assertEqual(it['impact'], '정렬·상위5')
        self.assertEqual(it['default'], 'A')
        self.assertEqual(it['fallback'], '63분에 A 로 진행')
        self.assertEqual(it['memo'], '')
        self.assertFalse(it['answered'])

    def test_three_candidates_with_recommend_and_other(self):
        cands = self.by_id['D07']['candidates']
        self.assertEqual([c['key'] for c in cands], ['A', 'B', 'C'])
        self.assertEqual([c['recommended'] for c in cands], [True, False, False])
        self.assertEqual([c['other'] for c in cands], [False, False, True])
        self.assertNotIn('(추천)', cands[0]['text'])          # 추천 표시는 플래그로 빠진다
        self.assertTrue(cands[0]['text'].startswith('최대 이탈률'))
        self.assertEqual(cands[2]['text'], '기타')             # ____ 는 비어 있는 것으로 본다

    def test_answered_item_with_applied_mark(self):
        it = self.by_id['D08']
        self.assertTrue(it['answered'])
        self.assertEqual(it['answer'], 'B')
        self.assertEqual(it['applied'], '10:35')
        self.assertEqual(it['memo'], '담당자가 KST 라고 답함')
        self.assertTrue(it['candidates'][1]['recommended'])

    def test_title_with_parentheses_keeps_meta_parsing(self):
        it = self.by_id['D09']
        self.assertEqual(it['title'], '(예시) 반올림 자리')
        self.assertEqual(it['default'], 'A')
        self.assertEqual(it['fallback'], '80분에 A 로 진행')

    def test_unanswered_skips_answered(self):
        self.assertEqual([it['id'] for it in decide.unanswered(self.items)], ['D07', 'D09'])

    def test_empty_text_gives_no_items(self):
        self.assertEqual(decide.parse_pending(''), [])

    def test_parse_answers_reads_choice_other_memo_time(self):
        text = decide.ANSWERS_HEADER + 'D07: A (메모: 담당자 말대로) @10:31\nD09: C (기타: 중앙값) @10:40\n잡담 줄\n'
        ans = decide.parse_answers(text)
        self.assertEqual(ans['D07'], {'choice': 'A', 'other': '', 'memo': '담당자 말대로', 'time': '10:31'})
        self.assertEqual(ans['D09']['other'], '중앙값')
        self.assertNotIn('D08', ans)


# ---------------------------------------------------------------- 기록 (순수 함수)
class TestRecord(unittest.TestCase):
    def test_mark_answered_sets_x_and_keeps_other_lines(self):
        out = decide.mark_answered(SAMPLE, 'D07', 'A')
        self.assertIn('- [x] A. 최대 이탈률', out)
        before, after = SAMPLE.split('\n'), out.split('\n')
        self.assertEqual(len(before), len(after))
        diff = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
        self.assertEqual(len(diff), 1, '바뀐 줄은 정확히 1줄')
        self.assertTrue(decide.parse_pending(out)[0]['answered'])

    def test_mark_answered_other_fills_blank(self):
        out = decide.mark_answered(SAMPLE, 'D07', 'C', other='중앙값')
        self.assertIn('- [x] C. 기타: 중앙값', out)
        self.assertNotIn('____', out.split('## D08')[0])

    def test_answer_line_format(self):
        line = decide.format_answer_line('D07', 'A', memo='담당자 말대로', hhmm='10:31')
        self.assertEqual(line, 'D07: A (메모: 담당자 말대로) @10:31')
        self.assertRegex(decide.format_answer_line('D07', 'A', hhmm='09:05'), r'^D07: A @\d\d:\d\d$')
        self.assertEqual(decide.format_answer_line('D07', 'C', other='중앙값', memo='x', hhmm='10:31'), 'D07: C (기타: 중앙값) (메모: x) @10:31')
        self.assertRegex(decide.format_answer_line('D07', 'B'), r'^D07: B @\d\d:\d\d$')  # 시각 생략 시 현재 시각

    def test_append_answer_keeps_header_and_adds_one_line(self):
        out = decide.append_answer(decide.ANSWERS_HEADER, 'D07', 'A', memo='m', hhmm='10:31')
        self.assertTrue(out.startswith(decide.ANSWERS_HEADER))
        self.assertTrue(out.endswith('D07: A (메모: m) @10:31\n'))
        out2 = decide.append_answer('', 'D07', 'A', hhmm='10:31')  # 빈 파일이면 머리 2줄부터
        self.assertTrue(out2.startswith('# 결정 답변'))
        self.assertEqual(decide.parse_answers(out2)['D07']['choice'], 'A')

    def test_memo_newlines_are_folded_to_one_line(self):
        line = decide.format_answer_line('D07', 'A', memo='첫 줄\n둘째 줄', hhmm='10:31')
        self.assertEqual(line.count('\n'), 0)
        self.assertIn('첫 줄 / 둘째 줄', line)

    def test_already_answered_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            decide.mark_answered(SAMPLE, 'D08', 'A')
        self.assertIn('이미', str(ctx.exception))

    def test_unknown_id_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            decide.mark_answered(SAMPLE, 'D99', 'A')
        self.assertIn('D99', str(ctx.exception))

    def test_empty_choice_and_unknown_choice_are_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            decide.mark_answered(SAMPLE, 'D07', '')
        self.assertIn('D07', str(ctx.exception))
        with self.assertRaises(ValueError) as ctx2:
            decide.mark_answered(SAMPLE, 'D07', 'Z')
        self.assertIn('Z', str(ctx2.exception))

    def test_other_without_text_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            decide.mark_answered(SAMPLE, 'D07', 'C', other='  ')
        self.assertIn('기타', str(ctx.exception))

    def test_record_answer_writes_both_files_or_neither(self):
        tmp = tempfile.mkdtemp(prefix='decide_rec_')
        try:
            p, a = os.path.join(tmp, 'pending.md'), os.path.join(tmp, 'answers.md')
            decide.write_text(p, SAMPLE)
            line = decide.record_answer(p, a, 'D07', 'A', memo='메모', hhmm='11:00')
            self.assertEqual(line, 'D07: A (메모: 메모) @11:00')
            self.assertIn('- [x] A. 최대 이탈률', decide.read_text(p))
            self.assertTrue(decide.read_text(a).endswith(line + '\n'))
            snap_p, snap_a = decide.read_text(p), decide.read_text(a)
            with self.assertRaises(ValueError):
                decide.record_answer(p, a, 'D07', 'B', hhmm='11:01')   # 두 번째 답은 거부, 파일 불변
            self.assertEqual((decide.read_text(p), decide.read_text(a)), (snap_p, snap_a))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- 파일 계약 (키트에 든 실제 파일)
class TestKitFiles(unittest.TestCase):
    """decisions/ 두 파일의 형식 계약(AGENTS.md 5절). 내용은 시험 중 바뀌므로(Codex 가 항목을 더하고 사람이 답한다) 형식만 본다."""

    def test_kit_pending_items_follow_format(self):
        items = decide.parse_pending(decide.read_text(os.path.join(ROOT, 'decisions', 'pending.md')))
        self.assertTrue(items, 'pending.md 에 항목(## Dnn …)이 하나도 없음')
        ids = [it['id'] for it in items]
        self.assertEqual(len(ids), len(set(ids)), '결정 ID 중복: %s' % ids)
        for it in items:
            with self.subTest(item=it['id']):
                self.assertTrue(it['title'], '제목 없음')
                self.assertTrue(it['default'] and it['fallback'], "기본값과 '안 정하면' 시각은 필수")
                keys = [c['key'] for c in it['candidates']]
                self.assertTrue(2 <= len(keys) <= 4, '후보는 2~4개: %s' % keys)
                self.assertEqual(len(keys), len(set(keys)), '후보 키 중복: %s' % keys)
                self.assertIn(it['default'], keys, '기본값 %r 이 후보 키에 없음' % it['default'])
                self.assertEqual(sum(1 for c in it['candidates'] if c['recommended']), 1, '추천은 정확히 1개')

    def test_kit_answers_header_and_lines_parse(self):
        text = decide.read_text(os.path.join(ROOT, 'decisions', 'answers.md'))
        self.assertTrue(text.startswith(decide.ANSWERS_HEADER), 'answers.md 머리 2줄이 ANSWERS_HEADER 와 다름')
        body = [line for line in text[len(decide.ANSWERS_HEADER):].splitlines() if line.strip()]
        bad = [line for line in body if not decide.ANSWER_RE.match(line.strip())]
        self.assertEqual(bad, [], '`D07: A (메모: …) @HH:MM` 형식이 아닌 줄')
        self.assertEqual(len(decide.parse_answers(text)), len({line.split(':')[0] for line in body}))


# ---------------------------------------------------------------- 서버 (임시 포트 — 시험장 포트 충돌 방지)
class TestServer(unittest.TestCase):
    PORT = 0

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='decide_srv_')
        cls.pending = os.path.join(cls.tmp, 'pending.md')
        cls.answers = os.path.join(cls.tmp, 'answers.md')
        decide.write_text(cls.pending, SAMPLE)
        decide.write_text(cls.answers, decide.ANSWERS_HEADER)
        cls.srv = decide.make_server('127.0.0.1', cls.PORT, cls.pending, cls.answers, KIT)
        cls.PORT = cls.srv.server_address[1]  # 0 → OS 가 고른 빈 포트
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:%d' % cls.PORT

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join(5)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_get_root_200_html_with_form(self):
        st, ct, body = _get(self.base + '/')
        self.assertEqual(st, 200)
        self.assertIn('text/html', ct)
        self.assertIn('name="viewport"', body)
        self.assertEqual(len(re.findall(r'<h1[\s>]', body)), 1)
        self.assertIn('D07', body)
        self.assertIn('name="choice" value="A"', body)
        self.assertIn('<details', body)                       # 답변된 D08 은 접힌 상태
        self.assertIn('답변됨', body)
        self.assertNotRegex(body, r'(src|href)=["\']https?://')
        self.assertNotIn('#', re.search(r'<style>(.*?)</style>', body, re.S).group(1))  # raw hex 없음

    def test_post_ok_200_and_files_updated(self):
        body = urllib.parse.urlencode({'id': 'D09', 'choice': 'A', 'memo': '폼에서 기록'})
        st, html = _post(self.base + '/answer', body)
        self.assertEqual(st, 200)
        self.assertIn('기록됨', html)
        self.assertIn('- [x] A. 소수 둘째 자리', decide.read_text(self.pending))
        self.assertRegex(decide.read_text(self.answers), r'D09: A \(메모: 폼에서 기록\) @\d\d:\d\d\n$')

    def test_post_broken_400(self):
        st, html = _post(self.base + '/answer', '{not json', 'application/json')
        self.assertEqual(st, 400)
        self.assertIn('폼 본문이 아님', html)
        st2, html2 = _post(self.base + '/answer', urllib.parse.urlencode({'id': 'D99', 'choice': 'A'}))
        self.assertEqual(st2, 400)
        self.assertIn('D99', html2)
        st3, html3 = _post(self.base + '/answer', urllib.parse.urlencode({'id': 'D07', 'choice': ''}))
        self.assertEqual(st3, 400)
        self.assertIn('고르지 않음', html3)
        self.assertNotIn('[x] A. 최대', decide.read_text(self.pending))   # 거부된 요청은 파일을 바꾸지 않는다

    def test_path_traversal_403(self):
        st, _, _ = _get(self.base + '/design-kit/../AGENTS.md')
        self.assertEqual(st, 403)
        st2, _, _ = _get(self.base + '/../../etc/passwd')
        self.assertEqual(st2, 403)
        st3, _, _ = _get(self.base + '/design-kit/%2e%2e/AGENTS.md')
        self.assertEqual(st3, 403)

    def test_static_css_200_and_non_css_404(self):
        st, ct, body = _get(self.base + '/design-kit/tokens.css')
        self.assertEqual(st, 200)
        self.assertIn('text/css', ct)
        self.assertIn('--brand', body)
        st2, _, _ = _get(self.base + '/design-kit/ui_check.py')
        self.assertEqual(st2, 404)
        st3, _, _ = _get(self.base + '/nothing')
        self.assertEqual(st3, 404)


if __name__ == '__main__':
    unittest.main()
