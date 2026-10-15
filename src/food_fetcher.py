import os
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()


class FoodFetcher:
    """Fetch and cache food photos using the Pixabay API."""

    BASE_URL = "https://pixabay.com/api/"

    def __init__(self, cache_dir="output/food_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.api_key = os.environ.get("PIXABAY_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "PIXABAY_API_KEY not set. Add it to your .env file:\n"
                "PIXABAY_API_KEY=your_key_here"
            )

    def _filename(self, description: str) -> str:
        key = hashlib.sha256(
            description.strip().lower().encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{key}.jpg")

    def fetch(self, food_description: str) -> str:
        """Return a cached food photo or download a new one from Pixabay."""
        path = self._filename(food_description)

        # Reuse cached image
        if os.path.exists(path) and os.path.getsize(path) > 5000:
            return path

        # Build a good search query
        query = self._build_query(food_description)

        params = {
            "key": self.api_key,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "category": "food",
            "safesearch": "true",
            "per_page": 5,
            "order": "popular",
        }

        try:
            resp = requests.get(self.BASE_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise RuntimeError(
                f"Pixabay request failed for '{food_description}': {exc}"
            ) from exc

        hits = data.get("hits", [])
        if not hits:
            # Retry with a simpler query
            simple_query = food_description.split()[0]
            params["q"] = simple_query
            resp = requests.get(self.BASE_URL, params=params, timeout=20)
            hits = resp.json().get("hits", [])

        if not hits:
            raise RuntimeError(
                f"No Pixabay results for: {food_description}"
            )

        # Pick the largest / best image
        hit = sorted(
            hits,
            key=lambda h: h.get("imageWidth", 0) * h.get("imageHeight", 0),
            reverse=True,
        )[0]

        image_url = (
            hit.get("largeImageURL")
            or hit.get("webformatURL")
            or hit.get("previewURL")
        )

        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()

        with open(path, "wb") as f:
            f.write(img_resp.content)

        print(f"    ✓ Pixabay image: {food_description} → {hit.get('tags')}")
        return path

    @staticmethod
    def _build_query(description: str) -> str:
        """Make the description search-friendly for Pixabay."""
        d = description.lower().strip()
        # Pixabay works better with short, keyword-style queries
        replacements = {
            "boiled eggs": "boiled eggs",
            "idli with sambar": "idli sambar",
            "pesarattu with chutney": "dosa chutney",
            "upma with vegetables": "upma",
            "white bread toast with jam": "white bread jam toast",
            "sugary cereal": "sweet cereal bowl",
            "fried puri": "puri fried",
            "buttermilk": "buttermilk glass",
            "soft drink": "soda glass",
            "rice with dal and vegetables": "indian thali rice dal",
            "fast food burger": "burger fast food",
            "banana and apple": "banana apple fruit",
            "biscuits": "cookies biscuits",
        }
        return replacements.get(d, d)