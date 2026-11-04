# DESIGN.md — 디자인 키트 사용 설명 (1쪽)

- 키트 = 토큰·부품·템플릿 3종·아이콘·그림 자리·참고 md. 외부 URL·CDN·폰트 파일·라이브러리 금지(로컬 `illustrations/`·`icons.svg` 는 허용).
- 순서: REFERENCE.md 유형 1개(출발점) → refs 후보 5 → 시안 5(색 md·배치·그림 자리가 다름) → 사람이 1개 선택 → DESIGN_과제.md → templates/ 복사·tokens.css·배치 → 데이터 매핑 → 그림 자리 초안 → ui_check·스크린샷 3장 → 최종 그림 → `ui_check --final`.

| 파일 | 용도 |
|---|---|
| tokens.css | 색·반경·그림자·간격·서체. 바꾸는 곳은 [브랜드] 4줄과 [중립] 바탕·패널·잉크뿐 |
| base.css | reset·글자 5단·레이아웃(container·split·cols-3)·반응형 3구간(≥1025 / 641–1024 / ≤640) |
| components.css | 부품 전부: card·badge·btn·table·banner/empty·stat·spark/hbar·eq·alarm·rows·tabs·seg·form·figure·app |
| kit.js | 공통 함수 K: esc·fmt·hhmm·kv·badge·chips·toast·setStatus·load·spark·hbar |
| kit.html | 부품 견본 + 설정 폼·위험 구역·홈 히어로 블록 |
| templates/ | dashboard(모니터링)·tool(조회·검색)·mobile(현장 앱). data.json fetch, 상태 배너 3종 |
| REFERENCE.md | 화면 유형 5개: 와이어 1280/834/390(출발점)·섹션 순서·문구 톤·그림 자리 |
| refs/ | 참고 DESIGN.md 53개(한국 27·해외 26)·INDEX.md·pick.py·DESIGN_과제 틀 |
| icons.svg | 24px 라인 아이콘 27개, `<use href="icons.svg#i-bell"/>` |
| illustrations/ | 그림 폴백 세트 자리(README)·생성 프롬프트(PROMPTS: 세트·과제 전용·시안 틀+배치 5종) |
| serve.py / ui_check.py | 정적 서버(Codex 가 띄우고 포트 보고) / 정적 점검(구조·접근성·토큰·그림·장식·외부·대비) |

## 1. 사용 절차 (과제 폴더에서)
1. 유형·디자인: REFERENCE.md 유형 1개(섞이면 주 화면만) + DESIGN_과제.md(2절).
2. 복사: 템플릿 + tokens/base/components.css·kit.js·icons.svg → 정적 폴더, `../` 삭제(틀리면 ui_check `local asset` FAIL). 복사한 tokens.css 에 DESIGN_과제.md 2절 색. 배치는 1-1 표대로(와이어와 달라도 시안을 따른다).
3. 매핑: `K.load('<API 또는 json>', 내장샘플)` → render 함수. 매핑 표는 B_web.md ⑤(단일 세션은 DECISIONS 1).
4. 상태: 배너 3종(실데이터·내장 샘플·실패) 유지. 빈 결과는 `.empty`(무엇이 없나 + 다음 행동). 확인 `?state=fallback|failed`.
5. 점검: B 가 서버를 띄우고 포트 보고 뒤 `python3 design-kit/ui_check.py http://127.0.0.1:<PORT>/` FAIL 0, 스크린샷 3장(캡처 절), 834·390px 1회.

## 2. 참고 md·시안 5개 (`$web-ui 시안` — 사람이 1개 고른 뒤 본 화면)
- 흐름: 유형 → `python3 design-kit/refs/pick.py <유형|키워드>` 후보 5 → 시안 N = md N + 배치 N(PROMPTS.md 5종, 서로 다르게) + 그림 자리 1~2(일러스트가 그려진 상태) → 1줄씩 보고 → 사람이 번호 1개 → `design-kit/DESIGN_과제.md`(틀 `refs/_DESIGN_과제.template.md`) → 1절.
- 필수 블록(PRD 4·5 화면 요구)은 5개 모두에, 배치·그림 자리·강조 방식은 시안마다 다르게. 색만 다른 5장은 다시 만든다.
- 시안: 생성 도구가 있으면 1280×800 PNG `static/draft/sian_N.png`, 없으면 토큰+배치 CSS 1줄을 입힌 `static/draft/sian_N.html` + 캡처. 틀·배치 표·명령은 `illustrations/PROMPTS.md` 시안 절.
- 보고: `시안 N · refs/<md> · 배치 <이름> · 분위기 3단어 · 그림 자리 <위치> · <미리보기 경로>`. 고를 때까지 본 화면은 안 만든다(서버·API·매핑 표는 된다). 사람은 `시안 N 선택`(바꿀 점 `색/배치/그림은 시안 M 것`), `시안 생략` 이면 키트 기본 토큰·와이어.
- 고른 뒤: 고른 시안만 `static/draft/` 에, 나머지 4장은 `.tmp/draft/`(비교 근거는 DESIGN_과제.md 0절 다른 후보 1~4).
- 옮기는 것: 색·서체 느낌·간격·반경·분위기만(로고·이름·폰트 파일·문구 원문은 안 옮긴다). hex 는 `static/tokens.css` [브랜드]·[중립]에만, 상태색 5쌍 고정 → contrast PASS(4.5:1).
- 라이선스: ko = CC BY 4.0, awesome = MIT(LICENSE Third-party notices 3·4). 고른 md 출처 1줄 → DESIGN_과제.md 0절·README 실제 vs 목업 표.

## 3. Codex 지시 틀 (`$web-ui 시안` / `초안` / `최종`)
```
목표: <화면 1개> (PRD 4·5 요구) · 유형 REFERENCE <번호> · 디자인 DESIGN_과제.md(시안 <N> · 배치 <이름>)
범위: <API/파일> → render 매핑만. 새 화면·새 기능 없음
제약: tokens.css 변수만(raw hex·외부 URL·라이브러리 0), 상태색 고정, 진입 애니메이션 없음, 834 2열·390 1열, K.esc,
      그림 자리는 .figure 초안(DESIGN_과제.md 9절), 서버는 네가 백그라운드로 띄우고 포트 보고
완료: ui_check FAIL 0 · smoke_web PASS · 스크린샷 3장 · 매핑 표 B_web.md ⑤ · 피할 것 = 4절
```

## 4. 피할 것 (AI 생성 티)
같은 카드 반복·KPI 4칸 공식 / 점-pill 배지·pill 버튼 남발 / 섹션마다 세로 바+설명줄(`.why`) / 도구 화면의 큰 제목+리드 / 광원·글래스·이중 베젤 / 크림+세리프+테라코타, 흑색+형광 1색 / 제목 위 대문자 라벨(`.eyebrow` 는 홈 히어로 1곳) / 띄어쓴 가운뎃점 메타 / 버튼 꼬리 화살표 / 진입 fade-up / 장식용 01·02 번호 / 헤드라인 한 단어 색 강조 / 기계 문자열 노출(ISO 시각·내부 키) / 축 없는 막대 / 임시 문구 / 단색 히어로+추상 블롭 / 반경 여러 종.
**그림 0장·글자 블록 대체가 가장 큰 티** → `.figure` 자리를 남기고 최종에 그림(생성 5장 이하), 없으면 틴트 면+아이콘(`.ico-tile`)이나 데이터 그림.
비평·수정 기준은 `$web-ui 최종` ⑥-3(`.agents/skills/web-ui/references/`). ui_check 의 Floor 5규칙·장식 3규칙(WARN)이 정적 절반을 잡는다.

## 5. 현장 관례
REFERENCE.md 1절 표(설비 5상태·지표·로트·SPC·알람, 검토 필요).

## 6. 그림: 초안 → 최종
- 초안: `<figure class="figure" data-ratio="16/9"><figcaption>어떤 그림: 주제, 2색 라인</figcaption></figure>`(비율 21/9·16/9·4/3·1/1·3/1). 자리는 고른 시안대로, 그림 계획 표(번호·위치·비율·주제·스타일·상태)는 DESIGN_과제.md 9절(B_web.md ⑤ 는 상태만).
- 최종: `<figure class="figure is-final"><img src="img/21-name.png" alt="무엇을 보여주나"></figure>`(생성) 또는 `static/img/` 로 복사한 키트 세트 `img/NN-name.svg`(브랜드색 칠하기는 mask 변형, illustrations/README.md).
- 교체 순서: (a) 과제 전용 생성 그림 → (b) illustrations/ 세트 → (c) 데이터 그림(스파크라인·미니 맵) → (d) 틴트 면+아이콘. 그림이 없어도 완성(`.figure` → `.empty` 또는 (d)).
- 생성 조건: 5장 이하 · PROMPTS.md 과제 전용 틀 · 색은 DESIGN_과제.md 2절 `--brand`·`--brand-soft` · 긴 변 1024·장당 500KB·`static/img/` 합계 3MB · 기록은 PROMPTS.md 표 1줄. 화면 교체는 CP2 freeze 뒤, 연결 신호 대기 중에 미리 생성해 `static/img/` 에 두는 것은 된다.
- 마무리: `ui_check.py <URL> --final` → 초안 0 → 스크린샷 3장 → HUMAN_CHECK.

## 7. HUMAN_CHECK 4질문 + 834·390px
1. 첫 화면에 핵심 1개가 보이나(stat 행·미확인 알림 / 모바일은 큰 숫자 1 + 목록 첫 2행)?
2. 제목 단계(h1 20 → h2 16 → h3 14)가 눈으로 구분되나?
3. 상태가 색+글자로 함께 있나(배지 글자·좌측 띠·범례)?
4. 가로 스크롤이 없나(표는 `.table-wrap` 안에서만)?
834px: 2열 그리드 유지 / split 이 접히면 상세가 목록 아래 / 터치 타깃 36px. 390px: 1열 / 터치 타깃 36px(앱 44px) / 하단 탭이 내용을 안 가림 / 그림 비율 유지. 결과 `HUMAN_CHECK PASS HH:MM (1280·834·390)` 는 B_web.md ⑤(단일 세션은 DECISIONS 6).

## 캡처 (Codex 가 헤드리스로 직접 — 보이는 창·마우스·키보드 없음)
```bash
CHROME=$(command -v google-chrome || command -v chromium || command -v chromium-browser || ls /opt/ms-playwright/chromium*/chrome-linux/chrome 2>/dev/null | head -1)
mkdir -p screenshots .tmp/chrome
for V in "1280,900 desktop" "834,1194 tablet" "390,844 mobile"; do set -- $V
  "$CHROME" --headless=new --disable-gpu --no-sandbox --user-data-dir=.tmp/chrome --window-size=$1 --screenshot=screenshots/$2.png "http://127.0.0.1:$PORT/"
done
```
- 결과 `screenshots/desktop.png·tablet.png·mobile.png`. 크롬이 없으면 `NOT_RUN` + HUMAN_CHECK(사람이 미리보기에서 1280·834·390). 캐시는 `.tmp/chrome` 에만.
- 3장을 Codex 가 열어 가로 스크롤·겹침·빈 박스를 확인 → verify.json `screenshots: PASS|NOT_RUN`(PASS = 3장 다 있음). 시안 캡처는 창 1280,800 · `static/draft/sian_N.png`.
