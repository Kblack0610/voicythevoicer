# Voice Assistant Project Scratchpad

## Project Goal
Create a speech-to-text solution that can:
1. Convert spoken words to text
2. Integrate with LLM providers
3. Input text into applications or run terminal commands

## Tasks
- [X] Create project structure
- [ ] Research speech recognition options (SpeechNote or alternatives)
- [ ] Implement basic speech recognition functionality
- [ ] Add integration with LLM providers
- [ ] Implement text input into applications or terminal commands
- [ ] Test and refine

## Implementation Plan
1. Use Python for the implementation
2. Create a virtual environment
3. Implement speech recognition using appropriate libraries
4. Add LLM integration
5. Add functionality to input text or run commands

## Research Notes
- SpeechNote was mentioned as a potential option, but we should evaluate:
  - Python libraries like SpeechRecognition, which supports multiple engines
  - Cloud services like Google Speech-to-Text, Azure Speech, etc.
  - Offline options like Vosk or Mozilla DeepSpeech

## Dependencies to consider
- speech_recognition
- pyaudio (for microphone input)
- requests/openai (for LLM API calls)
- pyautogui (for application input)
- subprocess (for terminal commands)

## Lessons
(Add lessons learned during development here)