import os

from PIL import Image
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    OutputImageRawFrame,
    SpriteFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor, FrameProcessorQueue


def get_frames(substring_match: str):
    """Load animation frames for MindBot based on state (listening, talking, thinking)."""
    
    sprites = []
    parent_dir = os.path.dirname(os.path.dirname(__file__))
    # Get all PNG files from the assets directory and sort them
    assets_dir = os.path.join(parent_dir, "assets", "animation_frames")
    
    # If the directory doesn't exist or has no files, return a placeholder
    if not os.path.exists(assets_dir):
        # For now, fall back to the original modalbot frames until custom ones are created
        fallback_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "server", "bot", "assets", "animation_frames"
        )
        assets_dir = fallback_dir
    
    for filename in sorted(os.listdir(assets_dir)):
        # Map mindbot states to modalbot frames as placeholders
        if substring_match == "listening" and "listening" in filename and filename.endswith('.png'):
            full_path = os.path.join(assets_dir, filename)
            with Image.open(full_path) as img:
                sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))
        elif substring_match == "talking" and "talking" in filename and filename.endswith('.png'):
            full_path = os.path.join(assets_dir, filename)
            with Image.open(full_path) as img:
                sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))
        elif substring_match == "thinking" and "thinking" in filename and filename.endswith('.png'):
            full_path = os.path.join(assets_dir, filename)
            with Image.open(full_path) as img:
                sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))

    if len(sprites) == 1:
        return sprites[0]
    elif len(sprites) > 1:
        return SpriteFrame(sprites)
    else:
        # If no frames found, return None - video will be disabled
        return None


class MindBotAnimation(FrameProcessor):
    """Manages MindBot's visual animation states.

    Switches between static (listening), thinking, and talking states based on
    the bot's current status. MindBot uses a retro-futuristic aesthetic with
    slight glitches to match the personality.
    """

    def __init__(self):
        super().__init__()
        self._is_talking = False
        self._talking_frames = get_frames("talking")
        self._thinking_frames = get_frames("thinking")
        self._listening_frames = get_frames("listening")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process incoming frames and update animation state.

        Args:
            frame: The incoming frame to process
            direction: The direction of frame flow in the pipeline
        """
        
        await super().process_frame(frame, direction)
        # Switch to talking animation when bot starts speaking
        if isinstance(frame, BotStartedSpeakingFrame):
            print("MindBot started speaking")
            if not self._is_talking:
                self.__input_queue = FrameProcessorQueue()
                if self._talking_frames:
                    await self.push_frame(self._talking_frames)
                self._is_talking = True
        # Return to static frame when bot stops speaking
        elif isinstance(frame, BotStoppedSpeakingFrame):
            print("MindBot stopped speaking")
            self.__input_queue = FrameProcessorQueue()
            if self._listening_frames:
                await self.push_frame(self._listening_frames)
            self._is_talking = False
        # Switch to thinking animation when user stops speaking
        elif isinstance(frame, UserStoppedSpeakingFrame):
            print("User stopped speaking - MindBot thinking")
            self.__input_queue = FrameProcessorQueue()
            if self._thinking_frames:
                await self.push_frame(self._thinking_frames)
            self._is_talking = False

        await self.push_frame(frame, direction)
