# AGENTS - Multi-Personality AI Voice Bot Framework

This directory contains different AI agent personalities and configurations built on the same underlying framework. Each agent has its own personality, knowledge base, and use case.

## 🤖 Available Agents

### MindBot - Festival Guide (Intergalactic Music Festival 2045)

**Location**: `AGENTS/nodes/mindbot/`

**Personality**: A self-aware AI mixing Bender (Futurama) and Rick Sanchez (Rick and Morty)
- Sarcastic but genuinely helpful
- Mission-driven (saving humanity through music)
- Entertaining and engaging for voice kiosk interactions

**Use Case**: Voice-activated kiosk agent for The Intergalactic Music Festival 2045
- Festival information and schedules
- Artist recommendations
- Navigation assistance
- Entertainment and engagement

**Knowledge Base**: `AGENTS/nodes/mindbot/assets/festival_knowledge.md`
- Festival schedule and lineup
- Venue information
- Artist details
- Practical information (food, transportation, rules)
- Festival lore and mission

## 📁 Directory Structure

```
AGENTS/
├── README.md (this file)
├── __init__.py
└── nodes/
    └── mindbot/
        ├── __init__.py
        ├── mindbot_app.py          # Modal deployment configuration
        ├── mindbot_bot.py           # Main bot pipeline logic
        ├── assets/
        │   ├── festival_knowledge.md    # Knowledge base
        │   └── animation_frames/        # Visual assets (if enabled)
        ├── avatar/
        │   ├── __init__.py
        │   └── mindbot_animation.py     # Visual state management
        └── processors/
            ├── __init__.py
            └── festival_rag.py          # RAG system & prompts
```

## 🚀 Deployment

### Prerequisites

1. **Modal Account**: Set up at [modal.com](https://modal.com)
2. **Modal CLI**: Install and authenticate
   ```bash
   pip install modal
   modal setup
   ```

3. **Deploy Supporting Services** (if not already deployed):
   ```bash
   # Deploy VLLM inference server
   modal deploy -m server.llm.vllm_server

   # Deploy Parakeet STT service
   modal deploy -m server.stt.parakeet_stt

   # Deploy Kokoro TTS service
   modal deploy -m server.tts.kokoro_tts
   ```

### Deploy MindBot

```bash
# From the project root directory
modal deploy -m AGENTS.nodes.mindbot.mindbot_app
```

Or if you want to test it first:

```bash
modal serve -m AGENTS.nodes.mindbot.mindbot_app
```

### Frontend Setup

1. Build the client:
   ```bash
   cd client
   npm install
   npm run build
   ```

2. Update `client/.env` with your Modal deployment URL:
   ```
   VITE_API_URL=https://{YOUR_MODAL_ORG}--mindbot-festival-2045-serve-frontend.modal.run
   ```

## 🎭 Creating Your Own Agent

Want to create a different personality? Follow this structure:

### 1. Create Agent Directory

```bash
mkdir -p AGENTS/nodes/your_agent_name/{assets,avatar,processors}
```

### 2. Required Files

- `your_agent_bot.py` - Main pipeline logic (copy from mindbot_bot.py)
- `your_agent_app.py` - Modal deployment config (copy from mindbot_app.py)
- `assets/knowledge_base.md` - Your agent's knowledge
- `processors/rag_processor.py` - RAG system with custom prompts
- `avatar/animation.py` - Visual states (optional)

### 3. Customize Personality

Edit the `get_system_prompt()` function in your RAG processor to define:
- Personality traits
- Speaking style
- Mission/purpose
- Response format

### 4. Update Knowledge Base

Create your own markdown file with relevant information for your agent's domain.

### 5. Deploy

```bash
modal deploy -m AGENTS.nodes.your_agent_name.your_agent_app
```

## 🔧 Configuration Options

### Voice Settings

In your bot file (`mindbot_bot.py`), adjust TTS parameters:

```python
tts = ModalKokoroTTSService(
    app_name="kokoro-tts",
    cls_name="KokoroTTS",
    voice="am_fenrir",  # Voice type
    speed=1.4,          # Speaking speed
)
```

Available voices:
- `am_puck` - Lighter voice
- `am_fenrir` - Deeper voice (used for MindBot)

### RAG Settings

In your RAG processor, adjust retrieval:

```python
festival_rag = FestivalRag(
    chroma_db=chroma_db,
    similarity_top_k=3,      # Number of chunks to retrieve
    num_adjacent_nodes=2     # Context around each chunk
)
```

### Animation (Optional)

Enable visual animations by setting `enable_mindbot_animation=True` in the bot task call.

Place animation frames in `assets/animation_frames/`:
- `mindbot-listening-XX.png` - Idle state
- `mindbot-talking-XX.png` - Speaking state  
- `mindbot-thinking-XX.png` - Processing state

## 🎯 Framework Features

All agents inherit these capabilities:

- **Real-time Voice**: Low-latency speech-to-speech interaction
- **RAG System**: ChromaDB vector search for knowledge retrieval
- **LLM Integration**: vLLM backend for fast inference
- **Structured Output**: JSON responses with spoken + visual content
- **WebRTC Transport**: Browser-based audio/video streaming
- **Smart Turn Detection**: Natural conversation flow
- **Interruption Handling**: Can be interrupted mid-response

## 📊 Response Format

All agents use structured JSON responses:

```json
{
    "spoke_response": "Short, punchy spoken answer",
    "festival_info": ["Detail 1", "Detail 2"],
    "portal_links": ["Link 1", "Stage Name"]
}
```

Customize the field names in your RAG processor's system prompt.

## 🐛 Troubleshooting

### Import Errors

Make sure you're running commands from the project root and that all `__init__.py` files are present.

### Modal Connection Issues

```bash
modal token set
modal run -m AGENTS.nodes.mindbot.mindbot_app::app.ping
```

### RAG Not Finding Content

Check that your knowledge base markdown file exists and is properly loaded in the ChromaVectorDB setup.

### Voice/TTS Issues

Ensure the Kokoro TTS service is deployed:
```bash
modal deploy -m server.tts.kokoro_tts
```

## 📝 Notes

- The original `server/bot/moe_and_dal_bot.py` remains intact as a template
- MindBot is a standalone agent in the AGENTS directory
- Framework is designed for easy personality swapping
- Each agent can have completely different knowledge bases
- Same infrastructure (Modal, Pipecat, vLLM) powers all agents

## 🎉 Example Use Cases

- **Festival Guide** (MindBot) - Current implementation
- **Tech Support Bot** - Help desk with documentation
- **Museum Guide** - Art and history information
- **Product Demo Agent** - Sales and product information
- **Educational Tutor** - Subject-specific teaching
- **Game NPC** - Interactive character with lore

## 🔗 Related Documentation

- [Main Project README](../README.md)
- [Modal Documentation](https://modal.com/docs)
- [Pipecat Framework](https://github.com/pipecat-ai/pipecat)
- [Festival Knowledge Base](nodes/mindbot/assets/festival_knowledge.md)

## 💡 Tips

1. **Keep responses punchy** - Voice interactions work best with short sentences
2. **Test personality early** - The system prompt is crucial for engagement
3. **Iterate on knowledge base** - RAG quality depends on good documentation structure
4. **Monitor latency** - Use Modal's metrics to optimize cold starts
5. **Balance entertainment with utility** - Users want both personality AND useful info

---

**Have fun building agents! Remember: every personality is just a system prompt away.** 🤖✨
