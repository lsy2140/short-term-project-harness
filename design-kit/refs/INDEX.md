# refs/INDEX.md — 서비스별 디자인 참고 md 목록 (색·서체·분위기 후보)

## 쓰는 법 (INDEX 만 읽고 후보 5개만 연다 — 원문은 한 개 21~142KB)
1. 유형 1개(REFERENCE.md) → `python3 design-kit/refs/pick.py <유형|키워드 …>` 로 후보 5개(시안 N = md N + 배치 N)
2. 후보마다 시안 1개: 이미지 생성 도구가 있으면 `static/draft/sian_N.png`, 없으면 `static/draft/sian_N.html` + 캡처(틀: `illustrations/PROMPTS.md` 시안 절)
3. 사람에게 1줄씩 보고(번호·출처 md·배치 이름·분위기 3단어·그림 자리·미리보기 경로) → 사람이 번호 1개 선택(그 전에는 본 화면을 만들지 않는다)
4. 고른 md(색) + 배치 + 그림 자리 + PRD 4절 → `design-kit/DESIGN_과제.md`(틀: `refs/_DESIGN_과제.template.md`, 0·1-1·2·9절)
5. 템플릿·키트 파일을 `static/` 에 복사하고 `static/tokens.css` 를 DESIGN_과제.md 2절(색) 값으로 바꾼다(hex 는 tokens.css 에만) → ui_check 대비 4.5:1
6. 데이터 매핑·그림 자리로 화면 초안(`$web-ui 초안`, SKILL ②~③)
- 옮기는 것: 색·서체 느낌(굵기·자간)·간격·반경·분위기·문구 톤 / 안 옮기는 것: 로고·서비스 이름·폰트 파일·문구 원문·사진

## 표 읽는 법
- 유형 태그 = REFERENCE.md 유형 번호: 모니터링(1)·조회(2)·콘솔(3)·모바일(4)·홈(5). 앞에 적은 태그가 더 잘 맞는다.
- 주색·바탕 = 원문에 적힌 값. 화면에 옮길 때 글자 대비를 다시 잰다(ui_check). 크기KB = 원문 크기.
- 서체 느낌 = 원문 서체. 화면은 시스템 서체만 쓰므로 굵기·자간으로 느낌만 맞춘다.
- 출처: `ko/` = ko-design-md(CC BY 4.0), `awesome/` = awesome-design-md(MIT). 원문을 고치지 않고 그대로 복사했다. 저작자 표기 전문은 LICENSE 의 Third-party notices 3·4.
- 고른 md 는 DESIGN_과제.md 0절과 README 실제 vs 목업 표에 1줄: `디자인 참고: refs/ko/toss.md (ko-design-md, CC BY 4.0) — 색·간격만 참고, 원문 수정 없음`.

## 목록 (53개: 한국 서비스 27 · 해외 서비스 26)
| 폴더/파일 | 서비스 한 줄 | 유형 태그 | 분위기 3단어 | 주색·바탕 | 서체 느낌 | 크기KB | 라이선스 |
|---|---|---|---|---|---|---|---|
| `ko/11st.md` | 11번가 — 종합 쇼핑몰(모바일 우선) | 홈, 모바일 | 강렬·정돈·실용 | #FF0038 빨강 / 흰색 | 시스템 고딕, 가격만 전용 서체 | 28 | CC BY 4.0 |
| `ko/baemin.md` | 배달의민족 — 음식·장보기 배달 앱 | 모바일, 홈 | 위트·친근·손맛 | 민트(배포 #0CEFD3) / 흰색 | 간판풍 손글씨 제목 + Pretendard | 65 | CC BY 4.0 |
| `ko/banksalad.md` | 뱅크샐러드 — 자산관리·금융상품 비교 | 모바일, 조회 | 절제·차분·신뢰 | #06A96C 초록 / 흰색(쿨 그레이) | Pretendard, 숫자 고정폭 | 70 | CC BY 4.0 |
| `ko/bezier.md` | 채널톡 — 고객 상담 SaaS 제품 화면 | 콘솔, 조회 | 밝음·깨끗·둥긂 | #6157EA 인디고 / 흰색 | Inter + Noto Sans KR | 142 | CC BY 4.0 |
| `ko/class101.md` | 클래스101 — 온라인 클래스 구독 | 홈, 모바일 | 활기·선명·일관 | #FF5D00 주황 / 흰색 | 공식 서체 없음(Pretendard 대체) | 41 | CC BY 4.0 |
| `ko/codeit.md` | 코드잇 — 프로그래밍 교육 | 홈, 조회 | 깔끔·몰입·긍정 | #6500C3 보라 / 흰색 | Spoqa Han Sans Neo + 코드 Menlo | 63 | CC BY 4.0 |
| `ko/gmarket.md` | 지마켓 — 오픈마켓 쇼핑(모바일 우선) | 홈, 모바일 | 밝음·깨끗·정렬 | #00C400 초록(구매 #0028AC) / 흰색 | Noto Sans KR + 제목·가격 전용 서체 | 48 | CC BY 4.0 |
| `ko/greeting.md` | 그리팅 — 채용 관리 업무 도구 | 콘솔, 조회 | 밀도·조용·사무적 | #1890FF 파랑 / 흰색 | Pretendard 하나 | 60 | CC BY 4.0 |
| `ko/gs-retail.md` | 우리동네GS — 편의점·장보기 앱 | 모바일 | 친근·생활밀착·둥긂 | #00D4EA 청록, 버튼 #1E2530 / 흰색 | 미확인(웹뷰는 Pretendard) | 37 | CC BY 4.0 |
| `ko/gs-shop.md` | GS SHOP — TV·모바일 홈쇼핑 | 모바일, 홈 | 선명·대비·촘촘 | #0F78FF 파랑, 구매 #FF2F93 / 흰색 | Pretendard | 48 | CC BY 4.0 |
| `ko/krds.md` | KRDS — 정부·공공 웹 디자인 시스템 | 홈, 조회, 콘솔 | 신뢰·중립·접근성 | #256EF4 파랑 / 흰색 | Pretendard GOV | 38 | CC BY 4.0 |
| `ko/kyobobook.md` | 교보문고 — 서점 온라인 몰 | 조회, 홈 | 미니멀·가독·지적 | #5055B1 인디고 / 흰색 | Noto Sans KR + Roboto | 31 | CC BY 4.0 |
| `ko/lg-electronics.md` | LG전자 — 가전 브랜드·쇼핑 | 홈 | 따뜻·감성·둥긂 | #FD312E 빨강 / 웜 그레이 #F0ECE4 | 전용 서체(재배포 불가), 국내는 Pretendard | 64 | CC BY 4.0 |
| `ko/likelion.md` | 멋쟁이사자처럼 — 코딩 교육·부트캠프 | 홈 | 격려·친근·실무 | #FF6000 주황 / 흰색 | Pretendard | 34 | CC BY 4.0 |
| `ko/line-design-system.md` | 라인 — 메신저 계열 앱 공용 시스템 | 모바일 | 절제·조용·중립 | #06C755 초록 / 흰색 | 언어별 시스템 서체(웹폰트 없음) | 58 | CC BY 4.0 |
| `ko/nol.md` | NOL — 여행·공연 예약 | 모바일, 조회, 홈 | 선명·사진 중심·둥긂 | #3549FF 파랑 / 흰색 | Pretendard | 56 | CC BY 4.0 |
| `ko/remember.md` | 리멤버 — 명함·경력 채용 | 모바일, 조회 | 절제·전문·무채색 | 검정 #000000, 강조 #FF6A0D / 흰색 | Pretendard | 39 | CC BY 4.0 |
| `ko/ridi.md` | 리디 — 웹툰·웹소설·전자책 | 조회, 홈 | 차분·정돈·표지 중심 | #1F9EFF 하늘색 / 흰색 | Pretendard Variable | 87 | CC BY 4.0 |
| `ko/samsung-one-ui.md` | 삼성 One UI — 기기 공통 화면 언어 | 모바일 | 편안·단순·한 손 | #0381FE 파랑 / 흰색 #FAFAFA | Roboto·Pretendard(시스템) | 45 | CC BY 4.0 |
| `ko/seed-design.md` | 당근 — 동네 커뮤니티·중고거래 | 모바일 | 친근·부드러움·역할 중심 | #FF6600 주황 / 흰색 | 시스템 서체(자체 서체 없음) | 79 | CC BY 4.0 |
| `ko/socar.md` | 쏘카 — 차량 공유 | 모바일, 조회 | 차분·신뢰·덜어냄 | #0078FF 파랑 / 흰색(푸른 회색) | Pretendard Variable | 54 | CC BY 4.0 |
| `ko/teamsparta.md` | 팀스파르타 — 학습 대시보드(수강생·운영자) | 콘솔, 모니터링 | 따뜻·격려·실행 | #FA0030 빨강 / 흰색 | Pretendard Variable, 12~14px 촘촘 | 35 | CC BY 4.0 |
| `ko/toss.md` | 토스 — 송금·금융 앱 | 모바일, 홈 | 절제·명료·친근 | #3182F6 파랑 / 흰색(#F2F4F6) | 전용 서체(Toss Product Sans) | 64 | CC BY 4.0 |
| `ko/vapor-ui.md` | 구름 — 개발 교육·도구 제품 화면 | 콘솔, 조회 | 밝음·부드러움·토큰 중심 | #2A72E5 파랑 / 흰색 | Pretendard + 숫자 Inter | 74 | CC BY 4.0 |
| `ko/wanted.md` | 원티드 — 채용·커리어 | 조회, 홈 | 깔끔·여유·중립 | #0066FF 파랑 / 흰색 | Pretendard JP + 제목 Wanted Sans | 91 | CC BY 4.0 |
| `ko/yeogi.md` | 여기어때 — 숙박·여행 예약 | 모바일, 조회 | 단순·생생·즐거움 | #F7323F 빨강 / 흰색 | Pretendard + 제목 전용 서체 | 68 | CC BY 4.0 |
| `ko/zigbang.md` | 직방 — 부동산 앱 공통 부품 | 모바일, 조회 | 조밀·무채색·한 점 강조 | #FF6905 주황 / 흰색(#F7F7F7) | Pretendard | 56 | CC BY 4.0 |
| `awesome/airbnb.md` | Airbnb — 숙소·체험 예약 | 조회, 모바일, 홈 | 따뜻·여유·사진 중심 | #FF385C 분홍빨강 / 흰색 | 둥근 산세리프, 중간 굵기 | 30 | MIT |
| `awesome/airtable.md` | Airtable — 표 기반 업무 도구 | 조회, 홈 | 차분·편집·잡지형 | #181D26 거의 검정 / 흰색 | 그로테스크, 굵기 절제 | 34 | MIT |
| `awesome/cal.md` | Cal.com — 일정 예약 | 조회, 홈 | 친근·깔끔·여유 | #111111 검정 / 흰색 | 좁은 기하 제목 + Inter | 30 | MIT |
| `awesome/clickhouse.md` | ClickHouse — 분석용 데이터베이스 | 모니터링 | 고대비·강렬·직설 | #FAFF69 형광 노랑 / 검정 #0A0A0A | Inter 굵게 + 코드 모노 | 25 | MIT |
| `awesome/cursor.md` | Cursor — AI 코드 편집기 | 조회 | 조용·편집·따뜻 | #F54E00 주황 / 크림 #F7F7F4 | 산세리프 400 제목 + 코드 모노 | 21 | MIT |
| `awesome/hashicorp.md` | HashiCorp — 클라우드 인프라 자동화 | 콘솔 | 확신·기술·제품색 구분 | 흰색 버튼(제품별 강조색) / 검정 #000000 | 기하 산세리프 600~700 | 27 | MIT |
| `awesome/ibm.md` | IBM(Carbon) — 기업용 시스템 | 모니터링, 콘솔, 조회 | 평면·사각·엄정 | #0F62FE 파랑 / 흰색(#F4F4F4) | IBM Plex Sans, 가는 제목 | 26 | MIT |
| `awesome/intercom.md` | Intercom — 고객 상담 플랫폼 | 조회, 콘솔 | 차분·제품 중심·따뜻 | #111111 차콜(AI 강조 #FF5600) / 크림 #F5F1EC | 기하 산세리프 500 | 23 | MIT |
| `awesome/linear.app.md` | Linear — 이슈 추적·프로젝트 관리 | 조회, 콘솔 | 어둠·밀도·정밀 | #5E6AD2 라벤더 / 검정 #010102 | 기하 산세리프, 음수 자간 | 24 | MIT |
| `awesome/mercury.md` | Mercury — 스타트업 은행 | 모바일, 홈 | 조용·정밀·야간 | #5266EB 인디고 / 흰색 #FBFCFD(밤 #171721) | 가벼운 굵기 전용 산세리프 | 24 | MIT |
| `awesome/mintlify.md` | Mintlify — 개발 문서 사이트 | 조회, 홈 | 밀도·문서형·하늘빛 | #0A0A0A 검정(강조 #00D4A4) / 흰색 | Inter + 코드 모노 | 43 | MIT |
| `awesome/mongodb.md` | MongoDB — 데이터베이스 클라우드 | 콘솔, 홈 | 대비·기술·문서형 | #00ED64 초록 / 흰색(띠 #001E2B) | 기하 산세리프 + 코드 모노 | 31 | MIT |
| `awesome/notion.md` | Notion — 문서·DB 작업 공간 | 홈, 조회 | 자신감·일러스트·파스텔 | #5645D4 보라 / 흰색(띠 #0A1530) | Inter 기반 산세리프 | 34 | MIT |
| `awesome/nvidia.md` | NVIDIA — GPU·반도체 기술 | 홈, 모니터링 | 공학·각짐·정보 밀도 | #76B900 초록 / 흰색(띠 #000000) | 굵은 산세리프(Arial 대체) | 35 | MIT |
| `awesome/oracle.md` | Oracle — 기업용 클라우드 | 콘솔, 홈 | 절제·웜그레이·조용 | #312D2A 차콜(로고만 #C74634) / 흰색(#FBF9F8) | 휴머니스트 산세리프 + 세리프 제목 | 42 | MIT |
| `awesome/posthog.md` | PostHog — 제품 분석 | 모니터링, 콘솔 | 따뜻·장난·스케치북 | #F7A501 노랑주황 / 크림 #EEEFE9 | IBM Plex Sans | 40 | MIT |
| `awesome/raycast.md` | Raycast — 명령 팔레트 런처 | 조회 | 어둠·정밀·간결 | 흰색 버튼 / 검정 #07080A | Inter(대체 글자 모양) | 40 | MIT |
| `awesome/revolut.md` | Revolut — 모바일 뱅킹 | 모바일, 홈 | 고대비·대담·잡지형 | #494FDF 인디고 / 검정·흰색 교차 | 휴머니스트 산세리프 + Inter | 31 | MIT |
| `awesome/sap.md` | SAP — 기업 업무 시스템 | 콘솔, 조회 | 조용·업무형·평면 | #0057D2 파랑 / 흰색(상단 바 #F5F6F7) | 가변 산세리프, 굵기로 위계 | 33 | MIT |
| `awesome/sentry.md` | Sentry — 오류·성능 모니터링 | 모니터링 | 어둠·장난·대담 | #C2EF4E 라임 / 보랏빛 밤 #1F1633 | 둥근 산세리프(Rubik) + 모노 | 35 | MIT |
| `awesome/stripe.md` | Stripe — 결제 인프라 | 홈, 콘솔 | 정제·편집·금융 | #533AFD 인디고 / 흰색(글자 #0D253D) | 가는 산세리프 300, 숫자 고정폭 | 24 | MIT |
| `awesome/supabase.md` | Supabase — 오픈소스 DB 플랫폼 | 콘솔, 모니터링 | 명료·조용·기술 | #3ECF8E 에메랄드 / 흰색 | 휴머니스트 기하 산세리프(Inter 대체) | 21 | MIT |
| `awesome/uber.md` | Uber — 이동·배달 앱 | 모바일 | 흑백·절제·알약형 | #000000 검정 / 흰색 | 기하 산세리프 700 제목 | 34 | MIT |
| `awesome/vercel.md` | Vercel — 개발자 배포 플랫폼 | 콘솔, 홈 | 흑백·단호·정밀 | #171717 검정 / 흰색 #FAFAFA | 기하 산세리프 + 모노 라벨 | 40 | MIT |
| `awesome/wise.md` | Wise — 해외 송금 | 모바일, 홈 | 대담·산뜻·잡지형 | #9FE870 라임 / 흰색(세이지 #E8EBE6) | 아주 굵은 제목(900) + Inter | 24 | MIT |
| `awesome/zapier.md` | Zapier — 업무 자동화 | 콘솔, 홈 | 따뜻·성숙·수수 | #FF4F00 주황 / 크림 #FFFEFB | 기하 제목 + Inter | 22 | MIT |

## 새 md 를 넣을 때
- 원본 저장소의 md 를 바이트 그대로 복사한다(줄끝 LF, 고치지 않는다). 파일을 열어 보고 위 표에 1행을 적는다(모르면 '-').
- 확인: `python3 -m unittest discover -s scripts/tests -p test_refs_pick.py` (표 행 = 파일, 크기·라이선스 대조). 새 저장소면 LICENSE 의 Third-party notices 에도 1항.
