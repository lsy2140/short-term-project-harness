---
name: plan
description: PRD.md 가 v1 로 승인된 뒤, 코드 전에 쓴다. PRD ID 가 걸린 PLAN.md 4번 task 표(담당 A/B/C·검증 담당·완료 조건)와 4-2 연결 표, TASK 5, work/agents 역할 파일 3개, 담당별 시작 프롬프트를 낸다.
---

# plan

목표: 승인된 PRD 를 task 표(담당·검증 담당·테스트 이름)와 연결 표(누가 언제 무엇을 넘겨받나)로 바꾼다. 사람이 두 표를 승인(CP0)해야 에이전트를 띄운다.

## 입력
- `PRD.md`(2행 `v1` 이상) · `TASK.md` 3·5 · PRD 11 제출물 · 사람이 준 총 예산(분). `v0` 이면 `$prd`·승인을 먼저 권하고 멈춘다.
- 소유권 `work/README.md`, 역할 파일 틀 `work/agents/_template.md`.

## 절차
1. PRD 의 G 목표·MUST 를 2줄로 재진술한다. 다르게 읽히면 멈추고 묻는다.
2. PLAN.md 4번 task 표. 열 고정: `# | task | 담당 | 검증 | 입력 | 산출 파일 | 완료 조건 | 의존 | 분 | 상태`.
   - 담당 = A(A_core·핵심 계산) / B(B_web·화면) / C(C_verify·독립 검증). 검증 열 = 재계산·대조할 담당(구현 A 면 C).
   - 담당별 1번 task = 뼈대 확인. A: 계약 고정(`work/contract.md`)+scaffold 출력. B: `$web-ui 시안` → 사람 선택 → `$web-ui 초안`(더미 렌더). C: `check_contract` 뼈대+엣지 입력.
   - 그다음 규칙 1개 = task 1개 = `core/<task>.py` = `tests/test_<task>.py`(모듈명 영문 소문자, task 열은 `판정(judge)`). 마지막은 동결·문서(HANDOFF 초안·종합정리).
   - 입력 = 구현하는 PRD ID(`R01·B03`)+입력 파일. PRD 5 MUST·6 규칙·11 제출물이 어느 행에도 없으면 누락. `대기 Dnn` 규칙은 의존에 `Dnn`.
   - 번호 NN 은 전역 선배정(예 A 01~04 · B 05~07 · C 08~09) = `out/debug/NN_<모듈명>`, 중간에 안 바꾼다. 같은 산출 파일을 두 담당에 주지 않는다.
   - 완료 조건 = PRD 5 의 `test_<규칙>_<상황>` + 먼저 FAIL 을 볼 입력 1개. 못 재면 `HUMAN_CHECK`+이유. 거부 규칙은 `assertRaises(ValueError)` task 따로.
   - 검증 방법: 규칙형 → 규칙당 unittest / 분석형 → 핵심 숫자 재계산+샘플 N건 대조 / 화면형 → "[동작]하면 [결과]"+`smoke_web.py`+`HUMAN_CHECK`.
   - 의존은 번호로(이유 한 단어). 서로 독립인 A task 2~3개는 의존 열에 `묶음 P1`(A 가 하위 에이전트로 한 턴에, work/README.md 8; 1번·`대기 Dnn` 행 제외). PRD·README 에 없는 요구는 추측 말고 TASK 3 질문 또는 pending 으로.
   - 분 합계는 사람 예산 기준, 넘치면 뒤에서부터 `생략 후보`(생략은 CP 에서 사람이). 상태는 `NOT_RUN` 시작, 담당이 자기 행만(`NOT_RUN(생략: 사유)`).
3. PLAN 4-2 연결 표(`# | 신호 | 받는 담당 | 가져오는 것 | 하는 일 | 끝 신호 | 비고`):
   - 의존 열에 다른 담당 번호가 있으면 1행. 신호 = 그 task 끝(예 A 계약 끝 → B 더미 렌더 / A 판정 초안 끝 → B 표 열·C 재계산).
   - 같은 신호는 한 행(받는 담당을 함께). 가져오는 것은 파일·열·숫자로.
   - C 검증 쪼개기: 어느 신호 뒤 어느 task 를 어떤 방법(재계산·check_contract·smoke_web)으로 보나. CP1 전·CP2 전 각 1회 이상.
4. TASK 5: PRD ID 마다 1행(`# | PRD ID | 조건 | 테스트 | 검증 방법 | 상태`), 테스트 이름은 4번 표와 같게.
5. A↔B 계약: A 1번 task 산출 = `work/contract.md`(출력 파일·열·API 경로·샘플 2행). B 는 그것만 보고 더미 렌더. 변경은 pending 으로만.
6. `work/agents/{A_core,B_web,C_verify}.md` 를 `_template.md` 대로: ① 역할 ② 내 task(번호·PRD ID) ③ 쓰는 파일·포트(+pending 대역 A D01–D39 / B D40–D69 / C D70–D99) ④ 안 건드리는 파일 ⑤ 진행 로그 ⑥ 막힌 것 ⑦ 요청(`연결 N`·`@`). 2행 `상태:` 는 `대기`.
7. 시작 프롬프트 3개(사람이 각 창에 붙임): "`work/agents/X.md` 를 읽고 그 범위로만 · 첫 task NN · 기다릴 신호(연결 #) · 하위는 A 의 묶음만 · 꼬리 1줄". C 는 A·B 1번 task green 뒤.
8. 승인 요청: 4번 표와 4-2 연결 표를 함께 보인다. 셸 명령 `python3 scripts/scaffold.py --stages <A 모듈명들>`(쉼표, 예 `contract,judge`, A 만 1회, 빈 모듈 금지). 구조: 상수는 `config.py`(출처 주석) · 300줄/함수 40줄 넘으면 분리 · CLI 는 `--help`·exit 0/비0·stdout 결과/stderr 진단·파괴적 동작엔 `--dry-run`.

## 변형
- 1세션 폴백: 담당 열 전부 A, 연결 표는 생략(뼈대 확인 task 의 뜻은 유지).
- 웹 없는 과제: B = 출력·보고 형식 담당 또는 A+C 만.

## 출력
- PLAN 4번 표(10행 이내)·4-2 연결 표 · TASK 5 · `work/agents/*.md` 3개 · 시작 프롬프트 3개 · 승인 요청 1줄. 꼬리 1줄은 AGENTS 7절.

## 금지
- 코드·테스트 작성, 하위 에이전트·포크, README·PRD 에 없는 기능 task, "나머지 전부" 같은 검증 불가 task, 시간 경과로 자동 생략, 신호 없이 "알아서 맞춰" 식 연결.
