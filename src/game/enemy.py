import random
import pygame
import math
import time
from . import assets

class Enemy:
    # Preload death sound as a class variable
    death_sound = assets.load_audio('game/sounds/effects/slime_death.wav')

    def __init__(self, x, y, health=10, size=24, color=(255, 0, 60)):
        self.x = x
        self.y = y
        self.health = health
        self.size = size
        self.color = color
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        # Animations
        self.eye_bob_timer = 0.0
        self.eye_bob_amplitude = 0.5
        self.eye_bob_speed = 0.01
        self.blink_timer = 0.0
        self.blink_interval = 3.0
        self.blink_duration = 0.2
        self.is_blinking = False
        # Footprints
        self.footprints = []
        self._last_footprint_pos = (self.x, self.y)
        self._footprint_distance = 18
        self._footprint_side = "left"

        # Floating damage numbers: list of (damage, timestamp, x, y)
        self.floating_damage = []
        # Flash white effect
        self.flash_timer = 0.0
        self.flash_duration = 0.15
        # Blood splatter effect
        self.blood_splatters = []  # List of dicts: {x, y, dx, dy, timer}

        # Velocidade atual (para steering)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 1  # Velocidade base do inimigo (pixels por segundo)
        # Quão rápido ele ajusta a direção (0.0 a 1.0)
        self.steer_strength = 0.1
        # Spawning animation
        self.spawning = True
        self.spawn_timer = 0.0
        self.spawn_duration = random.uniform(0.5, 4.0)
        self.removed = False

        self.damage = 5

    def _get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def take_damage(self, amount, hit_direction=None):
        # Ignore damage if already dying or spawning
        if getattr(self, 'is_dead', False) or getattr(self, 'spawning', False):
            return
        self.health -= amount
        # Add floating damage number
        self.floating_damage.append({
            'damage': amount,
            'timestamp': time.time(),
            'x': self.x + self.size // 2,
            'y': self.y,
            'alpha': 255,
            'offset': 0
        })
        # Start flash white effect
        self.flash_timer = self.flash_duration
        # Add blood splatter effect and knockback
        if hit_direction is not None:
            for _ in range(random.randint(3, 6)):
                angle = math.atan2(hit_direction[1], hit_direction[0]) + random.uniform(-0.5, 0.5)
                speed = random.uniform(4, 8)
                dx = math.cos(angle) * speed
                dy = math.sin(angle) * speed
                self.blood_splatters.append({
                    'x': self.x + self.size // 2,
                    'y': self.y + self.size // 2,
                    'dx': dx,
                    'dy': dy,
                    'timer': 0.0,
                    'duration': random.uniform(0.3, 0.7)
                })
            # Knockback effect
            knockback_strength = 8.0
            self.vx += hit_direction[0] * knockback_strength
            self.vy += hit_direction[1] * knockback_strength
        if self.health <= 0:
            self.die()

    def die(self):
        # Play death sound effect
        if Enemy.death_sound:
            Enemy.death_sound.play()
        # Pixel Explosion Death Animation
        self.is_dead = True
        self.death_timer = 0.0
        self.death_duration = 0.5  # tempo total da animação
        self.death_flash_frames = 2  # frames de flash branco
        self.death_chunks = []
        n_chunks = random.randint(4, 6)
        base_color = tuple(max(0, int(c * 0.8)) for c in self.color)  # cor mais escura
        center_x = self.x + self.size // 2
        center_y = self.y + self.size // 2
        for i in range(n_chunks):
            angle = 2 * math.pi * i / n_chunks + random.uniform(-0.2, 0.2)
            speed = random.uniform(5, 11)
            chunk_size = self.size // 3
            chunk_x = center_x - chunk_size // 2
            chunk_y = center_y - chunk_size // 2
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            self.death_chunks.append({
                'x': chunk_x,
                'y': chunk_y,
                'dx': dx,
                'dy': dy,
                'size': chunk_size,
                'color': base_color,
                'alpha': 255,
                'timer': 0.0
            })

    def update(self, dt=0.016, player_pos=None, other_enemies=None, player=None):
        if player and hasattr(player, 'engine') and player.engine.is_paused:
            return
        # Death animation: pixel explosion
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer'):
            self.death_timer += dt
            # Flash branco nos primeiros frames
            if hasattr(self, 'death_flash_frames') and self.death_timer < 0.05 * self.death_flash_frames:
                pass  # só flash, chunks não se movem
            elif hasattr(self, 'death_chunks'):
                for chunk in self.death_chunks:
                    chunk['x'] += chunk['dx'] * dt * 60
                    chunk['y'] += chunk['dy'] * dt * 60
                    chunk['timer'] += dt
                    # Fade out
                    chunk['alpha'] = max(0, 255 - int((chunk['timer'] / self.death_duration) * 255))
            if self.death_timer >= self.death_duration:
                self.death_timer = self.death_duration
                # Remove enemy do room/enemy list após animação
                room = getattr(self, 'room', None)
                if room and hasattr(room, 'enemies') and self in room.enemies:
                    room.enemies.remove(self)
                else:
                    engine = getattr(self, 'engine', None)
                    if engine and hasattr(engine, 'enemies') and self in engine.enemies:
                        engine.enemies.remove(self)
            return
        # Update spawn animation
        if self.spawning:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_duration:
                self.spawning = False
            return
        # Update flash timer
        if self.flash_timer > 0.0:
            self.flash_timer -= dt
            if self.flash_timer < 0.0:
                self.flash_timer = 0.0
        # Update blood splatters
        for splat in self.blood_splatters[:]:
            splat['x'] += splat['dx'] * dt * 60
            splat['y'] += splat['dy'] * dt * 60
            splat['timer'] += dt
            if splat['timer'] > splat['duration']:
                self.blood_splatters.remove(splat)
        # Group behavior: calculate offset angle for flanking
        group_angle_offset = 0.0
        if other_enemies and player_pos is not None:
            # Find this enemy's index in the group
            try:
                idx = other_enemies.index(self)
            except ValueError:
                idx = 0
            # Spread angles from -30 to +30 degrees for up to 5 enemies
            max_spread = 30  # degrees
            n = min(len(other_enemies), 5)
            if n > 1:
                group_angle_offset = ((idx - (n-1)/2) / (n-1)) * max_spread
            else:
                group_angle_offset = 0.0
        # Animações e pegadas
        self.eye_bob_timer += dt
        if self.eye_bob_timer > 1.0 / self.eye_bob_speed:
            self.eye_bob_timer -= 1.0 / self.eye_bob_speed

        self.blink_timer += dt
        if not self.is_blinking and self.blink_timer >= self.blink_interval:
            self.is_blinking = True
            self.blink_timer = 0.0
        elif self.is_blinking and self.blink_timer >= self.blink_duration:
            self.is_blinking = False
            self.blink_timer = 0.0

        # IA: Persegue o jogador se player_pos for fornecido
        if player_pos is not None:
            px, py = player_pos
            dx = px - self.x
            dy = py - self.y
            dist = math.hypot(dx, dy)
            # Apply group offset to target position
            if dist > 0 and group_angle_offset != 0.0:
                angle_to_player = math.atan2(dy, dx)
                offset_angle_rad = math.radians(group_angle_offset)
                flank_dist = min(64, dist * 0.5)  # how far to flank from player
                flank_x = px + math.cos(angle_to_player + offset_angle_rad) * flank_dist
                flank_y = py + math.sin(angle_to_player + offset_angle_rad) * flank_dist
                dx = flank_x - self.x
                dy = flank_y - self.y
                dist = math.hypot(dx, dy)

            # 1) Vetor de separação
            sep_x = sep_y = 0.0
            sep_radius = self.size
            if other_enemies:
                for other in other_enemies:
                    if other is self: continue
                    ox, oy = other.x, other.y
                    dx_sep = self.x - ox
                    dy_sep = self.y - oy
                    d = math.hypot(dx_sep, dy_sep)
                    if 0 < d < sep_radius:
                        # força inversamente proporcional à distância
                        strength = (sep_radius - d) / sep_radius
                        sep_x += (dx_sep / d) * strength
                        sep_y += (dy_sep / d) * strength

            # 2) Vetor desejado ao jogador
            if dist > 2:
                to_player_x = dx / dist
                to_player_y = dy / dist
            else:
                to_player_x = to_player_y = 0

            # 3) Combine e normalize
            separation_weight = 20
            desired_x = to_player_x + sep_x * separation_weight * 0.01
            desired_y = to_player_y + sep_y * separation_weight * 0.01
            d_desired = math.hypot(desired_x, desired_y)
            if d_desired > 0:
                desired_x /= d_desired
                desired_y /= d_desired

            # 4) Steering: ajuste suave da velocidade atual em direção ao desejado
            self.vx += (desired_x * self.speed - self.vx) * self.steer_strength
            self.vy += (desired_y * self.speed - self.vy) * self.steer_strength

            # 5) Atualiza posição
            new_x = self.x + self.vx * dt * 60
            new_y = self.y + self.vy * dt * 60
            new_rect = pygame.Rect(new_x, new_y, self.size, self.size)
            # Salva a posição futura para checagem global
            self.next_pos = (new_x, new_y)
            # Checa colisão com outros inimigos (usando as posições futuras já salvas)
            can_move = True
            # Só verifica colisão com inimigos próximos (raio de 1.5x tamanho)
            if other_enemies:
                min_dist = self.size * 1.5
                for other in other_enemies:
                    if other is self:
                        continue
                    other_future_x, other_future_y = getattr(other, 'next_pos', (other.x, other.y))
                    dist_to_other = math.hypot(new_x - other_future_x, new_y - other_future_y)
                    if dist_to_other < min_dist:
                        other_rect = pygame.Rect(other_future_x, other_future_y, other.size, other.size)
                        if new_rect.colliderect(other_rect):
                            can_move = False
                            break
            # Checa colisão com jogador
            player_rect = pygame.Rect(px, py, self.size, self.size)
            if new_rect.colliderect(player_rect):
                can_move = False
                if player is not None:
                    # Enemy deals damage to player on collision
                    if hasattr(player, 'take_damage'):
                        player.take_damage(self.damage)  # You can adjust damage value as needed
            # Só move se não houver colisão
            if can_move:
                self.x = new_x
                self.y = new_y
                self.rect.topleft = (self.x, self.y)
            # Limpa a posição futura após o movimento
            if hasattr(self, 'next_pos'):
                del self.next_pos
            # If blocked, try to slide around obstacle (perpendicular movement)
            if not can_move:
                # Calculate perpendicular direction to player
                perp_x = -to_player_y
                perp_y = to_player_x
                # Try both perpendicular directions
                slide_attempts = [
                    (self.x + perp_x * self.speed * dt * 60, self.y + perp_y * self.speed * dt * 60),
                    (self.x - perp_x * self.speed * dt * 60, self.y - perp_y * self.speed * dt * 60)
                ]
                for sx, sy in slide_attempts:
                    slide_rect = pygame.Rect(sx, sy, self.size, self.size)
                    blocked = False
                    if other_enemies:
                        for other in other_enemies:
                            if other is self:
                                continue
                            other_future_x, other_future_y = getattr(other, 'next_pos', (other.x, other.y))
                            other_rect = pygame.Rect(other_future_x, other_future_y, other.size, other.size)
                            if slide_rect.colliderect(other_rect):
                                blocked = True
                                break
                    if slide_rect.colliderect(player_rect):
                        blocked = True
                        if player is not None:
                            if hasattr(player, 'take_damage'):
                                player.take_damage(1)
                    if not blocked:
                        self.x = sx
                        self.y = sy
                        self.rect.topleft = (self.x, self.y)
                        break

        # Pegadas
        moved_dist = ((self.x - self._last_footprint_pos[0]) ** 2 + (self.y - self._last_footprint_pos[1]) ** 2) ** 0.5
        if moved_dist > self._footprint_distance:
            offset = self.size // 4
            dx = self.x - self._last_footprint_pos[0]
            dy = self.y - self._last_footprint_pos[1]
            angle = math.atan2(dy, dx) if dx != 0 or dy != 0 else 0
            perp_angle = angle + (math.pi / 2 if self._footprint_side == "left" else -math.pi / 2)
            fp_x = int(self.x + self.size // 2 + math.cos(perp_angle) * offset)
            fp_y = int(self.y + self.size // 2 + math.sin(perp_angle) * offset)
            self.footprints.append((fp_x, fp_y, time.time(), self._footprint_side))
            self._last_footprint_pos = (self.x, self.y)
            self._footprint_side = "right" if self._footprint_side == "left" else "left"

    def draw(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if getattr(self, 'removed', False):
            return
        # Death animation: pixel explosion
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer') and hasattr(self, 'death_chunks'):
            # Flash branco nos primeiros frames
            if self.death_timer < 0.05 * getattr(self, 'death_flash_frames', 2):
                render_x = self.x - camera_x
                render_y = self.y - camera_y
                enemy_rect = pygame.Rect(render_x, render_y, self.size, self.size)
                pygame.draw.rect(surface, (255, 255, 255, 255), enemy_rect, border_radius=6)
            else:
                for chunk in self.death_chunks:
                    chunk_surf = pygame.Surface((chunk['size'], chunk['size']), pygame.SRCALPHA)
                    pygame.draw.rect(chunk_surf, (*chunk['color'], chunk['alpha']), (0, 0, chunk['size'], chunk['size']))
                    draw_x = int(chunk['x'] - camera_x)
                    draw_y = int(chunk['y'] - camera_y)
                    surface.blit(chunk_surf, (draw_x, draw_y))
            # Render floating damage numbers mesmo durante a morte
            font = pygame.font.SysFont('arial', 18, bold=True)
            damage_lifetime = 0.7
            damage_rise = 30
            now = time.time()
            for dmg in self.floating_damage[:]:
                elapsed = now - dmg['timestamp']
                if elapsed > damage_lifetime:
                    self.floating_damage.remove(dmg)
                    continue
                alpha = max(0, 255 - int((elapsed / damage_lifetime) * 255))
                offset = int((elapsed / damage_lifetime) * damage_rise)
                dmg_text = font.render(str(dmg['damage']), True, (255, 50, 50))
                dmg_surf = pygame.Surface(dmg_text.get_size(), pygame.SRCALPHA)
                dmg_surf.blit(dmg_text, (0, 0))
                dmg_surf.set_alpha(alpha)
                draw_x = int(dmg['x'] - camera_x - dmg_text.get_width() // 2)
                draw_y = int(dmg['y'] - camera_y - 20 - offset)
                surface.blit(dmg_surf, (draw_x, draw_y))
            return
        # ...restante do draw original...
        # --- Render blood splatters ---
        for splat in self.blood_splatters:
            alpha = max(0, 180 - int((splat['timer'] / splat['duration']) * 180))
            radius = max(2, int(self.size // 8))
            blood_color = (180, 0, 30, alpha)
            pygame.draw.circle(surface, blood_color, (int(splat['x'] - camera_x), int(splat['y'] - camera_y)), radius)
        # --- Render footprints ---
        footprint_color = (255, 100, 180)
        footprint_radius = max(2, self.size // 6)
        max_footprints = 60
        fade_time = 1.0
        now = time.time()
        self.footprints = [fp for fp in self.footprints if now - fp[2] < fade_time]
        for fp_x, fp_y, fp_time, fp_side in self.footprints[-max_footprints:]:
            alpha = max(0, 255 - int((now - fp_time) / fade_time * 255))
            footprint_surf = pygame.Surface((footprint_radius*2, footprint_radius*2), pygame.SRCALPHA)
            pygame.draw.ellipse(
                footprint_surf,
                (*footprint_color, alpha),
                (0, footprint_radius//2, footprint_radius*2, footprint_radius)
            )
            if fp_side == "right":
                footprint_surf = pygame.transform.flip(footprint_surf, True, False)
            surface.blit(footprint_surf, (fp_x - footprint_radius - camera_x, fp_y - footprint_radius - camera_y))

        # --- Render floating damage numbers ---
        font = pygame.font.SysFont('arial', 18, bold=True)
        damage_lifetime = 0.7  # seconds
        damage_rise = 30  # pixels
        for dmg in self.floating_damage[:]:
            elapsed = now - dmg['timestamp']
            if elapsed > damage_lifetime:
                self.floating_damage.remove(dmg)
                continue
            # Fade out and move up
            alpha = max(0, 255 - int((elapsed / damage_lifetime) * 255))
            offset = int((elapsed / damage_lifetime) * damage_rise)
            dmg_text = font.render(str(dmg['damage']), True, (255, 50, 50))
            dmg_surf = pygame.Surface(dmg_text.get_size(), pygame.SRCALPHA)
            dmg_surf.blit(dmg_text, (0, 0))
            dmg_surf.set_alpha(alpha)
            draw_x = int(dmg['x'] - camera_x - dmg_text.get_width() // 2)
            draw_y = int(dmg['y'] - camera_y - 20 - offset)
            surface.blit(dmg_surf, (draw_x, draw_y))

        # --- Spawning animation: scale up ---
        spawn_scale = 1.0
        if self.spawning:
            t = min(self.spawn_timer / self.spawn_duration, 1.0)
            spawn_scale = 0.2 + 0.8 * (1 - pow(1-t, 3))
            death_alpha = 255
        else:
            death_alpha = 255

        # --- Render enemy body with bob animation ---
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        eye_bob_offset = (self.eye_bob_amplitude + 3) * math.sin(self.eye_bob_timer * 2 * math.pi * (self.eye_bob_speed + 0.5))
        new_height = int((self.size - abs(eye_bob_offset) * 0.5) * spawn_scale)
        new_width = int((self.size + abs(eye_bob_offset) * 0.5 * 2) * spawn_scale)
        base_y = render_y + self.size
        new_y = base_y - new_height
        base_x = render_x + self.size / 2
        new_x = base_x - new_width / 2
        enemy_rect = pygame.Rect(new_x, new_y, new_width, new_height)
        # Contorno rosa avermelhado
        outline_color = (255, 100, 180)
        outline_alpha = death_alpha
        pygame.draw.rect(surface, (*outline_color, outline_alpha), enemy_rect, border_radius=6)
        pygame.draw.rect(surface, (*outline_color, outline_alpha), enemy_rect, width=4, border_radius=6)
        # Corpo preenchido
        if self.flash_timer > 0.0:
            # Flash white
            pygame.draw.rect(surface, (255, 255, 255, outline_alpha), enemy_rect.inflate(-6, -6), border_radius=6)
        else:
            pygame.draw.rect(surface, (*self.color, outline_alpha), enemy_rect.inflate(-6, -6), border_radius=6)

        # --- Render eyes (aparecem só após spawn) ---
        if not self.spawning:
            eye_size = max(2, int(self.size // 8 * spawn_scale))
            eye_gap = max(2, int(self.size // 6 * spawn_scale))
            eye_y = render_y + int(self.size // 2 * spawn_scale) - eye_size // 2
            center_x = render_x + int(self.size // 2 * spawn_scale)
            left_eye_x = center_x - eye_gap // 2 - eye_size
            right_eye_x = center_x + eye_gap // 2
            if self.is_blinking:
                eye_height = 0
            else:
                eye_height = eye_size
            pygame.draw.rect(surface, (0, 0, 0, outline_alpha), (left_eye_x, eye_y, eye_size, eye_height))
            pygame.draw.rect(surface, (0, 0, 0, outline_alpha), (right_eye_x, eye_y, eye_size, eye_height))


class VoidWrath(Enemy):
    def __init__(self, x, y, health=12, size=24, color=(80, 0, 120)):
        super().__init__(x, y, health=health, size=size, color=color)
        self.state = 'waiting'  # waiting, windup, fading_out, dashing, fading_in, confused
        self.timer = 0.0
        self.wait_duration = random.uniform(0.8, 2.0)
        self.windup_duration = 0.3
        self.fade_duration = 0.5
        self.dash_duration = 0.25
        self.dash_speed = 16.0  # pixels per frame
        self.alpha = 255
        self.target_pos = None
        self.dash_start = None
        self.dash_end = None
        # Use Enemy's spawn animation
        self.spawning = True
        self.spawn_timer = 0.0
        self.spawn_duration = random.uniform(0.5, 4.0)
        self.confused_timer = 0.0
        self.confused_duration = 0.7
        self.confused_bounce = (0, 0)
        self.removed = False
        self.windup_halo_radius = self.size * 1.2
        self.windup_eyes_glow = False
        self.dash_trail = []  # List of (x, y, timestamp)

        self.damage = 10

        # Preload dizzy sound effect
        self.dizzy_sound = assets.load_audio('game/sounds/effects/void_wrath_dizzing.wav')
        # Preload telegraphy sound effect
        self.telegraphy_sound = assets.load_audio('game/sounds/effects/telegraphy_void_wrath.wav')
        self.telegraphy_sound.set_volume(0.3)  # Set volume to 50%

    def take_damage(self, amount, hit_direction=None):
        # Ignore damage if spawning
        if getattr(self, 'spawning', False):
            return
        super().take_damage(amount, hit_direction=hit_direction)
        # Flash white effect for VoidWrath
        self.flash_timer = self.flash_duration
        # Knockback effect for VoidWrath
        if hit_direction is not None:
            knockback_strength = 8.0
            self.vx += hit_direction[0] * knockback_strength
            self.vy += hit_direction[1] * knockback_strength

    def die(self):
        # Use Enemy's die method to play sound and handle animation
        super().die()

    def update(self, dt=0.016, player_pos=None, other_enemies=None, player=None):
        if player and hasattr(player, 'engine') and player.engine.is_paused:
            return
        # Death animation: pixel explosion
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer'):
            self.death_timer += dt
            # Flash branco nos primeiros frames
            if hasattr(self, 'death_flash_frames') and self.death_timer < 0.05 * self.death_flash_frames:
                pass  # só flash, chunks não se movem
            elif hasattr(self, 'death_chunks'):
                for chunk in self.death_chunks:
                    chunk['x'] += chunk['dx'] * dt * 60
                    chunk['y'] += chunk['dy'] * dt * 60
                    chunk['timer'] += dt
                    chunk['alpha'] = max(0, 255 - int((chunk['timer'] / self.death_duration) * 255))
            if self.death_timer >= self.death_duration and not self.removed:
                self.death_timer = self.death_duration
                room = getattr(self, 'room', None)
                if room and hasattr(room, 'enemies') and self in room.enemies:
                    room.enemies.remove(self)
                else:
                    engine = getattr(self, 'engine', None)
                    if engine and hasattr(engine, 'enemies') and self in engine.enemies:
                        engine.enemies.remove(self)
                self.removed = True
            if self.removed:
                return
            return
        # Spawning animation logic (same as Enemy)
        if self.spawning:
            self.spawn_timer += dt
            if self.spawn_timer >= self.spawn_duration:
                self.spawning = False
            return
        self.timer += dt
        if self.state == 'waiting':
            if self.timer >= self.wait_duration and player_pos is not None:
                self.state = 'windup'
                self.timer = 0.0
                self.target_pos = player_pos
                # Play telegraphy sound effect when telegraphy indicator appears
                if self.telegraphy_sound:
                    self.telegraphy_sound.play()
        elif self.state == 'windup':
            t = min(self.timer / self.windup_duration, 1.0)
            self.windup_eyes_glow = True
            self.windup_halo_radius = self.size * (1.2 - 0.7 * t)
            if self.timer >= self.windup_duration:
                self.state = 'fading_out'
                self.timer = 0.0
                self.windup_eyes_glow = False
        elif self.state == 'fading_out':
            t = min(self.timer / self.fade_duration, 1.0)
            self.alpha = int(255 * (1 - t))
            if self.timer >= self.fade_duration:
                self.state = 'dashing'
                self.timer = 0.0
                # Dash: parar logo após a posição do jogador
                px, py = self.target_pos
                dx = px - self.x
                dy = py - self.y
                dist = math.hypot(dx, dy)
                if dist > 0:
                    dash_dx = dx / dist
                    dash_dy = dy / dist
                else:
                    dash_dx = dash_dy = 0
                self.dash_start = (self.x, self.y)
                # Dash vai até um ponto logo APÓS o jogador (ex: 1.2x a distância até o jogador)
                dash_multiplier = 1.2
                dash_target_x = self.x + dash_dx * dist * dash_multiplier
                dash_target_y = self.y + dash_dy * dist * dash_multiplier
                # Checa colisão com paredes no caminho
                dash_steps = int(dist * dash_multiplier)
                last_safe_x = self.x
                last_safe_y = self.y
                collision_found = False
                for step in range(1, dash_steps+1):
                    test_x = self.x + dash_dx * step
                    test_y = self.y + dash_dy * step
                    test_rect = pygame.Rect(test_x, test_y, self.size, self.size)
                    engine = getattr(self, 'engine', None)
                    wall_rects = []
                    if engine:
                        current_room = engine.dungeon.get_current_room()
                        wall_rects = current_room.get_wall_rects() if hasattr(current_room, 'get_wall_rects') else []
                    wall_hit = any(test_rect.colliderect(wall) for wall in wall_rects)
                    if wall_hit:
                        collision_found = True
                        break
                    last_safe_x = test_x
                    last_safe_y = test_y
                if collision_found:
                    bounce_dist = 8
                    bounce_dx = -dash_dx * bounce_dist
                    bounce_dy = -dash_dy * bounce_dist
                    self.confused_bounce = (bounce_dx, bounce_dy)
                    self.dash_end = (last_safe_x, last_safe_y)
                    self._collision_on_dash = True
                else:
                    self.dash_end = (dash_target_x, dash_target_y)
                    self._collision_on_dash = False
        elif self.state == 'dashing':
            t = min(self.timer / self.dash_duration, 1.0)
            # Ease-out cubic for dash
            ease_t = 1 - pow(1 - t, 3)
            if self.dash_start and self.dash_end:
                prev_x = self.x
                prev_y = self.y
                self.x = self.dash_start[0] + (self.dash_end[0] - self.dash_start[0]) * ease_t
                self.y = self.dash_start[1] + (self.dash_end[1] - self.dash_start[1]) * ease_t
                self.rect.topleft = (self.x, self.y)
                # Add trail point if moved enough
                trail_dist = math.hypot(self.x - prev_x, self.y - prev_y)
                if trail_dist > 2:
                    self.dash_trail.append((self.x, self.y, time.time()))
            # Check collision with player and deal damage
            if player is not None:
                player_rect = pygame.Rect(player.x, player.y, player.size, player.size)
                if self.rect.colliderect(player_rect):
                    if hasattr(player, 'take_damage'):
                        player.take_damage(self.damage)
            self.alpha = 50  # visible while dashing
            if self.timer >= self.dash_duration:
                self.wait_duration = random.uniform(0.8, 2.0)
                if getattr(self, '_collision_on_dash', False):
                    self.state = 'confused'
                    self.confused_timer = 0.0
                    # Play dizzy sound effect
                    if self.dizzy_sound:
                        self.dizzy_sound.play()
                else:
                    self.state = 'fading_in'
                self.timer = 0.0
        elif self.state == 'confused':
            self.confused_timer += dt
            # Ease-out cubic for bounce
            bounce_t = min(self.confused_timer / self.confused_duration, 1.0)
            ease_bounce = 1 - pow(1 - bounce_t, 3)
            bounce_x = self.confused_bounce[0] * ease_bounce
            bounce_y = self.confused_bounce[1] * ease_bounce
            # Cute shake: gentle sine wave wiggle
            shake_amplitude = 3
            shake_frequency = 7  # wiggles per second
            shake_x = math.sin(self.confused_timer * shake_frequency * 2 * math.pi) * shake_amplitude
            shake_y = math.cos(self.confused_timer * shake_frequency * 2 * math.pi) * (shake_amplitude * 0.5)
            self.x = self.dash_end[0] + bounce_x + shake_x
            self.y = self.dash_end[1] + bounce_y + shake_y
            self.rect.topleft = (self.x, self.y)
            # Check collision with player and deal damage
            if player is not None:
                player_rect = pygame.Rect(player.x, player.y, player.size, player.size)
                if self.rect.colliderect(player_rect):
                    if hasattr(player, 'take_damage'):
                        player.take_damage(1)
            self.alpha = 180
            if self.confused_timer >= self.confused_duration:
                self.state = 'fading_in'
                self.timer = 0.0
                # Aumenta o cooldown do dash em 2 segundos após ficar tonto
                self.wait_duration += 2.0
        elif self.state == 'fading_in':
            t = min(self.timer / self.fade_duration, 1.0)
            self.alpha = int(255 * t)
            if self.timer >= self.fade_duration:
                self.state = 'waiting'
                self.timer = 0.0
                self.alpha = 255

        # Update flash timer for VoidWrath
        if hasattr(self, 'flash_timer') and self.flash_timer > 0.0:
            self.flash_timer -= dt
            if self.flash_timer < 0.0:
                self.flash_timer = 0.0

    def draw(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        if getattr(self, 'removed', False):
            return
        # Death animation: pixel explosion
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer') and hasattr(self, 'death_chunks'):
            if self.death_timer < 0.05 * getattr(self, 'death_flash_frames', 2):
                render_x = self.x - camera_x
                render_y = self.y - camera_y
                enemy_rect = pygame.Rect(render_x, render_y, self.size, self.size)
                pygame.draw.rect(surface, (255, 255, 255, 255), enemy_rect, border_radius=6)
            else:
                for chunk in self.death_chunks:
                    chunk_surf = pygame.Surface((chunk['size'], chunk['size']), pygame.SRCALPHA)
                    pygame.draw.rect(chunk_surf, (*chunk['color'], chunk['alpha']), (0, 0, chunk['size'], chunk['size']))
                    draw_x = int(chunk['x'] - camera_x)
                    draw_y = int(chunk['y'] - camera_y)
                    surface.blit(chunk_surf, (draw_x, draw_y))
            # Render floating damage numbers mesmo durante a morte
            font = pygame.font.SysFont('arial', 18, bold=True)
            damage_lifetime = 0.7
            damage_rise = 30
            now = time.time()
            for dmg in self.floating_damage[:]:
                elapsed = now - dmg['timestamp']
                if elapsed > damage_lifetime:
                    self.floating_damage.remove(dmg)
                    continue
                alpha = max(0, 255 - int((elapsed / damage_lifetime) * 255))
                offset = int((elapsed / damage_lifetime) * damage_rise)
                dmg_text = font.render(str(dmg['damage']), True, (255, 50, 50))
                dmg_surf = pygame.Surface(dmg_text.get_size(), pygame.SRCALPHA)
                dmg_surf.blit(dmg_text, (0, 0))
                dmg_surf.set_alpha(alpha)
                draw_x = int(dmg['x'] - camera_x - dmg_text.get_width() // 2)
                draw_y = int(dmg['y'] - camera_y - 20 - offset)
                surface.blit(dmg_surf, (draw_x, draw_y))
            return
        # --- Render dash trail (dark) ---
        trail_lifetime = 0.4
        trail_color = (30, 0, 40)
        trail_radius = max(4, self.size // 4)
        now = time.time()
        self.dash_trail = [pt for pt in self.dash_trail if now - pt[2] < trail_lifetime]
        for tx, ty, tstamp in self.dash_trail:
            alpha = max(0, 120 - int((now - tstamp) / trail_lifetime * 120))
            trail_surf = pygame.Surface((trail_radius*2, trail_radius*2), pygame.SRCALPHA)
            pygame.draw.ellipse(trail_surf, (*trail_color, alpha), (0, 0, trail_radius*2, trail_radius*2))
            surface.blit(trail_surf, (int(tx - trail_radius - camera_x), int(ty - trail_radius - camera_y)) )
        # --- Render floating damage numbers ---
        font = pygame.font.SysFont('arial', 18, bold=True)
        damage_lifetime = 0.7
        damage_rise = 30
        now = time.time()
        for dmg in self.floating_damage[:]:
            elapsed = now - dmg['timestamp']
            if elapsed > damage_lifetime:
                self.floating_damage.remove(dmg)
                continue
            alpha = max(0, 255 - int((elapsed / damage_lifetime) * 255))
            offset = int((elapsed / damage_lifetime) * damage_rise)
            dmg_text = font.render(str(dmg['damage']), True, (255, 50, 50))
            dmg_surf = pygame.Surface(dmg_text.get_size(), pygame.SRCALPHA)
            dmg_surf.blit(dmg_text, (0, 0))
            dmg_surf.set_alpha(alpha)
            draw_x = int(dmg['x'] - camera_x - dmg_text.get_width() // 2)
            draw_y = int(dmg['y'] - camera_y - 20 - offset)
            surface.blit(dmg_surf, (draw_x, draw_y))
        # --- Spawning and death animation: scale up/down ---
        spawn_scale = 1.0
        if self.spawning:
            t = min(self.spawn_timer / self.spawn_duration, 1.0)
            spawn_scale = 0.2 + 0.8 * (1 - pow(1-t, 3))
            death_alpha = 255
        else:
            death_alpha = 255
        # --- Render enemy body with scale and fade ---
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        new_height = int(self.size * spawn_scale)
        new_width = int(self.size * spawn_scale)
        base_y = render_y + self.size
        new_y = base_y - new_height
        base_x = render_x + self.size / 2
        new_x = base_x - new_width / 2
        enemy_rect = pygame.Rect(new_x, new_y, new_width, new_height)
        outline_color = (120, 0, 180)
        outline_alpha = death_alpha
        pygame.draw.rect(surface, (*outline_color, outline_alpha), enemy_rect, border_radius=6)
        pygame.draw.rect(surface, (*outline_color, outline_alpha), enemy_rect, width=4, border_radius=6)
        if getattr(self, 'flash_timer', 0.0) > 0.0:
            pygame.draw.rect(surface, (255, 255, 255, outline_alpha), enemy_rect.inflate(-6, -6), border_radius=6)
        else:
            pygame.draw.rect(surface, (*self.color, outline_alpha), enemy_rect.inflate(-6, -6), border_radius=6)
        # --- Windup visual cue: eyes glow red + shrinking halo ---
        if self.state == 'windup':
            t = min(self.timer / self.windup_duration, 1.0)
            ease_t = 1 - pow(1 - t, 3)
            halo_radius = int(self.size * (1.2 - 0.7 * ease_t))
            halo_surf = pygame.Surface((halo_radius*2, halo_radius*2), pygame.SRCALPHA)
            pygame.draw.ellipse(halo_surf, (255, 255, 255, 128), (0, 0, halo_radius*2, halo_radius*2), width=6)
            halo_x = int(render_x + self.size/2 - halo_radius)
            halo_y = int(render_y + self.size/2 - halo_radius)
            surface.blit(halo_surf, (halo_x, halo_y))
        # --- Render eyes (aparecem só após spawn) ---
        if not self.spawning:
            eye_size = max(2, int(self.size // 8 * spawn_scale))
            eye_gap = max(2, int(self.size // 6 * spawn_scale))
            eye_y = render_y + int(self.size // 2 * spawn_scale) - eye_size // 2
            center_x = render_x + int(self.size // 2 * spawn_scale)
            left_eye_x = center_x - eye_gap // 2 - eye_size
            right_eye_x = center_x + eye_gap // 2
            if self.state == 'windup' and self.windup_eyes_glow:
                glow_color = (255, 0, 0, 220)
                pygame.draw.rect(surface, glow_color, (left_eye_x, eye_y, eye_size, eye_size))
                pygame.draw.rect(surface, glow_color, (right_eye_x, eye_y, eye_size, eye_size))
            else:
                eye_color = (0, 0, 0, outline_alpha)
                pygame.draw.rect(surface, eye_color, (left_eye_x, eye_y, eye_size, eye_size))
                pygame.draw.rect(surface, eye_color, (right_eye_x, eye_y, eye_size, eye_size))
