# Plan to the deadline

Relate by Neo4j Hackathon. The deadline is **11 Dec 2026, 6:00 PM PST (12 Dec, 7:30 AM IST)**. We
target submitting by 10 Dec IST, which leaves a day of buffer. The repo stays private until the
owner approves submission, then goes public with the topics `relate` and `relate-neo4j-hackathon`.

Judging (from the contest page): Creativity 10, Relate and connected context 30, Functionality and
completeness 25, Usefulness 20, Documentation and reproducibility 15. The rules page also lists equal
weights with "effective use of connected context ... graph, retrieval and agent features". Both are
covered below.

| # | Dates (IST) | Milestone | Done when |
|---|---|---|---|
| 1 | 15 Nov | **Graph and data.** Schema, 46 cited items, build to `.rl` with the CLI, queries `reach`, `chains`, `best_fix` and `power`, 22 tests, WASM parity | ✅ this commit |
| 2 | 16–21 Nov | **Web UI** (static, `@relate/relate-wasm` in the browser). Bag builder (search items), venue picker plus "describe your venue", chain graph view with the weakest link highlighted, a citation and confidence chip on every link, a mode ladder (720p→4K60), charging panel, best-fix card | Runs from `npx serve` with no server, and every number is clickable to its source |
| 3 | 22–27 Nov | **"Pack my bag" agent over MCP.** `relate serve --mcp` on the catalog (`get_schema`, `read_cypher`) plus a writable per-user store for `write_cypher`. Prompts and a skill file: paste a venue tech-requirements email or an adapter spec → the agent writes `Venue`/`Item` nodes with `confidence:'user'` → runs the four queries → answers with what to pack and why. Works in any MCP host, with no paid API in the repo | Scripted demo transcript, plus a test that replays an email through MCP |
| 4 | 28 Nov–2 Dec | **Data depth and accuracy.** Grow to ~80 items: more common laptops, docks, popular named adapters and projectors. Second-source check on every `medium` edge. Add a `best_fix` for charging, more venue scenarios, and a `--strict` mode that excludes low-confidence edges. Model DSC/4K120 only if well documented | Every edge cited, the medium-confidence count goes down, tests still green |
| 5 | 3–6 Dec | **Docs and demo.** README with screenshots and a graph image, architecture diagram, "how the query works" walkthrough. Demo video **≤ 2 min**: problem → bag → weakest link → one fix → agent reads a venue email | Video uploaded unlisted for review, captions checked |
| 6 | 7–9 Dec | **Review and launch prep.** Owner review, make the repo public, add topics, run a fresh-clone check of the README steps, prepare the Devpost draft (description, capabilities and AI-use statement) | Owner approves. Submit only on the owner's go-ahead |

## Risks

- **Spec accuracy** (the main risk). We use only documented limits with conservative timings, and
  every edge carries a source and confidence. Known simplifications are listed in `docs/DATA.md`.
- **Relate is experimental.** We are pinned to 1.0.1 (CLI and WASM). Parity is tested so that a
  regression shows up immediately.
- **Hosting the UI.** GitHub Pages needs a public repo. Until submission we develop locally. The
  hosting choice is the owner's decision.
