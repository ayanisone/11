"""`duplex live`: a local web app. Open the page, put on headphones, talk."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import fields
from pathlib import Path
from typing import Callable

from aiohttp import WSMsgType, web

from .floor import Params
from .session import Session

STATIC = Path(__file__).parent / "static"


def make_app(*, bank_dir: Path, make_session_parts: Callable[[], dict], params: dict, log_dir: Path) -> web.Application:
    app = web.Application()
    manifest = json.loads((bank_dir / "manifest.json").read_text()) if (bank_dir / "manifest.json").exists() else {}
    bank_ms = {k: sum(f["ms"] for f in v) / len(v) for k, v in manifest.get("items", {}).items() if v}

    async def index(_):
        return web.FileResponse(STATIC / "index.html")

    async def bank(request):
        name = request.match_info["name"]
        path = (bank_dir / name).resolve()
        if path.parent != bank_dir.resolve() or not path.exists():
            raise web.HTTPNotFound()
        return web.FileResponse(path)

    async def ws_handler(request):
        ws = web.WebSocketResponse(heartbeat=20, max_msg_size=4 * 1024 * 1024)
        await ws.prepare(request)
        out: asyncio.Queue = asyncio.Queue()

        async def writer():  # one writer, so frames from concurrent tasks never interleave
            while True:
                item = await out.get()
                if isinstance(item, bytes):
                    await ws.send_bytes(item)
                else:
                    await ws.send_json(item)

        async def send_json(d):
            await out.put(d)

        async def send_bytes(b):
            await out.put(b)

        w = asyncio.create_task(writer())
        session = Session(send_json=send_json, send_bytes=send_bytes, params=Params(**params), bank_ms=bank_ms,
                          log_dir=log_dir, **make_session_parts())
        await send_json({"type": "hello", "params": {f.name: getattr(session.floor.p, f.name) for f in fields(Params)}})
        try:
            await session.start()
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    await session.mic(msg.data)
                elif msg.type == WSMsgType.TEXT:
                    await session.browser(json.loads(msg.data))
        except Exception as e:
            await send_json({"type": "log", "t": 0, "text": f"session error: {e}"})
            await asyncio.sleep(0.2)
        finally:
            stats = await session.close()
            print(f"session closed: {json.dumps(stats)}")
            w.cancel()
        return ws

    app.router.add_get("/", index)
    app.router.add_get("/bank/{name}", bank)
    app.router.add_get("/ws", ws_handler)
    return app


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="duplex-live", description="Pseudo-duplex voice agent: ElevenLabs + Claude.")
    ap.add_argument("--voice", default="gYf9sqh3BkV9QqFMN9Hs", help="ElevenLabs voice id (default: Anya, as Riff)")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--language", default=None, help="Scribe language code, e.g. en or hi (default: auto)")
    ap.add_argument("--model", default=None, help="Claude model for listener + brain (default claude-haiku-5-5)")
    ap.add_argument("--tts-model", default="eleven_v4_turbo")
    ap.add_argument("--bank-dir", default=None, help="where backchannel takes live (default ~/.duplex/bank/<voice>)")
    ap.add_argument("--log-dir", default="sessions")
    ap.add_argument("--set", action="append", default=[], metavar="KNOB=VALUE", help="override a floor knob")
    a = ap.parse_args(argv)

    from .claude import MODEL, Claude
    from .eleven_rt import Mouth, Scribe, build_bank

    bank_dir = Path(a.bank_dir or Path.home() / ".duplex" / "bank" / a.voice)
    print(f"backchannel bank: {bank_dir} (rendering any missing takes with eleven_v4)")
    build_bank(a.voice, bank_dir)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("note: ANTHROPIC_API_KEY is not set; the Anthropic client will look for other credentials")

    params = {}
    kinds = {f.name: type(getattr(Params(), f.name)) for f in fields(Params)}
    for kv in a.set:
        k, _, v = kv.partition("=")
        if k not in kinds:
            raise SystemExit(f"unknown knob {k}; knobs: {', '.join(kinds)}")
        params[k] = (v.lower() in ("1", "true", "yes")) if kinds[k] is bool else kinds[k](v)

    def parts():
        return {"stt": Scribe(language=a.language), "claude": Claude(a.model or MODEL),
                "mouth": Mouth(a.voice, model_id=a.tts_model)}

    app = make_app(bank_dir=bank_dir, make_session_parts=parts, params=params, log_dir=Path(a.log_dir))
    print(f"open http://{a.host}:{a.port}  (headphones on, then press Start)")
    web.run_app(app, host=a.host, port=a.port, print=None)


if __name__ == "__main__":
    main()
