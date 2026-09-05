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
    str(AUDIO), language="tr", beam_size=5, vad_filter=True,
    word_timestamps=True, condition_on_previous_text=False
)

words = []
texts = []
for seg in segments:
    texts.append(seg.text.strip())
    for w in (seg.words or []):
        token = w.word.strip()
        if token:
            words.append({"word": token, "start": round(float(w.start),3), "end": round(float(w.end),3)})

def norm(s):
    s = s.casefold().replace("â","a")
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

objects = {
    "arı": "arı",
    "araba": "araba",
    "aslan": "aslan",
    "ayı": "Melipo (tek ayı)",
    "agac": "ağaç",\n    "ağac": "ağaç",\n    "ağaç": "ağaç",
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

step = EXPECTED / SCENES
manifest = []
for i in range(SCENES):
    start = round(i * step, 3)
    end = EXPECTED if i == SCENES - 1 else round((i + 1) * step, 3)
    scene_cues = [c for c in cues if c["word_start"] < end and c["word_end"] >= start]
    manifest.append({
        "scene_id": i + 1,
        "start_seconds": start,
        "duration_seconds": round(end - start, 3),
        "end_seconds": round(end, 3),
        "song": {"url": MASTER_URL, "start_seconds": start, "duration_seconds": round(end-start,3)},
        "required_objects": sorted(set(c["object"] for c in scene_cues)),
        "timed_cues": scene_cues,
    })

total = round(sum(s["duration_seconds"] for s in manifest), 3)
if total != EXPECTED:
    raise SystemExit(f"Manifest total mismatch: {total}")
if len(manifest) != 30 or len({s["scene_id"] for s in manifest}) != 30:
    raise SystemExit("Scene uniqueness failure")

Path("preflight").mkdir(exist_ok=True)
Path("preflight/transcript.txt").write_text("\n".join(texts), encoding="utf-8")
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
