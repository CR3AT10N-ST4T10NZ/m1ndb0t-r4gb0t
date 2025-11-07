import asyncio
from pathlib import Path
import time

import modal

from server import BOT_REGION

app = modal.App("mindbot-festival-2045")

# Container specifications for the MindBot Pipecat pipeline
bot_image = (
    modal.Image.debian_slim(python_version="3.12",)
    .apt_install(
        "git",
        "ffmpeg",
    )
    .uv_pip_install(
        "pipecat-ai[webrtc,openai,silero,local-smart-turn,noisereduce,soundfile]==0.0.92",
        "chromadb",
        "sentence-transformers[openvino]",
        "llama-index==0.14.7",
        "llama-index-embeddings-openvino",
        "llama-index-vector-stores-chroma",
        "websocket-client",
        "aiofiles",
        "fastapi[standard]",
        "huggingface_hub[hf_transfer]",
    )
    .env({
        "HF_HUB_ENABLE_HF_TRANSFER": "1",
    })
    .add_local_dir("server", remote_path="/root/server")
    .add_local_dir("AGENTS", remote_path="/root/AGENTS")
)

MINUTES = 60  # seconds in a minute

with bot_image.imports():
    from loguru import logger
    from pipecat.transports.smallwebrtc.connection import (
        IceServer,
        SmallWebRTCConnection,
    )

    from AGENTS.nodes.mindbot.mindbot_bot import run_bot

@app.cls(
    image=bot_image,
    timeout=30 * MINUTES,
    region=BOT_REGION,
    enable_memory_snapshot=True,
    max_inputs=1,
)
class MindBotServer:

    @modal.enter(snap=True)
    def load(self):
        from AGENTS.nodes.mindbot.processors.festival_rag import ChromaVectorDB
        self.chroma_db = ChromaVectorDB()

    @modal.method()
    async def serve_bot(self, d: modal.Dict):
        """Launch MindBot with WebRTC connection and run the bot pipeline.

        Args:
            d (modal.Dict): A dictionary containing the WebRTC offer and ICE servers configuration.

        Raises:
            RuntimeError: If the bot pipeline fails to start or encounters an error.
        """
        
        try:

            offer = await d.get.aio("offer")
            ice_servers = await d.get.aio("ice_servers")
            ice_servers = [
                IceServer(
                    **ice_server,
                )
                for ice_server in ice_servers
            ]

            webrtc_connection = SmallWebRTCConnection(ice_servers)
            await webrtc_connection.initialize(sdp=offer["sdp"], type=offer["type"])

            @webrtc_connection.event_handler("closed")
            async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
                logger.info("WebRTC connection to MindBot closed.")

            print("Starting MindBot process.")
            bot_task = asyncio.create_task(run_bot(webrtc_connection, self.chroma_db, enable_mindbot_animation=False))

            answer = webrtc_connection.get_answer()
            await d.put.aio("answer", answer)

            await bot_task

        except Exception as e:
            raise RuntimeError(f"Failed to start MindBot pipeline: {e}")

    @modal.method()
    def ping(self):
        return "pong"


frontend_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("fastapi==0.115.12")
    .add_local_dir("server", remote_path="/root/server")
    .add_local_dir(
        Path(__file__).parent.parent.parent.parent / "client/dist",
        remote_path="/frontend",
    )
)

with frontend_image.imports():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles

@app.function(image=frontend_image)
@modal.asgi_app()
@modal.concurrent(max_inputs=100)
def serve_frontend():
    """Create and configure the FastAPI application for MindBot.

    This function initializes the FastAPI app with middleware, routes, and lifespan management.
    It is decorated to be used as a Modal ASGI app.
    """

    web_app = FastAPI()

    static_files = StaticFiles(directory="/frontend")
    web_app.mount("/frontend", static_files)

    @web_app.get("/")
    async def root():
        return HTMLResponse(content=open("/frontend/index.html").read())
    
    @web_app.post("/offer")
    async def offer(offer: dict):

        _ICE_SERVERS = [
            {
                "urls": "stun:stun.l.google.com:19302",
            }
        ]

        with modal.Dict.ephemeral() as d:

            await d.put.aio("ice_servers", _ICE_SERVERS)
            await d.put.aio("offer", offer)

            MindBotServer().serve_bot.spawn(d)

            while True:
                answer = await d.get.aio("answer")
                if answer:
                    return answer
                await asyncio.sleep(0.1)

    return web_app

# Warmup snapshots if needed
if __name__ == "__main__":
    mindbot_server = modal.Cls.from_name("mindbot-festival-2045", "MindBotServer").with_options(scaledown_window=2)
    num_cold_starts = 20
    for _ in range(num_cold_starts):
        start_time = time.time()
        mindbot_server().ping.remote()
        end_time = time.time()
        print(f"Time taken to ping: {end_time - start_time:.3f} seconds")
        time.sleep(10.0) # allow container to drain
    print(f"MindBotServer cold starts: {num_cold_starts}")
