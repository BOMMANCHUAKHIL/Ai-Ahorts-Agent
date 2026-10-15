import json
import os
import random


class PromptEngine:
    """Picks the next unused concept, builds a full prompt from a template,
    and persists history to output/prompt_history.json."""

    def __init__(self, prompts_file: str = "prompts.json"):
        with open(prompts_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.topic = data["topic"]
        self.style = data.get("image_style", "")
        self.template = data["prompt_template"]
        self.concepts = data["concepts"]

        self.history_file = "output/prompt_history.json"
        self.used_indices = self._load_history()

    def _load_history(self) -> list:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("used_indices", [])
            except Exception:
                return []
        return []

    def _save_history(self):
        os.makedirs("output", exist_ok=True)
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(
                {"used_indices": self.used_indices},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def next_prompt(self) -> dict:
        """Return {prompt, info, concept, index}."""
        # Available indices = not yet used
        available = [
            i for i in range(len(self.concepts))
            if i not in self.used_indices
        ]

        # Reset cycle when exhausted
        if not available:
            print("    → All concepts used. Resetting cycle.")
            self.used_indices = []
            available = list(range(len(self.concepts)))

        idx = random.choice(available)
        self.used_indices.append(idx)
        self._save_history()

        entry = self.concepts[idx]
        concept = entry["label"]
        info = entry.get("info", self.topic)

        # Build the full prompt from the template
        prompt = self.template.format(
            topic=self.topic,
            concept=concept,
            style=self.style,
        )


        print(f"    → Concept #{idx + 1}/{len(self.concepts)}: {concept}")

        return {
            "prompt": prompt,
            "concept": concept,
            "info": info,
            "index": idx,
        }