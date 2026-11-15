# "Pack my bag" agent over Relate MCP

The agent answers *"what do I pack, and what one thing should I buy?"* for a venue. It can read a
venue's AV email or an adapter's spec page, write what it learns into the graph with its source and
confidence, and then run the same four queries the CLI and the web UI use. It needs no paid API, no
API key and no network: Relate serves the graph over MCP on your machine, and the model is whichever
one your MCP host already has. There is also a deterministic offline demo that needs no model at all.

```
 MCP host (Claude Desktop, Cursor, VS Code, Claude Code …)      offline demo / CI
        │  stdio JSON-RPC                                         scripts/agent_demo.py
        ▼                                                                │
 scripts/mcp_server.py catalog ── relate serve --mcp stdio --read-only ──┤ data/weakest-link.rl (committed, never written)
 scripts/mcp_server.py mybag   ── relate serve --mcp stdio ──────────────┘ data/work/my-bag.rl  (your copy, git-ignored)
                                       read_cypher · write_cypher · get_schema
```

| Server | Store | Tools | Use |
|---|---|---|---|
| `weakest-link-catalog` | `data/weakest-link.rl`, opened `--read-only` | `read_cypher`, `get_schema` | the shared, cited catalog. Writes are impossible (`write_cypher` is not even offered) |
| `weakest-link-mybag` | `data/work/my-bag.rl`, a copy made on first start | `write_cypher`, `read_cypher`, `get_schema` | venues and items you ingest, plus everything in the catalog |

On first start the writable store is copied from the catalog and gets six `:Recipe` nodes: the
vetted read queries (`reach`, `chains`, `best_fix`, `power`) and write statements (`ingest_venue`,
`ingest_item`). Any MCP host can discover them with `read_cypher`, so the model does not have to
write Cypher. It fills in parameters. Start again from a clean copy with
`python3 scripts/mcp_server.py init --reset`.

## Run the offline demo (no model, about 0.2 s)

```bash
python3 scripts/agent_demo.py              # readable story
python3 scripts/agent_demo.py --pace 2     # pause 2 s between steps, for filming
python3 scripts/agent_demo.py --json       # machine-readable summary, used by the tests
```

It starts both MCP servers as subprocesses and speaks MCP to them, like a host. Then it:

1. lists the tools on each server and the `:Recipe` nodes;
2. reads `agent/examples/venue-email-riverside.eml` and extracts the venue (Full HD projector, HDMI
   of unstated version, so HDMI 1.4 at low confidence, plus VGA; "one of our older" HDMI cables
   becomes a Standard HDMI cable). It writes the venue with `ingest_venue` through `write_cypher`
   and reads it back;
3. reads a sample spec page (`agent/examples/spec-page-examplelabs-usbc-hdmi.html`, a fictional
   product), extracts a USB-C to HDMI 2.0 adapter with 85 W PD pass-through, writes it with
   `ingest_item` and reads it back;
4. checks that the read-only catalog refuses writes and does not contain the new venue;
5. runs `reach`, `chains`, `best_fix` and `power` through `read_cypher`;
6. answers in plain English:

```
At Riverside Library, Room 2 your current bag only reaches 720p at 60 Hz (the display can do 1080p (Full HD) at 60 Hz).
The weakest link is Standard HDMI cable (Category 1, 720p/1080i) at 1.782 Gbps (HDMI-Standard-cable, medium confidence,
source: https://www.hdmi.org/resource/cables).
The Example Labs USB-C to HDMI 2.0 Adapter with 100W PD you asked about would not help at Riverside Library, Room 2:
even with it, the weakest link is still Standard HDMI cable (Category 1, 720p/1080i).
Buy one thing: USB-C to HDMI cable, 4K60 (HDMI 2.0 class). It makes 1080p (Full HD) at 60 Hz work at 2 more venues
(Riverside Library, Room 2, Podcast studio). It also makes 4K60 work at 2 of these venues.
Pack: Apple 70W USB-C Power Adapter, USB-C to USB-C charge cable, USB 2.0, 60 W, USB-C to HDMI cable, 4K60 (HDMI 2.0 class).
Leave at home: Apple USB-C Digital AV Multiport Adapter (older model A1621), USB-C multiport hub with HDMI 4K30 (typical 7-in-1).
Charging: Apple 70W USB-C Power Adapter + USB-C to USB-C charge cable, USB 2.0, 60 W charges at full speed (60 W; …).
```

Try your own inputs with `--email my.eml`, `--spec page.html` and `--profile me.json` (format:
`agent/examples/my-profile.json`). To use a venue that a model extracted, pass `--venue-json v.json`.
In the demo the extraction is done by rule-based extractors (`scripts/agent_lib.py`) written for the
sample formats. In an MCP host the model does that step, following `agent/prompts/`.

## Connect an MCP host

Prerequisites: the Relate CLI 1.0.1 (`curl -sSfL https://relatedb.ai/install.sh | bash`) and
Python 3.9+. The launcher finds `relate` on `PATH`, in `~/.local/bin`, or through `RELATE_BIN`.
Hosts that start with a minimal `PATH`, such as Claude Desktop on macOS, are covered by the
`~/.local/bin` fallback.

**Cursor**: the repo ships `.cursor/mcp.json` (it uses `${workspaceFolder}`). Open the folder, then
enable `weakest-link-catalog` and `weakest-link-mybag` under Settings → MCP. The rule
`.cursor/rules/pack-my-bag.mdc` points the agent at the skill.

**VS Code** (agent mode): the repo ships `.vscode/mcp.json`. Start the servers from that file's
code lens. `.github/prompts/pack-my-bag.prompt.md` adds a `/pack-my-bag` prompt.

**Claude Code**: the repo ships a project-scoped `.mcp.json`. Run `claude` in the repo and approve
the two servers. Or add them by hand:
`claude mcp add weakest-link-mybag -- python3 scripts/mcp_server.py mybag`.

**Claude Desktop**: copy `agent/clients/claude_desktop_config.json` into
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows), and replace `/ABSOLUTE/PATH/TO/weakest-link`.
Restart Claude. For the instructions, upload `agent/skills/pack-my-bag/` as a skill (zip the folder),
or paste `agent/prompts/system.md` into a Project's instructions.

**Any other host**: `agent/clients/relate-direct.mcp.json` runs `relate serve` directly with no
Python. Run `python3 scripts/mcp_server.py init` once first, so the writable store and its recipes exist.

## Prompts and skill

| File | What it is for |
|---|---|
| `agent/prompts/system.md` | rules: discover recipes, pass them verbatim, never invent numbers, extract conservatively, verify writes, answer shape |
| `agent/prompts/ingest-venue-email.md` | email → `$v` mapping table (the slower option when vague) and a worked example |
| `agent/prompts/ingest-spec-page.md` | spec page → `$it` (ports, standards, PD pass-through, confidence) |
| `agent/prompts/what-to-pack.md` | the plan: `reach` → `chains` → `best_fix` (tie-break at 4K60) → `reach` per venue → `power` |
| `agent/skills/pack-my-bag/` | a self-contained skill: `SKILL.md`, the prompts, and `CYPHER.md` with every recipe, check query and schema (generated by `scripts/build_agent_docs.py`) |
| `agent/schemas/*.json` | JSON Schemas for the ingest parameters |
| `agent/cypher/*.cypher` | the two write statements. Each is a single statement, because `write_cypher` takes one statement |

Example conversation in a host:

> **You:** I'm speaking at the Riverside Library next month. Here's their email: *(paste)*. I have a
> MacBook Air M2, the old Apple AV adapter, a 4K30 hub, the 70 W charger and a 60 W USB-C cable.
> I also like this adapter: *(paste spec page)*. What should I bring?
>
> **Agent:** *(discovers recipes → shows the extracted venue JSON → `write_cypher` ingest_venue →
> verifies → ingests the adapter → runs reach/chains/best_fix/power)* "At Riverside your bag only
> reaches 720p, because the venue's older HDMI cable is the weakest link … that adapter won't help …
> buy a 4K60 USB-C to HDMI cable …"

## Safety and limits

- The committed catalog is opened `--read-only`, and the writable store is a git-ignored copy.
  The ingest statements refuse to overwrite catalog venues or items: they write nothing, and
  `nodes_created` is 0.
- `write_cypher` on the my-bag store accepts any Cypher, so a model *could* damage that copy. Reset
  it with `mcp_server.py init --reset`. Relate's `--safe` mode is not used, because in Relate 1.0.1
  it refuses the vetted recipes (it rejects reads that have no `LIMIT`).
- Relate's MCP `read_cypher` rejects `CALL { }` subqueries, and `write_cypher` returns counters but
  no rows. The recipes are written for those limits (`best_fix` has no `CALL`), and writes are
  checked with a follow-up read.
- Relate's MCP server offers tools only (no MCP prompts or resources), which is why the recipes live
  in the graph and the prompts are files.
- The offline extractors handle the sample formats and common phrasings. They are not a general
  email parser. For anything else, let the host's model extract the JSON (`--venue-json` in the demo).
