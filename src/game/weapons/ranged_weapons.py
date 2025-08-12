import pygame
import math
import time
from game.weapons.weapon import PistolBullet, Projectile, Weapon
from sound_manager import SoundManager

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
            damage=self.damage,
            weapon=self
        )
        projectiles.append(proj)
        # Effects will be applied on projectile hit (handled elsewhere)
        return True
    
    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1):
        return super().render_static(surface, center, camera_x, camera_y, zoom)
    
    def update_static(self, dt, **kwargs):
        """Update logic for static weapons (e.g., those displayed on pillars). Override in subclasses if needed."""
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

        from game.assets import get_image
        self.sprite_pistol = get_image("sprite_pistol", pistol_path)
        self.sprite_pistol_hold = get_image("sprite_pistol_hold", pistol_hold_path)

        
        # Load both sprites
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


    def get_muzzle_pos(self, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, hand_pos=None):
        # This function returns both world and screen position of the muzzle, matching the render logic
        sprite = self.sprite_pistol_hold if self.sprite_pistol_hold else self.sprite
        if not sprite:
            return hand_pos

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
        # Play gunfire sound
        from game.assets import load_audio
        gunfire_sound = load_audio("game/sounds/effects/gunfire.mp3")
        gunfire_sound.set_volume(0.5)  # Set volume (0.0 to 1.0)
        if gunfire_sound:
            SoundManager.get_instance().play_sfx(gunfire_sound)

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

        proj = PistolBullet(
            x=muzzle_world_x,
            y=muzzle_world_y,
            angle=angle,
            speed=self.projectile_speed,
            damage=self.damage,
            weapon=self
        )
        projectiles.append(proj)
        print(f"Firing {self.name}! Projectiles count: {len(projectiles)}")
        print(f"Calling attack with muzzle_pos: {(muzzle_world_x, muzzle_world_y)}")
        # Effects will be applied on projectile hit (handled elsewhere)
        return True


    def update(self, dt, **kwargs):
        if self.recoil_timer > 0:
            self.recoil_timer -= dt
            self.recoil_offset = self.recoil_strength * (self.recoil_timer / self.recoil_duration)
        else:
            self.recoil_offset = 0

    def render(self, surface, player_center, angle, camera_x=0, camera_y=0, zoom=1.0, held=True):
        # Use pistol_hold sprite if held, else pistol sprite
        sprite = self.sprite_pistol_hold if self.sprite_pistol_hold is not None else self.sprite_pistol
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

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1.0, size=None):
        """Render the static version of the pistol, supporting dropped/static weapon scaling."""
        if not self.sprite_pistol:
            return
        sprite = self.sprite_pistol
        original_rect = sprite.get_rect()
        # Use provided size for dropped/static weapons, else fallback to previous logic
        if size is not None:
            scale_width = int(size * zoom)
            scale_height = int(scale_width * original_rect.height / original_rect.width)
        else:
            base_width = 64
            scale_width = int((base_width * 0.5) * zoom)
            scale_height = int(scale_width * original_rect.height / original_rect.width)
        # Bobbing effect: vertical offset based on time
        bob_amplitude = 10 * zoom  # pixels
        bob_speed = 0.3  # cycles per second
        t = time.time() % 1000
        bob_offset = math.sin(t * bob_speed * math.pi * 2) * bob_amplitude
        # Shadow parameters
        shadow_color = (0, 0, 0, 80)  # RGBA, semi-transparent
        shadow_radius = int(scale_width * 0.45)
        pistol_center = (center[0], center[1])
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

class DoublePistol(RangedWeapon):
    def render_hud_sprite(self, surface, rect, sprite_size):
        """Draw two pistol sprites stacked vertically with a small offset in the HUD slot."""
        if not self.sprite_pistol:
            return
        center_x, center_y = rect.center
        vertical_offset = int(sprite_size * 0.22)
        scaled_sprite = pygame.transform.smoothscale(self.sprite_pistol, (sprite_size, sprite_size))
        # Draw top pistol
        top_rect = scaled_sprite.get_rect(center=(center_x, center_y - vertical_offset))
        surface.blit(scaled_sprite, top_rect)
        # Draw bottom pistol
        bottom_rect = scaled_sprite.get_rect(center=(center_x, center_y + vertical_offset))
        surface.blit(scaled_sprite, bottom_rect)
    def __init__(self):
        # Load both sprites: pistol (static) and pistol_hold (when held)
        pistol_path = "game/assets/sprites/weapons/pistol/pistol.png"
        pistol_hold_path = "game/assets/sprites/weapons/pistol/pistol_hold.png"
        super().__init__(
            name="Double Pistol",
            sprite_path=pistol_path,
            color=(150, 150, 255),
            damage=6,
            fire_rate=2.0,  # 2 shots per second
            projectile_speed=500
        )
        # Load both sprites using get_image for PyInstaller compatibility
        from game.assets import get_image
        self.sprite_pistol = get_image("sprite_pistol", pistol_path)
        self.sprite_pistol_hold = get_image("sprite_pistol_hold", pistol_hold_path)

        
        if self.sprite_pistol_hold:
            rect = self.sprite_pistol_hold.get_rect()
            self.origin = (rect.width // 2, rect.height)  # bottom center
        elif self.sprite:
            rect = self.sprite.get_rect()
            self.origin = (rect.width // 2, rect.height)
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
            rect = self.sprite.get_rect()
            self.origin = (rect.width // 2, rect.height)  # bottom center

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
        offset = offset.rotate(-math.degrees(angle))

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
        # Play gunfire sound twice
        from game.assets import load_audio
        gunfire_sound = load_audio("game/sounds/effects/gunfire.mp3")
        if gunfire_sound:
            SoundManager.get_instance().play_sfx(gunfire_sound)
            import threading
            def play_second():
                import time
                time.sleep(0.08)  # 80ms delay for double shot effect
                SoundManager.get_instance().play_sfx(gunfire_sound)
            threading.Thread(target=play_second, daemon=True).start()
        # Reconstruct conversion position from player_center and angle
        conversion_distance = 250
        conversion_pos = (
            player_center[0] + math.cos(angle) * conversion_distance,
            player_center[1] + math.sin(angle) * conversion_distance
        )

        aiming_left = math.cos(angle) < 0
        angle_rad = angle

        hands = ["left", "right"]
        hand_signs = [1, -1]
        for hand, hand_sign in zip(hands, hand_signs):
            # --- Copy offset logic from render ---
            target_horizontal_offset = (20 * zoom) * hand_sign if math.cos(angle_rad) >= 0 else (-20 * zoom) * hand_sign
            target_lower_offset = -10 * zoom if math.sin(angle_rad) < 0 else 10 * zoom

            hand_pos = (
                player_center[0] + target_horizontal_offset,
                player_center[1] + target_lower_offset
            )

            muzzle_pos = self.get_muzzle_pos(hand_pos, angle, zoom=zoom, hand=hand)

            # Calculate angle from barrel to conversion position
            dx = conversion_pos[0] - muzzle_pos[0]
            dy = conversion_pos[1] - muzzle_pos[1]
            bullet_angle = math.atan2(dy, dx)

            proj = PistolBullet(
                x=muzzle_pos[0],
                y=muzzle_pos[1],
                angle=bullet_angle,
                speed=self.projectile_speed,
                damage=self.damage,
                weapon=self
            )
            projectiles.append(proj)
            # Effects will be applied on projectile hit (handled elsewhere)


    def update(self, dt, **kwargs):
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

    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1.0, size=None):
        """Render the static version of the double pistol: draw two pistols, each with bobbing and shadow, no center sprite."""
        if not self.sprite_pistol:
            return
        sprite = self.sprite_pistol
        original_rect = sprite.get_rect()
        # Use provided size for dropped/static weapons, else fallback to previous logic
        if size is not None:
            scale_width = int(size * zoom)
            scale_height = int(scale_width * original_rect.height / original_rect.width)
            offset = int(size * 0.55 * zoom)  # horizontal offset between pistols, proportional to size
        else:
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