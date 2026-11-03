# 결정 답변 (answers) — 사람이 쓰고 Codex 가 task 끝·CP 에서 읽는다
형식: `D07: A (메모: …) @HH:MM` 한 줄 = 답 하나 (복수 ID `D12,D71: A (메모: …) @HH:MM` 는 각 ID 에 같은 답, 기타를 고르면 `D07: C (기타: 내용) (메모: …) @HH:MM`). decide.py 가 append 하고 손으로 써도 된다. 손으로 쓴 줄은 `decide.py --apply` 로 pending 의 고른 후보에 `[x]` 를 옮기고, Codex 는 반영한 뒤 그 후보 줄을 `- [x] A. … 반영 HH:MM` 으로 바꾼다(별도 줄 금지).
