# Hallmark "The Floor" 16 — 한국어 요약과 우리 키트 대응

출처: Nutlope/hallmark (MIT) `skills/hallmark/SKILL.md` "The Floor" 1~16, `references/gates.md` §1·§4, `references/interaction-and-states.md`, `references/macrostructures/{04-stat-led,05-workbench,02-long-document}.md` — 커밋 8f6969f, 2026-10-28 확인. 원문 영어는 복사하지 않고 번역·요약했다(라이선스는 `../LICENSE.txt`). 괄호 숫자는 원문 게이트 번호.
읽는 법: '우리 키트에서' = **ui_check 가 잡는다**(검사 이름) / **사람이 본다**(HUMAN_CHECK·캡처) / **해당 없음**(이유). ui_check 의 Floor 검사 5개는 모두 WARN 이고 기존 FAIL 기준과 섞지 않는다.

## 1. The Floor 16 — 면제 불가 (SKILL.md "The Floor")
| # | 규칙(번역·요약) | 우리 키트에서 |
|---|---|---|
| 1 | 모든 색·서체는 `:root` 토큰을 거친다. 토큰 블록 밖에 색 리터럴·`font-family` 금지 (48) | ui_check `no raw hex in page`(FAIL)·`no raw hex in linked css`·`var() defined` |
| 2 | `transition: all` 금지. `width`·`height`·`top`·`left` 를 애니메이션하지 않는다 (10a) | ui_check `no transition all`. 시간만 적은 `transition: .25s`(키트 `.toast`)는 못 잡는다 → 새로 쓰지 않고, 보이면 사람이 본다 |
| 3 | 로만체 제목 안에 이탤릭 한 단어 금지 (38i) | 사람이 본다. 키트 CSS 에 이탤릭이 없어 새로 넣지 않으면 생기지 않는다 |
| 4 | `html`·`body` 에 `overflow-x: clip`. `hidden` 도 `100vw` 도 금지 (34) | ui_check `no 100vw width`(width/min-width 만 — `max-width` 의 100vw 는 가로 스크롤을 못 만든다). 가로 스크롤 자체는 HUMAN_CHECK 4번 |
| 5 | 이미지 든 그리드 트랙은 `minmax(0, 1fr)`, 큰 제목에 `overflow-wrap: break-word; min-width: 0` (50) | 사람이 본다(390px). web-ui-build 절차 7 의 처방 `minmax(0,…)`·`overflow-x:auto` |
| 6 | 모든 상호작용 요소에 `:focus-visible` 링, 즉시 표시 (26a, 15) | 해당 없음 — base.css:27 전역 `:focus-visible` 링. `outline: none` 을 새로 쓰지 않으면 유지 |
| 7 | 모든 애니메이션에 `prefers-reduced-motion: reduce` 폴백, 스크립트를 꺼도 내용이 보인다 (27, 62) | 해당 없음 — base.css:93 전역 폴백. JS 렌더 템플릿은 빈 상태 글자가 먼저 보이는지 사람이 본다 |
| 8 | 지어낸 지표·추천사·로고 벽·사례 수 금지 (46a) | 사람이 본다 — AGENTS 절대 규칙 2(수치는 코드로, 없는 값은 '확인 필요') |
| 9 | 아이브로(제목 위 짧은 라벨) 금지. 대문자 추적·스몰캡 라벨 금지 — 라벨·캡션·표 머리·태그·내비는 본문 서체 한 단계 작게, 문장체 (54, 67) | ui_check `uppercase tracked label`(같은 블록의 uppercase+letter-spacing)·`no all-caps headings`. 키트는 `.eyebrow` 를 히어로 1곳만 허용(DESIGN.md 4절) — Hallmark 보다 느슨 |
| 10 | 가운뎃점으로 이은 메타 문자열, 링크 글자에 붙인 화살표, 장식 상태 점 금지 (63) | ui_check `no middot meta`(띄어쓴 `A · B` 3요소 이상)·`no '→' tail`. 한국어 나열 '수율·가동률'은 띄지 않아 제외. 상태 점은 글자와 함께면 허용(색+글자 원칙) |
| 11 | 보라→파랑 그라디언트, 카드 속 카드, 아이콘 대용 이모지, 손으로 그린 브라우저·OS 창 금지 (2a, 4, 30a, 47a) | ui_check `no card in card`(`.card.flat` 안쪽은 허용 — kit.html:122 '중첩 카드용'). 그라디언트·이모지·창 프레임은 사람이 본다 |
| 12 | 히어로의 헤드라인·한 문장·주 행동이 1280×800 에서 스크롤 없이 보인다 (44b) | 사람이 본다 — HUMAN_CHECK 1번(폴드 안 핵심 1개). 운영 화면은 히어로 대신 KPI 첫 줄·알람 배너 |
| 13 | 한 화면 약 80단어. 히어로 글은 헤드라인·한 문장·행동뿐 (58) | 해당 없음 — 운영 화면은 표·숫자가 주인공이라 단어 수 상한을 적용하지 않는다. 설명문(`.why`)은 1줄만 |
| 14 | 컨테이너는 상한을 두고 가운데. 1920 에서 여백만 늘고 행 길이·그리드 열은 늘지 않는다 (44d) | 해당 없음 — base.css:45 `.container` max-width 1120px. 새 전폭 레이아웃을 만들면 사람이 본다 |
| 15 | CSS 첫 줄은 Hallmark 스탬프, 그 다음 비평 줄·면제 줄 (20) | 해당 없음 — Hallmark 전용 서명. 우리 기록은 DECISIONS.md 검증 로그 |
| 16 | Node 가 있으면 `sloplint.mjs --render` 를 돌려 FAIL 전부 수정, REFLEX 는 수정 또는 면제 | 해당 없음 — sloplint 미반입(외부 폰트 검사 등 시험장과 불일치). ui_check Floor 5규칙이 2·4·9·10·11 의 정적 절반을 맡는다 |

Floor 위에는 **Reflex**(모델이 빠지는 기본값, 이유를 적고 면제 가능)와 **Finish**(마감 세부, 보고만) 가 있다(gates.md §1). 아래는 Reflex 중 운영 화면에 맞는 12개.

## 2. Reflex 12 — 대시보드·콘솔·모바일 폼에 맞는 것 (gates.md §4)
| 게이트 | 티(번역·요약) | 수정·키트 대응 |
|---|---|---|
| 3 | 카드 티: 아이콘-제목-글 타일 3열 균등, 둥근 타일 속 아이콘, 카드의 두꺼운 색 띠 | 폭·높이를 달리, 아이콘은 인라인. 키트 `.eq` 좌측 보더는 상태(색+글자)라 유지, 장식 띠는 안 쓴다 |
| 9 | 모든 섹션을 같은 방식·같은 간격으로 나눈다 | 자리마다 표면 단계를 달리: 여백 → 헤어라인 → 틴트 면 → 카드 |
| 11 | 같은 hover 리프트를 모든 카드에, 한 요소에 효과 둘, 상호작용 없는 요소의 hover, 이미지 확대 | 요소당 신호 1개. `.card.lift` 는 클릭되는 항목 카드에만 |
| 16 | 이미 화면에 보이는 효과에 축하 토스트 | 토스트는 실패와 안 보이는 효과(제출 전송)에만 — `.toast` |
| 24b | 간격 척도 밖의 값 | `--s-*` 만, 미세 조정은 3곳 이하 |
| 25 | 본문 문단 `max-width` 가 45~75ch 밖, 한 줄 88자 이상 | 설명 문단 `max-width: 65ch` |
| 26b | `:active`·`:disabled` 없음 | 컨트롤 8상태(기본·hover·focus·active·disabled·loading·error·success). disabled 는 opacity+`cursor`+속성 3채널 |
| 39b | 컨트롤 높이가 44~52px 밖(앱 UI 는 32~40 + 히트 영역 확장) | 키트 `.btn` 36px, 폼 44px(DESIGN.md 6절) |
| 64 | 코드·수치가 아닌 라벨·캡션·표 머리에 모노 | 모노는 `.id`·수치·코드만 |
| 71 | 제목이 뒤 내용보다 앞 내용에 더 가깝다 | 제목 위 여백 ≥ 아래 여백 × 2 |
| 72 | 박스 안 글자가 가장자리 8px 안, 폰 가장자리 8px 안 | 박스 패딩 `--s-3` 이상, 폰 거터 16px |
| 75 | 본문 12px 미만, 기능 글자 11px 미만, 여러 줄 행간 1.3 미만 | 본문 16(모바일)·표 13(Linear 밀도), 라벨은 한 단계 작게, 행간 1.5 |

## 3. 매크로구조 3종 — 어떤 과제 화면에 맞나 (macrostructures/04·05·02)
**Stat-Led (04)**
- 사용자가 준 숫자 하나가 히어로, 그 옆에 뜻을 말하는 헤드라인(예: "4초. 알림에서 느린 구간까지"). 뒤 섹션은 각각 숫자·차트로 받친다.
- `tabular-nums`, 헤어라인 구분, 버튼은 동사 라벨의 윤곽 칩. 숫자 세기 모션은 실제 숫자일 때만 — 우리는 진입 모션 0 이라 생략.
- 맞는 화면: KPI 대시보드(`templates/dashboard.html` KPI 4개 첫 줄), 수율·가동률 리포트, 심사자에게 보여줄 결과 요약.
- 숫자가 없으면 쓰지 않는다. 지어낸 큰 숫자는 없는 것보다 나쁘다(46a).
**Workbench (05)**
- 실제 제품 캡처가 주인공. 페이지는 '쓰고 있는 앱'의 안내 투어, 캡션은 사실 한 줄 + 주석 1개, 마케팅 문구 없음.
- 캡처는 `<figure>`+`<figcaption>`, 브라우저·기기 프레임 없음. 행동은 히어로 1개(필요하면 셋째 캡처 뒤 하단 고정 바).
- 맞는 화면: 운영자 콘솔(`templates/console.html` 좌 미리보기 베젤 / 우 컨트롤), 조치·설정 도구, README 데모 순서 페이지.
- 보여줄 UI 가 없는 개념·서비스형 과제에는 맞지 않는다.
**Long Document (02)**
- 메모·편지처럼 한 열 연속 산문. 제목은 굵은 짧은 구로 본문 흐름에 녹이고, 행간 1.65 이상·60~65ch.
- 구분은 여백뿐, 이미지는 본문 폭 안, 진입 모션 없음. 행동은 문단 안의 동사 링크 하나.
- 맞는 화면: 심사자용 PLAN/HANDOFF 미리보기, 결정과 이유를 설명하는 페이지(`.container.narrow`).
- 제출·확인처럼 결정적 행동이 하나 있는 화면에는 맞지 않는다 — 행동이 문장 속에 숨는다.
