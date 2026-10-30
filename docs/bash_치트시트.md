# bash 치트시트 (웹 IDE 터미널 · Linux)

이전 참가 후기: "생소한 IDE와 bash 터미널 때문에 고생". 사전 체험 15분에 아래를 한 번씩 쳐 본다.

## 둘러보기
```bash
pwd; ls -la; ls -la data/            # 위치·파일·크기
find . -maxdepth 2 -type f | grep -v '/.git/' | sort     # 깊이 2 파일 목록
wc -l data/*.csv                     # 행 수
head -5 data/a.csv; tail -3 data/a.csv
grep -c "" data/a.csv                # 줄 수(빈 줄 포함)
grep -n "NA\|null" data/a.csv | head # 결측 표기 찾기
cut -d, -f3 data/a.csv | sort | uniq -c | sort -rn | head   # 3번째 열 빈도
python3 -V; which python3 pip3; pip3 list 2>/dev/null | head -20
```

## 파이썬·테스트
```bash
python3 scripts/eda_bootstrap.py data/*.csv --out eda_summary.md
python3 -m unittest -v               # tests/ 패키지(tests/__init__.py 필요)
python3 -m unittest tests.test_rules -v
python3 scripts/preflight.py --require out/result.csv README.md PLAN.md; echo "exit=$?"
PYTHONIOENCODING=utf-8 python3 main.py   # 한글 출력 깨지면
pip3 install --user <pkg>            # 설치는 승인 필요할 수 있음, 묶어서 1회
```

## 서버 (미리보기)
```bash
PORT=8000 python3 app.py             # 0.0.0.0 바인딩, 별도 터미널(분할)에서 유지
curl -s http://localhost:8000/orders | head -c 300; echo
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
ps aux | grep -v grep | grep app.py  # 떠 있나
kill %1  또는  pkill -f app.py       # 종료
```

## 기록 (시험장은 git clone 만 허용, 커밋 없음)
```bash
python3 scripts/debug_dir.py 01_첫완주        # out/debug/01_첫완주/ 생성(red.txt·green.txt·verify.json·decisions.txt·note.md 5파일까지)
python3 scripts/debug_dir.py --check          # 총 40파일·금지 패턴(*_before, chrome_profile, 입력 복사본) 검사
python3 scripts/preflight.py --freeze         # 110분 1차 동결: .tmp/freeze_1/ 복구본 + tests/ 해시 (1회)
python3 scripts/preflight.py --check-freeze   # 1차 동결 이후 tests/ 변경 여부
```

## 하네스 반입
```bash
git clone https://github.com/<계정>/short-term-project-harness.git
cp short-term-project-harness/{AGENTS.md,TASK.md,DECISIONS.md,PLAN.md,RUN.md,HANDOFF.md} .
cp -r short-term-project-harness/{.agents,scripts,tests,docs,design-kit,decisions} .
rm -rf short-term-project-harness            # 제출물에 섞이지 않게
node -v && node .agents/skills/archify/bin/archify.mjs doctor   # 사전 체험 ⑧: Node ≥18 이고 doctor OK 면 $archify, 실패하면 rm -r .agents/skills/archify (도식은 flowmap 만)
codex                                # /status 로 모델·승인 모드 확인
```

## 자주 쓰는 키
`Ctrl+C` 중단 · `Ctrl+L` 화면 지움 · `↑` 이전 명령 · `Tab` 자동완성 · `Ctrl+R` 명령 검색 · `q` less 종료
