# Demo video script (DRAFT)

Draft for Suganthi's review only. It has not been uploaded anywhere.

- Video: [`weakest-link-demo-draft.mp4`](weakest-link-demo-draft.mp4), 100.4 s, 1920×1080, 30 fps. Captions are burned in and also in [`weakest-link-demo-draft.srt`](weakest-link-demo-draft.srt).
- Narration: OpenAI TTS, `tts-1-hd`, voice `nova`, normalized to -16 LUFS. The measurements are in [`verification.json`](verification.json).
- Source of the narration: [`scripts/video/narration.json`](../../scripts/video/narration.json). To rebuild: `scripts/video/tts.py`,
  then `scripts/video/record.mjs` (Xvfb + local `vite preview`), then `scripts/video/assemble.py`.

| Time | Scene | On screen | Narration |
|---|---|---|---|
| 00:00–00:12 | hook | Title card: a 4K projector, five minutes to go, the screen says 1080p 30 Hz, then No signal. | Five minutes before your talk, you plug in, and the 4K projector shows a blurry 1080p. Or nothing at all. The laptop is fine. Somewhere in your bag is a weak link. |
| 00:12–00:25 | ui | Web UI on the local preview build: first-run intro, pick a laptop, tick the bag, pick the venue and 4K at 60 Hz. | Weakest Link tells you before you leave. Pick your laptop, tick what's in your bag, then choose the venue and the picture you want. It all runs in your browser, on Relate's WebAssembly engine. |
| 00:25–00:40 | diagram | Verdict and chain diagram: the hub is highlighted as the weakest link, with a confidence chip and a source link on every hop; the Cypher behind it. | The answer is a path through a graph: port, hub, cable, projector input. The hop with the lowest capacity is the weakest link. Here, a hub that only does HDMI 1.4. Every link shows its source and a confidence level. |
| 00:40–00:53 | fix | Best purchase tab: single purchases ranked by how many of the chosen venues they fix. | Best purchase looks across every venue you visit. One USB-C to HDMI cable fixes three of nine. And when the venue's own display is the limit, it says so instead of selling you something. |
| 00:53–01:03 | charge | Charging tab: a 140 W charger throttled to 60 W by a USB 2.0 cable, the cable to buy, Add to bag, then Fast-charges. | Same graph, in watts. A 140 watt charger on a thin cable charges slowly. It names the cable to buy, and one click later, it fast-charges. |
| 01:03–01:23 | agent | Terminal: python3 scripts/agent_demo.py --pace, a pack-my-bag agent driving relate serve --mcp. | Your AI assistant gets the same graph through Relate's MCP server. This pack-my-bag agent reads a venue's email, writes it into its own copy of the graph with the source, and runs the vetted query recipes. Pack this, leave that, buy one cable, and a better charging cable. |
| 01:23–01:40 | close | Closing card: why a graph, why Relate. | Why a graph? Compatibility is relationships: what plugs into what, and what each hop can carry. Relate keeps it all in one cited file that runs the same in the command line, the browser, and MCP. Weakest Link. Find it before your audience does. |
