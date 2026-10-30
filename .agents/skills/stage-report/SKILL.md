---
name: stage-report
description: 두 번째(보고서 전용) Codex 세션에서 끝난 단계 묶음의 검증 보고서 HTML 을 만들 때 사용. out/debug 단계 폴더·PLAN·DECISIONS·코드 위치를 읽어 docs/flow.example.json 모양의 스펙을 쓰고 scripts/flowmap.py 로 out/report/stage_NN-MM.html(요약·단계 스트립·차트·구현 위치·방법·결과 숫자·샘플·테스트)을 만든다. "1-3단계 보고서 만들어", "보고서 세션", "검증 html", "단계 보고서", "그래프로 보여줘", "한눈에 보게", "report 갱신", "stage report"라는 요청에 사용한다. 메인 세션의 파일은 건드리지 않는다.
---

# stage-report

목표: 메인 세션이 4~6단계를 하는 동안, 끝난 1~3단계를 **사람이 코드를 열지 않고 검증**할 수 있는 보고서를 만든다. 쓰는 곳은 `out/report/` 뿐이다.

## 이 세션의 범위 (메인 세션과 충돌 금지)
- 수정 허용: `out/report/**` 만. 코드·`tests/`·`docs/`·TASK/PLAN/DECISIONS·`decisions/`·`out/debug/` 는 **읽기만**.
- 실행 허용: 읽기 명령(`head`·`wc -l`·`grep`·`sed -n`·`python3 -c` 로 집계)과 `python3 scripts/flowmap.py`. **테스트·앱·서버 실행 금지**(메인 세션이 쓰는 out/ 과 충돌, 포트는 AGENTS 1절 11).
- 숫자는 근거 파일에서만 옮긴다. 근거가 없으면 값을 만들지 말고 `results[].note` 에 "근거 없음", 상태는 `NOT_RUN`.

## 절차
1. **범위**: "1-3" 은 PLAN.md 4번 표의 단계 번호 = `out/debug/NN_단계명/` 의 NN. 해당 폴더가 없으면 그 단계는 `NOT_RUN` 으로 두고 보고에 적는다.
2. **근거 수집(읽기)**: 단계마다 `out/debug/NN_*/verify.json`(숫자·테스트·파일 위치) → `green.txt`/`red.txt`(테스트 이름·결과) → `note.md`·`decisions.txt`(결정) → PLAN.md 4번 규칙표(규칙·발동 건수·상태) → DECISIONS.md 1·4·6번. 코드는 `grep -n "def \|# 결정:" <파일>` 과 `sed -n a,bp` 로 **구현 위치(파일:줄·함수)와 방법만** 읽는다(파일 통째 금지). 출력 파일은 `head -3`·`wc -l`.
3. **스펙 작성** `out/report/stage_NN-MM.json` — `docs/flow.example.json` 과 같은 모양(`docs/diagram_guide.md` 3절 지침). 단계마다 `role` 1줄 → `implemented[]`(파일:줄·함수·무엇) → `method[]` 3~6줄(순서대로, 전문 용어 없이) → `results[]`(숫자 + note 에 출처) → `charts[]`(지침의 차트 선택표: 사유별 건수 hbar · 전/후 compare · 분포 hist · 시간 흐름 line · 단계×검증 matrix · 구성 stacked) → `samples[]` 2~3행(입력→출력) → `tests[]` → `status`. 전역 `summary` 3줄은 결론 먼저(무엇이 됐나 / 숫자가 맞나 / 남은 위험). `decisions[].stage` 로 단계에 붙인다. 범위 밖 단계는 넣지 않는다.
4. **생성**: `python3 scripts/flowmap.py --spec out/report/stage_NN-MM.json --out out/report/stage_NN-MM.html` → exit 0 확인(합계 불일치면 근거를 다시 읽어 스펙을 고친다. 숫자를 맞추려고 바꾸지 않는다) → `python3 scripts/flowmap.py --index out/report`.
5. **보고 5줄**: 파일 경로 / 단계별 상태 한 줄 / 핵심 숫자 3개(출처) / 근거 없음·NOT_RUN 목록 / 미리보기 명령 `python3 design-kit/serve.py $PORT --dir out/report --index index.html`(사람이 다른 터미널에서 실행 — 직접 띄우지 않는다).

## 금지
- 메인 세션 파일 수정, 테스트·서버 실행, 추정 숫자, 범주 10개 넘는 차트, 값 라벨 없는 차트, 같은 보고서를 요청 없이 다시 만들기.
