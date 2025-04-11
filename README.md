# Voice2Text

A modular and extensible voice-to-text tool that allows you to input spoken words directly into any application input field.

## Features

- **Multiple Speech Recognition Engines**: Google, Whisper, Deepgram, and more
- **Voice Activity Detection**: Only processes audio when speech is detected
- **Modular Architecture**: Easily extensible with new engines and features
- **Error Suppression**: Reduces ALSA/JACK errors and other noise
- **Configurable**: YAML-based configuration with sensible defaults

## Installation

1. Clone the repository or download the files
2. Install the dependencies:

```bash
pip install -r requirements.txt
```

3. Optional: Install additional dependencies for specific engines:

```bash
# For Whisper local model
pip install openai-whisper

# For faster Whisper implementation
pip install faster-whisper

# For Deepgram
pip install deepgram-sdk
```

4. Make the script executable:

```bash
chmod +x voice2text
```

## Usage

### Basic Usage

Simply run the script:

```bash
./voice2text
```

This will start listening and transcribe your speech to the current active window.

### Configuration

Configuration is handled via `config.yaml`. You can modify settings like:

- Which speech recognition engine to use
- Audio parameters (sample rate, channels, etc.)
- Voice activity detection settings
- Output behavior

## Available Engines

### Google Speech-to-Text
- Good accuracy for general use
- Requires internet connection
- Free for limited usage

### Whisper (OpenAI)
- Highly accurate, supports many languages
- Can run locally or via API
- Local models range from tiny (fast) to large (most accurate)

### Deepgram
- Very low latency, excellent for real-time use
- Requires internet connection and API key
- Commercial service with free tier available

## Architecture

- `core/`: Core functionality modules
  - `audio_input.py`: Audio recording and voice activity detection
  - `engines.py`: Engine interface and registry
  - `error_handlers.py`: Error suppression utilities
  - `text_output.py`: Text insertion into applications

- `engines/`: Speech recognition engine implementations
  - `google.py`: Google Speech Recognition
  - `whisper.py`: OpenAI Whisper (local and API)
  - `deepgram.py`: Deepgram API integration

- `tests/`: Test modules
  - `test_engines.py`: Tests for engine functionality
  - `test_audio_input.py`: Tests for audio recording and processing

## API Keys

Some engines require API keys:

- **Google Cloud**: Set `GOOGLE_CLOUD_SPEECH_API_KEY` environment variable
- **OpenAI API**: Set `OPENAI_API_KEY` environment variable
- **Deepgram**: Set `DEEPGRAM_API_KEY` environment variable

## Testing

Run the test suite:

```bash
python -m unittest discover tests
```

## Contributing

Contributions are welcome! To add a new engine:

1. Create a new file in the `engines/` directory
2. Implement the `SpeechEngine` interface
3. Add the `@register_engine` decorator to your class

## License

This project is licensed under the MIT License.