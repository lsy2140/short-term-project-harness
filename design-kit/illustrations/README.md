# illustrations/ — 생성 그림의 폴백 세트 (그림 파일은 사람이 넣는다)

- 용도: 과제 전용 생성 그림(1순위, 5장 이하, 틀은 PROMPTS.md 과제 전용 틀)이 안 되거나 5장을 넘는 자리의 `.figure` 최종 교체 폴백. 로컬 파일로만 쓴다(외부 URL 금지, 이 폴더는 허용).
- 현재: 그림 파일 없음. 시험 전에 PROMPTS.md 로 생성 → SVG 변환(vtracer·potrace) → 이 폴더에 넣는다. 확인: `ls design-kit/illustrations/*.svg`(15장).
- 그림이 없어도 화면은 완성된다: `.empty`(글자) 또는 틴트 면+아이콘(`.ico-tile`).

## 15장 목록 (번호·파일명 고정)
| # | 파일명 | 주제 | 비율 | 쓰는 곳 |
|---|---|---|---|---|
| 01 | 01-empty.svg | 빈 결과: 빈 상자와 돋보기 | 1/1 | 검색 0건, `.empty` |
| 02 | 02-no-alerts.svg | 알림 없음: 조용한 종 | 1/1 | 알림 패널 빈 상태 |
| 03 | 03-done.svg | 완료: 체크된 목록 | 1/1 | 모바일 완료, 제출 완료 |
| 04 | 04-offline.svg | 오류·연결 끊김: 끊긴 케이블 | 1/1 | 실패 배너 아래 |
| 05 | 05-upload.svg | 업로드: 서류가 상자로 | 4/3 | 파일 등록 빈 상태 |
| 06 | 06-schedule.svg | 일정: 달력과 시계 | 4/3 | 일정·교대 화면 |
| 07 | 07-report.svg | 보고서: 막대 차트가 있는 문서 | 4/3 | 보고서·내보내기 |
| 08 | 08-team.svg | 팀: 작업자 3명 | 4/3 | 담당자·권한 |
| 09 | 09-wafer.svg | 웨이퍼: 다이 격자 원판 | 1/1 | 수율·검사 |
| 10 | 10-line.svg | 설비 라인: 장비 3대와 이송 | 3/1 | 현황판 띠, 홈 |
| 11 | 11-inspection.svg | 검사: 돋보기 아래 웨이퍼 | 4/3 | 검사·불량 |
| 12 | 12-dashboard.svg | 대시보드 추상: 패널 4개 | 16/9 | 홈 기능 소개 |
| 13 | 13-shift.svg | 교대 작업자: 방진복 2명 인수인계 | 4/3 | 인수인계·교대 |
| 14 | 14-maintenance.svg | 점검: 공구와 설비 패널 | 4/3 | PM·점검 |
| 15 | 15-hero.svg | 히어로: 라인 + 웨이퍼 + 작업자 1명 | 4/3 | 홈 히어로 |

## 파일명·형식 규칙
- `NN-영문소문자.svg`(우선) 또는 `NN-영문소문자.png`. 1~15 는 위 표 고정(이 폴더), 과제 전용 생성 그림은 `21-` 부터(`static/img/` 에 두고 아래 생성 PNG 규칙).
- 세트 크기 상한(이 폴더): SVG 60KB/장(경로 단순화), PNG 120KB/장(긴 변 1200px 이하), 폴더 합계 2MB.
- 과제 전용 생성 PNG(`static/img/21-*.png`, 시험 중 생성): 긴 변 1024px 이하 · 장당 500KB 이하 · `static/img/` 합계 3MB 이하(넘으면 Python 으로 축소하거나 장수를 줄인다).
- 2색 플랫: 브랜드 계열 1색 + 연한 면 1색, 투명 배경, 글자·로고·그라디언트 없음.
- SVG 안에 외부 참조·script·글꼴 금지. viewBox 는 남기고 width·height 속성은 지운다.
- 넣은 뒤: PROMPTS.md 의 생성 기록 표를 채우고, LICENSE 의 Third-party notices 절에 생성 그림 1줄(모델·날짜)을 더한다.

## 쓰는 법
- img(`static/img/` 로 복사한 뒤): `<figure class="figure is-final" data-ratio="1/1"><img src="img/01-empty.svg" alt="빈 결과"></figure>`
- 경로는 페이지 기준 상대 경로. templates/ 안에서는 `../illustrations/01-empty.svg`.
- mask(1색 SVG 를 브랜드색으로 칠하기): `<figure class="figure is-final mask" data-ratio="1/1" style="--mask: url(/img/09-wafer.svg)"><i></i></figure>`
  - 그림의 칠해진 부분이 `--brand` 색, 바탕이 `--brand-soft` 가 된다. 브랜드를 바꾸면 그림 색도 따라간다.
  - mask 의 url 은 `/` 로 시작하는 경로를 쓴다(CSS 변수 안 상대 경로는 기준 위치가 브라우저마다 다를 수 있음). 예는 static/ 을 `/` 로 서빙할 때의 경로다. 같은 서버에서만 보인다.
- 확인: `python3 design-kit/ui_check.py <URL> --final` (img·svg 가 없는 `.figure` 가 남으면 FAIL, mask 변형은 style 의 url 이 있으면 최종으로 본다).
