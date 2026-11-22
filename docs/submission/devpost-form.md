# Devpost submission text: Weakest Link

Paste-ready text for the Relate by Neo4j Hackathon form (https://relate.devpost.com/).
Deadline: Fri 11 Dec 2026, 6:00 PM PST (Sat 12 Dec 2026, 7:30 AM IST).
Status: text ready; live demo hosted; the video is not uploaded yet and nothing is submitted.

## Project name

Weakest Link

## Elevator pitch / tagline (140 characters max)

Will your laptop reach that projector at 4K60? A Relate graph of ports, adapters and cables names the weakest link in your bag.

(127 characters)

## About the project

### Inspiration

Most of us have seen it: five minutes before a talk, the laptop goes into the venue's HDMI and the
4K projector shows a blurry 1080p at 30 Hz, or nothing. The laptop is almost never the problem.
One link in the chain is: a hub that only does HDMI 1.4, a 240 W USB-C cable that is USB 2.0 inside
and carries no video, a passive DP-to-HDMI adapter on a port without DP++, or the venue's old
Standard HDMI cable taped to the floor. Spec sheets answer one item at a time. The question people
actually have is about the whole chain, and that is a graph question.

### What it does

You pick your laptop (or phone or tablet), tick what is in your bag, choose a venue or describe a
display, and pick the picture you want (720p up to 4K60). Weakest Link answers:

- **Will it connect?** A yes or no for your exact bag and venue, with a chain diagram. Every hop
  shows its capacity, a confidence level and a link to its public source, and the hop with the
  lowest capacity is highlighted as the weakest link.
- **Best purchase.** Across all the venues you visit, the single item that fixes the most of them.
  When the venue's own display is the limit, it says so instead of suggesting a purchase.
- **Charging.** The same graph in watts: charger → cable → laptop, and the cable or charger to buy
  if it won't fast-charge.
- **Strict mode.** One switch ignores links whose source only confirms the feature and not its
  speed, for when a wrong "yes" is not an option.
- **"Pack my bag" agent.** Through Relate's MCP server, any MCP host (Claude Desktop, Cursor,
  VS Code, Claude Code) can read a venue's AV email or an adapter's spec page, write it into its own
  copy of the graph with a source and confidence, run the vetted query recipes stored in the graph,
  and answer: pack this, leave that, buy one thing.

What connects to what: laptops and adapters have `Port`s; plugs `MATES` sockets; each item carries
`VIDEO` (Gbps) and `POWER` (watts) through itself; panels `SUPPORTS_MODE`; venues `PROVIDES` their
cables and displays; every capability edge `CITES` a `Source`.

### How we built it

- **Data:** 100 items (19 laptops, 7 phones, 4 tablets, 18 adapters/hubs/docks, 21 cables,
  16 chargers, 15 monitors/TVs/projectors), 208 ports, 16 standards, 5 video modes, 9 venues and
  64 public sources, hand-written as cited JSON in `data/src/`. Every edge was audited against its
  source; the audit table is in `docs/DATA.md`. The built store has 499 nodes and 7,958
  relationships.
- **Relate store:** `scripts/build_store.py` builds a single-file store, `data/weakest-link.rl`,
  with the `relate` CLI (v1.0.1). It is committed so judges can open it with `--read-only`.
- **Queries:** five Cypher files in `queries/` (`reach`, `chains`, `best_fix`, `power`,
  `charge_fix`). "Does my bag reach this TV at 4K60?" is one quantified path pattern with inline
  predicates on every hop, restricted to items you own or the venue provides; `reduce()` over the
  path's relationships picks the bottleneck hop. Strict mode is one `$strict` parameter.
- **Browser:** a static Vite site that loads the same graph and the same query files into
  `@relate/relate-wasm`. No server, no API key. A parity test checks that CLI and WASM return the
  same rows. A display you describe is written into the in-browser graph as real nodes, so the same
  queries apply to it.
- **Agent:** `scripts/mcp_server.py` runs `relate serve --mcp` twice: a read-only catalog
  (`get_schema`, `read_cypher`) and a writable "my bag" copy that adds `write_cypher`. The vetted
  queries and two single-statement ingest recipes live in the graph as `:Recipe` nodes, so the model
  discovers them and fills in parameters instead of writing Cypher. `scripts/agent_demo.py` drives
  the whole flow offline, with no model, for judges and CI.
- **Tests:** 80 Python tests (30 query, 26 catalog-trap and audit, 24 agent/MCP flow), 19
  Playwright browser tests on desktop and mobile with axe accessibility checks, and the CLI/WASM
  parity test.

### Challenges we ran into

- **Spec accuracy.** Marketing pages often say "4K" without saying 30 or 60 Hz. We kept every edge
  to documented limits, gave each a confidence level, downgraded edges whose source only confirmed
  the feature, and added strict mode so users can exclude them.
- **Bottlenecks in Cypher.** Finding the weakest hop needed variable-length paths where every hop
  has its own predicate, plus a `reduce()` over relationships. We wrote `best_fix` without `CALL`
  so the MCP `read_cypher` tool accepts it.
- **Same answer everywhere.** The CLI, the WASM build in the browser and the MCP server had to give
  identical results from one store, so we load all three from the same import script and query
  files and test parity.
- **Safe agent writes.** An agent that ingests emails should not be able to change the shared
  catalog. The catalog is served read-only, and writes go to a separate copy through two fixed
  ingest recipes.

### Accomplishments that we're proud of

- One cited, audited single-file graph that answers real "will it work" questions in under a second,
  in a terminal, in a browser tab and through an AI assistant.
- Every answer names a specific item and links its source, so a user can check it.
- `best_fix` says when nothing you can buy will help, rather than always recommending something.
- The agent works with no paid API and no key; the offline demo runs in about two seconds.

### What we learned

Compatibility is a relationship problem, not a lookup problem. Modelling "what plugs into what" and
"what each hop carries" as edges turned five different features (connect, best purchase, charging,
strict mode, agent ingest) into small variations of one path query. We also learned that putting the
vetted queries in the graph as recipes makes an MCP agent far more reliable than asking it to write
Cypher.

### What's next

- More items and venues, including docks with DSC and 4K120, with community-submitted sources.
- A "venue sheet" page that event organisers can share with speakers.
- Pulling a subgraph from Neo4j or Aura for larger catalogs, through Relate's Neo4j connection.

## Built with

relate, relate-wasm, cypher, mcp, neo4j, python, javascript, vite, webassembly, playwright, axe-core, github

## Try it out links

- Repository: https://github.com/suganthikannan093-hue/weakest-link
- Live demo: https://weakest-link-nu.vercel.app (static build on Vercel; the graph and queries run in the
  browser on Relate WASM, no login, no server). Locally: `npm install && npm run build && npm run preview`.

## Video demo link

To fill after upload: YouTube, Vimeo or Youku URL, public or unlisted, playable without a login.
Source file: `docs/submission/weakest-link-demo-v2.mp4` (1:38, 1920×1080, burned-in captions).

## Image gallery (suggested order)

1. `docs/screenshots/desktop-connect-weakest-link.png`: verdict and chain with the weakest link
2. `docs/screenshots/desktop-best-purchase.png`: best purchase across venues
3. `docs/screenshots/desktop-charging-fix.png`: charging chain and the cable to buy
4. `docs/screenshots/desktop-custom-display.png`: a described display written into the graph
5. `docs/screenshots/mobile-connect.png`: mobile view

## Answers for the rules' required statements (paste into any extra question, or the end of the description)

**Relate mode and why:** single file, `data/weakest-link.rl`. The catalog is shared, read-only
reference data that ships with the repo: one file is easy to commit, review, open `--read-only` and
`--load` from a URL. The browser loads the same graph into Relate WASM in memory; the agent's
writable copy is a separate single file in `data/work/`.

**Relate capabilities used:** `relate` CLI with a single-file store; Cypher quantified path patterns,
`SHORTEST 1`, `reduce()`, `EXISTS {}` and `CALL () {}` subqueries, indexes, `--fetch-params`;
`relate serve --mcp` (read-only and writable stores, `get_schema`, `read_cypher`, `write_cypher`);
`@relate/relate-wasm` in the browser.

**Third-party tools:** Vite, Playwright, axe-core, Python standard library. Dataset facts come from
the 64 public sources listed in `data/src/sources.json`.

**AI tools:** an AI coding agent helped write the build script, queries, web UI, agent, tests and
docs; every spec value was checked against its cited source. The demo video's narration is OpenAI
text-to-speech (`tts-1-hd`) and its captions are timed with OpenAI Whisper. The product itself calls
no AI service: the agent uses whatever model your MCP host already has, or runs offline.

**Earlier code reused:** none. The project was started on 15 Nov 2026, inside the contest period.

**Where the data lives:** `data/weakest-link.rl` (inspect with `relate info -d data/weakest-link.rl`).

## Self-score against the judging criteria (honest estimate)

| Criterion | Points | Estimate | Why | Risk |
|---|---|---|---|---|
| Creativity | 10 | 8–9 | Hardware compatibility as a bottleneck path query is not in the gallery, Relate's ideas list or GitHub (checked 15 Nov). | Judges may see it as a niche utility. |
| Relate and connected context | 30 | 27–29 | The core answer is a graph traversal; one store runs in CLI, WASM and MCP with parity tests; recipes in the graph; read-only vs writable stores. | The hosted demo covers the web UI; the CLI and MCP agent still need a clone and the Relate CLI. |
| Functionality and completeness | 25 | 21–23 | Connect, best purchase, charging, strict mode and agent all work; 80 + 19 tests; fresh-clone check and the full browser suite against the hosted demo passed 23 Nov. | 100 items cannot cover every adapter. |
| Usefulness | 20 | 15–17 | A real, common problem for speakers and teachers, with a named item to buy. | The audience is narrower than general dev tools. |
| Documentation and reproducibility | 15 | 13–14 | README follows the contest template, first result in four commands, offline agent demo. | Needs the Relate CLI installed. |
| **Total** | **100** | **84–92** | | Live demo hosted 23 Nov; 38/38 browser tests pass against it. |
