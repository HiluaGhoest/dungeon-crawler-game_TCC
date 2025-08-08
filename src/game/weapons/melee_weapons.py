import pygame
import math
import time
import random
from game.weapons.weapon import Weapon

class MeleeWeapon(Weapon):
    def can_deal_damage(self):
        """Returns True if weapon is in the damage-dealing phase (phase 3)."""
        return self.swing_phase == 3
    def __init__(self, name, sprite_path=None, color=(200, 100, 100), damage=10, attack_range=80):
        super().__init__(name, sprite_path, color)
        self.damage = damage
        self.attack_range = attack_range
        # Swing animation state
        self.swing_progress = 0
        self.swing_duration = 0.25  # seconds
        self.swing_start_time = 0
        self.swing_max_angle = 90
        self.swing_phase = 0  # 0 = none, 1 = forward, 2 = backward, 3 = finish

    def can_attack(self):
        return (time.time() - self.last_attack_time) >= getattr(self, 'swing_cooldown', 1.0)

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

class SteelSword(MeleeWeapon):
    def can_deal_damage(self):
        """Returns True if sword is in the damage-dealing phase (phase 2)."""
        return self.swing_phase == 2
    def __init__(self):
        super().__init__(name="Steel Sword", sprite_path=None, color=(220, 220, 60))
        from game.assets import get_image
        self.sprites = [
            get_image("steel_sword_1", "game/assets/sprites/weapons/steel_sword/steel_sword_1.png"),
            get_image("steel_sword_2", "game/assets/sprites/weapons/steel_sword/steel_sword_2.png"),
            get_image("steel_sword_3", "game/assets/sprites/weapons/steel_sword/steel_sword_3.png"),
        ]
        self.sprite = self.sprites[0]  # Default sprite
        self.current_frame = 0
        self.frame_duration = 0.15  # Time between frames in seconds
        self.frame_timer = 0
        self.is_swinging = False
        self.origin = (self.sprites[0].get_width() // 2, self.sprites[0].get_height())
        self.damage = 15
        # Calculate swing_cooldown to match animation duration
        phase1_hold_time = 0.3  # must match value in update()
        swing_duration = getattr(self, 'swing_duration', 0.25)
        self.swing_cooldown = swing_duration * 3 + phase1_hold_time
        # Trail effect
        self.trails = []  # Each trail: {pos, time, alpha}
        self.trail_spawn_interval = 0.1
        self.trail_timer = 0
        self.trail_lifetime = 0.1  # seconds
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

        # --- Smooth interpolation for offsets (like Pistol/DoublePistol) ---
        if not hasattr(self, '_prev_horizontal_offset'):
            self._prev_horizontal_offset = 0
        if not hasattr(self, '_prev_lower_offset'):
            self._prev_lower_offset = 0

        target_horizontal_offset = -20 * zoom if math.cos(angle_rad) < 0 else 20 * zoom
        target_lower_offset = -10 * zoom if math.sin(angle_rad) < 0 else 10 * zoom

        interp_speed = 0.18
        # Use time-based interpolation for smoothness
        dt_interp = 1 / 60
        if hasattr(self, 'last_interp_time'):
            now = time.time()
            dt_interp = min(now - self.last_interp_time, 0.05)
            self.last_interp_time = now
        else:
            self.last_interp_time = time.time()

        lerp_factor = 1 - math.exp(-interp_speed * dt_interp * 60)
        horizontal_offset = lerp(self._prev_horizontal_offset, target_horizontal_offset, lerp_factor)
        lower_offset = lerp(self._prev_lower_offset, target_lower_offset, lerp_factor)
        self._prev_horizontal_offset = horizontal_offset
        self._prev_lower_offset = lower_offset

        rotated_sprite = pygame.transform.rotate(scaled_sprite, -adjusted_angle)
        rotated_rect = rotated_sprite.get_rect()
        image_center = pygame.math.Vector2(scale_width / 2, scale_height / 2)
        origin = pygame.math.Vector2(origin_x, origin_y)
        offset = origin - image_center
        offset_rotated = offset.rotate(adjusted_angle)
        blit_pos_world = pygame.math.Vector2(player_center) - pygame.math.Vector2(rotated_rect.width / 2, rotated_rect.height / 2) - offset_rotated
        draw_x = blit_pos_world.x - camera_x + horizontal_offset
        draw_y = blit_pos_world.y - camera_y + lower_offset

        # --- TRAIL EFFECT ---
        def lerp_color(color1, color2, t):
            return tuple(int(c1 + (c2 - c1) * t) for c1, c2 in zip(color1, color2))

        fire_colors = [
            (128, 0, 128),      # deep purple (base)
            (186, 85, 211),     # medium purple
            (221, 160, 221),    # lavender
            (255, 255, 255)     # bright white (core / tip)
        ]

        self.trail_timer += dt
        tip_length = random.uniform(-scale_height * 0.5, scale_height * 0.5)
        tip_offset = pygame.math.Vector2(0, -tip_length)
        tip_offset = tip_offset.rotate(adjusted_angle)
        tip_pos = pygame.math.Vector2(draw_x + scale_width/2, draw_y + scale_height/2) + tip_offset

        def smoothstep(t):
            return t * t * (3 - 2 * t)

        smoothing_factor = 0.1
        if self.last_tip_pos is not None:
            dist = (tip_pos - self.last_tip_pos).length()
            self.last_tip_pos = self.last_tip_pos.lerp(tip_pos, smoothing_factor)
            if dist > 0:
                min_steps = 8
                max_steps = 24
                steps = random.randint(min_steps, max_steps)
                for i in range(1, steps+1):
                    interp_factor = smoothstep(i/steps)
                    interp = self.last_tip_pos.lerp(tip_pos, interp_factor)
                    tip_length = random.uniform(0, scale_height * 0.25)
                    tip_offset = pygame.math.Vector2(0, -tip_length)
                    tip_offset = tip_offset.rotate(adjusted_angle)
                    trail_pos = interp + tip_offset
                    self.trails.append({'pos': trail_pos, 'time': 0, 'alpha': 255, 'interp': interp_factor, 'interp_pos': interp})
        else:
            offset_spread = 5 * zoom
            rand_offset = pygame.math.Vector2(
                random.uniform(-offset_spread, offset_spread),
                random.uniform(-offset_spread, offset_spread)
            )
            tip_length = random.uniform(0, scale_height * 0.25)
            tip_offset = pygame.math.Vector2(0, -tip_length)
            tip_offset = tip_offset.rotate(adjusted_angle)
            interp = tip_pos
            trail_pos = tip_offset + rand_offset
            self.trails.append({'pos': trail_pos, 'time': 0, 'alpha': 255, 'interp': 1.0, 'interp_pos': interp})
            self.last_tip_pos = tip_pos

        for trail in self.trails:
            fade = 1.0 - (trail['time'] / self.trail_lifetime)
            fade = fade * fade
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

