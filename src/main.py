import random
import pygame
import sys
from game.engine import GameEngine

# Initialize pygame
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

# Fullscreen + NOFRAME
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Main Menu")
clock = pygame.time.Clock()

# Colors and Fonts
BG_COLOR = (10, 10, 10)
BTN_COLOR = (40, 40, 40)
HOVER_COLOR = (80, 80, 80)
TEXT_COLOR = (255, 255, 255)
FONT = pygame.font.Font(None, 48)

# Sound effects
pygame.mixer.init()
hover_sound = pygame.mixer.Sound("game/sounds/effects/button_hover.mp3")
start_game = pygame.mixer.Sound("game/sounds/effects/start_game.mp3")
# Load background music
MUSIC_PATH = "game/sounds/music/Echoes_of_the_Abyss.mp3"
pygame.mixer.music.load(MUSIC_PATH)
pygame.mixer.music.set_volume(0.2)  # Low volume

class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.2, 1.0)
        self.size = random.randint(1, 3)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        pygame.draw.circle(surface, (200, 200, 255), (int(self.x), int(self.y)), self.size)

stars = [Star() for _ in range(100)]

# Button class
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

# Button actions
def start_singleplayer():
    start_game.play()
    fade_out()
    # Start background music (looping)
    pygame.mixer.music.play(-1)
    game = GameEngine()
    game.run()
    # Optionally stop music after game ends
    pygame.mixer.music.stop()


def open_settings():
    print("[INFO] Settings screen is not yet implemented.")

title_font = pygame.font.Font("game/assets/fonts/CinzelDecorative-Regular.ttf", 72)
title_text = title_font.render("Tenebris Caeli Crypta", True, (255, 245, 255))
title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 200))


# Create menu buttons (centered on screen)
buttons = [
    Button("Singleplayer", (WIDTH//2 - 150, HEIGHT//2 - 100, 300, 60), start_singleplayer),
    Button("Settings",     (WIDTH//2 - 150, HEIGHT//2 + 100, 300, 60), open_settings),
]

def fade_out():
    fade = pygame.Surface((WIDTH, HEIGHT))
    fade.fill((0, 0, 0))
    for alpha in range(0, 255, 10):
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)


# Main menu loop
def run_menu():
    while True:
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        for star in stars:
            star.update()
            star.draw(screen)
        screen.blit(title_text, title_rect)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for button in buttons:
                    button.click(mouse_pos)

        for button in buttons:
            button.draw(screen, mouse_pos)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    run_menu()
