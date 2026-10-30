# 이 사본에서 바꾼 것 (Apache License 2.0 제4조 (b) 변경 고지)

원본: https://github.com/tt-a1i/archify — 커밋 `d6059331abbddb49bca380ff46dca8ce33158b04`, 스킬 폴더 `archify/` (v3.2.0).
원본의 `LICENSE`, `LICENSE-MIT`, `NOTICE`, `THIRD_PARTY_NOTICES.md` 는 수정하지 않고 그대로 두었다.

| 구분 | 내용 |
|---|---|
| 수정 | `SKILL.md` — frontmatter 아래에 이 키트용 안내 인용 블록(출력 경로·Node 버전·폴백·갱신 확인 끄기)을 추가했고, `description` 끝에 한국어 트리거 어휘를 덧붙였다. 나머지 본문은 원문 그대로다. |
| 수정 | `locales/manifest.json` — 카탈로그 목록을 `en`, `ko` 로 줄였다(등록되지 않은 locale 은 원본 코드가 영어로 폴백한다). |
| 제외 | `examples/` 중 렌더된 HTML·locale 예시 등 — 코드가 참조하거나 SKILL.md 가 읽으라고 지시하는 JSON 21개만 남겼다. |
| 제외 | `locales/` 의 en·ko 외 카탈로그, 개발용 생성 스크립트(`scripts/generate-validators.mjs`, `scripts/generate-brand-marks.mjs` 등 — 번들되지 않은 devDependencies 필요), 패키징·배포 스크립트. |
| 변경 없음 | `bin/`, `renderers/`, `schemas/`, `references/`, `explainer/`, `assets/`, `brand-marks/`, `delta/`, `migrations/`, `recipes/` 의 파일 내용. |

변경일: 2026-10-29. 변경한 부분도 원본과 같은 Apache License 2.0 으로 배포한다.
