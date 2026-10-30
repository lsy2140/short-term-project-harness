# 보고서·도식화 사용법 — 두 터미널 운영, flowmap 보고서 작성 지침, archify

코드와 숫자만 보고는 "맞게 돌고 있나"를 사람도 심사자도 판단하기 어렵다. 보고서는 **메인 세션이 아니라 두 번째 세션**이 만든다. 메인 세션은 단계마다 흔적(verify.json)만 남기고 다음 단계로 간다.

| | 메인 세션(해결자) | 보고서 세션(`$stage-report`) | `$archify` |
|---|---|---|---|
| 무엇 | 구현·테스트·디버그 폴더 기록 | 끝난 단계 묶음의 검증 보고서 `out/report/stage_NN-MM.html` + `index.html`, 동결 구간의 최종 구현 종합정리 `implementation_summary.md` | 구조도 `docs/diagrams/*.html` |
| 쓰는 곳 | 코드·tests·docs·TASK/PLAN/DECISIONS·out/debug | **`out/report/` 만** | `docs/diagrams/`·`.archify/` |
| 입력 | README·담당자 답·데이터 | `out/debug/NN_*/verify.json`·green.txt·PLAN 4번·DECISIONS·코드 위치(grep) | 저장소(`--repo-root .`) |
| 비용 | — | 묶음당 1~2턴(읽기 + flowmap). 테스트·서버 실행 없음 | 1장당 1~2턴·30~60k 토큰 |

## 0. 두 터미널 운영 (사람이 하는 것)
```
터미널 1  메인:   codex  →  "1~3단계 진행해" … "4~6단계 진행해"
터미널 2  보고서: codex  →  "$stage-report 1-3"  (메인이 4~6을 하는 동안)  →  out/report/stage_01-03.html 을 미리보기로 검증
터미널 3  미리보기 서버(사람): python3 design-kit/serve.py $PORT --dir out/report --index index.html
```
- 두 세션은 **같은 과제 폴더**에서 연다. 보고서 세션은 `out/report/` 외에는 쓰지 않으므로 메인 세션과 파일이 겹치지 않는다.
- 보고서 세션에도 AGENTS.md 가 읽히므로 규칙(포트 안 열기, 숫자 암산 금지)은 같다. 첫 프롬프트는 `docs/delegation_prompts.md` 9번(또는 `python3 scripts/prompt.py 26`).
- 사람은 보고서를 보며 "숫자가 맞나, 규칙이 발동했나, 샘플이 그럴듯한가"를 확인하고, 틀린 것은 **메인 세션**에 `요구사항 갱신:` 또는 `$debug-loop` 로 넘긴다. 보고서 세션에 코드를 고치게 하지 않는다.
- 묶음 크기는 사람이 정한다(보통 2~3단계). 1차 동결(110분)과 최종 동결(144~165분)에는 `$stage-report all` 로 전체 보고서를 만들어 README 데모 순서에 `out/report/index.html` 을 링크한다.

## 1. 메인 세션이 단계마다 남길 것 (보고서의 재료)
`python3 scripts/debug_dir.py NN_단계명` 폴더의 **`verify.json`** 에 아래 키를 채운다(없는 키는 생략, 숫자는 실행 결과에서). `green.txt`(PASS 출력)·`red.txt`(먼저 본 FAIL)·`note.md`(결정이 필요했던 것)·`decisions.txt`(`# 결정:` grep)는 기존 규칙대로.
```json
{"stage": "02_규칙_tz", "what": "라인 B 시각 UTC→KST", "status": "PASS",
 "files": ["run.py:67-98 normalize_timestamp()"],
 "method": ["Z/오프셋은 그대로 변환", "naive B 는 +9h(가정 run.py:93)"],
 "inputs": {"sensor_log.csv": 35496}, "outputs": {"정규화 행": 30312},
 "counts": {"Z 변환": 10800, "mTorr→Torr": 2665, "파싱 실패": 0},
 "before_after": {"알람 건수": [15, 17]},
 "samples": [["2026-10-26T17:00:00Z", "2026-10-27 02:00 KST"]],
 "tests": [{"name": "tests.test_tz.test_z_converts_once", "status": "PASS"}],
 "notes": "담당자 확인 NOT_RUN: B 라인 원천 시간대"}
```
이 파일 하나면 보고서 세션이 코드를 깊이 읽지 않아도 된다. 비어 있으면 보고서 세션이 green.txt·PLAN·코드 grep 으로 메우되, 못 메운 항목은 "근거 없음"으로 남는다.

## 2. 보고서 세션 시작법
```
cd <과제 폴더> && codex                      # 메인과 같은 폴더, 다른 터미널
$stage-report 1-3                            # 또는: "1~3단계 보고서 만들어. out/report/ 밖은 건드리지 마."
```
결과: `out/report/stage_01-03.json`(스펙) + `stage_01-03.html` + `index.html`. 같은 묶음을 다시 요청하면 덮어쓴다. 전체는 `$stage-report all` → `stage_all.html`.

## 3. 보고서 작성 지침 (flowmap 스펙을 채우는 규칙)
**읽는 순서 = 쓰는 순서.** 결론 먼저, 한 화면에 상태, 그다음 단계별 상세.
1. **`summary` 3줄**: ① 무엇이 됐나(입력 N → 출력 M, 핵심 숫자) ② 숫자가 맞나(합계 보존·테스트 PASS 수) ③ 남은 위험 1개(가정·NOT_RUN). 이 3줄만 읽어도 결론이 나와야 한다.
2. **단계 스트립**(자동): 단계마다 `status` 와 `results[0]` 이 카드로 뜬다. 그래서 `results[0]` 은 그 단계를 대표하는 숫자 1개로 둔다.
3. **단계별 상세** 순서: `role`(이 단계가 하는 일 1줄, 업무 말로) → `implemented[]`(파일:줄·함수·무엇 — 심사자가 바로 열 수 있게) → `method[]`(3~6줄, "~를 읽어 ~하면 ~로 분류한다"처럼 순서대로, 전문 용어 없이) → `results[]`(숫자 + `note` 에 출처 파일) → `charts[]` → `samples[]`(입력 1행 → 출력 1행, 2~3개; 규칙이 걸린 실제 예) → `tests[]`(이름·상태·근거) → `decisions`(`stage` 로 묶임).
4. **차트 선택표** — "무엇을 보여 주고 싶나"로 고른다. 전부 값 라벨이 붙고 아래에 데이터 표가 접혀 있다.

| 보여 줄 것 | type | 예 |
|---|---|---|
| 사유별·범주별 건수(순위) | `hbar` (범주 12개 넘으면 bar 도 자동 hbar) | 제외 사유별 행 수, 규칙별 발동 건수 |
| 적은 범주의 크기 비교 | `bar` | 라인별 알람 건수 |
| 규칙·변경 **전과 후** | `compare` | 규칙 끔/켬 알람 건수, 수정 전/후 테스트 수 |
| 전체가 어떤 조각으로 이루어졌나 | `stacked` | 라인별 시각 형식 구성, 설비별 제외 사유 구성 |
| 값의 **분포** | `hist`(구간은 미리 세어 `label`·`value` 로) | severity 분포, 구간 길이 분포 |
| **시간**·순서에 따른 변화 | `line`(`series[].points[{x,y}]`, 점 12개 이하면 값 표시) | 시간대별 건수, 단계별 누적 테스트 수 |
| 단계·항목 × 상태 **격자** | `matrix`(셀 `status` 로 색) | 단계 × 검증 방법, 규칙 × 데이터셋 |
5. **숫자 출처 규칙**: 모든 숫자는 `verify.json`·`out/audit.json`·green.txt·`wc -l` 에서 옮기고 `note`/`evidence` 에 파일을 적는다. 합계 보존(`conservation`)은 입력 = 통과 + 제외 합이 맞아야 하며, 안 맞으면 flowmap 이 exit 1 — 숫자를 맞추려 고치지 말고 **근거를 다시 센다**.
6. **금지**: 추정·암산 숫자, 범주 10개 넘는 차트(상위 9 + 기타로 묶는다), 값 라벨 없는 그림, 파이 차트·3D, 한 단계에 차트 3개 초과, 전역 차트 4개 초과, 단계 `status` 를 테스트 근거 없이 PASS 로 쓰기(테스트가 없으면 `NOT_RUN`, 사람 눈 확인은 `HUMAN_CHECK`).
7. **한눈 기준**(사람 체크): 첫 화면에 summary 3줄 + KPI + 단계 스트립이 보이나 / 단계 카드 하나가 한 화면에 들어오나 / 차트 제목만 읽어도 무슨 숫자인지 아나 / 샘플 행이 규칙이 걸린 실제 예인가.

## 4. 스펙 키 (v1 + v2, 전부 `docs/flow.example.json` 에 예가 있다)
| 키 | 적는 것 | 출처 |
|---|---|---|
| `title`, `as_of`, `summary[]`(1~3줄), `stage_range`(--stages 가 자동으로 붙임) | 제목·기준·결론 | TASK.md·README |
| `stages[]`: `id`·`name`·`status`·`role`·`inputs[]`·`outputs[]`·`notes` | 단계 뼈대 | PLAN.md 4번·verify.json |
| `stages[].implemented[]`: `file`·`lines`·`symbol`·`what` | 구현 위치 | `grep -n "def "`·verify.json files |
| `stages[].method[]` | 방법 3~6줄 | 코드 `sed -n`·verify.json method |
| `stages[].rules[]`: `name`·`fired`·`test` | 규칙 1개 = 테스트 1개 + 발동 건수 | audit.json rule_counts·PLAN 4번 |
| `stages[].results[]`: `label`·`value`·`unit`·`note` | 결과 숫자(첫 항목이 대표) | verify.json counts/outputs |
| `stages[].charts[]`, `charts[]` | 4절 선택표 | verify.json counts·before_after |
| `stages[].samples[]`: `before`·`after`·`note` | 입력→출력 실제 예 2~3행 | verify.json samples·`head` |
| `stages[].tests[]`: `name`·`status`·`evidence` | 테스트와 결과 | green.txt·red.txt |
| `conservation`: `input`·`passed`·`excluded{사유: 건수}` | 합계 보존 | audit.json |
| `decisions[]`: `stage`·`where`·`what` / `verification[]` / `links[]` | 결정·검증·링크 | decisions.txt·DECISIONS.md |

## 5. 명령·검사
```
python3 scripts/flowmap.py --spec out/report/stage_01-03.json --out out/report/stage_01-03.html   # 생성 (exit 0)
python3 scripts/flowmap.py --spec docs/flow.json --stages 1-3 --out out/report/stage_01-03.html    # 전체 스펙에서 1~3단계만
python3 scripts/flowmap.py --index out/report                                                     # index.html
python3 scripts/flowmap.py --check --spec out/report/stage_01-03.json                             # 스펙만 검증
python3 design-kit/ui_check.py out/report/stage_01-03.html --tokens design-kit/tokens.css          # FAIL 0 (URL 모드의 "tokens.css linked" WARN 1건은 정상)
python3 design-kit/serve.py $PORT --dir out/report --index index.html                             # 사람이 별도 터미널에서(Codex 는 명령만 준다)
```
보고서는 CSS(design-kit 토큰 값을 rgb() 로 복사)까지 든 단독 파일이라 제출물에 그대로 들어가고 외부 자원이 없다. 640px 이하에서는 파이프라인이 세로, 차트가 1열로 바뀐다. 링크는 보고서 위치 기준 상대경로라 `out/report/` 에서 열어야 맞는다.

## 6. archify — 구조도 (선택)
사전 체험에서 `node -v` 가 18 이상이면 `node .agents/skills/archify/bin/archify.mjs doctor` 를 한 번 돌린다(RUN.md -15 ⑧). 실패하면 `archify` 스킬 폴더를 지운다. **사용 시점 제한은 없다.** 권장: 10~30분 dataflow 1장으로 담당자와 흐름 확인 → 63분 첫 완주 뒤 `--repo-root .` architecture → 동결 때 갱신 → 서술형 준비에 sequence/lifecycle. 출력 `docs/diagrams/`, 후보 `.archify/`(제출물 아님). 보고서 세션에서 돌려도 된다(쓰는 곳이 `docs/diagrams/` 라 메인과 겹치지 않음).

## 7. 폴백과 역할 분리
보고서 세션을 열 여유가 없으면 메인 세션에 "여기서 `$stage-report 1-3` 해" 라고 명시해 같은 세션에서 만든다(시간이 든다는 것만 안다). Node 가 없으면 archify 없이 flowmap 만으로 충분하다. 심사자가 묻는 "몇 건이 어디서 빠졌나·규칙이 발동했나·무엇을 검증했나"는 보고서가 답하고, archify 는 "구조가 왜 이런가"를 보탠다. README 데모 순서에는 `out/report/index.html` 먼저, `docs/diagrams/` 다음으로 링크한다.
