---
name: verify-agent
description: C_verify 창에서 사람이 `$verify-agent <task 번호들|summary>` 로 부를 때만 쓴다. 독립 재계산으로 확인한 단계 보고 out/report/stage_NN.md 1쪽, 또는 종합정리(동결 전이면 핵심 3개 초안)를 낸다.
---

# verify-agent

목표: 구현과 따로 숫자를 다시 세서, 사람이 코드를 열지 않고 단계 결과를 믿을 수 있게 한다. C_verify 역할 파일 `work/agents/C_verify.md` 를 먼저 읽고, 사람이 `$verify-agent` 로 부를 때만 돈다.

## 범위
- 쓰기: C 소유 파일만 — `scripts/check_contract.py`·`tests/test_contract.py`·`out/report/stage_NN.md`·`out/report/implementation_summary.md`·debug C 단계·HANDOFF 초안·`work/agents/C_verify.md`(AGENTS 9절).
- A·B 의 코드·테스트·문서는 읽기만. 고칠 곳은 자기 파일 ⑦ `@A`·`@B`·`@사람` 으로.
- 실행: 전체 unittest·preflight·check_contract·`run.py` 독립 재실행은 C 와 사람만(AGENTS 9절). 서버는 B 의 8000(B 파일 ③), 없을 때만 8100+ 임시 점검 → 보고 → 끈다(AGENTS 1절 11). 변형 입력은 `.tmp/C_verify/`.
- 심사는 이 스킬이 아니다(별도 read-only 창, `docs/judge_simulation.md`).

## `$verify-agent 3-5` — 단계 검증
1. 범위: 번호 = PLAN 4 task 번호 = `out/debug/NN_…/` 의 NN. 폴더가 없으면 그 단계는 `NOT_RUN`. 부르는 때는 PLAN 4-2 연결 표의 신호 뒤(CP1 전·CP2 전 각 1회 이상).
2. 근거 읽기: `verify.json` → `green.txt`·`red.txt` → `note.md` → PLAN 4 그 행(PRD ID) → DECISIONS 1·4·6. 코드는 `python3 scripts/docmap.py` 로 위치를 보고 필요한 줄만 `sed -n 'a,bp'`(통째 금지). 출력 파일은 `head -3`·`wc -l`.
3. 독립 재계산: 구현 함수를 import 하지 않고 입력·출력 파일에서 다시 센다(`python3 -c` 또는 `tests/test_contract.py`) — 행 수·헤더·정렬·키 중복·범위·`입력 == 통과 + 제외`.
4. 계약: `python3 scripts/check_contract.py`(파일·열·인코딩·실행). exit 2 는 통과가 아니다(출력도 `run.py` 도 없음). 먼저 INPUTS 자리표시 `data/<입력>.csv` 를 과제 입력으로 채운다. FAIL M-noop = RUN_CMD 가 환경변수 INPUT_DIR 을 안 읽음 → 기본 입력 폴더를 `os.environ.get('INPUT_DIR', 'data')` 로(못 하면 METAMORPHIC 을 None) · FAIL M-0 = 변형할 입력 파일 없음.
5. 엣지 발동: 발동 0건인 규칙은 `python3 scripts/make_edge_cases.py <csv> --out .tmp/C_verify/edge` 로 발동 입력을 만들어 재확인.
6. `out/report/stage_NN.md`(범위가 여러 개면 `stage_NN-MM.md`) 1쪽, 쉬운 말 개조식:
   - 첫 3줄: 무엇이 됐나 / 숫자가 맞나(재계산 일치 여부) / 남은 위험.
   - 단계마다: 역할 1줄 · 구현 위치(`파일:줄` 함수) · 방법 3~5줄 · 결과 숫자(출처) · 샘플 2행(입력→출력) · 테스트 · 상태.
   - 끝: 불일치 목록 · 근거 없음 목록.
   - 숫자는 verify.json·`out/` 파일(또는 그것을 다시 센 명령 출력)에서만 옮긴다. 근거가 없으면 `근거 없음`, 상태 `NOT_RUN`.
7. 불일치는 직접 고치지 않는다: 담당에 ⑦ 요청 + 자기 파일 ⑥ 에 DECISIONS 5 후보 1줄.

## `$verify-agent summary` — 종합정리
1. 조건: TASK 머리 2행 `Status: \`FROZEN\`` 뒤에 전부. FROZEN 전(CP2)이면 맨 위 '핵심 3개'(`docs/implementation_summary.md` 골격) 초안만 쓰고 멈춘다.
2. `docs/implementation_summary.md` 의 문서 모양·골격·표 7개·정리 항목을 그대로 따라 `out/report/implementation_summary.md` 를 쓴다. 표·항목·행을 골라 줄이지 않는다(해당 없으면 `해당 없음 — 이유`). 규칙 ↔ 코드 ↔ 검증 표는 PRD 6 규칙마다, 결함 사례 카드는 DECISIONS 4 행 수만큼.
3. 읽기: PRD(5·6·9·10)·TASK·DECISIONS(0·1·4·5·6)·PLAN 4·4-2·8·`python3 scripts/docmap.py` 출력·`decisions/answers.md`·`out/debug/*/verify.json`·`note.md`·`out/report/stage_*.md`·`work/agents/*.md` ⑤.
4. 빠짐없이: 핵심 알고리즘·바꾼 것(전/후·이유) / 규칙별 지킴·검증 / 데이터·모듈 흐름·단계별 관리 주체 / 실서비스 한계·동시 요청 때 지금 동작(테스트가 없으면 `확인 안 함`) / 결함마다 발견 → 맡긴 것·직접 한 것 → 검증.
5. 대조: 적은 코드 좌표는 `sed -n 'N,Mp'` 로 다시 열어 문장과 맞춘다. 숫자는 verify.json·green.txt 와 맞춘다. 기록에 없으면 '근거 없음 목록'으로.
6. 사람이 자기 말로 설명하기 어려운 문장은 쉬운 말로 다시 쓴다.

## 보고 5줄
파일 경로 / 단계별 상태 / 핵심 숫자 3개(출처) / 불일치·근거 없음 / 사람이 먼저 볼 곳. 꼬리 1줄은 AGENTS 7절.

## 금지
- 추정 숫자, 대조하지 않은 좌표, A·B 파일 수정, B 의 8000 서버 끄기·8100+ 밖 포트, 요청 없는 재생성, 제출물에 없는 기능·검증을 있는 것처럼 쓰기.
