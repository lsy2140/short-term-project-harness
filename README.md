# short-term-project-harness

웹 IDE 에서 Codex 로 수행하는 **단기 과제(약 180분 구현 + 짧은 서술형 회고)용 작업 규약·검증 도구 템플릿**. 과제 폴더에 복사해 쓰는 모듈이며 연습용 파일(출제자 페르소나·채점기·프로필)·과제 정답·구현은 들어 있지 않다.

## 구성
```
AGENTS.md            Codex 작업 규약(역할·절대 규칙 10·순서·증거·환경·디버그 정책·도식화·위임·결정 대기함·문서·보고 꼬리 3줄)
TASK.md              과제 계약(한 문장·P0·사실/가정/열린 질문/안 할 일/완료 조건/평가/못 한 것) — 머리에 `시작: HH:MM`
DECISIONS.md         결정 기록(합의문·구조·데이터·믿지 않은 것·오류 수정·실패 지점·검증 로그·제출 상태)
PLAN.md              제출용 계획·보고(입출력·규칙·검증 숫자·데모 순서·실제 vs 목업·AI 활용·제한사항)
RUN.md               180분 운영표(대기 중 사람이 할 일 열 포함) · 문제 유형 분기 · 막힘 결정 트리 · 제출 체크
HANDOFF.md           다음 사람이 이어가기 위한 문서(동결 구간에 작성)
LICENSE · THIRD_PARTY_NOTICES.md · LICENSES/   자체 작성 부분 MIT · 포함된 외부 구성요소 고지 · Apache-2.0 전문
decisions/           결정 대기함: pending.md(Codex 가 쓴다 — 후보·추천·기본값·'안 정하면' 시각) · answers.md(사람이 쓴다 — `[x]` 또는 decide.py 폼)
.agents/skills/      Codex 스킬 14개(상한 15): exam-kickoff · stakeholder-interview · eda-first · task-breakdown · unit-test-starter
                     · debug-loop · evidence-gate · handoff-docs · narrative-prep · web-ui-build · ui-audit(화면 비평·수정)
                     · codebase-orientation · probe-judge · archify(외부 원문 축약본, Node ≥18, 출력 docs/diagrams/)
scripts/recon.py           낯선 환경 5초 파악(Python 버전·fromisoformat·도구·git·인코딩·주의할 점)
scripts/preflight.py       제출 직전 점검(환경·필수 파일·미완성 표시·비밀키·절대경로·compile·unittest·--smoke·--freeze/--check-freeze(1차 동결 복구본·tests 해시)·out/debug 파일 수) exit 0/1/2
scripts/check_contract.py  출력을 입력에서 재계산해 대조하는 독립 검사기(구조·대조·실행·메타모픽) exit 0/1/2
scripts/next.py            지금 구간·규칙 진행·다음 추천 3개·대기 중 할 일 — 보고 꼬리 3줄의 숫자 출처(AGENTS.md 7절)
scripts/decide.py          decisions/pending.md 를 브라우저 폼(0.0.0.0·PORT)으로 띄워 answers.md 에 기록
scripts/debug_dir.py       out/debug/NN_단계명 폴더 생성 + 파일 수 검사(폴더당 5파일, 전체 40파일; --check)
scripts/prompt.py          구간별 프롬프트 템플릿을 터미널에 출력(docs/prompt_examples.md, 토큰 0)
scripts/flowmap.py         docs/flow.json → out/report.html(파이프라인 도식·합계 보존 띠·규칙 발동 건수·결정 목록·검증 결과)
scripts/eda_bootstrap.py   CSV/JSON 첫 파악 요약 (Codex에는 이 요약만 읽힌다)
scripts/make_edge_cases.py 아무 CSV에서 경계·오염 변형 파일 생성
scripts/with_server.py     서버 띄우고 포트 대기 후 명령 실행·정리     scripts/smoke_web.py  웹 스모크(urllib)
scripts/llm_seam.py        모델 호출 경계(Stub/Codex CLI/HTTP + 캐시·폴백·참조 무결성) — 과제가 허용할 때만
scripts/guards.py          정규화·금지어·근거 대조·사유별 제외·타임아웃 폴백·마스킹
scripts/timer.py           경과·구간·구간 끝 3질문 + next.py 꼬리 3줄
tests/test_template.py     5분류 테스트 템플릿(정상·규칙·경계·명시적 거부·계약·제출 계약)
tests/test_guards.py       guards.py 규칙 테스트 21개(우회·과차단 방지·합계 보존·마스킹·타임아웃)
tests/test_{next,decide,debug_dir,prompt,ui_check,flowmap}.py   키트 스크립트 자체 테스트(리허설 1 반영분)
design-kit/                토큰·컴포넌트 CSS·스타일가이드·템플릿 4종(대시보드/콘솔/랜딩/모바일)·serve.py·ui_check.py·DESIGN.md
docs/                      stakeholder_interview · delegation_prompts · prompt_examples(25) · diagram_guide · flow.example.json · written_answer_prep · submission_checklist · judge_simulation · bash_cheatsheet
```

## 시험장에서 (사전 체험 15분 또는 시작 직후, 5분 이내)
```bash
git clone https://github.com/<계정>/short-term-project-harness.git
cd short-term-project-harness && python3 scripts/recon.py          # "주의할 점"을 TASK.md 1절(사실)에 복사
cd ../<과제폴더>                                             # 과제 폴더가 따로면
cp ../short-term-project-harness/{AGENTS.md,TASK.md,DECISIONS.md,PLAN.md,RUN.md,HANDOFF.md} .
cp -r ../short-term-project-harness/{.agents,scripts,tests,docs,design-kit,decisions} .
rm -rf ../short-term-project-harness                                 # 제출물에 섞이지 않게 (또는 과제 폴더 밖에 둔다)
node -v && node .agents/skills/archify/bin/archify.mjs doctor # 사전 체험: Node ≥18 이고 doctor OK 면 $archify 사용 가능. 실패하면 rm -r .agents/skills/archify (도식은 scripts/flowmap.py 만)
ls -a && codex                                                # /status /model 로 Sol 6.1·승인 모드 확인 · 스킬 14개 표시 확인
```
과제 유형이 정해지면(0~10분) 안 쓸 스킬 폴더를 지운다(RUN.md 원칙 5, 턴당 토큰 절약): 웹 없음 → `web-ui-build`·`ui-audit`, 기존 코드 없음 → `codebase-orientation`, Node 없음 → `archify`.

`git clone`이 막히면 **Plan C**: GitHub 웹에서 AGENTS.md → TASK.md → DECISIONS.md 순으로 복사·붙여넣기(이 3개면 절반). 나머지는 Codex에게 "AGENTS.md 3절 규칙대로 preflight.py를 만들어줘".

첫 프롬프트(docs/delegation_prompts.md 0번과 같은 문장):
```
AGENTS.md를 읽고 이 세션의 규약으로 써. 코드는 아직 쓰지 마.
TASK.md 머리에 `시작: HH:MM` 을 적고, 타이머 명령(python3 scripts/timer.py --start HH:MM --loop 300)을 첫 보고에 그대로 출력해.
README와 파일 목록, 데이터 형식, 제출물 형식을 읽고 TASK.md의 한 문장·P0·1~5번을 채워 보여줘.
업무 담당자에게 물어볼 질문 5~8개를 docs/stakeholder_interview.md 순서로 만들어. 번호를 붙이고 한 번호에 한 주제, 질문마다 괄호로 왜 묻는지 한 줄. 끝에 사용 가능한 스킬 이름을 한 줄로 덧붙여.
보고는 꼬리 3줄(지금 / 다음 추천 / 대기 중 할 일)로 끝내.
```

## 검증 명령 (변경 전후 같은 명령)
```bash
python3 -m unittest -v                                   # 규칙 1개 = 테스트 1개
python3 scripts/check_contract.py                        # 출력↔입력 독립 대조 (exit 2는 통과 아님)
python3 scripts/preflight.py --require out/<결과> README.md PLAN.md --smoke "python3 <진입점> ..."
python3 scripts/next.py                                  # 지금 구간·다음 추천 3개·대기 중 할 일 (보고 꼬리 3줄과 같은 숫자)
python3 scripts/debug_dir.py --check                     # out/debug 단계 폴더당 ≤5파일, 전체 ≤40파일, 스냅샷 폴더 없음
python3 scripts/with_server.py --server "PORT=8000 python3 app.py" --port 8000 -- python3 scripts/smoke_web.py http://127.0.0.1:8000
```

## 원칙 한 줄
적는다(TASK/DECISIONS) → 먼저 FAIL을 본다 → 작게 시키고 직접 확인하고 기록한다 → 내 말로 설명할 수 있는 것만 남긴다.

## 라이선스
직접 작성한 부분은 [MIT](LICENSE)다. 포함된 외부 구성요소(Archify, theme-factory 테마, `scripts/with_server.py`, Hallmark·Impeccable 번역 요약)는 각자의 라이선스(Apache-2.0 또는 MIT)를 따르며 목록과 출처는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있다.

