import json, math, re, subprocess, unicodedata
from pathlib import Path
from faster_whisper import WhisperModel

AUDIO = Path("a_song_vocals.mp3")
EXPECTED = 163.920
SCENES = 30
MASTER_URL = "https://d1ojnqroiei5k7.cloudfront.net/melipo/music/A/v1/a_song_vocals.mp3"

probe = subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration",
    "-of","default=noprint_wrappers=1:nokey=1",str(AUDIO)
], text=True).strip()
duration = float(probe)
if abs(duration - EXPECTED) > 0.08:
    raise SystemExit(f"Duration mismatch: {duration:.3f} vs {EXPECTED:.3f}")

model = WhisperModel("medium", device="cpu", compute_type="int8")
segments, info = model.transcribe(
    str(AUDIO), language="tr", beam_size=8, vad_filter=False,
    word_timestamps=True, condition_on_previous_text=True,
    initial_prompt="Türkçe çocuk şarkısı. A harfi, arı, araba, aslan, ayı Melipo, ağaç ve ay."
)

words = []
texts = []
for seg in segments:
    texts.append(seg.text.strip())
    for w in (seg.words or []):
        token = w.word.strip()
        if token:
            words.append({"word": token, "start": round(float(w.start),3), "end": round(float(w.end),3)})

# The canonical song ends with "Görüşürüz çocuklar". Discard any decoder
# hallucination after that verified closing phrase (for example subtitle credits).
closing = None
for i, item in enumerate(words):
    clean = re.sub(r"[^a-zçğıöşü]", "", item["word"].casefold())
    if clean == "görüşürüz":
        for j in range(i + 1, min(i + 4, len(words))):
            nxt = re.sub(r"[^a-zçğıöşü]", "", words[j]["word"].casefold())
            if nxt == "çocuklar":
                closing = j
if closing is not None:
    words = words[:closing + 1]
texts = [" ".join(w["word"] for w in words)]


def norm(s):
    s = s.casefold().replace("â","a")
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

objects = {
    "arı": "arı",
    "araba": "araba",
    "aslan": "aslan",
    "ayı": "Melipo (tek ayı)",
    "agac": "ağaç",
    "ağac": "ağaç",
    "ağaç": "ağaç",
    "ay": "ay",
}
cues = []
for w in words:
    clean = re.sub(r"[^a-zçğıöşüA-ZÇĞİÖŞÜ]", "", norm(w["word"]))
    if clean in objects:
        cues.append({
            "object": objects[clean],
            "word": w["word"],
            "word_start": w["start"],
            "word_end": w["end"],
            "visible_from": round(max(0.0, w["start"] - 0.45), 3),
            "visible_until": w["end"],
        })

# Build 30 unequal scenes by snapping each target boundary to a real gap
# between recognised words. This preserves the exact master duration while
# avoiding cuts in the middle of a sung word or phrase.
step = EXPECTED / SCENES
gaps = []
for left, right in zip(words, words[1:]):
    gap = max(0.0, right["start"] - left["end"])
    midpoint = (left["end"] + right["start"]) / 2.0
    gaps.append((midpoint, gap))

bounds = [0.0]
for i in range(1, SCENES):
    target = i * step
    remaining = SCENES - i
    lo = bounds[-1] + 3.0
    hi = EXPECTED - remaining * 3.0
    valid = [(mid, gap) for mid, gap in gaps if lo <= mid <= hi and abs(mid-target) <= 2.2]
    if valid:
        chosen = min(valid, key=lambda x: abs(x[0]-target) - min(x[1], 1.2)*0.30)[0]
    else:
        chosen = min(max(target, lo), hi)
    bounds.append(round(chosen, 3))
bounds.append(EXPECTED)

manifest = []
for i in range(SCENES):
    start, end = bounds[i], bounds[i+1]
    scene_words = [w for w in words if w["start"] < end and w["end"] > start]
    scene_cues = [c for c in cues if c["visible_from"] < end and c["visible_until"] >= start]
    duration_seconds = round(end - start, 3)
    manifest.append({
        "scene_id": i + 1,
        "start_seconds": start,
        "duration_seconds": duration_seconds,
        "end_seconds": round(end, 3),
        "lyrics": " ".join(w["word"] for w in scene_words),
        "song": {"url": MASTER_URL, "start_seconds": start, "duration_seconds": duration_seconds},
        "required_objects": sorted(set(c["object"] for c in scene_cues)),
        "timed_cues": scene_cues,
    })

total = round(sum(s["duration_seconds"] for s in manifest), 3)
if total != EXPECTED:
    raise SystemExit(f"Manifest total mismatch: {total}")
if len(manifest) != 30 or len({s["scene_id"] for s in manifest}) != 30:
    raise SystemExit("Scene uniqueness failure")

Path("preflight").mkdir(exist_ok=True)
Path("preflight/transcript.txt").write_text("\\n".join(texts), encoding="utf-8")
Path("preflight/word_timestamps.json").write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
Path("preflight/object_cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=2), encoding="utf-8")
Path("preflight/scene_manifest.json").write_text(json.dumps({
    "audio_duration": duration,
    "expected_duration": EXPECTED,
    "scene_count": 30,
    "scene_duration_sum": total,
    "language": info.language,
    "language_probability": info.language_probability,
    "scenes": manifest,
}, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"duration":duration,"words":len(words),"object_cues":len(cues),"scene_total":total}, ensure_ascii=False))
