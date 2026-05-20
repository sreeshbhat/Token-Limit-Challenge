import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

CHALLENGES = [
    {
        "round": 1,
        "title": "Client Delay Email",
        "word_limit": 50,
        "task": "Write a prompt that makes AI generate a professional email informing a client that delivery is delayed by 3 days due to final testing.",
    },
    {
        "round": 2,
        "title": "Customer JSON Extractor",
        "word_limit": 30,
        "task": "Write a prompt that makes AI extract customer name, email, phone, and issue into valid JSON from a support message.",
    },
    {
        "round": 3,
        "title": "Vector Databases for Beginners",
        "word_limit": 15,
        "task": "Write a prompt that makes AI explain vector databases to complete beginners using simple language.",
    },
    {
        "round": 4,
        "title": "Meeting Notes Summarizer",
        "word_limit": 10,
        "task": "Write a prompt that makes AI summarize meeting notes into action items.",
    },
]

PROVIDER_ENV_MAP = {
    "OpenAI": "OPENAI_API_KEY",
    "Google Gemini": "GEMINI_API_KEY",
    "Groq": "GROQ_API_KEY",
}

PROVIDER_KEY_HINTS = {
    "OpenAI": "OpenAI keys usually start with 'sk-' or 'sess-'",
    "Google Gemini": "Gemini keys usually start with 'AIza'",
    "Groq": "Groq keys usually start with 'gsk_'",
}


def count_words(text: str) -> int:
    return len(re.findall(r"\b\S+\b", text.strip()))


def validate_api_key_format(provider: str, api_key: str) -> bool:
    key = api_key.strip()
    if not key:
        return False

    if provider == "OpenAI":
        return key.startswith(("sk-", "sess-"))
    if provider == "Google Gemini":
        return key.startswith("AIza")
    if provider == "Groq":
        return key.startswith("gsk_")
    return True


def get_provider_key_hint(provider: str) -> str:
    return PROVIDER_KEY_HINTS.get(provider, "Use a valid API key for the selected provider.")


def get_default_provider() -> str:
    for provider, env_name in PROVIDER_ENV_MAP.items():
        value = os.getenv(env_name, "").strip()
        if value and validate_api_key_format(provider, value):
            return provider
    return "OpenAI"


def resolve_api_key(provider: str, student_api_key: str) -> Dict[str, Optional[str]]:
    env_name = PROVIDER_ENV_MAP.get(provider)
    student_key = student_api_key.strip()
    instructor_key = os.getenv(env_name, "").strip() if env_name else ""

    if student_key:
        is_valid = validate_api_key_format(provider, student_key)
        return {
            "api_key": student_key if is_valid else None,
            "source": "student",
            "env_name": env_name,
            "is_valid": is_valid,
            "message": None if is_valid else f"Student API key does not match {provider}. {get_provider_key_hint(provider)}.",
        }
    if instructor_key:
        is_valid = validate_api_key_format(provider, instructor_key)
        return {
            "api_key": instructor_key if is_valid else None,
            "source": "instructor",
            "env_name": env_name,
            "is_valid": is_valid,
            "message": None if is_valid else f"{env_name} does not look like a valid {provider} key. {get_provider_key_hint(provider)}.",
        }
    return {
        "api_key": None,
        "source": None,
        "env_name": env_name,
        "is_valid": False,
        "message": f"No API key available for {provider}.",
    }


def get_admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "").strip()


def safe_json_loads(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    if not cleaned:
        raise ValueError("Empty AI response.")

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_evaluation(data: Dict[str, Any]) -> Dict[str, Any]:
    def to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    clarity = min(max(to_float(data.get("clarity")), 0.0), 2.0)
    context = min(max(to_float(data.get("context")), 0.0), 2.0)
    output_format = min(max(to_float(data.get("output_format")), 0.0), 2.0)
    constraints = min(max(to_float(data.get("constraints")), 0.0), 2.0)
    effectiveness = min(max(to_float(data.get("effectiveness")), 0.0), 2.0)

    total = round(clarity + context + output_format + constraints + effectiveness, 2)
    reported_score = min(max(to_float(data.get("score"), total), 0.0), 10.0)

    # Prefer the rubric-derived total if the model's score is materially inconsistent.
    score = total if abs(reported_score - total) > 1 else round(reported_score, 2)

    return {
        "score": score,
        "clarity": round(clarity, 2),
        "context": round(context, 2),
        "output_format": round(output_format, 2),
        "constraints": round(constraints, 2),
        "effectiveness": round(effectiveness, 2),
        "feedback": str(data.get("feedback", "No feedback provided.")).strip(),
        "improved_prompt": str(data.get("improved_prompt", "")).strip(),
    }


def leaderboard_to_csv(rows) -> bytes:
    import pandas as pd

    frame = pd.DataFrame(rows)
    return frame.to_csv(index=False).encode("utf-8")


def inject_css() -> None:
    import streamlit as st

    st.markdown(
        """
        <style>
        .stApp {
            color: #17324a;
            background:
                radial-gradient(circle at top right, rgba(71, 163, 255, 0.16), transparent 28%),
                radial-gradient(circle at top left, rgba(32, 201, 151, 0.12), transparent 25%),
                linear-gradient(180deg, #f6fbff 0%, #eef5fb 100%);
        }
        .stApp, .stApp p, .stApp label, .stApp span, .stApp div, .stApp li {
            color: #17324a;
        }
        h1, h2, h3, h4, h5, h6 {
            color: #14324a !important;
        }
        .hero-card, .metric-card {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(28, 63, 95, 0.10);
            border-radius: 18px;
            padding: 1.2rem;
            box-shadow: 0 12px 30px rgba(38, 70, 83, 0.08);
        }
        .hero-title {
            font-size: 2rem;
            font-weight: 700;
            color: #14324a;
            margin-bottom: 0.2rem;
        }
        .hero-subtitle {
            color: #46637c;
            font-size: 1rem;
            margin-bottom: 0;
        }
        .badge {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: #e8f4ff;
            color: #0b5cab;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 0.4rem;
        }
        .round-card {
            background: #ffffff;
            border-left: 5px solid #0b84f3;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 24px rgba(20, 50, 74, 0.06);
            margin-bottom: 0.8rem;
        }
        .small-muted {
            color: #5b7388;
            font-size: 0.92rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid rgba(28, 63, 95, 0.10);
            border-radius: 14px;
            padding: 0.35rem;
        }
        .stTabs [data-baseweb="tab"] {
            color: #23445f !important;
            background: transparent;
            border-radius: 10px;
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            background: #dff0ff !important;
            color: #0b5cab !important;
        }
        .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label {
            color: #17324a !important;
            font-weight: 600;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
            color: #17324a !important;
            background: rgba(255, 255, 255, 0.95) !important;
            border-color: rgba(28, 63, 95, 0.18) !important;
        }
        .stTextInput input::placeholder, .stTextArea textarea::placeholder {
            color: #71879b !important;
        }
        .stMarkdown, .stMarkdown p, .stCaptionContainer, .stAlert, .stProgress {
            color: #17324a !important;
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid rgba(28, 63, 95, 0.10);
            border-radius: 14px;
            padding: 0.85rem;
        }
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricDelta"] div {
            color: #17324a !important;
        }
        div[data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid rgba(28, 63, 95, 0.10);
            border-radius: 18px;
            padding: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
