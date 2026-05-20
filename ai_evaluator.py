from typing import Any, Dict

import google.generativeai as genai
from groq import Groq
from openai import OpenAI

from utils import normalize_evaluation, safe_json_loads

OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"
GROQ_MODEL = "llama-3.1-8b-instant"


def build_evaluation_messages(student_prompt: str, challenge: Dict[str, Any]) -> tuple[str, str]:
    # One shared evaluator prompt keeps scoring consistent across providers.
    system_prompt = """
You are an expert prompt engineering evaluator for a classroom challenge.
Score the student's prompt out of 10 using this rubric:
- Clarity: 2 marks
- Context: 2 marks
- Output format: 2 marks
- Constraints: 2 marks
- Effectiveness: 2 marks

Return valid JSON only with these exact keys:
{
  "score": 8,
  "clarity": 2,
  "context": 1.5,
  "output_format": 2,
  "constraints": 1.5,
  "effectiveness": 1,
  "feedback": "Short explanation",
  "improved_prompt": "A better version of the student's prompt"
}

Rules:
- Output JSON only, with no markdown and no extra commentary.
- The total score should align with the component marks.
- Feedback must be concise and classroom-friendly.
- Improved prompt must remain within the round word limit.
""".strip()

    user_prompt = f"""
Challenge title: {challenge["title"]}
Round number: {challenge["round"]}
Task description: {challenge["task"]}
Maximum allowed words: {challenge["word_limit"]}

Student prompt:
{student_prompt}

Evaluate the prompt using the rubric and return JSON only.
""".strip()
    return system_prompt, user_prompt


def evaluate_with_openai(student_prompt: str, challenge: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    system_prompt, user_prompt = build_evaluation_messages(student_prompt, challenge)
    client = OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    return normalize_evaluation(safe_json_loads(content))


def evaluate_with_gemini(student_prompt: str, challenge: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    system_prompt, user_prompt = build_evaluation_messages(student_prompt, challenge)
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        system_instruction=system_prompt,
    )
    response = model.generate_content(
        user_prompt,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    content = getattr(response, "text", "") or ""
    return normalize_evaluation(safe_json_loads(content))


def evaluate_with_groq(student_prompt: str, challenge: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    system_prompt, user_prompt = build_evaluation_messages(student_prompt, challenge)
    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content or ""
    return normalize_evaluation(safe_json_loads(content))


def evaluate_prompt(
    provider: str,
    student_prompt: str,
    challenge: Dict[str, Any],
    api_key: str,
) -> Dict[str, Any]:
    try:
        if provider == "OpenAI":
            return evaluate_with_openai(student_prompt, challenge, api_key)
        if provider == "Google Gemini":
            return evaluate_with_gemini(student_prompt, challenge, api_key)
        if provider == "Groq":
            return evaluate_with_groq(student_prompt, challenge, api_key)
        return {"error": f"Unsupported provider: {provider}"}
    except Exception as exc:
        # Streamlit shows this safely instead of letting provider or JSON issues crash the app.
        return {
            "error": (
                "Evaluation failed due to an API or parsing error. "
                f"Details: {exc}"
            )
        }
