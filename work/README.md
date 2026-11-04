# work — 다중 에이전트 작업 폴더
<!-- $plan 이 agents/_template.md 로 A_core.md·B_web.md·C_verify.md 를 만든다. 창 하나(1세션)로 하면 A_core.md 하나 -->

## 소유권
| 주인 | 쓰는 것 | 규칙 |
|---|---|---|
| A_core 핵심기술 | `run.py`·`core/**`·`tests/test_<A단계>.py`·`out/` 출력 파일(debug·report 제외)·`work/contract.md`·debug A 단계·`PRD.md`(T1 의 `$kickoff`·`$prd` 초안·갱신) | 자기 모듈 테스트 + `run.py` 출력 확인. PRD 는 사람 승인 뒤 10절로만 바꾼다 |
| B_web 웹서비스 | `app.py`·`static/**`(시안 `static/draft/` 포함)·`design-kit/DESIGN_과제.md`·`tests/test_<B단계>.py`·`screenshots/`(desktop·tablet·mobile 3장)·debug B 단계 | contract 샘플로 렌더 → CP2 에서 실값. `run.py` 는 `@A` 요청, 포트 8000 은 B 가 열고 보고 |
| C_verify 기술검증 | `scripts/check_contract.py`·`tests/test_contract.py`·`out/report/stage_NN.md`·`out/report/implementation_summary.md`·debug C 단계·HANDOFF 초안 | 연결 표의 신호 뒤에 검증. 전체 unittest·preflight·check_contract·`run.py` 독립 재실행. 서버는 B 의 8000, 없을 때만 8100+ 임시 뒤 끔 |
| 사람 | PRD 승인(v1)·TASK·DECISIONS·PLAN(상태 열은 담당이 자기 행만)·`decisions/answers.md`·README | 후보 `[x]` 선택·decide.py(8010) 는 CP 때 · 연결 신호 전달 |
| 읽기 전용 | `data/`·`design-kit/`(B 의 `DESIGN_과제.md` 제외)·AGENTS.md · B·C 에게는 `PRD.md` 도 | 변형 입력은 `.tmp/<이름>/` · PRD 를 바꿔야 하면 ⑦ `@사람` |

## 충돌 규칙
1. 같은 파일을 두 담당에 배정하지 않는다. 남의 파일이 필요하면 자기 파일 ⑦ 에 `@B`·`@사람` 으로 요청한다.
2. 단계 번호 NN 은 PLAN 4 에서 전역으로 미리 나눈다(out/debug 폴더 충돌 0).
3. pending ID 대역: A D01–D39 · B D40–D69 · C D70–D99. 자기 항목은 끝에 덧붙이기(append)만.
4. 후보 `[x]` 선택·decide.py 는 CP 때 사람, `반영 HH:MM` 표시는 그 대역 담당.
5. A↔B 계약(`work/contract.md`) 변경은 pending 항목으로만 한다.
6. 진행 로그 ⑤ 는 덧붙이기만(삭제 금지). 요청·질문은 task 끝에 ⑦ 로만, 즉답을 요구하지 않는다.
7. 연결 표(PLAN 4-2)의 신호는 사람이 전달한다: 한 창의 "task N 끝" 보고(⑦ `연결 N`) → 받는 창에 `docs/prompts.md` 14.
