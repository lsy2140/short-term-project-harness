# 도식화 사용법 — flowmap(숫자 보고) 과 archify(구조도)

코드와 숫자만 보고는 "맞게 돌고 있나"를 사람도 심사자도 판단하기 어렵다. 두 도구는 역할이 다르고 둘 다 미리보기 탭에서 본다.

| | `scripts/flowmap.py` | `$archify` (`.agents/skills/archify/`) |
|---|---|---|
| 무엇 | **숫자 보고서** `out/report.html`: 파이프라인 도식 + 합계 보존 띠 + 규칙 발동 건수 + 결정 목록 + 검증 배지 | **구조도** `docs/diagrams/*.html`: architecture·dataflow·sequence·lifecycle (코드 근거 SRC 마커) |
| 입력 | `docs/flow.json` (사람·Codex 가 실행 결과를 옮겨 적음) | 저장소 자체(`--repo-root .`) 또는 README 설명 |
| 조건 | Python 3.9 표준 라이브러리만, 외부 자원 0 | Node ≥18. Chrome 없으면 browser-check 만 skipped(exit 2)이고 HTML 은 유효 |
| 비용 | 1턴 미만, 토큰 거의 0 | 1장당 1~2턴·약 30~60k 토큰(스키마·예시 읽기 포함). 토큰은 채점 기록 |
| 답하는 질문 | 입력이 어디서 몇 건 빠졌나, 규칙이 실제로 발동했나, 무엇을 검증했나 | 모듈이 어떻게 이어지나, 요청이 어떤 순서로 흐르나 |

## 1. flowmap — 언제
AGENTS.md 4절·8절: **기능 하나가 끝날 때마다** `docs/flow.json` 갱신 → `python3 scripts/flowmap.py` → 미리보기. 1차 동결(110분)·최종 동결(144~165분)에 다시 돌린다(RUN.md 구간표). `evidence-gate` 4단계가 이것을 필수로 부른다. 코드가 이해 안 될 때도 이 그림으로 입력→규칙→출력을 본다(RUN.md 결정 트리).

## 2. flowmap — 스펙 채우는 법 (`docs/flow.example.json` 을 복사해 시작)
```
cp docs/flow.example.json docs/flow.json      # 과제A 센서 알람 예시 (35,496 = 30,312 + 5,184)
python3 scripts/flowmap.py --check             # 스펙만 검증 (파일 생성 없음)
python3 scripts/flowmap.py                     # docs/flow.json → out/report.html
```
| 키 | 적는 것 | 숫자의 출처 |
|---|---|---|
| `title`, `as_of` | 과제 한 문장, 기준 시각 | README·TASK.md |
| `stages[]` | 단계 순서대로 `id`(영문 짧게)·`name`·`inputs[]`·`outputs[]`·`notes` | 입력·출력 파일명과 행 수는 `wc -l`·audit |
| `stages[].rules[]` | `name`(업무 문장)·`fired`(발동 건수, 정수)·`test`(tests.모듈.함수) | **`out/audit.json` 의 rule_counts·excluded_counts**, 테스트 이름은 `grep "def test_"` |
| `conservation` | `input` = `passed` + `excluded{사유: 건수}` 합 | audit.json 의 input/kept/excluded_counts. 안 맞으면 exit 1 + 띠에 `FAIL: 합계 불일치` |
| `decisions[]` | `where`(파일:줄)·`what`(무엇 / 왜 / 버린 대안) | `grep -rn "결정:" .` 결과 그대로 |
| `verification[]` | `name`·`status`(PASS/FAIL/NOT_RUN/HUMAN_CHECK)·`evidence`(명령·파일:줄) | unittest·check_contract·preflight 출력. 안 돌린 것은 NOT_RUN 으로 적는다 |
| `links[]` | `label`·`path`(프로젝트 루트 기준) | 출력 파일·DECISIONS.md·`docs/diagrams/`(있으면) |
숫자는 실행 결과에서 옮긴다. 암산·추정 숫자를 넣으면 보고서가 거짓이 된다. 발동 0건 규칙은 노란 행으로 표시되니 `scripts/make_edge_cases.py` 로 발동하는 입력을 만들어 재확인한다.

## 3. flowmap — 미리보기·검사
```
python3 design-kit/serve.py $PORT --dir out --index report.html     # 사람이 별도 터미널에서 실행(Codex 는 명령만 준다). 미리보기 탭에 포트 입력 → /report.html
python3 design-kit/ui_check.py out/report.html --tokens design-kit/tokens.css   # 구조·접근성·토큰·대비 FAIL 0 (URL 모드로 보면 "tokens.css linked" WARN 1건은 정상 — 토큰을 인라인한 설계)
```
report.html 은 CSS(design-kit 토큰 값을 rgb() 로 복사)까지 든 단독 파일이라 제출물에 그대로 들어가고 외부 자원이 없다. 640px 이하에서는 파이프라인이 세로로 바뀐다. 링크는 report.html 위치 기준 상대경로라 `out/` 에서 열어야 맞는다.

## 4. archify — 사전 체험(-15분)과 권장 시점
사전 체험에서 `node -v` 가 18 이상이면 `node .agents/skills/archify/bin/archify.mjs doctor` 를 한 번 돌린다(RUN.md -15 ⑧). 실패하면 이번 시험은 flowmap 만 쓰고 `archify` 스킬 폴더를 지운다(턴당 토큰 절약).
**사용 시점 제한은 없다.** 권장(강제 아님):
1. **10~30분** README·데이터 흐름을 dataflow 1장으로 그려 담당자에게 "제가 이해한 흐름이 맞나요"로 확인 — 질문 품질이 올라간다.
2. **63분 첫 완주 뒤** `--repo-root .` 로 architecture 1장 — 코드 근거(SRC 마커)가 붙는다.
3. **1차·최종 동결** 때 갱신 — README 데모 순서에 `docs/diagrams/` 링크(handoff-docs).
4. **서술형 준비(165분~)** sequence/lifecycle 로 "왜 이 구조인가"의 재료.
호출은 `$archify` 한 줄이면 되고 출력은 `docs/diagrams/`, 후보 파일은 `.archify/`(제출물 아님). 한 장에 1~2턴·30~60k 토큰이 들고 토큰은 채점 기록이므로, 같은 그림을 두 번 그리지 않고 동결 때 한 번 갱신한다.

## 5. 폴백과 역할 분리
Node 가 없거나 18 미만, doctor 실패, 시간이 없을 때는 **flowmap 만으로 충분**하다. 심사자가 묻는 "몇 건이 어디서 빠졌나·규칙이 발동했나·무엇을 검증했나"는 flowmap 이 답하고, archify 는 "구조가 왜 이런가"를 보탠다. 둘 다 있으면 README 데모 순서에 `out/report.html` 먼저, `docs/diagrams/` 다음으로 링크한다.
