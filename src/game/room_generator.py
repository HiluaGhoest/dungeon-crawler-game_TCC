import pygame
import random
import math
import heapq
from game.room import Room
from game.weapons import DoublePistol, Pistol, Weapon, Steel_Sword

class RoomGenerator:
    """Gerador de salas com formatos aleatórios."""
    
    def __init__(self, tile_size=20):
        self.tile_size = tile_size

    def generate_rectangular_room(self, x, y, min_width=12, max_width=32, min_height=12, max_height=32, allow_islands=True, allow_subrooms=True, is_first_room=False):
        """Gera uma sala retangular simples."""
        width = random.randint(min_width, max_width) * self.tile_size
        height = random.randint(min_height, max_height) * self.tile_size
        print(f"[ROOM] Gerando sala retangular: {width//self.tile_size}x{height//self.tile_size} tiles (first_room: {is_first_room})")
        
        room = TiledRoom(x, y, width, height, self.tile_size)
        return room
    
    def generate_first_room(self, x, y, min_width=12, max_width=32, min_height=12, max_height=32, allow_islands=True, allow_subrooms=True, is_first_room=False):
        """Gera uma sala retangular simples."""
        width = random.randint(min_width, max_width) * self.tile_size
        height = random.randint(min_height, max_height) * self.tile_size
        print(f"[ROOM] Gerando sala retangular: {width//self.tile_size}x{height//self.tile_size} tiles (first_room: {is_first_room})")
        
        room = TiledRoom(x, y, width, height, self.tile_size)

        if is_first_room:
            room.add_pillars_in_circle(count=8)

        return room

    
    def generate_l_shaped_room(self, x, y):
        """Gera uma sala em formato de L."""
        main_width = random.randint(12, 32) * self.tile_size
        main_height = random.randint(22, 22) * self.tile_size
        
        ext_width = random.randint(8, 15) * self.tile_size
        ext_height_tiles = random.randint(8, 12)
        
        max_ext_height_tiles = (main_height // self.tile_size) // 2
        if ext_height_tiles > max_ext_height_tiles:
            ext_height_tiles = max_ext_height_tiles
        
        if ext_height_tiles < 2:
            ext_height_tiles = 2
        
        ext_height = ext_height_tiles * self.tile_size
        
        print(f"[ROOM] Gerando sala em formato de L:")
        print(f"       Principal: {main_width//self.tile_size}x{main_height//self.tile_size}, Extensão: {ext_width//self.tile_size}x{ext_height//self.tile_size}")
        
        return LShapedRoom(x, y, main_width, main_height, ext_width, ext_height, self.tile_size)
    
    def generate_random_room(self, x, y, is_first_room=False, last_opening_direction=None):
        if is_first_room:
            return self.generate_rectangular_room(x, y, is_first_room=True)
        
        room_types = [
            self.generate_rectangular_room,
            self.generate_l_shaped_room
        ]
        
        room_names = [
            "Retangular",
            "Formato L"
        ]

        weights = [0.25, 0.25]
        
        chosen_index = random.choices(range(len(room_types)), weights=weights)[0]
        room_type = room_types[chosen_index]
        
        print(f"[ROOM] Selecionado tipo: {room_names[chosen_index]}")
        return room_type(x, y)
    
class Pillar:
    def __init__(self, x, y, tile_size, weapon=None, toggleable=True):
        self.rect = pygame.Rect(x, y, tile_size * 2, tile_size * 2)
        self.weapon = weapon      # arma que o pilar tem
        self.original_weapon = weapon  # usada para restaurar se for toggle
        self.toggleable = toggleable   # se True, a arma volta pro pilar quando trocada
        self.interacted = False

    def interact(self, player):
        # Se o pilar não tem arma, e o jogador tem uma, e o pilar aceita toggle, devolve a arma
        if self.weapon is None and self.toggleable and player.weapon and player.weapon_origin is self:
            self.weapon = player.weapon
            player.weapon = None
            player.weapon_origin = None
            print(f"[PILLAR] {self.weapon.name} devolvida ao pilar.")
            return

        # Se o pilar tem arma e o jogador não tem
        if self.weapon and not player.weapon:
            player.weapon = self.weapon
            player.weapon_origin = self if self.toggleable else None
            print(f"[PILLAR] {self.weapon.name} pega pelo jogador.")
            self.weapon = None
            return

        # Se o jogador já tem arma e esse pilar tem outra
        if self.weapon and player.weapon and self.weapon != player.weapon:
            if self.toggleable and player.weapon_origin:
                # Devolve a arma atual para o pilar de origem
                player.weapon_origin.weapon = player.weapon
            player.weapon = self.weapon
            player.weapon_origin = self if self.toggleable else None
            print(f"[PILLAR] Arma trocada: agora o jogador tem {player.weapon.name}")
            self.weapon = None

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        # Only render the weapon, not the pillar itself
        render_rect = self.rect.move(-camera_x, -camera_y)
        weapon_render_rect = render_rect.move(0, -32)
        if self.weapon:
            center = weapon_render_rect.center
            self.weapon.render_static(surface, center, camera_x, camera_y, zoom)

class DustParticle:
    def __init__(self, x, y, size=None):
        self.x = x
        self.y = y
        self.size = size if size else random.randint(1, 3)
        self.color = (
            random.randint(180, 220),
            random.randint(180, 200),
            random.randint(150, 180)
        )
        self.alpha = random.randint(50, 150)
        
    def render(self, surface, camera_x=0, camera_y=0):
        render_x = self.x - camera_x
        render_y = self.y - camera_y
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill((*self.color, self.alpha))
        surface.blit(s, (render_x, render_y))

class TiledRoom(Room):
    """Sala base usando sistema de tiles."""
    
    def __init__(self, x, y, width, height, tile_size):
        self.tile_size = tile_size
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.wall_color = (60, 55, 70)  # Muted dark gray with purple undertones
        self.floor_color = (20, 18, 28)  # Very dark gray/black with a subtle purple tint
        self.pillar_tiles = []  # <-- pilares
        self.dust_particles = []

        self.wall_tiles = self._generate_wall_tiles()

        self.decorations = []
        self._add_concave_corner_fillers()
        self._generate_dust_particles()
        
        

    def _generate_dust_particles(self):
        """Generate random dust particles on floor tiles"""
        dust_count = random.randint(20, 50)  # Adjust count as needed
        
        for _ in range(dust_count):
            # Random position within room bounds (excluding walls)
            x = self.x + random.randint(self.tile_size, self.width - 2*self.tile_size)
            y = self.y + random.randint(self.tile_size, self.height - 2*self.tile_size)
            
            # Only add if it's actually on a floor tile
            if self.is_floor_tile(x, y):
                self.dust_particles.append(DustParticle(x, y))

    def add_pillars_in_circle(self, count=8):
        import math
        import random

        available_weapons = [Steel_Sword, Pistol, DoublePistol]  # Add more weapon classes here as needed

        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2
        radius = min(self.width, self.height) // 3

        for i in range(count):
            angle = (2 * math.pi / count) * i
            px = center_x + int(radius * math.cos(angle))
            py = center_y + int(radius * math.sin(angle))

            tile_x = (px // self.tile_size) * self.tile_size
            tile_y = (py // self.tile_size) * self.tile_size

            has_weapon = random.choice([True, False])

            weapon = random.choice(available_weapons)() if has_weapon else None

            pillar = Pillar(tile_x, tile_y, self.tile_size, weapon=weapon, toggleable=True)
            self.pillar_tiles.append(pillar)

            
    def _generate_wall_tiles(self):
        """Gera tiles individuais para as paredes."""
        tiles = []
        tiles_wide = self.width // self.tile_size
        tiles_tall = self.height // self.tile_size
        
        for tx in range(tiles_wide):
            for ty in range(tiles_tall):
                if (tx == 0 or tx == tiles_wide - 1 or 
                    ty == 0 or ty == tiles_tall - 1):
                    
                    # Use the room's actual position
                    tile_x = self.x + tx * self.tile_size
                    tile_y = self.y + ty * self.tile_size
                    tile_type = self._get_tile_type(tx, ty, tiles_wide, tiles_tall)
                    
                    tiles.append({
                        'rect': pygame.Rect(tile_x, tile_y, self.tile_size, self.tile_size),
                        'type': tile_type,
                        'grid_pos': (tx, ty)
                    })
        return tiles
    
    def shift_position(self, dx, dy):
        self.x += dx
        self.y += dy
        for tile in self.wall_tiles:
            tile['rect'].x += dx
            tile['rect'].y += dy
        if hasattr(self, 'floor_tiles'):
            for tile in self.floor_tiles:
                tile.x -= dx
                tile.y += dy
        if hasattr(self, 'original_wall_tiles'):
            for tile in self.original_wall_tiles:
                tile['rect'].x += dx
                tile['rect'].y += dy
        
        # Shift dust particles
        for dust in self.dust_particles:
            dust.x += dx
            dust.y += dy
            
        # Shift pillars
        for pillar in self.pillar_tiles:
            pillar.rect.x += dx
            pillar.rect.y += dy
                
    def _get_tile_type(self, tx, ty, width, height):
        """Determina o tipo de tile baseado na posição na grade."""
        if tx == 0 and ty == 0:
            return 'corner_top_left'
        elif tx == width - 1 and ty == 0:
            return 'corner_top_right'
        elif tx == 0 and ty == height - 1:
            return 'corner_bottom_left'
        elif tx == width - 1 and ty == height - 1:
            return 'corner_bottom_right'
        elif ty == 0:
            return 'wall_top'
        elif ty == height - 1:
            return 'wall_bottom'
        elif tx == 0:
            return 'wall_left'
        elif tx == width - 1:
            return 'wall_right'
        else:
            return 'floor'
    
    def _add_concave_corner_fillers(self):
        """Adiciona tiles de preenchimento para cantos côncavos (internos).
        Base implementation does nothing - only complex room shapes need this."""
        pass
    
    def _draw_tile(self, surface, tile, camera_x=0, camera_y=0):
        """Desenha uma tile individual com suas texturas."""
        rect = tile['rect']
        tile_type = tile['type']
        render_rect = pygame.Rect(
            rect.x - camera_x,
            rect.y - camera_y,
            rect.width,
            rect.height
        )
        pygame.draw.rect(surface, self.wall_color, render_rect)
        
        color = (255, 255, 255)
        line_width = 2
        
        # Ajustes para linhas direita e inferior para ficarem dentro do retângulo
        right_x = render_rect.right - 2
        bottom_y = render_rect.bottom - 2
        
        if tile_type == 'concave_filler':
            # Não desenha contorno, apenas o preenchimento
            pass
        elif tile_type == 'corner_top_left':
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.right, render_rect.top), line_width)
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.left, render_rect.bottom), line_width)
        elif tile_type == 'corner_top_right':
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.right, render_rect.top), line_width)
            pygame.draw.line(surface, color, 
                            (right_x, render_rect.top), (right_x, render_rect.bottom), line_width)
        elif tile_type == 'corner_bottom_left':
            pygame.draw.line(surface, color, 
                            (render_rect.left, bottom_y), (render_rect.right, bottom_y), line_width)
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.left, render_rect.bottom), line_width)
        elif tile_type == 'corner_bottom_right':
            pygame.draw.line(surface, color, 
                            (render_rect.left, bottom_y), (render_rect.right, bottom_y), line_width)
            pygame.draw.line(surface, color, 
                            (right_x, render_rect.top), (right_x, render_rect.bottom), line_width)
        elif tile_type == 'wall_top':
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.right, render_rect.top), line_width)
        elif tile_type == 'wall_bottom':
            pygame.draw.line(surface, color, 
                            (render_rect.left, bottom_y), (render_rect.right, bottom_y), line_width)
        elif tile_type == 'wall_left':
            pygame.draw.line(surface, color, 
                            (render_rect.left, render_rect.top), (render_rect.left, render_rect.bottom), line_width)
        elif tile_type == 'wall_right':
            pygame.draw.line(surface, color, 
                            (right_x, render_rect.top), (right_x, render_rect.bottom), line_width)

    
    def get_wall_rects(self):
        """Retorna uma lista com todos os retângulos das paredes para detecção de colisão."""
        return [tile['rect'] for tile in self.wall_tiles]
    
    def is_floor_tile(self, x, y):
        """Verifica se a posição (x, y) é um tile de chão navegável."""
        for tile in self.wall_tiles:
            if tile['rect'].collidepoint(x, y):
                return False
        return (self.x <= x < self.x + self.width and 
                self.y <= y < self.y + self.height)
    
    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Renderiza a sala com tiles."""
        floor_rect = pygame.Rect(self.x - camera_x, self.y - camera_y, self.width, self.height)
        pygame.draw.rect(surface, self.floor_color, floor_rect)
        
        for tile in self.wall_tiles:
            self._draw_tile(surface, tile, camera_x, camera_y)
            if show_collision_rects:
                rect = tile['rect']
                debug_rect = pygame.Rect(rect.x - camera_x, rect.y - camera_y, rect.width, rect.height)
                pygame.draw.rect(surface, (255, 0, 0), debug_rect, 2)
        
        for pillar in self.pillar_tiles:
            pillar.render(surface, camera_x, camera_y)

        for dust in self.dust_particles:
            dust.render(surface, camera_x, camera_y)




class LShapedRoom(TiledRoom):
    """Sala em formato de L usando tiles."""
    
    def __init__(self, x, y, main_width, main_height, ext_width, ext_height, tile_size):
        self.main_width = main_width
        self.main_height = main_height
        self.ext_width = ext_width
        self.ext_height = ext_height
        total_width = main_width + ext_width
        total_height = main_height
        self.pillar_tiles = []  # <-- Aqui guardaremos os pilares
        super().__init__(x, y, total_width, total_height, tile_size)
    
    def _generate_dust_particles(self):
        """Generate random dust particles on floor tiles for L-shaped room"""
        dust_count = random.randint(30, 70)  # More dust for larger rooms
        
        l_rects = self._get_l_rectangles()
        for _ in range(dust_count):
            # Choose a random rectangle (main or extension)
            rect = random.choice(l_rects)
            
            # Random position within the chosen rectangle (excluding walls)
            x = rect.x + random.randint(self.tile_size, rect.width - 2*self.tile_size)
            y = rect.y + random.randint(self.tile_size, rect.height - 2*self.tile_size)
            
            # Only add if it's actually on a floor tile
            if self.is_floor_tile(x, y):
                self.dust_particles.append(DustParticle(x, y))

    def _generate_wall_tiles(self):
        """Gera tiles para uma sala em formato de L."""
        tiles = []
        l_rects = self._get_l_rectangles()
        
        for rect in l_rects:
            tiles_wide = rect.width // self.tile_size
            tiles_tall = rect.height // self.tile_size
            
            for tx in range(tiles_wide):
                for ty in range(tiles_tall):
                    tile_x = rect.x + tx * self.tile_size
                    tile_y = rect.y + ty * self.tile_size
                    tile_rect = pygame.Rect(tile_x, tile_y, self.tile_size, self.tile_size)
                    
                    if self._is_external_wall(tile_rect, l_rects):
                        tile_type = self._get_l_tile_type(tile_rect, l_rects)
                        tiles.append({
                            'rect': tile_rect,
                            'type': tile_type,
                            'grid_pos': (tx, ty)
                        })
        return tiles
    
    def _get_l_rectangles(self):
        """Retorna os retângulos que formam o L."""
        main_rect = pygame.Rect(self.x, self.y, self.main_width, self.main_height)
        ext_rect = pygame.Rect(
            self.x + self.main_width, 
            self.y + self.main_height - self.ext_height, 
            self.ext_width, 
            self.ext_height
        )
        return [main_rect, ext_rect]
    
    def _is_external_wall(self, tile_rect, room_rects):
        """Verifica se uma tile é uma parede externa."""
        directions = [
            (0, -self.tile_size),
            (0, self.tile_size),
            (-self.tile_size, 0),
            (self.tile_size, 0)
        ]
        
        is_on_border = False
        for rect in room_rects:
            if rect.contains(tile_rect):
                rel_x = tile_rect.x - rect.x
                rel_y = tile_rect.y - rect.y
                tiles_wide = rect.width // self.tile_size
                tiles_tall = rect.height // self.tile_size
                tx = rel_x // self.tile_size
                ty = rel_y // self.tile_size
                
                if (tx == 0 or tx == tiles_wide - 1 or 
                    ty == 0 or ty == tiles_tall - 1):
                    is_on_border = True
                    break
        
        if not is_on_border:
            return False
        
        for dx, dy in directions:
            neighbor_rect = pygame.Rect(tile_rect.x + dx, tile_rect.y + dy, self.tile_size, self.tile_size)
            is_inside_room = any(rect.contains(neighbor_rect) for rect in room_rects)
            if not is_inside_room:
                return True
        
        return False
    
    def _get_l_tile_type(self, tile_rect, room_rects):
        """Determina o tipo de tile para salas em formato de L."""
        directions = {
            'top': (0, -self.tile_size),
            'bottom': (0, self.tile_size),
            'left': (-self.tile_size, 0),
            'right': (self.tile_size, 0)
        }
        
        external_directions = []
        
        for direction, (dx, dy) in directions.items():
            neighbor_x = tile_rect.x + dx
            neighbor_y = tile_rect.y + dy
            neighbor_rect = pygame.Rect(neighbor_x, neighbor_y, self.tile_size, self.tile_size)
            is_inside_room = any(rect.contains(neighbor_rect) for rect in room_rects)
            if not is_inside_room:
                external_directions.append(direction)
        
        if len(external_directions) >= 2:
            if 'top' in external_directions and 'left' in external_directions:
                return 'corner_top_left'
            elif 'top' in external_directions and 'right' in external_directions:
                return 'corner_top_right'
            elif 'bottom' in external_directions and 'left' in external_directions:
                return 'corner_bottom_left'
            elif 'bottom' in external_directions and 'right' in external_directions:
                return 'corner_bottom_right'
        elif len(external_directions) == 1:
            direction = external_directions[0]
            return f'wall_{direction}'
        
        return 'wall'

    def _add_concave_corner_fillers(self):
        """Adiciona tile de preenchimento para o canto côncavo interno do L."""
        # Para uma sala em L, há apenas um canto côncavo interno
        # onde o braço horizontal se encontra com o braço vertical
        
        # Posição do canto côncavo interno (onde o L se dobra)
        # Este deve ser o tile à esquerda do gap, no canto interno do main rect
        corner_x = self.x + self.main_width - self.tile_size
        corner_y = self.y + self.main_height - self.ext_height
        
        # Cria o tile de preenchimento
        filler_tile = {
            'rect': pygame.Rect(corner_x, corner_y, self.tile_size, self.tile_size),
            'type': 'concave_filler',
            'grid_pos': (corner_x // self.tile_size, corner_y // self.tile_size)
        }
        
        self.wall_tiles.append(filler_tile)

    def is_floor_tile(self, x, y):
        for tile in self.wall_tiles:
            if tile['rect'].collidepoint(x, y):
                return False
        l_rects = self._get_l_rectangles()
        return any(rect.collidepoint(x, y) for rect in l_rects)
    
    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        l_rects = self._get_l_rectangles()
        for rect in l_rects:
            floor_rect = pygame.Rect(rect.x - camera_x, rect.y - camera_y, rect.width, rect.height)
            pygame.draw.rect(surface, self.floor_color, floor_rect)
        
        for tile in self.wall_tiles:
            self._draw_tile(surface, tile, camera_x, camera_y)
            if show_collision_rects:
                rect = tile['rect']
                debug_rect = pygame.Rect(rect.x - camera_x, rect.y - camera_y, rect.width, rect.height)
                pygame.draw.rect(surface, (255, 0, 0), debug_rect, 2)

        for dust in self.dust_particles:
            dust.render(surface, camera_x, camera_y)
