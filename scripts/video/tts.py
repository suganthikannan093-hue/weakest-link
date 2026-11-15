#!/usr/bin/env python3
"""Generate the narration clips for the demo video with OpenAI TTS (tts-1-hd, nova). Never prints the key."""
import json, os, subprocess, sys, urllib.error, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("WL_VIDEO_WORK", "/workspace/wlvideo-work"))


def duration(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], text=True))


def main():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY missing: the video will have captions only")
    cfg = json.loads((HERE / "narration.json").read_text())
    out = WORK / "tts"; out.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    durs = {}
    for s in cfg["scenes"]:
        dest = out / f"{s['id']}.mp3"
        if (not only or s["id"] in only) or not dest.exists():
            body = json.dumps({**cfg["voice"], "input": s["text"], "response_format": "mp3"}).encode()
            req = urllib.request.Request("https://api.openai.com/v1/audio/speech", data=body, method="POST",
                                         headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    dest.write_bytes(r.read())
            except urllib.error.HTTPError as e:
                raise SystemExit(f"TTS failed for {s['id']}: HTTP {e.code}") from None
        durs[s["id"]] = round(duration(dest), 3)
    (WORK / "tts_durations.json").write_text(json.dumps(durs, indent=1))
    print(json.dumps(durs), "total", round(sum(durs.values()), 2))


if __name__ == "__main__":
    main()
