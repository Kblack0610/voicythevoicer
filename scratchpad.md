# Voice-to-Text Assistant Scratchpad

## Project Goal
Create a voice-to-text tool that allows inputting spoken words directly into any application input field.

## Progress
- [X] Create basic voice-to-text functionality
- [X] Implement continuous listening mode
- [X] Optimize for reduced lag and error suppression
- [X] Design modular architecture for better maintainability
- [X] Create core modules (audio, engines, text output, error handlers)
- [X] Implement Google speech recognition engine
- [X] Create main application and executable script
- [X] Fix import issues with speech recognition engines
- [X] Install and verify Google Speech Recognition engine
- [X] Install and verify Whisper engine
- [ ] Test voice-to-text functionality with multiple engines
- [X] Set up configuration system with YAML support
- [X] Implement Whisper speech recognition engine (local and API)
- [X] Implement Deepgram speech recognition engine
- [X] Implement Speechmatics speech recognition engine
- [X] Implement Groq speech recognition engine
- [X] Create automatic engine selection and fallback utility
- [X] Create requirements.txt and project documentation
- [X] Add comprehensive test coverage with test modules for engines and core components
- [X] Create installation script for easy setup
- [X] Create engine comparison tool for performance testing
- [X] Create environment testing tool for application compatibility
- [X] Test in various applications and environments

## Current Improvements

### Speed and Lag Reduction
- Reduced ambient noise adjustment duration from 1.0s to 0.5s
- Shortened timeout values for faster speech detection
- Adjusted phrase and pause thresholds for quicker response
- Set shorter operation_timeout for the Google API
- Minimized sleep times between operations

### Error Suppression
- Added ALSA/JACK error suppression through stderr redirection
- Added `--quiet` flag to completely suppress audio system errors

### Configuration Improvements
- Added dynamic energy threshold adjustment
- Adjusted default values for better performance
- Added more command-line options for fine-tuning

## New Modular Architecture

### Directory Structure
```
voice_assistant/
├── core/
│   ├── __init__.py
│   ├── audio_input.py    # Audio capture module
│   ├── engines.py        # Speech recognition engines
│   ├── text_output.py    # Text output handling
│   └── error_handlers.py # Error suppression
├── engines/
│   ├── __init__.py
│   ├── google.py         # Google Speech API
│   ├── whisper.py        # OpenAI Whisper (local/API)
│   ├── deepgram.py       # Deepgram API
│   ├── groq.py           # Groq's distil-whisper
│   └── speechmatics.py   # Speechmatics API
├── tests/
│   ├── test_audio_input.py
│   ├── test_engines.py
│   └── test_integration.py
├── voice2text            # Main executable 
└── config.yaml           # Configuration
```

### Engine Comparison

| Engine       | Latency    | Accuracy   | Offline | Notes                          |
|--------------|------------|------------|---------|--------------------------------|
| Google       | Medium     | Good       | No      | Default option, API-based      |
| Whisper      | Low-Medium | Excellent  | Yes     | Local or API, adjustable size  |
| Deepgram     | Very Low   | Excellent  | No      | Real-time streaming            |
| Groq         | Very Low   | Very Good  | No      | Extremely fast inference       |
| Speechmatics | Low        | Very Good  | No      | Good for interactive use       |

### Implementation Plan

1. **Core Module Development**:
   - Speech Engine Interface
   - Audio Input System
   - Text Output Manager
   - Error Handling Layer

2. **Engine Integration**:
   - Google Engine (existing)
   - Whisper Implementation
   - API-based services

3. **Testing Framework**:
   - Unit tests for each component
   - Integration tests
   - Performance benchmarks

4. **Configuration System**:
   - YAML-based config
   - Environment variables
   - Command-line override

## Usage
```bash
/home/kblack0610/.dotfiles/.local/bin/voice_assistant/voice2text [options]
```

### Key Options
- `--engine`: Select speech recognition engine (google, whisper, deepgram, etc.)
- `--quiet`: Suppress ALSA errors completely
- `--config`: Path to custom configuration file
- `--test`: Run test suite

## Lessons
- PyAudio requires PortAudio dev libraries (`portaudio19-dev`)
- ALSA/JACK errors can be suppressed with stderr redirection
- Modular design makes debugging and extension easier
- Modern AI engines (Whisper, Deepgram) offer better accuracy and speed
- Exception handling is critical for audio operations on Linux
- For reliable output, multiple typing methods (pyautogui, keyboard, pynput) should be supported
- Voice Activity Detection significantly improves response time by only processing actual speech
- Providing fallback engines ensures the system works even when preferred engines aren't available
- Fine-tuning speech recognition parameters significantly impacts latency
- When using virtual environments, always use the explicit path to the Python interpreter (`.venv/bin/python`) instead of relying on `source .venv/bin/activate` which may not correctly update Python aliases
- The `openai-whisper` package is imported as just `whisper` in Python code
- When installing packages with `uv`, they are correctly installed in the virtual environment's site-packages directory
- ALSA/JACK errors during audio testing can be safely ignored as they don't affect functionality