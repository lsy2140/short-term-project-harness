---
name: evidence-gate
description: 구현·수정 작업을 마무리하거나 "완료", "됐어?", "검증해", "테스트 돌려", "제출 전 점검"이라는 요청에 사용. 모든 결과를 PASS/FAIL/NOT_RUN/HUMAN_CHECK로 보고하고, 실행 명령·출력·결과 파일 경로·계산 코드 위치를 함께 제시하며, preflight를 실행한다.
---

# evidence-gate

목표: "완료했습니다"를 증거로 바꾼다.

## 절차
1. 완료 조건(TASK.md 5번) 각각에 대해 테스트를 실행한다: `python3 -m unittest -v` (또는 README가 지정한 명령). 새 규칙은 먼저 FAIL이 나는지 확인한 뒤 구현한다. 새 규칙 테스트는 **위반 케이스 + 정상 통과 케이스 쌍**으로 둔다. 보안 계약 3종 — 출력 열 화이트리스트 / 불일치 참조 거부(`ValueError`) / 외부 실패 위장 금지(LLM·네트워크 실패를 정상 결과처럼 내보내지 않음) — 중 최소 1개는 실제 FAIL을 본 뒤 통과시킨다.
2. 출력 파일을 검증한다: 존재 / 행 수 / 헤더 / 정렬 / 인코딩 / 샘플 3행 눈 확인(`head`). 불변량(합계·키 중복·범위)을 한 줄 스크립트로 재계산한다. 규칙별 **발동 건수 표**(규칙 | 발동 행 수 | 예시 키)를 만들고, 0건인 규칙은 발동하는 입력을 만들어(`scripts/make_edge_cases.py`) 재확인한다. 민감 열(사번·이름·전화)이 출력 파일·로그·화면에 노출되는지 `grep`으로 확인한다. http.server 과제면 서버 실행 명령을 사람에게 주고(AGENTS 1절 11 — 직접 띄우지 않는다), 사람이 띄웠다고 하면 `python3 scripts/smoke_web.py http://127.0.0.1:8000`으로 스모크를 돌리고 결과 표를 붙인다.
3. `python3 scripts/preflight.py --require <필수 파일...>` 실행. exit 2는 통과가 아니다.
4. 보고 표:

| 항목 | 상태 | 명령 | 출력 요약 | 근거(파일:줄) |
|---|---|---|---|---|
| 결정 주석 목록 | | `grep -rn "결정:" src tests`(폴더명은 과제에 맞게) | 건수·누락 지점 | DECISIONS.md 1절과 대조 |

   단계 기록(**필수**): 이 단계의 `out/debug/NN_단계명/verify.json` 에 위 표의 숫자를 적는다 — `stage`·`what`·`status`·`files`(파일:줄 함수)·`method`·`counts`·`before_after`·`samples`·`tests`·`notes`(AGENTS 4절, 예 `docs/diagram_guide.md` 1절). 보고서 HTML 은 만들지 않는다(두 번째 세션의 `$stage-report` 가 이 파일로 만든다). Node ≥18 이 있으면 `$archify` 로 `docs/diagrams/` 구조도를 갱신할 수 있다(선택).

5. FAIL/NOT_RUN이 있으면 다음 행동 1개를 제안한다. HUMAN_CHECK(UI·판단)는 사람이 확인할 항목을 적는다.
6. 통과했으면 이 단계의 디버그 폴더(`scripts/debug_dir.py NN_단계명`)에 green.txt·verify.json 을 남기고 DECISIONS.md 4·6번에 한 줄 적는다.

## 금지
- 실행하지 않은 것을 PASS로 쓰기. 테스트 전부 SKIP을 통과로 쓰기. 숫자를 암산으로 보고하기.
