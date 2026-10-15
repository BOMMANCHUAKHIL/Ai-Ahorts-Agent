import json
import os
from datetime import datetime

from src.prompt_engine import PromptEngine
from src.poster_composer import PosterComposer
from src.video_composer import VideoComposer
from src.youtube_uploader import YouTubeUploader


class ShortsOrchestrator:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.prompt_engine = PromptEngine(
            self.config.get("prompts_file", "prompts.json")
        )
        self.poster_composer = PosterComposer()
        self.video_comp = VideoComposer(self.config)
        self.uploader = YouTubeUploader()

        self.video_counter = 0
        self.music_index = 0
        self.state_path = "output/state.json"
        self._load_state()

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

        # Try each track once; skip missing files
        for _ in range(len(tracks)):
            track = tracks[self.music_index % len(tracks)]
            self.music_index += 1
            if os.path.exists(track):
                return track
        return None

    def run_cycle(self):
        self.video_counter += 1
        print(f"\n{'='*50}")
        print(f"Cycle #{self.video_counter} — {datetime.now().isoformat()}")
        print(f"{'='*50}")

        # 1. Pick the next unused concept
        print("\n[1/4] Selecting concept...")
        entry = self.prompt_engine.next_prompt()
        english_concept = entry["concept"]
        info_hint = entry.get("info", "")

        # 2. Build the poster
        print("\n[2/4] Building Telugu poster...")
        poster_png = self.poster_composer.compose(
            english_concept=english_concept,
            info_hint=info_hint,
        )

        # 3. Compose video with the next audio
        print("\n[3/4] Composing video...")
        music = self._next_music()
        print(f"    → Using music: {music}")
        video_path = self.video_comp.compose(
            poster_png=poster_png,
            music_path=music,
        )
        print(f"    ✓ Video: {video_path}")

        # 4. Upload
        print("\n[4/4] Uploading to YouTube...")
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
            # Save state so the next run advances to a different song
            self._save_state()
            return False

        self._save_state()
        print(f"\n✓ Done. Video ID: {vid}")
        return True