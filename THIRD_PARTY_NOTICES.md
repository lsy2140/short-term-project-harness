# Third-Party Notices

이 저장소에서 **직접 작성한 부분**(문서·스크립트·테스트·design-kit·대부분의 스킬)은 루트 [`LICENSE`](LICENSE)(MIT)를 따른다.
아래 구성요소는 외부 저작물이거나 외부 저작물을 바탕으로 만든 것이며 **각자의 라이선스를 따른다**. 해당 폴더의 라이선스 파일이 이 문서보다 우선한다.
Apache License 2.0 전문은 [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt)에 있다.

| 구성요소 | 경로 | 출처(확인한 커밋) | 라이선스 | 이 저장소에서 한 일 | 라이선스·고지 파일 |
|---|---|---|---|---|---|
| Archify | `.agents/skills/archify/` | https://github.com/tt-a1i/archify (`d6059331`, v3.2.0) | Apache-2.0 (일부 과거 기여는 MIT 유지 — 폴더의 NOTICE 참조) | 축약 복사 + 일부 수정 | 폴더의 `LICENSE`, `LICENSE-MIT`, `NOTICE`, `THIRD_PARTY_NOTICES.md`, 변경 내역 `MODIFICATIONS.md` |
| Archify 번들: Pele 1.3.0 | `.agents/skills/archify/explainer/vendor/pele/` | https://github.com/obsidianmd/pele | 폴더의 LICENSE | Archify 에 포함된 그대로 | `explainer/vendor/pele/LICENSE` |
| theme-factory 테마 10종 | `.agents/skills/web-ui-build/references/themes/` | https://github.com/anthropics/skills (`dbd4588f`, `skills/theme-factory/themes/`) · Copyright 2026 Anthropic, PBC | Apache-2.0 | 원문 복사(줄바꿈 CRLF→LF 만 변경) | `.agents/skills/web-ui-build/references/LICENSE.txt` |
| with_server.py | `scripts/with_server.py` | https://github.com/anthropics/skills (`dbd4588f`, `skills/webapp-testing/scripts/with_server.py`) · Copyright 2026 Anthropic, PBC | Apache-2.0 | 수정·축약(단일 서버, PORT 환경변수, Windows 프로세스 트리 정리) — 파일 머리에 변경 고지 | `LICENSES/Apache-2.0.txt` |
| Hallmark "The Floor" 등 | `.agents/skills/ui-audit/references/hallmark-floor.md` | https://github.com/Nutlope/hallmark (`8f6969f8`) · Copyright (c) 2026 Hallmark contributors | MIT | 한국어 번역·요약(원문 미복사) | `.agents/skills/ui-audit/LICENSE.txt` (MIT 전문 포함) |
| Impeccable reference | `.agents/skills/ui-audit/references/impeccable-audit.md` | https://github.com/pbakaus/impeccable (`5e745ace`) · Copyright 2025 Paul Bakaus | Apache-2.0 | 한국어 번역·요약(원문 미복사) — 변경 고지 포함 | `.agents/skills/ui-audit/LICENSE.txt`, `LICENSES/Apache-2.0.txt` |

## 직접 작성했지만 아이디어를 참고한 것 (복사 없음 · MIT)
| 경로 | 참고한 것 | 비고 |
|---|---|---|
| `.agents/skills/task-breakdown/`, `unit-test-starter/`, `debug-loop/`, `codebase-orientation/` | https://github.com/proflead/codex-skills-library (`a05260c8`) 의 스킬 주제·절차 순서 | 원 저장소에 라이선스 표기가 없어(2026-10-28 확인) **문장을 복사하지 않고** 한국어로 새로 작성했다. 각 폴더 `LICENSE.txt` 참조 |
| `.agents/skills/exam-kickoff/` 5단계 | https://github.com/openai/skills `define-goal`(Apache-2.0) 의 목표 점검 질문 | 개념만 참고해 새로 작성 |
| `design-kit/DESIGN.md` 4절(피할 것) | https://github.com/anthropics/skills `frontend-design`(Apache-2.0) 의 기본값 경계 원칙 | 개념만 참고해 새로 작성 |

상표(Linear, Notion, Stripe, Vercel, Toss, Material, Grafana 등)는 `design-kit/DESIGN.md` 의 어휘표에서 디자인 특징을 설명하려고 이름만 언급하며, 각 소유자에게 있다. 이 저장소는 이들과 관련이 없다.
