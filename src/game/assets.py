import pygame
import os
pygame.font.init()

def load_image(path):
    full_path = os.path.join(os.path.dirname(__file__), '..', path)
    if not os.path.exists(full_path):
        print(f"[ASSET] Image not found: {full_path}")
        return None
    try:
        img = pygame.image.load(full_path).convert_alpha()
        print(f"[ASSET] Loaded image: {full_path}")
        return img
    except Exception as e:
        print(f"[ASSET] Failed to load image: {full_path} ({e})")
        return None

def load_font(path, size):
    full_path = os.path.join(os.path.dirname(__file__), '..', path)
    if not os.path.exists(full_path):
        print(f"[ASSET] Font not found: {full_path}")
        return pygame.font.SysFont(None, size)
    try:
        font = pygame.font.Font(full_path, size)
        print(f"[ASSET] Loaded font: {full_path}")
        return font
    except Exception as e:
        print(f"[ASSET] Failed to load font: {full_path} ({e})")
        return pygame.font.SysFont(None, size)

_image_cache = {}
def get_image(name, path):
    if name not in _image_cache:
        _image_cache[name] = load_image(path)
    return _image_cache[name]

# Usage example (call after display is initialized):
# hotbar_selected = get_image("hotbar_selected", "game/assets/sprites/ui/hotbar/selected.png")

# Preload fonts
FONTS = {
    "hud": load_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 48),
    "overlay": load_font("game/assets/fonts/CinzelDecorative-Black.ttf", 18),
    "bar": load_font("game/assets/fonts/CinzelDecorative-Black.ttf", 24),
    # Add more font sizes/types as needed
}

# Dynamic font cache for animated text sizes
_font_cache = {}
def get_font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = load_font(path, size)
    return _font_cache[key]
