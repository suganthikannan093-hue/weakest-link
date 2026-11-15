#!/usr/bin/env python3
"""Transcribe each narration clip with OpenAI Whisper (word timestamps) and check it against the script.

Writes $WL_VIDEO_WORK/words.json: {scene: {"words": [{word,start,end}], "text": ..., "match": ratio}}.
Exits non-zero if a clip repeats or drops words (match < 0.97 or extra words). Never prints the key."""
import difflib, json, os, re, sys, uuid, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(os.environ.get("WL_VIDEO_WORK", "/workspace/wlvideo-work"))
norm = lambda s: re.findall(r"[a-z0-9]+", s.lower().replace("4k", "4k").replace("1.4", "1 4"))


def transcribe(path, key):
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("model", "whisper-1"), ("response_format", "verbose_json"), ("timestamp_granularities[]", "word"), ("language", "en")):
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode()
                 + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=b"".join(parts), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": f"multipart/form-data; boundary={b}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"transcription failed for {path.name}: HTTP {e.code}") from None


def main():
    key = os.environ["OPENAI_API_KEY"]
    cfg = json.loads((HERE / "narration.json").read_text())
    only = set(sys.argv[1:])
    path = WORK / "words.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    bad = []
    for s in cfg["scenes"]:
        if only and s["id"] not in only and s["id"] in res:
            continue
        j = transcribe(WORK / "tts" / f"{s['id']}.mp3", key)
        a, b = norm(s["text"]), norm(j["text"])
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        res[s["id"]] = {"text": j["text"], "words": j.get("words", []), "match": round(ratio, 3),
                        "script_words": len(a), "heard_words": len(b)}
        flag = ratio < 0.95 or len(b) > len(a) + 1
        print(f"{s['id']:8} match {ratio:.3f} words {len(b)}/{len(a)} {'REPEAT/DROP?' if flag else 'ok'}")
        if flag:
            print("   heard:", j["text"])
            bad.append(s["id"])
    path.write_text(json.dumps(res, indent=1))
    if bad:
        raise SystemExit(f"clips to regenerate: {' '.join(bad)}")


if __name__ == "__main__":
    main()
