
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
            from game.assets import get_image
            self.sprite = get_image(f"weapon_{name}", sprite_path)

    def can_attack(self):
        current_time = time.time()
        return (current_time - self.last_attack_time) >= (1.0 / self.fire_rate)

    def attack(self, player_pos, angle):
        """Método genérico para atacar — deve ser implementado nas subclasses."""
        raise NotImplementedError
    
    def render_static(self, surface, center, camera_x=0, camera_y=0, zoom=1.0, size=None):
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
        # Use provided size for dropped/static weapons, else fallback to previous logic
        if size is not None:
            scale_width = int(size * zoom)
            original_rect = sprite.get_rect()
            scale_height = int(scale_width * original_rect.height / original_rect.width)
        else:
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
        
    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        screen_x = (self.pos.x - camera_x) * (zoom - 0.3)
        screen_y = (self.pos.y - camera_y) * (zoom - 0.3)

        # DEBUG: Draw spawn point marker
        pygame.draw.circle(surface, (0, 255, 0), (int(screen_x), int(screen_y)), int(5 * zoom))
        
        pygame.draw.circle(surface, (255, 255, 255), (int(screen_x), int(screen_y)), int(self.radius * zoom))

class PistolBullet(Bullet):
    def __init__(self, x, y, angle, speed, damage):
        # Typical pistol bullet characteristics:
        # - Medium speed (faster than shotgun, slower than rifle)
        # - Moderate damage
        # - Small radius
        super().__init__(x, y, angle, speed=speed, damage=damage)
        self.radius = 2  # Smaller visual radius than default bullet
        self.lifetime = 1.5  # Slightly shorter lifetime than default
        
    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        screen_x = (self.pos.x - camera_x) * (zoom - 0.3)
        screen_y = (self.pos.y - camera_y) * (zoom - 0.3)

        # Draw bullet with a slight yellow tint for pistol bullets
        pygame.draw.circle(surface, (255, 255, 200), (int(screen_x), int(screen_y)), int(self.radius * zoom))
        
        # Optional: Add a small glow effect
        glow_radius = max(1, int(self.radius * zoom * 1.5))
        glow_surface = pygame.Surface((glow_radius*2, glow_radius*2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (255, 255, 200, 100), (glow_radius, glow_radius), glow_radius)
        surface.blit(glow_surface, (int(screen_x - glow_radius), int(screen_y - glow_radius)))