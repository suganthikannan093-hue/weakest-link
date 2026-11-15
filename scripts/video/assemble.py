#!/usr/bin/env python3
"""Assemble the demo video (v2): recorded scenes + TTS narration + burned-in captions timed from
Whisper word timestamps, plus programmatic checks.

Writes docs/submission/weakest-link-demo-v2.{mp4,srt}, script-v2.md, verification-v2.json and a
contact sheet of frames every 5 s in docs/submission/v2-frames/.
Inputs (in $WL_VIDEO_WORK): tts/*.mp3 + tts_durations.json (tts.py), words.json (transcribe.py),
scenes/*.mp4 (record.mjs).
"""
import difflib, hashlib, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
WORK = Path(os.environ.get("WL_VIDEO_WORK", "/workspace/wlvideo-work"))
OUT = ROOT / "docs" / "submission"
NAME = "weakest-link-demo-v2"
T = json.loads((HERE / "timing.json").read_text())
LEAD = T["lead"]
tail = lambda sid: T["tail"].get(sid, T["tail"]["default"])
BG = "0x0b1120"
CW, CH, CX, CY = 1664, 936, 128, 8  # content box; the band below holds the captions
MAX_SECONDS = 105.0
tok = lambda s: re.findall(r"[a-z0-9]+", s.lower())


def sh(*a):
    return subprocess.run(a, check=True, text=True, capture_output=True)


def dur(p):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)).stdout)


def split_cues(text, limit=80):
    """Sentences, long ones cut at clause breaks; a very short cue joins the NEXT one when it fits."""
    out = []
    for p in re.split(r"(?<=[.?!])\s+", text.strip()):
        while len(p) > limit:
            cut = max(p.rfind(", ", 0, limit), p.rfind(": ", 0, limit))
            if cut < 25:
                cut = p.rfind(" ", 0, limit)
            out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
        out.append(p)
    merged, i = [], 0
    while i < len(out):
        c = out[i]
        if len(c) < 20 and i + 1 < len(out) and len(c) + 1 + len(out[i + 1]) <= limit:
            merged.append(c + " " + out[i + 1]); i += 2
        else:
            merged.append(c); i += 1
    return merged


def cue_times(text, words):
    """(start, end) of each cue within the clip, from Whisper word timestamps aligned to the script."""
    cues = split_cues(text)
    stoks, owner = [], []
    for k, c in enumerate(cues):
        for t_ in tok(c):
            stoks.append(t_); owner.append(k)
    wtoks, wt = [], []
    for w in words:
        for t_ in tok(w["word"]):
            wtoks.append(t_); wt.append((w["start"], w["end"]))
    m = {}
    for a, b, n in difflib.SequenceMatcher(None, stoks, wtoks, autojunk=False).get_matching_blocks():
        for j in range(n):
            m[a + j] = b + j
    res = []
    for k, c in enumerate(cues):
        idx = [m[i] for i in range(len(stoks)) if owner[i] == k and i in m]
        if not idx:
            raise SystemExit(f"cue not found in the transcript: {c!r}")
        res.append([c, wt[min(idx)][0], wt[max(idx)][1], len(idx), sum(1 for o in owner if o == k)])
    return res


def ts(t, ass=False):
    if ass:
        h, r = divmod(t, 3600); m_, s = divmod(r, 60)
        return f"{int(h)}:{int(m_):02d}:{s:05.2f}"
    ms = int(round(t * 1000)); h, ms = divmod(ms, 3600000); m_, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m_:02d}:{s:02d},{ms:03d}"


def agent_fx():
    """digital zoom on the answer block, plus highlight boxes on the key lines, in source pixels"""
    A = T["agent"]; z = A["zoom"]; row = A["row_px"]
    p = f"clip((in_time-{z['start']})/{z['ramp']},0,1)"
    zoom = f"1+({z['factor']}-1)*{p}*{p}*(3-2*{p})"
    boxes = ",".join(
        f"drawbox=x=24:y={b['rows'][0] * row + 1:.0f}:w=1572:h={(b['rows'][1] - b['rows'][0] + 1) * row + 2:.0f}"
        f":color=0x5cb3ff@0.95:t=3:enable='between(t,{b['from']},{b['to']})'" for b in A["boxes"])
    # zoompan with d=1 maps each input frame to one output frame; render at 2x first so the zoom stays smooth
    return (f"{boxes},scale=3840:2160:flags=lanczos,zoompan=z='{zoom}':d=1:fps=30:s=1920x1080"
            f":x='(iw-iw/zoom)*{z['focus_x']}':y='(ih-ih/zoom)*{z['focus_y']}'")


def main():
    cfg = json.loads((HERE / "narration.json").read_text())
    durs = json.loads((WORK / "tts_durations.json").read_text())
    words = json.loads((WORK / "words.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    checks = []
    check = lambda name, ok, detail="": checks.append({"check": name, "pass": bool(ok), "detail": detail})

    scenes, t = [], 0.0
    for s in cfg["scenes"]:
        length = round(durs[s["id"]] + LEAD + tail(s["id"]), 3)
        rec = WORK / "scenes" / f"{s['id']}.mp4"
        if dur(rec) < length - 0.05:
            raise SystemExit(f"{s['id']}: recording is {dur(rec):.2f}s, needs {length:.2f}s")
        scenes.append({**s, "start": round(t, 3), "length": length, "speech": durs[s["id"]], "file": rec,
                       "clip": [round(t + LEAD, 3), round(t + LEAD + durs[s["id"]], 3)]})
        t += length
    total = t

    # 1) narration clips: exactly one voice at a time
    gaps = [round(b["clip"][0] - a["clip"][1], 3) for a, b in zip(scenes, scenes[1:])]
    inside = all(s["clip"][0] >= s["start"] and s["clip"][1] <= s["start"] + s["length"] for s in scenes)
    check("narration clips never overlap (placement)", min(gaps) > 0 and inside, f"minimum gap {min(gaps):.3f} s")
    for s in scenes:
        w = words[s["id"]]
        check(f"clip '{s['id']}' says the script once, no repeats or drops (Whisper)", w["match"] >= 0.97 and w["heard_words"] <= w["script_words"] + 1,
              f"match {w['match']}, {w['heard_words']}/{w['script_words']} words")

    # 6) captions from word timestamps, each inside its own scene's clip
    cues = []
    for s in scenes:
        ct = cue_times(s["text"], words[s["id"]]["words"])
        for k, (txt, a, b, found, n) in enumerate(ct):
            st_ = s["clip"][0] + a - 0.05
            nxt = s["clip"][0] + ct[k + 1][1] - 0.05 if k + 1 < len(ct) else s["start"] + s["length"] - 0.1
            en = min(s["clip"][0] + b + 0.35, nxt - 0.04)
            cues.append({"scene": s["id"], "start": round(st_, 3), "end": round(en, 3), "text": txt, "aligned_words": f"{found}/{n}"})
    bad_scene = [c["text"] for c in cues for s in scenes if c["scene"] == s["id"] and not (s["start"] <= c["start"] < c["end"] <= s["start"] + s["length"])]
    overl = [(a["text"], b["text"]) for a, b in zip(cues, cues[1:]) if b["start"] < a["end"]]
    check("every caption lies inside its own scene", not bad_scene, f"{len(cues)} cues")
    check("captions never overlap", not overl, f"min gap {min(b['start'] - a['end'] for a, b in zip(cues, cues[1:])):.3f} s")
    check("captions timed from Whisper word timestamps", all(c["aligned_words"].split('/')[0] == c["aligned_words"].split('/')[1] for c in cues),
          "every script word of every cue found in the clip's transcript")
    (OUT / f"{NAME}.srt").write_text("\n".join(f"{i}\n{ts(c['start'])} --> {ts(c['end'])}\n{c['text']}\n" for i, c in enumerate(cues, 1)))
    ass = WORK / "captions-v2.ass"
    ass.write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,DejaVu Sans,42,&H00FFFFFF,&H00FFFFFF,&H0020110B,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,200,200,24,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "".join(f"Dialogue: 0,{ts(c['start'], True)},{ts(c['end'], True)},Cap,,0,0,0,,{c['text']}\n" for c in cues))

    # video + audio. The narration is ONE mono track: each clip delayed by LEAD and padded to its scene.
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for s in scenes:
        args += ["-i", str(s["file"])]
    for s in scenes:
        args += ["-i", str(WORK / "tts" / f"{s['id']}.mp3")]
    fc = []
    for i, s in enumerate(scenes):
        L = s["length"]
        fx = agent_fx() + "," if s["id"] == "agent" else ""
        fc.append(f"[{i}:v]trim=0:{L},setpts=PTS-STARTPTS,fps=30,{fx}scale={CW}:{CH}:flags=lanczos,"
                  f"pad=1920:1080:{CX}:{CY}:color={BG},format=yuv420p,setsar=1,"
                  f"fade=t=in:st=0:d=0.25:color={BG},fade=t=out:st={L - 0.25:.3f}:d=0.25:color={BG}[v{i}]")
        k = len(scenes) + i
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,adelay={int(LEAD * 1000)},apad,atrim=0:{L},asetpts=PTS-STARTPTS[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(len(scenes))) + f"concat=n={len(scenes)}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]subtitles={ass}[vout]")
    fc.append("[ac]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=channel_layouts=stereo[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(mp4)]
    subprocess.run(args, check=True)

    # loudnorm is single-pass; trim any residual offset from -16 LUFS with a plain gain (video copied)
    def integrated():
        m_ = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128", "-f", "null", "-"], text=True, capture_output=True).stderr
        return float(re.search(r"I:\s+(-?[\d.]+) LUFS", m_[m_.rfind("Summary:"):]).group(1))
    off = -16.0 - integrated()
    if abs(off) > 0.2:
        tmp = mp4.with_suffix(".tmp.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-c:v", "copy", "-af", f"volume={off:.2f}dB",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(tmp)], check=True)
        tmp.replace(mp4)

    # measurements
    meter = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           text=True, capture_output=True).stderr
    summ = meter[meter.rfind("Summary:"):]
    num = lambda pat: float(re.search(pat, summ).group(1))
    probe = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size",
                          "-of", "json", str(mp4)).stdout)
    v = next(x for x in probe["streams"] if x["codec_type"] == "video")
    a = next(x for x in probe["streams"] if x["codec_type"] == "audio")
    D = float(probe["format"]["duration"])
    loud = {"integrated_lufs": num(r"I:\s+(-?[\d.]+) LUFS"), "loudness_range_lu": num(r"LRA:\s+(-?[\d.]+) LU"),
            "true_peak_dbtp": num(r"Peak:\s+(-?[\d.]+) dBFS"), "target_lufs": -16, "measured_with": "ffmpeg ebur128=peak=true"}
    check("duration at most 1:45", D <= MAX_SECONDS, f"{D:.2f} s")
    check("loudness about -16 LUFS integrated, true peak below -1 dBTP", abs(loud["integrated_lufs"] + 16) <= 1 and loud["true_peak_dbtp"] <= -1.0,
          f"{loud['integrated_lufs']} LUFS, {loud['true_peak_dbtp']} dBTP")

    # measured from the final mix: speech islands between silences must match the 7 clips
    sd = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "silencedetect=n=-45dB:d=0.5", "-f", "null", "-"],
                        text=True, capture_output=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", sd)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sd)]
    long_sil = [(s_, e_) for s_, e_ in zip(starts, ends) if e_ - s_ >= 0.9]
    between = [g for g in long_sil if g[0] > scenes[0]["clip"][0] + 1]
    check("final mix: a silence of at least 0.9 s between every pair of clips (silencedetect)",
          all(any(g[0] <= sc["clip"][1] + 0.3 and g[1] >= nx["clip"][0] - 0.3 for g in between) for sc, nx in zip(scenes, scenes[1:])),
          f"{len(long_sil)} silences of 0.9 s or more")
    # the full mix transcribed: the scripted text appears exactly once, in order (catches doubled phrases)
    import transcribe as TR
    seg = WORK / "v2-mix.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vn", "-ac", "1", "-b:a", "64k", str(seg)], check=True)
    heard = TR.transcribe(seg, os.environ["OPENAI_API_KEY"])
    script_toks = [x for s in scenes for x in tok(s["text"])]
    heard_toks = tok(heard["text"])
    ratio = difflib.SequenceMatcher(None, script_toks, heard_toks, autojunk=False).ratio()
    pi = heard["text"].lower().count("projector input")
    check("final mix transcript matches the script (no doubled narration)", ratio >= 0.95 and len(heard_toks) <= len(script_toks) + 3 and pi == 1,
          f"match {ratio:.3f}, {len(heard_toks)}/{len(script_toks)} words, 'projector input' heard {pi}x")
    # idle tail: the agent scene ends within 1 s of its narration
    ag = next(s for s in scenes if s["id"] == "agent")
    check("no idle terminal after the agent narration", ag["start"] + ag["length"] - ag["clip"][1] <= 1.0,
          f"{ag['start'] + ag['length'] - ag['clip'][1]:.2f} s after the last word")

    # contact sheet: a frame every 5 s
    fr = OUT / "v2-frames"; fr.mkdir(exist_ok=True)
    for old in fr.glob("*.jpg"):
        old.unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=1/5,scale=640:-1", "-q:v", "4", str(fr / "t%03d.jpg")], check=True)
    files = sorted(fr.glob("t*.jpg"))
    for k, f in enumerate(files):  # name by timestamp: frame k is at k*5 s (first at 0 s... ffmpeg fps picks centres)
        f.rename(fr / f"at-{k * 5:03d}s.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "fps=1/5,scale=480:-1,tile=4x6:padding=6:color=white", "-frames:v", "1",
                    str(fr / "contact-sheet.jpg")], check=True)

    ver = {
        "file": f"docs/submission/{NAME}.mp4",
        "status": "DRAFT v2 for the owner's review. Not uploaded anywhere.",
        "duration_seconds": round(D, 2), "duration_limit_seconds": MAX_SECONDS,
        "size_bytes": int(probe["format"]["size"]), "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(),
        "video": {"codec": v["codec_name"], "width": v["width"], "height": v["height"], "fps": v["r_frame_rate"]},
        "audio": {"codec": a["codec_name"], "sample_rate": int(a["sample_rate"]), "channels": a["channels"], "narration": "one mono voice track, upmixed"},
        "loudness": loud,
        "narration": {**cfg["voice"], "engine": "OpenAI TTS", "speech_seconds": round(sum(durs.values()), 2),
                      "min_gap_between_clips_seconds": min(gaps), "clips": [{"id": s["id"], "start": s["clip"][0], "end": s["clip"][1]} for s in scenes]},
        "captions": {"burned_in": True, "srt": f"docs/submission/{NAME}.srt", "cues": len(cues), "timing": "Whisper (whisper-1) word timestamps per clip"},
        "capture": "Xvfb 1920x1200 + ffmpeg x11grab: Chromium (Playwright) on the local vite preview build at 1.25x, and xfce4-terminal "
                   f"(DejaVu Sans Mono {T['agent']['font_pt']} pt, {T['agent']['cols']} columns) running scripts/agent_demo.py --brief --pace {T['agent']['pace']}",
        "scenes": [{"id": s["id"], "start": s["start"], "end": round(s["start"] + s["length"], 3)} for s in scenes],
        "checks": checks,
        "all_checks_pass": all(c["pass"] for c in checks),
    }
    (OUT / "verification-v2.json").write_text(json.dumps(ver, indent=2) + "\n")
    mmss = lambda x: f"{int(x // 60)}:{x % 60:04.1f}"
    rows = "\n".join(f"| {mmss(s['start'])}–{mmss(s['start'] + s['length'])} | {s['id']} | {s['visual']} | {s['text']} |" for s in scenes)
    (OUT / "script-v2.md").write_text(f"""# Demo video script, v2 (DRAFT)

Draft for Suganthi's review only. It has not been uploaded anywhere.

- Video: [`{NAME}.mp4`]({NAME}.mp4), {D:.1f} s, 1920×1080, 30 fps. Captions are burned in and also in [`{NAME}.srt`]({NAME}.srt).
- Narration: OpenAI TTS, `{cfg['voice']['model']}`, voice `{cfg['voice']['voice']}`, one mono voice track normalized to -16 LUFS.
  Captions are timed from Whisper word timestamps. Checks: [`verification-v2.json`](verification-v2.json). Frames every 5 s: [`v2-frames/`](v2-frames/).
- Rebuild: `scripts/video/tts.py` → `transcribe.py` → `record.mjs` (Xvfb + local `vite preview`) → `assemble.py`.

## Changes from the first draft

1. Narration: one voice track, clips placed back to back with at least {min(gaps):.1f} s between them; checked by placement, silence detection and a transcript of the final mix.
2. No drawn pointer. Emphasis is a highlight box around the element being discussed; clicks get a short pause and a ripple.
3. The UI flow starts from a working bag and never shows an empty or error state (the app does update live while ticking; there is now an e2e test for it).
4. Terminal: `agent_demo.py --brief`, a {T['agent']['font_pt']} pt font in a {T['agent']['cols']}-column terminal (no wrapping), a digital zoom on the answer and highlight boxes on the pack, leave, buy and charging lines.
5. No idle terminal: the agent scene ends {ag['start'] + ag['length'] - ag['clip'][1]:.1f} s after its last word.
6. Captions come from each clip's own word timestamps and never cross a scene boundary.

| Time | Scene | On screen | Narration |
|---|---|---|---|
{rows}
""")
    print(json.dumps({"duration": round(D, 2), "min_gap": min(gaps), "loudness": loud, "checks": [(c["check"], c["pass"], c["detail"]) for c in checks]}, indent=1))
    if not ver["all_checks_pass"]:
        raise SystemExit("some checks failed")


if __name__ == "__main__":
    main()
