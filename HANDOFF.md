# HANDOFF — 인수인계 (동결 뒤)
<!-- 동결 선언 뒤 쓴다. 항목당 3줄 이내, 모든 주장에 근거(파일:줄·테스트·명령).
요구사항·가정은 PRD ID(R·B·A), 결정은 DECISIONS 1 ID 로 가리킨다 -->

## 1. 지금 상태
- 돌아가는 것(한 문장):
- 테스트 __/__ PASS · preflight exit __ · check_contract exit __ · 출력 __행
- debug __폴더(`debug_dir.py --check` exit __) · 동결 복구본 `.tmp/freeze_N/` · `--check-freeze` tests 변경 __건 · 저장 __:__
- 제출물: PRD 11 표대로 · 빠진 것 __개(이유는 5 에)

## 2. 실행 방법
<!-- 실제로 쳐 본 명령만 -->
```bash
python3 <진입점> ...
python3 -m unittest -v                        # __ run / __ fail
python3 scripts/preflight.py --require ...    # exit __
PORT=8000 python3 app.py                      # 웹 과제(0.0.0.0), Codex 가 백그라운드로 띄우고 포트 보고
```

## 3. 구조
| 파일 | 역할 | 테스트(파일·개수·결과) | 고칠 곳 |
|---|---|---|---|
|  |  |  |  |

## 5. 알려진 문제·한계
| 조건 | 증상 | 위치 | 대응안 | 믿지 말 것 |
|---|---|---|---|---|
|  |  |  |  |  |
| 화면 HUMAN_CHECK(사람이 눈으로 확인) | 데스크톱/834/390px 확인 결과(시각) |  |  |  |

## 6. 다음에 할 일
<!-- 중요한 것부터 -->
1. 
2. 
