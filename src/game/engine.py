# Engine do jogo
import pygame
import math
from game.player import Player
from game.dungeon import Dungeon

class GameEngine:
    # Track previous room index for rendering
    def __init__(self, width=800, height=600, title="Dungeon Crawler", fullscreen=True):
        pygame.init()
        
        # Configurar fullscreen
        if fullscreen:
            info = pygame.display.Info()
            self.width = info.current_w
            self.height = info.current_h
            self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        else:
            self.width = width
            self.height = height
            self.screen = pygame.display.set_mode((width, height))
            
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.previous_room_index = None
        

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
        self.fps_font = pygame.font.Font(None, 32)

        # Collision rects debug
        self.show_collision_rects = False

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
    
    def _center_camera_on_room(self):
        """Centraliza a câmera no centro da sala."""
        room_center_x, room_center_y = self.room.get_center()
        self.camera_x = room_center_x - self.width // (2 * self.zoom)
        self.camera_y = room_center_y - self.height // (2 * self.zoom)
    
    def _center_camera_on_player(self):
        """Centraliza a câmera no jogador."""
        player_center_x = self.player.x + self.player.size // 2
        player_center_y = self.player.y + self.player.size // 2
        self.camera_x = player_center_x - self.width // (2 * self.zoom)
        self.camera_y = player_center_y - self.height // (2 * self.zoom)
    
    def _update_camera(self):
        """Atualiza a câmera para seguir o jogador suavemente."""
        # Posição alvo da câmera (centrada no jogador)
        player_center_x = self.player.x + self.player.size // 2
        player_center_y = self.player.y + self.player.size // 2
        target_camera_x = player_center_x - self.width // (2 * self.zoom)
        target_camera_y = player_center_y - self.height // (2 * self.zoom)
        
        # Interpolação suave para a posição alvo
        self.camera_x += (target_camera_x - self.camera_x) * self.camera_smoothing
        self.camera_y += (target_camera_y - self.camera_y) * self.camera_smoothing

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    # Space key is no longer needed for opening transitions
                    print("[INFO] Walk through openings in walls to change rooms!")
                elif event.key == pygame.K_F11:
                    # Toggle fullscreen
                    self._toggle_fullscreen()
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Zoom in
                    self.zoom = min(self.zoom * 1.2, 5.0)
                elif event.key == pygame.K_MINUS:
                    # Zoom out
                    self.zoom = max(self.zoom / 1.2, 0.5)
                elif event.key == pygame.K_F3:
                    # Toggle FPS monitor
                    self.show_fps = not self.show_fps
                elif event.key == pygame.K_F4:
                    # Toggle collision rects debug
                    self.show_collision_rects = not self.show_collision_rects

    def update(self):
        current_index = self.dungeon.current_room_index
        adjacent_rooms = self.dungeon.get_adjacent_rooms(current_index)

        # move player
        self.player.update(rooms=adjacent_rooms)

        # update room based on player position (bounding box detection)
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


    def render(self):
        self.screen.fill((10, 10, 15))  # Dark background
        
        # Render the current and previous room, and the player in both
        current_room = self.dungeon.get_current_room()
        previous_room = None
        if self.previous_room_index is not None:
            previous_room = self.dungeon.rooms[self.previous_room_index]

        rooms_to_render = [current_room]
        if previous_room and previous_room != current_room:
            rooms_to_render.append(previous_room)

        if abs(self.zoom - 1.0) > 0.05:
            virtual_width = int(self.width / self.zoom)
            virtual_height = int(self.height / self.zoom)
            virtual_surface = pygame.Surface((virtual_width, virtual_height))
            virtual_surface.fill((10, 10, 15))

            # Render current and previous room
            for room in rooms_to_render:
                room.render(virtual_surface, self.camera_x, self.camera_y, show_collision_rects=self.show_collision_rects)

            # Render the player in both rooms
            self.player.render(
                virtual_surface,
                self.camera_x,
                self.camera_y,
                rooms_to_render,
                show_collision_rects=self.show_collision_rects
            )

            # Scale and draw to real screen
            scaled_surface = pygame.transform.scale(virtual_surface, (self.width, self.height))
            self.screen.blit(scaled_surface, (0, 0))
        else:
            self.screen.fill((10, 10, 15))

            # Render current and previous room
            for room in rooms_to_render:
                room.render(self.screen, self.camera_x, self.camera_y, show_collision_rects=self.show_collision_rects)

            # Render the player in both rooms
            self.player.render(
                self.screen,
                self.camera_x,
                self.camera_y,
                rooms_to_render,
                show_collision_rects=self.show_collision_rects
            )

        # Render UI (always on top)
        self.dungeon.render_ui(self.screen)

        # FPS monitor
        if self.show_fps:
            fps = self.clock.get_fps()
            playerPos = self.player.x, self.player.y
            fps_text = self.fps_font.render(f"FPS: {fps:.1f}", True, (255, 255, 0))
            playerPos_text = self.fps_font.render(f"Player Pos: {playerPos}", True, (255, 255, 0))
            self.screen.blit(fps_text, (10, 10))
            self.screen.blit(playerPos_text, (10, 30))

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
