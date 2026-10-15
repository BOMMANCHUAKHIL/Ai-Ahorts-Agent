import time
from src.telugu_generator import TeluguGenerator
from src.food_fetcher import FoodFetcher
from src.html_renderer import HTMLRenderer


class PosterComposer:
    def __init__(self):
        self.generator = TeluguGenerator()
        self.fetcher = FoodFetcher()
        self.renderer = HTMLRenderer()

    def compose(self, english_concept: str, info_hint: str = "") -> str:
        content = self.generator.get_content(english_concept, info_hint)

        rows = []
        total = len(content["rows"])
        for i, r in enumerate(content["rows"]):
            good_img = self.fetcher.fetch(r["good_food"])
            bad_img  = self.fetcher.fetch(r["bad_food"])
            rows.append({
                "time": r["time"],
                "good_image": good_img,
                "bad_image": bad_img,
                "good_label": r["good_label"],
                "bad_label": r["bad_label"],
            })
            if i < total - 1:
                time.sleep(0.8)      # be gentle to APIs

        context = {
            "telugu_title": content["telugu_title"],
            "telugu_subtitle": content["telugu_subtitle"],
            "rows": rows,
            "tips": content["tips"][:4],
            "footer": content["footer"],
        }
        return self.renderer.render(context)