import os
import time
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright


class HTMLRenderer:
    """Renders the poster HTML template to a PNG using headless Chromium."""

    def __init__(self, template_dir: str = "templates",
                 output_dir: str = "output/posters"):
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
        )
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def render(self, context: dict) -> str:
        # 1. Render Jinja2 template → HTML string
        template = self.env.get_template("poster.html")

        # Convert all image paths to file:// URLs for Chromium
        for row in context["rows"]:
            row["good_image"] = self._to_file_url(row["good_image"])
            row["bad_image"] = self._to_file_url(row["bad_image"])

        # Absolute font directory path
        font_dir = os.path.abspath("assets/fonts").replace("\\", "/")
        context["font_dir"] = font_dir

        html = template.render(**context)

        # Write HTML to a temp file so Chromium can load it
        tmp_html = os.path.abspath(
            os.path.join(self.output_dir, "_tmp_render.html")
        )
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html)

        # 2. Render HTML → PNG using Playwright
        out_png = os.path.abspath(
            os.path.join(self.output_dir, f"poster_{int(time.time())}.png")
        )

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.goto(f"file:///{tmp_html.replace(chr(92), '/')}")
            page.wait_for_timeout(1500)  # wait for fonts + images
            page.screenshot(path=out_png, full_page=False)
            browser.close()

        return out_png

    def _to_file_url(self, path: str) -> str:
        abspath = os.path.abspath(path).replace("\\", "/")
        return f"file:///{abspath}"