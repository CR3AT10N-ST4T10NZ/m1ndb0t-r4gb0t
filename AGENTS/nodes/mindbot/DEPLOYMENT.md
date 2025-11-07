# MindBot Deployment Guide 🤖🚀

Quick guide to get MindBot up and running for The Intergalactic Music Festival 2045!

## Prerequisites ✅

- Python 3.12+
- Modal account (sign up at [modal.com](https://modal.com))
- Node.js and npm (for frontend)

## Step 1: Install Modal CLI

```bash
pip install modal
modal setup
```

Follow the prompts to authenticate with your Modal account.

## Step 2: Deploy Backend Services

These services need to be deployed once and are shared across all agents:

```bash
# From project root directory

# 1. Deploy VLLM inference server (LLM backend)
modal deploy -m server.llm.vllm_server

# 2. Deploy Speech-to-Text service
modal deploy -m server.stt.parakeet_stt

# 3. Deploy Text-to-Speech service
modal deploy -m server.tts.kokoro_tts
```

Each deployment will give you a URL. These services run independently and MindBot will connect to them automatically.

## Step 3: Deploy MindBot

```bash
# From project root directory
modal deploy -m AGENTS.nodes.mindbot.mindbot_app
```

This will:
- Build the container with all dependencies
- Load the festival knowledge base
- Create the RAG vector index
- Deploy the WebRTC server
- Deploy the frontend interface

You'll get a URL like: `https://YOUR_ORG--mindbot-festival-2045-serve-frontend.modal.run`

## Step 4: Build Frontend (First Time Only)

```bash
cd client
npm install
npm run build
cd ..
```

## Step 5: Configure Frontend (Optional)

If you want to run the frontend locally for development:

```bash
cd client
cp env.example .env
```

Edit `.env` and set:
```
VITE_API_URL=https://YOUR_ORG--mindbot-festival-2045-serve-frontend.modal.run
```

Then run:
```bash
npm run dev
```

## Testing Your Deployment 🧪

### Quick Health Check

```bash
# Test if MindBot server responds
modal run -m AGENTS.nodes.mindbot.mindbot_app::app
```

### Test in Browser

1. Open your deployment URL in a browser
2. Click "Connect" or "Start"
3. Allow microphone permissions
4. Say something like: "Hey, who are you?"
5. MindBot should respond with his sarcastic introduction!

## Common Issues & Solutions 🔧

### Issue: "Module not found" errors

**Solution**: Make sure you're running commands from the project root directory (where `AGENTS/` folder is located)

### Issue: Services not connecting

**Solution**: Verify all backend services are deployed:
```bash
modal app list
```

You should see:
- `vllm-server`
- `parakeet-transcription`
- `kokoro-tts`
- `mindbot-festival-2045`

### Issue: No audio output

**Solution**: 
1. Check browser console for errors
2. Ensure TTS service is running: `modal app logs kokoro-tts`
3. Check microphone permissions

### Issue: Slow responses

**Solution**: 
- First connection might be slow (cold start)
- Subsequent requests should be faster
- Consider enabling `min_containers=1` in mindbot_app.py for production

## Development Mode 🛠️

For faster iteration during development:

```bash
# Use 'serve' instead of 'deploy' - auto-reloads on code changes
modal serve -m AGENTS.nodes.mindbot.mindbot_app
```

Changes to personality/prompts:
- Edit `AGENTS/nodes/mindbot/processors/festival_rag.py`
- Modify the `get_system_prompt()` function
- Save and the service will reload

Changes to knowledge base:
- Edit `AGENTS/nodes/mindbot/assets/festival_knowledge.md`
- Save and redeploy (knowledge is embedded at container build time)

## Production Optimizations ⚡

### Enable Snapshots for Faster Cold Starts

Uncomment in `mindbot_app.py`:
```python
@app.cls(
    ...
    # min_containers=1,  # Keep at least 1 container warm
)
```

### Warm Up Snapshots

```bash
python -m AGENTS.nodes.mindbot.mindbot_app
```

This will ping the service 20 times to create optimized snapshots.

## Monitoring 📊

### View Logs

```bash
# MindBot logs
modal app logs mindbot-festival-2045

# TTS logs
modal app logs kokoro-tts

# STT logs  
modal app logs parakeet-transcription

# LLM logs
modal app logs vllm-server
```

### Check Container Status

```bash
modal container list --app mindbot-festival-2045
```

## Cost Management 💰

Modal charges based on:
- Compute time (CPU/GPU usage)
- Container running time
- Storage

Tips to minimize costs:
- Use `serve` for development (free)
- Deploy for production only
- Modal auto-scales down when not in use
- Set appropriate timeouts in the config

## Updating MindBot 🔄

### Update Personality

1. Edit `AGENTS/nodes/mindbot/processors/festival_rag.py`
2. Modify system prompt in `get_system_prompt()`
3. Redeploy: `modal deploy -m AGENTS.nodes.mindbot.mindbot_app`

### Update Knowledge Base

1. Edit `AGENTS/nodes/mindbot/assets/festival_knowledge.md`
2. Redeploy: `modal deploy -m AGENTS.nodes.mindbot.mindbot_app`
3. Knowledge is re-embedded automatically

### Update Voice Settings

1. Edit `AGENTS/nodes/mindbot/mindbot_bot.py`
2. Change voice/speed in TTS configuration
3. Redeploy

## Kiosk Setup 🖥️

For festival kiosk deployment:

1. Deploy MindBot as above
2. Set up dedicated tablet/kiosk device
3. Open browser in kiosk mode pointing to your deployment URL
4. Configure auto-start on boot
5. Disable sleep/screensaver
6. Test audio output levels

### Browser Kiosk Mode

**Chrome**:
```bash
chrome.exe --kiosk --app=YOUR_MINDBOT_URL
```

**Firefox**:
```bash
firefox.exe -kiosk YOUR_MINDBOT_URL
```

## Security Notes 🔒

- The `api_key` in the code is for internal Modal service communication
- WebRTC connections are encrypted
- No user data is stored permanently
- Conversations are not logged by default

## Support & Debugging 💡

### Enable Verbose Logging

In `mindbot_bot.py`, the logger is already set to DEBUG level.

### Test Individual Components

```bash
# Test RAG retrieval
python -c "from AGENTS.nodes.mindbot.processors.festival_rag import ChromaVectorDB; db = ChromaVectorDB(); print(db.query('Who is playing tonight?'))"

# Test TTS service
modal run -m server.tts.kokoro_tts::KokoroTTS.ping
```

## Next Steps 🎯

1. ✅ Deploy MindBot
2. ✅ Test basic interaction
3. 🎨 Customize personality if needed
4. 📝 Expand knowledge base with real festival data
5. 🎨 Create custom animation frames
6. 🚀 Deploy to kiosk devices

## Quick Reference Commands

```bash
# Deploy everything
modal deploy -m server.llm.vllm_server
modal deploy -m server.stt.parakeet_stt
modal deploy -m server.tts.kokoro_tts
modal deploy -m AGENTS.nodes.mindbot.mindbot_app

# Development mode
modal serve -m AGENTS.nodes.mindbot.mindbot_app

# View logs
modal app logs mindbot-festival-2045

# Check status
modal app list

# Stop services
modal app stop mindbot-festival-2045
```

---

**Ready to save humanity through music? Let's go! 🎸🤖⚡**

For more details, see [AGENTS/README.md](../../README.md)
