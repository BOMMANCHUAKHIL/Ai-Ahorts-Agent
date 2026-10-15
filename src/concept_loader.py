import json
import os


class ConceptLoader:
    """Loads concepts from concepts_db.json."""

    def __init__(self, db_path: str = "concepts_db.json"):
        if not os.path.exists(db_path):
            raise FileNotFoundError(
                f"Concept database not found: {db_path}\n"
                f"Create concepts_db.json in the project root."
            )
        with open(db_path, "r", encoding="utf-8") as f:
            self.db = json.load(f)
        self.concepts = self.db["concepts"]

    def get(self, concept_id: str) -> dict:
        for c in self.concepts:
            if c["id"] == concept_id:
                return c
        raise KeyError(f"Concept not found: {concept_id}")

    def all_ids(self) -> list:
        return [c["id"] for c in self.concepts]