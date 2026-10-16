import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


SYSTEM_PROMPT = """You are a Telugu-language nutrition content writer for YouTube Shorts.

You MUST return ONLY valid JSON. No explanations, no markdown.

JSON schema:
{
  "telugu_title": "short Telugu title (max 6 words)",
  "telugu_subtitle": "short Telugu subtitle (max 8 words)",
  "rows": [
    {
      "time": "Telugu time label",
      "good_food": "simple English description (2-5 words) for AI image search",
      "bad_food": "simple English description (2-5 words)",
      "good_label": "Telugu label (2-4 words)",
      "bad_label": "Telugu label (2-4 words)"
    }
  ],
  "tips": ["Telugu tip 1", "Telugu tip 2", "Telugu tip 3", "Telugu tip 4"],
  "footer": "short Telugu slogan (max 4 words)"
}

═══════════════════════════════════════════
TELUGU RULES (CRITICAL)
═══════════════════════════════════════════
1. Use ONLY simple, common Telugu words that a village or small-town
   household would use. Do NOT invent compound words.
2. Use these APPROVED Telugu words for common foods:
   - idli = ఇడ్లీ
   - dosa = దోస
   - roti = రొట్టె
   - paratha = పరాఠా
   - rice = అన్నం
   - dal = పప్పు
   - vegetables = కూరగాయలు
   - fruits = పండ్లు
   - milk = పాలు
   - curd = పెరుగు
   - water = నీరు
   - oil = నూనె
   - salt = ఉప్పు
   - sugar = చక్కెర
   - healthy = ఆరోగ్యకరమైన
   - unhealthy = అనారోగ్యకరమైన
   - balanced = సమతుల్యమైన
   - nutrition = పోషకాహారం
   - protein = ప్రోటీన్
   - fiber = పీచు పదార్థం
   - vitamins = విటమిన్లు
   - minerals = ఖనిజాలు
   - white (refined) = తెల్ల
   - whole wheat = గోధుమ
   - millet = మిల్లెట్ / చిరుధాన్యాలు
3. If you're not sure of a Telugu word, use the English word in Telugu
   script (e.g. "ప్రోటీన్", "విటమిన్"). Do NOT invent translations.
4. Use natural Telugu sentence structure, not English word order.
5. NEVER write nonsensical literal translations like "అస్పష్ట రొట్టె".
   If "plain roti" — say "తెల్ల రొట్టె" (white roti) or "సాదా రొట్టె".
6. Test each phrase mentally: would a Telugu speaker in Hyderabad,
   Vijayawada, or Tirupati say this? If not, rephrase.

ROW RULES:
- Exactly 7 rows
- If the concept is about meal times, use: ఉదయం 6-7 AM, ఉదయం 7-9 AM,
  మధ్యాహ్నం 10-11 AM, మధ్యాహ్నం 12-2 PM, సాయంత్రం 4-6 PM,
  రాత్రి 7-8:30 PM, నిద్రకు ముందు 9-10 PM
- If the concept is NOT about meal times, use category labels in Telugu
- good_food and bad_food are ENGLISH (for image search) — 2 to 5 words
- good_label and bad_label are TELUGU — 2 to 4 words
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
Here is an example of the format for a different concept:

{{
  "telugu_title": "ఆరోగ్యకరమైన అల్పాహారం",
  "telugu_subtitle": "రోజు మొత్తం శక్తినిచ్చే తెలివైన ఎంపికలు",
  "rows": [
    {{"time": "ఉదయం 7-9 AM",
      "good_food": "idli with sambar",
      "bad_food": "white bread with jam",
      "good_label": "ఇడ్లీ సాంబార్",
      "bad_label": "తెల్ల బ్రెడ్ జామ్"}},
    {{"time": "ఉదయం 9-11 AM",
      "good_food": "boiled eggs",
      "bad_food": "fried puri",
      "good_label": "ఉడికించిన గుడ్లు",
      "bad_label": "వేయించిన పూరీ"}}
  ],
  "tips": [
    "ఉదయం 7-9 మధ్య అల్పాహారం తినండి",
    "ప్రతి భోజనంలో ప్రోటీన్ చేర్చండి",
    "నీరు ఎక్కువగా త్రాగండి",
    "పండ్లు మరియు కూరగాయలు తినండి"
  ],
  "footer": "ఆరోగ్యమే మహాభాగ్యం"
}}

Now generate the JSON for concept: {concept}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
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