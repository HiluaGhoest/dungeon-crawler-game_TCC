import pygame

class Enemy:
    def __init__(self, x, y, health=10, size=32, color=(200, 0, 0)):
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

        # Velocidade atual (para steering)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 1  # Velocidade base do inimigo (pixels por segundo)
        # Quão rápido ele ajusta a direção (0.0 a 1.0)
        self.steer_strength = 0.1

    def _get_rect(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.die()

    def die(self):
        # Handle enemy death (remove from game, play animation, etc.)
        pass

    def update(self, dt=0.016, player_pos=None, other_enemies=None):
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
            import math
            px, py = player_pos
            dx = px - self.x
            dy = py - self.y
            dist = math.hypot(dx, dy)

            # 1) Vetor de separação
            sep_x = sep_y = 0.0
            sep_radius = self.size * 2
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
            if other_enemies:
                for other in other_enemies:
                    if other is self:
                        continue
                    # Use a posição futura do outro, se já calculada
                    other_future_x, other_future_y = getattr(other, 'next_pos', (other.x, other.y))
                    other_rect = pygame.Rect(other_future_x, other_future_y, other.size, other.size)
                    if new_rect.colliderect(other_rect):
                        can_move = False
                        break
            # Checa colisão com jogador
            player_rect = pygame.Rect(px, py, self.size, self.size)
            if new_rect.colliderect(player_rect):
                can_move = False
            # Só move se não houver colisão
            if can_move:
                self.x = new_x
                self.y = new_y
                self.rect.topleft = (self.x, self.y)
            # Limpa a posição futura após o movimento
            if hasattr(self, 'next_pos'):
                del self.next_pos

        # Pegadas
        moved_dist = ((self.x - self._last_footprint_pos[0]) ** 2 + (self.y - self._last_footprint_pos[1]) ** 2) ** 0.5
        if moved_dist > self._footprint_distance:
            import time, math
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
        import pygame, time, math
        # --- Render footprints ---
        footprint_color = (255, 255, 0)
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

        # --- Render enemy body with bob animation ---
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        eye_bob_offset = (self.eye_bob_amplitude + 3) * math.sin(self.eye_bob_timer * 2 * math.pi * (self.eye_bob_speed + 0.5))
        new_height = int(self.size - abs(eye_bob_offset) * 0.5)
        new_width = int(self.size + abs(eye_bob_offset) * 0.5 * 2)
        base_y = render_y + self.size
        new_y = base_y - new_height
        base_x = render_x + self.size / 2
        new_x = base_x - new_width / 2
        enemy_rect = pygame.Rect(new_x, new_y, new_width, new_height)
        # Contorno amarelo grosso
        outline_color = (255, 220, 0)
        pygame.draw.rect(surface, outline_color, enemy_rect, border_radius=6)
        pygame.draw.rect(surface, outline_color, enemy_rect, width=4, border_radius=6)
        # Corpo preenchido
        pygame.draw.rect(surface, self.color, enemy_rect.inflate(-6, -6), border_radius=6)

        # --- Render eyes (pretos e pequenos, estilo original) ---
        eye_size = max(2, self.size // 8)
        eye_gap = max(2, self.size // 6)  # distância entre olhos
        eye_y = render_y + self.size // 2 - eye_size // 2
        center_x = render_x + self.size // 2
        left_eye_x = center_x - eye_gap // 2 - eye_size
        right_eye_x = center_x + eye_gap // 2
        if self.is_blinking:
            eye_height = 0
        else:
            eye_height = eye_size
        pygame.draw.rect(surface, (0, 0, 0), (left_eye_x, eye_y, eye_size, eye_height))
        pygame.draw.rect(surface, (0, 0, 0), (right_eye_x, eye_y, eye_size, eye_height))