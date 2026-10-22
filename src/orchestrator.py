import json
import os
from datetime import datetime

from src.prompt_engine import PromptEngine
from src.poster_composer import PosterComposer
from src.video_composer import VideoComposer
from src.youtube_uploader import YouTubeUploader
from src.reviewer_agent import ReviewerAgent


class ShortsOrchestrator:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.prompt_engine = PromptEngine(
            self.config.get("prompts_file", "prompts.json")
        )
        self.reviewer = ReviewerAgent(strict_images=False)
        self.poster_composer = PosterComposer()
        self.video_comp = VideoComposer(self.config)
        self.uploader = YouTubeUploader()

        self.video_counter = 0
        self.music_index = 0
        self.state_path = "output/state.json"
        self._load_state()

    # ────────────────────────────────────────────────────────────────
    def _load_state(self):
        if os.path.exists(self.state_path):
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.video_counter = data.get("counter", 0)
                self.music_index = data.get("music_index", 0)

    def _save_state(self):
        os.makedirs("output", exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "counter": self.video_counter,
                    "music_index": self.music_index,
                },
                f,
                indent=2,
            )

    def _next_music(self):
        tracks = self.config.get("music_rotation", [])
        if not tracks:
            return None
        for _ in range(len(tracks)):
            track = tracks[self.music_index % len(tracks)]
            self.music_index += 1
            if os.path.exists(track):
                return track
        return None

    @staticmethod
    def _apply_text_fixes(content: dict, issues: list) -> dict:
        """Apply each suggestion back into the content dict."""
        for issue in issues:
            field = issue["field"]
            suggestion = issue.get("suggestion")
            if not suggestion:
                continue
            parts = field.replace("[", ".").replace("]", "").split(".")
            target = content
            for part in parts[:-1]:
                if part.isdigit():
                    target = target[int(part)]
                else:
                    target = target[part]
            target[parts[-1]] = suggestion
        return content

    # ────────────────────────────────────────────────────────────────
    def run_cycle(self):
        self.video_counter += 1
        print(f"\n{'='*50}")
        print(f"Cycle #{self.video_counter} — {datetime.now().isoformat()}")
        print(f"{'='*50}")

        # 1. Concept
        print("\n[1/5] Selecting concept...")
        entry = self.prompt_engine.next_prompt()
        english_concept = entry["concept"]
        info_hint = entry.get("info", "")

        # 2. Poster + metadata (content, rows)
        print("\n[2/5] Building Telugu poster...")
        try:
            poster_png, content, rows = self.poster_composer.compose_with_meta(
                english_concept=english_concept,
                info_hint=info_hint,
            )
        except Exception as e:
            print(f"    ✗ Poster build failed: {e}")
            self._save_state()  # persists video_counter so next run picks a new concept
            return False

        # 3. Review
        print("\n[3/5] Reviewing poster...")
        review = self.reviewer.check(content, rows)

        if not review["ok"]:
            print("    ✗ Reviewer rejected — attempting one fix pass...")

            if review["text_issues"]:
                content = self._apply_text_fixes(content, review["text_issues"])

            for issue in review["image_issues"]:
                # Don't re-fetch placeholders — they'll stay placeholders
                img_path = issue.get("image", "")
                if img_path and os.path.exists(img_path):
                    try:
                        if os.path.getsize(img_path) < 5000:
                            continue
                    except OSError:
                        pass

                query = issue.get("food_query") or issue.get("label") or ""
                if not query:
                    continue
                self.poster_composer.fetcher.clear_cache(query)
                new_img = self.poster_composer.fetcher.fetch(query)
                rows[issue["row"]][f"{issue['side']}_image"] = new_img

            # Re-render once with fixes applied
            context = {
                "telugu_title": content["telugu_title"],
                "telugu_subtitle": content["telugu_subtitle"],
                "rows": rows,
                "tips": content["tips"][:4],
                "footer": content["footer"],
            }
            poster_png = self.poster_composer.renderer.render(context)

            review2 = self.reviewer.check(content, rows)
            if not review2["ok"]:
                print("    ⚠ Reviewer still flagged issues after fix — continuing anyway")
                for iss in (review2["text_issues"] + review2["image_issues"]):
                    print(f"      - {iss.get('field') or iss.get('label')}: {iss.get('problem') or iss.get('reason')}")
            else:
                print("    ✓ Reviewer approved on second pass")
        else:
            print("    ✓ Reviewer approved")

        # 4. Video
        print("\n[4/5] Composing video...")
        music = self._next_music()
        print(f"    → Using music: {music}")
        video_path = self.video_comp.compose(
            poster_png=poster_png,
            music_path=music,
        )
        print(f"    ✓ Video: {video_path}")

        # 5. Upload
        print("\n[5/5] Uploading to YouTube...")
        cached = self.poster_composer.generator.cache.get(
            english_concept.lower().strip(), {}
        )
        title = cached.get("telugu_title", english_concept.title())

        try:
            vid = self.uploader.upload(
                video_path=video_path,
                title=title,
                description=self.config["video_description"],
                privacy=self.config["privacy_status"],
            )
        except Exception as e:
            print(f"    ✗ Upload failed: {e}")
            self._save_state()
            return False

        self._save_state()
        print(f"\n✓ Done. Video ID: {vid}")
        return True