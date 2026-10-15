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
        """Return path to a cached or newly downloaded food photo."""
        path = self._filename(food_description)

        if os.path.exists(path) and os.path.getsize(path) > 5000:
            return path

        query = self._build_query(food_description)

        # Try sources in order. First one that returns a working URL wins.
        image_url = (
            self._try_pixabay(query)
            or self._try_openverse(query)
            or self._try_wikimedia(query)
        )

        if image_url:
            try:
                self._download_image(image_url, path)
                print(f"    ✓ Image: {food_description} ← {image_url[:60]}...")
                return path
            except Exception as exc:
                print(f"    ⚠ Download failed ({exc}); using placeholder")

        # Every online source failed — local placeholder
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
                "category": "food",
                "safesearch": "true",
                "per_page": 5,
                "order": "popular",
            }

            try:
                resp = requests.get(self.PIXABAY_API, params=params, timeout=15)
                if resp.status_code == 429:
                    print(f"    ⏳ Pixabay key {self._key_index % len(self.pixabay_keys)} rate-limited")
                    time.sleep(0.8)
                    continue
                resp.raise_for_status()
                hits = resp.json().get("hits", [])
                if not hits:
                    continue
                hit = sorted(
                    hits,
                    key=lambda h: h.get("imageWidth", 0) * h.get("imageHeight", 0),
                    reverse=True,
                )[0]
                url = (
                    hit.get("webformatURL")
                    or hit.get("previewURL")
                    or hit.get("largeImageURL")
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
    def _download_image(self, url: str, path: str, max_tries: int = 4) -> None:
        last_exc = None
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
                    raise RuntimeError("Downloaded file too small")
                with open(path, "wb") as f:
                    f.write(resp.content)
                return
            except Exception as exc:
                last_exc = exc
                time.sleep(1.5 * (attempt + 1))

        raise RuntimeError(f"Download failed after {max_tries} tries: {last_exc}")

    # ────────────────────────────────────────────────────────────────
    # Placeholder (never crashes the cycle)
    # ────────────────────────────────────────────────────────────────
    def _placeholder(self, food_description: str, path: str) -> str:
        img = Image.new("RGB", (512, 512), color=(230, 245, 230))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        # Wrap text roughly
        words = food_description.split()
        lines, line = [], ""
        for w in words:
            if len(line + " " + w) > 22:
                lines.append(line)
                line = w
            else:
                line = (line + " " + w).strip()
        if line:
            lines.append(line)
        y = 200
        for ln in lines[:5]:
            draw.text((40, y), ln, fill=(40, 80, 40))
            y += 40
        img.save(path, "JPEG", quality=85)
        print(f"    ⚠ Placeholder for: {food_description}")
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
        replacements = {
            "boiled eggs": "boiled eggs",
            "idli with sambar": "idli sambar",
            "pesarattu with chutney": "dosa chutney",
            "upma with vegetables": "upma",
            "white bread toast with jam": "bread jam toast",
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