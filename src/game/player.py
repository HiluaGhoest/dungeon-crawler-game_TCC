
import math
import time
from numpy import angle, eye
import pygame
from pygame import gfxdraw
from game.weapons import RangedWeapon, MeleeWeapon


class Player:
    def render_weapon_hud(self, surface, screen_width, screen_height):
        # HUD: 3 squares at bottom right
        slot_size = 32
        spacing = 12
        margin = 24
        total_width = slot_size * 3 + spacing * 2
        x_start = screen_width - margin - total_width
        y = screen_height - margin - slot_size
        for i in range(3):
            x = x_start + i * (slot_size + spacing)
            rect = pygame.Rect(x, y, slot_size, slot_size)
            # Highlight active slot
            if i == self.active_weapon_index:
                color = (255, 255, 0)  # yellow border for active
                border = 4
            else:
                color = (180, 180, 180)
                border = 2
            pygame.draw.rect(surface, color, rect, border)
            # Optionally, fill if weapon exists
            if self.weapons[i] is not None:
                pygame.draw.rect(surface, (100, 200, 255), rect.inflate(-8, -8))
            # Draw slot number
            font = pygame.font.SysFont(None, 18)
            num_surface = font.render(str(i+1), True, (255,255,255))
            num_rect = num_surface.get_rect(center=rect.center)
            surface.blit(num_surface, num_rect)
    def __init__(self, x, y, speed=5, color=(200, 200, 50), size=16, sprite_path=None):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.size = size
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.interact_key_pressed = False
        # Swing state now handled by weapon (if MeleeWeapon)

        # Health, Stamina
        self.max_health = 100
        self.health = self.max_health
        self.display_health = self.health

        self.max_stamina = 100
        self.stamina = self.max_stamina
        self.display_stamina = self.stamina

        # Player Weapons (3 slots)
        self.weapons = [None, None, None]  # 3 weapon slots
        self.active_weapon_index = 0
        self.weapon_origin = None  # pilar de onde veio a arma, se aplicável

        self.eye_bob_timer = 0.0        # controla o tempo do bob
        self.eye_bob_amplitude = 0.5    # altura máxima do bob (pixels)
        self.eye_bob_speed = 0.01        # velocidade do bob (ciclos por segundo)

        self.blink_timer = 0.0          # controla o tempo do piscar
        self.blink_interval = 3.0       # tempo entre piscadas (segundos)
        self.blink_duration = 0.2       # duração do piscar (segundos)
        self.is_blinking = False



        if sprite_path:
            # Load and scale the sprite to the desired size
            sprite_image = pygame.image.load(sprite_path).convert_alpha()
            self.sprite = pygame.transform.scale(sprite_image, (self.size, self.size))
        else:
            self.sprite = None
            self.color = (255, 255, 255)  # fallback color

    def set_position(self, x, y):
        """Set player position directly"""
        self.x = x
        self.y = y
        self.rect.topleft = (x, y)

    def try_interact_with_pillars(self, rooms):
        for room in rooms:
            for pillar in room.pillar_tiles:
                if self.rect.colliderect(pillar.rect.inflate(8, 8)):
                    pillar.interact(self)

    def attack(self, camera_x=0, camera_y=0, zoom=1.0, projectiles=None):
        weapon = self.get_active_weapon()
        if not weapon:
            return False
        if projectiles is None:
            return False
        angle = self.get_mouse_angle(camera_x, camera_y, zoom)
        print(f"Player world pos: ({self.x}, {self.y})")
        print(f"Camera offset: ({camera_x}, {camera_y})")
        player_center = (self.x, self.y)
        if isinstance(weapon, RangedWeapon):
            return weapon.attack(player_center, angle, projectiles=projectiles)
        elif isinstance(weapon, MeleeWeapon):
            return weapon.attack(player_center, angle)
        return False

    def get_active_weapon(self):
        if 0 <= self.active_weapon_index < len(self.weapons):
            return self.weapons[self.active_weapon_index]
        return None

    @property
    def weapon(self):
        # For backward compatibility
        return self.get_active_weapon()

    @weapon.setter
    def weapon(self, value):
        # Set weapon in current slot
        self.weapons[self.active_weapon_index] = value




    def handle_input(self, rooms=None):
        if rooms is None:
            rooms = []

        keys = pygame.key.get_pressed()
        old_x, old_y = self.x, self.y
        new_x, new_y = self.x, self.y

        # Weapon switching (1, 2, 3)
        if keys[pygame.K_1]:
            self.active_weapon_index = 0
        elif keys[pygame.K_2]:
            self.active_weapon_index = 1
        elif keys[pygame.K_3]:
            self.active_weapon_index = 2

        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        moving = (keys[pygame.K_w] or keys[pygame.K_UP] or
                keys[pygame.K_s] or keys[pygame.K_DOWN] or
                keys[pygame.K_a] or keys[pygame.K_LEFT] or
                keys[pygame.K_d] or keys[pygame.K_RIGHT])
        
        if keys[pygame.K_e]:
            if not self.interact_key_pressed:
                self.interact_key_pressed = True
                self.try_interact_with_pillars(rooms)
        else:
            self.interact_key_pressed = False

        if sprinting and moving and self.stamina > 0:
            self.use_stamina(0.7)
            move_speed = self.speed
        else:
            move_speed = self.speed * 0.5

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            new_y -= move_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            new_y += move_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            new_x -= move_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            new_x += move_speed

        # Horizontal move
        if new_x != old_x:
            temp_rect = pygame.Rect(new_x, self.y, self.size, self.size)
            if not self._check_collision(temp_rect, rooms):
                self.x = new_x

        # Vertical move
        if new_y != old_y:
            temp_rect = pygame.Rect(self.x, new_y, self.size, self.size)
            if not self._check_collision(temp_rect, rooms):
                self.y = new_y

        self.rect.topleft = (self.x, self.y)

    def get_mouse_angle(self, camera_x=0, camera_y=0, zoom=1.0):
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Convert mouse screen position to world coordinates
        world_mouse_x = (mouse_x / zoom) + camera_x
        world_mouse_y = (mouse_y / zoom) + camera_y

        player_center_x = self.x + self.size // 2
        player_center_y = self.y + self.size // 2

        dx = world_mouse_x - player_center_x
        dy = world_mouse_y - player_center_y

        angle = math.atan2(dy, dx)
        return angle  # in radians

    
    def _check_collision(self, player_rect, rooms):
        for room in rooms:
            room_rect = pygame.Rect(room.x, room.y, room.width, room.height)
            # Optional: skip room if player is far
            if not room_rect.colliderect(player_rect.inflate(64, 64)):
                continue

            for wall in room.get_wall_rects():
                if player_rect.colliderect(wall):
                    return True
        return False
    
        # Example methods to modify attributes safely
    def take_damage(self, amount):
        self.health = max(0, self.health - amount)

    def restore_health(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def use_stamina(self, amount):
        self.stamina = max(0, self.stamina - amount)

    def restore_stamina(self, amount):
        self.stamina = min(self.max_stamina, self.stamina + amount)

    def _draw_vertical_bar_with_layers(self, surface, x, y, height, current, max_val,
                        base_color, mid_color, top_color,
                        invert=False, line_width=8, circle_radius=12, radius=4, label=None, font=None, value=None):
        
        fill_ratio = max(0.0, min(current / max(1, max_val), 1.0))

        # Clamp so the bar never fills the last 50px at the end (bottom for normal, top for inverted)
        min_bar_margin = 50
        if invert:
            # Inverted: fill from top to bottom (depletes from top)
            fill_height = int(height * fill_ratio)
            fill_height = max(0, fill_height - min_bar_margin)
            bar_top = y
        else:
            # Normal: fill from bottom to top (depletes from bottom)
            fill_height = int(height * fill_ratio)
            fill_height = min(fill_height, height - min_bar_margin)
            bar_top = y + (height - fill_height)

        # Center X for bar layers
        center_x = x + line_width // 2


        full_width = line_width

        # Draw the capsule ends ONCE for the whole bar, then draw each layer as a rect only
        pill_radius = full_width // 2
        # Only draw the capsule ends if the bar is tall enough
        if fill_height > 0:
            if fill_height <= full_width:
                # If the bar is very short, just draw an ellipse
                pygame.draw.ellipse(surface, base_color, (x, bar_top, full_width, fill_height))
            else:
                # Draw top and bottom circles (ends)
                pygame.draw.ellipse(surface, base_color, (x, bar_top, full_width, full_width))
                pygame.draw.ellipse(surface, base_color, (x, bar_top + fill_height - full_width, full_width, full_width))
                # Draw the center rect (between the circles)
                pygame.draw.rect(surface, base_color, (x, bar_top + pill_radius, full_width, fill_height - 2 * pill_radius))

        # Now draw the layers as rectangles only (no round ends)
        layer1_x = x
        layer1_width = int(full_width * 0.25)
        self._draw_bar_layer(surface,
            x=layer1_x,
            y=bar_top,
            width=layer1_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=base_color,
            radius=radius,
            draw_capsule_ends=False
        )

        layer2_x = x + int(full_width * 0.25)
        layer2_width = int(full_width * 0.5)
        self._draw_bar_layer(surface,
            x=layer2_x,
            y=bar_top,
            width=layer2_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=mid_color,
            radius=radius,
            draw_capsule_ends=False
        )

        layer3_x = x + int(full_width * 0.75)
        layer3_width = int(full_width * 0.25)
        self._draw_bar_layer(surface,
            x=layer3_x,
            y=bar_top,
            width=layer3_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=top_color,
            radius=radius,
            draw_capsule_ends=False
        )




        # --- Draw horseshoe/arc using asset image (white) ---
        circle_x = center_x
        circle_y = y if invert else y + height
        arc_radius = circle_radius
        # Load the horseshoe asset (white version)
        # You may want to cache this in a class/static variable for performance
        try:
            horseshoe_img = pygame.image.load("game/assets/sprites/ui/horseshoe.png").convert_alpha()
        except Exception:
            horseshoe_img = None
        if horseshoe_img:
            # Scale the horseshoe to fit the arc_radius
            scale_factor = (arc_radius * 2) / max(horseshoe_img.get_width(), horseshoe_img.get_height())
            new_size = (int(horseshoe_img.get_width() * scale_factor), int(horseshoe_img.get_height() * scale_factor))
            horseshoe_img = pygame.transform.smoothscale(horseshoe_img, new_size)
            # Rotate if inverted
            if invert:
                horseshoe_img = pygame.transform.rotate(horseshoe_img, 180)
            # Center the image on (circle_x, circle_y)
            img_rect = horseshoe_img.get_rect(center=(circle_x, circle_y))
            surface.blit(horseshoe_img, img_rect)
        else:
            # Fallback: draw a simple white circle if asset missing
            pygame.draw.circle(surface, (255,255,255), (circle_x, circle_y), arc_radius, 2)

        # --- Draw value/max and label to the right of the horseshoe ---
        if label and font and value is not None:
            # Value text (larger)
            value_font = font
            value_text = f"{int(value)}/{int(max_val)}"
            value_surface = value_font.render(value_text, True, (255, 255, 255))
            # Reserve space for the widest possible value text (e.g., '100/100')
            max_value_text = f"{int(max_val)}/{int(max_val)}"
            max_value_surface = value_font.render(max_value_text, True, (255, 255, 255))
            max_value_rect = max_value_surface.get_rect()
            value_rect = value_surface.get_rect()
            # Label text (smaller, but same custom font)
            try:
                font_path = font.path if hasattr(font, 'path') else "game/assets/fonts/CinzelDecorative-Black.ttf"
                label_font = pygame.font.Font(font_path, max(12, font.get_height() // 2))
            except Exception:
                label_font = pygame.font.SysFont(None, max(12, font.get_height() // 2))
            label_surface = label_font.render(label, True, (255, 255, 255))
            label_rect = label_surface.get_rect()

            # Reserve a fixed area for the value text, so the label and value never move
            reserved_x = circle_x + arc_radius + 12
            reserved_y = circle_y
            # Center the reserved area vertically on the circle_y
            reserved_rect = pygame.Rect(0, 0, max_value_rect.width, max_value_rect.height)
            reserved_rect.midleft = (reserved_x, reserved_y)

            # Center the actual value_surface inside the reserved area
            value_rect.center = reserved_rect.center

            # Label positioning: always relative to the reserved area, not the value_rect
            if label.lower() == "health":
                # Label above reserved area
                label_rect.midbottom = (reserved_rect.centerx, reserved_rect.top - 2)
            elif label.lower() == "stamina":
                # Label below reserved area
                label_rect.midtop = (reserved_rect.centerx, reserved_rect.bottom + 2)
            else:
                # Default: to the right of reserved area
                label_rect.midleft = (reserved_rect.right + 8, reserved_rect.centery)

            surface.blit(value_surface, value_rect)
            surface.blit(label_surface, label_rect)




    def _draw_bar_layer(self, surface, x, y, width, height, current, max_val, color, radius=5, draw_capsule_ends=False):
        # Make sure width/height are valid
        width = max(1, int(width))
        height = max(1, int(height))

        x = int(x)
        y = int(y)

        # Draw as a rectangle with rounded ends (capsule shape)
        # Use border_radius to make the ends round
        border_radius = min(width, height) // 2 if width > 1 and height > 1 else 0
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=border_radius)

    def render_bars(self, surface, screen_height):
        bar_x = 20
        bar_y = 20
        bar_height = screen_height - 40

        white = (255, 255, 255)
        base = (255, 255, 255)
        mid = (255, 255, 255)
        top = (255, 255, 255)

        # Load custom font
        font_path = "game/assets/fonts/CinzelDecorative-Black.ttf"
        try:
            custom_font = pygame.font.Font(font_path, 24)
        except Exception:
            custom_font = pygame.font.SysFont(None, 24)

        self._draw_vertical_bar_with_layers(
            surface, bar_x, bar_y, bar_height,
            current=self.display_health,
            max_val=self.max_health,
            base_color=base,
            mid_color=mid,
            top_color=top,
            invert=False,
            label="Health",
            font=custom_font,
            value=self.display_health
        )

        # STAMINA (top, inverted)
        self._draw_vertical_bar_with_layers(
            surface, bar_x + 30, bar_y, bar_height,
            current=self.display_stamina,
            max_val=self.max_stamina,
            base_color=base,
            mid_color=mid,
            top_color=top,
            invert=True,
            label="Stamina",
            font=custom_font,
            value=self.display_stamina
        )


    def update(self, rooms=None, dt=0.016 ):
        self.handle_input(rooms)

        # Regenerate stamina if not sprinting or moving
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d] or \
                    keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if not (sprinting and is_moving):
            self.restore_stamina(0.5)  # só regenera se não estiver sprintando *e* se movendo

        def safe_lerp(current, target, speed, dt):
            delta = (target - current) * speed * dt
            if not (isinstance(delta, float) and (delta != delta or delta == float('inf') or delta == float('-inf'))):
                # Snap to target if very close to avoid visual "stall"
                if abs(target - current) < 0.5:
                    return target
                return current + delta
            return target

        speed = 10

        self.display_health = safe_lerp(self.display_health, self.health, speed, dt)

        # Clamp stamina between 0 and max_stamina
        self.stamina = max(0, min(self.stamina, self.max_stamina))

        # If stamina is at boundaries, sync display immediately, else interpolate
        if self.stamina <= 0:
            self.display_stamina = 0
        elif self.stamina >= self.max_stamina:
            self.display_stamina = self.max_stamina
        else:
            self.display_stamina = safe_lerp(self.display_stamina, self.stamina, speed, dt)

        # Swing logic now handled by weapon
        weapon = self.get_active_weapon()
        if weapon and hasattr(weapon, 'update'):
            weapon.update(dt)

        # Atualiza bob dos olhos
        self.eye_bob_timer += dt
        if self.eye_bob_timer > 1.0 / self.eye_bob_speed:
            self.eye_bob_timer -= 1.0 / self.eye_bob_speed

        # Atualiza piscar
        self.blink_timer += dt
        if not self.is_blinking and self.blink_timer >= self.blink_interval:
            self.is_blinking = True
            self.blink_timer = 0.0
        elif self.is_blinking and self.blink_timer >= self.blink_duration:
            self.is_blinking = False
            self.blink_timer = 0.0

                
    def get_interactable_pillars(self, player_rect, radius=64):
        interactables = []
        for pillar in self.pillar_tiles:
            if player_rect.colliderect(pillar.rect.inflate(radius, radius)):
                interactables.append(pillar)
        return interactables



    def render(self, surface, camera_x=0, camera_y=0, rooms=None, zoom=1.0, show_collision_rects=False, dt=0.016):
        from game.util.light import create_soft_player_light
        # Calculate render position with camera offset
        render_x = self.x - camera_x
        render_y = self.y - camera_y

        # Get room walls for light collision
        wall_rects = []
        if rooms:
            for room in rooms:
                if not hasattr(room, 'get_wall_rects'):
                    continue
                for wall in room.get_wall_rects():
                    screen_wall = pygame.Rect(
                        wall.x - camera_x,
                        wall.y - camera_y,
                        wall.width,
                        wall.height
                    )
                    wall_rects.append(screen_wall)
            # Performance: limit walls for lighting
            if len(wall_rects) > 150:
                player_center_x = render_x + self.size // 2
                player_center_y = render_y + self.size // 2
                walls_with_distance = [
                    ((wall.x + wall.width // 2 - player_center_x) ** 2 + (wall.y + wall.height // 2 - player_center_y) ** 2, wall)
                    for wall in wall_rects
                ]
                walls_with_distance.sort(key=lambda x: x[0])
                wall_rects = [wall for _, wall in walls_with_distance[:100]]

        # Render soft light around player
        create_soft_player_light(
            surface,
            render_x + self.size // 2,
            render_y + self.size // 2,
            radius=100,
            wall_rects=wall_rects
        )

        # Weapon rendering delegated to weapon class
        weapon = self.get_active_weapon()
        if weapon and hasattr(weapon, 'render'):
            mouse_screen_x, mouse_screen_y = pygame.mouse.get_pos()
            mouse_virtual_x = mouse_screen_x / zoom
            mouse_virtual_y = mouse_screen_y / zoom
            world_mouse_x = mouse_virtual_x + camera_x
            world_mouse_y = mouse_virtual_y + camera_y
            player_center_x = self.x + self.size // 2
            player_center_y = self.y + self.size // 2
            player_center = (player_center_x, player_center_y)
            angle = self.get_mouse_angle(camera_x, camera_y, zoom)
            # Pass dt to weapon.render if it accepts it
            try:
                weapon.render(surface, player_center, angle, camera_x, camera_y, zoom, dt=dt)
            except TypeError:
                weapon.render(surface, player_center, angle, camera_x, camera_y, zoom)

        if self.sprite:
            surface.blit(self.sprite, (render_x, render_y))
        else:
            # --- pega posição do mouse no mundo ---
            mouse_screen_x, mouse_screen_y = pygame.mouse.get_pos()
            mouse_virtual_x = mouse_screen_x / zoom + camera_x
            mouse_virtual_y = mouse_screen_y / zoom + camera_y

            player_center_x = self.x + self.size // 2
            player_center_y = self.y + self.size // 2

            dx = mouse_virtual_x - player_center_x

            eye_offset = 2
            if dx > 5:
                eye_shift = eye_offset
            elif dx < -5:
                eye_shift = -eye_offset
            else:
                eye_shift = 0

            render_x = self.x - camera_x
            render_y = self.y - camera_y

            # --- bob timer já atualizado no update(dt), aqui só calcula o offset ---
            eye_bob_offset = (self.eye_bob_amplitude + 3) * math.sin(self.eye_bob_timer * 2 * math.pi * (self.eye_bob_speed + 0.5))

            # Corpo: encolhe a altura baseado no bob
            new_height = int(self.size - abs(eye_bob_offset) * 0.5)
            new_width = int(self.size + abs(eye_bob_offset) * 0.5 * 2)

            base_y = render_y + self.size
            new_y = base_y - new_height

            base_x = render_x + self.size / 2
            new_x = base_x - new_width / 2

            player_rect = pygame.Rect(new_x, new_y, new_width, new_height)
            pygame.draw.rect(surface, self.color, player_rect)

            # Olhos
            eye_size = 2

            eye_y_base = render_y + 5
            eye_y = eye_y_base  # olhos sobem e descem suavemente

            left_eye_x = render_x + 5 + eye_shift
            right_eye_x = render_x + self.size - 5 - eye_size + eye_shift

            if self.is_blinking:
                eye_height = 0
            else:
                eye_height = 2

            pygame.draw.rect(surface, (0, 0, 0), (left_eye_x, eye_y, eye_size, eye_height))
            pygame.draw.rect(surface, (0, 0, 0), (right_eye_x, eye_y, eye_size, eye_height))
