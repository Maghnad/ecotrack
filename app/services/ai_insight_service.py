"""
EcoTrack - AI Insight Service (Google Gemini)
Generates personalised, context-aware reduction tips from the user's
recent activity log using the Gemini generative AI model.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.secrets import get_secret

settings = get_settings()

# Hardcoded fallback tips used in testing or when Gemini is unavailable.
_FALLBACK_TIPS = [
    "Try switching one car journey per week to public transport — it's one of the highest-impact swaps you can make. 🚌",
    "Reducing beef consumption by just one meal a week saves roughly 52 kg of CO₂ per year. 🥗",
    "Lowering your home thermostat by 1°C reduces heating emissions by up to 10%. ❄️",
    "Short-haul flights are extremely carbon-intensive — consider if a train journey is viable instead. 🚂",
    "Washing clothes at 30°C instead of 60°C uses around 40% less energy. 🧺",
]


def generate_ai_insights(uid: str, recent_logs: list[dict], category: str = None) -> dict:
    """
    Analyses the user's recent footprint logs and returns personalised insights.
    Uses Gemini 1.5 Flash in production; returns structured fallback data in testing.
    """
    if settings.environment == "testing" or settings.gemini_api_key == "mock_key":
        return _build_mock_insight(recent_logs, category)

    prompt = _build_gemini_prompt(recent_logs, category)

    try:
        import google.generativeai as genai

        api_key = get_secret("gemini_api_key")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        tips_text = response.text.strip()
        tips = [t.strip("- ").strip()
                for t in tips_text.split("\n") if t.strip()]
        return {
            "tips": tips[:5],
            "weekly_summary": _summarise_logs(recent_logs),
            "biggest_emission_source": _find_biggest_source(recent_logs),
            "potential_savings_kg": _estimate_potential_savings(recent_logs),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return _build_mock_insight(recent_logs, category)


def chat_with_gemini(uid: str, message: str) -> dict:
    if settings.environment == "testing" or settings.gemini_api_key == "mock_key":
        return {"reply": f"Got it: {message}", "carbon_emissions_kg": 0.0, "message": "Mock response"}

    try:
        import google.generativeai as genai
        api_key = get_secret("gemini_api_key")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            f"User says: '{message}'. Act as EcoTrack's chatbot. "
            "Give a very short helpful reply and estimate the carbon footprint in kg CO2. "
            "Format: 'Reply text|2.5'. If no footprint, put 0."
        )
        response = model.generate_content(prompt)
        parts = response.text.split("|")
        reply = parts[0].strip() if parts else "I couldn't process that."
        kg = 0.0
        if len(parts) > 1:
            try:
                kg = float(parts[1].strip())
            except ValueError:
                pass
        return {"reply": reply, "carbon_emissions_kg": kg, "message": "Success"}
    except Exception:
        return {"reply": "Sorry, AI is offline.", "carbon_emissions_kg": 0.0, "message": "Error"}


def _build_gemini_prompt(logs: list[dict], category: str = None) -> str:
    log_summary = "\n".join(
        f"- {log.get('log_type', 'commute')}: {log.get('carbon_emissions_kg', 0):.3f} kg CO₂"
        f" ({log.get('transport_mode', log.get('meal_type', 'unknown'))})"
        for log in logs[-14:]  # Last 14 entries max to keep prompt tight
    )
    return f"""
You are EcoTrack's friendly climate coach. A user has shared their recent carbon footprint logs:

{log_summary}

Based on this data:
1. Identify their 1-2 biggest emission sources.
2. Generate exactly 3 specific, actionable, encouraging tips to reduce emissions. Focus strictly on {category if category else 'general habits'}.
   - Each tip should be practical and achievable.
   - Reference their actual data where relevant (e.g., "your commute is your biggest source…").
   - Keep each tip to 1-2 sentences, positive tone.
   - Format: one tip per line, no bullet prefix, no numbering.
3. Do not include any preamble or closing remarks.
"""


def _summarise_logs(logs: list[dict]) -> str:
    total_kg = sum(log_entry.get("carbon_emissions_kg", 0)
                   for log_entry in logs)
    if not logs:
        return "No activity logged yet this week."
    days = len(set(log_entry.get("logged_at", "")[:10] for log_entry in logs))
    return (
        f"This week you logged {days} day(s) of activity, "
        f"totalling {total_kg:.2f} kg CO₂."
    )


def _find_biggest_source(logs: list[dict]) -> str:
    categories: dict[str, float] = {}
    for log in logs:
        cat = log.get("log_type", "commute")
        categories[cat] = categories.get(
            cat, 0) + log.get("carbon_emissions_kg", 0)
    if not categories:
        return "None yet"
    return max(categories, key=lambda k: categories[k])


def _estimate_potential_savings(logs: list[dict]) -> float:
    """
    Simple heuristic: estimate 15% reduction if the user optimises their
    single biggest emission category.
    """
    total = sum(log_entry.get("carbon_emissions_kg", 0) for log_entry in logs)
    return round(total * 0.15, 2)


def _build_mock_insight(logs: list[dict], category: str = None) -> dict:
    tips = _FALLBACK_TIPS[:3]
    if category == "diet":
        tips = ["Try going meatless on Mondays.", "Choose local produce."] + tips[:1]
    elif category == "transport":
        tips = ["Walk short distances.", "Carpool to work."] + tips[:1]

    return {
        "tips": tips,
        "weekly_summary": _summarise_logs(logs),
        "biggest_emission_source": _find_biggest_source(logs),
        "potential_savings_kg": _estimate_potential_savings(logs),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "insight_category": category,
    }
