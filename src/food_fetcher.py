import os
import time
import hashlib
import random
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

load_dotenv()


class FoodFetcher:
    """
    Fetch and cache food photos.
    Tries multiple Pixabay keys (rotation on 429), then falls back to
    Openverse, then Wikimedia Commons, then a local placeholder.
    """

    PIXABAY_API = "https://pixabay.com/api/"
    OPENVERSE_API = "https://api.openverse.engineering/v1/images/"
    WIKI_API = "https://commons.wikimedia.org/w/api.php"

    def __init__(self, cache_dir="output/food_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # Load multiple Pixabay keys
        keys_env = os.environ.get("PIXABAY_API_KEYS", "").strip()
        if not keys_env:
            # Back-compat with old single key
            single = os.environ.get("PIXABAY_API_KEY", "").strip()
            keys_env = single

        self.pixabay_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        if not self.pixabay_keys:
            print("[FoodFetcher] No Pixabay keys — will use fallback sources only")

        # Rotates on each Pixabay call
        self._key_index = 0

        # Rotates on each Openverse/Wikimedia call
        self._user_agent = "shorts-agent/1.0 (contact: your@email.com)"

        print(f"[FoodFetcher] Loaded {len(self.pixabay_keys)} Pixabay key(s)")

    # ────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────
    def fetch(self, food_description: str) -> str:
        path = self._filename(food_description)
        if os.path.exists(path) and os.path.getsize(path) > 5000:
            return path

        query = self._build_query(food_description)

        # Try every source with every candidate URL
        sources = [
            ("Wikimedia", self._try_wikimedia),
            ("Pixabay", self._try_pixabay),
        ]
        for name, fn in sources:
            url = fn(query)
            if not url:
                continue
            print(f"    → trying {name}")
            if self._download_image(url, path):
                print(f"    ✓ Image ({name}): {food_description}")
                return path

        return self._placeholder(food_description, path)

    # ────────────────────────────────────────────────────────────────
    # Source 1: Pixabay with key rotation
    # ────────────────────────────────────────────────────────────────
    def _try_pixabay(self, query: str) -> str | None:
        if not self.pixabay_keys:
            return None

        # Try up to len(keys) keys; each key gets 1 attempt
        for attempt in range(len(self.pixabay_keys)):
            key = self.pixabay_keys[self._key_index % len(self.pixabay_keys)]
            self._key_index += 1

            params = {
                "key": key,
                "q": query,
                "image_type": "photo",
                "orientation": "horizontal",
                "category": "food",  # ← only food category
                "safesearch": "true",
                "per_page": 10,  # ← fetch more, pick better
                "order": "popular",
                "min_width": 400,  # ← avoid tiny images
                "min_height": 400,
                "editors_choice": "true",  # ← only editor-curated, higher quality
            }

            try:
                resp = requests.get(self.PIXABAY_API, params=params, timeout=15)
                if resp.status_code == 429:
                    print(f"    ⏳ Pixabay key {self._key_index % len(self.pixabay_keys)} rate-limited")
                    time.sleep(0.8)
                    continue
                data = resp.json()
                hits = data.get("hits", [])
                if not hits:
                    params.pop("editors_choice", None)  # retry without the filter
                    resp = requests.get(self.PIXABAY_API, params=params, timeout=15)
                    hits = resp.json().get("hits", [])
                hit = sorted(
                    hits,
                    key=lambda h: h.get("imageWidth", 0) * h.get("imageHeight", 0),
                    reverse=True,
                )[0]
                url = (
                        hit.get("webformatURL")  # ~640px — perfect for our display
                        or hit.get("previewURL")
                        or hit.get("largeImageURL")  # ~1280px — CDN throttles this hard
                )
                if url:
                    return url
            except Exception as exc:
                print(f"    ⚠ Pixabay error: {exc}")
                continue

        return None

    # ────────────────────────────────────────────────────────────────
    # Source 2: Openverse (no API key needed)
    # ────────────────────────────────────────────────────────────────
    def _try_openverse(self, query: str) -> str | None:
        params = {
            "q": query,
            "license_type": "commercial",
            "page_size": 5,
            "mature": "false",
        }
        headers = {"User-Agent": self._user_agent}

        for attempt in range(2):
            try:
                resp = requests.get(
                    self.OPENVERSE_API, params=params,
                    headers=headers, timeout=15,
                )
                if resp.status_code == 429:
                    print("    ⏳ Openverse rate-limited")
                    time.sleep(1.5)
                    continue
                resp.raise_for_status()
                results = resp.json().get("results", [])
                for r in results:
                    url = r.get("url")
                    if url:
                        return url
            except Exception as exc:
                print(f"    ⚠ Openverse error: {exc}")
            break
        return None

    # ────────────────────────────────────────────────────────────────
    # Source 3: Wikimedia Commons (no API key needed)
    # ────────────────────────────────────────────────────────────────
    def _try_wikimedia(self, query: str) -> str | None:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",       # File namespace
            "gsrlimit": "5",
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": "640",
        }
        headers = {"User-Agent": self._user_agent}

        try:
            resp = requests.get(
                self.WIKI_API, params=params,
                headers=headers, timeout=15,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            for page in pages.values():
                infos = page.get("imageinfo", [])
                if infos:
                    url = infos[0].get("thumburl") or infos[0].get("url")
                    if url:
                        return url
        except Exception as exc:
            print(f"    ⚠ Wikimedia error: {exc}")
        return None

    # ────────────────────────────────────────────────────────────────
    # Download + retry
    # ────────────────────────────────────────────────────────────────
    def _download_image(self, url: str, path: str, max_tries: int = 4) -> bool:
        """Returns True on success, False on failure (never raises)."""
        for attempt in range(max_tries):
            try:
                resp = requests.get(
                    url, timeout=30,
                    headers={"User-Agent": self._user_agent},
                )
                if resp.status_code == 429:
                    wait = 1.5 * (attempt + 1)
                    print(f"    ⏳ CDN 429, waiting {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                if len(resp.content) < 5000:
                    return False
                with open(path, "wb") as f:
                    f.write(resp.content)
                return True
            except Exception as exc:
                print(f"    ⚠ {exc}")
                time.sleep(1.5 * (attempt + 1))
        return False

    # ────────────────────────────────────────────────────────────────
    # Placeholder (never crashes the cycle)
    # ────────────────────────────────────────────────────────────────
    def _placeholder(self, food_description: str, path: str) -> str:
        """Make a colorful placeholder so missing images are obvious."""
        from PIL import Image, ImageDraw, ImageFont

        W, H = 512, 512
        img = Image.new("RGB", (W, H), color=(255, 240, 200))  # warm yellow
        draw = ImageDraw.Draw(img)

        # Draw a border
        draw.rectangle([6, 6, W - 6, H - 6], outline=(200, 130, 20), width=6)

        # Wrap text
        words = food_description.split()
        lines, line = [], ""
        for w in words:
            candidate = (line + " " + w).strip()
            if len(candidate) > 22 and line:
                lines.append(line)
                line = w
            else:
                line = candidate
        if line:
            lines.append(line)

        # Try to load a font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 34)
        except Exception:
            font = ImageFont.load_default()

        # Center the text
        y = H // 2 - (len(lines) * 20)
        for ln in lines[:4]:
            bbox = draw.textbbox((0, 0), ln, font=font)
            w = bbox[2] - bbox[0]
            draw.text(((W - w) // 2, y), ln, fill=(120, 60, 10), font=font)
            y += 40

        # Save as a tiny file so it's never treated as valid cache
        img.save(path, "JPEG", quality=40, optimize=True)
        # Force size below the 5000-byte cache threshold
        if os.path.getsize(path) >= 5000:
            # Re-save at much lower quality if still too big
            img.save(path, "JPEG", quality=20)
        print(f"    ⚠ Placeholder: {food_description}")
        return path
    # ────────────────────────────────────────────────────────────────
    # Utilities
    # ────────────────────────────────────────────────────────────────
    def _filename(self, description: str) -> str:
        key = hashlib.sha256(
            description.strip().lower().encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{key}.jpg")

    @staticmethod
    def _build_query(description: str) -> str:
        d = description.lower().strip()
        # Common food-photo searches that work well on Pixabay
        replacements = {
            # Roti family
            "healthy roti": "whole wheat chapati",
            "millet roti": "bajra roti millet",
            "plain roti": "chapati roti",
            "white roti": "plain chapati",
            "oil roti": "paratha oil",
            # Paratha
            "healthy paratha": "whole wheat paratha",
            "oil paratha": "fried paratha",
            "stuffed paratha": "aloo paratha",
            # Rice
            "rice": "cooked white rice bowl",
            "brown rice": "brown rice bowl",
            "rice with dal": "dal rice indian",
            # Dal
            "dal": "dal curry indian",
            "spinach dal": "palak dal",
            # Bread
            "white bread": "white bread slices",
            "bread jam": "bread with jam",
            "whole wheat bread": "brown bread loaf",
            # Snacks
            "samosa": "samosa fried",
            "pakora": "pakora indian snack",
            "biscuits": "cookies biscuits",
            "chips": "potato chips",
            "namkeen": "indian namkeen snack",
            # Drinks
            "buttermilk": "buttermilk glass",
            "soft drink": "cola glass soda",
            "tea": "indian chai tea",
            "coffee": "black coffee cup",
            "water": "glass of water",
            # Produce
            "banana": "banana fruit",
            "apple": "red apple fruit",
            "spinach": "fresh spinach leaves",
            "tomato": "ripe tomatoes",
            "carrot": "fresh carrots",
            # Meals
            "healthy meal": "indian thali balanced",
            "balanced meal": "indian thali vegetables",
            "salad": "fresh vegetable salad",
        }
        # Exact match first
        if d in replacements:
            return replacements[d]
        # Then try substring matches
        for key, val in replacements.items():
            if key in d:
                return val
        # Fallback: strip filler words
        fillers = ["healthy", "unhealthy", "good", "bad", "fresh", "the", "a", "an"]
        words = [w for w in d.split() if w not in fillers]
        return " ".join(words) if words else "indian food"

    def clear_cache(self, food_description: str):
        path = self._filename(food_description)
        if os.path.exists(path):
            os.remove(path)
            print(f"    ↻ Cleared cache for: {food_description}")