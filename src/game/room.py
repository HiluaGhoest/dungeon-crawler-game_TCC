import pygame
import random

class Room:
    def __init__(self, x, y, width, height, wall_thickness=20):
        """
        Cria uma sala com paredes.
        
        Args:
            x, y: Posição da sala no mundo
            width, height: Dimensões da sala
            wall_thickness: Espessura das paredes
        """
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.wall_thickness = wall_thickness
        
        # Cores
        self.wall_color = (80, 60, 40)  # Marrom escuro para paredes
        self.floor_color = (60, 50, 40)  # Marrom mais escuro para o chão
        
        # Definir as paredes como retângulos sem sobreposição nos cantos
        self.walls = [
            # Parede superior
            pygame.Rect(x, y, width, wall_thickness),
            # Parede inferior
            pygame.Rect(x, y + height - wall_thickness, width, wall_thickness),
            # Parede esquerda (sem os cantos para evitar sobreposição)
            pygame.Rect(x, y + wall_thickness, wall_thickness, height - 2 * wall_thickness),
            # Parede direita (sem os cantos para evitar sobreposição)
            pygame.Rect(x + width - wall_thickness, y + wall_thickness, wall_thickness, height - 2 * wall_thickness)
        ]
        
        # Área interna da sala (onde o jogador pode andar)
        self.inner_area = pygame.Rect(
            x + wall_thickness,
            y + wall_thickness,
            width - 2 * wall_thickness,
            height - 2 * wall_thickness
        )
    
    def get_center(self):
        """Retorna o centro da sala."""
        return (
            self.x + self.width // 2,
            self.y + self.height // 2
        )
    
    def get_spawn_position(self):
        """Retorna uma posição válida para spawnar o jogador."""
        center_x, center_y = self.get_center()
        return center_x - 16, center_y - 16  # Ajusta para o centro do player (32x32)
    
    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Renderiza a sala na superfície com offset da câmera."""
        # Calcular posição de renderização
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        
        # Desenha o chão primeiro
        floor_rect = pygame.Rect(render_x, render_y, self.width, self.height)
        pygame.draw.rect(surface, self.floor_color, floor_rect)
        
        # Desenha as paredes com offset da câmera
        for wall in self.walls:
            wall_render = pygame.Rect(
                wall.x - camera_x,
                wall.y - camera_y,
                wall.width,
                wall.height
            )
            pygame.draw.rect(surface, self.wall_color, wall_render)
            if show_collision_rects:
                pygame.draw.rect(surface, (255, 0, 0), wall_render, 2)
        # Adiciona um pouco de textura às paredes (opcional)
        self._add_wall_texture(surface, camera_x, camera_y)
    
    def get_wall_rects(self):
        """Retorna uma lista com todos os retângulos das paredes para detecção de colisão."""
        return self.walls
    
    def _add_wall_texture(self, surface, camera_x=0, camera_y=0):
        """Adiciona uma textura simples às paredes."""
        # Adiciona algumas linhas nas paredes para dar textura
        for i, wall in enumerate(self.walls):
            # Calcular posição de renderização da parede
            wall_render_x = wall.x - camera_x
            wall_render_y = wall.y - camera_y
            wall_render_right = wall_render_x + wall.width
            wall_render_bottom = wall_render_y + wall.height
            
            # Linha mais clara na borda externa
            if i < 2:  # Paredes horizontais (superior e inferior)
                if i == 0:  # Parede superior - linha na parte de cima (borda externa)
                    pygame.draw.line(surface, 
                                   (100, 80, 60), 
                                   (wall_render_x, wall_render_y), 
                                   (wall_render_right, wall_render_y), 2)
                else:  # Parede inferior - linha na parte de baixo (borda externa)
                    pygame.draw.line(surface, 
                                   (100, 80, 60), 
                                   (wall_render_x, wall_render_bottom), 
                                   (wall_render_right, wall_render_bottom), 2)
            else:  # Paredes verticais (esquerda e direita)
                if i == 2:  # Parede esquerda - linha na esquerda (borda externa)
                    # Estender a linha para conectar com os cantos
                    pygame.draw.line(surface, 
                                   (100, 80, 60), 
                                   (wall_render_x, self.y - camera_y), 
                                   (wall_render_x, self.y + self.height - camera_y), 2)
                else:  # Parede direita - linha na direita (borda externa)
                    # Estender a linha para conectar com os cantos
                    pygame.draw.line(surface, 
                                   (100, 80, 60), 
                                   (wall_render_right, self.y - camera_y), 
                                   (wall_render_right, self.y + self.height - camera_y), 2)

class DungeonRoom(Room):
    """Uma sala de dungeon com decorações específicas."""
    
    def __init__(self, x, y, width, height, wall_thickness=20):
        super().__init__(x, y, width, height, wall_thickness)
        
        # Cores mais escuras para dungeon
        self.wall_color = (40, 35, 30)  # Pedra escura
        self.floor_color = (25, 20, 15)  # Chão de pedra
        
        # Adiciona algumas decorações
        self.decorations = self._generate_decorations()
    
    def _generate_decorations(self):
        """Gera decorações aleatórias para a sala."""
        decorations = []
        
        # Adiciona algumas pedras ou detritos no chão
        for _ in range(random.randint(3, 8)):
            # Verificar se há espaço suficiente para decorações
            min_x = self.inner_area.left + 20
            max_x = self.inner_area.right - 20
            min_y = self.inner_area.top + 20
            max_y = self.inner_area.bottom - 20
            
            # Só adicionar decoração se há espaço suficiente
            if max_x >= min_x and max_y >= min_y:
                x = random.randint(min_x, max_x)
                y = random.randint(min_y, max_y)
                size = random.randint(5, 15)
                decorations.append({
                    'type': 'stone',
                    'pos': (x, y),
                    'size': size,
                'color': (35, 30, 25)
            })
        
        return decorations
    
    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):  
        """Renderiza a sala do dungeon."""
        # Renderiza a sala base
        super().render(surface)
        
        for tile in self.floor_tiles:
            draw_x = tile.x - camera_x
            draw_y = tile.y - camera_y
            surface.blit(tile.image, (draw_x, draw_y))

        # Renderiza decorações
        for decoration in self.decorations:
            if decoration['type'] == 'stone':
                pygame.draw.circle(
                    surface, 
                    decoration['color'], 
                    decoration['pos'], 
                    decoration['size']
                )