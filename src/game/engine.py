# Engine do jogo
import random
import socket
import threading
import pygame
import math
from game.player import Player
from game.dungeon import Dungeon
from game.util.light import render_volumetric_light
import os
from game.util.ui import Button
from game.assets import get_font, get_image
import builtins
from game.util.ui import blur_surface


import json

# Stardust: moeda coletável
class Stardust:
    def __init__(self, x, y, amount=1):
        self.x = x
        self.y = y
        self.amount = amount
        self.radius = 2 + amount * 2  # Tamanho proporcional ao valor
        self.collected = False
        self.float_timer = 0.0
        self.float_duration = 0.7
        self.vx = random.uniform(-0.3, 0.3)
        self.vy = random.uniform(-0.2, 0.2)

    def update(self, dt, player):
        # Stardust flutua e faz bobbing
        self.float_timer += dt
        self.x += self.vx
        self.y += self.vy + math.sin(self.float_timer * 4) * 0.2  # bobbing vertical
        # Suaviza movimento
        self.vx *= 0.95
        # Se perto do player, move em direção com easing
        dist = math.hypot(player.x - self.x, player.y - self.y)
        if dist < 250:
            # Easing: quanto mais perto, mais rápido (ease-out)
            t = min(1.0, dist / 250)
            ease = 1 - (1 - t) ** 2  # ease-out quad
            dx = (player.x - self.x) * 0.12 * ease
            dy = (player.y - self.y) * 0.12 * ease
            self.x += dx
            self.y += dy
            if dist < player.size * 2:
                self.collected = True

    def draw(self, surface, camera_x, camera_y, rooms=None):
        px = int(self.x - camera_x)
        py = int(self.y - camera_y)
        color = (255, 255, 255)
        pygame.draw.circle(surface, color, (px, py), int(self.radius))

# Gerenciador de Stardust
class StardustManager:
    def __init__(self, save_path="stardust.json"):
        self.save_path = save_path
        self.stardust = 0
        self.load_stardust()

    def add_stardust(self, amount):
        self.stardust += amount
        self.save_stardust()

    def spend_stardust(self, amount):
        if self.stardust >= amount:
            self.stardust -= amount
            self.save_stardust()
            return True
        return False

    def save_stardust(self):
        with open(self.save_path, "w") as f:
            json.dump({"stardust": self.stardust}, f)

    def load_stardust(self):
        if os.path.exists(self.save_path):
            with open(self.save_path, "r") as f:
                data = json.load(f)
                self.stardust = data.get("stardust", 0)
        else:
            self.stardust = 0

# Instância global do gerenciador de stardust
stardust_manager = StardustManager()

class GameEngine:
    def run_store_room(self):
        """Executa o fluxo normal, mas com animação de introdução personalizada 'Store'."""
        # Cria uma dungeon com apenas 1 sala para o modo loja
        # Passa spawn_perks=True para garantir que a loja gere PerkPillar
        self.dungeon = Dungeon(tile_size=20, total_rooms=1, branching_factor=1, spawn_perks=True)
        self.room = self.dungeon.get_current_room()
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        self.player = Player(spawn_x, spawn_y)
        self.dungeon.player = self.player
        self.camera_x = spawn_x - self.width // 2
        self.camera_y = spawn_y - self.height // 2
        self.run_intro_cutscene(floor_number="Store", message="Welcome to the Store!", post_delay=0.6, overlay_fade_duration=0.5)
        self.tutorial_step = 0
        self.tutorial_phrases = [
            "WASD to move, Shift to sprint.",
            "Press E to pick up weapon, Q to drop."
        ]
        accumulated_pause_time = 0
        while self.running:
            self.handle_events()
            dt = self.clock.tick(144) / 1000.0
            self.update(dt)
            self.render()
    # Persistent virtual surface for zoomed rendering
    def run_game_over_screen(self):
        """Show a game over overlay and wait for player to restart the floor or quit."""
        overlay_alpha = 160
        animation_time = 0.0
        animation_duration = 1.2  # seconds for fade-in
        running_game_over = True
        button_restart = Button("Restart Floor", (self.width//2 - 150, self.height//2 + 40, 300, 60), action=None)
        button_quit = Button("Quit", (self.width//2 - 150, self.height//2 + 120, 300, 60), action=None)
        buttons = [button_restart, button_quit]
        selected_index = 0
        self.game_over_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 64)
        text_surf = self.game_over_font.render("GAME OVER", True, (255, 60, 60))
        text_rect = text_surf.get_rect(center=(self.width//2, self.height//2 - 80))
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))
        mouse_active = False
        pygame.mouse.set_visible(False)

        def restart():
            nonlocal running_game_over
            running_game_over = False
            # Fully reload the game by restarting the process

        def quit_game():
            nonlocal running_game_over
            self.running = False
            running_game_over = False

        button_restart.action = restart
        button_quit.action = quit_game

        while running_game_over and self.running:
            self.dt = self.clock.get_time() / 1000.0
            self.update_crosshair(self.dt)
            self.update_crosshair_particles(self.dt)
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    running_game_over = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        buttons[selected_index].action()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_index = (selected_index + 1) % len(buttons)
                        mouse_active = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected_index = (selected_index - 1) % len(buttons)
                        mouse_active = False
                elif event.type == pygame.MOUSEMOTION:
                    for i, button in enumerate(buttons):
                        if button.rect.collidepoint(mouse_pos):
                            selected_index = i
                            mouse_active = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, button in enumerate(buttons):
                        if button.rect.collidepoint(mouse_pos):
                            selected_index = i
                            button.action()
            # Proper fade calculation
            animation_time += self.dt
            fade = min(1.0, animation_time / animation_duration)

            # Draw last frame as background (optional: could use a snapshot)
            self.render(do_flip=False)
            # Overlay
            overlay.set_alpha(int(overlay_alpha * fade))
            self.screen.blit(overlay, (0, 0))
            # Game Over text
            text_surf.set_alpha(int(255 * fade))
            self.screen.blit(text_surf, text_rect)
            # Draw buttons
            for i, button in enumerate(buttons):
                is_selected = (i == selected_index)
                button.draw(self.screen, mouse_pos, selected=is_selected)
            # Crosshair
            crosshair_img = self.current_crosshair if hasattr(self, 'current_crosshair') else None
            crosshair_offset = self.crosshair_offset if hasattr(self, 'crosshair_offset') else (0, 0)
            if crosshair_img:
                self.screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))
            pygame.display.flip()

        # After leaving, reset mouse visibility
        pygame.mouse.set_visible(True)
    # Track previous room index for rendering
    def __init__(self, screen, width=800, height=600, title="Dungeon Crawler", fullscreen=True):
        self.mouse_attack_held = False  # Track if mouse attack button is held
        
        # Configurar fullscreen
        if fullscreen:
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            self.screen = screen
        else:
            self.width = width
            self.height = height
            self.screen = screen
            
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.previous_room_index = None
        self.powerup_menu_shown_rooms = set()
        
        # Light sources
        self.light_sources = []  # Track all light sources
        self.light_cache = {} # Cache for light textures

        # Câmera/viewport
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.3
        self.camera_smoothing = 0.1

        # Track previous room index for rendering
        self.previous_room_index = None

        # Criar o dungeon
        self.dungeon = Dungeon(tile_size=20, total_rooms=25, branching_factor=3)
        
        # Obter a sala atual
        self.room = self.dungeon.get_current_room()
        # Cache for wall rects per room
        self._room_wall_rect_cache = {}
        # Cached wall rects and room rect for current room
        self.current_wall_rects = None
        self.current_room_rect = None

        # Get spawn position from dungeon
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        self.player = Player(spawn_x, spawn_y)
        self.dungeon.player = self.player

        # Initialize camera
        self.camera_x = spawn_x - self.width // 2
        self.camera_y = spawn_y - self.height // 2

        # FPS monitor
        self.show_fps = False
        self.fps_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 32)

        # Collision rects debug
        self.show_collision_rects = False

        # --- GLOBAL PROJECTILES LIST ---
        if not hasattr(builtins, 'projectiles') or not isinstance(builtins.projectiles, list):
            builtins.projectiles = []
        self.projectiles = builtins.projectiles

        # Persistent darkness overlay surface (for performance)
        self.virtual_surface = None
        self.darkness_overlay = None

        # Crosshair particles
        self.crosshair_particles = []
        self.particle_spawn_timer = 0
        self.particle_spawn_interval = 0.05  # seconds between particles
        self.particle_lifetime = 0.5  # seconds
        self.particle_colors = [
            (255, 255, 255),  # white
            (230, 230, 255),  # light blue-white
            (255, 230, 230)   # light pink-white
        ]

        # Load crosshair sprite
        try:
            self.crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
            self.crosshair_attack = get_image("crosshair_attack", "game/assets/sprites/ui/cursor/cursor_attack.png")
            # Scale if needed (example scales to 16x16)
            size = (16, 16)
            if self.crosshair_normal:
                self.crosshair_normal = pygame.transform.scale(self.crosshair_normal, size)
            if self.crosshair_attack:
                self.crosshair_attack = pygame.transform.scale(self.crosshair_attack, size)
            if not self.crosshair_normal or not self.crosshair_attack:
                raise Exception("Missing crosshair image")
        except:
            # Fallback: create simple crosshairs if images not found
            size = (32, 32)
            self.crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.line(self.crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
            pygame.draw.line(self.crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)
            self.crosshair_attack = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.line(self.crosshair_attack, (255, 0, 0), (16, 0), (16, 32), 3)
            pygame.draw.line(self.crosshair_attack, (255, 0, 0), (0, 16), (32, 16), 3)
            
        # Current crosshair (starts as normal)
        self.current_crosshair = self.crosshair_normal
        self.crosshair_offset = (size[0] // 2, size[1] // 2)
        self.is_paused = False  # Flag para pausar atualizações
        self.pause_start_time = 0  # Armazenará quando o pause começou

            
        # For smooth transitions
        self.crosshair_scale = 1.0
        self.target_scale = 1.0

        self.enemies = []
        self.stardusts = []
        # Floor system
        self.current_floor = 1
        self.max_floor = 99

    def descend_floor(self):
        """Desce para o próximo andar, gerando novo dungeon e aumentando dificuldade."""
        if self.current_floor < self.max_floor:
            self.current_floor += 1
            # Gera novo dungeon
            self.dungeon = Dungeon(tile_size=20, total_rooms=25, branching_factor=3)
            self.room = self.dungeon.get_current_room()
            self._room_wall_rect_cache = {}
            self.current_wall_rect = None
            self.current_room_rect = None
            # Reposiciona player
            spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
            self.player.set_position(spawn_x, spawn_y)
            self.camera_x = spawn_x - self.width // 2
            self.camera_y = spawn_y - self.height // 2
            # Limpa projéteis e stardusts
            self.projectiles.clear()
            self.stardusts.clear()
            # Atualiza inimigos do novo andar
            self.enemies = getattr(self.room, 'enemies', []) if hasattr(self.room, 'enemies') else []
            # Aplica multiplicador de vida nos inimigos
            for room in self.dungeon.rooms.values():
                if hasattr(room, 'enemies'):
                    for enemy in room.enemies:
                        enemy.health = int(enemy.health * (1 + 0.5 * (self.current_floor - 1)))
        
    def update_crosshair(self, dt):
        """Smoothly transition between crosshair states"""
        if self.mouse_attack_held:
            self.target_scale = 0.8  # Smaller when attacking
            self.current_crosshair = self.crosshair_attack
        else:
            self.target_scale = 1.0  # Normal size
            self.current_crosshair = self.crosshair_normal
        
        # Smooth scaling animation
        self.crosshair_scale += (self.target_scale - self.crosshair_scale) * 0.2
        
        # Ensure we don't get stuck in between values
        if abs(self.crosshair_scale - self.target_scale) < 0.01:
            self.crosshair_scale = self.target_scale
            
    def update_crosshair_particles(self, dt):
        # Update existing particles
        for particle in self.crosshair_particles[:]:
            particle['time'] += dt
            particle['alpha'] = int(255 * (1 - (particle['time'] / self.particle_lifetime)))
            if particle['time'] >= self.particle_lifetime:
                self.crosshair_particles.remove(particle)
        
        # Spawn new particles
        self.particle_spawn_timer += dt
        if self.particle_spawn_timer >= self.particle_spawn_interval:
            self.particle_spawn_timer = 0
            mouse_pos = pygame.mouse.get_pos()
            
            # Add some randomness to position
            offset = pygame.math.Vector2(
                random.uniform(-10, 10),
                random.uniform(-10, 10)
            )

            self.crosshair_particles.append({
                'pos': pygame.math.Vector2(mouse_pos[0] + offset.x, mouse_pos[1] + offset.y),
                'time': 0,
                'alpha': 255,
                'radius': random.uniform(1, 3),
                'color': random.choice(self.particle_colors),
                'velocity': pygame.math.Vector2(
                    random.uniform(-20, 20),
                    random.uniform(5, 15))  # slight downward drift
            })
            
    def add_light_source(self, x, y, radius, intensity=255):
        self.light_sources.append({
            'pos': (x, y),
            'radius': radius,
            'intensity': intensity
        })
        
    def get_light_texture(self, radius, max_alpha):
        key = (radius, max_alpha)
        if key not in self.light_cache:
            # Create and cache light surface
            texture = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            for r in range(radius, 0, -1):
                alpha = int(max_alpha * (r/radius))
                pygame.draw.circle(texture, (0,0,0,alpha), (radius, radius), r)
            self.light_cache[key] = texture
        return self.light_cache[key]

    def reset_to_first_room(self):
        """Reset game to first room"""
        self.dungeon.current_room_index = 0
        self.dungeon._setup_current_room_connections()
        
        # Get spawn position from dungeon
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        self.player.set_position(spawn_x, spawn_y)
        
        # Reset camera
        self.camera_x = spawn_x - self.width // 2
        self.camera_y = spawn_y - self.height // 2
    



    def _update_camera(self):
        player_center_x = self.player.x + self.player.size // 2
        player_center_y = self.player.y + self.player.size // 2

        viewport_width = self.width / self.zoom
        viewport_height = self.height / self.zoom

        # Target camera pos centered on player
        target_camera_x = player_center_x - viewport_width / 2
        target_camera_y = player_center_y - viewport_height / 2

        room = self.dungeon.get_current_room()

        # Clamp only if room is larger than viewport, otherwise center room
        if room.width > viewport_width:
            min_camera_x = room.x
            max_camera_x = room.x + room.width - viewport_width
            target_camera_x = max(min_camera_x, min(target_camera_x, max_camera_x))
        else:
            target_camera_x = room.x + (room.width - viewport_width) / 2

        if room.height > viewport_height:
            min_camera_y = room.y
            max_camera_y = room.y + room.height - viewport_height
            target_camera_y = max(min_camera_y, min(target_camera_y, max_camera_y))
        else:
            target_camera_y = room.y + (room.height - viewport_height) / 2

        # Smooth move camera
        self.camera_x += (target_camera_x - self.camera_x) * self.camera_smoothing
        self.camera_y += (target_camera_y - self.camera_y) * self.camera_smoothing

    def run_pause_menu(self):
        self.is_paused = True  # Ativa flag de pausa
        self.pause_start_time = pygame.time.get_ticks()  # Registra o início do pause

        # Only set up cooldown variable, but do not check/set it when opening
        if not hasattr(self, '_global_pause_cooldown'):
            self._global_pause_cooldown = 0.0
        cooldown_time = 1.5  # seconds
        current_time = pygame.time.get_ticks() / 1000.0
        self.render(do_flip=True)  # render + swap buffers
        pygame.display.flip()      # ensure front buffer is visible
        background_snapshot = self.screen.copy()

        # Create buttons
        from main import run_settings_menu
        button_resume = Button("Resume", (self.width//2 - 150, self.height//2 - 100, 300, 60), action=None)
        button_settings = Button("Settings", (self.width//2 - 150, self.height//2 - 20, 300, 60), action=None)
        button_quit = Button("Quit", (self.width//2 - 150, self.height//2 + 60, 300, 60), action=None)
        buttons = [button_resume, button_settings, button_quit]
        selected_index = 0

        def resume():
            nonlocal running_pause, animating_out, animation_time
            animating_out = True
            animation_time = 0.0

        def open_settings():
            # Run settings menu, then return to pause menu
            run_settings_menu(background_snapshot)

        def quit_game():
            nonlocal running_pause, animating_out, animation_time
            self.running = False
            animating_out = True
            animation_time = 0.0

        button_resume.action = resume
        button_settings.action = open_settings
        button_quit.action = quit_game

        running_pause = True
        animating_in = True
        animating_out = False
        animation_time = 0.0
        animation_duration = 3.0  # seconds
        bounce_height = 40
        overlay_alpha = 100

        # Create overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))

        # Pause text
        font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 72)
        text_surf = font.render("I I", True, (255, 255, 255))
        blurred_text_surf = blur_surface(text_surf, iterations=2)
        text_rect = blurred_text_surf.get_rect(center=(self.width//2, self.height//2 - 150))

        pygame.mouse.set_visible(False)  # Always hide system cursor
        mouse_active = False

        def ease_out_cubic(t):
            # t in [0,1]
            return 1 - pow(1 - t, 3)

        def get_anim_y(start_y, end_y, t, bounce=True):
            # t in [0,1]
            # Use ease-out cubic for slide effect
            eased = ease_out_cubic(t)
            return start_y + (end_y - start_y) * eased

        # Initial positions
        menu_top_y = -self.height
        menu_final_y = 0
        text_final_y = self.height//2 - 150
        button_offsets = [self.height//2 - 100, self.height//2 - 20, self.height//2 + 60]

        while running_pause:
            # Update crosshair and particles (dt from clock)
            self.dt = self.clock.get_time() / 1000.0
            self.update_crosshair(self.dt)
            self.update_crosshair_particles(self.dt)
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    running_pause = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Only allow ESC if not animating in/out
                        if not animating_in and not animating_out:
                            animating_out = True
                            animation_time = 0.0
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_index = (selected_index + 1) % len(buttons)
                        mouse_active = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected_index = (selected_index - 1) % len(buttons)
                        mouse_active = False
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if not animating_in and not animating_out:
                            buttons[selected_index].action()
                elif event.type == pygame.MOUSEMOTION:
                    prev_selected = selected_index
                    mouse_active = True
                    # Only update selected_index if mouse is over a different button
                    for i, button in enumerate(buttons):
                        if button.rect.collidepoint(mouse_pos):
                            if i != selected_index:
                                selected_index = i
                            break
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if not animating_in and not animating_out:
                        for i, button in enumerate(buttons):
                            if button.rect.collidepoint(mouse_pos):
                                selected_index = i
                                button.action()

            # Animation logic
            if animating_in:
                animation_time += self.dt
                t = min(animation_time / animation_duration, 1.0)
                menu_y = get_anim_y(menu_top_y, menu_final_y, t, bounce=False)
                text_y = get_anim_y(menu_top_y + text_final_y, text_final_y, t, bounce=False)
                button_ys = [get_anim_y(menu_top_y + b, b, t, bounce=False) for b in button_offsets]
                if t >= 1.0:
                    animating_in = False
            elif animating_out:
                animation_time += self.dt
                t = min(animation_time / animation_duration, 1.0)
                menu_y = get_anim_y(menu_final_y, menu_top_y, t, bounce=False)
                text_y = get_anim_y(text_final_y, menu_top_y + text_final_y, t, bounce=False)
                button_ys = [get_anim_y(b, menu_top_y + b, t, bounce=False) for b in button_offsets]
                if t >= 1.0:
                    running_pause = False
                    self.is_paused = False  # Desativa flag de pausa ao sair do menu
                    pause_duration = pygame.time.get_ticks() - self.pause_start_time
                    self.clock.tick()  # Reseta o clock
                    # Set global cooldown only after closing menu
                    self._global_pause_cooldown = pygame.time.get_ticks() / 1000.0 + cooldown_time
                    return pause_duration

            else:
                menu_y = menu_final_y
                text_y = text_final_y
                button_ys = button_offsets

            # Draw the snapshot of the game scene
            self.screen.blit(background_snapshot, (0, 0))

            # Draw overlay with animated Y
            overlay_y = int(menu_y)
            self.screen.blit(overlay, (0, overlay_y))

            # Draw thick white line at the bottom of the pause menu
            line_y = overlay_y + self.height  # 20px from bottom of overlay
            pygame.draw.line(
                self.screen,
                (255, 255, 255),
                (0, line_y),
                (self.width, line_y),
                8  # thickness in pixels
            )

            # Draw pause text with animated Y
            text_rect_anim = blurred_text_surf.get_rect(center=(self.width//2, int(text_y)))
            self.screen.blit(text_surf, text_rect_anim)

            # Draw buttons with selection logic and animated Y
            for i, button in enumerate(buttons):
                # If mouse_active, highlight selected_index unless mouse is over another button
                if mouse_active:
                    is_selected = (i == selected_index)
                else:
                    is_selected = (i == selected_index)
                # Draw at animated Y
                button_rect = button.rect.copy()
                button_rect.y = int(button_ys[i])
                button.rect = button_rect
                button.draw(self.screen, mouse_pos, selected=is_selected)
            # Restore button rects after drawing
            for i, button in enumerate(buttons):
                button.rect.y = button_offsets[i]

            # Draw crosshair particles
            for particle in self.crosshair_particles:
                particle['pos'] += particle['velocity'] * self.dt
                particle_surface = pygame.Surface((particle['radius']*2, particle['radius']*2), pygame.SRCALPHA)
                color_with_alpha = (*particle['color'], particle['alpha'])
                pygame.draw.circle(
                    particle_surface, 
                    color_with_alpha, 
                    (particle['radius'], particle['radius']), 
                    particle['radius'])
                self.screen.blit(
                    particle_surface,
                    (particle['pos'].x - particle['radius'],
                    particle['pos'].y - particle['radius']))

            # Draw custom crosshair at mouse position (pause menu)
            crosshair_img = self.current_crosshair if hasattr(self, 'current_crosshair') else None
            crosshair_offset = self.crosshair_offset if hasattr(self, 'crosshair_offset') else (0, 0)
            if crosshair_img:
                self.screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))

            pygame.display.flip()



    def cut_radial_light(self, surface, center, radius, max_alpha=255, wall_rects=None, light_color=(255, 255, 255)):
        """Enhanced lighting with raycasting and performance optimizations"""
        # Performance settings
        PERFORMANCE_MODE = "balanced"  # "fast", "balanced", "quality"

        # Convert parameters for the lighting system
        px, py = center
        color = light_color if light_color else (255, 255, 255)

        # Convert wall rects from world space to surface space if needed
        processed_walls = []
        if wall_rects:
            for wall in wall_rects:
                wall_x = wall.x - self.camera_x
                wall_y = wall.y - self.camera_y
                processed_walls.append(pygame.Rect(wall_x, wall_y, wall.width, wall.height))

        # Cache rendered volumetric light textures
        if not hasattr(self, '_volumetric_light_cache'):
            self._volumetric_light_cache = {}
        # Use a tuple of (radius, max_alpha, color, tuple of wall rects) as cache key
        wall_hash = tuple((w.x, w.y, w.width, w.height) for w in processed_walls) if processed_walls else None
        cache_key = (radius, max_alpha, color, wall_hash)
        if cache_key not in self._volumetric_light_cache:
            light_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            render_volumetric_light(
                light_surface,
                radius, radius,
                radius=radius,
                color=color,
                breathing_intensity=0.1,
                flicker_intensity=0.05,
                wall_rects=processed_walls,
                performance_mode=PERFORMANCE_MODE
            )
            self._volumetric_light_cache[cache_key] = light_surface
        else:
            light_surface = self._volumetric_light_cache[cache_key]

        surface.blit(light_surface, (px - radius, py - radius), special_flags=pygame.BLEND_RGBA_SUB)

    def calculate_dirty_rects(self):
        """Calculate areas that need redrawing"""
        dirty_rects = []
        
        # Player movement area
        player_rect = pygame.Rect(
            self.player.x - self.camera_x - 50,
            self.player.y - self.camera_y - 50,
            100, 100
        )
        dirty_rects.append(player_rect)
        
        # Add UI area
        dirty_rects.append(pygame.Rect(0, 0, 200, 100))  # UI area
        
        return dirty_rects

    def run(self):
        self.run_intro_cutscene()
        self.tutorial_step = 0
        self.tutorial_phrases = [
            "WASD to move, Shift to sprint.",
            "Press E to pick up weapon, Q to drop."
        ]

        accumulated_pause_time = 0  # Tempo total gasto em pausas
        
        while self.running:
            # --- PAUSE LOGIC ---
            # If PowerUpMenu is active, pause game updates and only process menu events/draw
            if hasattr(self, 'powerup_menu') and self.powerup_menu and self.powerup_menu.active:
                # Block all game updates except menu
                self.dt = self.clock.get_time() / 1000.0
                self.update_crosshair(self.dt)
                self.update_crosshair_particles(self.dt)
                mouse_pos = pygame.mouse.get_pos()
                for event in pygame.event.get():
                    self.powerup_menu.handle_event(event)
                self.render()
                pygame.time.wait(16)  # ~60 FPS
                continue
            # Se estiver em pause, não atualize nada
            if self.is_paused:
                pygame.time.wait(100)  # Reduz consumo de CPU
                continue
            # Handle eventos (inclui verificação de pause)
            self.handle_events()
            # Atualiza o jogo com dt ajustado
            dt = self.clock.tick(144) / 1000.0
            self.update(dt)
            self.render()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.run_pause_menu()
                elif event.key == pygame.K_F3:
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_F4:
                    self.show_collision_rects = not self.show_collision_rects
                elif event.key == pygame.K_SPACE:
                    # Advance tutorial if active
                    if hasattr(self, 'tutorial_step') and self.tutorial_step < len(self.tutorial_phrases):
                        self.tutorial_step += 1

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_attack_held = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse_attack_held = False

    def update(self, dt):
        if getattr(self, "in_cutscene", False):
            # still update lightweight things the cutscene expects (optional)
            return

        # Não atualiza nada se estiver pausado
        if self.is_paused:
            return
            
        self.dt = dt  # Atualiza o delta time global
        current_room = self.dungeon.get_current_room()
        current_index = self.dungeon.current_room_index
        adjacent_rooms = self.dungeon.get_adjacent_rooms(current_index)

        # Atualizações do jogador
        self.player.update(rooms=adjacent_rooms, dt=dt, enemies=self.enemies)

        # --- PLAYER DEATH CHECK ---
        if self.player.health <= 0:
            self.run_game_over_screen()
            if not self.running:
                return
            # Restart floor and restore player stats
            self.reset_to_first_room()
            self.player.health = self.player.max_health
            self.player.display_health = self.player.max_health
            self.player.stamina = self.player.max_stamina
            self.player.display_stamina = self.player.max_stamina
            self.projectiles.clear()
            return
        

        # --- UPDATE ENEMIES ---
        for enemy in self.enemies:
            enemy.update(dt, player_pos=(self.player.x, self.player.y), 
                         other_enemies=self.enemies, player=self.player)

        # --- UPDATE STARDUSTS ---
        for stardust in self.stardusts[:]:
            stardust.update(dt, self.player)
            if stardust.collected:
                stardust_manager.add_stardust(stardust.amount)
                self.stardusts.remove(stardust)

        # --- POWER-UP MENU TRIGGER ---
        # Se todas as salas estiverem limpas de inimigos, desce para o próximo andar
        all_rooms_cleared = all(
            hasattr(room, 'enemies') and len(room.enemies) == 0
            for room in self.dungeon.rooms.values()
        )
        if all_rooms_cleared:
            self.descend_floor()
        else:
            # If all enemies in the room are cleared and menu not already active, show power-up menu
            if hasattr(self, 'powerup_menu') and self.powerup_menu and self.powerup_menu.active:
                # Handle menu events and drawing in main loop
                pass
            else:
                room_id = getattr(self.room, 'id', self.dungeon.current_room_index)
                if self.dungeon.current_room_index > 0 and len(self.enemies) == 0 and room_id not in self.powerup_menu_shown_rooms:
                    # Get available power-ups (example: from trees)
                    from game.powerups.power_up import PowerUpTree, poison1, poison2, poison3, poison4, poison5, fire1, fire2, fire3, fire4, fire5
                    from game.powerups.power_up_menu import PowerUpMenu
                    # Example: build a list of trees and get next tier for each theme
                    trees = [PowerUpTree('Poison'), PowerUpTree('Fire')]
                    trees[0].add_powerup(poison1)
                    trees[0].add_powerup(poison2)
                    trees[0].add_powerup(poison3)
                    trees[0].add_powerup(poison4)
                    trees[0].add_powerup(poison5)
                    
                    trees[1].add_powerup(fire1)
                    trees[1].add_powerup(fire2)
                    trees[1].add_powerup(fire3)
                    trees[1].add_powerup(fire4)
                    trees[1].add_powerup(fire5)
                    available = []
                    for tree in trees:
                        tier = self.player.get_powerup_tier(tree.theme)
                        available += tree.get_available_powerups(tier)
                    # Pick 3 random available power-ups
                    choices = random.sample(available, min(3, len(available)))
                    if choices:
                        self.powerup_menu = PowerUpMenu(choices, self.player, lambda p: self.player.apply_powerup(p))
                        self.powerup_menu_shown_rooms.add(room_id)

        # update room based on player position (bounding box detection)
        prev_room_index = self.dungeon.current_room_index
        self.dungeon.update_player_room(self.player.rect)
        if self.dungeon.current_room_index != prev_room_index:
            # Track previous room index
            self.previous_room_index = prev_room_index
            for o in self.dungeon.opening_positions:
                print("   ", o)
            self.room = self.dungeon.get_current_room()
            self.enemies = getattr(self.room, 'enemies', []) if hasattr(self.room, 'enemies') else []

        # update camera to follow player
        self._update_camera()
        self.update_crosshair(dt)
        self.update_crosshair_particles(dt)

        # --- UPDATE PROJECTILES ---
        if self.mouse_attack_held:
            self.player.attack(
                self.camera_x,
                self.camera_y,
                self.zoom,
                self.projectiles,
                self.enemies,
            )

        # Get wall rects for the current room
        wall_rects = current_room.get_wall_rects() if hasattr(current_room, 'get_wall_rects') else []
        # Get room boundary as a pygame.Rect
        room_rect = pygame.Rect(current_room.x, current_room.y, current_room.width, current_room.height)
        for proj in self.projectiles[:]:
            # ADD PAUSE CHECK HERE
            if not self.is_paused:
                proj.update(self.dt, self.enemies, wall_rects, room_rect)
            if not getattr(proj, 'is_alive', True):
                self.projectiles.remove(proj)
                
        # --- UPDATE ENEMIES ---
        for enemy in self.enemies:
            enemy.engine = self  # Ensure each enemy can access engine context
            # Enemy.update already has a pause check

    def cut_radial_light(self, surface, center, radius, max_alpha=255, wall_rects=None, light_color=(255, 255, 255)):
        """Enhanced lighting with raycasting and performance optimizations"""
        # Performance settings
        PERFORMANCE_MODE = "balanced"  # "fast", "balanced", "quality"

        # Convert parameters for the lighting system
        px, py = center
        color = light_color if light_color else (255, 255, 255)

        # Convert wall rects from world space to surface space if needed
        processed_walls = []
        if wall_rects:
            for wall in wall_rects:
                wall_x = wall.x - self.camera_x
                wall_y = wall.y - self.camera_y
                processed_walls.append(pygame.Rect(wall_x, wall_y, wall.width, wall.height))

        # Cache light_surface per radius
        if not hasattr(self, '_light_surface_cache'):
            self._light_surface_cache = {}
        cache_key = (radius, max_alpha)
        if cache_key not in self._light_surface_cache or self._light_surface_cache[cache_key].get_size() != (radius*2, radius*2):
            self._light_surface_cache[cache_key] = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        light_surface = self._light_surface_cache[cache_key]
        light_surface.fill((0, 0, 0, 0))  # Clear before rendering

        render_volumetric_light(
            light_surface,
            radius, radius,
            radius=radius,
            color=color,
            breathing_intensity=0.1,
            flicker_intensity=0.05,
            wall_rects=processed_walls,
            performance_mode=PERFORMANCE_MODE
        )

        surface.blit(light_surface, (px - radius, py - radius), special_flags=pygame.BLEND_RGBA_SUB)



    def render(self, skip_ui=False, do_flip=True, ui_alpha=255):
        # Room surface caching
        current_room = self.dungeon.get_current_room()
        current_index = self.dungeon.current_room_index
        adjacent_rooms = self.dungeon.get_adjacent_rooms(current_index)
        rooms_to_render = [current_room] + adjacent_rooms

        # Create or reuse a virtual surface for zoomed rendering if needed
        if abs(self.zoom - 1.0) > 0.05:
            virtual_width = int(self.width / self.zoom)
            virtual_height = int(self.height / self.zoom)
            if self.virtual_surface is None or self.virtual_surface.get_size() != (virtual_width, virtual_height):
                self.virtual_surface = pygame.Surface((virtual_width, virtual_height))
            virtual_surface = self.virtual_surface
            virtual_surface.fill((0, 0, 0))
        else:
            virtual_surface = self.screen
            virtual_width = self.width
            virtual_height = self.height

        # Render all rooms (current and adjacent)
        current_room.render(virtual_surface, self.camera_x, self.camera_y, 
                show_collision_rects=self.show_collision_rects)
        # for room in rooms_to_render:
        #     room.render(virtual_surface, self.camera_x, self.camera_y, 
        #             show_collision_rects=self.show_collision_rects)


        # --- RENDER ENEMIES IN CURRENT ROOM ---
        enemies = getattr(current_room, 'enemies', []) if hasattr(current_room, 'enemies') else []
        for enemy in enemies:
            enemy.draw(virtual_surface, self.camera_x, self.camera_y)

        # --- RENDER STARDUSTS ---
        for stardust in self.stardusts:
            stardust.draw(virtual_surface, self.camera_x, self.camera_y, rooms=rooms_to_render)

        # Render the player
        if not (hasattr(self.player, 'is_dead') and self.player.is_dead and \
                self.player.death_timer >= self.player.death_duration):
            self.player.render(
                virtual_surface,
                self.camera_x,
                self.camera_y,
                rooms_to_render,
                zoom=self.zoom,
                show_collision_rects=self.show_collision_rects
            )

        # If player is dead and death animation is playing, update it
        if hasattr(self.player, 'is_dead') and self.player.is_dead:
            self.player.update_death_animation(self.dt)

        # --- RENDER PROJECTILES ---
        for proj in self.projectiles:
            proj.render(virtual_surface, self.camera_x, self.camera_y, self.zoom)

        # --- DARKNESS OVERLAY ---
        # Allocate once and reuse
        if self.darkness_overlay is None or self.darkness_overlay.get_size() != (virtual_width, virtual_height):
            self.darkness_overlay = pygame.Surface((virtual_width, virtual_height), pygame.SRCALPHA)

        darkness_overlay = self.darkness_overlay
        darkness_overlay.fill((0, 0, 0, 255))  # Fully opaque black

        for light in self.light_sources:
            light_x = light['pos'][0] - self.camera_x
            light_y = light['pos'][1] - self.camera_y
            self.cut_radial_light(
                darkness_overlay,
                (light_x, light_y),
                light['radius'],
                light['intensity']
            )

        floor_screen_rect = pygame.Rect(
            current_room.x - self.camera_x,
            current_room.y - self.camera_y,
            current_room.width,
            current_room.height
        )

        # Update cached wall_rects and room_rect only if room changed
        room_id = getattr(current_room, 'id', id(current_room))
        if not hasattr(self, '_last_room_id') or self._last_room_id != room_id:
            self._last_room_id = room_id
            self.current_wall_rects = [pygame.Rect(wall.x, wall.y, wall.width, wall.height) for wall in current_room.get_wall_rects()]
            self.current_room_rect = pygame.Rect(current_room.x, current_room.y, current_room.width, current_room.height)
        wall_rects = [pygame.Rect(
            rect.x - self.camera_x,
            rect.y - self.camera_y,
            rect.width,
            rect.height
        ) for rect in self.current_wall_rects]

        if wall_rects:
            union_rect = wall_rects[0].unionall(wall_rects[1:])
            darkness_overlay.fill((0, 0, 0, 0), union_rect)

        player_center_x = int(self.player.x - self.camera_x + self.player.size // 2)
        player_center_y = int(self.player.y - self.camera_y + self.player.size // 2)
        player_center = (player_center_x, player_center_y)
        light_radius = 130
        self.cut_radial_light(darkness_overlay, player_center, 100)

        # Apply darkness overlay to scene
        virtual_surface.blit(darkness_overlay, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        # --- Dirty rect rendering ---
        if abs(self.zoom - 1.0) > 0.05:
            scaled_surface = pygame.transform.scale(virtual_surface, (self.width, self.height))
            self.screen.blit(scaled_surface, (0, 0))
        else:
            self.screen.blit(virtual_surface, (0, 0))

        # ---- UI (only when skip_ui is False) ----
        if not skip_ui:
            ui_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            self.dungeon.render_ui(ui_surface)
            self.player.render_bars(ui_surface, ui_surface.get_height())
            self.player.render_weapon_hud(ui_surface, ui_surface.get_width(), ui_surface.get_height())
            self.player.render_weapon_info_overlay(ui_surface, self.camera_x, self.camera_y, self.room, self.zoom)

            for particle in self.crosshair_particles:
                particle['pos'] += particle['velocity'] * getattr(self, 'dt', 0.0)
                color_with_alpha = (*particle['color'], particle['alpha'])
                pygame.draw.circle(
                    ui_surface,
                    color_with_alpha,
                    (int(particle['pos'].x), int(particle['pos'].y)),
                    int(particle['radius'])
                )

            mouse_pos = pygame.mouse.get_pos()
            if abs(self.crosshair_scale - 1.0) > 0.01:
                scaled_size = (int(self.current_crosshair.get_width() * self.crosshair_scale), 
                            int(self.current_crosshair.get_height() * self.crosshair_scale))
                scaled_crosshair = pygame.transform.scale(self.current_crosshair, scaled_size)
                offset = (scaled_size[0] // 2, scaled_size[1] // 2)
                ui_surface.blit(scaled_crosshair, 
                                (mouse_pos[0] - offset[0], 
                                mouse_pos[1] - offset[1]))
            else:
                ui_surface.blit(self.current_crosshair, 
                                (mouse_pos[0] - self.crosshair_offset[0], 
                                mouse_pos[1] - self.crosshair_offset[1]))

            # Draw power-up menu if active
            if hasattr(self, 'powerup_menu') and self.powerup_menu and self.powerup_menu.active:
                self.powerup_menu.draw(ui_surface)

            if self.show_fps:
                fps = self.clock.get_fps()
                playerPos = self.player.x, self.player.y
                fps_text = self.fps_font.render(f"FPS: {fps:.1f}", True, (255, 255, 0))
                playerPos_text = self.fps_font.render(f"Player Pos: {playerPos}", True, (255, 255, 0))
                ui_surface.blit(fps_text, (10, self.screen.get_height() - fps_text.get_height() - 10))
                ui_surface.blit(playerPos_text, (10,  self.screen.get_height() - fps_text.get_height() - 30))

            if hasattr(self, 'tutorial_step') and self.tutorial_step < len(self.tutorial_phrases):
                tutorial_text = self.tutorial_phrases[self.tutorial_step]
                font_tip = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 22)
                font_space = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 18)
                tip_surf = font_tip.render(tutorial_text, True, (255, 255, 255))
                space_surf = font_space.render("Press SPACE for next tip", True, (200, 200, 200))
                px = int((self.player.x - self.camera_x + self.player.size // 2) * self.zoom)
                py = int((self.player.y - self.camera_y + self.player.size) * self.zoom)
                tip_rect = tip_surf.get_rect(center=(px, py + int(22 * self.zoom)))
                space_rect = space_surf.get_rect(center=(px, tip_rect.bottom + int(14 * self.zoom)))
                ui_surface.blit(tip_surf, tip_rect)
                ui_surface.blit(space_surf, space_rect)

            if ui_alpha < 255:
                tmp = ui_surface.copy()
                tmp.set_alpha(ui_alpha)
                self.screen.blit(tmp, (0, 0))
            else:
                self.screen.blit(ui_surface, (0, 0))

        # --- only flip / update when requested ---
        if do_flip:
            pygame.display.flip()

    def run_intro_cutscene(self, floor_number=1, message="Prepare for the journey ahead...", post_delay=0.6, overlay_fade_duration=0.5):
        """Cutscene state machine with overlay fade-out at end.
        Phases: fade_in -> fall -> bounce -> bars_slide -> ui_fade -> post_delay -> overlay_fade_out -> done.
        """
        self.in_cutscene = True

        # Fonts / text
        title_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 72)
        subtitle_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 36)
        if str(floor_number).lower() == "store":
            title = title_font.render("STORE", True, (255, 255, 255))
        else:
            title = title_font.render(f"FLOOR {floor_number}", True, (255, 255, 255))
        subtitle = subtitle_font.render(message, True, (200, 200, 200))

        # starfield (we'll draw stars into overlay surface so they can fade)
        stars = [(random.uniform(0, self.width), random.uniform(0, self.height),
                random.randint(1, 3), random.uniform(0.2, 1.0)) for _ in range(120)]

        # cinematic bars
        start_bar_h = 140.0
        min_bar_h = 60.0

        # spawn & start pos
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        start_y = spawn_y - 900.0
        self.player.x = spawn_x
        self.player.y = start_y

        # initial camera (and force cutscene camera for first frame)
        self.camera_x = self.player.x - self.width // 2
        self.camera_y = self.player.y - self.height // 2
        self._update_camera_cutscene()

        # timings
        fade_duration = 1.2
        fall_duration = 2.2
        landing_bounce_duration = 0.35
        bars_slide_duration = 0.6
        ui_fade_duration = 0.7

        clock = pygame.time.Clock()

        # state machine
        phase = "fade_in"
        phase_start = pygame.time.get_ticks() / 1000.0
        landed = False
        bounce_start = None
        bars_start = None
        ui_fade_start = None
        ui_alpha = 0
        current_bar_h = start_bar_h
        overlay_alpha = 255  # controls full overlay (stars, bars, text) in final fade-out

        while True:
            dt = clock.tick(60) / 1000.0
            self.dt = dt

            # input handling (quit + skip)
            skip = False
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.running = False
                    self.in_cutscene = False
                    return
                elif ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    skip = True

            now = pygame.time.get_ticks() / 1000.0
            phase_t = now - phase_start

            # skip shortcut: jump forward to appropriate phases
            if skip:
                if phase in ("fade_in", "fall", "bounce"):
                    self.player.y = spawn_y
                    landed = True
                    bounce_start = None
                    bars_start = now
                    ui_fade_start = now + 0.12
                    phase = "bars_slide"
                    phase_start = now
                elif phase == "bars_slide":
                    current_bar_h = min_bar_h
                    bars_start = phase_start
                    ui_fade_start = now
                    phase = "ui_fade"
                    phase_start = now
                elif phase == "ui_fade":
                    ui_alpha = 255
                    phase = "post_delay"
                    phase_start = now
                    post_end = now + float(post_delay)
                elif phase == "post_delay":
                    # go straight to overlay fade-out
                    phase = "overlay_fade_out"
                    phase_start = now
                    overlay_start = now

            # --- Phase logic ---
            if phase == "fade_in":
                text_alpha = int(255 * min(1.0, phase_t / fade_duration))
                if phase_t >= fade_duration:
                    phase = "fall"
                    phase_start = now

            elif phase == "fall":
                t = min(1.0, phase_t / fall_duration)
                eased = 1 - (1 - t) ** 3
                self.player.y = start_y + (spawn_y - start_y) * eased
                text_alpha = 255
                if t >= 1.0:
                    phase = "bounce"
                    phase_start = now

            elif phase == "bounce":
                bt = (now - bounce_start) / landing_bounce_duration if bounce_start else 1.0
                if bt < 1.0:
                    overshoot = 24.0
                    damp = math.exp(-4 * bt)
                    self.player.y = spawn_y + overshoot * math.cos(bt * math.pi * 2) * damp
                else:
                    self.player.y = spawn_y
                    phase = "bars_slide"
                    phase_start = now
                    bars_start = now
                    ui_fade_start = now + 0.12
                text_alpha = 255

            elif phase == "bars_slide":
                t = min(1.0, (now - bars_start) / bars_slide_duration)
                slide = 1 - (1 - t) * (1 - t)
                current_bar_h = start_bar_h * (1 - slide) + min_bar_h * slide
                text_alpha = 255
                if t >= 1.0:
                    current_bar_h = min_bar_h
                    phase = "ui_fade"
                    phase_start = now
                    ui_fade_start = now

            elif phase == "ui_fade":
                t = min(1.0, (now - ui_fade_start) / ui_fade_duration) if ui_fade_start else 1.0
                ui_alpha = int(255 * t)
                text_alpha = 255
                if t >= 1.0:
                    phase = "post_delay"
                    phase_start = now
                    post_end = now + float(post_delay)

            elif phase == "post_delay":
                text_alpha = 255
                ui_alpha = 255
                current_bar_h = min_bar_h
                if now >= post_end:
                    phase = "overlay_fade_out"
                    phase_start = now
                    overlay_start = now

            elif phase == "overlay_fade_out":
                # Start music crossfade when overlay fade begins
                t = min(1.0, (now - overlay_start) / overlay_fade_duration)
                overlay_alpha = int(255 * (1.0 - t))
                # keep UI visible underneath
                text_alpha = int(255 * (overlay_alpha / 255))  # text fades with overlay
                ui_alpha = 255
                current_bar_h = min_bar_h
                if t >= 1.0:
                    # overlay fully gone -> done
                    break

            else:
                text_alpha = 255
                ui_alpha = 255

            # --- Camera updates ---
            use_cutscene_camera = phase in ("fade_in", "fall", "bounce", "bars_slide")
            if use_cutscene_camera:
                prev_smooth = getattr(self, "camera_smoothing", 0.1)
                self.camera_smoothing = max(prev_smooth, 0.28)
                self._update_camera_cutscene()
            else:
                self.camera_smoothing = getattr(self, "camera_smoothing", 0.1)
                self._update_camera()

            # apply non-blocking camera shake
            shake_x, shake_y = self._apply_camera_shake(dt)
            cam_x_saved, cam_y_saved = self.camera_x, self.camera_y
            self.camera_x += shake_x
            self.camera_y += shake_y

            # --- Render frame (world + UI if appropriate) ---
            render_ui_now = (phase in ("ui_fade", "post_delay", "overlay_fade_out"))
            ui_alpha_to_pass = ui_alpha if render_ui_now else 0
            self.render(skip_ui=not render_ui_now, do_flip=False, ui_alpha=ui_alpha_to_pass)

            # draw cinematic overlay into a temp surface so we can control overall overlay alpha at the end
            overlay_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)

            # starfield — draw onto overlay_surf
            for (sx, sy, size, depth) in stars:
                px = int((sx - (self.camera_x * 0.2 * depth)) % (self.width + 50))
                py = int((sy - (self.camera_y * 0.2 * depth)) % (self.height + 50))
                pygame.draw.circle(overlay_surf, (220, 220, 255, 255), (px, py), size)

            # cinematic bars on overlay_surf
            pygame.draw.rect(overlay_surf, (0, 0, 0, 255), (0, 0, self.width, int(current_bar_h)))
            pygame.draw.rect(overlay_surf, (0, 0, 0, 255),
                            (0, self.height - int(current_bar_h), self.width, int(current_bar_h)))

            # prepare text surfaces with text_alpha and blit onto overlay_surf
            title.set_alpha(int(max(0, min(255, text_alpha))))
            subtitle.set_alpha(int(max(0, min(255, text_alpha))))
            title_rect = title.get_rect(center=(self.width // 2, self.height // 2 - 40))
            subtitle_rect = subtitle.get_rect(center=(self.width // 2, self.height // 2 + 20))
            overlay_surf.blit(title, title_rect)
            overlay_surf.blit(subtitle, subtitle_rect)

            # Now apply overlay_alpha if we're in overlay_fade_out; for earlier phases overlay_alpha == 255
            if overlay_alpha < 255:
                tmp = overlay_surf.copy()
                tmp.set_alpha(overlay_alpha)
                self.screen.blit(tmp, (0, 0))
            else:
                # direct blit (already has per-pixel alpha)
                self.screen.blit(overlay_surf, (0, 0))

            # restore camera (remove shake)
            self.camera_x, self.camera_y = cam_x_saved, cam_y_saved

            # single flip per frame
            pygame.display.flip()

        # final cleanup: ensure exact final frame and release cutscene lock
        self._update_camera()
        self.render(skip_ui=False, do_flip=True, ui_alpha=255)
        pygame.display.flip()
        pygame.event.pump()
        self.in_cutscene = False
        # Reset music blend flag for next cutscene
        if hasattr(self, '_music_blend_started'):
            del self._music_blend_started



    def _start_camera_shake(self, duration, intensity):
        """Start a non-blocking camera shake (frames apply via _apply_camera_shake)."""
        self._camera_shake_timer = duration
        self._camera_shake_intensity = intensity

    def _apply_camera_shake(self, dt):
        """Return (offset_x, offset_y) for current shake state and decrease timer."""
        if getattr(self, "_camera_shake_timer", 0.0) > 0.0:
            self._camera_shake_timer -= dt
            intensity = getattr(self, "_camera_shake_intensity", 0)
            # decaying intensity
            t = max(0.0, self._camera_shake_timer)
            decay = t / (t + 0.0001)  # simple decay factor
            ang = random.random() * math.tau
            ox = int(math.cos(ang) * intensity * decay)
            oy = int(math.sin(ang) * intensity * decay)
            return ox, oy
        return 0, 0

    def _update_camera_cutscene(self, smoothing=None):
        """Center camera on player without room-clamping (used only during cutscene)."""
        player_center_x = self.player.x + self.player.size // 2
        player_center_y = self.player.y + self.player.size // 2

        viewport_width = self.width / self.zoom
        viewport_height = self.height / self.zoom

        target_camera_x = player_center_x - viewport_width / 2
        target_camera_y = player_center_y - viewport_height / 2

        if smoothing is None:
            smoothing = max(0.05, min(0.5, getattr(self, "camera_smoothing", 0.1) * 2.5))

        # smooth-damp toward target
        self.camera_x += (target_camera_x - self.camera_x) * smoothing
        self.camera_y += (target_camera_y - self.camera_y) * smoothing

    # Persistent virtual surface for zoomed rendering
    def run_game_over_screen(self):
        """Show a game over overlay and wait for player to restart the floor or quit."""
        overlay_alpha = 160
        animation_time = 0.0
        animation_duration = 1.2  # seconds for fade-in
        running_game_over = True
        button_restart = Button("Restart Floor", (self.width//2 - 150, self.height//2 + 40, 300, 60), action=None)
        button_quit = Button("Quit", (self.width//2 - 150, self.height//2 + 120, 300, 60), action=None)
        buttons = [button_restart, button_quit]
        selected_index = 0
        self.game_over_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 64)
        text_surf = self.game_over_font.render("GAME OVER", True, (255, 60, 60))
        text_rect = text_surf.get_rect(center=(self.width//2, self.height//2 - 80))
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))
        mouse_active = False
        pygame.mouse.set_visible(False)

        def restart():
            nonlocal running_game_over
            running_game_over = False
            # Fully reload the game by restarting the process

        def quit_game():
            nonlocal running_game_over
            self.running = False
            running_game_over = False

        button_restart.action = restart
        button_quit.action = quit_game

        while running_game_over and self.running:
            self.dt = self.clock.get_time() / 1000.0
            self.update_crosshair(self.dt)
            self.update_crosshair_particles(self.dt)
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    running_game_over = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        buttons[selected_index].action()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected_index = (selected_index + 1) % len(buttons)
                        mouse_active = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected_index = (selected_index - 1) % len(buttons)
                        mouse_active = False
                elif event.type == pygame.MOUSEMOTION:
                    for i, button in enumerate(buttons):
                        if button.rect.collidepoint(mouse_pos):
                            selected_index = i
                            mouse_active = True
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, button in enumerate(buttons):
                        if button.rect.collidepoint(mouse_pos):
                            selected_index = i
                            button.action()
            # Proper fade calculation
            animation_time += self.dt
            fade = min(1.0, animation_time / animation_duration)

            # Draw last frame as background (optional: could use a snapshot)
            self.render(do_flip=False)
            # Overlay
            overlay.set_alpha(int(overlay_alpha * fade))
            self.screen.blit(overlay, (0, 0))
            # Game Over text
            text_surf.set_alpha(int(255 * fade))
            self.screen.blit(text_surf, text_rect)
            # Draw buttons
            for i, button in enumerate(buttons):
                is_selected = (i == selected_index)
                button.draw(self.screen, mouse_pos, selected=is_selected)
            # Crosshair
            crosshair_img = self.current_crosshair if hasattr(self, 'current_crosshair') else None
            crosshair_offset = self.crosshair_offset if hasattr(self, 'crosshair_offset') else (0, 0)
            if crosshair_img:
                self.screen.blit(crosshair_img, (mouse_pos[0] - crosshair_offset[0], mouse_pos[1] - crosshair_offset[1]))
            pygame.display.flip()

        # After leaving, reset mouse visibility
        pygame.mouse.set_visible(True)
    # Track previous room index for rendering
    def __init__(self, screen, width=800, height=600, title="Dungeon Crawler", fullscreen=True):
        self.mouse_attack_held = False  # Track if mouse attack button is held
        
        # Configurar fullscreen
        if fullscreen:
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            self.screen = screen
        else:
            self.width = width
            self.height = height
            self.screen = screen
            
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.previous_room_index = None
        self.powerup_menu_shown_rooms = set()
        
        # Light sources
        self.light_sources = []  # Track all light sources
        self.light_cache = {} # Cache for light textures

        # Câmera/viewport
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.3
        self.camera_smoothing = 0.1

        # Track previous room index for rendering
        self.previous_room_index = None

        # Criar o dungeon
        self.dungeon = Dungeon(tile_size=20, total_rooms=25, branching_factor=3)
        
        # Obter a sala atual
        self.room = self.dungeon.get_current_room()
        # Cache for wall rects per room
        self._room_wall_rect_cache = {}
        # Cached wall rects and room rect for current room
        self.current_wall_rects = None
        self.current_room_rect = None

        # Get spawn position from dungeon
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        self.player = Player(spawn_x, spawn_y)
        self.dungeon.player = self.player

        # Initialize camera
        self.camera_x = spawn_x - self.width // 2
        self.camera_y = spawn_y - self.height // 2

        # FPS monitor
        self.show_fps = False
        self.fps_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 32)

        # Collision rects debug
        self.show_collision_rects = False

        # --- GLOBAL PROJECTILES LIST ---
        if not hasattr(builtins, 'projectiles') or not isinstance(builtins.projectiles, list):
            builtins.projectiles = []
        self.projectiles = builtins.projectiles

        # Persistent darkness overlay surface (for performance)
        self.virtual_surface = None
        self.darkness_overlay = None

        # Crosshair particles
        self.crosshair_particles = []
        self.particle_spawn_timer = 0
        self.particle_spawn_interval = 0.05  # seconds between particles
        self.particle_lifetime = 0.5  # seconds
        self.particle_colors = [
            (255, 255, 255),  # white
            (230, 230, 255),  # light blue-white
            (255, 230, 230)   # light pink-white
        ]

        # Load crosshair sprite
        try:
            self.crosshair_normal = get_image("crosshair_normal", "game/assets/sprites/ui/cursor/cursor.png")
            self.crosshair_attack = get_image("crosshair_attack", "game/assets/sprites/ui/cursor/cursor_attack.png")
            # Scale if needed (example scales to 16x16)
            size = (16, 16)
            if self.crosshair_normal:
                self.crosshair_normal = pygame.transform.scale(self.crosshair_normal, size)
            if self.crosshair_attack:
                self.crosshair_attack = pygame.transform.scale(self.crosshair_attack, size)
            if not self.crosshair_normal or not self.crosshair_attack:
                raise Exception("Missing crosshair image")
        except:
            # Fallback: create simple crosshairs if images not found
            size = (32, 32)
            self.crosshair_normal = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.line(self.crosshair_normal, (255, 255, 255), (16, 0), (16, 32), 2)
            pygame.draw.line(self.crosshair_normal, (255, 255, 255), (0, 16), (32, 16), 2)
            self.crosshair_attack = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.line(self.crosshair_attack, (255, 0, 0), (16, 0), (16, 32), 3)
            pygame.draw.line(self.crosshair_attack, (255, 0, 0), (0, 16), (32, 16), 3)
            
        # Current crosshair (starts as normal)
        self.current_crosshair = self.crosshair_normal
        self.crosshair_offset = (size[0] // 2, size[1] // 2)
        self.is_paused = False  # Flag para pausar atualizações
        self.pause_start_time = 0  # Armazenará quando o pause começou

            
        # For smooth transitions
        self.crosshair_scale = 1.0
        self.target_scale = 1.0

        self.enemies = []
        self.stardusts = []
        
    def update_crosshair(self, dt):
        """Smoothly transition between crosshair states"""
        if self.mouse_attack_held:
            self.target_scale = 0.8  # Smaller when attacking
            self.current_crosshair = self.crosshair_attack
        else:
            self.target_scale = 1.0  # Normal size
            self.current_crosshair = self.crosshair_normal
        
        # Smooth scaling animation
        self.crosshair_scale += (self.target_scale - self.crosshair_scale) * 0.2
        
        # Ensure we don't get stuck in between values
        if abs(self.crosshair_scale - self.target_scale) < 0.01:
            self.crosshair_scale = self.target_scale
            
    def update_crosshair_particles(self, dt):
        # Update existing particles
        for particle in self.crosshair_particles[:]:
            particle['time'] += dt
            particle['alpha'] = int(255 * (1 - (particle['time'] / self.particle_lifetime)))
            if particle['time'] >= self.particle_lifetime:
                self.crosshair_particles.remove(particle)
        
        # Spawn new particles
        self.particle_spawn_timer += dt
        if self.particle_spawn_timer >= self.particle_spawn_interval:
            self.particle_spawn_timer = 0
            mouse_pos = pygame.mouse.get_pos()
            
            # Add some randomness to position
            offset = pygame.math.Vector2(
                random.uniform(-10, 10),
                random.uniform(-10, 10)
            )

            self.crosshair_particles.append({
                'pos': pygame.math.Vector2(mouse_pos[0] + offset.x, mouse_pos[1] + offset.y),
                'time': 0,
                'alpha': 255,
                'radius': random.uniform(1, 3),
                'color': random.choice(self.particle_colors),
                'velocity': pygame.math.Vector2(
                    random.uniform(-20, 20),
                    random.uniform(5, 15))  # slight downward drift
            })
            
    def add_light_source(self, x, y, radius, intensity=255):
        self.light_sources.append({
            'pos': (x, y),
            'radius': radius,
            'intensity': intensity
        })
        
    def get_light_texture(self, radius, max_alpha):
        key = (radius, max_alpha)
        if key not in self.light_cache:
            # Create and cache light surface
            texture = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            for r in range(radius, 0, -1):
                alpha = int(max_alpha * (r/radius))
                pygame.draw.circle(texture, (0,0,0,alpha), (radius, radius), r)