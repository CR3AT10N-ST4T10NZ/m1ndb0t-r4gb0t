import sys
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.pipeline.parallel_pipeline import ParallelPipeline

from pipecat.processors.frameworks.rtvi import RTVIObserver, RTVIProcessor

from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport
from pipecat.transports.base_transport import TransportParams

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.processors.aggregators.llm_response import LLMUserAggregatorParams
from pipecat.frames.frames import LLMRunFrame

from server.bot.services.modal_parakeet_service import ModalParakeetSegmentedSTTService
from server.bot.services.modal_kokoro_service import ModalKokoroTTSService
from server.bot.processors.unison_speaker_mixer import UnisonSpeakerMixer
from server.bot.services.modal_vllm_service import ModalVLLMService
from .processors.festival_rag import FestivalRag, get_system_prompt, ChromaVectorDB

from .avatar.mindbot_animation import MindBotAnimation, get_frames

import modal

try:
    logger.remove(0)
    logger.add(sys.stderr, level="DEBUG")
except ValueError:
    # Handle the case where logger is already initialized
    pass

_AUDIO_INPUT_SAMPLE_RATE = 16000
_AUDIO_OUTPUT_SAMPLE_RATE = 24000
_MINDBOT_FRAME_RATE = 12
_MINDBOT_FRAME_WIDTH = 1024
_MINDBOT_FRAME_HEIGHT = 576

_DEFAULT_ENABLE_VIDEO = False

async def run_bot(
    webrtc_connection: SmallWebRTCConnection,
    chroma_db: ChromaVectorDB,
    enable_mindbot_animation: bool = _DEFAULT_ENABLE_VIDEO,
):
    """Main MindBot execution function.

    Sets up and runs the bot pipeline including:
    - WebRTC transport with audio/video parameters
    - Festival RAG system with vLLM backend
    - Parakeet STT and Kokoro TTS services
    - Voice activity detection and smart turn management
    - Animation processing with talking animations
    - RTVI event handling
    """

    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_in_sample_rate=_AUDIO_INPUT_SAMPLE_RATE,
        audio_out_enabled=True,
        audio_out_sample_rate=_AUDIO_OUTPUT_SAMPLE_RATE,
        video_out_enabled=enable_mindbot_animation,
        video_out_width=_MINDBOT_FRAME_WIDTH,
        video_out_height=_MINDBOT_FRAME_HEIGHT,
        video_out_framerate=_MINDBOT_FRAME_RATE,
        vad_analyzer=SileroVADAnalyzer(
            params=VADParams(
                stop_secs=0.2)
        ),
        turn_analyzer=LocalSmartTurnAnalyzerV3(
            params=SmartTurnParams()
        ),
    )

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=transport_params,
    )

    stt = ModalParakeetSegmentedSTTService(
        app_name="parakeet-transcription",
        cls_name="Transcriber",
        audio_passthrough=True,
    )

    festival_rag = FestivalRag(chroma_db=chroma_db, similarity_top_k=3, num_adjacent_nodes=2)

    vllm_dict = modal.Dict.from_name("vllm-dict", create_if_missing=True)
    llm_url = vllm_dict.get("vllm_url")

    llm = ModalVLLMService(
        model="Qwen/Qwen3-4B-Instruct-2507",
        api_key = "super-secret-key",
        base_url = llm_url,
        params=OpenAILLMService.InputParams(
            extra={
                "stream": True,
            },
        ),
    )

    messages = [
        {
            "role": "system", 
            "content": get_system_prompt(),
        },
        {
            "role": "user",
            "content": "Yo, who are you and what's this festival about?",
        }
    ]

    # Set up conversation context and management
    # The context_aggregator will automatically collect conversation context
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(
        context,
        user_params=LLMUserAggregatorParams(aggregation_timeout=0.05),
    )

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor()

    processors = [
        transport.input(),
        rtvi,
        stt,
        festival_rag,
        context_aggregator.user(),
        llm,
        
    ]
    
    # only add animation processor if video is enabled
    if enable_mindbot_animation:
        ta = MindBotAnimation()
        # Using single voice for MindBot (not dual speakers)
        tts = ModalKokoroTTSService(
            app_name="kokoro-tts",
            cls_name="KokoroTTS",
            voice="am_fenrir",  # Deep voice for that Rick/Bender vibe
            speed=1.4,  # Slightly faster, more energetic
        )
        processors += [
            tts,
            ta,
        ]
    else:
        processors.append(ModalKokoroTTSService(
            app_name="kokoro-tts",
            cls_name="KokoroTTS",
            voice="am_fenrir",  # Deep voice for that Rick/Bender vibe
            speed=1.4,  # Slightly faster, more energetic
        ))

    processors += [
        transport.output(),
        context_aggregator.assistant(),
    ]

    pipeline = Pipeline(
        processors=processors,
    )
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        logger.info("Pipecat client ready.")
        await rtvi.set_bot_ready()
        await task.queue_frame(LLMRunFrame())
        
    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Pipecat Client disconnected")
        await task.cancel()
        logger.info("Pipeline task cancelled.")

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Pipecat Client connected")
        await task.queue_frame(get_frames("listening"))
        
    runner = PipelineRunner()
    await runner.run(task)

    logger.info("Pipeline task Finished.")
