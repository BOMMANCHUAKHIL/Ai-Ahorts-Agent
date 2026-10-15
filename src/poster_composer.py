import os
from src.telugu_generator import TeluguGenerator
from src.food_fetcher import FoodFetcher
from src.html_renderer import HTMLRenderer


class PosterComposer:
    def __init__(self):
        self.generator = TeluguGenerator()
        self.fetcher = FoodFetcher()
        self.renderer = HTMLRenderer()

    def compose(self, english_concept: str, info_hint: str = "") -> str:
        # 1. Telugu content from Groq
        content = self.generator.get_content(english_concept, info_hint)

        # 2. Fetch images from Pixabay for each row
        rows = []
        for r in content["rows"]:
            good_img = self.fetcher.fetch(r["good_food"])
            bad_img = self.fetcher.fetch(r["bad_food"])
            rows.append({
                "time": r["time"],
                "good_image": good_img,
                "bad_image": bad_img,
                "good_label": r["good_label"],
                "bad_label": r["bad_label"],
            })

        # 3. Render the poster HTML → PNG
        context = {
            "telugu_title": content["telugu_title"],
            "telugu_subtitle": content["telugu_subtitle"],
            "rows": rows,
            "tips": content["tips"][:4],
            "footer": content["footer"],
        }
        return self.renderer.render(context)