"""Minimal Gradio UI for testing suno/bark (Hugging Face transformers port)."""
import os, time, threading
import numpy as np
import torch
import gradio as gr
from transformers import AutoProcessor, BarkModel

torch.set_num_threads(os.cpu_count() or 4)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

MODELS = {"bark-small (faster)": "suno/bark-small", "bark (full quality)": "suno/bark"}
LANGS = {"en": "English", "de": "German", "es": "Spanish", "fr": "French", "hi": "Hindi",
         "it": "Italian", "ja": "Japanese", "ko": "Korean", "pl": "Polish", "pt": "Portuguese",
         "ru": "Russian", "tr": "Turkish", "zh": "Chinese"}
VOICES = ["(none - random voice)"] + [f"v2/{l}_speaker_{i}" for l in LANGS for i in range(10)]

_cache, _lock = {}, threading.Lock()

def load(model_id):
    with _lock:
        if model_id not in _cache:
            proc = AutoProcessor.from_pretrained(model_id)
            model = BarkModel.from_pretrained(model_id).to(DEVICE).eval()
            _cache[model_id] = (proc, model)
        return _cache[model_id]

def generate(text, model_label, voice, text_temp, wave_temp, seed):
    if not text.strip():
        raise gr.Error("Enter some text first.")
    proc, model = load(MODELS[model_label])
    if seed >= 0:
        torch.manual_seed(int(seed))
    preset = None if voice.startswith("(none") else voice
    inputs = proc(text, voice_preset=preset).to(DEVICE)
    t = time.time()
    with torch.inference_mode():
        audio = model.generate(**inputs, do_sample=True,
                               semantic_temperature=text_temp,
                               coarse_temperature=wave_temp,
                               fine_temperature=0.5).cpu().numpy().squeeze()
    sr = model.generation_config.sample_rate
    peak = 20 * np.log10(np.abs(audio).max() + 1e-9)
    info = (f"{len(audio)/sr:.1f}s of audio rendered in {time.time()-t:.0f}s on {DEVICE} · "
            f"{sr} Hz mono · peak {peak:.1f} dBFS")
    return (sr, audio.astype(np.float32)), info

with gr.Blocks(title="Bark TTS test bench") as demo:
    gr.Markdown(
        "# Bark text-to-audio test bench\n"
        "Running on **CPU** — expect roughly 8x (small) to 20x+ (full) slower than real time. "
        "Bark works best on ~13 s chunks of text.\n\n"
        "**Non-speech cues:** `[laughter]` `[laughs]` `[sighs]` `[music]` `[gasps]` `[clears throat]` · "
        "`—` or `...` for hesitation · `♪` around lyrics to sing · CAPITALS for emphasis.")
    with gr.Row():
        with gr.Column():
            text = gr.Textbox(label="Text", lines=4,
                              value="Hello, my name is Suno. And, uh — and I like pizza. [laughs] "
                                    "But I also have other interests such as playing tic tac toe.")
            model = gr.Radio(list(MODELS), value="bark-small (faster)", label="Model")
            voice = gr.Dropdown(VOICES, value="v2/en_speaker_6", label="Voice preset (speaker prompt)")
            with gr.Accordion("Advanced", open=False):
                text_temp = gr.Slider(0.1, 1.2, 0.7, step=0.05, label="Text temperature (semantic stage)")
                wave_temp = gr.Slider(0.1, 1.2, 0.7, step=0.05, label="Waveform temperature (coarse stage)")
                seed = gr.Number(-1, precision=0, label="Seed (-1 = random)")
            btn = gr.Button("Generate", variant="primary")
        with gr.Column():
            out_audio = gr.Audio(label="Output", type="numpy")
            out_info = gr.Markdown()
    btn.click(generate, [text, model, voice, text_temp, wave_temp, seed], [out_audio, out_info])

if __name__ == "__main__":
    demo.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=7860)
