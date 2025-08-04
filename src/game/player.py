import pygame

class Player:
    def __init__(self, x, y, speed=5, color=(200, 200, 50), size=16):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.size = size
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)

    def set_position(self, x, y):
        """Set player position directly"""
        self.x = x
        self.y = y
        self.rect.topleft = (x, y)


    def handle_input(self, rooms=None):
        if rooms is None:
            rooms = []

        keys = pygame.key.get_pressed()
        old_x, old_y = self.x, self.y
        new_x, new_y = self.x, self.y
        
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            new_y -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            new_y += self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            new_x -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            new_x += self.speed

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


    def update(self, rooms=None):
        """Atualiza o jogador, incluindo verificação de colisão."""
        self.handle_input(rooms)

    def render(self, surface, camera_x=0, camera_y=0, rooms=None, show_collision_rects=False):
        from game.util.light import create_soft_player_light
        
        # Calcular posição de renderização com offset da câmera
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        
        # Obter as paredes da sala para detecção de colisão da luz
        wall_rects = []
        if rooms:
            for room in rooms:
                if not hasattr(room, 'get_wall_rects'):
                    continue

                for wall in room.get_wall_rects():
                    # Convert to screen space
                    screen_wall = pygame.Rect(
                        wall.x - camera_x,
                        wall.y - camera_y,
                        wall.width,
                        wall.height
                    )
                    wall_rects.append(screen_wall)

            
            # Performance optimization: limit walls passed to lighting system for large rooms
            if len(wall_rects) > 150:
                player_center_x = render_x + self.size // 2
                player_center_y = render_y + self.size // 2
                
                # Filter walls by distance from player (in SCREEN SPACE)
                walls_with_distance = []
                for wall in wall_rects:
                    wall_center_x = wall.x + wall.width // 2
                    wall_center_y = wall.y + wall.height // 2
                    dist_sq = (wall_center_x - player_center_x) ** 2 + (wall_center_y - player_center_y) ** 2
                    walls_with_distance.append((dist_sq, wall))
                
                # Sort by distance and keep only the closest 100 walls
                walls_with_distance.sort(key=lambda x: x[0])
                wall_rects = [wall for _, wall in walls_with_distance[:100]]
        
        # Renderiza a luz suave em volta do jogador
        create_soft_player_light(
            surface, 
            render_x + self.size // 2, 
            render_y + self.size // 2, 
            radius=130,
            wall_rects=wall_rects  # Now in screen coordinates!
        )
        
        # Renderizar o jogador
        player_render_rect = pygame.Rect(render_x, render_y, self.size, self.size)
        pygame.draw.rect(surface, self.color, player_render_rect)

        # Draw collision rect if debug enabled
        if show_collision_rects:
            pygame.draw.rect(surface, (0, 255, 0), player_render_rect, 2)