"""Render a grid of DhVaani test lines (reference voice x language) and time each one.

Run from a checkout of ARTPARK-IISc/DhVaani-0.5:  python test_dhvaani.py <dhvaani_dir> <out_dir>
"""
import sys
import time

import soundfile as sf

sys.path.insert(0, sys.argv[1])
from dhvaani import DhVaani  # noqa: E402

DHV, OUT = sys.argv[1], sys.argv[2]
REFS = {
    "hindi_ref": (f"{DHV}/samples/hindi.wav", "इसे कई बार मंचित भी किया गया है।"),
    "english_ref": ("/home/user/work/index-tts/examples/voice_07.wav", "Of course, I'm your ex-boyfriend."),
}
LINES = {
    "hi": "मित्र दा ढाबा में आपका स्वागत है। तंदूर गरम है और चाय हमारी तरफ़ से।",
    "pa": "ਮਿੱਤਰ ਦਾ ਢਾਬਾ ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ। ਤੰਦੂਰ ਗਰਮ ਹੈ ਤੇ ਚਾਹ ਸਾਡੇ ਵੱਲੋਂ।",
    "hinglish": "मित्र दा ढाबा में welcome है! आज का special है butter chicken और garlic naan.",
}

t = time.time()
tts = DhVaani(model_dir=DHV)
print(f"load {time.time() - t:.1f}s on {tts.device}", flush=True)
for ref_name, (wav, transcript) in REFS.items():
    for lang, text in LINES.items():
        out = f"{OUT}/{lang}__{ref_name}.wav"
        t = time.time()
        tts.synthesize(text=text, prompt_wav=wav, prompt_text=transcript, out_path=out)
        dur = sf.info(out).duration
        print(f"{out.split('/')[-1]}: {dur:.2f}s audio in {time.time() - t:.1f}s", flush=True)
