import sys, time, os
os.chdir("/home/user/work/index-tts")
sys.path.insert(0, "/home/user/work/index-tts")
from indextts.infer_v2 import IndexTTS2
t=time.time()
tts = IndexTTS2(cfg_path="checkpoints/config.yaml", model_dir="checkpoints", device="cpu", use_fp16=False)
print(f"load {time.time()-t:.1f}s", flush=True)
jobs = [
  ("examples/voice_01.wav", "Welcome to Mitra da Dhaba. The tandoor is hot and the chai is on the house.", "/home/user/11/outputs/01_neutral.wav", {}),
  ("examples/voice_07.wav", "Welcome to Mitra da Dhaba. The tandoor is hot and the chai is on the house.", "/home/user/11/outputs/02_happy_vector.wav",
     {"emo_vector":[0.6,0,0,0,0,0,0,0.2]}),
]
for spk, text, out, kw in jobs:
    t=time.time()
    tts.infer(spk_audio_prompt=spk, text=text, output_path=out, verbose=False, **kw)
    print(f"{out} {time.time()-t:.1f}s", flush=True)
