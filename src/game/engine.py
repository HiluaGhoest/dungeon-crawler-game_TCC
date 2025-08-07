# Engine do jogo
import random
import socket
import threading
import pygame
import math
from game.player import Player
from game.dungeon import Dungeon
from game.util.light import render_volumetric_light
from game.util.ui import Button

class GameEngine:
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

        # Get spawn position from dungeon
        spawn_x, spawn_y = self.dungeon.get_player_spawn_position()
        self.player = Player(spawn_x, spawn_y)
        self.dungeon.player = self.player

        # Initialize camera
        self.camera_x = spawn_x - self.width // 2
        self.camera_y = spawn_y - self.height // 2

        # FPS monitor
        self.show_fps = False
        from game.assets import get_font, get_image
        self.fps_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 32)

        # Collision rects debug
        self.show_collision_rects = False

        # --- GLOBAL PROJECTILES LIST ---
        import builtins
        if not hasattr(builtins, 'projectiles') or not isinstance(builtins.projectiles, list):
            builtins.projectiles = []
        self.projectiles = builtins.projectiles

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
        
        # For smooth transitions
        self.crosshair_scale = 1.0
        self.target_scale = 1.0

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
        # Only set up cooldown variable, but do not check/set it when opening
        if not hasattr(self, '_global_pause_cooldown'):
            self._global_pause_cooldown = 0.0
        cooldown_time = 1.5  # seconds
        current_time = pygame.time.get_ticks() / 1000.0
        background_snapshot = self.screen.copy()

        # Create buttons
        button_resume = Button("Resume", (self.width//2 - 150, self.height//2 - 60, 300, 60), action=None)
        button_quit = Button("Quit", (self.width//2 - 150, self.height//2 + 20, 300, 60), action=None)
        buttons = [button_resume, button_quit]
        selected_index = 0

        def resume():
            nonlocal running_pause, animating_out, animation_time
            animating_out = True
            animation_time = 0.0

        def quit_game():
            nonlocal running_pause, animating_out, animation_time
            self.running = False
            animating_out = True
            animation_time = 0.0

        button_resume.action = resume
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
        from game.util.ui import blur_surface
        font = pygame.font.Font(None, 72)
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
        button_offsets = [self.height//2 - 60, self.height//2 + 20]

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
                    # Set global cooldown only after closing menu
                    self._global_pause_cooldown = pygame.time.get_ticks() / 1000.0 + cooldown_time
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

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Quando apertar ESC, abrir o menu pause
                    self.run_pause_menu()
                elif event.key == pygame.K_F3:
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_F4:
                    self.show_collision_rects = not self.show_collision_rects

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.mouse_attack_held = True
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.mouse_attack_held = False

    def update(self):
        self.dt = self.clock.get_time() / 1000.0  # seconds
        current_index = self.dungeon.current_room_index
        adjacent_rooms = self.dungeon.get_adjacent_rooms(current_index)

        # move player
        self.player.update(rooms=adjacent_rooms)

        # update room based on player position (bounding box detection)
        if self.mouse_attack_held:
            if self.player.attack(self.camera_x, self.camera_y, self.zoom):
                print("Ataque executado!")
        prev_room_index = self.dungeon.current_room_index
        self.dungeon.update_player_room(self.player.rect)
        if self.dungeon.current_room_index != prev_room_index:
            # Track previous room index
            self.previous_room_index = prev_room_index
            print(f"[DEBUG] room_opening_sides for {self.dungeon.current_room_index}:",
                  self.dungeon.room_opening_sides.get(self.dungeon.current_room_index))
            print(f"[DEBUG] opening_positions for room {self.dungeon.current_room_index}:")
            for o in self.dungeon.opening_positions:
                print("   ", o)
            self.room = self.dungeon.get_current_room()

        # update camera to follow player
        self._update_camera()
        self.update_crosshair(self.dt)
        self.update_crosshair_particles(self.dt)

        # --- UPDATE PROJECTILES ---
        if self.mouse_attack_held:
            self.player.attack(
                self.camera_x,
                self.camera_y,
                self.zoom,
                self.projectiles
            )
            
        current_room = self.dungeon.get_current_room()

        enemies = getattr(current_room, 'enemies', []) if hasattr(current_room, 'enemies') else []
        # Get wall rects for the current room
        wall_rects = current_room.get_wall_rects() if hasattr(current_room, 'get_wall_rects') else []
        # Get room boundary as a pygame.Rect
        room_rect = pygame.Rect(current_room.x, current_room.y, current_room.width, current_room.height)
        for proj in self.projectiles[:]:
            proj.update(self.dt, enemies, wall_rects, room_rect)
            if not getattr(proj, 'is_alive', True):
                self.projectiles.remove(proj)
        # --- UPDATE ENEMIES ---
        for enemy in enemies:
            enemy.update()

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
                # Convert to surface coordinates (relative to the darkness overlay)
                wall_x = wall.x - self.camera_x
                wall_y = wall.y - self.camera_y
                processed_walls.append(pygame.Rect(wall_x, wall_y, wall.width, wall.height))
        
        # Create temporary surface for the light
        light_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        
        # Render the volumetric light
        render_volumetric_light(
            light_surface,
            radius, radius,  # Center on our temp surface
            radius=radius,
            color=color,
            breathing_intensity=0.1,
            flicker_intensity=0.05,
            wall_rects=processed_walls,
            performance_mode=PERFORMANCE_MODE
        )
        
        # Subtract the light from darkness (inverse of normal additive blending)
        surface.blit(light_surface, (px - radius, py - radius), 
                    special_flags=pygame.BLEND_RGBA_SUB)



    def render(self):
        # Render the current room and all adjacent rooms
        current_room = self.dungeon.get_current_room()
        current_index = self.dungeon.current_room_index
        adjacent_rooms = self.dungeon.get_adjacent_rooms(current_index)
        rooms_to_render = [current_room] + adjacent_rooms

        # Create a virtual surface for zoomed rendering if needed
        if abs(self.zoom - 1.0) > 0.05:
            virtual_width = int(self.width / self.zoom)
            virtual_height = int(self.height / self.zoom)
            virtual_surface = pygame.Surface((virtual_width, virtual_height))
            virtual_surface.fill((0, 0, 0))
        else:
            virtual_surface = self.screen
            virtual_width = self.width
            virtual_height = self.height

        # Render all rooms (current and adjacent)
        for room in rooms_to_render:
            room.render(virtual_surface, self.camera_x, self.camera_y, 
                    show_collision_rects=self.show_collision_rects)

        # --- RENDER ENEMIES IN CURRENT ROOM ---
        enemies = getattr(current_room, 'enemies', []) if hasattr(current_room, 'enemies') else []
        for enemy in enemies:
            enemy.draw(virtual_surface, self.camera_x, self.camera_y)

        # Render the player
        self.player.render(
            virtual_surface,
            self.camera_x,
            self.camera_y,
            rooms_to_render,
            zoom=self.zoom,
            show_collision_rects=self.show_collision_rects
        )

        # --- RENDER PROJECTILES ---
        for proj in self.projectiles:
            proj.render(virtual_surface, self.camera_x, self.camera_y, self.zoom)

        # --- DARKNESS OVERLAY ---
        darkness_overlay = pygame.Surface((virtual_width, virtual_height), pygame.SRCALPHA)
        darkness_overlay.fill((0, 0, 0, 255))  # Fully opaque black

            # Cut light holes for ALL light sources
        for light in self.light_sources:
            # Convert to screen coordinates
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

        
        wall_rects = []
        for wall in current_room.get_wall_rects():
            screen_wall = pygame.Rect(
                wall.x - self.camera_x,
                wall.y - self.camera_y,
                wall.width,
                wall.height
            )
            wall_rects.append(screen_wall)

        # Fill the union of all wall rects as a single region
        if wall_rects:
            union_rect = wall_rects[0].unionall(wall_rects[1:])
            darkness_overlay.fill((0, 0, 0, 0), union_rect)
        
        player_center_x = int(self.player.x - self.camera_x + self.player.size // 2)
        player_center_y = int(self.player.y - self.camera_y + self.player.size // 2)
        player_center = (player_center_x, player_center_y)
        light_radius = 130  # or self.player_light_radius if you have
        self.cut_radial_light(darkness_overlay, player_center, 100)


        # Create player light mask using ray casting (if needed, can be added here)
        player_center_x = int(self.player.x - self.camera_x + self.player.size // 2)
        player_center_y = int(self.player.y - self.camera_x + self.player.size // 2)

        # Collect wall rects in screen space (if needed for future light logic)

        # Apply darkness overlay to scene
        virtual_surface.blit(darkness_overlay, (0, 0), special_flags=pygame.BLEND_PREMULTIPLIED)

        # Scale to screen if zoomed
        if abs(self.zoom - 1.0) > 0.05:
            scaled_surface = pygame.transform.scale(virtual_surface, (self.width, self.height))
            self.screen.blit(scaled_surface, (0, 0))

        # Render UI (always on top)
        self.dungeon.render_ui(self.screen)
        self.player.render_bars(self.screen, self.screen.get_height())  # top-left corner HUD bars
        self.player.render_weapon_hud(self.screen, self.screen.get_width(), self.screen.get_height())  # top-right corner weapon HUD
        self.player.render_weapon_info_overlay(self.screen, self.camera_x, self.camera_y, self.room, self.zoom)  # Render weapon info overlay if player is near a weapon

        # Draw crosshair particles
        for particle in self.crosshair_particles:
            # Update position based on velocity
            particle['pos'] += particle['velocity'] * self.dt

            # Create particle surface
            particle_surface = pygame.Surface((particle['radius']*2, particle['radius']*2), pygame.SRCALPHA)
            color_with_alpha = (*particle['color'], particle['alpha'])
            pygame.draw.circle(
                particle_surface, 
                color_with_alpha, 
                (particle['radius'], particle['radius']), 
                particle['radius'])
            
            # Draw particle
            self.screen.blit(
                particle_surface,
                (particle['pos'].x - particle['radius'],
                particle['pos'].y - particle['radius']))
            
        # Draw crosshair at mouse position
        mouse_pos = pygame.mouse.get_pos()

        # Apply smooth scaling
        if abs(self.crosshair_scale - 1.0) > 0.01:
            scaled_size = (int(self.current_crosshair.get_width() * self.crosshair_scale), 
                        int(self.current_crosshair.get_height() * self.crosshair_scale))
            scaled_crosshair = pygame.transform.scale(self.current_crosshair, scaled_size)
            offset = (scaled_size[0] // 2, scaled_size[1] // 2)
            self.screen.blit(scaled_crosshair, 
                            (mouse_pos[0] - offset[0], 
                            mouse_pos[1] - offset[1]))
        else:
            self.screen.blit(self.current_crosshair, 
                            (mouse_pos[0] - self.crosshair_offset[0], 
                            mouse_pos[1] - self.crosshair_offset[1]))

        # FPS monitor
        if self.show_fps:
            fps = self.clock.get_fps()
            playerPos = self.player.x, self.player.y
            fps_text = self.fps_font.render(f"FPS: {fps:.1f}", True, (255, 255, 0))
            playerPos_text = self.fps_font.render(f"Player Pos: {playerPos}", True, (255, 255, 0))
            self.screen.blit(fps_text, (10, self.screen.get_height() - fps_text.get_height() - 10))
            self.screen.blit(playerPos_text, (10,  self.screen.get_height() - fps_text.get_height() - 30))

        pygame.display.flip()

        # Calculate changed areas
        dirty_rects = self.calculate_dirty_rects()

        # Only update changed areas
        for rect in dirty_rects:
            pygame.display.update(rect)

        # Track current drawn areas for next frame
        self.last_drawn_rects = dirty_rects

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
        while self.running:
            
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(360)
        pygame.quit()
