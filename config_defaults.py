import os

# Full path to magick.exe — adjust only if Step 1 found a different location
IMAGEMAGICK_PATH = r"C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe"

if os.path.exists(IMAGEMAGICK_PATH):
    os.environ["IMAGEMAGICK_BINARY"] = IMAGEMAGICK_PATH
    print(f"[config] ImageMagick set to: {IMAGEMAGICK_PATH}")
else:
    print(f"[config] WARNING: magick.exe not found at {IMAGEMAGICK_PATH}")