# DESIGN.md — 디자인 키트 사용 설명 (1쪽)

시험장 제약(외부 브라우저·CDN·npm 불가, Codex 는 화면을 못 봄)에서 "시중 제품 수준의 화면"을 30분 안에 내기 위한 키트. **참고는 시험장에서 하는 행위가 아니라 동결 전에 끝내 둔 행위**다 — 이 폴더가 그 결과물이다. 전부 표준 기술, 외부 요청 0.

| 파일 | 역할 |
|---|---|
| `tokens.css` | 토큰 1파일: 중립 7 · 브랜드 4(한 블록만 바꾸면 전환) · 의미색 5쌍 · 반경 5단 · 그림자 2 · 링 · 간격 8단 · 시스템 폰트 · 모노 |
| `base.css` | reset · 페이퍼 바탕 + radial 광원 · keep-all · 타이포 5단 · `.container/.section(세로 바 h2 + .why)/.grid/.rail/.split/.stack` · `.hero/.pill` · 미디어쿼리 1024/640 |
| `components.css` | `.card/.bezel` · `.badge`(ok/warn/bad/info/off/brand + live) · `.btn`(기본/primary/brand) · `.table-wrap` · `.banner/.empty/.skeleton/.toast` · `.topbar`(pill/full) · `.kpi/.spark` · `.eq-board[data-state]/.progress` · `.alarm` · `.item/.chip/.order-list` · `.form/.field/.check/.steps` · `.app/.appbar/.list/.tabbar` |
| `kit.html` | 살아있는 스타일가이드. 시험 시작 직후 띄워 **이 환경에서 렌더되는지 2분 안에 확인** |
| `templates/` | `dashboard`(KPI 4 + 설비 보드 + SPC + 로트 표 + 알람) · `console`(좌 미리보기 베젤 / 우 컨트롤 스택) · `landing`(히어로 + 섹션 + 카드 그리드 + 빈 상태) · `mobile`(앱바 + 단계형 폼 + 리스트 + 탭바). 각각 `data.json` 을 fetch 하는 더미 렌더러 + 상태 배너(ok/fallback/failed) 포함 |
| `data.json` | 템플릿 공통 더미(라인·설비·로트·알람·SPC·공지·점검) |
| `serve.py` | `python3 design-kit/serve.py` → `0.0.0.0:$PORT`(기본 8000), `/` 는 `kit.html` 로 |
| `ui_check.py` | 구조·접근성·토큰 준수·문구·반응형·외부 자원·대비를 PASS/WARN/FAIL 표로, exit 0/1 |

## 1. 사용 절차 (과제 폴더에서)
```
cp design-kit/tokens.css design-kit/base.css design-kit/components.css ./static/      # ① 복사 (경로는 과제 구조대로)
cp design-kit/templates/dashboard.html ./static/index.html                            #    가장 가까운 템플릿 1개
python3 design-kit/serve.py 8000 --dir ./static  # 또는 과제 서버                      # ② 미리보기에 뭔가 렌더 (T+30 안)
python3 design-kit/ui_check.py http://127.0.0.1:8000/                                 # ⑤ FAIL 0 까지
python3 scripts/smoke_web.py http://127.0.0.1:8000 --path /api/items                  #    서버 계약
```
① **복사**(템플릿의 `<link href="../tokens.css">` 3줄은 복사 위치에 맞게 — `--dir ./static` 처럼 static 이 서버 루트면 `../` 가 루트로 묶여 그대로 동작, 하위 경로로 서빙하면 `./` 로) → ② **토큰만 사용**: 페이지 CSS·인라인 style 에 raw hex·새 반경·외부 URL 금지, `var(--x)` 만(ui_check 가 잡음) → ③ **data→DOM 매핑 표**를 DECISIONS.md 1번에: `필드 → DOM 요소 → 표시 규칙(단위·정렬·상태색)` → ④ 템플릿 `render()` 만 교체, `esc()` 로 모든 문자열 이스케이프 → ⑤ **ui_check PASS** → ⑥ **HUMAN_CHECK 4질문**(6절, 데스크톱·390px) → ⑦ **기록** debug 폴더 verify.json 에 `ui_check PASS, HUMAN_CHECK`.
매핑 표 예: `lots[].qty → td.num → 정수, 우정렬, 합계 tfoot` / `equipment[].state → .eq[data-state] + .st 글자 → RUN=가동(ok)…`.
Git Bash 주의: `--path /data.json` 처럼 `/` 로 시작하는 인자는 `MSYS_NO_PATHCONV=1` 을 앞에 둔다. `with_server.py` 는 Windows 에서도 서버 트리를 정리한다(taskkill /T, 2026-10-28 수정 · 포트 닫힘 확인). 시험장 Linux 는 killpg.

## 2. 참고 제품 어휘표 (브랜드명 대신 토큰 수준으로 말한다)
| 제품 | 내 이해 기준 서술(공식 토큰 아님) | 키트에서 |
|---|---|---|
| Linear | 13px 고밀도, 1px 헤어라인(6~8% 알파), 반경 6~8, 무채 + 강조 1색, 상태 점, 표가 주인공 | `.table-wrap` + `.badge`, `--r-sm`, 브랜드는 배지·바에만 |
| Notion | 흰 종이, 시스템 16px, 보더 최소, hover 회색, 좌측 정렬 | `.container.narrow`, `.card.flat`, `--hover` |
| Stripe 대시보드 | 연회색 바탕 + 흰 카드, 반경 12, 1px 선, 강조 1색, tabular 숫자, 차트 우선, 12px 메타 | `templates/dashboard.html` 그대로: `.kpi` 첫 줄, `.num`, `.spark` |
| Vercel/Geist | 순흑백, 1px 선, 반경 8, 모노 메타, 여백 넉넉 | `.btn.primary`(검정), `.id`(모노), `--s-7/8` 간격 |
| shadcn/ui | 중립 토큰, radius .625rem, ring 1px 10%, muted-foreground, Card/Badge/Table 프리미티브 | 키트의 기본값(`--ring`, `--muted`, `.card/.badge/table`) |
| Material 3 | 톤 표면, 반경 12/16/28, filled/tonal/outlined 버튼, 엘리베이션 1~3 | `.btn.brand`(filled) / `.btn`(outlined) / `.btn.ghost`, `--shadow-1/2` |
| Toss | 흰 바탕, 24px 굵은 제목, 16px 본문, 전폭 파란 버튼 반경 16~20, 패딩 20~24, 큰 숫자, 짧은 문장 | `templates/mobile.html`: `.btn.brand.wide`, `.summary .value`, 문장 1줄 |
| 커머스 앱(상품 목록형) | 흰 바탕, 2열 상품 카드(정사각 이미지 + 배지 + 2줄 제목 + 가격), 가로 레일, 하단 탭 5개, 큰 검정 CTA | `.item` 카드 2열(640px 이하 자동), `.rail`, `.tabbar`, `.btn.primary` |
| Grafana 알림 목록 | 심각도 색 좌측 띠 + 라벨 칩 + 발생 시각 + 상태(firing/resolved) + 확인 버튼, 최신순 | `.alarm` 행(배지 + 메시지 + 시각 + 확인), `.eq` 좌측 보더 |
| 이전 대회 상위 제출물(사전 조사) 어휘 | 더블베젤(외피/이너코어), 앰비언트 틴트 그림자, 헤어라인 링, 글래스 pill 헤더, 버튼-인-버튼 CTA, 섹션 세로 바 + ⓘ 근거 1줄 | `.bezel>.core`, `--shadow-*`, `--ring`, `.topbar .bar`, `.btn.primary .arrow`, `.section>h2 + .why` |

## 3. Codex 지시 프롬프트 템플릿 (위임 5요소 + 스타일)
```
목표: 설비 상태 대시보드 1페이지(README 3.2 "운영자 화면" 요구 충족)
범위: design-kit/templates/dashboard.html 을 static/index.html 로 복사해 /api/status 응답을 매핑. 새 화면·새 기능 없음
제약: tokens.css 변수만(raw hex·외부 URL·라이브러리 0), 반경은 --r-* 만, 상태색 매핑 ok/warn/bad/info/off 고정,
      진입 애니메이션 없음(hover·active 만), 390px 에서 1열, 모든 문자열 esc(), 서버 0.0.0.0:$PORT
스타일: Stripe 대시보드식 흰 카드 + tabular 숫자. 히어로 없음, KPI 4개가 첫 줄, 표는 Linear 밀도
완료 조건: ui_check.py FAIL 0 · h1 1개/h2 4개 · smoke_web PASS · 매핑 표가 DECISIONS.md 1번에 있음
검증: python3 design-kit/ui_check.py http://127.0.0.1:$PORT/ ; python3 scripts/smoke_web.py http://127.0.0.1:$PORT --path /api/status
피할 것: 4절 전부. 먼저 토큰 계획(색 4~6 · 서체 · ASCII 레이아웃 · 원칙 3줄)만 보여주고 승인 뒤 구현
```

## 4. 피할 것 (AI 생성 티 — 공개 frontend-design 스킬 + 공개 제출물 2개 비교에서)
크림 바탕 + 세리프 + 테라코타 강조 / 흑색 바탕 + 형광 1색 / 신문형 헤어라인·반경 0 / 같은 반경·같은 회색 그림자의 카드 키트 / **모든 제목 위 대문자 추적 라벨**(`.eyebrow` 는 히어로 1곳) / 중점(·)으로 이은 메타 문자열 / `WORD — fragment` 라벨 / 틴트한 근검정 / 작은 라벨만 모노 / **버튼·링크 꼬리 `→`** / 섹션마다 fade-up·카드마다 hover(진입 모션 0, hover·active 만) / 순서가 아닌데 01·02 번호 / 헤드라인 한 단어만 색 강조 / 내부 식별자(`section-type`, `well-RELAX`) 노출 / 로렘 입숨·임시 문구 / 짙은 단색 슬래브 히어로 + 추상 블롭 / 보더 1px 로만 구획된 폼 인상 / 반경 9종이 흩어진 상태. **상위 제출물이 좋아 보인 이유의 절반은 실사진이었다** — 시험장엔 사진이 없으니 미디어 자리에 상태색 블록 + 공정 약어 + 숫자를 넣는다(`.item .media`).
비평·수정은 `$ui-audit`(`.agents/skills/ui-audit/references/hallmark-floor.md`·`impeccable-audit.md`) — Hallmark Floor 16 + Impeccable 점검 순서·비평 형식을 요약했고, ui_check 의 Floor 5규칙(WARN)이 그 정적 절반을 잡는다.

## 5. 반도체 현장 대시보드 관례 (일반 도메인 지식, 검토 필요)
| 항목 | 규칙 |
|---|---|
| 설비 상태 | SEMI E10 6분류를 5상태로 축약: RUN 가동=ok(녹) · IDLE 대기=info(청) · PM 예방보전·엔지니어링=warn(황) · DOWN 고장·알람=bad(적) · OFF 비가동=off(회). **색만으로 구분 금지** — `.eq[data-state]` 좌측 보더 + `.st` 글자 + 배지 |
| KPI 순서 | 수율(%) → 가동률/OEE(%) → WIP(lot) → Cycle time → MTBF/MTTR → Cpk. 큰 숫자 + 단위(`<small>`) + 전일 대비 delta(개선 ok / 악화 bad; 알람 건수는 감소가 개선). 단위 혼재(nm·µm·°C·Torr·sccm·lot·wafer)는 열 이름에 단위를 적는다 |
| 로트 표 열 순서 | LOT_ID(`.id` 모노) → 제품/공정 STEP → EQP_ID → 수량(`.num`) → 시작/종료(시각 HH:MM, 시간대 명시) → 상태 `.badge` → 홀드 사유. sticky 헤더, 필터 + 건수 메타, 홀드 행 `.row-bad`, 20행 넘으면 필터 필수 |
| SPC 추세 | 인라인 SVG 폴리라인 + UCL/LCL 점선(`.limit`) + 목표 실선(`.target`) + 이탈 점 적색 원(`.ooc`). points 생성: `W,H,p=120,32,4; lo,hi=min(v+[lcl]),max(v+[ucl]); pts=' '.join('%.1f,%.1f'%(p+i*(W-2*p)/(len(v)-1), H-p-(x-lo)*(H-2*p)/(hi-lo)) for i,x in enumerate(v))` |
| 알람 패널 | 심각도 Critical/Major/Minor → bad/warn/info, 최신순, 미확인 Critical 은 상단 `.banner.bad`, 확인(ack) 버튼 → 확인자·시각 기록 |
| 톤 | 현장은 표가 많다 → 랜딩형 히어로 대신 "상단 KPI 행 + 상태 보드 + 표"(Stripe/Linear)를 기본값으로. 브랜드색은 `--brand` 블록 1곳. 운영 콘솔은 좌 현황 / 우 조치 컨트롤 `.split` |

## 6. HUMAN_CHECK 4질문 + 390px 체크
미리보기에서 데스크톱 1회, 창 폭 390px 1회. 결과는 DECISIONS.md 에 `HUMAN_CHECK PASS(시각)`.
1. **폴드 안에 핵심 1개**가 보이나(KPI 첫 줄 또는 알람 배너 / 모바일은 핵심 숫자 1개 + 리스트 첫 2행)?
2. **제목 3단**(h1 → 세로 바 h2 → h3)이 눈으로 구분되나?
3. **상태가 색 + 글자**로 함께 있나(배지 텍스트·좌측 보더·범례)?
4. **가로 스크롤이 없나**(표는 `.table-wrap` 안에서만 스크롤)?
390px 추가: `.split`·`.grid` 1~2열로 적층되는지 / `.hide-md` 요소가 숨는지 / 버튼 터치 타깃 ≥ 36px(폼 44px) / 탭바가 콘텐츠를 가리지 않는지(`.app` padding-bottom).

## 7. 헤드리스 크롬 스크린샷 (바이너리가 있을 때만, 없으면 NOT_RUN)
```
CHROME=$(ls /opt/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | head -1); [ -z "$CHROME" ] && CHROME=$(command -v chromium chromium-browser google-chrome 2>/dev/null | head -1)
mkdir -p screenshots
"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=1280,2200 --virtual-time-budget=5000 --screenshot=screenshots/desktop.png "http://127.0.0.1:$PORT/"
"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --window-size=390,1600  --virtual-time-budget=5000 --screenshot=screenshots/mobile.png  "http://127.0.0.1:$PORT/"
```
`--screenshot` 은 뷰포트만 찍으므로 세로를 크게 준다. 시험 -15분에 `ls /opt/ms-playwright` 와 `codex --help | grep -i image` 로 확인(공개 제출물의 스크린샷 스크립트가 그 경로를 적었다 — 추정). Windows 로컬 크롬은 창 최소 폭(약 500px) 때문에 390 이 잘리므로 `<iframe width="390">` 래퍼 페이지를 찍는다(1절 주의와 같은 로컬 한정 사항).

## 8. 검증 기록 (2026-10-28, 로컬 Windows 10 · Python 3.9.7 · Chrome 헤드리스)
| 검증 | 명령 | 결과 |
|---|---|---|
| 스타일가이드·템플릿 4종 구조 점검 | `python design-kit/serve.py 8014` + `python design-kit/ui_check.py kit.html dashboard console landing mobile` | 5페이지 모두 **20 PASS / 0 WARN / 0 FAIL**, exit 0 (대비 최저 4.71 `--warn/--warn-bg`) |
| 서버 계약 | `python scripts/smoke_web.py http://127.0.0.1:8014 --path /data.json --expect-text "디자인 키트"` | **9 PASS / 0 FAIL**(GET / 302→kit.html 200, viewport, h1 1개, 외부 자원 0, JSON, 경로 탈출 404) |
| 방어막 함수 | `python -m unittest tests.test_guards -v` | **21 tests OK**(우회 5 · 과차단 방지 2 · 합계 보존 · 마스킹 · 타임아웃 · 근거) |
| 렌더 확인(시각) | 헤드리스 크롬 1280 + 390(iframe 래퍼) 10장 | kit·dashboard·landing·mobile 양쪽 렌더 확인. 발견·수정한 결함 3건: `.alarm` 패널과 표 행 클래스 충돌 → `.row-bad/.row-warn`, 진행 바 `.bar` 와 `.topbar .bar` 충돌로 상단바 잘림 → `.progress`, 390px 상단바 글자 세로 깨짐 → `nowrap` + `.actions` 줄바꿈 |
| 콘솔 390px | 동일 출처 iframe 에서 DOM 덤프 | `status=banner ok · 섹션 3개 · 설비 5대`, JS 오류 0 (file:// 래퍼 스크린샷은 스켈레톤으로 찍혔음 — 캡처 타이밍 문제, 실제 미리보기에서 HUMAN_CHECK 필요) |
| 제출 전 점검 | `python scripts/preflight.py` (하네스 루트) | **exit 0** — secret-scan PASS(28파일) · abs-path PASS · compile PASS · tests PASS **33 run / 0 fail / 1 skip**(test_guards 21 포함). 미완성 문구 스캔 WARN 3건은 키트 밖 기존 파일(README.md·scripts/check_contract.py·tests/test_template.py) |
| 검사기 음성 테스트 | 일부러 망가뜨린 페이지(hex·라벨 없는 input·thead 없음·`→` 꼬리·외부 script·lorem·미정의 var) | **12 FAIL / 5 WARN**, exit 1 — 검사기가 실제로 실패를 잡는 것을 확인 |

NOT_RUN: 웹 IDE 실제 미리보기에서의 HUMAN_CHECK(시험장에서만 가능), Linux 헤드리스 크롬 `--window-size=390` 동작(사전 체험 때 확인), 브랜드 전환 후 대비 재검사(전환할 때 `ui_check` 재실행).
