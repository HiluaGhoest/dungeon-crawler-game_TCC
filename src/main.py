import math
import random
import pygame
import sys
from game.engine import GameEngine
from game.util.ui import BTN_COLOR, FONT, HOVER_COLOR, MIXER, TEXT_COLOR, Button

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

# Sound effects
start_game = MIXER.Sound("game/sounds/effects/start_game.mp3")
# Load background music
MUSIC_PATH = "game/sounds/music/Echoes_of_the_Abyss.mp3"
MIXER.music.load(MUSIC_PATH)
MIXER.music.set_volume(0.2)  # Low volume

class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.2, 1.0)
        self.size = random.randint(1, 3)
        self.alpha = random.randint(100, 255)

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        star_color = (255, 255, 255, self.alpha)
        star_surface = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
        pygame.draw.circle(star_surface, star_color, (self.size, self.size), self.size)
        surface.blit(star_surface, (int(self.x), int(self.y)))

stars = [Star() for _ in range(100)]

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
    run_settings_menu()

settings = {
    "fullscreen": True,
    "resolution": (WIDTH, HEIGHT),
    "music_volume": 0.2,
    "sfx_volume": 1.0,
}

class ToggleButton:
    def __init__(self, label, rect, initial_value, on_toggle):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.value = initial_value
        self.on_toggle = on_toggle

    def draw(self, surface, mouse_pos):
        color = HOVER_COLOR if self.rect.collidepoint(mouse_pos) else BTN_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        text = f"{self.label}: {'ON' if self.value else 'OFF'}"
        text_surf = FONT.render(text, True, TEXT_COLOR)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def click(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.value = not self.value
            self.on_toggle(self.value)

def run_settings_menu():
    back_button = Button("Back", (WIDTH//2 - 150, HEIGHT - 100, 300, 60), run_menu)

    # Main loop
    while True:
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        for star in stars:
            star.update()
            star.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                back_button.click(mouse_pos)

        back_button.draw(screen, mouse_pos)

        pygame.display.flip()
        clock.tick(60)


title_font = pygame.font.Font("game/assets/fonts/CinzelDecorative-Regular.ttf", 72)
title_text = title_font.render("Tenebris Caeli Crypta", True, (255, 245, 255))
text_surface = title_font.render("Tenebris Caeli Crypta", True, (255, 255, 255))
title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 200))

glow_surface = pygame.Surface(title_text.get_size(), pygame.SRCALPHA)
glow_surface.blit(title_text, (0, 0))
glow_color = pygame.Surface(glow_surface.get_size(), pygame.SRCALPHA)
glow_color.fill((180, 80, 255))  # Purple glow
glow_surface.blit(glow_color, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

def blur_surface(surface, iterations=3):
    for i in range(iterations):
        surface = pygame.transform.smoothscale(surface, (surface.get_width()//2, surface.get_height()//2))
        surface = pygame.transform.smoothscale(surface, (surface.get_width()*2, surface.get_height()*2))
    return surface

glow_surface = blur_surface(glow_surface)

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
        text_pos = (WIDTH//2 - text_surface.get_width()//2, HEIGHT//4 - text_surface.get_height()//2)
        screen.blit(glow_surface, text_pos)
        screen.blit(text_surface, text_pos)

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
