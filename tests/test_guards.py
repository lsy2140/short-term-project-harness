# -*- coding: utf-8 -*-
"""scripts/guards.py 규칙 테스트 (unittest, Python 3.9). 실행: python3 -m unittest tests.test_guards -v
분류: 우회 5케이스(띄어쓰기·NFD·대소문자·zero-width·기호 끼워넣기) / 과차단 방지 2케이스 / 합계 보존 / 마스킹 / 타임아웃·근거."""
import copy
import os
import sys
import time
import unicodedata
import unittest

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:  # noqa
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, 'scripts')
# 'scripts' 라는 이름은 다른 설치 패키지와 겹칠 수 있어(Anaconda 등) 폴더를 직접 경로에 넣고 모듈 이름으로 가져온다.
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

from guards import (  # noqa: E402
    check_banned, check_grounded, exclude_with_reason, mask_pii,
    normalize_for_check, normalize_hangul_only, with_timeout_fallback,
)

BANNED = ['무결점', '100% 보장', 'Lorem ipsum', '완치']


# ---------------------------------------------------------------- 우회 5케이스
class TestBannedBypass(unittest.TestCase):
    def test_spaces_inside_word_are_caught(self):
        self.assertEqual(check_banned('이 제품은 무 결 점 입니다', BANNED), ['무결점'])

    def test_nfd_decomposed_hangul_is_caught(self):
        nfd = unicodedata.normalize('NFD', '무결점 크림')
        self.assertNotEqual(nfd, '무결점 크림')  # 실제로 분해됐는지 전제 확인
        self.assertEqual(check_banned(nfd, BANNED), ['무결점'])

    def test_case_insensitive_latin(self):
        self.assertEqual(check_banned('LOREM IPSUM dolor', BANNED), ['Lorem ipsum'])

    def test_zero_width_characters_are_stripped(self):
        self.assertEqual(check_banned('무​결‍점', BANNED), ['무결점'])

    def test_symbols_and_digits_between_hangul_are_ignored(self):
        self.assertEqual(check_banned('무.결-점 / 1OO% 보장', BANNED), ['무결점'])
        self.assertEqual(check_banned('무1결2점', BANNED), ['무결점'])  # 한글만 정규화로 잡힘


# ---------------------------------------------------------------- 과차단 방지 2케이스
class TestBannedNoOverBlock(unittest.TestCase):
    def test_similar_but_different_words_pass(self):
        """'완치' 금지어는 '완전 치유'(띄어쓰기 제거해도 '완전치유')나 '처리' 에 걸리지 않는다."""
        self.assertEqual(check_banned('완전 치유를 목표로 처리합니다', BANNED), [])

    def test_empty_inputs_do_not_hit_or_crash(self):
        self.assertEqual(check_banned('', BANNED), [])
        self.assertEqual(check_banned(None, BANNED), [])
        self.assertEqual(check_banned('무결점', []), [])
        self.assertEqual(check_banned('무결점', None), [])


# ---------------------------------------------------------------- 정규화 계약
class TestNormalize(unittest.TestCase):
    def test_normalize_for_check_keeps_only_alnum_hangul_lower(self):
        self.assertEqual(normalize_for_check(' ABC-123 가나다! '), 'abc123가나다')

    def test_normalize_hangul_only(self):
        self.assertEqual(normalize_hangul_only('A가1나-다'), '가나다')

    def test_hits_are_unique_and_in_input_order(self):
        self.assertEqual(check_banned('무결점 100% 보장 무결점', ['100% 보장', '무결점', '무결점']), ['100% 보장', '무결점'])


# ---------------------------------------------------------------- 근거 검사
class TestGrounded(unittest.TestCase):
    def test_claim_not_in_evidence_is_reported(self):
        missing = check_grounded('비타민C 보습 미백 크림', ['비타민C', '보습', '미백'], ['name: 보습 크림', 'tags: 수분, 비타민C'])
        self.assertEqual(missing, ['미백'])

    def test_vocab_absent_from_text_is_not_reported(self):
        self.assertEqual(check_grounded('보습 크림', ['미백'], ['name: 보습 크림']), [])


# ---------------------------------------------------------------- 제외 사유·합계 보존
ROWS = [
    {'id': 'A', 'stock': 3, 'price': 1000, 'cat': 'skin'},
    {'id': 'B', 'stock': 0, 'price': None, 'cat': 'skin'},   # 두 규칙 위반 → 첫 사유만
    {'id': 'C', 'stock': 5, 'price': None, 'cat': 'hair'},
    {'id': 'D', 'stock': 2, 'price': 500, 'cat': 'none'},
]
RULES = [
    ('out_of_stock', lambda r: r['stock'] <= 0),
    ('missing_price', lambda r: r['price'] is None),
    ('unknown_category', lambda r: r['cat'] not in ('skin', 'hair')),
]


class TestExcludeWithReason(unittest.TestCase):
    def test_total_is_conserved_and_first_reason_only(self):
        kept, excluded, counts = exclude_with_reason(ROWS, RULES)
        self.assertEqual(len(ROWS), len(kept) + len(excluded))
        self.assertEqual([r['id'] for r in kept], ['A'])
        self.assertEqual([(r['id'], why) for r, why in excluded], [('B', 'out_of_stock'), ('C', 'missing_price'), ('D', 'unknown_category')])
        self.assertEqual(counts, {'out_of_stock': 1, 'missing_price': 1, 'unknown_category': 1})
        self.assertEqual(sum(counts.values()), len(excluded))

    def test_input_is_not_mutated_and_empty_rows_ok(self):
        snapshot = copy.deepcopy(ROWS)
        exclude_with_reason(ROWS, RULES)
        self.assertEqual(ROWS, snapshot)
        kept, excluded, counts = exclude_with_reason([], RULES)
        self.assertEqual((kept, excluded), ([], []))
        self.assertEqual(counts, {'out_of_stock': 0, 'missing_price': 0, 'unknown_category': 0})

    def test_predicate_exception_excludes_row_instead_of_crashing(self):
        kept, excluded, counts = exclude_with_reason([{'id': 'X'}], [('needs_stock', lambda r: r['stock'] <= 0)])
        self.assertEqual(kept, [])
        self.assertEqual(excluded[0][1], 'needs_stock')


# ---------------------------------------------------------------- 타임아웃 폴백
class TestTimeoutFallback(unittest.TestCase):
    def test_fast_function_returns_ok(self):
        self.assertEqual(with_timeout_fallback(lambda: 42, -1, 1.0), (42, 'ok'))

    def test_slow_function_returns_fallback_with_timeout_status(self):
        value, status = with_timeout_fallback(lambda: time.sleep(2) or 'late', 'fallback', 0.2)
        self.assertEqual((value, status), ('fallback', 'timeout'))

    def test_raising_function_returns_fallback_with_error_status(self):
        def boom():
            raise RuntimeError('model down')
        self.assertEqual(with_timeout_fallback(boom, lambda: 'fb', 1.0), ('fb', 'error'))


# ---------------------------------------------------------------- PII 마스킹
class TestMaskPii(unittest.TestCase):
    def test_phone_and_employee_id_are_masked_by_default(self):
        out = mask_pii('담당 김철수 010-1234-5678 / 02 123 4567, 사번 E123456 및 20231234')
        self.assertNotIn('1234-5678', out)
        self.assertNotIn('E123456', out)
        self.assertNotIn('20231234', out)
        self.assertEqual(out.count('[전화]'), 2)
        self.assertEqual(out.count('[사번]'), 2)
        self.assertIn('김철수', out)  # 이름 패턴을 주지 않으면 이름은 건드리지 않는다

    def test_name_pattern_masks_names_and_lot_ids_survive(self):
        out = mask_pii('LOT-24A113 담당 김철수, 사번 E123456', name_pat=r'김[가-힣]{2}')
        self.assertIn('[이름]', out)
        self.assertNotIn('김철수', out)
        self.assertIn('LOT-24A113', out)  # 로트 ID 는 사번 패턴(6~8자리 숫자)에 걸리지 않는다

    def test_none_and_empty(self):
        self.assertEqual(mask_pii(None), '')
        self.assertEqual(mask_pii(''), '')


if __name__ == '__main__':
    unittest.main()
