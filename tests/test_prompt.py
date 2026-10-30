# -*- coding: utf-8 -*-
"""scripts/prompt.py · docs/프롬프트_예시.md 계약 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_prompt -v
고정하는 것: 예시 수 25 · 구간별 개수 · 4요소(본문·막는 실수·출처·구간) · 번호/키워드 조회 · 없는 키워드 exit 1 · 파싱 형식."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPT = os.path.join(ROOT, 'scripts', 'prompt.py')
DOC = os.path.join(ROOT, 'docs', '프롬프트_예시.md')

# 'prompt' 는 짧은 이름이라 설치 패키지와 겹칠 수 있어 파일 경로로 직접 읽는다.
_spec = importlib.util.spec_from_file_location('kit_prompt', SCRIPT)
prompt_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prompt_cli)

# 개선계획 6절: 킥오프 3 · 인터뷰 4 · 첫 완주 3 · 규칙 구현 5 · 캐내기 2 · 디버그 2 · 문서 3 · 심사자 1 · 서술형 2 = 25
EXPECTED_SECTIONS = [('킥오프', 3), ('인터뷰', 4), ('첫 완주', 3), ('규칙 구현', 5), ('캐내기', 2),
                     ('디버그', 2), ('문서', 3), ('심사자', 1), ('서술형', 2)]
UNIQUE_KEYWORD = '트레이스백'   # 18번에만 있는 키워드
UNIQUE_KEYWORD_NUM = 18
AMBIGUOUS_KEYWORD = '인터뷰'    # 구간 이름이라 4개가 걸린다


def run_cli(*args, timeout=30):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, encoding='utf-8',
                       errors='replace', env=env, cwd=ROOT, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


# ---------------------------------------------------------------- 문서 계약
class TestDocContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOC, 'rb') as fh:
            cls.raw = fh.read()
        cls.text = cls.raw.decode('utf-8')
        cls.examples = prompt_cli.parse_examples(cls.text)

    def test_example_count_is_25(self):
        self.assertEqual(len(self.examples), 25)

    def test_numbers_are_1_to_25_in_order(self):
        self.assertEqual([e['num'] for e in self.examples], list(range(1, 26)))

    def test_every_example_has_body_mistake_source_section(self):
        for e in self.examples:
            with self.subTest(num=e['num']):
                self.assertTrue(e['title'], '제목 없음')
                self.assertTrue(e['section'], '구간 없음')
                self.assertTrue(e['body'].strip(), '본문(코드 블록) 없음')
                self.assertTrue(e['mistake'].strip(), '막는 실수 없음')
                self.assertTrue(e['source'].strip(), '출처 없음')
                self.assertGreaterEqual(len(e['keywords']), 2, '키워드 2개 이상')

    def test_section_counts_match_plan(self):
        counts = []
        for e in self.examples:
            if counts and counts[-1][0] == e['section']:
                counts[-1][1] += 1
            else:
                counts.append([e['section'], 1])
        self.assertEqual([tuple(c) for c in counts], EXPECTED_SECTIONS)

    def test_titles_are_unique(self):
        titles = [e['title'] for e in self.examples]
        self.assertEqual(len(titles), len(set(titles)))

    def test_mistake_is_one_line_sentence(self):
        for e in self.examples:
            with self.subTest(num=e['num']):
                self.assertNotIn('\n', e['mistake'])
                self.assertGreater(len(e['mistake']), 10)

    def test_doc_is_utf8_lf_without_bom(self):
        self.assertFalse(self.raw.startswith(b'\xef\xbb\xbf'), 'BOM 있음')
        self.assertNotIn(b'\r\n', self.raw, 'CRLF 있음')
        self.assertTrue(self.raw.endswith(b'\n'))

    def test_no_unfinished_markers_in_doc(self):
        # preflight 의 미완성 표기 검사와 같은 단어. 테스트 소스에 그 단어를 그대로 두지 않으려고 조각으로 만든다.
        markers = ['TO' + 'DO', 'FIX' + 'ME', 'T' + 'BD', '미' + '구현', 'place' + 'holder']
        low = self.text.lower()
        for m in markers:
            self.assertNotIn(m.lower(), low, m)

    def test_unique_keyword_belongs_to_one_example(self):
        hits = prompt_cli.find(self.examples, UNIQUE_KEYWORD)
        self.assertEqual([h['num'] for h in hits], [UNIQUE_KEYWORD_NUM])

    def test_side_session_opinion_section_exists(self):
        self.assertIn('## 보조 세션 운영 의견', self.text)
        self.assertIn('prompt.py', self.text.split('## 보조 세션 운영 의견')[1])


# ---------------------------------------------------------------- 파싱 형식 (합성 입력)
FIXTURE = """# 제목

## 사용법
```bash
python3 scripts/prompt.py
```

## 1. 첫 번째 예시
- 구간: 구간A
- 키워드: 알파, beta
```
본문 1행
본문 2행
```
- 막는 실수: 실수 A.
- 출처: 출처 A

## 2. 두 번째 예시
- 구간: 구간B
- 키워드: 감마
```
본문 둘
```
설명 문단(파서가 무시한다).
```
두 번째 코드 블록은 본문이 아니다
```
- 막는 실수: 실수 B.
- 출처: 출처 B

## 의견
- 구간: 이 줄은 예시가 아니다
"""


class TestParserFormat(unittest.TestCase):
    def test_fixture_parses_two_examples_with_fields(self):
        ex = prompt_cli.parse_examples(FIXTURE)
        self.assertEqual([e['num'] for e in ex], [1, 2])
        self.assertEqual(ex[0]['title'], '첫 번째 예시')
        self.assertEqual(ex[0]['section'], '구간A')
        self.assertEqual(ex[0]['keywords'], ['알파', 'beta'])
        self.assertEqual(ex[0]['body'], '본문 1행\n본문 2행')
        self.assertEqual(ex[0]['mistake'], '실수 A.')
        self.assertEqual(ex[0]['source'], '출처 A')

    def test_only_first_fence_is_body_and_outside_fences_are_ignored(self):
        ex = prompt_cli.parse_examples(FIXTURE)
        self.assertEqual(ex[1]['body'], '본문 둘')
        self.assertEqual(ex[1]['section'], '구간B')

    def test_number_lookup_accepts_beon_suffix(self):
        ex = prompt_cli.parse_examples(FIXTURE)
        self.assertEqual([e['num'] for e in prompt_cli.find(ex, '2번')], [2])
        self.assertEqual(prompt_cli.find(ex, '3'), [])

    def test_keyword_lookup_is_case_insensitive_on_title_keywords_section(self):
        ex = prompt_cli.parse_examples(FIXTURE)
        self.assertEqual([e['num'] for e in prompt_cli.find(ex, 'BETA')], [1])
        self.assertEqual([e['num'] for e in prompt_cli.find(ex, '구간b')], [2])
        self.assertEqual([e['num'] for e in prompt_cli.find(ex, '예시')], [1, 2])

    def test_crlf_input_is_tolerated(self):
        ex = prompt_cli.parse_examples(FIXTURE.replace('\n', '\r\n'))
        self.assertEqual(len(ex), 2)
        self.assertEqual(ex[0]['body'], '본문 1행\n본문 2행')


# ---------------------------------------------------------------- CLI
class TestCli(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DOC, 'r', encoding='utf-8') as fh:
            cls.examples = prompt_cli.parse_examples(fh.read())

    def test_no_args_lists_all_25_with_sections(self):
        code, out, err = run_cli()
        self.assertEqual(code, 0, err)
        for e in self.examples:
            self.assertIn('%2d. %s' % (e['num'], e['title']), out)
        for name, _ in EXPECTED_SECTIONS:
            self.assertIn('[%s]' % name, out)

    def test_number_prints_body_only(self):
        code, out, err = run_cli('11')
        self.assertEqual(code, 0, err)
        self.assertEqual(out.rstrip('\n'), self.examples[10]['body'])
        self.assertNotIn('막는 실수', out)
        self.assertNotIn('출처', out)

    def test_unique_keyword_prints_body(self):
        code, out, err = run_cli(UNIQUE_KEYWORD)
        self.assertEqual(code, 0, err)
        self.assertEqual(out.rstrip('\n'), self.examples[UNIQUE_KEYWORD_NUM - 1]['body'])

    def test_ambiguous_keyword_lists_candidates_exit_0(self):
        code, out, err = run_cli(AMBIGUOUS_KEYWORD)
        self.assertEqual(code, 0, err)
        hits = prompt_cli.find(self.examples, AMBIGUOUS_KEYWORD)
        self.assertGreaterEqual(len(hits), 2)
        for h in hits:
            self.assertIn('%2d. %s' % (h['num'], h['title']), out)
        self.assertIn('후보', err)

    def test_unknown_keyword_exits_1_with_next_action(self):
        code, out, err = run_cli('이런키워드는없다')
        self.assertEqual(code, 1)
        self.assertEqual(out, '')
        self.assertIn('해당 없음', err)
        self.assertIn('prompt.py', err)

    def test_all_flag_contains_every_title_and_body(self):
        code, out, err = run_cli('--all')
        self.assertEqual(code, 0, err)
        for e in self.examples:
            self.assertIn('### %d. %s' % (e['num'], e['title']), out)
            self.assertIn(e['body'], out)

    def test_help_exits_0(self):
        code, out, err = run_cli('--help')
        self.assertEqual(code, 0, err)
        self.assertIn('--all', out)

    def test_missing_file_exits_1(self):
        code, out, err = run_cli('--file', os.path.join(ROOT, 'docs', '없는_파일.md'))
        self.assertEqual(code, 1)
        self.assertIn('파일을 열 수 없음', err)

    def test_file_without_examples_exits_2(self):
        fd, path = tempfile.mkstemp(suffix='.md')
        os.close(fd)
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('# 비어 있음\n\n## 사용법\n본문 없음\n')
            code, out, err = run_cli('--file', path)
            self.assertEqual(code, 2)
            self.assertIn('0건', err)
        finally:
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
