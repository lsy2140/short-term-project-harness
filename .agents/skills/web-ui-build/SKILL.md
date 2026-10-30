---
name: web-ui-build
description: 웹 화면(대시보드·운영자 콘솔·조회 도구·랜딩·모바일 앱형 화면)을 만들 때 사용. design-kit 의 토큰·템플릿을 복사해 변수만 쓰고, data→DOM 매핑 표·품질 바닥(접근성 3·보안 3)·ui_check PASS·HUMAN_CHECK(데스크톱·390px) 순으로 완주한다. "화면 만들어", "대시보드", "운영자 콘솔", "웹페이지", "모바일 화면", "UI", "프론트", "HTML 페이지", "미리보기에 띄워", "디자인 다듬어"라는 요청에 사용한다. 외부 폰트·CDN·npm 금지.
---

# web-ui-build

목표: 30분 안에 "데이터가 보이는 화면"을 템플릿으로 완주하고, 다듬기는 토큰 안에서만 한다. 외부 요청 0(폰트·CDN·npm 금지), 순수 HTML/CSS/JS + Python http.server.

## 절차
1. **읽기** `design-kit/DESIGN.md` 를 읽는다(절차·어휘표·피할 것·현장 관례). 과제 README 가 화면 요구를 적었으면 그 문장을 TASK.md 1번에 원문으로 옮긴다.
2. **참고 제품 2개는 사람이 지정** — "Stripe 대시보드식 + Linear 표" 처럼. 브랜드명만 받지 말고 DESIGN.md 어휘표의 토큰 수준 서술(밀도·반경·선·강조색)로 바꿔 확인받는다.
3. **토큰 계획 → 승인 → 구현**: 색 4~6개(tokens.css 이름으로) / 서체(시스템 스택 고정) / 레이아웃 ASCII 와이어프레임 1개 / 원칙 3줄. 디폴트 티(DESIGN.md 피할 것)와 겹치면 고친 뒤 승인받고, 승인 전에는 HTML 을 쓰지 않는다.
4. **템플릿 복사 + data→DOM 매핑 표**: `design-kit/templates/{dashboard,console,landing,mobile}.html` 중 가장 가까운 것과 CSS 3파일을 과제 폴더로 복사. `data.json` 자리에 과제 API/파일을 넣고 `데이터 필드 → DOM 요소 → 표시 규칙(단위·정렬·상태색)` 표를 DECISIONS.md 1번에 적는다. 페이지 CSS 는 `var(--토큰)` 만, 새 hex·새 반경·외부 URL 금지, 진입 애니메이션 없음(hover·active 만). 템플릿 상단의 다른 템플릿 내비 링크(dashboard/console/landing/mobile)는 지운다(복사하지 않은 페이지는 404).
5. **품질 바닥**(기능이 돌면 바로):
   - 접근성 3: h1 1개 + 제목 단계 순서 / 모든 input 에 label / 상태는 색 + 글자(배지 텍스트).
   - 보안 3: 정적 파일은 지정 폴더 밖 경로 탈출 차단(`..` 정규화 후 prefix 검사, 403/404) / 모든 데이터 문자열은 `esc()` 로 HTML 이스케이프 / 입력은 길이·허용값 검증 후 400 명시 거부. ID·토큰이 필요하면 `secrets.token_hex`, 예측 가능한 난수 금지.
   - 서버는 `0.0.0.0` + `PORT` 환경변수, 잘못된 JSON POST → 400. 서버는 직접 띄우지 말고 실행 명령을 사람에게 준다(AGENTS 1절 11). 띄웠다는 답을 받으면 `scripts/smoke_web.py` 로 확인.
6. **ui_check PASS**: `python3 design-kit/ui_check.py http://127.0.0.1:$PORT/` (페이지마다). FAIL 0 이 될 때까지 고친다. WARN 은 사유를 DECISIONS.md 에 적는다.
7. **HUMAN_CHECK**: 사람이 미리보기에서 데스크톱 1회·창 폭 390px 1회. DESIGN.md 의 4질문(폴드 안 핵심 1개 / 제목 3단 구분 / 상태색+글자 / 가로 스크롤 없음)에 답하고 DECISIONS.md 에 `HUMAN_CHECK PASS(시각)` 로 기록. 가로 스크롤이 있으면 `minmax(0,…)`·`overflow-x:auto` 로 고친다.
8. **스크린샷·기록**: 헤드리스 크롬이 있으면 DESIGN.md 의 조건부 명령으로 `screenshots/desktop.png`, `screenshots/mobile.png` 저장(없으면 NOT_RUN 기록). 디버그 폴더 verify.json 에 ui_check·HUMAN_CHECK 결과를 적는다.

## 보고 형식 (5줄)
템플릿 / 매핑 표 위치 / ui_check 결과(PASS·WARN·FAIL 수) / HUMAN_CHECK 결과 / 남은 한계 1개.

## 금지
- README 에 없는 화면·기능 추가, 라이브러리·폰트·아이콘 CDN 설치, raw hex, 섹션마다 fade-up, 모든 제목 위 대문자 라벨, 버튼 꼬리 "→", 내부 식별자(section-type 등)를 화면 문구로 노출.
- 참고: `references/themes/*.md` 는 공개 theme-factory 팔레트 10개(Apache-2.0, `references/LICENSE.txt`). 브랜드 전환 시 색 후보로만 쓰고 대비 4.5:1 을 ui_check 로 확인한다.
- 완성된 화면의 비평·수정(AI 티 제거·접근성 점검·다듬기)은 `$ui-audit`(`.agents/skills/ui-audit/references/hallmark-floor.md`·`impeccable-audit.md`)으로 넘긴다 — 이 스킬은 만들기까지.
