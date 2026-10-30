# short-term-project-harness

Working rules, templates, skills, and verification scripts for short, time-boxed coding tasks with [Codex CLI](https://github.com/openai/codex). Python 3.9+ standard library only.

## Contents

| Path | Description |
|---|---|
| `AGENTS.md` | Working rules for Codex |
| `TASK.md` `PLAN.md` `DECISIONS.md` `HANDOFF.md` | Task contract, plan, decision log, and handoff templates |
| `RUN.md` | Time-boxed run sheet and checklists |
| `decisions/` | Pending decisions and answers |
| `.agents/skills/` | Codex skills (14) |
| `scripts/` | Preflight, contract check, next-step hints, decision form, flow report, and helpers |
| `design-kit/` | CSS tokens, components, page templates, and a UI checker |
| `docs/` | Prompt examples and guides |
| `tests/` | Test template and tests for the scripts |

## Usage

```bash
git clone https://github.com/lsy2140/short-term-project-harness.git
cd short-term-project-harness
cp AGENTS.md TASK.md DECISIONS.md PLAN.md RUN.md HANDOFF.md /path/to/project/
cp -r .agents scripts tests docs design-kit decisions /path/to/project/
```

Then start `codex` in the project folder. Delete skills you do not need to save tokens. The `archify` skill requires Node.js 18+.

```bash
python3 scripts/recon.py        # check the environment
python3 scripts/next.py         # current phase and next steps
python3 -m unittest             # run tests
python3 scripts/preflight.py    # final checks (exit 0 = pass)
```

## License

[MIT](LICENSE). Third-party components are licensed under their own terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
