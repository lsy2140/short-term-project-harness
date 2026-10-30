---
name: ui-audit
description: 이미 만들어 돌아가는 웹 화면(대시보드·운영자 콘솔·모바일 폼·랜딩)을 비평하고 design-kit 토큰 안에서 다듬을 때 사용. web-ui-build 로 만든 뒤 쓴다. Hallmark "The Floor" 16규칙(references/hallmark-floor.md)과 Impeccable 점검 순서·비평 형식·엣지 체크(references/impeccable-audit.md) 요약으로 위반을 심각도순 표(좌표·수정안)로 내고 ui_check 를 재실행한다. "디자인 점검", "AI 티", "화면 비평", "더 좋게", "다듬어", "접근성 점검", "보기 좋게", "촌스러", "어색해", "세련되게", "UI 리뷰", "화면 검수"라는 요청에 사용한다. 새 색·폰트·외부 URL·진입 애니메이션·기능 추가 금지.
---

# ui-audit

목표: 돌아가는 화면을 **기능·문구 사실을 바꾸지 않고** 운영 화면답게 다듬는다. 만들기는 `web-ui-build`, 여기는 비평·수정. 원칙은 "Operate 모드는 절제가 야심"(`references/impeccable-audit.md` 0절): 운영 화면은 표·숫자·상태가 주인공이고 장식은 뺀다.

## 절차
1. **렌더 확인**: 사람이 서버를 띄워 두었으면(직접 띄우지 않는다 — AGENTS 1절 11) 헤드리스 크롬(`design-kit/DESIGN.md` 7절 명령)으로 1280·390 캡처. 크롬이 없으면 `NOT_RUN` 으로 적고 사람의 HUMAN_CHECK(DESIGN.md 6절 4질문)를 1단계 증거로 쓴다.
2. **Floor 16 체크**: `references/hallmark-floor.md` 1절 표의 '우리 키트에서' 열대로 — ui_check 가 잡는 항목은 `python3 design-kit/ui_check.py <URL|파일>` 출력을 그대로 인용하고, 사람이 보는 항목은 캡처·HUMAN_CHECK 로 답한다. 2절 Reflex 12 는 해당하는 것만.
3. **Impeccable 순서 점검**: `references/impeccable-audit.md` 2절 — 위계 → 간격 → 상태 → 문구 → 반응형. 단계마다 1~3줄, 발견이 없으면 '없음'. 4절 harden 으로 빈·오류·긴 문자열·느린 상태를 한 번씩 만들어 본다.
4. **위반 표**: 심각도순 `P0 작업 불가 / P1 접근성·가독(WCAG AA) / P2 불편 / P3 다듬기`, 열은 `심각도 | 좌표(파일:줄 또는 CSS 선택자) | 무엇이 | 수정안(토큰·클래스 이름으로)`. P3 는 5개 이하.
5. **수정**: `var(--토큰)`·키트 클래스(`.card/.badge/.btn/.table-wrap/.empty/.skeleton`) 안에서만. 데이터·문구 사실·동작·API·파일명은 건드리지 않는다. 범위를 넓히는 수정(새 화면·새 지표)은 AGENTS 절대 규칙 10 대로 되묻는다.
6. **ui_check 재실행**: FAIL 0 유지, Floor WARN(`no transition all`·`no 100vw width`·`uppercase tracked label`·`no middot meta`·`no card in card`) 수가 줄었는지 전후 숫자로.
7. **보고 5줄**: 캡처/HUMAN_CHECK 결과 · 위반 표 요약(P0~P3 건수) · 고친 것(좌표) · 안 고친 것과 이유 · ui_check 전후(PASS/WARN/FAIL 수). debug 폴더 verify.json 에 `ui_check PASS, HUMAN_CHECK` 를 적는다. AGENTS 7절 꼬리 3줄로 끝낸다.

## 금지
- 새 색(raw hex·새 토큰)·새 폰트·외부 URL(폰트·CDN·아이콘)·진입 애니메이션(fade-up·숫자 세기)·기능 추가·문구 사실 변경·템플릿 구조 재설계.
- Hallmark 의 `sloplint.mjs`·Impeccable 런처는 반입하지 않았다(외부망·Node 의존). 출처·라이선스: `LICENSE.txt`(Hallmark MIT, Impeccable Apache-2.0, 원문 미복사·번역 요약).
