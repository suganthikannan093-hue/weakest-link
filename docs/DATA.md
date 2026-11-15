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
  | DP 1.2 HBR2 ×4, DP Alt Mode 4-lane HBR2 | 21.6 Gbps | 17.28 Gbps |
  | DP 1.4 HBR3 ×4 (also DP8K cables), DP Alt Mode 4-lane HBR3 | 32.4 Gbps | 25.92 Gbps |
  | DP Alt Mode 2-lane HBR3 | 16.2 Gbps | 12.96 Gbps |
  | DP Alt Mode 2-lane HBR2 | 10.8 Gbps | 8.64 Gbps |
  | DP 2.1 UHBR10 (not used by any edge) | 40 Gbps | 38.69 Gbps |
  | DP 2.1 UHBR13.5 (DP54 cable) | 54 Gbps | 52.22 Gbps |
  | VGA (analog, converter limit 1920×1200@60) | none | 3.7 Gbps equivalent |

* A mode's requirement is pixel clock × 24 bit (8-bit RGB 4:4:4, no compression), using CTA-861
  timings: 720p60 74.25 MHz, 1080p60 148.5 MHz, 4K30 297 MHz, 4K60 594 MHz. 1440p60 uses CVT-RB at
  241.5 MHz.
* Named products use the maker's own spec page (Apple tech specs, Lenovo PSREF, Dell, HP, Microsoft,
  Google, Samsung, Anker, CalDigit, Framework, LG, Epson, BenQ). **Generic classes** (for example
  "USB-C to HDMI adapter, 4K60 (HDMI 2.0 class)") use the limit of the standard they claim, and cite
  that standard's public spec page (hdmi.org, VESA or USB-IF). Every source URL is public; none
  points at this repository.
* When a maker documents a feature but not its rate (for example "video out up to 4K HDR" with no
  refresh rate), the edge uses the lowest rate that matches the documented limit and is marked
  **low**. The tool then errs towards "no".
* Docks and USB-C monitors with their own power supply get a `psu` endpoint, so the charging query
  treats them like chargers.

## What is in the catalog

100 items: 19 laptops (including a Chromebook and two generic classes), 7 phones, 4 tablets, 18
adapters, hubs and docks, 21 cables, 16 chargers and 15 displays and projectors. 62 are named
products from 13 makers and 38 are generic classes. They have 208 ports and 213 capability edges
(150 high, 54 medium and 9 low confidence; the medium share fell slightly, from 26% to 25%), drawn from 64 sources. Nine venues use them.

## Sources used

See `data/src/sources.json` (also loaded into the graph as `:Source` nodes). They are:

* Spec bodies: hdmi.org (cable types, Premium and Ultra High Speed certification, HDMI 1.4b, the
  HDMI 2.0 release), VESA (DP Alt Mode, the 2024 Tokyo workshop on DP and cable certification, the
  DP8K release) and USB-IF (cables, USB PD).
* Makers: Apple tech specs (MacBook Air M1/M2/M3/M4, MacBook Pro 14 M3/M4, iPhone 15/15 Pro/16,
  iPad 10, iPad Air M2) and Apple accessory pages; Lenovo PSREF (ThinkPad X1 Carbon Gen 11/12,
  T14 Gen 4, E14 Gen 5, IdeaPad Slim 3, IdeaPad 1, Yoga Slim 7, Flex 5 Chromebook Plus, ThinkVision
  monitors) and the Universal USB-C Dock datasheet; the Dell XPS 13 9340 manual and P2723QE page; the HP
  EliteBook 840 G10 datasheet; Microsoft's Surface USB4 Dock and Travel Hub pages; Google Pixel and
  Samsung DeX help pages; Anker, CalDigit, Framework, LG, Epson and BenQ product pages.
* Reference: Wikipedia's HDMI, DisplayPort, USB-C, Thunderbolt, CVT and VGA articles. These are used
  only for line-coding arithmetic, timing tables and VGA, where no spec body publishes a figure.

## Known simplifications (accuracy risks)

1. **Conservative timing.** We use CTA-861 timings, which is what TVs and projectors expect.
   Monitors on DisplayPort often accept reduced-blanking timings that need less bandwidth. For
   example, 4K60 over 2-lane HBR3 can work with CVT-RB2 but fails our check. The tool may say "no"
   to some setups that work. It should not say "yes" to one that cannot work.
2. **No DSC, chroma subsampling or 10-bit.** 4K120, 6K, 8K and HDR bit depths are not modelled yet.
3. **Cable certification is not cable behaviour.** A "High Speed" (10.2 Gbps) HDMI cable often
   passes 4K60, but it is not certified to. We model the certified limit. The Standard HDMI cable is
   marked medium confidence for this reason.
4. **Device port capability is sometimes inferred.** Apple documents "DisplayPort" and "6K60" but not
   the lane rate. HBR3 ×4 is assumed, at **medium** confidence (the M4 models state DisplayPort 1.4,
   so they are high). HDMI ports documented as "HDMI 2.1, up to 4K60" are modelled at the HDMI 2.0
   rate. Phones mostly say "up to 4K" without a refresh rate; they are modelled at 4K30 and **low**.
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
9. **Dock cables are part of the dock.** The CalDigit TS4, the ThinkPad Universal USB-C Dock and the
   Surface USB4 Dock are modelled with their bundled host cable as a USB-C plug, so a weak cable of
   your own cannot be put in that position.
10. **Charging thresholds for phones.** Apple names a 20 W adapter for iPhone fast charging; Google
    and Samsung pages cited here do not state wattages, so those phones get the verdict "unknown"
    rather than a guessed number.
11. **Shared ports on chargers and hubs.** Multi-port chargers (Anker 735, Anker Prime) are modelled
    with one port in use at its single-port maximum.

## Accuracy audit (milestone 4)

Every capability edge in `data/src/items.json`, every device charging threshold and every standard
was checked on 15 Nov 2026 (IST) against the source it cites. The check fetched the page text and
looked for the claim. Dell's and Framework's sites block scripted fetches, and Apple's 240 W cable store page renders its specs in script; those claims were
checked against search-engine extracts of the maker's own page and held at **medium**. The table is
generated by `python3 scripts/build_audit.py` from `data/src/items.json`, `data/src/standards.json`
and `data/src/audit.json`, and a test fails if it goes stale.

### What the audit changed

* **Fixed: `cable-dp8k`.** It was modelled at DP 2.1 UHBR10 (38.69 Gbps). VESA certifies DP8K cables
  at the full HBR3 rate (4 lanes × 8.1 Gbps = 25.92 Gbps data); UHBR13.5 is DP54 and UHBR20 is DP80.
  The verdict for 4K60 does not change. A DP54 cable was added as its own item.
* **Downgraded: High Speed HDMI cable**, high to medium. hdmi.org lists it at 10.2 Gbps, but the
  HDMI 2.0 press release says Category 2 cables carry 18 Gbps. We keep the conservative figure.
* **Downgraded: active DP-to-HDMI adapter class**, high to medium (many "active" adapters are 4K30).
* **Re-sourced: 20 generic edges** that cited `class-assumption` (a URL in this private repo) now
  cite the public page of the standard they claim. Their limits did not change.
* **Re-sourced: standards** from Wikipedia to spec bodies: HDMI 1.4 (hdmi.org 1.4b), HDMI 2.0 (the
  HDMI 2.0 release, because hdmi.org/spec/hdmi2_0 now returns 404), HDMI 2.1 FRL (the Ultra High
  Speed cable page, because the HDMI 2.1 URL now shows HDMI 2.2), DP 1.2/1.4 (VESA), USB PD 60 W and
  100 W (USB-IF). The Thunderbolt 4 cable now cites Apple's Thunderbolt cable page.
* **Confirmed unchanged:** MacBook Air M2 (6K60, 30 W included, fast charge at 67 W+), MacBook Pro 14
  M3 (HDMI to 4K120, fast charge with 96 W or a 94 W display), the Apple A2119 (4K60) and A1621 (4K30,
  1080p60) adapters, Apple's adapter wattages, X1 Carbon Gen 11 (TB4 with DP 1.4a, HDMI 4K60, Rapid
  Charge at 65 W), hdmi.org cable tiers, USB-IF PD and cable ratings, and VESA's Alt Mode lane rates.

### Audit table

<!-- AUDIT:BEGIN (generated by scripts/build_audit.py) -->
| Item | Claim | Source | Checked | Confidence | Result |
|---|---|---|---|---|---|
| `standard HDMI-Standard-cable` | 1.782 Gbps data | [HDMI Licensing Administrator: HDMI Cables - Different Cable Types](https://www.hdmi.org/resource/cables) | 2026-11-15, page fetched | medium | Verified (Standard cable tested for 720p/1080i). Medium: many pass more, uncertified. |
| `standard HDMI-1.4` | 8.16 Gbps data | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to hdmi.org (HDMI 1.4b: 4K30). Wikipedia is kept only for the 8b/10b arithmetic. |
| `standard HDMI-2.0` | 14.4 Gbps data | [HDMI Licensing Administrator: HDMI Forum releases version 2.0 of the HDMI Specification (press release)](https://www.hdmi.org/press/bodydetails/24) | 2026-11-15, page fetched | high | RE-SOURCED to the HDMI 2.0 release (18 Gbps, 4K60); hdmi.org/spec/hdmi2_0 now returns 404. |
| `standard HDMI-2.1-FRL` | 42.67 Gbps data | [HDMI Licensing Administrator: Ultra High Speed HDMI Cable](https://www.hdmi.org/spec21sub/ultrahighspeedcable) | 2026-11-15, page fetched | high | RE-SOURCED to the Ultra High Speed cable page (48 Gbps); the old HDMI 2.1 URL now shows HDMI 2.2. |
| `standard DP-1.2-HBR2` | 17.28 Gbps data | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to VESA (DPv1.2 = HBR2, 5.4 Gbps/lane). |
| `standard DP-1.4-HBR3` | 25.92 Gbps data | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to VESA (DPv1.4 = HBR3, 8.1 Gbps/lane). |
| `standard DP-2.1-UHBR10` | 38.69 Gbps data | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | RE-SOURCED to VESA. No catalog edge uses it any more (DP8K was moved to HBR3). |
| `standard DP-2.1-UHBR13.5` | 52.22 Gbps data | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | ADDED for the DP54 cable (VESA). Data rate after 128b/132b and FEC from Wikipedia. |
| `standard DP-Alt-4L-HBR3` | 25.92 Gbps data | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `standard DP-Alt-2L-HBR3` | 12.96 Gbps data | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `standard DP-Alt-4L-HBR2` | 17.28 Gbps data | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | ADDED for DisplayPort 1.2 USB-C ports and 5 Gbps cables. |
| `standard DP-Alt-2L-HBR2` | 8.64 Gbps data | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | ADDED; VESA's slide gives 2-lane HBR2 = 4K30, matching Apple's iPad 10 limit. |
| `standard VGA-1200p` | 3.7 Gbps data | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | medium | No spec body publishes this; Wikipedia only. Kept medium. |
| `standard USB-PD-3A` | 60 W | [USB-IF: USB-IF Cables and Connectors](https://usb.org/cable_connector) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to USB-IF (20 V at 3 A is the 60 W cable rating). |
| `standard USB-PD-5A` | 100 W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to USB-IF PD (100 W at 20 V/5 A). |
| `standard USB-PD-EPR` | 240 W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | Verified |
| `mba-m2` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Air (M2, 2022) - Tech Specs](https://support.apple.com/en-us/111867) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mba-m2` | power tb1→battery, tb2→battery, magsafe→battery: charges here | [Apple: MacBook Air (M2, 2022) - Tech Specs](https://support.apple.com/en-us/111867) | 2026-11-15, page fetched | high | Verified |
| `mba-m2` | charging threshold: recommended 30 W, fast 67 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m3` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Pro (14-inch, M3, Nov 2023) - Tech Specs](https://support.apple.com/en-us/117735) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mbp14-m3` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Apple: MacBook Pro (14-inch, M3, Nov 2023) - Tech Specs](https://support.apple.com/en-us/117735) | 2026-11-15, page fetched | high | Verified (Apple documents 4K120 over HDMI); modelled lower at the HDMI 2.0 rate, which covers every mode here. |
| `mbp14-m3` | power tb1→battery, tb2→battery, magsafe→battery: charges here | [Apple: MacBook Pro (14-inch, M3, Nov 2023) - Tech Specs](https://support.apple.com/en-us/117735) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m3` | charging threshold: recommended 67 W, fast 94 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `x1c-g11` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo PSREF: ThinkPad X1 Carbon Gen 11 - PSREF specifications](https://psref.lenovo.com/syspool/sys/pdf/thinkpad/thinkpad_x1_carbon_gen_11/thinkpad_x1_carbon_gen_11_spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `x1c-g11` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo PSREF: ThinkPad X1 Carbon Gen 11 - PSREF specifications](https://psref.lenovo.com/syspool/sys/pdf/thinkpad/thinkpad_x1_carbon_gen_11/thinkpad_x1_carbon_gen_11_spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `x1c-g11` | power tb1→battery, tb2→battery: charges here | [Lenovo PSREF: ThinkPad X1 Carbon Gen 11 - PSREF specifications](https://psref.lenovo.com/syspool/sys/pdf/thinkpad/thinkpad_x1_carbon_gen_11/thinkpad_x1_carbon_gen_11_spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `x1c-g11` | charging threshold: recommended 45 W, fast 65 W | [Lenovo PSREF: ThinkPad X1 Carbon Gen 11 - PSREF specifications](https://psref.lenovo.com/syspool/sys/pdf/thinkpad/thinkpad_x1_carbon_gen_11/thinkpad_x1_carbon_gen_11_spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `gen-laptop-usbc` | video gpu→usbc1, gpu→usbc2: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `gen-laptop-usbc` | power usbc1→battery, usbc2→battery: charges here | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `gen-laptop-usbc` | charging threshold: recommended 65 W, fast n/a W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | Verified |
| `gen-laptop-budget` | video gpu→hdmi: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mba-m1` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Air (M1, 2020) - Tech Specs](https://support.apple.com/en-us/111883) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mba-m1` | power tb1→battery, tb2→battery: charges here | [Apple: MacBook Air (M1, 2020) - Tech Specs](https://support.apple.com/en-us/111883) | 2026-11-15, page fetched | high | Verified |
| `mba-m1` | charging threshold: recommended 30 W, fast n/a W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `mba-m3` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Air (13-inch, M3, 2024) - Tech Specs](https://support.apple.com/en-us/118551) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mba-m3` | power tb1→battery, tb2→battery, magsafe→battery: charges here | [Apple: MacBook Air (13-inch, M3, 2024) - Tech Specs](https://support.apple.com/en-us/118551) | 2026-11-15, page fetched | high | Verified |
| `mba-m3` | charging threshold: recommended 30 W, fast 67 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `mba-m4` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Air (13-inch, M4, 2025) - Tech Specs](https://support.apple.com/en-us/122209) | 2026-11-15, page fetched | high | Verified |
| `mba-m4` | power tb1→battery, tb2→battery, magsafe→battery: charges here | [Apple: MacBook Air (13-inch, M4, 2025) - Tech Specs](https://support.apple.com/en-us/122209) | 2026-11-15, page fetched | high | Verified |
| `mba-m4` | charging threshold: recommended 30 W, fast 67 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m4` | video gpu→tb1, gpu→tb2, gpu→tb3: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: MacBook Pro (14-inch, M4, 2024) - Tech Specs](https://support.apple.com/en-us/121552) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m4` | video gpu→hdmi: HDMI-2.1-FRL (42.67 Gbps) | [Apple: MacBook Pro (14-inch, M4, 2024) - Tech Specs](https://support.apple.com/en-us/121552) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m4` | power tb1→battery, tb2→battery, tb3→battery, magsafe→battery: charges here | [Apple: MacBook Pro (14-inch, M4, 2024) - Tech Specs](https://support.apple.com/en-us/121552) | 2026-11-15, page fetched | high | Verified |
| `mbp14-m4` | charging threshold: recommended 67 W, fast 94 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `x1c-g12` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: ThinkPad X1 Carbon Gen 12 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_12/ThinkPad_X1_Carbon_Gen_12_Spec.pdf) | 2026-11-15, page fetched | medium | Verified port; PSREF says DisplayPort 2.1 without a UHBR rate, so held at HBR3 and medium. |
| `x1c-g12` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkPad X1 Carbon Gen 12 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_12/ThinkPad_X1_Carbon_Gen_12_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `x1c-g12` | power tb1→battery, tb2→battery: charges here | [Lenovo: ThinkPad X1 Carbon Gen 12 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_12/ThinkPad_X1_Carbon_Gen_12_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `x1c-g12` | charging threshold: recommended 45 W, fast 65 W | [Lenovo: ThinkPad X1 Carbon Gen 12 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_X1_Carbon_Gen_12/ThinkPad_X1_Carbon_Gen_12_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `t14-g4` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `t14-g4` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `t14-g4` | power tb1→battery, tb2→battery: charges here | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `t14-g4` | charging threshold: recommended 45 W, fast 65 W | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `yoga-slim7-14` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: Yoga Slim 7 14IMH9 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/Yoga/Yoga_Slim_7_14IMH9/Yoga_Slim_7_14IMH9_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `yoga-slim7-14` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo: Yoga Slim 7 14IMH9 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/Yoga/Yoga_Slim_7_14IMH9/Yoga_Slim_7_14IMH9_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `yoga-slim7-14` | power tb1→battery, tb2→battery: charges here | [Lenovo: Yoga Slim 7 14IMH9 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/Yoga/Yoga_Slim_7_14IMH9/Yoga_Slim_7_14IMH9_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `yoga-slim7-14` | charging threshold: recommended 45 W, fast 65 W | [Lenovo: Yoga Slim 7 14IMH9 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/Yoga/Yoga_Slim_7_14IMH9/Yoga_Slim_7_14IMH9_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `xps13-9340` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Dell: XPS 13 9340 Owner's Manual - External ports](https://www.dell.com/support/manuals/en-us/xps-13-9340-laptop/xps-13-9340_owners_manual/external-ports-and-slots?guid=guid-b8f739cc-a41e-4ac9-b3f8-ff6d9c6d8c19&lang=en-us) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `xps13-9340` | power tb1→battery, tb2→battery: charges here | [Dell: XPS 13 9340 Owner's Manual - External ports](https://www.dell.com/support/manuals/en-us/xps-13-9340-laptop/xps-13-9340_owners_manual/external-ports-and-slots?guid=guid-b8f739cc-a41e-4ac9-b3f8-ff6d9c6d8c19&lang=en-us) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `xps13-9340` | charging threshold: recommended 60 W, fast n/a W | [Dell: XPS 13 9340 Owner's Manual - External ports](https://www.dell.com/support/manuals/en-us/xps-13-9340-laptop/xps-13-9340_owners_manual/external-ports-and-slots?guid=guid-b8f739cc-a41e-4ac9-b3f8-ff6d9c6d8c19&lang=en-us) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `elitebook-840-g10` | video gpu→tb1, gpu→tb2: DP-Alt-4L-HBR3 (25.92 Gbps) | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `elitebook-840-g10` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `elitebook-840-g10` | power tb1→battery, tb2→battery: charges here | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `elitebook-840-g10` | charging threshold: recommended 45 W, fast 65 W | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `e14-g5` | video gpu→tb4, gpu→usbc: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: ThinkPad E14 Gen 5 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_E14_Gen_5_Intel/ThinkPad_E14_Gen_5_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `e14-g5` | video gpu→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkPad E14 Gen 5 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_E14_Gen_5_Intel/ThinkPad_E14_Gen_5_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `e14-g5` | power tb4→battery, usbc→battery: charges here | [Lenovo: ThinkPad E14 Gen 5 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_E14_Gen_5_Intel/ThinkPad_E14_Gen_5_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `e14-g5` | charging threshold: recommended 65 W, fast n/a W | [Lenovo: ThinkPad E14 Gen 5 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_E14_Gen_5_Intel/ThinkPad_E14_Gen_5_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iru8` | video gpu→usbc: DP-Alt-4L-HBR2 (17.28 Gbps) | [Lenovo: IdeaPad Slim 3 15IRU8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IRU8/IdeaPad_Slim_3_15IRU8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iru8` | video gpu→hdmi: HDMI-1.4 (8.16 Gbps) | [Lenovo: IdeaPad Slim 3 15IRU8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IRU8/IdeaPad_Slim_3_15IRU8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iru8` | power usbc→battery: charges here | [Lenovo: IdeaPad Slim 3 15IRU8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IRU8/IdeaPad_Slim_3_15IRU8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iru8` | charging threshold: recommended 65 W, fast n/a W | [Lenovo: IdeaPad Slim 3 15IRU8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IRU8/IdeaPad_Slim_3_15IRU8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad1-15amn7` | video gpu→hdmi: HDMI-1.4 (8.16 Gbps) | [Lenovo: IdeaPad 1 15AMN7 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_1_15AMN7/IdeaPad_1_15AMN7_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `chromebook-flex5-plus` | video gpu→usbc1, gpu→usbc2: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: IdeaPad Flex 5 Chromebook Plus 14IAU7 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IP_Flex_5_Chrome_14IAU7_Plus/IP_Flex_5_Chrome_14IAU7_Plus_Spec.PDF) | 2026-11-15, page fetched | high | Verified |
| `chromebook-flex5-plus` | power usbc1→battery, usbc2→battery: charges here | [Lenovo: IdeaPad Flex 5 Chromebook Plus 14IAU7 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IP_Flex_5_Chrome_14IAU7_Plus/IP_Flex_5_Chrome_14IAU7_Plus_Spec.PDF) | 2026-11-15, page fetched | high | Verified |
| `chromebook-flex5-plus` | charging threshold: recommended 45 W, fast n/a W | [Lenovo: IdeaPad Flex 5 Chromebook Plus 14IAU7 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IP_Flex_5_Chrome_14IAU7_Plus/IP_Flex_5_Chrome_14IAU7_Plus_Spec.PDF) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iah8` | video gpu→usbc: DP-Alt-4L-HBR2 (17.28 Gbps) | [Lenovo: IdeaPad Slim 3 15IAH8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IAH8/IdeaPad_Slim_3_15IAH8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iah8` | video gpu→hdmi: HDMI-1.4 (8.16 Gbps) | [Lenovo: IdeaPad Slim 3 15IAH8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IAH8/IdeaPad_Slim_3_15IAH8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `ideapad-slim3-15iah8` | power usbc→battery: charges here | [Lenovo: IdeaPad Slim 3 15IAH8 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/IdeaPad/IdeaPad_Slim_3_15IAH8/IdeaPad_Slim_3_15IAH8_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `iphone-15` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Apple: iPhone 15 - Tech Specs](https://support.apple.com/en-us/111831) | 2026-11-15, page fetched | low | Source says 'up to 4K HDR' with no refresh rate; modelled conservatively at 4K30, low confidence. |
| `iphone-15` | power usbc→battery: charges here | [Apple: iPhone 15 - Tech Specs](https://support.apple.com/en-us/111831) | 2026-11-15, page fetched | high | Verified |
| `iphone-15` | charging threshold: recommended n/a W, fast 20 W | [Apple: iPhone 15 - Tech Specs](https://support.apple.com/en-us/111831) | 2026-11-15, page fetched | high | Verified |
| `iphone-15-pro` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Apple: iPhone 15 Pro - Tech Specs](https://support.apple.com/en-us/111829) | 2026-11-15, page fetched | low | Source says 'up to 4K HDR' with no refresh rate; modelled conservatively at 4K30, low confidence. |
| `iphone-15-pro` | power usbc→battery: charges here | [Apple: iPhone 15 Pro - Tech Specs](https://support.apple.com/en-us/111829) | 2026-11-15, page fetched | high | Verified |
| `iphone-15-pro` | charging threshold: recommended n/a W, fast 20 W | [Apple: iPhone 15 Pro - Tech Specs](https://support.apple.com/en-us/111829) | 2026-11-15, page fetched | high | Verified |
| `iphone-16` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Apple: iPhone 16 - Tech Specs](https://support.apple.com/en-us/121029) | 2026-11-15, page fetched | low | Source says 'up to 4K HDR' with no refresh rate; modelled conservatively at 4K30, low confidence. |
| `iphone-16` | power usbc→battery: charges here | [Apple: iPhone 16 - Tech Specs](https://support.apple.com/en-us/121029) | 2026-11-15, page fetched | high | Verified |
| `iphone-16` | charging threshold: recommended n/a W, fast 20 W | [Apple: iPhone 16 - Tech Specs](https://support.apple.com/en-us/121029) | 2026-11-15, page fetched | high | Verified |
| `pixel-8` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Google: Connect your Pixel phone to a display (Pixel Phone Help)](https://support.google.com/pixelphone/answer/2865484?hl=en) | 2026-11-15, page fetched | low | Google confirms wired display output on Pixel 8+, no resolution; low confidence. |
| `pixel-8` | power usbc→battery: charges here | [Google: Connect your Pixel phone to a display (Pixel Phone Help)](https://support.google.com/pixelphone/answer/2865484?hl=en) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `pixel-7a` | power usbc→battery: charges here | [Google: Connect your Pixel phone to a display (Pixel Phone Help)](https://support.google.com/pixelphone/answer/2865484?hl=en) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `galaxy-s24` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | low | Samsung confirms HDMI/DeX output, no resolution; low confidence. |
| `galaxy-s24` | power usbc→battery: charges here | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `galaxy-z-flip6` | power usbc→battery: charges here | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `ipad-10` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Apple: iPad (10th generation) - Tech Specs](https://support.apple.com/en-us/111840) | 2026-11-15, page fetched | medium | Verified limit (4K30 or 1080p60); the 2-lane HBR2 rate matching it is our inference, so medium. |
| `ipad-10` | power usbc→battery: charges here | [Apple: iPad (10th generation) - Tech Specs](https://support.apple.com/en-us/111840) | 2026-11-15, page fetched | high | Verified |
| `ipad-10` | charging threshold: recommended 20 W, fast n/a W | [Apple: iPad (10th generation) - Tech Specs](https://support.apple.com/en-us/111840) | 2026-11-15, page fetched | high | Verified |
| `ipad-air-m2` | video gpu→usbc: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: iPad Air 11-inch (M2) - Tech Specs](https://support.apple.com/en-us/119894) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `ipad-air-m2` | power usbc→battery: charges here | [Apple: iPad Air 11-inch (M2) - Tech Specs](https://support.apple.com/en-us/119894) | 2026-11-15, page fetched | high | Verified |
| `ipad-air-m2` | charging threshold: recommended 20 W, fast n/a W | [Apple: iPad Air 11-inch (M2) - Tech Specs](https://support.apple.com/en-us/119894) | 2026-11-15, page fetched | high | Verified |
| `galaxy-tab-s9` | video gpu→usbc: DP-Alt-2L-HBR2 (8.64 Gbps) | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | low | Samsung confirms HDMI/DeX output, no resolution; low confidence. |
| `galaxy-tab-s9` | power usbc→battery: charges here | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `galaxy-tab-s9-fe` | power usbc→battery: charges here | [Samsung: Use the Samsung DeX screen on your Galaxy phone or tablet](https://www.samsung.com/us/support/answer/ANS10001955/) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `adp-usbc-hdmi-4k30` | video in→out: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `adp-usbc-hdmi-4k60` | video in→out: HDMI-2.0 (14.4 Gbps) | [HDMI Licensing Administrator: HDMI Forum releases version 2.0 of the HDMI Specification (press release)](https://www.hdmi.org/press/bodydetails/24) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `adp-usbc-hdmi21` | video in→out: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `adp-apple-av-a2119` | video in→out: HDMI-2.0 (14.4 Gbps) | [Apple: About the Apple USB-C Digital AV Multiport Adapter](https://support.apple.com/en-us/119850) | 2026-11-15, page fetched | high | Verified |
| `adp-apple-av-a1621` | video in→out: HDMI-1.4 (8.16 Gbps) | [Apple: About the Apple USB-C Digital AV Multiport Adapter](https://support.apple.com/en-us/119850) | 2026-11-15, page fetched | high | Verified |
| `adp-usbc-dp` | video in→out: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `adp-usbc-vga` | video in→out: VGA-1200p (3.7 Gbps) | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `adp-dp-hdmi-passive` | video in→out: HDMI-1.4 (8.16 Gbps) | [Wikipedia: DisplayPort - link rates, DP++ dual-mode, cables](https://en.wikipedia.org/wiki/DisplayPort) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `adp-dp-hdmi-active` | video in→out: HDMI-2.0 (14.4 Gbps) | [Wikipedia: DisplayPort - link rates, DP++ dual-mode, cables](https://en.wikipedia.org/wiki/DisplayPort) | 2026-11-15, page fetched | medium | DOWNGRADED high to medium: many adapters sold as 'active' are 4K30; the class only holds if the box says 4K60. |
| `adp-hdmi-vga` | video in→out: VGA-1200p (3.7 Gbps) | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `hub-usbc-4k30` | video in→out: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `adp-apple-vga` | video in→vga: VGA-1200p (3.7 Gbps) | [Apple: About the Apple USB-C VGA Multiport Adapter](https://support.apple.com/en-us/111815) | 2026-11-15, page fetched | high | Verified |
| `adp-apple-vga` | power pd→in: 60 W | [Apple: About the Apple USB-C VGA Multiport Adapter](https://support.apple.com/en-us/111815) | 2026-11-15, page fetched | high | Verified |
| `hub-anker-341` | video in→hdmi: HDMI-1.4 (8.16 Gbps) | [Anker: Anker 341 USB-C Hub (7-in-1)](https://www.anker.com/products/a8346) | 2026-11-15, page fetched | high | Verified |
| `hub-anker-341` | power pd→in: 85 W | [Anker: Anker 341 USB-C Hub (7-in-1)](https://www.anker.com/products/a8346) | 2026-11-15, page fetched | high | Verified |
| `hub-ms-travel` | video in→hdmi: HDMI-2.0 (14.4 Gbps) | [Microsoft: Use the Surface USB-C Travel Hub](https://support.microsoft.com/en-US/surface/surface-dock/use-the-surface-usb-c-travel-hub) | 2026-11-15, page fetched | high | Verified |
| `hub-ms-travel` | video in→vga: VGA-1200p (3.7 Gbps) | [Microsoft: Use the Surface USB-C Travel Hub](https://support.microsoft.com/en-US/surface/surface-dock/use-the-surface-usb-c-travel-hub) | 2026-11-15, page fetched | high | Verified |
| `dock-caldigit-ts4` | video host→dp: DP-1.4-HBR3 (25.92 Gbps) | [CalDigit: Thunderbolt Station 4 (TS4)](https://www.caldigit.com/thunderbolt-station-4/) | 2026-11-15, page fetched | high | Verified |
| `dock-caldigit-ts4` | video host→tb-down1, host→tb-down2: DP-Alt-4L-HBR3 (25.92 Gbps) | [CalDigit: Thunderbolt Station 4 (TS4)](https://www.caldigit.com/thunderbolt-station-4/) | 2026-11-15, page fetched | high | Verified |
| `dock-caldigit-ts4` | power psu→host: 98 W | [CalDigit: Thunderbolt Station 4 (TS4)](https://www.caldigit.com/thunderbolt-station-4/) | 2026-11-15, page fetched | high | Verified |
| `dock-lenovo-universal` | video host→dp1, host→dp2: DP-1.4-HBR3 (25.92 Gbps) | [Lenovo: ThinkPad Universal USB-C Dock - datasheet](https://techtoday.lenovo.com/sites/default/files/2025-08/thinkpad-universal-usb-c-dock-datasheet-ww-en.pdf) | 2026-11-15, page fetched | high | Verified |
| `dock-lenovo-universal` | video host→hdmi: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkPad Universal USB-C Dock - datasheet](https://techtoday.lenovo.com/sites/default/files/2025-08/thinkpad-universal-usb-c-dock-datasheet-ww-en.pdf) | 2026-11-15, page fetched | high | Verified |
| `dock-lenovo-universal` | power psu→host: 65 W | [Lenovo: ThinkPad Universal USB-C Dock - datasheet](https://techtoday.lenovo.com/sites/default/files/2025-08/thinkpad-universal-usb-c-dock-datasheet-ww-en.pdf) | 2026-11-15, page fetched | high | Verified |
| `dock-ms-usb4` | video host→hdmi: HDMI-2.0 (14.4 Gbps) | [Microsoft: Surface USB4 Dock - technical overview](https://learn.microsoft.com/en-us/surface/surface-usb4-dock) | 2026-11-15, page fetched | high | Verified |
| `dock-ms-usb4` | video host→usbc-front, host→usbc-rear: DP-Alt-4L-HBR3 (25.92 Gbps) | [Microsoft: Surface USB4 Dock - technical overview](https://learn.microsoft.com/en-us/surface/surface-usb4-dock) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `dock-ms-usb4` | power psu→host: 65 W | [Microsoft: Surface USB4 Dock - technical overview](https://learn.microsoft.com/en-us/surface/surface-usb4-dock) | 2026-11-15, page fetched | high | Verified |
| `adp-framework-hdmi` | video in→hdmi: HDMI-2.0 (14.4 Gbps) | [Framework: HDMI (3rd Gen) Expansion Card](https://frame.work/products/hdmi-expansion-card-gen-3) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `cable-usbc-usb2-60w` | power a→b: 60 W (USB-PD-3A) | [USB-IF: USB-IF Cables and Connectors](https://usb.org/cable_connector) | 2026-11-15, page fetched | high | Verified |
| `cable-usbc-usb2-240w` | power a→b: 240 W (USB-PD-EPR) | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | Verified |
| `cable-usbc-10g-100w` | video a→b: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `cable-usbc-10g-100w` | power a→b: 100 W (USB-PD-5A) | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | Verified |
| `cable-tb4` | video a→b: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to Apple's Thunderbolt cable page (HBR3 video). |
| `cable-tb4` | power a→b: 100 W (USB-PD-5A) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | RE-SOURCED from Wikipedia to Apple's Thunderbolt cable page (100 W). |
| `cable-hdmi-standard` | video a→b: HDMI-Standard-cable (1.782 Gbps) | [HDMI Licensing Administrator: HDMI Cables - Different Cable Types](https://www.hdmi.org/resource/cables) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `cable-hdmi-high-speed` | video a→b: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Cables - Different Cable Types](https://www.hdmi.org/resource/cables) | 2026-11-15, page fetched | medium | DOWNGRADED high to medium: hdmi.org lists 10.2 Gbps, but the HDMI 2.0 release says Category 2 cables carry 18 Gbps. Kept the conservative 10.2 Gbps. |
| `cable-hdmi-premium` | video a→b: HDMI-2.0 (14.4 Gbps) | [HDMI Licensing Administrator: Premium High Speed HDMI Cable certification](https://www.hdmi.org/spec/premiumcable) | 2026-11-15, page fetched | high | Verified |
| `cable-hdmi-ultra` | video a→b: HDMI-2.1-FRL (42.67 Gbps) | [HDMI Licensing Administrator: Ultra High Speed HDMI Cable](https://www.hdmi.org/spec21sub/ultrahighspeedcable) | 2026-11-15, page fetched | high | Verified |
| `cable-dp-hbr2` | video a→b: DP-1.2-HBR2 (17.28 Gbps) | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | medium | RE-SOURCED from Wikipedia to VESA (DPv1.2 = HBR2). |
| `cable-dp8k` | video a→b: DP-1.4-HBR3 (25.92 Gbps) | [VESA: VESA strengthens 8K video resolution ecosystem with DP8K-certified DisplayPort cables (press release)](https://vesa.org/press-releases/vesa-strengthens-8k-video-resolution-ecosystem-with-market-ready-dp8k-certified-displayport-cables/) | 2026-11-15, page fetched | high | FIXED: was DP 2.1 UHBR10 (38.69 Gbps). VESA certifies DP8K at 4-lane HBR3 (25.92 Gbps data). Still enough for 4K60. |
| `cable-usbc-hdmi-4k60` | video c→h: HDMI-2.0 (14.4 Gbps) | [HDMI Licensing Administrator: HDMI Forum releases version 2.0 of the HDMI Specification (press release)](https://www.hdmi.org/press/bodydetails/24) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `cable-usbc-dp14` | video c→d: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `cable-vga` | video a→b: VGA-1200p (3.7 Gbps) | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | low | Analog; no spec body publishes a cable limit. Kept low. |
| `cable-usbc-magsafe3` | power c→m: 140 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-tb4-pro` | video a→b: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-tb4-pro` | power a→b: 100 W (USB-PD-5A) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-tb5-pro` | video a→b: DP-Alt-4L-HBR3 (25.92 Gbps) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-tb5-pro` | power a→b: 240 W (USB-PD-EPR) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-240w` | power a→b: 240 W (USB-PD-EPR) | [Apple: 240W USB-C Charge Cable (2 m)](https://www.apple.com/shop/product/myqt3am/a/240w-usb-c-charge-cable-2-m) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `cable-usb4-240w` | video a→b: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | Verified |
| `cable-usb4-240w` | power a→b: 240 W (USB-PD-EPR) | [USB-IF: USB-IF Cables and Connectors](https://usb.org/cable_connector) | 2026-11-15, page fetched | high | Verified |
| `cable-usbc-5g-60w` | video a→b: DP-Alt-4L-HBR2 (17.28 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `cable-usbc-5g-60w` | power a→b: 60 W (USB-PD-3A) | [USB-IF: USB-IF Cables and Connectors](https://usb.org/cable_connector) | 2026-11-15, page fetched | high | Verified |
| `cable-dp54` | video a→b: DP-2.1-UHBR13.5 (52.22 Gbps) | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | Verified |
| `cable-apple-60w` | power a→b: 60 W (USB-PD-3A) | [Apple: About the Apple Thunderbolt Pro Cables](https://support.apple.com/en-us/118204) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-30w` | power psu→out: 30 W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-35w-dual` | power psu→out: 35 W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-70w` | power psu→out: 70 W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-96w` | power psu→out: 96 W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-140w` | power psu→out: 140 W | [Apple: Fast charge your MacBook Air or MacBook Pro](https://support.apple.com/en-us/102378) | 2026-11-15, page fetched | high | Verified |
| `chg-gen-20w` | power psu→out: 20 W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `chg-gen-65w` | power psu→out: 65 W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `chg-gen-100w` | power psu→out: 100 W | [USB-IF: USB Charger (USB Power Delivery)](https://usb.org/usb-charger-pd) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `chg-apple-20w` | power psu→out: 20 W | [Apple: iPhone 15 - Tech Specs](https://support.apple.com/en-us/111831) | 2026-11-15, page fetched | high | Verified |
| `chg-apple-67w` | power psu→out: 67 W | [Apple: Use a power adapter with your Mac](https://support.apple.com/en-us/109509) | 2026-11-15, page fetched | high | Verified |
| `chg-lenovo-65w` | power psu→out: 65 W | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `chg-lenovo-45w` | power psu→out: 45 W | [Lenovo: ThinkPad T14 Gen 4 (Intel) - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkPad/ThinkPad_T14_Gen_4_Intel/ThinkPad_T14_Gen_4_Intel_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `chg-hp-65w` | power psu→out: 65 W | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `chg-anker-735` | power psu→out: 65 W | [Anker: Anker 735 Charger (Nano II 65W)](https://www.anker.com/products/a2667) | 2026-11-15, page fetched | high | Verified |
| `chg-anker-prime-100w` | power psu→out: 100 W | [Anker: Anker Prime Charger (100W, 3 Ports, GaN)](https://www.anker.com/products/a2688-anker-prime-charger-100w-3-ports-gan) | 2026-11-15, page fetched | high | Verified |
| `chg-hp-45w` | power psu→out: 45 W | [HP: HP EliteBook 840 14 inch G10 - Datasheet](https://www8.hp.com/h20195/v2/GetDocument.aspx?docname=c08488438) | 2026-11-15, page fetched | high | Verified |
| `proj-1080p` | video hdmi→panel: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `proj-1080p` | video vga→panel: VGA-1200p (3.7 Gbps) | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `proj-xga-vga` | video vga→panel: VGA-1200p (3.7 Gbps) | [Wikipedia: VGA connector](https://en.wikipedia.org/wiki/VGA_connector) | 2026-11-15, page fetched | low | Class; 720p input on an XGA projector is assumed (low). Real example: Epson PowerLite 118. |
| `tv-4k-hdmi20` | video hdmi1→panel, hdmi2→panel: HDMI-2.0 (14.4 Gbps) | [HDMI Licensing Administrator: HDMI Forum releases version 2.0 of the HDMI Specification (press release)](https://www.hdmi.org/press/bodydetails/24) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `tv-4k-hdmi21` | video hdmi→panel: HDMI-2.1-FRL (42.67 Gbps) | [HDMI Licensing Administrator: Ultra High Speed HDMI Cable](https://www.hdmi.org/spec21sub/ultrahighspeedcable) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `disp-4k-hdmi14` | video hdmi→panel: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | medium | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-4k-multi` | video dp→panel: DP-1.4-HBR3 (25.92 Gbps) | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-4k-multi` | video hdmi→panel: HDMI-2.0 (14.4 Gbps) | [HDMI Licensing Administrator: HDMI Forum releases version 2.0 of the HDMI Specification (press release)](https://www.hdmi.org/press/bodydetails/24) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-4k-multi` | video usbc→panel: DP-Alt-4L-HBR3 (25.92 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-1440p` | video dp→panel: DP-1.2-HBR2 (17.28 Gbps) | [VESA: VESA Tokyo Workshop, October 2024 (DisplayPort and cable certification overview)](https://vesa.org/wp-content/uploads/2024/10/VESA-Tokyo-Workshop_October-2024.pdf) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-1440p` | video hdmi→panel: HDMI-1.4 (8.16 Gbps) | [HDMI Licensing Administrator: HDMI Specification 1.4b](https://www.hdmi.org/spec/hdmi1_4b) | 2026-11-15, page fetched | high | RE-SOURCED: was the repo-internal 'class-assumption' note (a private URL); now the public page of the standard the class claims. Limit unchanged. |
| `mon-portable-1080p` | video usbc→panel: DP-Alt-2L-HBR3 (12.96 Gbps) | [VESA: DisplayPort Alt Mode over USB Type-C (USB DevDays 2019)](https://www.vesa.org/wp-content/uploads/2019/10/USB-DevDays-2019-VESA-DP-Alt-Mode-over-USB-Type-C.pdf) | 2026-11-15, page fetched | low | Class; lane count rarely published. Kept low. |
| `mon-lenovo-t27h30` | video usbc→panel: DP-Alt-2L-HBR3 (12.96 Gbps) | [Lenovo: ThinkVision T27h-30 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_T27h_30/ThinkVision_T27h_30_Spec.pdf) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mon-lenovo-t27h30` | video hdmi→panel: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkVision T27h-30 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_T27h_30/ThinkVision_T27h_30_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lenovo-t27h30` | video dp→panel: DP-1.4-HBR3 (25.92 Gbps) | [Lenovo: ThinkVision T27h-30 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_T27h_30/ThinkVision_T27h_30_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lenovo-t27h30` | power psu→usbc: 90 W | [Lenovo: ThinkVision T27h-30 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_T27h_30/ThinkVision_T27h_30_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lenovo-p27u20` | video tb-in→panel: DP-Alt-4L-HBR3 (25.92 Gbps) | [Lenovo: ThinkVision P27u-20 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_P27u_20/ThinkVision_P27u_20_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lenovo-p27u20` | video hdmi1→panel, hdmi2→panel: HDMI-2.0 (14.4 Gbps) | [Lenovo: ThinkVision P27u-20 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_P27u_20/ThinkVision_P27u_20_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lenovo-p27u20` | video dp→panel: DP-1.2-HBR2 (17.28 Gbps) | [Lenovo: ThinkVision P27u-20 - PSREF](https://psref.lenovo.com/syspool/Sys/PDF/ThinkVision/ThinkVision_P27u_20/ThinkVision_P27u_20_Spec.pdf) | 2026-11-15, page fetched | high | Verified |
| `mon-lg-27up850` | video usbc→panel: DP-Alt-4L-HBR3 (25.92 Gbps) | [LG: LG 27UP850-W 27" UHD 4K IPS monitor - specifications](https://www.lg.com/uk/monitors/uhd-4k-5k/27up850-w/) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `mon-lg-27up850` | video hdmi1→panel, hdmi2→panel: HDMI-2.0 (14.4 Gbps) | [LG: LG 27UP850-W 27" UHD 4K IPS monitor - specifications](https://www.lg.com/uk/monitors/uhd-4k-5k/27up850-w/) | 2026-11-15, page fetched | high | Verified |
| `mon-lg-27up850` | video dp→panel: DP-1.4-HBR3 (25.92 Gbps) | [LG: LG 27UP850-W 27" UHD 4K IPS monitor - specifications](https://www.lg.com/uk/monitors/uhd-4k-5k/27up850-w/) | 2026-11-15, page fetched | high | Verified |
| `mon-lg-27up850` | power psu→usbc: 96 W | [LG: LG 27UP850-W 27" UHD 4K IPS monitor - specifications](https://www.lg.com/uk/monitors/uhd-4k-5k/27up850-w/) | 2026-11-15, page fetched | high | Verified |
| `mon-dell-p2723qe` | video usbc→panel: DP-Alt-4L-HBR3 (25.92 Gbps) | [Dell: Dell 27 4K USB-C Hub Monitor - P2723QE](https://www.dell.com/en-us/shop/dell-27-4k-usb-c-hub-monitor-p2723qe/apd/210-bdlk/monitors-monitor-accessories) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `mon-dell-p2723qe` | video hdmi→panel: HDMI-2.0 (14.4 Gbps) | [Dell: Dell 27 4K USB-C Hub Monitor - P2723QE](https://www.dell.com/en-us/shop/dell-27-4k-usb-c-hub-monitor-p2723qe/apd/210-bdlk/monitors-monitor-accessories) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `mon-dell-p2723qe` | video dp→panel: DP-1.4-HBR3 (25.92 Gbps) | [Dell: Dell 27 4K USB-C Hub Monitor - P2723QE](https://www.dell.com/en-us/shop/dell-27-4k-usb-c-hub-monitor-p2723qe/apd/210-bdlk/monitors-monitor-accessories) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `mon-dell-p2723qe` | power psu→usbc: 90 W | [Dell: Dell 27 4K USB-C Hub Monitor - P2723QE](https://www.dell.com/en-us/shop/dell-27-4k-usb-c-hub-monitor-p2723qe/apd/210-bdlk/monitors-monitor-accessories) | 2026-11-15, search extract | medium | Verified source; value partly inferred (site blocks scripted fetch) |
| `proj-epson-2250u` | video hdmi1→panel, hdmi2→panel: HDMI-1.4 (8.16 Gbps) | [Epson: PowerLite 2250U Full HD WUXGA 3LCD Projector - specification sheet](https://files.support.epson.com/docid/cpd5/cpd53093.pdf) | 2026-11-15, page fetched | medium | Verified 1080p over HDMI; HDMI version not published, so medium. |
| `proj-epson-2250u` | video vga→panel: VGA-1200p (3.7 Gbps) | [Epson: PowerLite 2250U Full HD WUXGA 3LCD Projector - specification sheet](https://files.support.epson.com/docid/cpd5/cpd53093.pdf) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `proj-epson-118` | video hdmi→panel: HDMI-1.4 (8.16 Gbps) | [Epson: PowerLite 118 3LCD XGA Classroom Projector - specification sheet](https://mediaserver.goepson.com/ImConvServlet/imconv/12d3ce5619f0521940bf4c07116acc0915c3ebf4/original?assetDescr=PowerLite-118-Projector_Specification-Sheet-CPD-58835.pdf) | 2026-11-15, page fetched | medium | Verified HDMI inputs and XGA panel; HDMI version not published, so medium. |
| `proj-epson-118` | video vga→panel: VGA-1200p (3.7 Gbps) | [Epson: PowerLite 118 3LCD XGA Classroom Projector - specification sheet](https://mediaserver.goepson.com/ImConvServlet/imconv/12d3ce5619f0521940bf4c07116acc0915c3ebf4/original?assetDescr=PowerLite-118-Projector_Specification-Sheet-CPD-58835.pdf) | 2026-11-15, page fetched | medium | Verified source; value partly inferred |
| `proj-benq-mh560` | video hdmi1→panel, hdmi2→panel: HDMI-1.4 (8.16 Gbps) | [BenQ: BenQ MH560 - specifications](https://www.benq.com/en-in/business/projector/mh560/specifications.html) | 2026-11-15, page fetched | high | Verified |
| `proj-benq-mh560` | video vga→panel: VGA-1200p (3.7 Gbps) | [BenQ: BenQ MH560 - specifications](https://www.benq.com/en-in/business/projector/mh560/specifications.html) | 2026-11-15, page fetched | high | Verified |
<!-- AUDIT:END -->
