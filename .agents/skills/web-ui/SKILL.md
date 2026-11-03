---
name: web-ui
description: 웹 화면을 처음 만들 때(`$web-ui 시안` → 사람 선택 → `초안`)와 CP2 freeze 뒤 그림·다듬기 때(`$web-ui 최종`) 쓴다. 시안·DESIGN_과제.md·초안 화면·ui_check 결과를 낸다.
---

# web-ui

목표: 사람이 고른 시안 1개로 디자인을 정하고 데이터가 보이는 화면을 템플릿으로 먼저 완성. 그림·다듬기는 CP2 freeze 뒤(그림 없어도 완성).
기록(시안·선택·매핑·그림 계획 표·WARN 사유·HUMAN_CHECK)은 `work/agents/B_web.md` ⑤(단일 세션은 DECISIONS 1·6).

## ① 시안 → 선택 (`$web-ui 시안` · `초안` 인데 DESIGN_과제.md 가 없을 때도)
1. 유형: `design-kit/REFERENCE.md` 5개 중 1개(와이어·순서·톤). 화면 요구는 PRD 4·5(빠진 것은 ⑦ `@사람`).
2. 후보: `python3 design-kit/refs/pick.py <유형> [키워드]` → 2~3개. `refs/INDEX.md` 만 읽고 후보 md 만 연다.
3. 시안(후보마다 1개, 틀 `illustrations/PROMPTS.md` 시안 절): 이미지 생성 도구가 있으면 1280×800 PNG `static/draft/sian_N.png`, 없으면 템플릿에 후보 토큰을 입힌 `static/draft/sian_N.html` + 헤드리스 캡처.
4. 보고 1줄씩 `시안 N · <md> · 분위기 3단어 · <미리보기 경로>` 후 멈춘다. 사람이 `시안 N 선택`(또는 `시안 생략` = 키트 기본 토큰) 할 때까지 기다린다. 그동안은 서버·API·매핑 표만.
5. 선택 뒤: `refs/_DESIGN_과제.template.md` → `design-kit/DESIGN_과제.md`(0절 출처·선택 시각, 2절 색).

## ② 템플릿 복사·매핑 (`$web-ui 초안`)
- 템플릿 1개 + tokens·base·components.css·`kit.js`·`icons.svg` → `static/`, `sed -i 's#\.\./##g' static/*.html`. `static/tokens.css` [브랜드]·[중립]을 DESIGN_과제.md 2절 값으로(hex 는 여기만) → contrast PASS(4.5:1).
- 매핑 표 `데이터 필드 | DOM 요소 | 표시 규칙(단위·정렬·상태색)`. `work/contract.md` 샘플로 더미 렌더 → CP2 에 실값.
- `K.load(url, 내장샘플)`·`K.setStatus`·`K.esc()`(모든 문자열)·`K.spark`/`K.hbar`. 빈·오류 화면은 `?state=fallback|failed`.
- 페이지 CSS 는 `var(--토큰)` 만(새 hex·반경·진입 애니메이션 없음). 복사 안 한 템플릿으로 가는 링크는 지운다.

## ③ 그림 자리(초안)
- 빈 박스 `<figure class="figure" data-ratio="16/9"><figcaption>어떤 그림: …</figcaption></figure>`(16/9·4/3·1/1·3/1), 캡션은 주제·구도·색 수까지.
- 그림 계획 표 `번호 | 위치 | 비율 | 주제 | 상태`(빈 박스·생성·키트·데이터·틴트).

## ④ 품질 바닥(기능이 돌면 바로)
- 접근성: h1 1개·제목 단계 순서 / 모든 input 에 label / 상태는 색 + 글자.
- 보안: 정적 경로 탈출 차단(정규화 후 prefix, 403) / `K.esc()` / 입력 길이·허용값 검증 후 400. 토큰은 `secrets.token_hex`.
- 서버: 깨진 JSON POST → 400, 본문 크기 제한, 내부 필드는 서버에서 제거. 띄운 뒤 `python3 scripts/smoke_web.py http://127.0.0.1:$PORT`.
- 동시 요청: 쓰기(생성·수정)는 한 번에 하나(잠금 또는 '처리 중' 409) + 테스트 1개(스레드 2개로 동시에 보내 중복·깨진 파일 0). 재시작 뒤 데이터가 남는지 1회.

## ⑤ ui_check·HUMAN_CHECK
- `python3 design-kit/ui_check.py http://127.0.0.1:$PORT/` 페이지마다 FAIL 0, WARN 은 사유를 기록에.
- HUMAN_CHECK: 사람이 데스크톱·390px 각 1회, DESIGN.md 4질문 → `HUMAN_CHECK PASS HH:MM`.
- 스크린샷: 헤드리스로 직접(DESIGN.md 캡처 절), 크롬이 없으면 `NOT_RUN`, 결과는 verify.json.

## ⑥ 최종(`$web-ui 최종`, CP2 freeze 뒤)
1. 그림 교체(계획 표 순서): 생성 도구가 있으면 `static/img/21-<영문>.png` → `.figure.is-final` 안 `<img alt>`(과제 전용 3장 이하, 문체 PROMPTS.md). 없으면 `design-kit/illustrations/` → 데이터 그림(`K.spark`·`K.hbar`) → 틴트 면 + `icons.svg`.
2. `python3 design-kit/ui_check.py --final http://127.0.0.1:$PORT/`: 그림 없는 `.figure` 가 남으면 FAIL.
3. 다듬기(필요할 때만): `references/hallmark-floor.md` → `references/impeccable-audit.md`. 위반 표 `심각도 P0~P3 | 좌표 | 무엇이 | 수정안`. 데이터·문구 사실·동작·API 는 그대로, ui_check 전후 숫자.
4. HUMAN_CHECK 1회 더, 그림 계획 표 상태 갱신.

## 보고 5줄
고른 시안·출처 md / 유형·템플릿·매핑 표 위치 / ui_check(PASS·WARN·FAIL 수) / HUMAN_CHECK / 남은 한계 1개. 꼬리 1줄은 AGENTS 7절.

## 금지
- 시안 선택 전 본 화면 작업. README 에 없는 화면·기능. 외부 폰트·CDN·npm·`http(s)://` 자원(로컬 `icons.svg`·`illustrations/` 는 허용).
- refs 의 로고·이름·폰트 파일·문구 복사, raw hex, 섹션마다 fade-up, 제목 위 대문자 라벨, 버튼 꼬리 "→", 내부 식별자 노출.
- KPI 4칸 공식·같은 카드 반복, 점 배지 남발, `.why` 설명줄, 광원·글래스.
- 출처: references = Hallmark(MIT)·Impeccable(Apache-2.0) 요약, `references/LICENSE.txt`.
