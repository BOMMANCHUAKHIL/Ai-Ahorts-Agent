from src.telugu_generator import TeluguGenerator
from src.food_fetcher import FoodFetcher
from src.html_renderer import HTMLRenderer


class PosterComposer:
    """Orchestrates: concept → LLM Telugu content → food photos → PNG."""

    def __init__(self):
        self.generator = TeluguGenerator()
        self.fetcher = FoodFetcher()
        self.renderer = HTMLRenderer()

    def compose(self, english_concept: str, info_hint: str = "") -> str:
        """Build a Telugu nutrition poster. Returns path to PNG."""

        # 1. Get Telugu content (from cache or Groq)
        content = self.generator.get_content(english_concept, info_hint)

        # 2. Fetch all food photos
        rows = content["rows"]
        print(f"    → Fetching {len(rows) * 2} food photos...")
        rows_rendered = []
        for i, row in enumerate(rows):
            print(f"       Row {i + 1}/{len(rows)}: "
                  f"{row['good_label']} vs {row['bad_label']}")

            try:
                good_img = self.fetcher.fetch(row["good_food"])
            except Exception as e:
                print(f"         ✗ good image failed: {e}")
                good_img = self.fetcher._placeholder()

            try:
                bad_img = self.fetcher.fetch(row["bad_food"])
            except Exception as e:
                print(f"         ✗ bad image failed: {e}")
                bad_img = self.fetcher._placeholder()

            rows_rendered.append({
                "time": row["time"],
                "good_image": good_img,
                "bad_image": bad_img,
                "good_label": row["good_label"],
                "bad_label": row["bad_label"],
            })

        # 3. Build template context
        context = {
            "telugu_title": content["telugu_title"],
            "telugu_subtitle": content["telugu_subtitle"],
            "rows": rows_rendered,
            "tips": content["tips"],
            "footer": content["footer"],
        }

        # 4. Render HTML → PNG
        print(f"    → Rendering HTML → PNG...")
        png_path = self.renderer.render(context)
        print(f"    ✓ Poster: {png_path}")

        return png_path