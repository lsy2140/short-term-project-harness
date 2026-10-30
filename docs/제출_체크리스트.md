# 제출 체크리스트 (작업 종료 15분 전부터)

## 파일
- [ ] README가 지정한 필수 파일명·경로·형식 그대로 존재 (대소문자·확장자·폴더)
- [ ] 출력 파일 헤더·정렬·인코딩(UTF-8)·구분자 확인, 샘플 3행 눈으로 대조
- [ ] 에디터 저장 상태 "저장됨" (외부 변경 감지 시 '외부 변경 불러오기' 후 재확인)
- [ ] 입력 원본 파일을 수정하지 않았음

## 증거
- [ ] `python3 -m unittest -v` 실행 결과 숫자 기록 (PASS/FAIL/SKIP)
- [ ] `python3 scripts/preflight.py --require <파일...>` exit 0 (exit 2는 통과 아님)
- [ ] 핵심 숫자 1개 이상 다른 방법으로 재계산
- [ ] out/debug 단계 폴더에 첫 완주·규칙·1차 동결·동결 기록 · `.tmp/freeze_1/` 복구본 있음(`preflight.py --check-freeze` 변경 0 또는 승인 기록)
- [ ] `python3 scripts/check_contract.py` exit 0 · 규칙별 발동 건수 0인 규칙 없음
- [ ] `python3 scripts/debug_dir.py --check` exit 0 (`out/debug` 총 40파일 이하 · 폴더당 5파일 · 스냅샷 `*_before`·입력 복사본·chrome_profile 없음 · `.tmp/`는 제출물 아님)
- [ ] 웹 과제: 미리보기 DevTools 콘솔 오류 0 / 창 폭 390px 가로 스크롤 없음 / README 데모 순서 1회 완주(시각 기록) / screenshots/ 2장

## 문서
- [ ] README: 한 문장 / 자동화한 것·안 한 것 / 실행 명령(실제 실행) / 현재 상태(숫자) / 결정·이유 / 한계
- [ ] PLAN.md 8번 AI 활용 기록, 9번 정직한 제한사항
- [ ] DECISIONS.md 0번 합의문(담당자 확인 시각), 5번 실패 지점, 6번 검증 로그, 7번 제출 직전 상태
- [ ] TASK.md Status `FROZEN`, 8번 하지 못한 것
- [ ] TODO·미구현·TBD·템플릿 문구 0 · 모든 주장에 증거 좌표
- [ ] HANDOFF.md 작성 · README에 데모 순서·실제 vs 목업 표
- [ ] `decisions/pending.md` 미답 항목 0 (답했거나 `[x] 기본값 적용`으로 표시) · 반영한 결정은 DECISIONS.md 1·7번에 있음
- [ ] `out/report.html`(flowmap) 최신 — 마지막 기능 뒤 `python3 scripts/flowmap.py` 재실행 · `docs/diagrams/`(archify, 있으면)와 함께 README 데모 순서에 링크

## 서술형 준비 (확정 전)
- [ ] 답변 3개(상충 조건 / 위험한 실패 / 믿지 않은 지점) 문장화
- [ ] 내 제출물 해당 질문 6개 골라 소리 내어 답해 봄
- [ ] 막힌 질문은 DECISIONS.md에 한 줄 추가

## 제출 동작
- [ ] "제출하고 문제풀기" → 미리보기 → "제출물 확정하고 문제풀기"
- [ ] 완료 화면의 제출 ID·시각·파일 수·크기 확인
