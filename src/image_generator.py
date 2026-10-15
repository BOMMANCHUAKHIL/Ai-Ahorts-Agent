
import os
import time
from typing import Optional

import torch
from diffusers import StableDiffusionXLPipeline


class ImageGenerator:
    """Generate images locally using Stable Diffusion XL."""

    def __init__(self, config: dict):
        self.output_dir = "output/images"
        os.makedirs(self.output_dir, exist_ok=True)

        self.width = 768
        self.height = 1344
        self.steps = 25

        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"Loading local SDXL model on {self.device}...")

        dtype = (
            torch.float16
            if self.device == "cuda"
            else torch.float32
        )

        self.pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=dtype,
            use_safetensors=True,
        )

        if self.device == "cuda":
            # Reduces GPU memory requirements.
            self.pipe.enable_model_cpu_offload()
        else:
            self.pipe.to("cpu")

        self.style = config.get("image_style", "")

        print("Local SDXL model loaded successfully.")

    def generate(self, prompt: str) -> Optional[str]:
        """Generate and save a vertical image."""

        try:
            full_prompt = (
                f"{prompt}. "
                "Vertical 9:16 composition. "
                "Photorealistic Indian food photography. "
                "Authentic South Indian ingredients. "
                "Clean visual composition. "
                "No text, no letters, no watermark, no logo. "
                "Leave clear space for a poster layout."
            )

            filename = f"nutrition_{int(time.time())}.png"
            path = os.path.join(self.output_dir, filename)

            result = self.pipe(
                prompt=full_prompt,
                negative_prompt=(
                    "gibberish text, misspelled letters, watermark, "
                    "logo, blurry food, deformed objects, "
                    "duplicate dishes, cluttered composition"
                ),
                width=self.width,
                height=self.height,
                num_inference_steps=self.steps,
                guidance_scale=7.0,
            )

            result.images[0].save(path)

            print(f"Image saved: {path}")
            return path

        except Exception as exc:
            print(f"Local image generation failed: {exc}")
            return None
