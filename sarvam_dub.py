"""Shared helpers for running Sarvam dubbing jobs."""
import mimetypes
import os
import time
from pathlib import Path

import httpx
from sarvamai import SarvamAI

# Marathi, Tamil, Gujarati, Telugu, Bengali, Kannada
TARGET_LANGUAGES = ["mr-IN", "ta-IN", "gu-IN", "te-IN", "bn-IN", "kn-IN"]

# Translation settings from Creator Studio: model "Sarvam Plus", style "Urban colloquial".
MODEL_TIER = "plus"
REGISTER = "modern-colloquial"

POLL_SECONDS = 20


def make_client():
    # Load .env into the environment (stdlib only, no python-dotenv).
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                key, sep, value = line.strip().partition("=")
                if sep and not key.startswith("#"):
                    os.environ.setdefault(key.strip(), value.strip())

    api_key = os.environ.get("SARVAM_API_KEY")
    if not api_key:
        raise SystemExit("SARVAM_API_KEY is not set. Add it to .env.")
    return SarvamAI(api_subscription_key=api_key)


def submit_job(client, media, source, export_options, num_speakers=None, job_name=None):
    """Create a job, upload the media and start it. Returns the job id."""
    create_args = dict(
        source_language_code=source,
        target_language_codes=TARGET_LANGUAGES,
        export_options=export_options,
        voice_cloning=True,  # clone every speaker's own voice
        register=REGISTER,
        disable_watermark=True,
        editor_flow=False,  # auto-export when done; True bills at the editor rate
        job_name=job_name or media.name,
        request_options={"additional_body_parameters": {"model_tier": MODEL_TIER}},
    )
    if num_speakers:
        create_args["num_speakers"] = num_speakers

    job = client.dubbing.create(**create_args).data
    print(f"Created job {job.job_id} for {media.name} (model_tier={job.model_tier}, voice_cloning={job.voice_cloning})")

    content_type = {".wav": "audio/wav"}.get(media.suffix.lower()) or mimetypes.guess_type(media.name)[0] or "video/mp4"
    client.dubbing.upload(job.upload_url, media, content_type=content_type).raise_for_status()
    client.dubbing.start(job.job_id)
    print(f"  uploaded and started {media.name}")
    return job.job_id


def wait_for_exports(client, job_id, label=""):
    """Poll until the job and its exports finish. Returns the export items."""
    while True:
        status = client.dubbing.get_live_status(job_id).data
        print(f"  {label:<12} {status.status:<16} {status.progress:>3}%  {status.current_step_label or ''}")
        if status.status in ("completed", "failed", "partial_failure"):
            break
        time.sleep(POLL_SECONDS)

    if status.status == "failed":
        raise SystemExit(f"Dubbing failed for {label or job_id}: {status.error_message}")

    while True:
        exports = client.dubbing.get_export_status(job_id).data.exports
        if exports and all(e.status != "in_progress" for e in exports):
            return exports
        time.sleep(POLL_SECONDS)


def download(url, dest_without_ext):
    """Download a signed URL, keeping the file extension from the URL."""
    ext = Path(httpx.URL(url).path).suffix or ".bin"
    dest = dest_without_ext.with_name(dest_without_ext.name + ext)
    with httpx.stream("GET", url, follow_redirects=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in r.iter_bytes():
                fh.write(chunk)
    return dest
