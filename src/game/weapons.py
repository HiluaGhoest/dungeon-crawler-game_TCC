
import random
import pygame
import time
import math



class Weapon:
    def __init__(self, name, sprite_path=None, color=(200, 100, 100)):
        self.name = name
        self.color = color
        self.damage = 0
        self.fire_rate = 1.0
        self.sprite = None
        self.origin = (0, 0)
        self.last_attack_time = 0

        if sprite_path:
            self.sprite = pygame.image.load(sprite_path).convert_alpha()

    def can_attack(self):
        current_time = time.time()
        return (current_time - self.last_attack_time) >= (1.0 / self.fire_rate)

    def attack(self, player_pos, angle):
        """Método genérico para atacar — deve ser implementado nas subclasses."""
        raise NotImplementedError
    
    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1.0):
        # Bobbing effect and shadow rendering for static weapons
        # Animate sprite if self.sprites exists (like in Steel_Sword)
        sprite = self.sprite
        if hasattr(self, 'sprites') and isinstance(self.sprites, list) and len(self.sprites) > 0:
            # Animate frames based on time
            frame_duration = getattr(self, 'frame_duration', 0.15)
            t = time.time() % 1000
            frame_idx = int((t // frame_duration) % len(self.sprites))
            sprite = self.sprites[frame_idx]
        if not sprite:
            return
        base_width = 64
        original_rect = sprite.get_rect()
        scale_width = int(base_width * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        scaled_sprite = pygame.transform.scale(sprite, (scale_width, scale_height))

        # Bobbing effect: vertical offset based on time
        bob_amplitude = 10 * zoom  # pixels
        bob_speed = 0.3  # cycles per second
        t = time.time() % 1000
        bob_offset = math.sin(t * bob_speed * math.pi * 2) * bob_amplitude

        # Shadow parameters
        shadow_color = (0, 0, 0, 80)  # RGBA, semi-transparent
        shadow_radius = int(scale_width * 0.45)
        shadow_center = (int(center[0]), int(center[1] + scale_height // 2 + 1 * zoom))

        # Draw shadow (using pygame's surface for alpha)
        shadow_surface = pygame.Surface((shadow_radius * 2, shadow_radius * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, shadow_color, (0, shadow_radius // 2, shadow_radius * 2, shadow_radius))
        surface.blit(shadow_surface, (shadow_center[0] - shadow_radius, shadow_center[1] - shadow_radius // 2))

        # Draw weapon sprite with bobbing
        rect = scaled_sprite.get_rect(center=(center[0], center[1] + bob_offset))
        surface.blit(scaled_sprite, rect.topleft)

    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        # No state needed for bobbing, handled in render_static
        pass


class MeleeWeapon(Weapon):
    def __init__(self, name, sprite_path=None, color=(200, 100, 100), damage=10, fire_rate=1.0, attack_range=80):
        super().__init__(name, sprite_path, color)
        self.damage = damage
        self.fire_rate = fire_rate
        self.attack_range = attack_range
        # Swing animation state
        self.swing_progress = 0
        self.swing_duration = 0.25  # seconds
        self.swing_start_time = 0
        self.swing_max_angle = 90
        self.swing_phase = 0  # 0 = none, 1 = forward, 2 = backward, 3 = finish

    def can_attack(self):
        return (time.time() - self.last_attack_time) >= getattr(self, 'swing_cooldown', 1.0 / self.fire_rate)

    def attack(self, player_center, angle):
        if not self.can_attack():
            return False
        self.last_attack_time = time.time()
        self.swing_start_time = time.time()
        self.swing_phase = 1  # start swing forward
        print(f"Swinging {self.name} at angle {math.degrees(angle):.1f} degrees!")
        return True

    def update(self, dt):
        # Handle swing phase transitions
        if self.swing_phase != 0:
            elapsed = time.time() - self.swing_start_time
            if elapsed > self.swing_duration:
                if self.swing_phase == 1:
                    self.swing_phase = 2  # backward
                    self.swing_start_time = time.time()
                elif self.swing_phase == 2:
                    self.swing_phase = 3
                    self.swing_start_time = time.time()
                else:
                    self.swing_phase = 0  # finished

    def render(self, surface, player_center, angle, camera_x=0, camera_y=0, zoom=1.0):
        # Calculate base sprite and scaling
        if not self.sprite:
            return
        original_rect = self.sprite.get_rect()
        base_width = 64
        scale_width = int(base_width * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        scaled_weapon = pygame.transform.scale(self.sprite, (scale_width, scale_height))

        # Calculate scaled origin
        origin_x = self.origin[0] * (scale_width / original_rect.width)
        origin_y = self.origin[1] * (scale_height / original_rect.height)

        # Rotate the scaled weapon image
        adjusted_angle = math.degrees(angle) + 90
        angle_rad = math.radians(math.degrees(angle))

        if math.cos(angle_rad) < 0:
            scaled_weapon = pygame.transform.flip(scaled_weapon, True, False)

        # Swing animation
        swing_offset = 0
        if hasattr(self, 'swing_phase') and self.swing_phase != 0:
            elapsed = time.time() - self.swing_start_time
            t = min(elapsed / self.swing_duration, 1.0)

            def ease_out_back(t):
                c1 = 1.70158
                c3 = c1 + 1
                return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2

            t_eased = ease_out_back(t)

            def lerp(a, b, t):
                return a + (b - a) * t

            pre_swing_offset = 40
            swing_max_angle = getattr(self, 'swing_max_angle', 90)
            swing_phase = self.swing_phase

            if swing_phase == 1:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(0, -swing_max_angle - pre_swing_offset, t_eased)
                else:
                    swing_offset = lerp(0, swing_max_angle + pre_swing_offset, t_eased)
            elif swing_phase == 2:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(-swing_max_angle, swing_max_angle, t_eased)
                else:
                    swing_offset = lerp(swing_max_angle, -swing_max_angle, t_eased)
            elif swing_phase == 3:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(swing_max_angle, 0, t_eased)
                else:
                    swing_offset = lerp(-swing_max_angle, 0, t_eased)
            # else swing_offset = 0

            adjusted_angle += swing_offset

        rotated_image = pygame.transform.rotate(scaled_weapon, -adjusted_angle)
        rotated_rect = rotated_image.get_rect()

        # Calculate the vector from the center of the scaled image to the origin
        image_center = pygame.math.Vector2(scale_width / 2, scale_height / 2)
        origin = pygame.math.Vector2(origin_x, origin_y)
        offset = origin - image_center
        offset_rotated = offset.rotate(adjusted_angle)

        blit_pos_world = pygame.math.Vector2(player_center) - pygame.math.Vector2(rotated_rect.width / 2, rotated_rect.height / 2) - offset_rotated
        draw_x = blit_pos_world.x - camera_x
        draw_y = blit_pos_world.y - camera_y

        surface.blit(rotated_image, (draw_x, draw_y))

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        return super().render_static(surface, center, camera_x, camera_y, zoom)

    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        pass


class RangedWeapon(Weapon):
    def __init__(self, name, sprite_path=None, color=(100, 200, 100), damage=8, fire_rate=0.8, projectile_speed=400):
        super().__init__(name, sprite_path, color)
        self.damage = damage
        self.fire_rate = fire_rate
        self.projectile_speed = projectile_speed

    def attack(self, player_pos, angle, enemies=None, projectiles=None):
        # Allow attack to be called with just (player_pos, angle) for player usage
        if not self.can_attack():
            return False
        self.last_attack_time = time.time()
        # If called without projectiles, just return True (no projectile spawned)
        if projectiles is None:
            return True
        proj = Projectile(
            x=player_pos[0],
            y=player_pos[1],
            angle=angle,
            speed=self.projectile_speed,
            damage=self.damage
        )
        projectiles.append(proj)
        return True
    
    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        return super().render_static(surface, center, camera_x, camera_y, zoom) 
    
    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        pass



class Projectile:
    def __init__(self, x, y, angle, speed, damage):
        self.pos = pygame.math.Vector2(x, y)
        self.angle = angle
        self.speed = speed
        self.damage = damage
        self.radius = 5  # pode ser ajustado
        self.velocity = pygame.math.Vector2(math.cos(angle), math.sin(angle)) * speed
        self.rect = pygame.Rect(x - self.radius, y - self.radius, self.radius*2, self.radius*2)
        self.is_alive = True

    def update(self, dt, enemies, wall_rects=None, room_rect=None):
        self.pos += self.velocity * dt
        self.rect.topleft = (self.pos.x - self.radius, self.pos.y - self.radius)

        # Checar colisão com inimigos
        for enemy in enemies:
            if self.rect.colliderect(enemy.rect):
                enemy.take_damage(self.damage)
                self.is_alive = False
                return

        # Checar colisão com paredes
        if wall_rects:
            for wall in wall_rects:
                if self.rect.colliderect(wall):
                    self.is_alive = False
                    return

        # Checar se saiu dos limites da sala
        if room_rect and not room_rect.colliderect(self.rect):
            self.is_alive = False
            return

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        # Default projectile: red circle (for other weapons)
        screen_x = (self.pos.x - camera_x) * zoom
        screen_y = (self.pos.y - camera_y) * zoom
        pygame.draw.circle(surface, (255, 50, 50), (int(screen_x), int(screen_y)), int(self.radius * zoom))


# --- Bullet class for Pistol ---
class Bullet(Projectile):
    def __init__(self, x, y, angle, speed, damage):
        super().__init__(x, y, angle, speed, damage)
        self.lifetime = 2.0  # 2 seconds
        print(f"Bullet created at world position: {x}, {y}")  # Debug world position
        
    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        screen_x = (self.pos.x - camera_x) * (zoom - 0.3)
        screen_y = (self.pos.y - camera_y) * (zoom - 0.3)

        print(f"Rendering bullet with zoom: {zoom}")  # Debug screen position
        print(f"Bullet screen position: {screen_x}, {screen_y}")  # Debug screen position

        # DEBUG: Draw spawn point marker
        pygame.draw.circle(surface, (0, 255, 0), (int(screen_x), int(screen_y)), int(5 * zoom))
        
        pygame.draw.circle(surface, (255, 255, 255), (int(screen_x), int(screen_y)), int(self.radius * zoom))

class Steel_Sword(MeleeWeapon):
    def __init__(self):
        super().__init__(name="Steel_Sword", sprite_path=None, color=(220, 220, 60))
        self.sprites = [
            pygame.image.load("game/assets/sprites/weapons/steel_sword/steel_sword_1.png").convert_alpha(),
            pygame.image.load("game/assets/sprites/weapons/steel_sword/steel_sword_2.png").convert_alpha(),
            pygame.image.load("game/assets/sprites/weapons/steel_sword/steel_sword_3.png").convert_alpha(),
        ]
        self.sprite = self.sprites[0]  # Default sprite
        self.current_frame = 0
        self.frame_duration = 0.15  # Time between frames in seconds
        self.frame_timer = 0
        self.is_swinging = False
        self.origin = (self.sprites[0].get_width() // 2, self.sprites[0].get_height())
        self.damage = 15
        self.fire_rate = 1.5
        self.swing_cooldown = 1.0 / self.fire_rate
        # Trail effect
        self.trails = []  # Each trail: {pos, time, alpha}
        self.trail_spawn_interval = 0.02
        self.trail_timer = 0
        self.trail_lifetime = 0.35  # seconds
        self.trail_color = (180, 0, 255)
        self.last_tip_pos = None

    def attack(self, player_center, angle):
        if not self.can_attack():
            return False
        self.last_attack_time = time.time()
        self.is_swinging = True
        self.swing_start_time = time.time()
        self.swing_phase = 1  # start swing forward
        print(f"Swinging {self.name} at angle {math.degrees(angle):.1f} degrees!")
        return True

    def update(self, dt):
        # Always update animation regardless of swinging state
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_timer -= self.frame_duration
            self.current_frame = (self.current_frame + 1) % len(self.sprites)
            self.sprite = self.sprites[self.current_frame]

        phase1_hold_time = 0.3  # segundos extras para ficar na fase 1
        # Handle swing phase transitions (copied from MeleeWeapon)
        if self.swing_phase != 0:
            elapsed = time.time() - self.swing_start_time

            if self.swing_phase == 1:
                if elapsed > self.swing_duration + phase1_hold_time:
                    self.swing_phase = 2  # backward
                    self.swing_start_time = time.time()

            elif self.swing_phase == 2:
                if elapsed > self.swing_duration:
                    self.swing_phase = 3  # return
                    self.swing_start_time = time.time()

            else:
                if elapsed > self.swing_duration:
                    self.swing_phase = 0  # finished
                    self.is_swinging = False

        # Update trails
        for trail in self.trails:
            trail['time'] += dt
        self.trails = [t for t in self.trails if t['time'] < self.trail_lifetime]

    def render(self, surface, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, dt=0.016):
        # Use current frame for animation
        sprite = self.sprites[self.current_frame]
        base_width = 64
        original_rect = sprite.get_rect()
        scale_width = int(base_width * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        scaled_sprite = pygame.transform.scale(sprite, (scale_width, scale_height))

        # Calculate scaled origin
        origin_x = self.origin[0] * (scale_width / original_rect.width)
        origin_y = self.origin[1] * (scale_height / original_rect.height)

        adjusted_angle = math.degrees(angle) + 90
        angle_rad = math.radians(math.degrees(angle))
        flip = math.cos(angle_rad) < 0
        if flip:
            scaled_sprite = pygame.transform.flip(scaled_sprite, True, False)

        # Swing animation (reuse MeleeWeapon logic if needed)
        swing_offset = 0
        elapsed = time.time() - self.swing_start_time
        t = min(elapsed / self.swing_duration, 1.0)
        def ease_out_back(t):
            c1 = 1.70158
            c3 = c1 + 1
            return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2
        
        t_eased = ease_out_back(t)
        def lerp(a, b, t):
            return a + (b - a) * t
                    
        def ease_out_expo(t):
            return 1 if t == 1 else 1 - pow(2, -10 * t)

        t_eased_expo = ease_out_expo(t)

        if hasattr(self, 'swing_phase') and self.swing_phase != 0:

            pre_swing_offset = 40
            swing_max_angle = getattr(self, 'swing_max_angle', 90)
            swing_phase = self.swing_phase
            if swing_phase == 1:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(0, -swing_max_angle - pre_swing_offset, t_eased)
                else:
                    swing_offset = lerp(0, swing_max_angle + pre_swing_offset, t_eased)
            elif swing_phase == 2:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(-swing_max_angle, swing_max_angle, t_eased_expo)
                else:
                    swing_offset = lerp(swing_max_angle, -swing_max_angle, t_eased_expo)
            elif swing_phase == 3:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(swing_max_angle, 0, t_eased)
                else:
                    swing_offset = lerp(-swing_max_angle, 0, t_eased)
            adjusted_angle += swing_offset

        rotated_sprite = pygame.transform.rotate(scaled_sprite, -adjusted_angle)
        rotated_rect = rotated_sprite.get_rect()
        image_center = pygame.math.Vector2(scale_width / 2, scale_height / 2)
        origin = pygame.math.Vector2(origin_x, origin_y)
        offset = origin - image_center
        offset_rotated = offset.rotate(adjusted_angle)
        blit_pos_world = pygame.math.Vector2(player_center) - pygame.math.Vector2(rotated_rect.width / 2, rotated_rect.height / 2) - offset_rotated
        draw_x = blit_pos_world.x - camera_x
        draw_y = blit_pos_world.y - camera_y


        # --- TRAIL EFFECT ---
        # lerp_color and fire_colors must be available for the whole render method
        def lerp_color(color1, color2, t):
            return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))

        fire_colors = [
            (128, 0, 128),      # deep purple (base)
            (186, 85, 211),     # medium purple
            (221, 160, 221),    # lavender
            (255, 255, 255)     # bright white (core / tip)
        ]

        self.trail_timer += dt
        # Sword tip position (base, no random offset here)
        tip_length = random.uniform(-scale_height * 0.5, scale_height * 0.5)
        tip_offset = pygame.math.Vector2(0, -tip_length)
        tip_offset = tip_offset.rotate(adjusted_angle)
        tip_pos = pygame.math.Vector2(draw_x + scale_width/2, draw_y + scale_height/2) + tip_offset

        def smoothstep(t):
            return t * t * (3 - 2 * t)

        smoothing_factor = 0.1  # More frequent updates for denser trails
        # Make trails denser by increasing the number of steps
        if self.last_tip_pos is not None:
            dist = (tip_pos - self.last_tip_pos).length()
            self.last_tip_pos = self.last_tip_pos.lerp(tip_pos, smoothing_factor)
            if dist > 0:
                min_steps = 8
                max_steps = 24
                steps = random.randint(min_steps, max_steps)  # More steps for denser trails
                for i in range(1, steps+1):
                    interp_factor = smoothstep(i/steps)
                    interp = self.last_tip_pos.lerp(tip_pos, interp_factor)
                    # Add a small random offset to the interpolated position
                    tip_length = random.uniform(0, scale_height * 0.25)
                    tip_offset = pygame.math.Vector2(0, -tip_length)
                    tip_offset = tip_offset.rotate(adjusted_angle)
                    trail_pos = interp + tip_offset
                    self.trails.append({'pos': trail_pos, 'time': 0, 'alpha': 255, 'interp': interp_factor, 'interp_pos': interp})
        else:
            offset_spread = 5 * zoom  # ajuste o quanto quer espalhar
            rand_offset = pygame.math.Vector2(
                random.uniform(-offset_spread, offset_spread),
                random.uniform(-offset_spread, offset_spread)
            )
            tip_length = random.uniform(0, scale_height * 0.25)
            tip_offset = pygame.math.Vector2(0, -tip_length)
            tip_offset = tip_offset.rotate(adjusted_angle)
            interp = tip_pos  # For the first trail, interp is just tip_pos
            trail_pos = tip_offset + rand_offset
            self.trails.append({'pos': trail_pos, 'time': 0, 'alpha': 255, 'interp': 1.0, 'interp_pos': interp})
            self.last_tip_pos = tip_pos


        # Draw trails with offset
        for trail in self.trails:
            fade = 1.0 - (trail['time'] / self.trail_lifetime)
            fade = fade * fade  # curva quadrática para desvanecer mais suavemente
            
            if fade > 0.75:
                t = (fade - 0.75) / 0.25
                color = lerp_color(fire_colors[2], fire_colors[3], t)
            elif fade > 0.5:
                t = (fade - 0.5) / 0.25
                color = lerp_color(fire_colors[1], fire_colors[2], t)
            else:
                t = fade / 0.5
                color = lerp_color(fire_colors[0], fire_colors[1], t)

            alpha = int(255 * fade)
            color = (*color, alpha)
            min_radius = 1
            max_radius = 3
            radius = int(min_radius + (max_radius - min_radius) * fade * zoom)
            color = (*self.trail_color, alpha)
            trail_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            pygame.draw.circle(trail_surface, color, (radius, radius), radius)

            # Only apply offset if trail is between tip and base (not at tip or base)
            if 'interp' in trail and 0.2 < trail['interp'] < 0.8:
                flicker_strength = max(1, int(self.sprite.get_height() / 10 * fade * zoom * 2))

                offset_x = math.sin(trail['time'] * 10 + trail['pos'].x) * flicker_strength * random.uniform(0.3, 0.7)
                offset_y = math.cos(trail['time'] * 12 + trail['pos'].y) * flicker_strength * random.uniform(0.3, 0.7)

                base_radius = int(min_radius + (max_radius - min_radius) * fade * zoom)
                radius = base_radius + random.randint(-1, 1)
                radius = max(1, radius)
            else:
                offset_x = 0
                offset_y = 0

            surface.blit(trail_surface, (trail['pos'].x - radius + int(offset_x), trail['pos'].y - radius + int(offset_y)))

        surface.blit(rotated_sprite, (draw_x, draw_y))

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        return super().render_static(surface, center, camera_x, camera_y, zoom)
    
    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        # Static weapons don't animate, but we can update their state if needed
        pass

class Pistol(RangedWeapon):
    def __init__(self):
        # Load both sprites: pistol (static) and pistol_hold (when held)
        pistol_path = "game/assets/sprites/weapons/pistol/pistol.png"
        pistol_hold_path = "game/assets/sprites/weapons/pistol/pistol_hold.png"
        super().__init__(
            name="Pistol",
            sprite_path=pistol_path,
            color=(150, 150, 255),
            damage=6,
            fire_rate=2.0,  # 2 shots per second
            projectile_speed=500
        )
        # Load both sprites
        try:
            self.sprite_pistol = pygame.image.load(pistol_path).convert_alpha()
        except Exception:
            self.sprite_pistol = None
        try:
            self.sprite_pistol_hold = pygame.image.load(pistol_hold_path).convert_alpha()
        except Exception:
            self.sprite_pistol_hold = None
        # Default sprite is pistol (for static display)
        self.sprite = self.sprite_pistol
        self.recoil_offset = 0
        self.recoil_timer = 0
        self.recoil_duration = 0.1  # segundos
        self.recoil_strength = 5


        # Muzzle origin (relative to weapon sprite, in pixels)
        # Example: (x, y) from top-left of sprite, or (float, float) for subpixel precision
        # You can set this manually after instantiating the weapon.
        self.muzzle_origin = (28, 56)  # Default, adjust as needed

        if self.sprite:
            self.origin = (0, self.sprite.get_height())


    def get_muzzle_pos(self, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, held=True):
        # This function returns both world and screen position of the muzzle, matching the render logic
        sprite = self.sprite_pistol_hold if held and self.sprite_pistol_hold is not None else self.sprite_pistol
        if not sprite:
            return player_center, (0, 0)
        original_rect = sprite.get_rect()
        base_width = 64
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        origin_x = self.origin[0] * (scale_width / original_rect.width)
        origin_y = self.origin[1] * (scale_height / original_rect.height)
        adjusted_angle = math.degrees(angle)
        angle_rad = math.radians(math.degrees(angle))
        # Offsets as in render
        target_horizontal_offset = -20 * zoom if math.cos(angle_rad) < 0 else 20 * zoom
        target_lower_offset = -10 * zoom if math.sin(angle_rad) < 0 else 10 * zoom
        draw_x = player_center[0] - camera_x + target_horizontal_offset
        draw_y = player_center[1] - camera_y + target_lower_offset
        mx = self.muzzle_origin[0] * (scale_width / original_rect.width)
        my = self.muzzle_origin[1] * (scale_height / original_rect.height)
        ox = self.origin[0] * (scale_width / original_rect.width)
        oy = self.origin[1] * (scale_height / original_rect.height)
        offset = pygame.math.Vector2(mx - ox, my - oy)
        offset_rot = offset.rotate(adjusted_angle)
        muzzle_screen_x = draw_x + offset_rot.x
        muzzle_screen_y = draw_y + offset_rot.y
        # Convert back to world coordinates
        muzzle_world_x = muzzle_screen_x + camera_x
        muzzle_world_y = muzzle_screen_y + camera_y
        return (muzzle_world_x, muzzle_world_y), (muzzle_screen_x, muzzle_screen_y)

    def attack(self, player_center, angle, enemies=None, projectiles=None, zoom=1.0, camera_x=0, camera_y=0, held=True):
        if not self.can_attack():
            return False
        self.last_attack_time = time.time()
        self.recoil_timer = self.recoil_duration
        if projectiles is None:
            print("Warning: No projectiles list provided to Pistol.attack()")
            return False

        # Use the current interpolated offsets for perfect alignment with render
        if not hasattr(self, '_prev_horizontal_offset'):
            self._prev_horizontal_offset = 0
        if not hasattr(self, '_prev_lower_offset'):
            self._prev_lower_offset = 0

        # Calculate draw position as in render
        sprite = self.sprite_pistol_hold if held and self.sprite_pistol_hold is not None else self.sprite_pistol
        if not sprite:
            return False
        original_rect = sprite.get_rect()
        base_width = 64
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        adjusted_angle = math.degrees(angle)

        draw_x = player_center[0] - camera_x + self._prev_horizontal_offset
        draw_y = player_center[1] - camera_y + self._prev_lower_offset

        # Calculate muzzle offset (rotated)
        mx = self.muzzle_origin[0] * (scale_width / original_rect.width)
        my = self.muzzle_origin[1] * (scale_height / original_rect.height)
        ox = self.origin[0] * (scale_width / original_rect.width)
        oy = self.origin[1] * (scale_height / original_rect.height)
        offset = pygame.math.Vector2(mx - ox, my - oy)
        offset_rot = offset.rotate(adjusted_angle)
        muzzle_screen_x = draw_x + offset_rot.x
        muzzle_screen_y = draw_y + offset_rot.y
        # Convert back to world coordinates
        muzzle_world_x = muzzle_screen_x + camera_x
        muzzle_world_y = muzzle_screen_y + camera_y

        proj = Bullet(
            x=muzzle_world_x,
            y=muzzle_world_y,
            angle=angle,
            speed=self.projectile_speed,
            damage=self.damage
        )
        projectiles.append(proj)
        print(f"Firing {self.name}! Projectiles count: {len(projectiles)}")
        print(f"Calling attack with muzzle_pos: {(muzzle_world_x, muzzle_world_y)}")
        return True


    def update(self, dt):
        if self.recoil_timer > 0:
            self.recoil_timer -= dt
            self.recoil_offset = self.recoil_strength * (self.recoil_timer / self.recoil_duration)
        else:
            self.recoil_offset = 0

    def render(self, surface, rect, adjusted_angle=0, flip=False):
        if self.sprite is None:
            return

        sprite = self.sprite

        if flip:
            sprite = pygame.transform.flip(sprite, True, False)

        scaled_sprite = pygame.transform.scale(sprite, (rect.width, rect.height))
        rotated_sprite = pygame.transform.rotate(scaled_sprite, -adjusted_angle)
        rotated_rect = rotated_sprite.get_rect(center=rect.center)

        # Aplica o recuo empurrando a sprite levemente para trás
        recoil_dx = math.cos(math.radians(adjusted_angle)) * -self.recoil_offset
        recoil_dy = math.sin(math.radians(adjusted_angle)) * -self.recoil_offset
        rotated_rect.move_ip(recoil_dx, recoil_dy)

        surface.blit(rotated_sprite, rotated_rect.topleft)

    def render(self, surface, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, held=True):
        # Use pistol_hold sprite if held, else pistol sprite
        sprite = self.sprite_pistol_hold if held and self.sprite_pistol_hold is not None else self.sprite_pistol
        if not sprite:
            return
        original_rect = sprite.get_rect()
        base_width = 64
        # Render at half size
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        scaled_weapon = pygame.transform.scale(sprite, (scale_width, scale_height))

        # Calculate scaled origin
        origin_x = self.origin[0] * (scale_width / original_rect.width)
        origin_y = self.origin[1] * (scale_height / original_rect.height)

        # Rotate the scaled weapon image
        adjusted_angle = math.degrees(angle)
        angle_rad = math.radians(math.degrees(angle))

        if math.cos(angle_rad) < 0:
            scaled_weapon = pygame.transform.flip(scaled_weapon, False, True)

        # Swing animation
        swing_offset = 0
        if hasattr(self, 'swing_phase') and self.swing_phase != 0:
            elapsed = time.time() - self.swing_start_time
            t = min(elapsed / self.swing_duration, 1.0)

            def ease_out_back(t):
                c1 = 1.70158
                c3 = c1 + 1
                return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2

            t_eased = ease_out_back(t)

            def lerp(a, b, t):
                return a + (b - a) * t

            pre_swing_offset = 40
            swing_max_angle = getattr(self, 'swing_max_angle', 90)
            swing_phase = self.swing_phase

            if swing_phase == 1:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(0, -swing_max_angle - pre_swing_offset, t_eased)
                else:
                    swing_offset = lerp(0, swing_max_angle + pre_swing_offset, t_eased)
            elif swing_phase == 2:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(-swing_max_angle, swing_max_angle, t_eased)
                else:
                    swing_offset = lerp(swing_max_angle, -swing_max_angle, t_eased)
            elif swing_phase == 3:
                if math.cos(angle_rad) > 0:
                    swing_offset = lerp(swing_max_angle, 0, t_eased)
                else:
                    swing_offset = lerp(-swing_max_angle, 0, t_eased)
            # else swing_offset = 0

            adjusted_angle += swing_offset

        rotated_image = pygame.transform.rotate(scaled_weapon, -adjusted_angle)
        rotated_rect = rotated_image.get_rect()

        # --- Smooth interpolation for offsets ---
        # Store previous offsets for interpolation
        if not hasattr(self, '_prev_horizontal_offset'):
            self._prev_horizontal_offset = 0
        if not hasattr(self, '_prev_lower_offset'):
            self._prev_lower_offset = 0

        target_horizontal_offset = -20 * zoom if math.cos(angle_rad) < 0 else 20 * zoom
        target_lower_offset = -10 * zoom if math.sin(angle_rad) < 0 else 10 * zoom

        interp_speed = 0.18  # smaller = slower, larger = snappier
        # Use time-based interpolation for smoothness
        dt = 1 / 60  # Assume 60 FPS if dt not provided
        if hasattr(self, 'last_interp_time'):
            now = time.time()
            dt = min(now - self.last_interp_time, 0.05)
            self.last_interp_time = now
        else:
            self.last_interp_time = time.time()

        def lerp(a, b, t):
            return a + (b - a) * t

        lerp_factor = 1 - math.exp(-interp_speed * dt * 60)  # frame-rate independent
        horizontal_offset = lerp(self._prev_horizontal_offset, target_horizontal_offset, lerp_factor)
        lower_offset = lerp(self._prev_lower_offset, target_lower_offset, lerp_factor)
        self._prev_horizontal_offset = horizontal_offset
        self._prev_lower_offset = lower_offset

        draw_x = player_center[0] - camera_x + horizontal_offset - rotated_rect.width / 2
        draw_y = player_center[1] - camera_y + lower_offset - rotated_rect.height / 2
        surface.blit(rotated_image, (draw_x, draw_y))

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        return super().render_static(surface, center, camera_x, camera_y, zoom)
    
    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        # Static weapons don't animate, but we can update their state if needed
        pass

class DoublePistol(RangedWeapon):
    def __init__(self):
        # Load both sprites: pistol (static) and pistol_hold (when held)
        pistol_path = "game/assets/sprites/weapons/pistol/pistol.png"
        pistol_hold_path = "game/assets/sprites/weapons/pistol/pistol_hold.png"
        super().__init__(
            name="Pistol",
            sprite_path=pistol_path,
            color=(150, 150, 255),
            damage=6,
            fire_rate=2.0,  # 2 shots per second
            projectile_speed=500
        )
        # Load both sprites
        try:
            self.sprite_pistol = pygame.image.load(pistol_path).convert_alpha()
        except Exception:
            self.sprite_pistol = None
        try:
            self.sprite_pistol_hold = pygame.image.load(pistol_hold_path).convert_alpha()
        except Exception:
            self.sprite_pistol_hold = None
        # Default sprite is pistol (for static display)
        self.sprite = self.sprite_pistol
        self.recoil_offset = 0
        self.recoil_timer = 0
        self.recoil_duration = 0.1  # segundos
        self.recoil_strength = 5

        # Separate muzzle origins for left and right pistols (relative to each weapon sprite)
        self.muzzle_origin_left = (22, 56)   # Example values, adjust as needed
        self.muzzle_origin_right = (34, 56)  # Example values, adjust as needed

        if self.sprite:
            self.origin = (0, self.sprite.get_height())

    def get_muzzle_pos(self, hand_pos, angle, zoom=1.0, hand="left"):
        if not self.sprite:
            return hand_pos

        original_rect = self.sprite.get_rect()
        base_width = 64
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)

        # Escolha a origem do muzzle
        aiming_left = math.cos(angle) < 0
        use_hand = "right" if aiming_left and hand == "left" else "left" if aiming_left and hand == "right" else hand
        muzzle_origin = self.muzzle_origin_left if use_hand == "left" else self.muzzle_origin_right

        # Calcule vetor offset do centro da sprite até o muzzle
        # (0,0) é o canto superior esquerdo. Precisamos de vetores relativos ao centro.
        muzzle_vec = pygame.math.Vector2(muzzle_origin[0], muzzle_origin[1])
        origin_vec = pygame.math.Vector2(self.origin[0], self.origin[1])
        offset = muzzle_vec - origin_vec

        # Escale o offset
        offset.x *= scale_width / original_rect.width
        offset.y *= scale_height / original_rect.height

        # Rotacione o offset com o ângulo (em graus)
        offset = offset.rotate(math.degrees(angle))

        # Adicione ao ponto da mão
        final_pos = (hand_pos[0] + offset.x, hand_pos[1] + offset.y)
        return final_pos


    def attack(self, player_center, angle, enemies=None, projectiles=None, zoom=1.0):
        if not self.can_attack():
            return False
        self.last_attack_time = time.time()
        self.recoil_timer = self.recoil_duration
        if projectiles is None:
            return False
        horizontal_offset = 20  # Offset for the left and right hand bullets
        hands = ["left", "right"]
        offsets = [-horizontal_offset, horizontal_offset]
        for hand, offset in zip(hands, offsets):
            hand_x = player_center[0] + math.cos(angle + math.pi/2) * offset
            hand_y = player_center[1] + math.sin(angle + math.pi/2) * offset
            muzzle_pos = self.get_muzzle_pos((hand_x, hand_y), angle, zoom, hand=hand)
            proj = Bullet(
                x=muzzle_pos[0],
                y=muzzle_pos[1],
                angle=angle,
                speed=self.projectile_speed,
                damage=self.damage
            )
            projectiles.append(proj)
        return True


    def update(self, dt):
        if self.recoil_timer > 0:
            self.recoil_timer -= dt
            self.recoil_offset = self.recoil_strength * (self.recoil_timer / self.recoil_duration)
        else:
            self.recoil_offset = 0
        
    def render(self, surface, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, held=True, debug_muzzle=False):
        # Use the same logic as Pistol, but draw two pistols with mirrored horizontal_offset and correct rotation
        sprite = self.sprite_pistol_hold if held and self.sprite_pistol_hold is not None else self.sprite_pistol
        if not sprite:
            return
        original_rect = sprite.get_rect()
        base_width = 64
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)

        adjusted_angle = math.degrees(angle)
        angle_rad = math.radians(adjusted_angle)
        aiming_left = math.cos(angle) < 0

        # For both hands, use correct muzzle origin and swap if aiming left
        hands = ["left", "right"]
        hand_signs = [1, -1]
        for hand, hand_sign in zip(hands, hand_signs):
            # Swap muzzle origin for hand if aiming left
            use_hand = "right" if (aiming_left and hand == "left") else ("left" if (aiming_left and hand == "right") else hand)
            if use_hand == "left":
                muzzle_origin = self.muzzle_origin_left
                
            else:
                muzzle_origin = self.muzzle_origin_right

            # --- Swing animation (copied from Pistol) ---
            hand_angle_rad = angle_rad
            hand_angle_deg = math.degrees(hand_angle_rad)
            swing_offset = 0
            if hasattr(self, 'swing_phase') and self.swing_phase != 0:
                elapsed = time.time() - self.swing_start_time
                t = min(elapsed / self.swing_duration, 1.0)
                def ease_out_back(t):
                    c1 = 1.70158
                    c3 = c1 + 1
                    return 1 + c3 * (t - 1)**3 + c1 * (t - 1)**2
                t_eased = ease_out_back(t)
                def lerp(a, b, t):
                    return a + (b - a) * t
                pre_swing_offset = 40
                swing_max_angle = getattr(self, 'swing_max_angle', 90)
                swing_phase = self.swing_phase
                if swing_phase == 1:
                    if math.cos(hand_angle_rad) > 0:
                        swing_offset = lerp(0, -swing_max_angle - pre_swing_offset, t_eased)
                    else:
                        swing_offset = lerp(0, swing_max_angle + pre_swing_offset, t_eased)
                elif swing_phase == 2:
                    if math.cos(hand_angle_rad) > 0:
                        swing_offset = lerp(-swing_max_angle, swing_max_angle, t_eased)
                    else:
                        swing_offset = lerp(swing_max_angle, -swing_max_angle, t_eased)
                elif swing_phase == 3:
                    if math.cos(hand_angle_rad) > 0:
                        swing_offset = lerp(swing_max_angle, 0, t_eased)
                    else:
                        swing_offset = lerp(-swing_max_angle, 0, t_eased)
                hand_angle_deg += swing_offset

            # --- Smooth interpolation for offsets (copied from Pistol) ---
            interp_key = f"_prev_horizontal_offset_{hand}"
            interp_key_lower = f"_prev_lower_offset_{hand}"
            if not hasattr(self, interp_key):
                setattr(self, interp_key, 0)
            if not hasattr(self, interp_key_lower):
                setattr(self, interp_key_lower, 0)
            target_horizontal_offset = (20 * zoom) * hand_sign if math.cos(angle_rad) >= 0 else (-20 * zoom) * hand_sign
            target_lower_offset = -10 * zoom if math.sin(angle_rad) < 0 else 10 * zoom
            interp_speed = 0.18
            dt = 1 / 60
            interp_time_key = f"last_interp_time_{hand}"
            if hasattr(self, interp_time_key):
                now = time.time()
                dt = min(now - getattr(self, interp_time_key), 0.05)
                setattr(self, interp_time_key, now)
            else:
                setattr(self, interp_time_key, time.time())
            def lerp(a, b, t):
                return a + (b - a) * t
            prev_horizontal_offset = getattr(self, interp_key)
            prev_lower_offset = getattr(self, interp_key_lower)
            lerp_factor = 1 - math.exp(-interp_speed * dt * 60)
            horizontal_offset = lerp(prev_horizontal_offset, target_horizontal_offset, lerp_factor)
            lower_offset = lerp(prev_lower_offset, target_lower_offset, lerp_factor)
            setattr(self, interp_key, horizontal_offset)
            setattr(self, interp_key_lower, lower_offset)

            # --- Rotate and flip sprite as in Pistol ---
            scaled_weapon = pygame.transform.scale(sprite, (scale_width, scale_height))
            flip = math.cos(hand_angle_rad) < 0
            if flip:
                scaled_weapon = pygame.transform.flip(scaled_weapon, False, True)
            rotated_image = pygame.transform.rotate(scaled_weapon, -hand_angle_deg)
            rotated_rect = rotated_image.get_rect()

            # Calculate muzzle offset for this hand
            mx = muzzle_origin[0] * (scale_width / original_rect.width)
            my = muzzle_origin[1] * (scale_height / original_rect.height)
            ox = self.origin[0] * (scale_width / original_rect.width)
            oy = self.origin[1] * (scale_height / original_rect.height)
            offset = pygame.math.Vector2(mx - ox, my - oy)
            offset_rot = offset.rotate(hand_angle_deg)

            draw_x = player_center[0] - camera_x + horizontal_offset - rotated_rect.width / 2
            draw_y = player_center[1] - camera_y + lower_offset - rotated_rect.height / 2
            # Adjust for muzzle offset so the muzzle is always at the correct place
            draw_x += offset_rot.x
            draw_y += offset_rot.y
            surface.blit(rotated_image, (draw_x, draw_y))

            # --- DEBUG: Draw muzzle_origin as a red circle ---
            if debug_muzzle:
                muzzle_screen_x = draw_x + rotated_rect.width / 2
                muzzle_screen_y = draw_y + rotated_rect.height / 2
                pygame.draw.circle(surface, (255, 0, 0), (int(muzzle_screen_x), int(muzzle_screen_y)), max(2, int(4 * zoom)))

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        """Render the static version of the double pistol: draw two pistols, each with bobbing and shadow, no center sprite."""
        if not self.sprite_pistol:
            return
        sprite = self.sprite_pistol
        original_rect = sprite.get_rect()
        base_width = 64
        scale_width = int((base_width * 0.5) * zoom)
        scale_height = int(scale_width * original_rect.height / original_rect.width)
        offset = 18 * zoom  # horizontal offset between pistols
        # Bobbing effect: vertical offset based on time
        bob_amplitude = 10 * zoom  # pixels
        bob_speed = 0.3  # cycles per second
        t = time.time() % 1000
        bob_offset = math.sin(t * bob_speed * math.pi * 2) * bob_amplitude
        # Shadow parameters
        shadow_color = (0, 0, 0, 80)  # RGBA, semi-transparent
        shadow_radius = int(scale_width * 0.45)
        # Draw both pistols with bobbing and shadow
        for sign in [-1, 1]:
            pistol_center = (center[0] + sign * offset, center[1])
            # Shadow
            shadow_center = (int(pistol_center[0]), int(pistol_center[1] + scale_height // 2 + 1 * zoom))
            shadow_surface = pygame.Surface((shadow_radius * 2, shadow_radius * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surface, shadow_color, (0, shadow_radius // 2, shadow_radius * 2, shadow_radius))
            surface.blit(shadow_surface, (shadow_center[0] - shadow_radius, shadow_center[1] - shadow_radius // 2))
            # Bobbing
            scaled_sprite = pygame.transform.scale(sprite, (scale_width, scale_height))
            rect = scaled_sprite.get_rect(center=(pistol_center[0], pistol_center[1] + bob_offset))
            surface.blit(scaled_sprite, rect.topleft)
    
    def update_static(self, dt):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
        # Static weapons don't animate, but we can update their state if needed
        pass