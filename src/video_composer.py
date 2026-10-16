import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

import os
import time

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
)


class VideoComposer:
    """Creates a vertical YouTube Short from a poster with motion, text and music."""

    def __init__(self, config: dict):
        self.duration = config.get("video_duration", 15)
        self.width = 1080
        self.height = 1920

        self.output_dir = "output/videos"
        os.makedirs(self.output_dir, exist_ok=True)

    def compose(self, poster_png: str, music_path: str) -> str:
        """Use the original poster and music inputs, then apply video effects."""

        if not os.path.exists(poster_png):
            raise FileNotFoundError(
                f"Poster image not found: {poster_png}"
            )

        audio = None
        video = None
        base_clip = None

        try:
            # 1. Load the original poster.
            base_clip = ImageClip(poster_png).set_duration(
                self.duration
            )

            # 2. Resize and crop to fill the vertical 1080x1920 frame.
            base_clip = base_clip.resize(height=self.height)

            if base_clip.w > self.width:
                base_clip = base_clip.crop(
                    x_center=base_clip.w / 2,
                    width=self.width,
                )
            else:
                base_clip = base_clip.resize(
                    width=self.width
                )

            base_clip = base_clip.set_duration(self.duration)

            # 3. Apply subtle zoom motion.
            # The original poster remains the visual source.
            try:
                zoomed_clip = base_clip.resize(
                    lambda t: 1.0 + 0.03 * t / self.duration
                )
                zoomed_clip = zoomed_clip.set_position("center")
            except Exception as exc:
                print(f"    ⚠ Zoom skipped: {exc}")
                zoomed_clip = base_clip

            # 4. Add text overlays without replacing poster content.
            text_clips = self._texts()

            # 5. Combine the poster and text overlays.
            video = CompositeVideoClip(
                [zoomed_clip] + text_clips,
                size=(self.width, self.height),
            ).set_duration(self.duration)

            # 6. Attach music, if available.
            if music_path and os.path.exists(music_path):
                try:
                    audio = AudioFileClip(music_path)

                    # Trim long audio; loop short music to fill the video.
                    if audio.duration >= self.duration:
                        audio = audio.subclip(0, self.duration)
                    else:
                        from moviepy.editor import afx

                        audio = afx.audio_loop(
                            audio,
                            duration=self.duration,
                        )

                    video = video.set_audio(audio)

                except Exception as exc:
                    print(f"    ⚠ Music skipped: {exc}")

            # 7. Export the finished Short.
            out = os.path.join(
                self.output_dir,
                f"short_{int(time.time())}.mp4",
            )

            video.write_videofile(
                out,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                preset="ultrafast",
                threads=2,
                logger=None,
            )

            print(f"    ✓ Video saved: {out}")
            return out

        finally:
            # Close resources to release memory and file handles.
            if video is not None:
                video.close()

            if base_clip is not None:
                base_clip.close()

            if audio is not None:
                audio.close()

    def _texts(self):
        """Create timed text overlays."""

        clips = []

        try:
            # Opening title: 0–3 seconds
            clips.append(
                TextClip(
                    "Healthy Food Tips",
                    fontsize=70,
                    color="white",
                    stroke_color="black",
                    stroke_width=3,
                    size=(self.width - 100, None),
                    method="caption",
                )
                .set_position(("center", 300))
                .set_start(0)
                .set_duration(min(3, self.duration))
            )

            # Middle message: 7–11 seconds
            if self.duration > 7:
                clips.append(
                    TextClip(
                        "Eat Smart, Stay Healthy!",
                        fontsize=52,
                        color="yellow",
                        stroke_color="black",
                        stroke_width=2,
                        size=(self.width - 100, None),
                        method="caption",
                    )
                    .set_position(("center", 1200))
                    .set_start(7)
                    .set_duration(min(4, self.duration - 7))
                )

            # Call to action: final 4 seconds
            if self.duration > 11:
                clips.append(
                    TextClip(
                        "Follow for more!",
                        fontsize=60,
                        color="white",
                        stroke_color="black",
                        stroke_width=3,
                    )
                    .set_position(("center", 1600))
                    .set_start(11)
                    .set_duration(min(4, self.duration - 11))
                )

        except Exception as exc:
            print(f"    ⚠ Text overlay skipped: {exc}")

        return clips
