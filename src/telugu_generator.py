import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """You are a Telugu-language nutrition content writer for YouTube Shorts.
You write simple, grammatically correct Telugu that common people understand.

You MUST return ONLY valid JSON. No explanations, no markdown, no code fences.

The JSON schema:
{
  "telugu_title": "short Telugu title (max 6 words)",
  "telugu_subtitle": "short Telugu subtitle (max 8 words)",
  "rows": [
    {
      "time": "Telugu time label like ఉదయం 7-9 AM",
      "good_food": "simple english description of healthy food for AI image generation",
      "bad_food": "simple english description of unhealthy alternative for AI image generation",
      "good_label": "Telugu label (2-4 words)",
      "bad_label": "Telugu label (2-4 words)"
    }
  ],
  "tips": [
    "Telugu tip 1",
    "Telugu tip 2",
    "Telugu tip 3",
    "Telugu tip 4"
  ],
  "footer": "short Telugu slogan (max 4 words)"
}

RULES:
- Exactly 7 rows.
- Time labels use Indian meal times: ఉదయం 6-7 AM, ఉదయం 7-9 AM, మధ్యాహ్నం 10-11 AM, మధ్యాహ్నం 12-2 PM, సాయంత్రం 4-6 PM, రాత్రి 7-8:30 PM, నిద్రకు ముందు 9-10 PM.
- If the concept is NOT about meal timing, use category labels in Telugu instead (like ప్రోటీన్, ఫైబర్, విటమిన్).
- good_food and bad_food: simple 2-5 word English descriptions for image search.
- Telugu must be correct, simple, and readable.
- No medical claims, no dosages, no disease cures.
- Focus on practical daily eating habits.
"""


class TeluguGenerator:
    """Uses Groq LLM to generate Telugu content for any nutrition concept."""

    def __init__(self, cache_path: str = "telugu_cache.json"):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY not set. Create a .env file with:\n"
                "GROQ_API_KEY=gsk_..."
            )
        self.client = Groq(api_key=api_key)
        self.model = "openai/gpt-oss-120b"
        self.cache_path = cache_path
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    def get_content(self, english_concept: str, info_hint: str = "") -> dict:
        """Get Telugu content for a concept. Uses cache when available."""
        cache_key = english_concept.lower().strip()

        if cache_key in self.cache:
            print(f"    → Using cached Telugu content for: {english_concept}")
            return self.cache[cache_key]

        print(f"    → Asking Groq to write Telugu content...")
        content = self._call_groq(english_concept, info_hint)

        self.cache[cache_key] = content
        self._save_cache()
        print(f"    ✓ Telugu content saved to cache")

        return content

    def _call_groq(self, concept: str, info_hint: str) -> dict:
        user_msg = f"""Concept: {concept}
Context: {info_hint}

Generate the Telugu content JSON for this nutrition concept."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=2500,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Groq returned invalid JSON: {e}\n\nRaw:\n{raw[:500]}"
            )

        # Validate structure
        required = ["telugu_title", "telugu_subtitle", "rows",
                    "tips", "footer"]
        for key in required:
            if key not in data:
                raise RuntimeError(f"Missing key in LLM output: {key}")

        if len(data["rows"]) < 5:
            raise RuntimeError(
                f"LLM returned only {len(data['rows'])} rows, expected 7"
            )

        # Ensure exactly 7 rows
        data["rows"] = data["rows"][:7]

        # Pad if fewer than 7
        while len(data["rows"]) < 7:
            data["rows"].append({
                "time": "అదనపు",
                "good_food": "fresh fruit",
                "bad_food": "processed snack",
                "good_label": "తాజా పండు",
                "bad_label": "ప్రాసెస్డ్ స్నాక్",
            })

        return data