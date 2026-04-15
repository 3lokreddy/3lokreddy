# Coursera Coach on ChatGPT (with persistent memory)

This repo now contains a simple Streamlit app that behaves like a Coursera-style study coach backed by ChatGPT, with persistent learner memory stored in SQLite.

## Features

- Ask learning questions and get ChatGPT tutoring responses.
- Save learner-specific memory (goals, preferences, weak areas).
- Reuse saved memory in future prompts for personalized coaching.
- Local persistence with `memory.db`.

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your API key:

```bash
export OPENAI_API_KEY="your_key_here"
```

4. Run the app:

```bash
streamlit run app.py
```

## File overview

- `app.py`: Streamlit app + SQLite memory logic.
- `requirements.txt`: Python dependencies.
- `.env.example`: Example environment variable setup.

## Notes

- Memory is keyed by `Learner ID` so multiple users can keep separate memory.
- The app uses `gpt-4.1-mini` by default; change it in `ask_chatgpt` if needed.
