import pygame
import random
import math
import heapq
from game.room import Room
from game.weapons.weapon import Weapon
from game.weapons.ranged_weapons import Pistol, DoublePistol
from game.weapons.melee_weapons import SteelSword
from game.powerups.perks import Perk, HealthBoostPerk, SpeedBoostPerk, DamageBoostPerk

class RoomGenerator:
    """Gerador de salas com formatos aleatórios."""
    
    def __init__(self, tile_size=20):
        self.tile_size = tile_size

    def generate_rectangular_room(self, x, y, depth=0, min_width=12, max_width=32, min_height=12, max_height=32, allow_islands=True, allow_subrooms=True, is_first_room=False):
        """Gera uma sala retangular simples."""
        growth_factor = 1 + 0.15 * depth
        min_w = int(min_width * growth_factor)
        max_w = int(max_width * growth_factor)
        min_h = int(min_height * growth_factor)
        max_h = int(max_height * growth_factor)
        width = random.randint(min_w, max_w) * self.tile_size
        height = random.randint(min_h, max_h) * self.tile_size
        
        room = TiledRoom(x, y, width, height, self.tile_size)
        return room
    
    def generate_first_room(self, x, y, min_width=12, max_width=32, min_height=12, max_height=32, allow_islands=True, allow_subrooms=True, is_first_room=False, spawn_perks=False):
        """Gera uma sala retangular simples."""
        width = random.randint(min_width, max_width) * self.tile_size
        height = random.randint(min_height, max_height) * self.tile_size
        room = TiledRoom(x, y, width, height, self.tile_size)
        if is_first_room:
            # Se for a sala da loja, gera perks nos pilares
            room.add_pillars_in_circle(count=8, spawn_perks=spawn_perks)
        return room

    
    def generate_l_shaped_room(self, x, y, depth=0):
        """Gera uma sala em formato de L."""
        growth_factor = 1 + 0.15 * depth
        main_width = random.randint(int(12 * growth_factor), int(32 * growth_factor)) * self.tile_size
        main_height = random.randint(int(22 * growth_factor), int(22 * growth_factor)) * self.tile_size
        ext_width = random.randint(int(8 * growth_factor), int(15 * growth_factor)) * self.tile_size
        ext_height_tiles = random.randint(int(8 * growth_factor), int(12 * growth_factor))
        
        max_ext_height_tiles = (main_height // self.tile_size) // 2
        if ext_height_tiles > max_ext_height_tiles:
            ext_height_tiles = max_ext_height_tiles
        
        if ext_height_tiles < 2:
            ext_height_tiles = 2
        
        ext_height = ext_height_tiles * self.tile_size
        
        
        return LShapedRoom(x, y, main_width, main_height, ext_width, ext_height, self.tile_size)
    
    def generate_random_room(self, x, y, is_first_room=False, last_opening_direction=None, spawn_perks=False):
        if is_first_room:
            # Se for a sala da loja, gera perks nos pilares
            return self.generate_first_room(x, y, is_first_room=True, spawn_perks=spawn_perks)
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
        return room_type(x, y)
    

class Pillar:
    def __init__(self, x, y, tile_size, weapon=None, toggleable=True):
        self.rect = pygame.Rect(x, y, tile_size * 2, tile_size * 2)
        self.weapon = weapon      # arma que o pilar tem
        self.original_weapon = weapon  # usada para restaurar se for toggle
        self.toggleable = toggleable   # se True, a arma volta pro pilar quando trocada
        self.interacted = False

    def interact(self, player):
        # Não é mais possível devolver armas ao pilar
        if self.weapon and not player.weapon:
            player.weapon = self.weapon
            player.weapon_origin = self if self.toggleable else None
            print(f"[PILLAR] {self.weapon.name} pega pelo jogador.")
            self.weapon = None
            return
        if self.weapon and player.weapon and self.weapon != player.weapon:
            player.drop_weapon()
            player.weapon = self.weapon
            player.weapon_origin = self if self.toggleable else None
            print(f"[PILLAR] Arma trocada: agora o jogador tem {player.weapon.name}")
            self.weapon = None

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        render_rect = self.rect.move(-camera_x, -camera_y)
        weapon_render_rect = render_rect.move(0, -32)
        if self.weapon:
            center = weapon_render_rect.center
            self.weapon.render_static(surface, center, camera_x, camera_y, zoom)

class PerkPillar:
    def __init__(self, x, y, tile_size, perk=None, base_cost=10, perks_save_path="perks.json"):
        self.rect = pygame.Rect(x, y, tile_size * 2, tile_size * 2)
        self.perk = perk
        self.interacted = False
        # Definir cor baseada no tipo de perk
        self.color = (180, 220, 120)  # padrão
        if perk:
            if perk.name == "Health Boost":
                self.color = (220, 80, 80)      # vermelho
            elif perk.name == "Speed Boost":
                self.color = (80, 180, 220)     # azul
            elif perk.name == "Damage Boost":
                self.color = (220, 180, 80)     # amarelo

    def interact(self, player, stardust_manager=None, perks_save_path="perks.json"):
        # Permite comprar o perk se tiver Stardust suficiente
        if self.perk and stardust_manager:
            import os, json
            level = 1
            if os.path.exists(perks_save_path):
                try:
                    with open(perks_save_path, "r") as f:
                        perks = json.load(f)
                        for p in perks:
                            if isinstance(p, dict) and p.get("name") == self.perk.name:
                                level = p.get("level", 1)
                                break
                except Exception:
                    level = 1
            cost = int((9 * level ** 2) / 4)
            if stardust_manager.spend_stardust(cost):
                self.perk.apply(player)
                # Feedback visual: animação simples de compra
                self.interacted = True
                print(f"[PERK PILLAR] {self.perk.name} comprado por {cost} Stardust.")
                # Salva perk adquirido
                perks = []
                if os.path.exists(perks_save_path):
                    with open(perks_save_path, "r") as f:
                        try:
                            perks = json.load(f)
                        except Exception:
                            perks = []
                # Verifica se o perk já existe e incrementa o nível
                found = False
                for p in perks:
                    if isinstance(p, dict) and p.get("name") == self.perk.name:
                        p["level"] = p.get("level", 1) + 1
                        found = True
                        break
                if not found:
                    perks.append({"name": self.perk.name, "level": 1})
                with open(perks_save_path, "w") as f:
                    json.dump(perks, f)
            else:
                # Feedback visual: animação de erro
                self.interacted = False
                print(f"[PERK PILLAR] Stardust insuficiente para comprar {self.perk.name}.")

    def render(self, surface, camera_x=0, camera_y=0, zoom=1.0):
        render_rect = self.rect.move(-camera_x, -camera_y)
        pygame.draw.ellipse(surface, self.color, render_rect)
        # Exibe o custo do perk (sempre atualizado e sem símbolo, cor branca)
        if self.perk:
            import os, json
            level = 1
            perks_save_path = "perks.json"
            if os.path.exists(perks_save_path):
                try:
                    with open(perks_save_path, "r") as f:
                        perks = json.load(f)
                        for p in perks:
                            if isinstance(p, dict) and p.get("name") == self.perk.name:
                                level = p.get("level", 1)
                                break
                except Exception:
                    level = 1
            cost = int((9 * level ** 2) / 4)
            font = pygame.font.SysFont('arial', 16)
            cost_text = font.render(f"{cost}", True, (255, 255, 255))
            surface.blit(cost_text, (render_rect.centerx - cost_text.get_width() // 2, render_rect.bottom + 2))
        # Feedback visual: animação simples
        if self.interacted:
            pygame.draw.ellipse(surface, (255, 255, 0), render_rect, 4)

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

        self.cached_surface = None
        self._cache_room_surface()

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

    def add_pillars_in_circle(self, count=8, spawn_perks=False):
        import math
        import random
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2
        radius = min(self.width, self.height) // 3
        if spawn_perks:
            available_perks = [HealthBoostPerk, SpeedBoostPerk, DamageBoostPerk]
            perk_types = available_perks.copy()
            random.shuffle(perk_types)
            for i in range(count):
                angle = (2 * math.pi / count) * i
                px = center_x + int(radius * math.cos(angle))
                py = center_y + int(radius * math.sin(angle))
                tile_x = (px // self.tile_size) * self.tile_size
                tile_y = (py // self.tile_size) * self.tile_size
                perk = perk_types[i]() if i < len(perk_types) else None
                pillar = PerkPillar(tile_x, tile_y, self.tile_size, perk=perk)
                self.pillar_tiles.append(pillar)
        else:
            available_weapons = [SteelSword, Pistol, DoublePistol]
            weapon_types = available_weapons.copy()
            random.shuffle(weapon_types)
            for i in range(count):
                angle = (2 * math.pi / count) * i
                px = center_x + int(radius * math.cos(angle))
                py = center_y + int(radius * math.sin(angle))
                tile_x = (px // self.tile_size) * self.tile_size
                tile_y = (py // self.tile_size) * self.tile_size
                weapon = weapon_types[i]() if i < len(weapon_types) else None
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
    
    def _cache_room_surface(self):
        """Render static room elements to a cached surface."""
        import pygame
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Draw floor
        floor_rect = pygame.Rect(0, 0, self.width, self.height)
        surface.fill(self.floor_color, floor_rect)
        # Draw wall tiles
        for tile in self.wall_tiles:
            rect = tile['rect'].copy()
            rect.x -= self.x
            rect.y -= self.y
            pygame.draw.rect(surface, self.wall_color, rect)
        # Draw pillars
    # Não desenhar o retângulo do pilar, apenas renderizar a arma (feito no método render do Pillar)
        # Draw dust particles
        for dust in self.dust_particles:
            dust_x = int(dust.x - self.x)
            dust_y = int(dust.y - self.y)
            s = pygame.Surface((dust.size, dust.size), pygame.SRCALPHA)
            s.fill((*dust.color, dust.alpha))
            surface.blit(s, (dust_x, dust_y))
        self.cached_surface = surface

    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Renderiza a sala usando cached surface for static elements."""
        if self.cached_surface:
            render_rect = pygame.Rect(self.x - camera_x, self.y - camera_y, self.width, self.height)
            surface.blit(self.cached_surface, render_rect)
        # Draw dynamic elements (e.g., dropped weapons, animated effects) as needed
        # Draw pillars and their weapons
        for pillar in self.pillar_tiles:
            pillar.render(surface, camera_x, camera_y)
        # ...existing code for dynamic rendering if needed




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
        self.cached_surface = None
        self._cache_room_surface()
    
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
    
    def _cache_room_surface(self):
        """Render static L-shaped room elements to a cached surface."""
        import pygame
        surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Draw floor for each L rectangle
        l_rects = self._get_l_rectangles()
        for rect in l_rects:
            floor_rect = pygame.Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)
            surface.fill(self.floor_color, floor_rect)
        # Draw wall tiles
        for tile in self.wall_tiles:
            rect = tile['rect'].copy()
            rect.x -= self.x
            rect.y -= self.y
            pygame.draw.rect(surface, self.wall_color, rect)
        # Draw pillars
        for pillar in self.pillar_tiles:
            pillar_rect = pillar.rect.copy()
            pillar_rect.x -= self.x
            pillar_rect.y -= self.y
            pygame.draw.rect(surface, (100, 100, 120), pillar_rect)
        # Draw dust particles
        for dust in self.dust_particles:
            dust_x = int(dust.x - self.x)
            dust_y = int(dust.y - self.y)
            s = pygame.Surface((dust.size, dust.size), pygame.SRCALPHA)
            s.fill((*dust.color, dust.alpha))
            surface.blit(s, (dust_x, dust_y))
        self.cached_surface = surface

    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Renderiza a sala em L usando cached surface."""
        if self.cached_surface:
            render_rect = pygame.Rect(self.x - camera_x, self.y - camera_y, self.width, self.height)
            surface.blit(self.cached_surface, render_rect)
        # Draw pillars and their weapons
        for pillar in self.pillar_tiles:
            pillar.render(surface, camera_x, camera_y)
        # ...existing code for dynamic rendering if needed...
