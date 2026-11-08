import sys, time, torch, scipy.io.wavfile
from transformers import AutoProcessor, BarkModel

model_id = sys.argv[1] if len(sys.argv) > 1 else "suno/bark-small"
text = sys.argv[2] if len(sys.argv) > 2 else "Hello! [laughs] This is Bark, running on a CPU in the cloud."
voice = sys.argv[3] if len(sys.argv) > 3 else "v2/en_speaker_6"
out = sys.argv[4] if len(sys.argv) > 4 else "out.wav"

torch.set_num_threads(4)
t = time.time()
processor = AutoProcessor.from_pretrained(model_id)
model = BarkModel.from_pretrained(model_id)
print(f"loaded {model_id} in {time.time()-t:.1f}s", flush=True)

t = time.time()
inputs = processor(text, voice_preset=voice)
with torch.inference_mode():
    audio = model.generate(**inputs, do_sample=True).cpu().numpy().squeeze()
sr = model.generation_config.sample_rate
scipy.io.wavfile.write(out, rate=sr, data=audio)
print(f"generated {len(audio)/sr:.1f}s of audio in {time.time()-t:.1f}s -> {out} @ {sr} Hz", flush=True)
