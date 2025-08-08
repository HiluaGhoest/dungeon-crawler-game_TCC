
import pygame
from game.assets import get_image, get_font, load_audio


# Initialize mixer if not already initialized
if not pygame.mixer.get_init():
    pygame.mixer.init()

hover_sound = load_audio("game/sounds/effects/button_hover.wav")

BTN_COLOR = (40, 40, 40)
HOVER_COLOR = (80, 80, 80)
FONT_PATH = "game/assets/fonts/CinzelDecorative-Regular.ttf"
FONT = get_font(FONT_PATH, 48)
TEXT_COLOR = (255, 255, 255)

def blur_surface(surface, iterations=3):
    for i in range(iterations):
        surface = pygame.transform.smoothscale(surface, (surface.get_width()//2, surface.get_height()//2))
        surface = pygame.transform.smoothscale(surface, (surface.get_width()*2, surface.get_height()*2))
    return surface


def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)


class Button:
    def __init__(self, text, rect, action):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.action = action
        self.hover_progress = 0  # from 0 to 1 for smooth scaling
        # Load button sprite after display is initialized
        self.button_sprite = get_image("button", "game/assets/sprites/ui/button.png")
        self._was_selected = False  # Track previous selected state for sound


    def draw(self, surface, mouse_pos, selected=False):
        # Play hover/select sound when selected changes from False to True
        if selected and not self._was_selected and hover_sound:
            try:
                hover_sound.play()
            except Exception:
                pass
        self._was_selected = selected

        # Animate hover progress
        target = 1 if selected else 0
        self.hover_progress += (target - self.hover_progress) * 0.1
        eased = ease_out_cubic(self.hover_progress)

        # Scale and draw rect (no bg)
        scale = 1.0 + 0.1 * eased
        draw_rect = self.rect.inflate(
            int(self.rect.width * (scale - 1)),
            int(self.rect.height * (scale - 1))
        )

        # --- Animated text size ---
        text_scale = 1.0 + 0.2 * eased
        base_font_size = 32
        font_size = int(base_font_size * text_scale)
        dynamic_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", font_size)
        
        # Render text first to get its dimensions
        text_surf = dynamic_font.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=draw_rect.center)

        # Draw side sprites (only if selected)
        if selected and self.button_sprite is not None:
            sprite_scale = 0.4
            sprite_w, sprite_h = self.button_sprite.get_size()
            scaled_w = int(sprite_w * sprite_scale)
            scaled_h = int(sprite_h * sprite_scale)
            scaled_sprite = pygame.transform.smoothscale(self.button_sprite, (scaled_w, scaled_h))
            flipped_sprite = pygame.transform.flip(scaled_sprite, True, False)
            sprite_y = draw_rect.centery - scaled_h // 2
            # Calculate offset based on text width (plus some padding)
            text_width = text_rect.width
            base_offset = text_width * 0.05  # 5% of text width as base offset
            max_offset = text_width * 0.1  # Maximum additional offset when fully selected
            # Apply easing to the additional offset
            dynamic_offset = base_offset + (max_offset * eased)
            # Left sprite moves left (negative X direction)
            surface.blit(flipped_sprite, (text_rect.left - scaled_w - int(dynamic_offset), sprite_y))
            # Right sprite moves right (positive X direction)
            surface.blit(scaled_sprite, (text_rect.right + int(dynamic_offset), sprite_y))

        # Draw text
        surface.blit(text_surf, text_rect)
        # --- Glowing underline when selected ---
        if selected:
            # 1. Render the text again (for the glow)
            underline_text = dynamic_font.render(self.text, True, (255, 255, 255))  # Purple text
            underline_rect = underline_text.get_rect(center=draw_rect.center)
            
            # 2. Create a glow surface (same size as text)
            glow_surf = pygame.Surface(underline_text.get_size(), pygame.SRCALPHA)
            glow_surf.blit(underline_text, (0, 0))
            
            # 3. Apply color overlay (like the title)
            glow_color = pygame.Surface(underline_text.get_size(), pygame.SRCALPHA)
            glow_color.fill((255, 255, 255, 255))  # Semi-transparent white
            glow_surf.blit(glow_color, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            # 4. Blur the glow surface (stronger blur = more spread)
            glow_surf = blur_surface(glow_surf, iterations=2)
            
            # 5. Position it below the text (adjust Y offset)
            glow_x = text_rect.x
            glow_y = text_rect.y
            
            # 6. Draw the glow
            surface.blit(glow_surf, (glow_x, glow_y))