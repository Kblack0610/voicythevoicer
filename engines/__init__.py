"""
Speech recognition engines for Voice2Text.

This package contains implementations of various speech recognition engines:
- Google Speech API
- OpenAI Whisper (local and API)
- Deepgram
- Groq's distil-whisper
- Speechmatics

Each engine implements the SpeechEngine interface defined in core.engines.
"""

# Import all available engines so they register themselves
try:
    from .google import GoogleEngine
except ImportError:
    pass

try:
    from .whisper import WhisperEngine
except ImportError:
    pass

try:
    from .deepgram import DeepgramEngine
except ImportError:
    pass

try:
    from .groq import GroqEngine
except ImportError:
    pass

try:
    from .speechmatics import SpeechmaticsEngine
except ImportError:
    pass