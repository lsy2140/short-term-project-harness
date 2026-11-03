# DESIGN.md — 디자인 키트 사용 설명 (1쪽)

- 키트 = 토큰·부품·템플릿 3종·아이콘·그림 자리·참고 md. 외부 URL·CDN·폰트 파일·라이브러리 금지(`illustrations/`·`icons.svg` 는 로컬이라 허용).
- 순서: REFERENCE.md 유형 1개 → refs 후보 시안 → 사람이 1개 선택 → DESIGN_과제.md → templates/ 복사·tokens.css → 데이터 매핑 → 그림 자리 초안 → ui_check → 최종 그림 → `ui_check --final`.

| 파일 | 용도 |
|---|---|
| tokens.css | 색·반경 2단+pill·그림자 2단·간격·서체. 바꾸는 곳은 [브랜드] 4줄과 [중립] 바탕·패널·잉크뿐 |
| base.css | reset·글자 5단·레이아웃(container·split 40:60·cols-3)·반응형 1024/640 |
| components.css | card/panel·badge·btn·table·banner/empty·stat/spark/hbar·eq·alarm·rows·tabs·seg·form·figure·app |
| kit.js | 공통 함수 K: esc·fmt·hhmm·kv·badge·chips·toast·setStatus·load·spark·hbar |
| kit.html | 부품 견본 + 템플릿에 없는 블록(설정 폼·위험 구역, 홈 히어로) |
| templates/ | dashboard(모니터링)·tool(조회·검색)·mobile(현장 앱). data.json fetch, 상태 배너 3종 |
| REFERENCE.md | 화면 유형 5개: 와이어 1280/390·섹션 순서·배치·문구 톤·그림 자리 |
| refs/ | 서비스별 참고 DESIGN.md 53개(한국 27·해외 26)·INDEX.md·pick.py·DESIGN_과제 틀(2절) |
| icons.svg | 직접 그린 24px 라인 아이콘 27개, `<use href="icons.svg#i-bell"/>` |
| illustrations/ | 그림 폴백 세트 자리(README)·생성 프롬프트(PROMPTS: 세트·과제 전용·시안 틀) |
| serve.py / ui_check.py | 정적 서버(Codex 가 띄우고 포트 보고) / 정적 점검(구조·접근성·토큰·그림 자리·장식·외부 자원·대비) |

## 1. 사용 절차 (과제 폴더에서)
1. 유형·디자인: REFERENCE.md 유형 1개(섞이면 주 화면만) + 2절에서 고른 DESIGN_과제.md.
2. 복사: 템플릿 + tokens/base/components.css·kit.js·icons.svg → 정적 폴더, `../` 삭제(틀리면 ui_check `local asset` FAIL). 복사한 tokens.css 에 DESIGN_과제.md 2절 색.
3. 매핑: `K.load('<API 또는 json>', 내장샘플)` → render 함수. '데이터 필드 → 화면 위치' 표는 B_web.md ⑤(단일 세션은 DECISIONS 1).
4. 상태: 배너 3종(실데이터·내장 샘플·실패)은 지우지 않는다. 빈 결과는 `.empty`(무엇이 없나 + 다음 행동). 확인은 주소에 `?state=fallback`·`?state=failed`.
5. 점검: B 가 서버를 띄우고 포트를 보고한 뒤 `python3 design-kit/ui_check.py http://127.0.0.1:<PORT>/` FAIL 0, 390px 1회.

## 2. 참고 md·시안 (`$web-ui 시안` — 사람이 1개 고른 뒤 본 화면)
- 흐름: 유형 → `python3 design-kit/refs/pick.py <유형|키워드>` 후보 2~3 → 후보마다 시안 1개 → 1줄씩 보고 → 사람이 번호 1개 → `design-kit/DESIGN_과제.md`(틀 `refs/_DESIGN_과제.template.md`) → 1절(복사 뒤 tokens.css).
- 시안: 이미지 생성 도구가 있으면(사전 체험 1장 성공) 1280×800 PNG `static/draft/sian_N.png`, 없으면 템플릿에 후보 토큰만 입힌 `static/draft/sian_N.html` + 캡처. 틀·명령은 `illustrations/PROMPTS.md` 시안 절.
- 보고: `시안 N · refs/<…>.md · 분위기 3단어 · <미리보기 경로>`. 고를 때까지 본 화면은 만들지 않는다(서버·API·매핑 표는 된다). 사람이 `시안 생략` 이면 키트 기본 토큰.
- 옮기는 것: 색·서체 느낌·간격·반경·분위기(로고·서비스 이름·폰트 파일·문구 원문은 안 옮긴다).
- tokens.css: 복사한 `static/tokens.css` 의 [브랜드]·[중립] 값만, 상태색 5쌍 고정, hex 는 tokens.css 에만 → `ui_check` contrast PASS(4.5:1).
- 4절 '피할 것'과 겹치는 원문(검정+형광, 크림+세리프)은 사람이 시안을 보고 고르면 쓴다 — DESIGN_과제.md 1절에 이유 1줄.
- 라이선스: ko = CC BY 4.0, awesome = MIT(원문 그대로, LICENSE Third-party notices 3·4). 고른 md 출처 1줄 → DESIGN_과제.md 0절·README 실제 vs 목업 표.

## 3. Codex 지시 틀 (`$web-ui 시안` / `초안` / `최종`)
```
목표: <화면 1개> (PRD 4·5 요구) · 유형 REFERENCE <번호> · 디자인 DESIGN_과제.md(시안 <N>)
범위: <API/파일> → render 매핑만. 새 화면·새 기능 없음
제약: tokens.css 변수만(raw hex·외부 URL·라이브러리 0), 상태색 고정, 진입 애니메이션 없음, 390px 1열, K.esc,
      그림 자리는 .figure 초안, 서버는 네가 백그라운드로 띄우고 포트를 보고한다
완료: ui_check FAIL 0 · smoke_web PASS · 매핑 표·그림 계획 표가 B_web.md ⑤(단일 세션은 DECISIONS 1) · 피할 것 = 4절
```

## 4. 피할 것 (AI 생성 티)
같은 반경·같은 그림자 카드 반복과 KPI 4칸 공식 / 점-pill 배지·pill 버튼 남발 / 섹션마다 세로 바 + 설명줄(`.why`) / 도구 화면의 큰 제목+리드 문장 / 광원·글래스·이중 베젤·버튼-인-버튼 / 크림 바탕+세리프+테라코타, 흑색 바탕+형광 1색 / 모든 제목 위 대문자 추적 라벨(`.eyebrow` 는 홈 히어로 1곳) / 띄어쓴 가운뎃점 메타 / 버튼·링크 꼬리 화살표 / 진입 fade-up(hover·active 만) / 순서가 아닌 01·02 번호 / 헤드라인 한 단어 색 강조 / 기계 문자열 노출(ISO 시각·내부 키) / 축 없는 막대 / 임시 문구 / 짙은 단색 히어로+추상 블롭 / 반경 여러 종.
**그림 0장과 글자 블록 대체가 가장 큰 티였다** → 그림 자리는 `.figure` 로 남기고 최종에 그림, 없으면 틴트 면+아이콘(`.ico-tile`)이나 데이터 그림.
비평·수정 기준은 `$web-ui 최종` ⑥-3(`.agents/skills/web-ui/references/hallmark-floor.md`·`impeccable-audit.md`). ui_check 의 Floor 5규칙과 장식 3규칙(WARN)이 정적 절반을 잡는다.

## 5. 반도체 현장 화면 관례
REFERENCE.md 1절 아래 표로 옮겼다(설비 5상태·지표 순서·로트 표·SPC·알람, 일반 도메인 지식이라 검토 필요).

## 6. 그림: 초안 → 최종
- 초안: `<figure class="figure" data-ratio="16/9"><figcaption>어떤 그림: 주제, 2색 라인</figcaption></figure>`(비율 16/9·4/3·1/1·3/1). 그림 계획 표(번호·위치·비율·주제·상태)는 매핑 표와 같은 곳에.
- 최종: `<figure class="figure is-final"><img src="img/21-name.png" alt="무엇을 보여주나"></figure>`(생성) 또는 키트 세트를 `static/img/` 로 복사한 `img/NN-name.svg`. 1색 svg 를 브랜드색으로 칠할 때는 mask 변형(illustrations/README.md).
- 교체 순서: (a) 과제 전용 생성 그림(아래 조건) → (b) illustrations/ 세트(파일이 있을 때) → (c) 데이터 그림(스파크라인·미니 맵) → (d) 틴트 면+아이콘. 그림이 없어도 완성(`.figure` → `.empty` 또는 (d)).
- 그림 생성 조건(시안은 2절): 사전 체험 1장 성공 · CP2 freeze 뒤 · 과제 전용 3장 이하 · PROMPTS.md 과제 전용 틀 · 기록(모델·날짜·프롬프트 번호)은 PROMPTS.md 표에 1줄.
- 마무리: `python3 design-kit/ui_check.py <URL> --final` → 초안 0 → HUMAN_CHECK.

## 7. HUMAN_CHECK 4질문 + 390px
1. 첫 화면에 핵심 1개가 보이나(stat 행·미확인 알림 / 모바일은 큰 숫자 1 + 목록 첫 2행)?
2. 제목 단계(h1 20 → h2 16 → h3 14)가 눈으로 구분되나?
3. 상태가 색+글자로 함께 있나(배지 글자·좌측 띠·범례)?
4. 가로 스크롤이 없나(표는 `.table-wrap` 안에서만)?
390px: split·패널 1열 / 터치 타깃 36px 이상(앱 44px) / 하단 탭이 내용을 가리지 않음 / 그림 자리 비율 유지. 결과 `HUMAN_CHECK PASS HH:MM` 는 B_web.md ⑤(단일 세션은 DECISIONS 6).

## 캡처 (Codex 가 헤드리스로 직접 — 보이는 창·마우스·키보드 없음)
```bash
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser || ls /opt/ms-playwright/chromium*/chrome-linux/chrome 2>/dev/null | head -1)
mkdir -p screenshots .tmp/chrome
"$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir=.tmp/chrome --window-size=1280,900 --screenshot=screenshots/desktop.png "http://127.0.0.1:$PORT/"
"$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir=.tmp/chrome --window-size=390,844  --screenshot=screenshots/mobile.png  "http://127.0.0.1:$PORT/"
```
- 크롬이 없으면 `NOT_RUN` + HUMAN_CHECK(사람이 미리보기에서 1280·390). 프로필·캐시는 `.tmp/chrome` 에만(out/debug 금지).
- 찍은 그림은 Codex 가 열어 보고 가로 스크롤·겹침·빈 박스를 확인해 verify.json 에 `screenshots: PASS|NOT_RUN`. 시안 캡처는 창 1280,800 · 저장 `static/draft/sian_N.png`.
