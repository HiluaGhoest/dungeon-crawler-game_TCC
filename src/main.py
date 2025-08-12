import math
import random
import pygame
import webbrowser
import sys
import time
import cProfile
from game.engine import GameEngine
from game.util.ui import BTN_COLOR, FONT, HOVER_COLOR, TEXT_COLOR, Button, blur_surface
from game.assets import load_audio
from sound_manager import SoundManager
from game.assets import get_image
from game.assets import get_font


# --- Loading Screen ---
def show_loading_screen():
    screen.fill((10, 10, 10))
    font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 64)
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
menu_music = load_audio("game/sounds/music/Open_Skies_Infinite_Orbit_Sonauto.mp3")
menu_music.set_volume(0.2)  # Adjust as needed

STAR_SURFACE_CACHE = {}  # key = size -> Surface with white circle
PARTICLE_POOL = {}
class Star:
    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.speed = random.uniform(0.2, 1.0)
        self.size = random.randint(1, 3)
        self.alpha = random.randint(100, 255)
        # get cached surface for size
        if self.size not in STAR_SURFACE_CACHE:
            s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255,255,255,255), (self.size, self.size), self.size)
            STAR_SURFACE_CACHE[self.size] = s
        self._surf = STAR_SURFACE_CACHE[self.size]

    def update(self):
        self.y += self.speed
        if self.y > HEIGHT:
            self.y = 0
            self.x = random.randint(0, WIDTH)

    def draw(self, surface):
        # set alpha and blit cached surface (set_alpha is inexpensive)
        self._surf.set_alpha(self.alpha)
        surface.blit(self._surf, (int(self.x), int(self.y)))

stars = [Star() for _ in range(100)]

# Button actions
def start_singleplayer():
    sound_mgr = SoundManager.get_instance()
    sound_mgr.play_sfx(start_game)  # Use centralized play method
    fade_out()
    game = GameEngine(screen)
    game.run()

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

def run_settings_menu(background_snapshot=None):
    sound_mgr = SoundManager.get_instance()
    back_button = Button("Back", (WIDTH//2 - 150, HEIGHT - 100, 300, 60), lambda: None)
    back_selected = False

    # Volume slider state
    music_volume = sound_mgr.music_volume
    sfx_volume = sound_mgr.sfx_volume

    music_slider_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 50, 400, 16)
    sfx_slider_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 + 50, 400, 16)
    dragging_music = False
    dragging_sfx = False

    # Preload crosshair (once)
    try:
        crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
        size = (16, 16)
        if crosshair_normal:
            crosshair_normal = pygame.transform.scale(crosshair_normal, size)
        if not crosshair_normal:
            raise Exception("Missing crosshair image")
    except Exception:
        size = (32, 32)
        crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)

    crosshair_img = crosshair_normal
    crosshair_offset = (size[0] // 2, size[1] // 2)
    pygame.mouse.set_visible(False)

    # Precreate overlay surface (reuse)
    overlay_alpha = 100
    _overlay_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    _overlay_surf.fill((0, 0, 0, overlay_alpha))

    # Cache label surfaces, only update when value changes
    def make_music_label(vol):
        music_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 32)
        return music_font.render(f"Music Volume: {int(vol*100)}%", True, (255,255,255))
    def make_sfx_label(vol):
        music_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 32)
        return music_font.render(f"SFX Volume: {int(vol*100)}%", True, (255,255,255))

    music_label_surf = make_music_label(music_volume)
    sfx_label_surf = make_sfx_label(sfx_volume)
    last_music_label_val = int(music_volume*100)
    last_sfx_label_val = int(sfx_volume*100)

    # Throttle audio set calls (avoid calling mixer too often)
    last_audio_set_time = 0.0
    audio_set_cooldown = 0.05  # seconds
    minimal_delta = 0.01       # only update if change > 1%

    # Main loop

    # Keyboard navigation state
    selected_index = 0  # 0: back button, 1: music slider, 2: sfx slider
    mouse_active = False
    while True:
        dt = clock.get_time() / 1000.0
        mouse_pos = pygame.mouse.get_pos()

        # Draw background
        if background_snapshot is not None:
            screen.blit(background_snapshot, (0, 0))
            screen.blit(_overlay_surf, (0, 0))
            line_y = HEIGHT
            pygame.draw.line(screen, (255,255,255), (0, line_y), (WIDTH, line_y), 8)
        else:
            screen.fill(BG_COLOR)
            for star in stars:
                star.update()
                star.draw(screen)

        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % 3
                    mouse_active = False
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % 3
                    mouse_active = False
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected_index == 0:
                        return
            elif event.type == pygame.MOUSEMOTION:
                mouse_active = True
                back_selected = back_button.rect.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_button.rect.collidepoint(mouse_pos):
                    return
                if music_slider_rect.collidepoint(mouse_pos):
                    dragging_music = True
                    rel_x = max(music_slider_rect.left, min(mouse_pos[0], music_slider_rect.right))
                    music_volume = (rel_x - music_slider_rect.left) / music_slider_rect.width
                if sfx_slider_rect.collidepoint(mouse_pos):
                    dragging_sfx = True
                    rel_x = max(sfx_slider_rect.left, min(mouse_pos[0], sfx_slider_rect.right))
                    sfx_volume = (rel_x - sfx_slider_rect.left) / sfx_slider_rect.width
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_music = False
                dragging_sfx = False

        # Throttled audio updates
        now_t = time.time()
        if (abs(music_volume - sound_mgr.music_volume) > minimal_delta and now_t - last_audio_set_time > audio_set_cooldown):
            sound_mgr.set_music_volume(music_volume)
            last_audio_set_time = now_t
        if (abs(sfx_volume - sound_mgr.sfx_volume) > minimal_delta and now_t - last_audio_set_time > audio_set_cooldown):
            sound_mgr.set_sfx_volume(sfx_volume)
            last_audio_set_time = now_t

        # Draw music slider
        pygame.draw.rect(screen, (80, 80, 80), music_slider_rect, border_radius=8)
        knob_x = int(music_slider_rect.left + music_volume * music_slider_rect.width)
        knob_size = 16
        pygame.draw.rect(screen, (255,255,255), (knob_x - knob_size//2, music_slider_rect.centery - knob_size//2, knob_size, knob_size), border_radius=3)

        current_music_val = int(music_volume * 100)
        if current_music_val != last_music_label_val:
            music_label_surf = make_music_label(music_volume)
            last_music_label_val = current_music_val
        screen.blit(music_label_surf, (WIDTH//2 - music_label_surf.get_width()//2, music_slider_rect.top - 70))

        # Draw SFX slider
        pygame.draw.rect(screen, (80, 80, 80), sfx_slider_rect, border_radius=8)
        knob_x = int(sfx_slider_rect.left + sfx_volume * sfx_slider_rect.width)
        pygame.draw.rect(screen, (255,255,255), (knob_x - knob_size//2, sfx_slider_rect.centery - knob_size//2, knob_size, knob_size), border_radius=3)

        current_sfx_val = int(sfx_volume * 100)
        if current_sfx_val != last_sfx_label_val:
            sfx_label_surf = make_sfx_label(sfx_volume)
            last_sfx_label_val = current_sfx_val
        screen.blit(sfx_label_surf, (WIDTH//2 - sfx_label_surf.get_width()//2, sfx_slider_rect.top - 70))

        # Draw back button with selection highlight
        back_selected_draw = back_selected or (not mouse_active and selected_index == 0)
        back_button.draw(screen, mouse_pos, selected=back_selected_draw)

        # Draw crosshair
        screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))

        pygame.display.flip()
        clock.tick(60)



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

def precompute_glows(base_glow, max_blur=12, steps=6):
    # steps = how many blur variants you want (fewer => faster)
    glows = {}
    for i in range(steps+1):
        # map i -> blur amount (coarse)
        amt = int(max_blur * (i / steps))
        if amt <= 0:
            glows[i] = base_glow
        else:
            g = blur_surface(base_glow, iterations=1)  # assume blur_surface supports iterations param
            # if you need more blur, blur multiple times or downscale/upsample trick
            glows[i] = g
    return glows

# usage (once at init after creating glow_surface)

_glow_levels = precompute_glows(glow_surface, max_blur=12, steps=6)
## Use this inside your animation loop, where slide_progress is defined:
# idx = int((1 - slide_progress) * 6)  # 0..6
# blurred_glow = _glow_levels[idx]

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


# --- Credits Menu ---
def run_credits_menu():
    credits_text = [
        "Sound Effects (from freesound.org):",
        '  "8-bit explosion low resonant.wav" by celesti-whispers — https://freesound.org/s/466006/',
        '  "8bit snare.wav" by cubix — https://freesound.org/s/124382/',
        '  "8 Bit Slam" by Jofae — https://freesound.org/s/361636/',
        '  "Roll.wav" by DrMrSir — https://freesound.org/s/529563/',
        '  "Slime Death (1)" by DrMinky — https://freesound.org/s/167074/',
        '  "FX - Clankibuzz Hit.wav" by JohanDeecke — https://freesound.org/s/367760/',
        '  "Stick-Swoosh Whoosh" by Hitrison — https://freesound.org/s/216675/',
        '  "Alarm.wav" by JomelleJager — https://freesound.org/s/383148/',
        '  "Menu screen mouse over" by DrMinky — https://freesound.org/s/166186/',
        "",
        "All sound effects are licensed under Creative Commons (CC0, CC BY 3.0, CC BY 4.0)",
        "See: https://creativecommons.org/",
        "",
        "Game Code:",
        "  Attilio Santana Minzoni",
        "",
        "Music:",
        "  https://sonauto.ai",
        "",
        "Artwork:",
        "  Attilio Santana Minzoni",
        "",
        "Special Thanks:",
        "  ...",
    ]
    font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 16)
    title_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 48)
    line_height = font.get_height() + 8
    title_height = title_font.get_height()
    back_button_height = 80
    credits_area_top = 80 + title_height
    credits_area_bottom = HEIGHT - back_button_height - 40
    credits_area_height = credits_area_bottom - credits_area_top
    scroll_offset = 0.0
    scroll_speed = 30  # pixels per second
    scroll_direction = 1  # 1 for down, -1 for up
    direction_cooldown = 0.0
    cooldown_time = 1.0  # seconds to pause at top/bottom
    back_button = Button("Back", (WIDTH//2 - 150, HEIGHT - 100, 300, 60), lambda: None)
    clock = pygame.time.Clock()
    selected_index = 0
    mouse_active = False
    back_selected = False
    # Setup custom crosshair (same as menu/settings)
    try:
        crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
        size = (16, 16)
        if crosshair_normal:
            crosshair_normal = pygame.transform.scale(crosshair_normal, size)
        if not crosshair_normal:
            raise Exception("Missing crosshair image")
    except Exception:
        size = (32, 32)
        crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
        pygame.draw.line(crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)
    crosshair_img = crosshair_normal
    crosshair_offset = (size[0] // 2, size[1] // 2)
    pygame.mouse.set_visible(False)

    menu_particle_timer = 0
    # ...existing code...
    link_rects_frame = []
    while True:
        dt = clock.get_time() / 1000.0
        mouse_pos = pygame.mouse.get_pos()
        # Auto-scroll credits (down then up, with cooldown)
        max_scroll = max(0, len(credits_text) * line_height - credits_area_height)
        if direction_cooldown > 0:
            direction_cooldown -= dt
        else:
            scroll_offset += scroll_speed * dt * scroll_direction
            if scroll_offset >= max_scroll:
                scroll_offset = max_scroll
                scroll_direction = -1
                direction_cooldown = cooldown_time
            elif scroll_offset <= 0:
                scroll_offset = 0
                scroll_direction = 1
                direction_cooldown = cooldown_time
        screen.fill(BG_COLOR)
        # Draw menu particles
        update_and_draw_menu_particles(screen, mouse_pos, dt)
        # Draw title
        title_surf = title_font.render("CREDITS", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(WIDTH//2, 80 + title_height//2))
        screen.blit(title_surf, title_rect)
        # Draw credits text in area between title and back button
        link_rects_frame.clear()
        for i, line in enumerate(credits_text):
            y = credits_area_top + i * line_height - scroll_offset
            if credits_area_top <= y <= credits_area_bottom:
                import re
                url_match = re.search(r'(https?://\S+)', line)
                if url_match:
                    url = url_match.group(1)
                    text_surf = font.render(line, True, (80, 180, 255))
                    text_rect = text_surf.get_rect(center=(WIDTH//2, int(y)))
                    # Highlight if mouse is over the actual text
                    if text_rect.collidepoint(mouse_pos):
                        pygame.draw.line(screen, (80, 180, 255), (text_rect.left, text_rect.bottom), (text_rect.right, text_rect.bottom), 2)
                        text_surf = font.render(line, True, (120, 220, 255))
                    screen.blit(text_surf, text_rect)
                    link_rects_frame.append((url, text_rect))
                else:
                    text_surf = font.render(line, True, (255, 255, 255))
                    text_rect = text_surf.get_rect(center=(WIDTH//2, int(y)))
                    screen.blit(text_surf, text_rect)
        # Draw back button with selection highlight
        back_selected_draw = back_selected or (not mouse_active and selected_index == 0)
        back_button.draw(screen, mouse_pos, selected=back_selected_draw)
        # Draw custom crosshair at mouse position
        screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))
        pygame.display.flip()
        # Now process events (after drawing, so rects are up-to-date)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                safe_exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    return
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected_index == 0:
                        return
            elif event.type == pygame.MOUSEMOTION:
                mouse_active = True
                back_selected = back_button.rect.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check if a link was clicked (use rects from this frame)
                for url, rect in link_rects_frame:
                    if rect.collidepoint(mouse_pos):
                        print(f"Opening link: {url}")
                        webbrowser.open_new(url)
                        break
                if back_button.rect.collidepoint(mouse_pos):
                    return
        clock.tick(60)

buttons = []
button_targets = [HEIGHT//2 + 30, HEIGHT//2 + 120, HEIGHT//2 + 210, HEIGHT//2 + 300]  # final Y positions

def safe_exit():
    pygame.quit()
    sys.exit()

for i, (label, action) in enumerate([
    ("Singleplayer", start_singleplayer),
    ("Settings", open_settings),
    ("Credits", run_credits_menu),
    ("Exit", safe_exit)
]):
    rect = pygame.Rect(WIDTH//2 - 150, HEIGHT + 100, 300, 60)  # Start off-screen
    buttons.append(Button(label, rect, action))
# --- Menu Crosshair Particle System ---
for r in (1,2,3):
    surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255,255,255,255), (r, r), r)
    PARTICLE_POOL[r] = surf

class MenuParticle:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.radius = random.randint(1, 3)
        self.color = random.choice([(255,255,255), (230,230,255), (255,230,230)])
        self.alpha = 255
        self.time = 0
        self.lifetime = 0.5
        self.velocity = pygame.math.Vector2(random.uniform(-20, 20), random.uniform(5, 15))
        # reference to pre-made surface
        self._base_surf = PARTICLE_POOL[self.radius]

    def update(self, dt):
        self.time += dt
        self.alpha = int(255 * (1 - (self.time / self.lifetime)))
        self.pos += self.velocity * dt

    def draw(self, surface):
        r = self.radius
        surf = self._base_surf
        surf.set_alpha(self.alpha)
        # tinting color per-particle is heavier; avoid per-pixel tinting.
        surface.blit(surf, (self.pos.x - r, self.pos.y - r))

menu_particles = []
menu_particle_timer = 0
menu_particle_interval = 0.05
menu_particle_lifetime = 0.5

MAX_MENU_PARTICLES = 80
def spawn_menu_particle(mouse_pos):
    if len(menu_particles) >= MAX_MENU_PARTICLES:
        # recycle oldest
        p = menu_particles.pop(0)
        p.pos.update(mouse_pos[0], mouse_pos[1])
        p.time = 0
        p.alpha = 255
        p.velocity = pygame.math.Vector2(random.uniform(-20, 20), random.uniform(5, 15))
        menu_particles.append(p)
    else:
        menu_particles.append(MenuParticle(mouse_pos))

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

    
    # Play music through sound manager
    sound_mgr = SoundManager.get_instance()
    sound_mgr.play_music(menu_music)

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
