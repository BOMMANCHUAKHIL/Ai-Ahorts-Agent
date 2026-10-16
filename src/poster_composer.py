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
        """Backward-compatible: returns only the PNG path."""
        png, _, _ = self.compose_with_meta(english_concept, info_hint)
        return png

    def compose_with_meta(self, english_concept: str, info_hint: str = ""):
        """Returns (poster_png, content_dict, rows_list)."""
        content = self.generator.get_content(english_concept, info_hint)

        rows = []
        total = len(content["rows"])
        for i, r in enumerate(content["rows"]):
            good_img = self.fetcher.fetch(r["good_food"])
            bad_img = self.fetcher.fetch(r["bad_food"])
            rows.append({
                "time": r["time"],
                "good_image": good_img,
                "bad_image": bad_img,
                "good_label": r["good_label"],
                "bad_label": r["bad_label"],
                "good_food": r["good_food"],
                "bad_food": r["bad_food"],
            })
            if i < total - 1:
                time.sleep(2.5)   # was 0.8 — gentler on Pixabay

        context = {
            "telugu_title": content["telugu_title"],
            "telugu_subtitle": content["telugu_subtitle"],
            "rows": rows,
            "tips": content["tips"][:4],
            "footer": content["footer"],
        }
        png = self.renderer.render(context)
        return png, content, rows