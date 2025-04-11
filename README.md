# Voice Assistant

A speech-to-text solution that converts spoken words to text and can integrate with LLM providers, input text into applications, or run terminal commands.

## Features

- Speech recognition using multiple providers
- Integration with LLM APIs
- Text input into applications
- Execute terminal commands via voice
- Customizable hotkeys for start/stop listening

## Installation

1. Clone this repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API keys (if using LLM integration)

## Usage

### Basic Speech Recognition

```bash
python voice_assistant.py
```

### With LLM Integration

```bash
python voice_assistant.py --llm openai
```

### To Input Text into Applications

```bash
python voice_assistant.py --input-mode application
```

### To Run Terminal Commands

```bash
python voice_assistant.py --input-mode terminal
```

## Configuration

Edit `config.py` to customize:
- Hotkey combinations
- Speech recognition engine
- LLM provider settings
- Default application focus

## License

MIT