import math
import random
import pygame
import sys
import cProfile
from game.engine import GameEngine
from game.util.ui import BTN_COLOR, FONT, HOVER_COLOR, TEXT_COLOR, Button, blur_surface
from game.assets import load_audio

# --- Loading Screen ---
def show_loading_screen():
    screen.fill((10, 10, 10))
    font = pygame.font.SysFont(None, 64)
    text = font.render("Loading...", True, (200, 200, 255))
    rect = text.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(text, rect)
    pygame.display.flip()
    # Give time for the loading screen to show
    pygame.time.delay(500)

# Initialize pygame
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h

# Fullscreen + NOFRAME
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF)
pygame.display.set_caption("Main Menu")
clock = pygame.time.Clock()

# Colors and Fonts
BG_COLOR = (10, 10, 10)

# Sound effects
start_game = load_audio("game/sounds/effects/start_game.mp3")

# Load menu/intro music
MENU_MUSIC_PATH = "game/sounds/music/Open Skies - Infinite Orbit - Sonauto.mp3"
pygame.mixer.music.load(MENU_MUSIC_PATH)
pygame.mixer.music.set_volume(0.2)  # Adjust as needed

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
    # Do NOT restart music here; let menu/intro music continue
    game = GameEngine(screen)
    game.run()
    # Do not stop music here; let menu or next game handle music state

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
    from game.assets import get_image
    try:
        crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
        size = (16, 16)
        if crosshair_normal:
            crosshair_normal = pygame.transform.scale(crosshair_normal, size)
        if not crosshair_normal:
            raise Exception("Missing crosshair image")
    except:
        size = (32, 32)
        crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)
    crosshair_img = crosshair_normal
    crosshair_offset = (size[0] // 2, size[1] // 2)
    pygame.mouse.set_visible(False)

    while True:
        dt = clock.get_time() / 1000.0
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        star_layers = [
            [Star() for _ in range(30)],
            [Star() for _ in range(30)],
            [Star() for _ in range(40)],
        ]
        star_speeds = [0.2, 0.5, 1.0]  # Slow to fast

        # In your drawing loop:
        for i, layer in enumerate(star_layers):
            for star in layer:
                star.speed = star_speeds[i]
                star.update()
                star.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        back_button.draw(screen, mouse_pos)
        update_and_draw_menu_particles(screen, mouse_pos, dt)
        # Draw custom crosshair at mouse position
        screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))

        pygame.display.flip()
        clock.tick(60)


from game.assets import get_font
title_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 72)
title_text = title_font.render("Tenebris Caeli Crypta", True, (255, 245, 255))
text_surface = title_font.render("Tenebris Caeli Crypta", True, (255, 255, 255))
title_rect = title_text.get_rect(center=(WIDTH//2, HEIGHT//2 - 200))


# Pre-render title glow surface only once and cache it
if not hasattr(pygame, "_cached_glow_surface"):
    glow_surface = pygame.Surface(title_text.get_size(), pygame.SRCALPHA)
    glow_surface.blit(title_text, (0, 0))
    glow_color = pygame.Surface(glow_surface.get_size(), pygame.SRCALPHA)
    glow_color.fill((180, 80, 255))  # Purple glow
    glow_surface.blit(glow_color, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    glow_surface = blur_surface(glow_surface)
    pygame._cached_glow_surface = glow_surface
else:
    glow_surface = pygame._cached_glow_surface



glow_surface = blur_surface(glow_surface)

button_targets = [
    HEIGHT//2 + 150 - 60,
    HEIGHT//2 + 240 - 60,
    HEIGHT//2 + 330 - 60
]

def fade_out():
    fade = pygame.Surface((WIDTH, HEIGHT))
    fade.fill((0, 0, 0))
    for alpha in range(0, 255, 10):
        fade.set_alpha(alpha)
        screen.blit(fade, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)

buttons = []
button_targets = [HEIGHT//2 + 90, HEIGHT//2 + 180, HEIGHT//2 + 270]  # final Y positions

def safe_exit():
    pygame.quit()
    sys.exit()

for i, (label, action) in enumerate([
    ("Singleplayer", start_singleplayer),
    ("Settings", open_settings),
    ("Exit", safe_exit)
]):
    rect = pygame.Rect(WIDTH//2 - 150, HEIGHT + 100, 300, 60)  # Start off-screen
    buttons.append(Button(label, rect, action))
# --- Menu Crosshair Particle System ---
class MenuParticle:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.radius = random.uniform(1, 3)
        self.color = random.choice([(255,255,255), (230,230,255), (255,230,230)])
        self.alpha = 255
        self.time = 0
        self.lifetime = 0.5
        self.velocity = pygame.math.Vector2(random.uniform(-20, 20), random.uniform(5, 15))
    def update(self, dt):
        self.time += dt
        self.alpha = int(255 * (1 - (self.time / self.lifetime)))
        self.pos += self.velocity * dt
    def draw(self, surface):
        r = int(self.radius)
        # Clamp color values to 0-255 and ensure tuple length 4
        base_color = [int(c) for c in self.color]
        alpha = int(self.alpha)
        color_with_alpha = tuple(max(0, min(255, v)) for v in (base_color + [alpha])[:4])
        particle_surface = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, color_with_alpha, (r, r), r)
        surface.blit(particle_surface, (self.pos.x - r, self.pos.y - r))

menu_particles = []
menu_particle_timer = 0
menu_particle_interval = 0.05
menu_particle_lifetime = 0.5

def spawn_menu_particle(mouse_pos):
    offset = pygame.math.Vector2(random.uniform(-10, 10), random.uniform(-10, 10))
    menu_particles.append(MenuParticle((mouse_pos[0] + offset.x, mouse_pos[1] + offset.y)))

def update_and_draw_menu_particles(surface, mouse_pos, dt):
    global menu_particle_timer
    menu_particle_timer += dt
    if menu_particle_timer >= menu_particle_interval:
        menu_particle_timer = 0
        spawn_menu_particle(mouse_pos)
    for p in menu_particles[:]:
        p.update(dt)
        p.draw(surface)
        if p.time >= menu_particle_lifetime:
            menu_particles.remove(p)

# Main menu loop
def run_menu():
    selected_index = 0
    mouse_active = False  # Start with keyboard navigation
    frame_count = 0  # track time since menu started
    animation_duration = 60  # frames (1 second at 60fps)

    pygame.mouse.set_visible(False)  # Hide mouse cursor initially

    # --- Opening Animation ---
    star_fade_duration = 120  # frames
    title_slide_duration = 60  # frames
    title_start_y = -title_rect.height
    # Use the same position as in the main loop for consistency
    title_end_y = HEIGHT//4 - text_surface.get_height()//2
    blur_max = 12
    button_anim_delay = title_slide_duration  # delay until title animation finishes
    button_anim_frames = animation_duration
    menu_ready = False  # Cooldown flag
    for anim_frame in range(max(star_fade_duration, title_slide_duration + button_anim_frames)):
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # Animate stars fade-in
        star_alpha = int(255 * min(1, anim_frame / star_fade_duration))
        for star in stars:
            star.update()
            # Draw with animated alpha
            orig_alpha = star.alpha
            star.alpha = int(orig_alpha * (star_alpha / 255))
            star.draw(screen)
            star.alpha = orig_alpha  # restore

        # Animate title slide and blur (ease-out cubic)
        slide_progress = min(1, anim_frame / title_slide_duration)
        eased_slide = 1 - (1 - slide_progress) ** 3  # ease-out cubic
        title_y = int(title_start_y + (title_end_y - title_start_y) * eased_slide)
        blur_amount = int(blur_max * (1 - slide_progress))
        if blur_amount > 0:
            # Blur the glow surface more at the start
            blurred_glow = blur_surface(glow_surface)
            for _ in range(blur_amount-1):
                blurred_glow = blur_surface(blurred_glow)
        else:
            blurred_glow = glow_surface
        text_pos = (WIDTH//2 - text_surface.get_width()//2, title_y)
        screen.blit(blurred_glow, text_pos)
        screen.blit(text_surface, text_pos)

        # Animate buttons in only after title animation finishes
        if anim_frame >= button_anim_delay:
            button_anim_frame = anim_frame - button_anim_delay
            for i, button in enumerate(buttons):
                target_y = button_targets[i]
                # Animate position: use ease-out curve
                if button_anim_frame < button_anim_frames:
                    progress = button_anim_frame / button_anim_frames
                    eased = 1 - (1 - progress) ** 3  # ease-out cubic
                    animated_y = HEIGHT + (target_y - HEIGHT) * eased
                    button.rect.y = int(animated_y)
                else:
                    button.rect.y = target_y

                # Pre-select the first button (Singleplayer) visually
                is_selected = (i == 0)
                button.draw(screen, mouse_pos, selected=is_selected)

        pygame.display.flip()
        clock.tick(60)

    # --- End Opening Animation ---
    menu_ready = True  # Allow input after animation and loading
    frame_count = 0
    mouse_active = False  # Force keyboard mode after animation
    pygame.mouse.set_visible(False)
    from game.assets import get_image
    try:
        crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
        size = (16, 16)
        if crosshair_normal:
            crosshair_normal = pygame.transform.scale(crosshair_normal, size)
        if not crosshair_normal:
            raise Exception("Missing crosshair image")
    except:
        size = (32, 32)
        crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)
    crosshair_img = crosshair_normal
    crosshair_offset = (size[0] // 2, size[1] // 2)
    pygame.mouse.set_visible(False)

    # Always reload and play menu music when entering menu
    pygame.mixer.music.load(MENU_MUSIC_PATH)
    pygame.mixer.music.set_volume(settings.get("music_volume", 0.2))
    pygame.mixer.music.play(-1)
    while True:
        frame_count += 1
        dt = clock.get_time() / 1000.0
        screen.fill(BG_COLOR)
        mouse_pos = pygame.mouse.get_pos()

        # Update and draw stars
        for star in stars:
            star.update()
            star.draw(screen)

        # Draw title
        text_pos = (WIDTH//2 - text_surface.get_width()//2, HEIGHT//4 - text_surface.get_height()//2)
        screen.blit(glow_surface, text_pos)
        screen.blit(text_surface, text_pos)

        # Input handling
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                safe_exit()
            if not menu_ready:
                continue  # Ignore all input until menu is ready
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    safe_exit()
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(buttons)
                    mouse_active = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(buttons)
                    mouse_active = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    buttons[selected_index].action()
            elif event.type == pygame.MOUSEMOTION:
                # Switch to mouse control when mouse moves
                prev_selected = selected_index
                mouse_active = True
                # Only update selected_index if mouse is over a different button
                for i, button in enumerate(buttons):
                    if button.rect.collidepoint(mouse_pos):
                        if i != selected_index:
                            selected_index = i
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Handle mouse clicks
                for i, button in enumerate(buttons):
                    if button.rect.collidepoint(mouse_pos):
                        selected_index = i  # Update selected index
                        button.action()

        # Draw buttons with hybrid selection logic (no animation)
        for i, button in enumerate(buttons):
            target_y = button_targets[i]
            button.rect.y = target_y
            # If mouse_active, highlight selected_index unless mouse is over another button
            if mouse_active:
                is_selected = (i == selected_index)
            else:
                is_selected = (i == selected_index)
            button.draw(screen, mouse_pos, selected=is_selected)

        update_and_draw_menu_particles(screen, mouse_pos, dt)
        # Draw custom crosshair at mouse position
        screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    show_loading_screen()
    # Load assets here if needed (fonts, images, sounds)
    cProfile.run("run_menu()")
