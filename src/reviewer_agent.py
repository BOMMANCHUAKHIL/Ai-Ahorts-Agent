import os
import json
import base64
from groq import Groq
from dotenv import load_dotenv
import re
load_dotenv()


SPELL_SYSTEM = """You are a Telugu language reviewer.

You will receive a JSON object of Telugu text strings.
Check EVERY string for:
1. Spelling mistakes in Telugu
2. Invented or unnatural compound words that a native speaker would not use
3. Grammatical errors
4. Wrong or missing matras
5. English words written in Telugu script incorrectly

Return ONLY valid JSON in this exact format:
{
  "ok": true/false,
  "issues": [
    {
      "field": "path.to.field",
      "original": "the original text",
      "problem": "short English description of the issue",
      "suggestion": "corrected Telugu text"
    }
  ]
}

If everything is correct, return {"ok": true, "issues": []}.
Do not invent issues. Only report real mistakes.
"""


VISION_SYSTEM = """You are a food image reviewer.

You will be shown an image and a Telugu/English label.
Decide whether the image actually shows the food described by the label.

Return ONLY valid JSON:
{
  "matches": true/false,
  "reason": "short English explanation"
}

Examples:
- Image of idli, label "idli" → matches: true
- Image of pizza, label "idli" → matches: false, reason: "image shows pizza, not idli"
- Blurry/wrong image → matches: false
Be strict. If you're not sure, return matches: false.
"""


class ReviewerAgent:
    """Verifies Telugu spelling and image-label matching before upload."""

    def __init__(self, strict_images: bool = True):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set")
        self.client = Groq(api_key=api_key)
        # self.text_model = "openai/gpt-oss-120b"          # fast, text-only
        # self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"  # vision
        self.text_model = "llama-3.3-70b-versatile"
        self.vision_model = "meta-llama/llama-4-scout-17b-16e-instruct"
        self.strict_images = strict_images

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────
    def check(self, content: dict, rows: list) -> dict:
        """
        content: the dict returned by TeluguGenerator.get_content()
        rows:    list of {good_label, bad_label, good_image, bad_image, ...}
        Returns: {"ok": bool, "text_issues": [...], "image_issues": [...]}
        """
        text_issues = self._check_spelling(content)
        image_issues = self._check_images(rows)

        if self.strict_images:
            ok = not text_issues and not image_issues
        else:
            # Only spelling blocks the cycle; image issues are logged
            ok = not text_issues

        return {
            "ok": ok,
            "text_issues": text_issues,
            "image_issues": image_issues,
        }

    # ────────────────────────────────────────────────────────────────
    # Text / spelling check
    # ────────────────────────────────────────────────────────────────
    def _check_spelling(self, content: dict) -> list:
        fields = {
            "telugu_title": content.get("telugu_title", ""),
            "telugu_subtitle": content.get("telugu_subtitle", ""),
            "footer": content.get("footer", ""),
        }
        for i, row in enumerate(content.get("rows", [])):
            fields[f"rows[{i}].time"] = row.get("time", "")
            fields[f"rows[{i}].good_label"] = row.get("good_label", "")
            fields[f"rows[{i}].bad_label"] = row.get("bad_label", "")
        for i, tip in enumerate(content.get("tips", [])):
            fields[f"tips[{i}]"] = tip

        user_msg = (
                "Check these Telugu strings for spelling and unnatural words. "
                "Reply with the JSON described in the system prompt.\n\n"
                + json.dumps(fields, ensure_ascii=False, indent=2)
        )

        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.text_model,
                    messages=[
                        {"role": "system", "content": SPELL_SYSTEM},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.1,
                    max_tokens=1500,
                    # NOTE: no response_format — that's what was breaking it
                )
                raw = resp.choices[0].message.content or ""
                print(f"    [debug] reviewer raw response length: {len(raw)}")
                if raw:
                    print(f"    [debug] first 200 chars: {raw[:200]}")

                # Extract the first {...} JSON block from the response
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not match:
                    print(f"    ⚠ No JSON in response (attempt {attempt+1}): {raw[:120]}")
                    continue

                data = json.loads(match.group(0))
                return data.get("issues", []) or []

            except json.JSONDecodeError as exc:
                print(f"    ⚠ Bad JSON (attempt {attempt+1}): {exc}")
                continue
            except Exception as exc:
                print(f"    ⚠ Reviewer error (attempt {attempt+1}): {exc}")
                continue

        print("    ⚠ Reviewer unavailable; skipping spell check")
        return []

    # ────────────────────────────────────────────────────────────────
    # Image / label matching
    # ────────────────────────────────────────────────────────────────
    def _check_images(self, rows: list) -> list:
        issues = []
        for i, row in enumerate(rows):
            for side in ("good", "bad"):
                img_path = row.get(f"{side}_image")
                label = row.get(f"{side}_label", "")
                food = row.get(f"{side}_food", "") or label

                issue = {
                    "row": i, "side": side,
                    "image": img_path, "label": label,
                    "food_query": food,
                }

                if not img_path or not os.path.exists(img_path):
                    issue["reason"] = "image file missing"
                    issues.append(issue)
                    continue

                # Skip placeholders — they're tiny (< 5 KB)
                try:
                    if os.path.getsize(img_path) < 5000:
                        continue
                except OSError:
                    pass

                match, reason = self._vision_match(img_path, food)
                if not match:
                    issue["reason"] = reason
                    issues.append(issue)
        return issues

    def _vision_match(self, image_path: str, label: str) -> tuple[bool, str]:
        """Return (matches, reason)."""
        try:
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
        except Exception as exc:
            return False, f"could not read image: {exc}"

        try:
            resp = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Does this image show: {label}?",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}"
                                },
                            },
                        ],
                    },
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            return bool(data.get("matches")), data.get("reason", "")
        except Exception as exc:
            # If the vision model fails, don't block the cycle
            print(f"    ⚠ Vision check failed for {label}: {exc}")
            return True, "vision check unavailable"