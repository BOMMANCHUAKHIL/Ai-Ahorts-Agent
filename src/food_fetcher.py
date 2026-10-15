import os
import re
import hashlib

import torch
from PIL import Image
from diffusers import StableDiffusionXLPipeline


class FoodFetcher:
    """Generate and cache food photos using local SDXL."""

    def __init__(self, cache_dir="output/food_cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if self.device == "cuda" else torch.float32

        print(f"Loading local SDXL for food photos on {self.device}...")

        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=dtype,
            use_safetensors=True,
        )

        if self.device == "cuda":
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe.to("cpu")

        print("Local food image generator ready.")

    def _filename(self, description):
        key = hashlib.sha256(
            description.strip().lower().encode("utf-8")
        ).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{key}.jpg")

    def fetch(self, food_description: str) -> str:
        """Return a cached food photo or generate a new one."""

        path = self._filename(food_description)

        if os.path.exists(path) and os.path.getsize(path) > 5000:
            return path

        prompt = (
            f"Photorealistic food photography of {food_description}. "
            "Show the exact food described, recognizable ingredients, "
            "realistic Indian food presentation when appropriate, "
            "natural food textures, appetizing lighting, "
            "single clear subject, centered composition, "
            "clean light background, sharp focus, square photograph. "
            "No text, no labels, no watermark, no collage."
        )

        try:
            result = self.pipe(
                prompt=prompt,
                negative_prompt=(
                    "wrong food, unrelated dish, incorrect ingredients, "
                    "multiple unrelated dishes, illustration, cartoon, "
                    "blurry, distorted, text, watermark, logo"
                ),
                width=512,
                height=512,
                num_inference_steps=20,
                guidance_scale=6.0,
            )

            image = result.images[0].convert("RGB")
            image.save(path, "JPEG", quality=92)
            print(f"    ✓ Generated food photo: {food_description}")
            return path

        except Exception as exc:
            print(
                f"    ✗ Local generation failed for "
                f"'{food_description}': {exc}"
            )
            raise RuntimeError(
                f"Could not generate food photo: {food_description}"
            ) from exc
