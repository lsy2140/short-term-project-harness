# RUN — 180분 운영 카드 (사람 전용 · 스크립트는 읽지 않음)

- Codex·스크립트는 이 파일을 읽지 않는다. 분 숫자는 '참고' 열 괄호 안 참고치뿐이다.
- 시계는 `python3 scripts/status.py` 가 남은 분을 표시만 한다. 행동은 사람이 체크포인트(CP)에서 고른다.
- B·C 에게 쓰지 않는 말: '병렬'·'하위 에이전트'. A 만 PLAN 4 `묶음 Pn`(독립 task 2~3개)을 하위 에이전트로 한 턴에(규칙 work/README.md 8). 포크(`codex fork`, 대화 전체 복제)는 금지. 창은 사람이 직접 연다.
- 붙여넣을 글: `docs/prompts.md`(예시 26개) · `docs/stakeholder_interview.md`(질문 묶음·PRD 검토 요청 5줄).
- 심사·정리용 글: `docs/judge_simulation.md` · `docs/implementation_summary.md`. 처음 보는 말은 8절 용어표.

| 창 | 역할 |
|---|---|
| T0 | 셸(사람 명령: scaffold·preflight·status·결정 폼. 서버는 Codex 가 띄우고 포트를 보고) |
| T1 | Codex A_core = 메인(`$kickoff`·`$prd`·`$plan` 도 여기, PRD.md 는 여기서만 쓴다) |
| T2 · T3 | Codex B_web · C_verify(같은 폴더에서 `codex`) |
| T4 | 심사 1회(`codex -s read-only`) |
| M | 메신저(담당자·도우미) |

- 기본은 A+B, C 는 A·B 첫 task 가 green 이 된 뒤. 창은 최대 5 + 메신저.
- 창 하나로 할 때(1세션 폴백): PLAN 4번 표 담당 열을 전부 A, T2·T3 는 열지 않는다. CP1(필수 출력이 올바른 헤더로 = 0점 아님)은 같다.
- 신호는 창이 스스로 읽는다: 보내는 창은 ⑦ `연결 N`, 받는 창은 task 끝마다·놀 때 30초 간격으로 `scripts/wait_signal.py`(기다리는 동안 그 창은 명령 실행 중, Esc 로 끊을 수 있다). 번호 붙은 요청(⑦ `@A C1:`)도 같은 길로 간다. 사람은 `status.py` 의 `연결 대기 N(→B)`·`요청 대기 C1(→A)` 가 한동안 남을 때만 받는 창에 prompts 14.

## 1. 사전 체험 카드

| # | 확인 | 행동·명령(창) | 끝 신호 | 참고 |
|---|---|---|---|---|
| 1 | 접속 | 규정 동의 → 웹캠 → 전체 화면 공유 → 감독 연결 | 감독 항목 전부 연결 | (-20분) |
| 2 | 하네스 | T0 `git clone <하네스 저장소 URL>` → 과제 폴더로 복사(하네스 README) | 과제 폴더에 AGENTS.md | 실패 → 5절 Plan C |
| 3 | 환경 | T0 `python3 scripts/preflight.py --env` | Python 3.9 이상 · 도구 유무 · `fromisoformat` OK | 특이점은 PRD 8(환경)에 1줄 |
| 4 | Codex | T1 `codex` → `/status` → `/model` → `/skills` | 스킬 6개: kickoff · prd · plan · rule-loop · web-ui · verify-agent | effort: A 는 규칙 설계·디버깅 때만 high, B·C medium |
| 5 | 동시 실행 | 같은 폴더에서 `codex` 2개를 띄워 각각 `ls` → 둘 다 종료 | 둘 다 응답 · 잠금·충돌 메시지 0 | (약 1분) |
| 6 | 미리보기 | T0 `python3 -m http.server 3000 --bind 0.0.0.0` → 미리보기 포트 3000 → Ctrl+C | 화면이 뜸 | 앱 8000 · 결정 폼 8010(막히면 8001·8011) |
| 6b | Codex 서버 | T1 에 "`python3 -m http.server 8100 --bind 0.0.0.0` 을 백그라운드로 띄우고 포트 보고" → 미리보기 8100 → T1 에 "끄기" | 보고 1줄 · 화면 뜸 · 끈 뒤 포트 닫힘 | 실패(권한·샌드박스) → 메시지 원문을 PRD 8 에, 그때만 T0 에서 같은 명령 |
| 7 | 이미지 생성(Codex 내장 도구, CLI 0.137 이상) | T1 에 "이미지 생성 도구로 1280×800 웹 화면 시안 1장을 `.tmp/sian_test.png` 로 저장" → T0 `ls -la .tmp/sian_test.png` · `codex features list` 의 `image_generation` 줄 | 파일 1개 · 성공·실패(실패면 메시지 원문) → PRD 8 | 성공 = 시안 5장·그림 생성 경로 / 실패 = HTML 시안 5개(`design-kit/illustrations/PROMPTS.md` 시안 절) · 그림은 키트 세트 → 데이터 그림 → 틴트 면 |
| 8 | 세션 로그 | 어느 Codex 창 로그가 수집되나(메인만 / 전부) | 범위 메모 | 어느 쪽이든 위임 원문은 PLAN 8 에 |
| 9 | 에디터·메신저·제출 | 새 파일 → '저장됨' 표시 · 담당자 창 보내기 1회 · 제출 버튼·제출 기준 폴더 경로 | 경로 메모 → PRD 8(환경) | |
- 시작 신호 뒤: README 정독(코드 금지) → 하네스 복사 → 2절 1단계.

## 2. 6단계 카드

| 단계 | 들어가는 조건 | 사람이 치는 것(창) | 끝 신호 | 참고 |
|---|---|---|---|---|
| 1 읽기·인터뷰·PRD | 시작 신호 뒤 | T1 prompts 1(`$kickoff`, 시작·마감 시각) → 질문을 M 에 3~4개씩 2~3회(첫 묶음 R+A+B+C, 다듬기 prompts 2) → 답을 T1 에 prompts 3(`답변 B2: …`) → T1 prompts 4(`$prd`) → PRD.md 를 읽고 prompts 5(검토 피드백) → PRD 검토 요청 5줄을 M 에 → 회신 원문을 붙여 T1 prompts 6("PRD 승인") | PRD v1 승인 + 담당자 회신 원문 기록(PRD 2행 버전 `v1` · DECISIONS 0 `담당자 회신: HH:MM "원문"`) · PRD 11 제출 표 초안 | (0–30분) 코드 금지 · 회신 전에 승인해도 됨(다른 점은 `요구사항 갱신:`) |
| 2 계획 CP0 | PRD v1 승인 | T1 prompts 8(`$plan`) → PLAN 4번 표·4-2 연결 표를 읽고 prompts 9(표 수정·"표 승인") → T0 `python3 scripts/scaffold.py --stages <A 모듈명,쉼표>`(영문 소문자, 예 `contract,judge`) 1회 | PLAN 4번 표(입력·완료 조건에 PRD ID) · 4-2 연결 표 · TASK 5 · `work/agents/` 3개 · run.py | (30–40분) 승인 안 함: 같은 산출 파일이 두 담당에 / PRD MUST 가 표에 없음 / 다른 담당을 기다리는 task 에 연결 행 없음 |
| 3 구현 | 표 승인 | T1 prompts 10(A_core 시작) → T2 `codex` + prompts 11(B_web `$web-ui 시안`, scaffold 출력 확인 뒤) → 시안 보고가 오면 미리보기 8000 `/draft/sian_N.png`(5장) 를 열어 색·배치·그림 자리를 비교 → T2 에 prompts 12(`시안 N 선택` 또는 `시안 생략`) → B 가 `design-kit/DESIGN_과제.md` 를 쓴 뒤 `$web-ui 초안` → T3 `codex` + prompts 13(C_verify, A·B 첫 task green 뒤) → 신호는 창이 wait_signal.py 로 읽음(status.py 에 `연결 대기` 가 남으면 prompts 14) → CP1 때 6절 'CP1' → 각 창 prompts 16(재개) | 담당별 `out/debug/NN_*/green.txt`·`verify.json` · `DESIGN_과제.md` 0절 출처 · CP1 = run.py 가 필수 출력을 올바른 헤더로 + B 더미 렌더 | (40–110분 · B 는 A +10분) 사람 = 고르기·답·놓친 신호(아래 표) |
| 4 통합 CP2 | 세 파일 2행 `상태:` 전부 green | T3 `$verify-agent <A·B task>` → T0 `preflight --require` · `check_contract`(3절) → T0 `preflight --freeze`(사람만) → 범위 축소 결정 → T4 심사 1회(prompts 22) → 미충족 2개를 담당 창에 prompts 16(재개) → T3 `$verify-agent summary`(FROZEN 전 = 핵심 3개 초안만) | preflight FAIL 0 · `.tmp/freeze_N/` · 미충족 ≤2 · 핵심 3개 초안 | (110–135분) CP1 이후 구조·라이브러리 변경 없음 |
| 5 화면 고도화 | `.tmp/freeze_N/` 있음 | T2 `$web-ui 최종`(B 가 서버 재시작·`ui_check --final`·헤드리스 스크린샷 3장까지 하고 포트 보고) → 미리보기에서 1280·834·390px 직접 클릭 → T2 에 prompts 20(1280·834·390 각 통과/이상) | `.figure` 빈 박스 0 · ui_check PASS · `screenshots/` 3장 · HUMAN_CHECK 기록 | (135–155분) 웹 없으면 건너뜀 · 그림 순서: 과제 전용 생성(5장 이하, 대기 중 미리 만든 것부터) → 키트 세트 → 데이터 그림 → 틴트 면 |
| 6 정리·제출 CP3 | 사람이 TASK 머리 Status 를 `FROZEN` 으로 | 세 창에 prompts 23(동결 선언) → T0 `python3 -m unittest -v` → T3 prompts 24(`$verify-agent summary`) → 4절 제출 카드(prompts 25) | TODO 0 · 핵심 3개 숫자 갱신 · PRD 11 표 전부 `[x]` · 제출 ID | (155–180분) 동결 뒤 허용 = 문서·근거(파일:줄)·복사·재시작 |

3단계에서 사람이 하는 일(고르기·답·놓친 신호):

| 이럴 때 | 사람이 하는 일 | 붙일 글(창) |
|---|---|---|
| B 가 시안 5개를 냈다(색·배치·그림 자리가 다른 5장) | `static/draft/sian_N` 을 미리보기·파일로 보고 `시안 N 선택`(이유 1줄, 색·배치를 따로 고르면 바꿀 점 줄) 또는 `시안 생략` | prompts 12 (T2) |
| `status.py` 에 `연결 대기 N(→B)` 가 남아 있다(받는 창이 놀고 있음) | 받는 창에 `연결 N` 한 줄 | prompts 14 (받는 창) |
| `결정 대기 Dnn` 으로 멈췄다 | 3절 '결정?' 대로 답 | prompts 15 (그 창) |
| ⑦ 의 `@B C1:` 요청 | 받는 창이 wait_signal 로 읽는다. `@사람` 과 `status.py` 에 `요청 대기` 로 남는 것만 다음 CP 까지 모았다가 답 | prompts 16 (각 창) |

- 남는 유일한 시간 규칙: 범위를 넓히는 요청에 Codex 가 `남은 N분 중 약 M분, 진행할까요?`(N 은 status.py) 로 되묻는다.
- 되묻기 없이 범위를 넓히기 시작하면 멈춘다.
- FROZEN 뒤 기능 요청에는 Codex 가 "동결 상태입니다, 해제할까요?" 로 되묻는다. 해제 안 하면 HANDOFF 6 에 1줄.
- PRD 승인 뒤 담당자 답이 바뀌면 T1 에 `요구사항 갱신: …`(prompts 7) → Codex 가 `$prd 갱신`(PRD 10절·바뀐 ID·영향 task).
- `$prd 갱신` 보고의 `@B`·`@C` 한 줄은 그 창에 전달한다.

## 3. 체크포인트 메뉴 (언제가 아니라 궁금할 때)

| 궁금한 것 | 명령·행동(창) |
|---|---|
| 지금 상태? | T0 `python3 scripts/status.py` — 1줄(끝에 PRD 버전), 추천·독촉 없음 |
| 다음에 누가 무엇을?(연결 표 보기) | PLAN 4-2 연결 표 · T0 `python3 scripts/wait_signal.py --me B --once`(B 몫 신호) · `status.py` 의 `연결 대기` |
| 시안 다시 보기 | T0 `ls static/draft/` · 미리보기 8000 `/draft/sian_N.png`(HTML 시안은 `/draft/sian_N.html`) · 고른 뒤에는 나머지 4장이 `.tmp/draft/` 에 있음 |
| 제출 가능? | T0 `python3 scripts/preflight.py --require <필수 파일>` + `python3 scripts/check_contract.py`(check_contract exit 2 는 통과 아님) · PRD 11 표 |
| 찍어둘까? | T0 `python3 scripts/preflight.py --freeze` — 사람만. 복구본 `.tmp/freeze_N/`(찍을 때마다 N+1) |
| 테스트 약해졌나? | T0 `python3 scripts/preflight.py --check-freeze` — 변경이 있으면 DECISIONS 에 승인 기록 |
| 결정? | 에이전트가 멈춘 CP 때만. 에디터로 `decisions/pending.md` 후보 `[ ]`→`[x]` + 메모 → 각 창에 prompts 15(결정 답 반영), 또는 아래 결정 폼 |
| 심사자라면? | T4 `codex -s read-only` → `docs/judge_simulation.md` 프롬프트(CP2 통합 뒤 1회) |
| 기록 규칙? | T0 `python3 scripts/debug_dir.py --check` · `python3 scripts/docmap.py --check` |
| 동결 선언 | TASK 머리 Status 를 `FROZEN` 으로 → 세 창에 prompts 23(동결 선언) → T0 `python3 -m unittest -v` |
| Codex 에게 | `STATE`(1줄 + 검증 안 된 항목 + 자가 감사 3개, prompts 17) · `요구사항 갱신: …`(prompts 7 → `$prd 갱신`) |
| 처음 보는 말? | 8절 용어표 |

결정 폼(`scripts/decide.py`):
1. 세 창이 모두 멈춘 CP 에만 연다(폼이 pending.md 를 다시 써서 append 중인 줄이 사라질 수 있다).
2. 다른 터미널(T0)에서 `python3 scripts/decide.py --port 8010` → `http://0.0.0.0:8010/` 이 찍힌다(막히면 `--port 8011`).
3. 미리보기 포트 8010 · 경로 `/` → 미답 카드마다 후보 1개(기타는 텍스트) + 메모 → `Dnn 답 기록`.
4. `담당자 확인: 필요` 카드는 담당자 답을 먼저 받는다.
5. 확인: `decisions/answers.md` 끝 `D07: A (메모: …) @HH:MM` · pending 후보 `[x]` → Ctrl+C → 각 창에 prompts 15.
6. 서버 없이 목록만 보기: `python3 scripts/decide.py --list`.
7. answers.md 에 손으로 쓴 줄은 `python3 scripts/decide.py --apply` 로 pending 후보 `[x]` 에 옮긴다(이것도 CP 때만).

## 4. 제출 카드 (순서 고정)

| # | 할 일 | 명령·행동(T0) | 확인 |
|---|---|---|---|
| 1 | PRD 11 표를 위에서부터 확인 | 행마다 파일·폴더·이름·형식을 README 원문과 대조 → 상태 `[x]` | 빠진 행 0 · 아래 2~9 의 대상 목록 |
| 2 | preflight 재실행 | `python3 scripts/preflight.py --require <PRD 11 의 파일들>` | exit 0 |
| 3 | 기록 규칙 | `python3 scripts/debug_dir.py --check` | exit 0 · 금지 패턴 0 |
| 4 | 서버 재시작 | T2(B, 1세션이면 T1)에 "서버 재시작" → `[서버] 포트 8000 열었음` 보고 확인 | 보고 1줄·미리보기 접속 |
| 5 | 화면 1회 | 미리보기 8000 → README 데모 순서 1회(정상 1 · 실패 1) | 콘솔 오류 0 · 834·390px 가로 스크롤 0 |
| 6 | 제출 기준 폴더 복사 | `cp -r <PRD 11 의 파일·폴더> <제출 기준 폴더>/ && ls -la <제출 기준 폴더>` | 파일 수 = PRD 11 표대로 |
| 7 | 저장됨 | 에디터 상단 '저장됨'(외부 변경 감지면 불러오기 뒤 재확인) | 미저장 0 |
| 8 | 제출 | 제출 버튼 → 미리보기 → 확정 | 확정 뒤 수정 불가 |
| 9 | 기록 | 제출 ID · 시각 · 파일 수 · 크기 → HANDOFF 1 | 완료 화면과 같음 |

- 웹 없는 과제는 4·5 를 건너뛴다. 제출 기준 폴더가 따로 없으면 6 은 `ls` 만.
- 서버 재시작·복사 표는 T2(1세션 T1)에 prompts 25 로 받는다. 복사는 사람이 T0 에서.

## 5. 막혔을 때

| 상황 | 할 일 |
|---|---|
| 같은 에러로 2회 실패 | 트레이스백 전문을 그 창에 붙이고 prompts 26(`$rule-loop`, 최소 재현 먼저) → DECISIONS 4 에 RED→FIX 1줄 |
| task 진전 없음 · 남은 분이 작음 | 기능 추가 중단 → PLAN 4번 표에 생략 후보 + 사유 → HANDOFF 5·6(조용히 틀린 코드가 더 큰 감점) |
| 코드가 이해 안 됨 | 그 창에 "더 단순하게, 내가 설명할 수 있게" + T3 `$verify-agent <task>` → `out/report/stages.md` 그 단계 절 |
| 결정을 못 정함 | 3절 '결정?'. 업무 사실이면 담당자(제외 목록 먼저 확인). 답이 올 때까지 에이전트는 다른 task |
| 담당자 답이 PRD 와 다름 | T1 에 `요구사항 갱신: …` → `$prd 갱신` 보고의 영향 task 를 담당 창에 전달 → 테스트부터 고친 뒤 코드 |
| 받는 창이 옛 계약·옛 헤더로 일함 | 신호를 놓친 것. PLAN 4-2 그 행을 다시 전달(prompts 14) → 바뀐 점만 고치게 |
| 시안 이미지가 안 만들어짐 | T2 에 같은 후보로 HTML 시안 5개(토큰 + 배치 CSS 1줄만 바꾼 페이지)를 요청. 고르는 답은 같다(`시안 N 선택`, prompts 12) |
| 두 에이전트가 같은 파일을 고침 | `work/README.md` 소유권 표로 한쪽을 되돌림. A↔B 계약 변경은 pending 으로만 |
| 에이전트가 `--freeze`·묶음 밖 하위 에이전트(B·C 포함)·보이는 브라우저 창 | 멈추고 "freeze·창·GUI 는 사람이 한다, 서버는 열되 포트를 보고"(AGENTS 1절) |
| `git clone` 실패 | Plan C: 저장소 웹 화면에서 AGENTS.md → TASK.md → PRD.md → DECISIONS.md 순으로 복사 |

## 6. 기다리는 동안 할 일

| 기다리는 때 | 사람이 하는 것 |
|---|---|
| 1 인터뷰 답 | README 재정독 · P0 체크(제출 파일명·형식 → PRD 11) · eda 요약을 내 말로 3줄 |
| 1 `$prd` | PRD 검토: 위험한 가정 2개·출처가 약한 규칙 2개·범위 밖 1개를 내 말로 → 고칠 곳 표시 |
| 2 `$plan` | PRD 3·5·6 을 소리 내어 읽기 · 되묻기 후보 2개 · 연결 표에서 내가 전달할 신호 세기 |
| 3 시안 대기 | 시안 5장을 PRD 4절 필수 블록과 나란히 놓고 첫 화면 핵심·배치·그림 자리·상태색·분위기 3단어를 비교 → `시안 N 선택` 1개(색·배치를 따로 고르면 바꿀 점 줄) |
| 3 구현 중 | `work/agents/*.md` 2행 `상태:` 만 읽기 · `status.py` 의 `연결 대기` 가 남으면 전달(prompts 14) · 나머지 ⑥⑦ 과 pending 미답은 CP 까지 모음 |
| 3 CP1 | 세 파일 ⑥⑦ + PLAN 표 → pending 답 → 담당자 묶음 → 생략 후보 결정 |
| 4 통합 | 심사 미충족 2개 · 핵심 3개(작동 원리·가장 위험한 실패·바꾼 것과 이유)를 내 말로 |
| 5·6 화면·정리 | 1280·834·390px 클릭 · 콘솔 · 설명 못 하는 코드 찾기 · PRD 11 표 상태 채우기 |

## 7. 제출 체크

- [ ] PRD 11 표 상태 전부 `[x]` — 파일명·경로·형식이 README 와 같음(대소문자·확장자·헤더·정렬·인코딩)
- [ ] 샘플 3행 눈 대조 · 입력 원본 불변
- [ ] 실행 명령을 실제로 쳐 봄(`--smoke`) · `unittest` 숫자(과제 `tests/` 만) · `check_contract.py` exit 0 · 발동 0건 규칙 없음
- [ ] `preflight.py` exit 0(SKIP 사유 설명 가능) · `docmap.py --check` · `debug_dir.py --check` exit 0
- [ ] `--check-freeze` 변경 0 또는 DECISIONS 승인 기록
- [ ] TASK 머리 Status `FROZEN` · 5 완료 조건(PRD ID) ↔ 테스트 1:1 · 템플릿 문구 0
- [ ] PRD 2행 버전 `v1` 이상·승인 시각 · 5 MUST 마다 TASK 5 행 · 10절 변경 이력 수 = `요구사항 갱신:` 수
- [ ] FROZEN 에서 `python3 -m unittest` 가 TASK·PLAN·DECISIONS·HANDOFF·PRD·README 의 자리표시를 FAIL 로 잡는다
- [ ] 자리표시(`HH:MM`·`__:__`·`__/__`·`exit __`·`___`·'아직 전송하지 않음')는 한 문장 목표·머리줄·HANDOFF 실행 블록까지 채운다
- [ ] PLAN 4 상태 열 전부 PASS/HUMAN_CHECK/`NOT_RUN(생략: 사유)`(status.py 에 `task 8/9(생략 1)` 로 따로) · 8 위임 원문 · 9 한계
- [ ] PLAN 4-2 연결 표의 신호마다 받는 쪽 반영 기록(work 파일 ⑤ '연결 N 반영')
- [ ] DECISIONS 0 PRD 송부·회신 시각·원문 · 1 결정자 열 · 4 RED→FIX · 5 한계 · 6 검증 로그
- [ ] HANDOFF 1 숫자 한 줄 · 5 한계+믿지 말 것 · 6 다음 할 일
- [ ] README 데모 순서(정상·실패) · 실제 vs 목업 · TODO/TBD 0 · 주장마다 근거(파일:줄)
- [ ] `status.py` 에 `대기 없음`(pending 미답 0) · `요구사항 갱신:` 이 PLAN 8(원문)·PRD 10(내용)·DECISIONS 0(시각) 에
- [ ] `out/report/stages.md`(검증한 단계 전부) · `out/report/implementation_summary.md` 핵심 3개 숫자 갱신 · README 에 링크
- [ ] 종합정리 표 7개 · 결함 사례 카드 수 = DECISIONS 4 행 수 · 동시 요청 때 지금 동작(테스트 또는 '확인 안 함')
- [ ] `work/agents/*.md` 2행 `상태:` 최종 · ⑤ 로그 남음
- [ ] 웹: 콘솔 오류 0 · 834·390px 가로 스크롤 0 · `screenshots/` 3장(desktop·tablet·mobile) · `.figure` 빈 박스 0 · 외부 URL 0
- [ ] 웹 디자인: `design-kit/DESIGN_과제.md` 있음 · README 에 고른 참고 md 출처 1줄(예 ko-design-md, CC BY 4.0)
- [ ] 심사 미충족 보완 또는 한계 기록 · 내가 설명 못 하는 코드 0줄

## 8. 용어 10개

| 용어 | 쉬운 말 | 어디서 쓰나 |
|---|---|---|
| CP0~CP3 | 사람이 멈춰서 고르는 지점: 계획 승인 · 뼈대 작동 · 필수 기능 완료 · 동결 | TASK 머리 2행 · 2절 단계 카드 |
| PRD v0 / v1 | 요구사항 초안 / 사람이 승인한 판 | PRD 2행 · status.py 줄 끝 |
| 연결 표 · 신호 | 한 담당의 task 가 끝나면 다른 담당이 이어받는 순서표 · 그 "끝" 보고 | PLAN 4-2 · `wait_signal.py` · prompts 14(놓쳤을 때) |
| pending · Dnn | 사람이 골라야 할 업무 결정 목록 · 그 번호 | `decisions/pending.md` · 3절 '결정?' |
| HUMAN_CHECK | 사람이 눈으로 확인(화면·판단) | PLAN 4·5 · HANDOFF 5 |
| NOT_RUN | 아직 안 돌림(통과가 아님) | PLAN 4 상태 열 · 보고 |
| green / RED→FIX | 테스트 통과 기록 / 실패를 다시 만들어 본 뒤 고침 | `out/debug/NN_*/` · DECISIONS 4 |
| freeze / FROZEN | 지금 상태를 찍어 둔 복구본 / 기능 변경을 끝낸 동결 선언 | `preflight --freeze` · TASK 머리 2행 |
| 근거(파일:줄) | 주장마다 붙이는 위치: 파일:줄·테스트 이름·명령 | 모든 제출 문서 |
| 시안 | 화면 후보(그림 또는 HTML) 5개(색 md × 배치 × 그림 자리가 서로 다름), 사람이 `시안 N 선택` 으로 1개 고름 | `static/draft/` · prompts 11·12 |
