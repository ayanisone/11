#!/usr/bin/env python3
"""Generate the Canara HSBC Life "AI Roast Me" voice lines (A01-A22) with ElevenLabs.

Settings: voice PpXxSapWoo4j3JoF2LPQ, model eleven_v4, stability 0.50,
similarity 0.65, style 0, speaker boost off, language auto-detect,
WAV 48 kHz.

Each line must come in under its MAX length. A take that runs long is
regenerated (up to MAX_ATTEMPTS times); if no take fits, the shortest one is
time-stretched with Rubber Band (tempo only, pitch and formants untouched).

Usage: ELEVENLABS_API_KEY=... python3 generate_lines.py [OUT_DIR] [LINE_ID ...]
"""
import json
import os
import subprocess
import sys
import tempfile

import requests

VOICE_ID = "PpXxSapWoo4j3JoF2LPQ"
MODEL_ID = "eleven_v4"
VOICE_SETTINGS = {
    "stability": 0.50,
    "similarity_boost": 0.65,
    "style": 0.0,
    "use_speaker_boost": False,
}
OUTPUT_FORMAT = "wav_48000"
MAX_ATTEMPTS = 5
SAFETY_MARGIN = 0.05  # seconds kept clear below each max length
EDGE_SILENCE = 0.04  # seconds of room tone kept at head and tail after trimming

# (id, max seconds, script text, text sent to TTS)
# "Canara" is respelled "Kenara" so it is spoken Ke-na-ra (केनरा) per the brief.
# A22 is sent in Devanagari so it is read with Hindi pronunciation.
LINES = [
    ("A01", 1.5, "Are you sure?", None),
    ("A02", 1.5, "Okay.", None),
    ("A03", 4.3, "Responsible. Practical. Thinks before making decisions.", None),
    ("A04", 2.2, "One more thing.", None),
    ("A05", 4.3, "Compares options. Looks for the best deal. Plans ahead.", None),
    ("A06", 2.1, "I'm building your profile.", None),
    ("A07", 6.3, "Knows where to order food from. Knows where to travel next. Knows which phone to buy next.", None),
    ("A08", 3.7, "Life after sixty... Status: unknown.", None),
    ("A09", 4.5, "Financial future... Status: unclear.", None),
    ("A10", 4.5, "Family's financial security... Status: loading.", None),
    ("A11", 4.5, "Not really. Do you know your plan for the next thirty years?", None),
    ("A12", 7.6, "That's the roast. For someone who plans everything... you're surprisingly comfortable winging the future.", None),
    ("A13", 3.8, "Do you want me to suggest ways to correct it?", None),
    ("A14", 7.0, "Based on your symptoms, I prescribe three options from Canara HSBC Life Insurance.",
     "Based on your symptoms, I prescribe three options from Kenara HSBC Life Insurance."),
    ("A15", 7.6, "Smart Guaranteed Pension. For the version of you that wants salary credits even after retirement.", None),
    ("A16", 10.3, "Promise for Life, Forever Income Option. Because \"one day everything will sort itself out\"... isn't actually a financial strategy.", None),
    ("A17", 8.6, "Pension for Life. For future you, who would prefer financial freedom over depending on the family WhatsApp group.", None),
    ("A18", 4.3, "And a bonus. All backed by a life cover plan.", None),
    ("A19", 10.5, "Because when it comes to claims, reliability matters. Canara HSBC Life Insurance has a ninety-nine point five two percent claim settlement ratio.",
     "Because when it comes to claims, reliability matters. Kenara HSBC Life Insurance has a ninety-nine point five two percent claim settlement ratio."),
    ("A20", 8.7, "Want the complete details, benefits, and fine print? Visit the Canara HSBC Life Insurance website.",
     "Want the complete details, benefits, and fine print? Visit the Kenara HSBC Life Insurance website."),
    ("A21", 8.4, "Financial planning isn't about knowing what's going to happen. It's about not being caught off guard when it does.", None),
    ("A22", 4.0, "Roast complimentary tha. Lesson important tha.", "रोस्ट कॉम्प्लिमेंट्री था। लेसन इम्पॉर्टेन्ट था।"),
]


def tts(text, path):
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        params={"output_format": OUTPUT_FORMAT},
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        json={"text": text, "model_id": MODEL_ID, "voice_settings": VOICE_SETTINGS},
        timeout=120,
    )
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)


def duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]
    )
    return float(out)


def ffmpeg(src, dst, af):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af,
         "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", dst],
        check=True,
    )


def trim_edges(src, dst):
    # Cut dead air before the first word and after the last one, leaving a short pad.
    sr = (f"silenceremove=start_periods=1:start_threshold=-50dB:"
          f"start_silence={EDGE_SILENCE}:detection=peak")
    ffmpeg(src, dst, f"{sr},areverse,{sr},areverse")


def stretch(src, dst, target):
    tempo = duration(src) / target
    ffmpeg(src, dst, f"rubberband=tempo={tempo:.5f}:pitch=1:formant=preserved:transients=smooth")


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "voice_lines"
    only = set(sys.argv[2:])
    os.makedirs(out_dir, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory() as tmp:
        for line_id, max_len, script, tts_text in LINES:
            if only and line_id not in only:
                continue
            limit = max_len - SAFETY_MARGIN
            takes = []
            for attempt in range(1, MAX_ATTEMPTS + 1):
                raw = os.path.join(tmp, f"{line_id}_{attempt}_raw.wav")
                trimmed = os.path.join(tmp, f"{line_id}_{attempt}.wav")
                tts(tts_text or script, raw)
                trim_edges(raw, trimmed)
                d = duration(trimmed)
                takes.append((d, trimmed, attempt))
                print(f"{line_id} take {attempt}: {d:.2f}s (max {max_len}s)", flush=True)
                if d <= limit:
                    break
            d, best, attempt = min(takes)
            final = os.path.join(out_dir, f"{line_id}.wav")
            method = "as generated"
            if d > limit:
                stretch(best, final, limit)
                method = f"time-stretched {d:.2f}s -> {limit:.2f}s (tempo x{d / limit:.3f}, pitch unchanged)"
            else:
                subprocess.run(["cp", best, final], check=True)
            final_d = duration(final)
            assert final_d < max_len, (line_id, final_d)
            report.append({
                "line": line_id, "max_s": max_len, "final_s": round(final_d, 3),
                "takes": len(takes), "used_take": attempt, "method": method, "text": script,
            })
            print(f"  -> {final}: {final_d:.2f}s, {method}", flush=True)
    with open(os.path.join(out_dir, "report.json"), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
