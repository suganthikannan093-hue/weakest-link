# Dataset: sources, confidence and known limits

The catalog in `data/src/` is hand-written for this project and licensed **CC BY 4.0** (see
`data/LICENSE`). The CSV export in `data/csv/` and the Relate store `data/weakest-link.rl` are
generated from it.

## Rules every capability edge follows

* Every `VIDEO` and `POWER` edge names a **source** (`source`, `source_url`) and a **confidence**
  (`high`, `medium` or `low`). A test (`tests/test_queries.py`) fails if any edge is uncited.
* Video bandwidth comes from the **standard** the link follows (`data/src/standards.json`), never
  from marketing copy. All numbers are *data* rates after line coding:

  | Standard | Raw | Data rate used |
  |---|---|---|
  | HDMI Standard cable (720p/1080i certification) | 2.23 Gbps | 1.782 Gbps |
  | HDMI 1.4 / High Speed cable | 10.2 Gbps | 8.16 Gbps |
  | HDMI 2.0 / Premium High Speed cable | 18 Gbps | 14.4 Gbps |
  | HDMI 2.1 FRL / Ultra High Speed cable | 48 Gbps | 42.67 Gbps |
  | DP 1.2 HBR2 ×4 | 21.6 Gbps | 17.28 Gbps |
  | DP 1.4 HBR3 ×4, DP Alt Mode 4-lane | 32.4 Gbps | 25.92 Gbps |
  | DP Alt Mode 2-lane HBR3 | 16.2 Gbps | 12.96 Gbps |
  | DP 2.1 UHBR10 (DP8K cable) | 40 Gbps | 38.69 Gbps |
  | VGA (analog, converter limit 1920×1200@60) | none | 3.7 Gbps equivalent |

* A mode's requirement is pixel clock × 24 bit (8-bit RGB 4:4:4, no compression), using CTA-861
  timings: 720p60 74.25 MHz, 1080p60 148.5 MHz, 4K30 297 MHz, 4K60 594 MHz. 1440p60 uses CVT-RB at
  241.5 MHz.
* Named products (Apple, Lenovo) use the maker's own spec page. **Generic classes** (for example
  "USB-C to HDMI adapter, 4K60 (HDMI 2.0 class)") use the limit of the standard they claim. Their
  source is `class-assumption`, which points to this file.

## Sources used

See `data/src/sources.json` (also loaded into the graph as `:Source` nodes). They are:

* Spec bodies: hdmi.org (cable types, Premium and Ultra High Speed certification, HDMI 1.4b and 2.1),
  VESA DP Alt Mode, and USB-IF (cables, USB PD).
* Makers: Apple tech specs for MacBook Air M2 and MacBook Pro 14 M3, Apple's AV adapter page, Apple
  power-adapter and fast-charge pages, and Lenovo PSREF for the X1 Carbon Gen 11.
* Reference: Wikipedia's HDMI, DisplayPort, USB-C, Thunderbolt, CVT and VGA articles. These are used
  for line-coding arithmetic and timing tables, and are cross-checked against the spec bodies.

## Known simplifications (accuracy risks)

1. **Conservative timing.** We use CTA-861 timings, which is what TVs and projectors expect.
   Monitors on DisplayPort often accept reduced-blanking timings that need less bandwidth. For
   example, 4K60 over 2-lane HBR3 can work with CVT-RB2 but fails our check. The tool may say "no"
   to some setups that work. It should not say "yes" to one that cannot work.
2. **No DSC, chroma subsampling or 10-bit.** 4K120, 6K, 8K and HDR bit depths are not modelled yet.
3. **Cable certification is not cable behaviour.** A "High Speed" (10.2 Gbps) HDMI cable often
   passes 4K60, but it is not certified to. We model the certified limit. The Standard HDMI cable is
   marked medium confidence for this reason.
4. **Laptop port capability is sometimes inferred.** Apple documents "DisplayPort" and "6K60" but not
   the lane rate. HBR3 ×4 is assumed, at **medium** confidence. The MacBook Pro 14 M3 HDMI port is
   documented at up to 4K120. We model it as HDMI 2.0 (4K60), which is enough for every mode here.
5. **Generic classes can hide bad products.** A no-name "4K" adapter may be 4K30. That is why named
   products exist (Apple A1621 vs A2119 look identical but differ) and why the confidence is shown.
6. **Power is a capacity, not a draw.** `capacity_w` is the most the chain can carry. The laptop draws
   only what it needs. Fast-charge thresholds come from the maker (Apple: MacBook Air 2022+ fast
   charges with a 67 W+ adapter, and MacBook Pro 14 with 96 W+ or a 94 W display. Lenovo: Rapid
   Charge with 65 W).
7. **Shared charger ports.** Apple's 35 W dual adapter splits 35 W across two ports. It is modelled
   as one port in use.
8. **One instance per item class.** A chain cannot use two of the same item. For example, two
   identical HDMI cables joined by a coupler are not modelled yet.
