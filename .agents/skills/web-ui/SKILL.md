---
name: web-ui
description: 웹 화면을 처음 만들 때(`$web-ui 시안` → 사람 선택 → `초안`)와 CP2 freeze 뒤 그림·다듬기 때(`$web-ui 최종`) 쓴다. 시안 5개·DESIGN_과제.md·초안 화면·ui_check 결과를 낸다.
---

# web-ui

목표: 고른 시안 1개(색 md·배치·그림 자리)로 데이터가 보이는 화면을 먼저 완성, 그림·다듬기는 CP2 freeze 뒤.
기록은 `work/agents/B_web.md` ⑤(단일 세션은 DECISIONS 1·6), 그림 계획 표는 DESIGN_과제.md 9절.

## ① 시안 5개 → 선택 (`$web-ui 시안` · `초안` 인데 DESIGN_과제.md 가 없을 때도)
1. 유형: `design-kit/REFERENCE.md` 5개 중 1개(필수 블록·순서의 출발점). 필수 블록 = PRD 4·5 화면 요구.
2. 후보: `python3 design-kit/refs/pick.py <유형> [키워드]` → md 5개(INDEX.md 만 읽고 후보만 연다).
3. 시안 N(1~5) = md N + 배치 N(PROMPTS.md 5종, 서로 다르게) + 그림 자리 1~2(일러스트가 그려진 상태). 필수 블록은 5개 모두에, 배치·그림·강조는 다르게. 1280×800 PNG `static/draft/sian_N.png`(생성 도구), 없으면 토큰+배치 CSS 를 입힌 `sian_N.html` 캡처.
4. 보고 1줄씩 `시안 N · <md> · 배치 <이름> · 분위기 3단어 · 그림 자리 <위치> · <경로>` 후 멈춘다. 사람의 `시안 N 선택`(바꿀 점 `색/배치/그림은 시안 M 것` · `시안 생략` = 키트 기본)까지 서버·API·매핑 표만.
5. 선택 뒤 `refs/_DESIGN_과제.template.md` → `design-kit/DESIGN_과제.md`(0 출처·시각, 1-1 배치, 2 색, 9 그림 계획). 고른 시안만 `static/draft/` 에, 나머지 4장은 `.tmp/draft/`.

## ② 템플릿 복사·매핑 (`$web-ui 초안`)
- 템플릿 1개 + tokens·base·components.css·`kit.js`·`icons.svg` → `static/`(`../` 삭제). `static/tokens.css` [브랜드]·[중립] = DESIGN_과제.md 2절(hex 는 여기만) → contrast PASS.
- 배치는 고른 시안(1-1 표)을 따른다: 순서·span·split 비율·사이드 패널·카드화·그림 자리 자유. 지키는 것 = 토큰 변수만·상태색 5쌍·배너 3종·필수 블록·접근성·DESIGN.md 4절.
- 매핑 표 `데이터 필드 | DOM 요소 | 표시 규칙(단위·정렬·상태색)`. `work/contract.md` 샘플로 더미 렌더 → CP2 에 실값.
- `K.load(url, 내장샘플)`·`K.setStatus`·`K.esc()`(모든 문자열)·`K.spark`/`K.hbar`. 빈·오류 화면 `?state=fallback|failed`. 페이지 CSS 는 `var(--토큰)` 만.

## ③ 그림 자리(초안)
- 9절 표 자리마다 `<figure class="figure" data-ratio="16/9"><figcaption>어떤 그림: …</figcaption></figure>`(비율 21/9·16/9·4/3·1/1·3/1), 캡션은 주제·구도·색 수.
- 연결 신호 대기 중에 ⑥-1 그림을 미리 만들어 `static/img/` 에 두어도 된다(교체는 freeze 뒤).

## ④ 품질 바닥(기능이 돌면 바로)
- 접근성: h1 1개·제목 순서 / input 마다 label / 상태는 색+글자.
- 보안: 정적 경로 탈출 403 / `K.esc()` / 길이·허용값·깨진 JSON 400 / 본문 크기 제한 / 내부 필드 제거 / 토큰 `secrets.token_hex`. 띄운 뒤 `python3 scripts/smoke_web.py <URL>`.
- 동시 요청: 쓰기는 한 번에 하나(잠금 또는 409) + 스레드 2개 동시 테스트 1개. 재시작 뒤 데이터 유지 1회.

## ⑤ ui_check·스크린샷·HUMAN_CHECK
- `python3 design-kit/ui_check.py <URL>` 페이지마다 FAIL 0, WARN 은 사유 기록.
- 스크린샷 3장 `screenshots/desktop(1280)·tablet(834)·mobile(390).png` 헤드리스(DESIGN.md 캡처 절), 크롬 없으면 `NOT_RUN`. 가로 스크롤·겹침·빈 박스 확인 → verify.json.
- HUMAN_CHECK: 사람이 1280·834·390 각 1회 → `HUMAN_CHECK PASS HH:MM (1280·834·390)`.

## ⑥ 최종(`$web-ui 최종`, CP2 freeze 뒤)
1. 그림 교체(9절 표 순서, 5장 이하): 생성 도구가 있으면 `static/img/21-<영문>.png`(PROMPTS.md 과제 전용 틀, 색 2절 `--brand`·`--brand-soft`, 긴 변 1024·500KB·합계 3MB) → `.figure.is-final` 안 `<img alt>`. 없으면 `illustrations/` → 데이터 그림 → 틴트 면 + `icons.svg`.
2. `python3 design-kit/ui_check.py --final <URL>`: 그림 없는 `.figure` 가 남으면 FAIL.
3. 다듬기: `references/hallmark-floor.md`·`impeccable-audit.md`, 위반 표 `P0~P3 | 좌표 | 무엇이 | 수정안`. 데이터·동작·API 는 그대로.
4. 스크린샷·HUMAN_CHECK 다시, 9절 표 갱신.

## 보고 5줄
고른 시안·md·배치 / 템플릿·매핑 표 위치 / ui_check 수·스크린샷 3장 / HUMAN_CHECK / 한계 1개. 꼬리 1줄은 AGENTS 7절.

## 금지
- 시안 선택 전 본 화면 작업. 시안 5개가 색만 다르고 배치가 같은 것. README 에 없는 화면·기능. 외부 폰트·CDN·npm·`http(s)://` 자원(로컬 `icons.svg`·`illustrations/` 허용).
- refs 의 로고·이름·폰트·문구 복사, raw hex, fade-up, 대문자 라벨, 버튼 꼬리 "→", 내부 식별자, KPI 4칸 공식·같은 카드 반복, 점 배지 남발, `.why`, 광원·글래스.
- 출처: references/ = Hallmark(MIT)·Impeccable(Apache-2.0) 요약(`LICENSE.txt`).
