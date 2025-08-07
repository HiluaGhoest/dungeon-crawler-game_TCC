import pygame

class Enemy:
    def __init__(self, x, y, health=10):
        self.x = x
        self.y = y
        self.health = health
        self.rect = self._get_rect()

    def _get_rect(self):
        # Returns a pygame.Rect for the enemy's position and size
        return pygame.Rect(self.x, self.y, 64, 64)

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.die()

    def die(self):
        # Handle enemy death (remove from game, play animation, etc.)
        pass

    def update(self):
        # Basic movement or AI logic
        pass

    def draw(self, surface, camera_x=0, camera_y=0):
        # Draw a simple red rectangle as the enemy, offset by camera
        render_rect = self.rect.move(-camera_x, -camera_y)
        pygame.draw.rect(surface, (200, 0, 0), render_rect)
