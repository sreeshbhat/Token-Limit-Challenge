# Token Limit Prompt Challenge

A beginner-friendly Streamlit classroom app where students write prompts under strict word limits, get AI-evaluated feedback, and compete on a leaderboard.

## Features

- Student login with name, roll number, and optional class/section
- Four challenge rounds with strict word limits
- AI evaluation with support for OpenAI, Google Gemini, and Groq
- Student-provided API key support from the sidebar
- Instructor fallback API keys loaded securely from `.env`
- SQLite database for students, submissions, and leaderboard data
- My Results section with feedback and improved prompt suggestions
- Leaderboard ranked by total score
- Admin tools for CSV export, reset, and submission review

## Project Structure

```text
token-limit-challenge/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── database.py
├── ai_evaluator.py
└── utils.py
```

## Installation

1. Clone or open this project folder.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Create `.env`

1. Copy `.env.example` to `.env`.
2. Add any instructor fallback API keys you want to support.
3. Set an admin password for reset/export actions.

Example:

```env
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
ADMIN_PASSWORD=your_admin_password
```

## Run the App

```bash
streamlit run app.py
```

## How Students Use Their Own API Key

- Students can select a provider in the sidebar.
- They can paste their own API key into the sidebar input.
- The app uses the student-entered API key first.
- Student API keys are not saved in the database.

## Instructor Fallback Key Behavior

- If a student does not enter an API key, the app checks `.env`.
- The fallback key used depends on the selected provider:
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY`
  - `GROQ_API_KEY`
- If neither a student key nor an instructor fallback key exists, the app shows a warning and blocks evaluation safely.

## Leaderboard Logic

- Scores are stored per round in SQLite (`challenge.db`).
- The leaderboard shows:
  - Rank
  - Student name
  - Roll number
  - Total score
  - Average score
  - Rounds attempted
- Ranking is sorted by total score descending, then average score descending.

## Notes

- The app uses AI models to score prompt quality and return JSON feedback.
- If an API returns invalid JSON or fails, the app shows a safe error instead of crashing.
- Model names are defined at the top of `ai_evaluator.py` for easy updates.
