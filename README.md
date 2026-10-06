# 11

## Sarvam dubbing

`dub.py` dubs a video into several Indian languages with [Sarvam's Dubbing API](https://docs.sarvam.ai/api-reference/creative-agents-dubbing/create-dub). It clones each speaker's voice and downloads the dubbed video, the audio and SRT subtitles for every language.

```bash
pip install -r requirements.txt
export SARVAM_API_KEY=your_key_here

# Defaults: Marathi, Tamil, Telugu, Kannada, Bengali, Odia; 3 speakers; voice cloning on; no watermark
python dub.py ~/Downloads/SHORTY03_30s.mp4 --source hi-IN
```

`--source` is the language spoken in the original video (`en-IN`, `hi-IN`, ...).

Output lands in `./dubs/` as `<name>_<lang>_<video|audio|srt>.<ext>`.

If the script is interrupted or an export fails, resume the same job without creating (and paying for) a new one:

```bash
python dub.py --job-id dub_xxxxxxxx
```

Other flags: `--targets`, `--speakers`, `--exports`, `--register`, `--watermark`, `--out`. See `python dub.py --help`.
