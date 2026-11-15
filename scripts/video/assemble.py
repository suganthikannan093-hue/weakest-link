#!/usr/bin/env python3
"""Assemble the draft demo video: recorded scenes + TTS narration + burned-in captions.

Writes docs/submission/weakest-link-demo-draft.{mp4,srt}, script.md and verification.json.
Inputs come from tts.py and record.mjs in $WL_VIDEO_WORK (default /workspace/wlvideo-work).
"""
import hashlib, json, os, re, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = Path(os.environ.get("WL_VIDEO_WORK", "/workspace/wlvideo-work"))
OUT = ROOT / "docs" / "submission"
NAME = "weakest-link-demo-draft"
LEAD, TAIL = 0.6, 0.9
EXTRA = {"hook": 0.2, "agent": 1.5, "close": 0.6}  # must match record.mjs
BG = "0x0b1120"
# content box inside the 1920x1080 frame; the band below it holds the captions
CW, CH, CX, CY = 1664, 936, 128, 8
MAX_SECONDS = 105.0


def sh(*a, **k):
    return subprocess.run(a, check=True, text=True, capture_output=True, **k)


def dur(p):
    return float(sh("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)).stdout)


def chunks(text, limit=84):
    """Split narration into caption cues of at most `limit` characters, at sentence or clause breaks."""
    parts = re.split(r"(?<=[.?!])\s+", text.strip())
    out = []
    for p in parts:
        while len(p) > limit:
            cut = max(p.rfind(", ", 0, limit), p.rfind(": ", 0, limit))
            if cut < 25:
                cut = p.rfind(" ", 0, limit)
            out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
        out.append(p)
    merged = []
    for c in out:  # glue very short cues to the previous one
        if merged and len(c) < 18 and len(merged[-1]) + len(c) + 1 <= limit:
            merged[-1] += " " + c
        else:
            merged.append(c)
    return merged


def ts(t, sep=","):
    h, r = divmod(t, 3600); m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}" if sep == "," else \
        f"{int(h)}:{int(m):02d}:{s:05.2f}"


def main():
    cfg = json.loads((HERE / "narration.json").read_text())
    durs = json.loads((WORK / "tts_durations.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    scenes, t = [], 0.0
    for s in cfg["scenes"]:
        length = round(durs[s["id"]] + LEAD + TAIL + EXTRA.get(s["id"], 0), 3)
        rec = WORK / "scenes" / f"{s['id']}.mp4"
        have = dur(rec)
        if have < length - 0.05:
            raise SystemExit(f"{s['id']}: recording is {have:.2f}s, needs {length:.2f}s")
        scenes.append({**s, "start": round(t, 3), "length": length, "speech": durs[s["id"]], "file": rec})
        t += length
    total = t
    if total > MAX_SECONDS:
        raise SystemExit(f"total {total:.1f}s is over {MAX_SECONDS}s")

    # captions: cue timing proportional to characters within each scene's speech
    cues = []
    for s in scenes:
        parts = chunks(s["text"])
        n = sum(len(p) for p in parts)
        a = s["start"] + LEAD
        for j, p in enumerate(parts):
            b = a + s["speech"] * len(p) / n
            last = j == len(parts) - 1  # hold the scene's last cue a moment; never overlap the next cue
            cues.append((a, min(b + 0.3, s["start"] + s["length"] - 0.05) if last else b - 0.02, p))
            a = b
    srt = "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n" for i, (a, b, txt) in enumerate(cues, 1))
    (OUT / f"{NAME}.srt").write_text(srt)
    ass = WORK / "captions.ass"
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
""" + "".join(f"Dialogue: 0,{ts(a, '.')},{ts(b, '.')},Cap,,0,0,0,,{txt}\n" for a, b, txt in cues))

    # video: each scene trimmed to length, boxed into the frame, short fades between scenes
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for s in scenes:
        args += ["-i", str(s["file"])]
    for s in scenes:
        args += ["-i", str(WORK / "tts" / f"{s['id']}.mp3")]
    fc = []
    for i, s in enumerate(scenes):
        L = s["length"]
        fc.append(f"[{i}:v]trim=0:{L},setpts=PTS-STARTPTS,fps=30,scale={CW}:{CH}:flags=lanczos,"
                  f"pad=1920:1080:{CX}:{CY}:color={BG},format=yuv420p,"
                  f"fade=t=in:st=0:d=0.25:color={BG},fade=t=out:st={L - 0.25:.3f}:d=0.25:color={BG}[v{i}]")
        k = len(scenes) + i
        fc.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={int(LEAD * 1000)}|{int(LEAD * 1000)},"
                  f"apad,atrim=0:{L},asetpts=PTS-STARTPTS[a{i}]")
    fc.append("".join(f"[v{i}][a{i}]" for i in range(len(scenes))) + f"concat=n={len(scenes)}:v=1:a=1[vc][ac]")
    fc.append(f"[vc]subtitles={ass}[vout]")
    fc.append("[ac]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[aout]")
    mp4 = OUT / f"{NAME}.mp4"
    args += ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(mp4)]
    subprocess.run(args, check=True)

    # verification
    meter = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(mp4), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           text=True, capture_output=True).stderr
    summary = meter[meter.rfind("Summary:"):]
    num = lambda pat: float(re.search(pat, summary).group(1))
    probe = json.loads(sh("ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size",
                          "-of", "json", str(mp4)).stdout)
    v = next(x for x in probe["streams"] if x["codec_type"] == "video")
    a = next(x for x in probe["streams"] if x["codec_type"] == "audio")
    D = float(probe["format"]["duration"])
    ver = {
        "file": f"docs/submission/{NAME}.mp4",
        "status": "DRAFT for the owner's review. Not uploaded anywhere.",
        "duration_seconds": round(D, 2),
        "duration_limit_seconds": MAX_SECONDS,
        "within_limit": D <= MAX_SECONDS,
        "size_bytes": int(probe["format"]["size"]),
        "sha256": hashlib.sha256(mp4.read_bytes()).hexdigest(),
        "video": {"codec": v["codec_name"], "width": v["width"], "height": v["height"], "fps": v["r_frame_rate"]},
        "audio": {"codec": a["codec_name"], "sample_rate": int(a["sample_rate"]), "channels": a["channels"]},
        "loudness": {"integrated_lufs": num(r"I:\s+(-?[\d.]+) LUFS"), "loudness_range_lu": num(r"LRA:\s+(-?[\d.]+) LU"),
                     "true_peak_dbtp": num(r"Peak:\s+(-?[\d.]+) dBFS"), "target_lufs": -16, "measured_with": "ffmpeg ebur128=peak=true"},
        "narration": {**cfg["voice"], "engine": "OpenAI TTS", "speech_seconds": round(sum(durs.values()), 2)},
        "captions": {"burned_in": True, "srt": f"docs/submission/{NAME}.srt", "cues": len(cues)},
        "capture": "Xvfb 1920x1200 + ffmpeg x11grab: Chromium (Playwright) on the local vite preview build at 1.25x, and xfce4-terminal running scripts/agent_demo.py --pace 1.6",
        "scenes": [{"id": s["id"], "start": s["start"], "end": round(s["start"] + s["length"], 3), "speech_seconds": s["speech"]} for s in scenes],
    }
    (OUT / "verification.json").write_text(json.dumps(ver, indent=2) + "\n")

    rows = "\n".join(f"| {ts(s['start'], '.')[2:7]}–{ts(s['start'] + s['length'], '.')[2:7]} | {s['id']} | {s['visual']} | {s['text']} |" for s in scenes)
    (OUT / "script.md").write_text(f"""# Demo video script (DRAFT)

Draft for Suganthi's review only. It has not been uploaded anywhere.

- Video: [`{NAME}.mp4`]({NAME}.mp4), {D:.1f} s, 1920×1080, 30 fps. Captions are burned in and also in [`{NAME}.srt`]({NAME}.srt).
- Narration: OpenAI TTS, `{cfg['voice']['model']}`, voice `{cfg['voice']['voice']}`, normalized to -16 LUFS. The measurements are in [`verification.json`](verification.json).
- Source of the narration: [`scripts/video/narration.json`](../../scripts/video/narration.json). To rebuild: `scripts/video/tts.py`,
  then `scripts/video/record.mjs` (Xvfb + local `vite preview`), then `scripts/video/assemble.py`.

| Time | Scene | On screen | Narration |
|---|---|---|---|
{rows}
""")
    print(json.dumps({k: ver[k] for k in ("duration_seconds", "size_bytes", "loudness")}, indent=1))


if __name__ == "__main__":
    main()
