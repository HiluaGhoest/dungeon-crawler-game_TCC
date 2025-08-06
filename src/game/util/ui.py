import pygame

pygame.mixer.init()
MIXER = pygame.mixer

hover_sound = pygame.mixer.Sound("game/sounds/effects/button_hover.mp3")

BTN_COLOR = (40, 40, 40)
HOVER_COLOR = (80, 80, 80)
pygame.font.init()
FONT = pygame.font.Font(None, 48)
TEXT_COLOR = (255, 255, 255)

class Button:
    def __init__(self, text, rect, action):
        self.text = text
        self.rect = pygame.Rect(rect)
        self.action = action
        self.hover_progress = 0  # from 0 to 1 for smooth scaling

    def draw(self, surface, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            if self.hover_progress == 0:  # Only play when hover starts
                hover_sound.play()
            self.hover_progress = min(self.hover_progress + 0.1, 1)
        else:
            self.hover_progress = max(self.hover_progress - 0.1, 0)

        scale = 1.0 + 0.1 * self.hover_progress  # scale from 1.0 to 1.1
        draw_rect = self.rect.inflate(
            int(self.rect.width * (scale - 1)),
            int(self.rect.height * (scale - 1))
        )
        color = (
            BTN_COLOR[0] + int((HOVER_COLOR[0] - BTN_COLOR[0]) * self.hover_progress),
            BTN_COLOR[1] + int((HOVER_COLOR[1] - BTN_COLOR[1]) * self.hover_progress),
            BTN_COLOR[2] + int((HOVER_COLOR[2] - BTN_COLOR[2]) * self.hover_progress),
        )
        pygame.draw.rect(surface, color, draw_rect, border_radius=12)

        text_surf = FONT.render(self.text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=draw_rect.center)
        surface.blit(text_surf, text_rect)


    def click(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.action()