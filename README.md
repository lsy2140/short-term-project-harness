# short-term-project-harness

Working rules, templates, skills, and verification scripts for short, time-boxed coding tasks with [Codex CLI](https://github.com/openai/codex). Python 3.9+ standard library only. The scripts report state; none of them acts on elapsed time.

## Contents

| Path | Description |
|---|---|
| `AGENTS.md` | Working rules for Codex (loaded automatically) |
| `PRD.md` | Requirements document, the single source of requirements (IDs for goals, features, business rules, assumptions) and the submission checklist (section 11): drafted by `$kickoff` and `$prd`, approved by the human, later changes logged in its section 10 |
| `TASK.md` `PLAN.md` `DECISIONS.md` `HANDOFF.md` | Templates: status board (goal, checks, questions, done criteria), plan with the task table and the hand-off table (section 4-2: when one agent finishes a task, who picks up what), decision log, handoff |
| `RUN.md` | Run card for the human operator, with a short glossary (scripts do not read it) |
| `decisions/` | Pending decisions (`pending.md`) and answers (`answers.md`) |
| `work/` | Multi-agent folder: ownership rules, the output contract between the core and web agents, agent file template |
| `.agents/skills/` | Codex skills (6): `kickoff`, `prd`, `plan`, `rule-loop`, `web-ui`, `verify-agent` |
| `scripts/` | 11 scripts: `status.py` (one-line status), `wait_signal.py` (waits for hand-off signals), `preflight.py`, `check_contract.py`, `debug_dir.py`, `decide.py` (decision form), `scaffold.py`, `docmap.py`, `smoke_web.py`, `eda_bootstrap.py`, `make_edge_cases.py`; their tests are in `scripts/tests/` |
| `design-kit/` | Design tokens, components, icons, page templates, layout references, and a UI checker |
| `design-kit/refs/` | Reference DESIGN.md files copied as-is from awesome-design-md (MIT) and ko-design-md (CC BY 4.0), with `INDEX.md` and `pick.py` to shortlist 2-3 for a service type |
| `docs/` | Stakeholder interview categories, review prompt, implementation summary guide, 26 example prompts |
| `tests/` | Test template for task code |

## Usage

```bash
git clone https://github.com/lsy2140/short-term-project-harness.git
cd short-term-project-harness
cp AGENTS.md PRD.md TASK.md DECISIONS.md PLAN.md RUN.md HANDOFF.md /path/to/project/
cp -r .agents scripts tests docs design-kit decisions work /path/to/project/
```

Then start `codex` in the project folder and send `$kickoff`. Once the stakeholder has answered, send `$prd`, review `PRD.md` and approve it before `$plan`.
- Codex starts servers itself in the background and reports the port in one line; you type that port into the preview tab. Ports: app 8000 (web agent; the single agent in one-session mode), temporary checks 8100+, decision form 8010 (you start it at checkpoints). No visible browser windows, mouse or keyboard automation; screenshots are headless.
- Only the human runs `python3 scripts/preflight.py --freeze`.
- Agents are opened by the human, one terminal each (`A_core`, `B_web`, `C_verify`). Each reads its own `work/agents/<name>.md`. Only `A_core` may spawn subagents, and only for a bundle (`묶음 Pn` in PLAN section 4) of 2-3 independent tasks run in one turn (rules in `work/README.md` 8); `B_web`, `C_verify` and forks never.
- `$plan` also writes the hand-off table (PLAN section 4-2). Agents pick hand-offs and numbered requests (`@A C1:`) up themselves with `scripts/wait_signal.py` (checked at the end of every task, polled every 30 s while idle). You relay one by hand only when `status.py` keeps showing `연결 대기` or `요청 대기`.
- Web tasks: `$web-ui 시안` shortlists 5 reference DESIGN.md files, makes one mock-up per candidate (an image if image generation works, otherwise an HTML page), each with a different layout (5 layout types) and 1-2 illustration slots, and waits. You answer `시안 N 선택` (pick N) or `시안 생략` (keep the kit tokens); it writes `design-kit/DESIGN_과제.md` and moves the other 4 mock-ups to `.tmp/draft/`, then `$web-ui 초안` builds the first page from the kit templates and `$web-ui 최종` adds the final figures (at most 5, generated with the built-in image tool) after the freeze. Screenshots are taken at desktop/tablet/mobile widths (1280/834/390).
- For an independent review, open `codex -s read-only` and paste the prompt from `docs/judge_simulation.md`.

```bash
python3 scripts/preflight.py --env                     # Python version and available tools
python3 scripts/scaffold.py --stages clean,rules       # thin run.py + one module per stage
python3 scripts/status.py                              # one-line status, ends with the PRD version (display only)
python3 scripts/decide.py --port 8010                  # decision form (you start it at checkpoints)
python3 scripts/decide.py --apply                      # copy hand-written answers.md lines into pending.md
python3 -m unittest                                    # task tests
python3 -m unittest discover -s scripts/tests          # harness tool tests
python3 scripts/docmap.py --check                      # every function has a docstring with inputs and outputs
python3 scripts/preflight.py                           # final checks (exit 0 = pass)
```

## License

[MIT](LICENSE). Third-party components are licensed under their own terms; see the Third-party notices section in [LICENSE](LICENSE).
