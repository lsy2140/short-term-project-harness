# work — 다중 에이전트 작업 폴더
<!-- $plan 이 agents/_template.md 로 A_core.md·B_web.md·C_verify.md 를 만든다. 창 하나(1세션)로 하면 A_core.md 하나 -->

## 소유권
| 주인 | 쓰는 것 | 규칙 |
|---|---|---|
| A_core 핵심기술 | `run.py`·`core/**`·`tests/test_<A단계>.py`·`out/` 출력 파일(debug·report 제외)·`work/contract.md`·debug A 단계·`PRD.md`(T1 의 `$kickoff`·`$prd` 초안·갱신) | 자기 모듈 테스트 + `run.py` 출력 확인. PRD 는 사람 승인 뒤 10절로만 바꾼다 |
| B_web 웹서비스 | `app.py`·`static/**`(시안 `static/draft/` 포함)·`design-kit/DESIGN_과제.md`·`tests/test_<B단계>.py`·`screenshots/`(desktop·tablet·mobile 3장)·debug B 단계 | contract 샘플로 렌더 → CP2 에서 실값. `run.py` 는 `@A` 요청, 포트 8000 은 B 가 열고 보고 |
| C_verify 기술검증 | `scripts/check_contract.py`·`tests/test_contract.py`·`out/report/stages.md`(단계마다 절, 검증할 때마다 갱신)·`out/report/implementation_summary.md`·debug C 단계·HANDOFF 초안 | 연결 표의 신호 뒤에 검증. 전체 unittest·preflight·check_contract·`run.py` 독립 재실행. 서버는 B 의 8000, 없을 때만 8100+ 임시 뒤 끔 |
| 사람 | PRD 승인(v1)·TASK·DECISIONS·PLAN(상태 열은 담당이 자기 행만)·`decisions/answers.md`·README | 후보 `[x]` 선택·decide.py(8010) 는 CP 때 · 연결 신호 전달 |
| 읽기 전용 | `data/`·`design-kit/`(B 의 `DESIGN_과제.md` 제외)·AGENTS.md · B·C 에게는 `PRD.md` 도 | 변형 입력은 `.tmp/<이름>/` · PRD 를 바꿔야 하면 ⑦ `@사람` |

## 충돌 규칙
1. 같은 파일을 두 담당에 배정하지 않는다. 남의 파일이 필요하면 자기 파일 ⑦ 에 `@B`·`@사람` 으로 요청한다.
2. 단계 번호 NN 은 PLAN 4 에서 전역으로 미리 나눈다(out/debug 폴더 충돌 0).
3. pending ID 대역: A D01–D39 · B D40–D69 · C D70–D99. 자기 항목은 끝에 덧붙이기(append)만.
4. 후보 `[x]` 선택·decide.py 는 CP 때 사람, `반영 HH:MM` 표시는 그 대역 담당.
5. A↔B 계약(`work/contract.md`) 변경은 pending 항목으로만 한다.
6. 진행 로그 ⑤ 는 덧붙이기만(삭제 금지). 요청·질문은 task 끝에 ⑦ 로만, 즉답을 요구하지 않는다.
7. 연결 표(PLAN 4-2)의 신호: 보내는 창은 task 끝에 ⑦ `연결 N` 1줄(숫자 필수). 받는 창은 task 끝마다 `python3 scripts/wait_signal.py --me X --once` 로 자기 몫을 읽어 반영하고 ⑤ 에 '연결 N 반영' 행을 남긴다(이 글자가 "받았다" 표시). 할 일이 없으면 `--once` 없이 기다린다(30초 간격·20분, 명령 시간 제한은 넉넉히, 끝나면 다시). 사람은 `status.py` 의 `연결 대기 N(→B)` 가 남을 때만 전달(`docs/prompts.md` 14). 요청도 같다: ⑦ 에 `- @A C1: 내용`(받는 담당 + 내 글자·번호), 받는 창이 wait_signal 로 읽고 ⑤ 에 'C1 반영'(또는 보낸 쪽이 'C1 해결 HH:MM')으로 닫는다. 번호 없는 `@A:` 줄은 추적하지 않고, `@사람` 은 사람이 CP 때 본다.
8. A 의 묶음 병렬(하위 에이전트, A 만): PLAN 4 의존 열에 같은 `묶음 Pn` 이 붙은 A task 2~3개를 한 턴에, 한 번에 한 묶음. 조건 = 서로 다른 `core/<task>.py`·`tests/test_<task>.py`, 서로의 산출이 입력이 아님, 같은 `대기 Dnn` 에 기대지 않음, 1번 task(계약) green 뒤. 하위 1개 = task 1개 = `.agents/skills/rule-loop/SKILL.md` ①~③ + 자기 `out/debug/NN_*/` 4파일. 하위 문맥은 비어 있으므로 지시에 규칙 문장(PRD ID)·결정(Dnn 답)·대상 함수 시그니처·파일 경로를 다 적는다. 하위가 안 건드리는 것: `core/config.py`·`core/pipeline.py`·`run.py`·`work/`·`decisions/`·DECISIONS·PLAN·TASK — 필요한 상수·pending 후보·`# 결정:` 은 보고로 돌려준다. A 본창: 하위 보고를 받아 config·pipeline 연결 → 묶음 테스트 전부 1회 → pending append·⑤ 'NN 끝' 행·PLAN 4 상태 → 보고 1회(꼬리 1줄). 하위가 FAIL 로 끝나면 그 task 만 본창이 ③ 재현부터.
