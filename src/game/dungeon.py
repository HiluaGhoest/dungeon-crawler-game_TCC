import pygame
import random
from collections import defaultdict, deque
from game.room_generator import RoomGenerator


class Dungeon:
    def get_adjacent_room_indices(self, index):
        """Return a list of indices for the current room and its directly connected rooms."""
        adjacent = [index]
        if index in self.room_connections:
            adjacent += [i for i in self.room_connections[index] if i != index]
        return adjacent

    """Manages the dungeon progression through multiple rooms."""
    
    def __init__(self, tile_size=20, total_rooms=25, branching_factor=3):
        self.tile_size = tile_size
        self.total_rooms = total_rooms
        self.branching_factor = branching_factor
        self.current_room_index = 0
        self.previous_room_index = None
        self.room_generator = RoomGenerator(tile_size=tile_size)
        self.rooms = {}
        self.opening_positions = []
        self.room_opening_configs = {}
        self.room_opening_sides = {}
        self.room_connections = {}  # Tracks connections between rooms
        self.room_parent = {}       # Tracks parent-child relationships
        self.room_depth = {}        # Tracks depth from start room
        self.occupied_positions = set()

        # Generate all rooms at their final positions
        self._generate_and_position_rooms()
        
        # Reset to first room after generation
        self.current_room_index = 0
        self.previous_room_index = None
    
    def _generate_and_position_rooms(self):
        """Generate and position all rooms of the dungeon with branching paths."""
        print(f"[DUNGEON] Generating {self.total_rooms} rooms with branching...")
        self.room_reserved_sides = defaultdict(set)
        self.direction_deltas = {
            'top': (0, -1),
            'bottom': (0, 1),
            'left': (-1, 0),
            'right': (1, 0),
        }

        # Create first room
        first_room = self.room_generator.generate_rectangular_room(
            0, 0, min_width=12, max_width=18, min_height=12, max_height=16,
            is_first_room=True
        )
        self.rooms[0] = first_room
        self.room_depth[0] = 0
        self.room_connections[0] = []
        self.room_parent[0] = None

        room_queue = deque([0])
        rooms_created = 1

        # FIRST PASS: Build connection graph
        while rooms_created < self.total_rooms and room_queue:
            parent_idx = room_queue.popleft()
            parent_depth = self.room_depth[parent_idx]

            possible_sides = ['top', 'bottom', 'left', 'right']
            random.shuffle(possible_sides)

            branches = random.randint(1, min(self.branching_factor, self.total_rooms - rooms_created))
            for _ in range(branches):
                if rooms_created >= self.total_rooms:
                    break

                # Get available sides for this parent
                used_sides = self.room_reserved_sides[parent_idx]
                available_sides = [side for side in possible_sides if side not in used_sides]
                if not available_sides:
                    break  # No more directions to branch

                chosen_side = available_sides[0]
                self.room_reserved_sides[parent_idx].add(chosen_side)

                child_idx = rooms_created
                self.rooms[child_idx] = None  # Placeholder
                self.room_depth[child_idx] = parent_depth + 1
                self.room_connections[child_idx] = []
                self.room_parent[child_idx] = parent_idx

                self.room_connections[parent_idx].append(child_idx)
                self.room_connections[child_idx].append(parent_idx)

                room_queue.append(child_idx)
                rooms_created += 1

                
                # Store this directional connection
                if parent_idx not in self.room_opening_sides:
                    self.room_opening_sides[parent_idx] = {'next': {}}
                self.room_opening_sides[parent_idx]['next'][child_idx] = chosen_side

        # SECOND PASS: Generate rooms and position them
        room_queue = deque([0])
        visited = set()

        while room_queue:
            room_idx = room_queue.popleft()
            visited.add(room_idx)

            # Garante que sala atual exista
            if self.rooms[room_idx] is None:
                self.rooms[room_idx] = self.room_generator.generate_random_room(0, 0)

            self.current_room_index = room_idx

            # Criar openings da sala atual (pai)
            self._setup_current_room_connections()

            for child_idx in self.room_connections[room_idx]:
                if self.room_parent[child_idx] == room_idx and child_idx not in visited:

                    # Criar a sala filha em (0,0)
                    if self.rooms[child_idx] is None:
                        self.rooms[child_idx] = self.room_generator.generate_random_room(0, 0)

                    # Criar openings da sala filha em 0,0
                    self.current_room_index = child_idx
                    self._setup_current_room_connections()

                    # Posicionar sala filha com base nos openings do pai e da filha
                    self._position_new_room(child_idx)

                    # Com a sala filha posicionada, criar os triggers (baseados nos openings posicionados)
                    self._create_triggers_for_room(child_idx)

                    room_queue.append(child_idx)
                    visited.add(child_idx)



        print(f"[DUNGEON] Created {rooms_created} rooms with branching structure")
        print(f"Room connections: {self.room_connections}")


    def _position_new_room(self, child_idx):
        """Position a newly generated child room relative to its parent using opening alignment."""
        print(f"[DEBUG] Room {child_idx} parent is {self.room_parent.get(child_idx)}")

        parent_idx = self.room_parent[child_idx]
        print(f"[POSITION] Positioning room {child_idx} relative to parent {parent_idx}")

        self.previous_room_index = parent_idx  # <-- FIX HERE

        parent_room = self.rooms[parent_idx]
        child_room = self.rooms[child_idx]

        # Get the side the parent used to connect to this child
        parent_side = None
        if parent_idx in self.room_opening_sides:
            next_dict = self.room_opening_sides[parent_idx].get('next', {})
            parent_side = next_dict.get(child_idx, None)

        print(f"[POSITION] Parent room {parent_idx} opening side for child {child_idx}: {parent_side}")

        # Get parent and child openings
        parent_opening = self._get_opening_rect(parent_room, f'next_{child_idx}')
        child_opening = self._get_opening_rect(child_room, 'previous')

        print(f"[DEBUG] Parent opening rect (room {parent_idx}, next_{child_idx}): {parent_opening}")
        print(f"[DEBUG] Child opening rect (room {child_idx}, previous): {child_opening}")

        if parent_opening and child_opening:
            parent_opening_global = parent_opening.move(parent_room.x, parent_room.y)
            child_opening_global = child_opening.move(child_room.x, child_room.y)

            # Align openings: shift the child to match the parent opening
            dx = parent_opening_global.centerx - child_opening_global.centerx
            dy = parent_opening_global.centery - child_opening_global.centery

            # Add a small intentional gap between rooms
            gap = self.tile_size
            if parent_side == 'top':
                dy -= gap
            elif parent_side == 'bottom':
                dy += gap
            elif parent_side == 'left':
                dx -= gap
            elif parent_side == 'right':
                dx += gap

            child_room.shift_position(dx, dy)
            print(f"[DUNGEON] Room {child_idx} positioned at ({child_room.x}, {child_room.y})")
        else:
            # Fallback: place to the right with large spacing
            print(f"[WARNING] Missing openings for precise positioning, using fallback.")
            fallback_gap = self.tile_size * 5
            dx = parent_room.x + parent_room.width + fallback_gap - child_room.x
            dy = parent_room.y - child_room.y
            proposed_x = child_room.x + dx
            proposed_y = child_room.y + dy
            proposed_pos = (proposed_x, proposed_y)

            # Check for overlapping room positions
            if proposed_pos in self.occupied_positions:
                print(f"[WARNING] Overlapping room detected at {proposed_pos}. Trying to shift...")
                
                # Try shifting away to avoid overlap (example: shift right multiple tiles)
                # You can expand this to try multiple fallback directions
                dx += self.tile_size * 10  # shift further to the right
                proposed_x = child_room.x + dx
                proposed_y = child_room.y + dy
                proposed_pos = (proposed_x, proposed_y)

            child_room.shift_position(dx, dy)
            self.occupied_positions.add((child_room.x, child_room.y))
            print(f"[DUNGEON] Room {child_idx} (fallback) positioned at ({child_room.x}, {child_room.y})")
        
    def _get_opening_rect(self, room, opening_type):
        if hasattr(room, 'opening_rects'):
            for key, rect in room.opening_rects.items():
                if key == opening_type or key.startswith(opening_type):
                    return rect
        return None


    def _setup_current_room_connections(self):
        """Setup wall openings for connections to adjacent rooms."""
        current_room = self.rooms[self.current_room_index]
        room_idx = self.current_room_index
        
        print(f"[DEBUG] Setting up room {room_idx} connections...")
        
        # Restore original wall tiles before creating openings
        if hasattr(current_room, 'original_wall_tiles'):
            current_room.wall_tiles = current_room.original_wall_tiles.copy()
            print(f"[DEBUG] Restored original wall tiles for room {room_idx}")
        elif hasattr(current_room, 'original_walls'):
            current_room.walls = current_room.original_walls.copy()
            print(f"[DEBUG] Restored original walls for room {room_idx}")
        
        # Check if we already have opening configuration for this room
        if room_idx in self.room_opening_configs:
            print(f"[DEBUG] Using existing opening config for room {room_idx}")
            opening_config = self.room_opening_configs[room_idx]
            self._restore_openings_from_config(current_room, opening_config)
            print(f"[DEBUG] Restored {len(self.opening_positions)} openings for room {room_idx}")
        else:
            print(f"[DEBUG] Creating new openings for room {room_idx}")
            opening_size = self.tile_size * 4
            self.opening_positions = []
            
            # Determine opening sides based on spatial logic
            opening_sides = self._get_opening_sides_for_room()
            self.room_opening_sides[self.current_room_index] = opening_sides

            print(f"[DEBUG] Opening sides for room {room_idx}: {opening_sides}")
            
            # For all room types, create openings on the determined sides
            if hasattr(current_room, 'wall_tiles'):
                print(f"[DEBUG] Creating openings on tiled room {room_idx}")
                self._create_opening_rects_on_tiled_room(current_room, opening_size, opening_sides)
            else:
                print(f"[DEBUG] Creating openings on standard room {room_idx}")
                self._create_openings_on_standard_room(current_room, opening_size, opening_sides)
            
            print(f"[DEBUG] Created {len(self.opening_positions)} openings for room {room_idx}")
            
            # Store the opening configuration and sides
            self._store_opening_configuration(current_room)
            self.room_opening_sides[room_idx] = opening_sides
            print(f"[DEBUG] Stored opening config for room {room_idx} with {len(self.room_opening_configs[room_idx]['openings'])} openings")
        
        print(f"[DEBUG] Room {room_idx} wall tiles: {len(current_room.wall_tiles) if hasattr(current_room, 'wall_tiles') else 'N/A'}")
        print(f"[DEBUG] Room {room_idx} walls: {len(current_room.walls) if hasattr(current_room, 'walls') else 'N/A'}")
        
    def _get_opening_sides_for_room(self):
        print(f"[DEBUG] current_room_index: {self.current_room_index}")
        print(f"[DEBUG] self.room_connections: {self.room_connections}")
        print(f"[DEBUG] self.room_opening_sides: {self.room_opening_sides}")

        opening_sides = self.room_opening_sides.get(self.current_room_index, {})  # preserve any existing data

        # For ALL rooms, set next openings for their children
        children = [neighbor for neighbor in self.room_connections.get(self.current_room_index, [])
                    if self.room_parent.get(neighbor) == self.current_room_index]

        print(f"[DEBUG] Children for room {self.current_room_index}: {children}")

        if children:
            # Exclude the side used for the previous opening (connection to parent)
            available_sides = ['top', 'right', 'bottom', 'left']
            prev_side = None
            if self.current_room_index != 0:
                parent_idx = self.room_parent.get(self.current_room_index)
                parent_side = None
                if parent_idx in self.room_opening_sides:
                    next_dict = self.room_opening_sides[parent_idx].get('next', {})
                    parent_side = next_dict.get(self.current_room_index, None)
                if parent_side:
                    prev_side = self._get_opposite_side(parent_side)
            if prev_side and prev_side in available_sides:
                available_sides.remove(prev_side)
            assigned_sides = {}
            opening_sides['next'] = opening_sides.get('next', {})
            for child_idx in children:
                if not available_sides:
                    print(f"[WARNING] Not enough sides to assign unique openings for all children of room {self.current_room_index}")
                    break
                side = available_sides.pop(0)
                assigned_sides[child_idx] = side
                opening_sides['next'][child_idx] = side
                print(f"[OPENING_SIDES] Room {self.current_room_index} child {child_idx} assigned to {side} side")
                # Store the parent’s info immediately
                if self.current_room_index not in self.room_opening_sides:
                    self.room_opening_sides[self.current_room_index] = {}
                self.room_opening_sides[self.current_room_index].setdefault('next', {})[child_idx] = side

        if self.current_room_index == 0:
            # Starting room has no previous opening
            pass
        else:
            parent_idx = self.room_parent.get(self.current_room_index)
            print(f"[OPENING_SIDES] Room {self.current_room_index}: parent is {parent_idx}")

            parent_side = None
            if parent_idx in self.room_opening_sides:
                next_dict = self.room_opening_sides[parent_idx].get('next', {})
                parent_side = next_dict.get(self.current_room_index, None)
                if parent_side:
                    opening_sides['previous'] = self._get_opposite_side(parent_side)
                    print(f"[OPENING_SIDES] Setting previous opening to opposite: {self._get_opposite_side(parent_side)}")
                    print(f"[OPENING_SIDES] Parent side for child {self.current_room_index}: {parent_side}")

            if parent_side is None:
                print(f"[WARNING] Parent side unknown for room {self.current_room_index}, using heuristic")
                current_room = self.rooms[self.current_room_index]
                parent_room = self.rooms[parent_idx]
                dx = current_room.x - parent_room.x
                dy = current_room.y - parent_room.y
                if abs(dx) > abs(dy):
                    parent_side = 'right' if dx > 0 else 'left'
                else:
                    parent_side = 'bottom' if dy > 0 else 'top'
                print(f"[HEURISTIC] Set parent_side as {parent_side} based on position ({dx}, {dy})")

            if parent_side:
                # The previous opening in the child should be on the same side as the parent's connection to the child
                opening_sides['previous'] = self._get_opposite_side(parent_side)
                print(f"[OPENING_SIDES] Setting previous opening to opposite: {self._get_opposite_side(parent_side)} (parent side: {parent_side})")

        # Finally, persist the computed sides
        self.room_opening_sides.setdefault(self.current_room_index, {}).update(opening_sides)
        print(f"[OPENING_SIDES] Final opening sides for room {self.current_room_index}: {opening_sides}")
        return opening_sides



    def _get_opening_by_type(self, room, opening_type):
        """Get opening data by type for a room."""
        room_index = next((i for i, r in self.rooms.items() if r is room), None)

        if room_index is None or room_index not in self.room_opening_configs:
            return None

        if room_index not in self.room_opening_configs:
            return None
        
        for opening in self.room_opening_configs[room_index]['openings']:
            # Match either exact type or type prefix
            if opening.get('type') == opening_type or opening.get('type', '').startswith(opening_type):
                return opening
        return None
    
    def _get_opposite_side(self, side):
        """Get the opposite side of a wall."""
        opposites = {
            'top': 'bottom',
            'bottom': 'top', 
            'left': 'right',
            'right': 'left'
        }
        return opposites.get(side, 'left')
    
    def _store_opening_configuration(self, room):
        """Store the current opening configuration for this room."""
        config = {
            'openings': [],
            'removed_tiles': [],
            'wall_modifications': []
        }
        
        # Store opening information
        for opening in self.opening_positions:
            config['openings'].append({
                'position': opening,
                'type': opening.get('type', 'opening')
            })
        
        # Store which tiles were removed (for tiled rooms)
        if hasattr(room, 'original_wall_tiles') and hasattr(room, 'wall_tiles'):
            original_tiles = {(tile['rect'].x, tile['rect'].y): tile for tile in room.original_wall_tiles}
            current_tiles = {(tile['rect'].x, tile['rect'].y): tile for tile in room.wall_tiles}
            
            for pos, tile in original_tiles.items():
                if pos not in current_tiles:
                    config['removed_tiles'].append(tile)
        
        # Store wall modifications (for standard rooms)
        if hasattr(room, 'original_walls') and hasattr(room, 'walls'):
            config['wall_modifications'] = {
                'original': room.original_walls.copy(),
                'modified': room.walls.copy()
            }
        
        self.room_opening_configs[self.current_room_index] = config
    
    def _restore_openings_from_config(self, room, config):
        """Restore openings from stored configuration."""
        # Restore opening positions
        self.opening_positions = []
        for opening_data in config.get('openings', []):
            self.opening_positions.append(opening_data['position'])
        
        # Restore removed tiles (for tiled rooms)
        if hasattr(room, 'wall_tiles') and config['removed_tiles']:
            for removed_tile in config['removed_tiles']:
                if removed_tile in room.wall_tiles:
                    room.wall_tiles.remove(removed_tile)
        
        # Restore wall modifications (for standard rooms)
        if 'wall_modifications' in config and config['wall_modifications']:
            room.walls = config['wall_modifications']['modified'].copy()
    
    def _create_openings_on_standard_room(self, room, opening_size, opening_sides):
        """Create openings on standard rectangular rooms with specified sides."""
        print(f"[OPENINGS] Creating openings on standard room (index {self.current_room_index}) with sides: {opening_sides}")
        
        # Process all openings in the config
        for key, side in opening_sides.items():
            # Handle next openings (next_0, next_1, etc)
            if key.startswith('next'):
                opening_pos = self._get_opening_position_for_side(room, side, opening_size)
                if opening_pos:
                    opening_x, opening_y, orientation = opening_pos
                    self._create_opening_in_wall(room, opening_x, opening_y, opening_size, orientation)
                    opening_type = 'next'
                    
                    # Determine dimensions
                    if orientation == 'horizontal':
                        width = opening_size
                        height = self.tile_size
                    else:
                        width = self.tile_size
                        height = opening_size
                    
                    self.opening_positions.append({
                        'x': opening_x, 'y': opening_y,
                        'width': width, 'height': height,
                        'orientation': orientation,
                        'type': opening_type,
                        'side': side
                    })
        
        # Previous opening (if not first room)
        if 'previous' in opening_sides and self.current_room_index > 0:
            prev_side = opening_sides['previous']
            opening_pos = self._get_opening_position_for_side(room, prev_side, opening_size)
            if opening_pos:
                opening_x, opening_y, orientation = opening_pos
                self._create_opening_in_wall(room, opening_x, opening_y, opening_size, orientation)
                
                # Determine dimensions
                if orientation == 'horizontal':
                    width = opening_size
                    height = self.tile_size
                else:
                    width = self.tile_size
                    height = opening_size
                
                self.opening_positions.append({
                    'x': opening_x, 'y': opening_y,
                    'width': width, 'height': height,
                    'orientation': orientation,
                    'type': 'previous',
                    'side': prev_side
                })
    
    def _create_openings_on_tiled_room(self, room, opening_size, opening_sides):
        print(f"[OPENINGS] Creating openings on tiled room (index {self.current_room_index}) with sides: {opening_sides}")
        wall_tiles = getattr(room, 'wall_tiles', [])
        
        if not wall_tiles:
            return

        opening_size = self.tile_size * 3

        wall_sides = {'top': [], 'bottom': [], 'left': [], 'right': []}
        for tile in wall_tiles:
            tile_rect = tile['rect']
            tile_x = tile_rect.x
            tile_y = tile_rect.y
            
            if tile_y <= room.y + self.tile_size:
                wall_sides['top'].append(tile)
            elif tile_y >= room.y + room.height - self.tile_size:
                wall_sides['bottom'].append(tile)
            elif tile_x <= room.x + self.tile_size:
                wall_sides['left'].append(tile)
            elif tile_x >= room.x + room.width - self.tile_size:
                wall_sides['right'].append(tile)
        

        openings_to_create = []
        # Always use the current room's geometry for previous opening
        if 'previous' in opening_sides:
            prev_side = opening_sides['previous']
            openings_to_create.append(('previous', prev_side, None))
        if 'next' in opening_sides and isinstance(opening_sides['next'], dict):
            for child_idx, side in opening_sides['next'].items():
                openings_to_create.append((f'next_{child_idx}', side, child_idx))

        # Inicializar dicionário de aberturas da sala (se não existir)
        if not hasattr(room, 'opening_rects'):
            room.opening_rects = {}

        for opening_type, side, child_idx in openings_to_create:
            if side in wall_sides and wall_sides[side]:
                if opening_type == 'previous':
                    print(f"[DEBUG] Creating 'previous' opening in room {self.current_room_index} on side '{side}'")
                    print(f"[DEBUG] Room y: {room.y}, Room height: {room.height}")
                    print(f"[DEBUG] Wall tiles for side '{side}': {[t['rect'] for t in wall_sides[side]]}")
                opening_tiles = self._find_best_opening_tiles(wall_sides[side], room, opening_size)
                if opening_tiles:
                    for tile in opening_tiles:
                        if tile in room.wall_tiles:
                            room.wall_tiles.remove(tile)
                    first_tile = opening_tiles[0]['rect']
                    opening_x = first_tile.x
                    opening_y = first_tile.y
                    if side in ['top', 'bottom']:
                        width = len(opening_tiles) * self.tile_size
                        height = self.tile_size
                        orientation = 'horizontal'
                    else:
                        width = self.tile_size
                        height = len(opening_tiles) * self.tile_size
                        orientation = 'vertical'
                    # Criar pygame.Rect para abertura
                    opening_rect = pygame.Rect(opening_x, opening_y, width, height)
                    room.opening_rects[opening_type] = opening_rect
                    # Optional: Expand the trigger a little in the direction of the opening
                    trigger_rect = pygame.Rect(opening_x, opening_y, width, height)
                    if opening_type == 'previous':
                        parent_idx = self.room_parent[self.current_room_index]
                        parent_room = self.rooms[parent_idx]
                        # Find the trigger rect that leads to us
                        for trigger in getattr(parent_room, 'opening_triggers', []):
                            if trigger.get('target') == self.current_room_index:
                                # Mirror the position (in the opposite direction)
                                opening_rect_mirrored = trigger['rect'].copy()
                                if side == 'top':
                                    opening_rect_mirrored.y += self.tile_size * -1
                                elif side == 'bottom':
                                    opening_rect_mirrored.y -= self.tile_size * -1
                                elif side == 'left':
                                    opening_rect_mirrored.x += self.tile_size * -1
                                elif side == 'right':
                                    opening_rect_mirrored.x -= self.tile_size * -1
                                trigger_rect = opening_rect_mirrored
                                break
                    else:
                        if side == 'top':
                            trigger_rect.y -= self.tile_size
                        elif side == 'bottom':
                            trigger_rect.y += self.tile_size
                        elif side == 'left':
                            trigger_rect.x -= self.tile_size
                        elif side == 'right':
                            trigger_rect.x += self.tile_size
                    if opening_type == 'previous':
                        print(f"[DEBUG] Created 'previous' opening trigger rect: {trigger_rect}")
                    # Store per-room!
                    if not hasattr(room, 'opening_triggers'):
                        room.opening_triggers = []
                    # For 'previous', set target to parent index at creation time
                    if 'next_' in opening_type:
                        target_idx = child_idx
                    else:
                        target_idx = self.room_parent[self.current_room_index]
                    room.opening_triggers.append({
                        'rect': trigger_rect,
                        'type': opening_type,
                        'side': side,
                        'target': target_idx
                    })
                    # Always append to opening_positions for both next and previous
                    self.opening_positions.append({
                        'x': opening_x,
                        'y': opening_y,
                        'width': width,
                        'height': height,
                        'orientation': orientation,
                        'type': opening_type if 'next_' in opening_type else 'previous',
                        'side': side
                    })
                    print(f"[OPENINGS] Created opening '{opening_type}' at {opening_rect} on side '{side}' in room {self.current_room_index}")

    def _create_opening_rects_on_tiled_room(self, room, opening_size, opening_sides):
        print(f"[OPENINGS] Creating opening rects (no triggers) on room {self.current_room_index}")

        wall_tiles = getattr(room, 'wall_tiles', [])
        if not wall_tiles:
            return

        wall_sides = {'top': [], 'bottom': [], 'left': [], 'right': []}
        for tile in wall_tiles:
            tile_rect = tile['rect']
            tile_x = tile_rect.x
            tile_y = tile_rect.y

            if tile_y <= room.y + self.tile_size:
                wall_sides['top'].append(tile)
            elif tile_y >= room.y + room.height - self.tile_size:
                wall_sides['bottom'].append(tile)
            elif tile_x <= room.x + self.tile_size:
                wall_sides['left'].append(tile)
            elif tile_x >= room.x + room.width - self.tile_size:
                wall_sides['right'].append(tile)

        openings_to_create = []
        if 'previous' in opening_sides:
            prev_side = opening_sides['previous']
            openings_to_create.append(('previous', prev_side, None))
        if 'next' in opening_sides and isinstance(opening_sides['next'], dict):
            for child_idx, side in opening_sides['next'].items():
                openings_to_create.append((f'next_{child_idx}', side, child_idx))

        if not hasattr(room, 'opening_rects'):
            room.opening_rects = {}

        for opening_type, side, child_idx in openings_to_create:
            if side in wall_sides and wall_sides[side]:
                opening_tiles = self._find_best_opening_tiles(wall_sides[side], room, opening_size)
                if opening_tiles:
                    for tile in opening_tiles:
                        if tile in room.wall_tiles:
                            room.wall_tiles.remove(tile)
                    first_tile = opening_tiles[0]['rect']
                    opening_x = first_tile.x
                    opening_y = first_tile.y
                    if side in ['top', 'bottom']:
                        width = len(opening_tiles) * self.tile_size
                        height = self.tile_size
                        orientation = 'horizontal'
                    else:
                        width = self.tile_size
                        height = len(opening_tiles) * self.tile_size
                        orientation = 'vertical'

                    opening_rect = pygame.Rect(opening_x, opening_y, width, height)
                    room.opening_rects[opening_type] = opening_rect

                    self.opening_positions.append({
                        'x': opening_x,
                        'y': opening_y,
                        'width': width,
                        'height': height,
                        'orientation': orientation,
                        'type': opening_type,
                        'side': side
                    })

                    print(f"[OPENINGS] Created opening rect '{opening_type}' at {opening_rect} on side '{side}'")

    def _create_triggers_for_room(self, room_idx):
        print(f"[DEBUG] Creating triggers for room {room_idx}...")

        room = self.rooms[room_idx]
        if not hasattr(room, 'opening_rects'):
            print(f"[DEBUG] Room {room_idx} has no 'opening_rects' attribute. Aborting trigger creation.")
            return

        if not hasattr(room, 'opening_triggers'):
            room.opening_triggers = []
        room.opening_triggers.clear()

        opening_rects = room.opening_rects
        if not opening_rects:
            print(f"[DEBUG] Room {room_idx} has empty 'opening_rects'. No triggers created.")
            return

        for opening_type, rect in opening_rects.items():
            print(f"[DEBUG] Processing opening '{opening_type}' with rect {rect}")

            side = None
            found_side = False
            for o in self.opening_positions:
                if o['type'] == opening_type:
                    side = o['side']
                    found_side = True
                    print(f"[DEBUG] Found side '{side}' for opening '{opening_type}'")
                    break
            if not found_side:
                print(f"[WARNING] No side found in 'opening_positions' for opening '{opening_type}'")

            trigger_rect = rect.copy()
            if side:
                if side == 'top':
                    trigger_rect.y -= self.tile_size
                elif side == 'bottom':
                    trigger_rect.y += self.tile_size
                elif side == 'left':
                    trigger_rect.x -= self.tile_size
                elif side == 'right':
                    trigger_rect.x += self.tile_size
                print(f"[DEBUG] Adjusted trigger_rect for side '{side}': {trigger_rect}")
            else:
                print(f"[WARNING] Side is None, trigger_rect not adjusted: {trigger_rect}")

            if 'next_' in opening_type:
                try:
                    target_idx = int(opening_type.split('_')[1])
                except Exception as e:
                    print(f"[ERROR] Failed to parse target index from opening_type '{opening_type}': {e}")
                    target_idx = None
            else:
                target_idx = self.room_parent.get(room_idx, None)

            print(f"[DEBUG] Trigger target index for '{opening_type}': {target_idx}")

            room.opening_triggers.append({
                'rect': trigger_rect,
                'type': opening_type,
                'side': side,
                'target': target_idx
            })

            print(f"[TRIGGER] Created trigger for '{opening_type}' at {trigger_rect} targeting room {target_idx}")


    def _create_openings_on_standard_tiled_room(self, room, opening_size, opening_sides, wall_tiles):
        """Create openings on standard tiled rooms (non-cross)."""
        # Categorize wall tiles by sides - only include tiles on flat surfaces
        wall_sides = {
            'top': [],
            'bottom': [],
            'left': [],
            'right': []
        }
        
        for tile in wall_tiles:
            tile_rect = tile['rect']
            tile_x = tile_rect.x
            tile_y = tile_rect.y
            
            # Check if this tile is on a flat wall surface by examining its neighbors
            # Count adjacent wall tiles in each direction
            left_wall = any(t['rect'].x == tile_x - self.tile_size and t['rect'].y == tile_y for t in wall_tiles)
            right_wall = any(t['rect'].x == tile_x + self.tile_size and t['rect'].y == tile_y for t in wall_tiles)
            top_wall = any(t['rect'].x == tile_x and t['rect'].y == tile_y - self.tile_size for t in wall_tiles)
            bottom_wall = any(t['rect'].x == tile_x and t['rect'].y == tile_y + self.tile_size for t in wall_tiles)
            
            # Check if tile is on exterior edge (not inside room)
            has_floor_inside = False
            if hasattr(room, 'is_floor_tile'):
                # Check interior adjacent positions for floor tiles
                interior_positions = [
                    (tile_x + self.tile_size//2, tile_y + self.tile_size),      # Below
                    (tile_x + self.tile_size//2, tile_y - self.tile_size),      # Above  
                    (tile_x + self.tile_size, tile_y + self.tile_size//2),      # Right
                    (tile_x - self.tile_size, tile_y + self.tile_size//2)       # Left
                ]
                has_floor_inside = any(room.is_floor_tile(x, y) for x, y in interior_positions)
            
            # Categorize based on position and neighboring tiles
            # Top wall: at top edge of room bounds, has horizontal neighbors or floor below
            if (tile_rect.y <= room.y + self.tile_size and 
                (left_wall or right_wall or has_floor_inside)):
                wall_sides['top'].append(tile)
            
            # Bottom wall: at bottom edge of room bounds, has horizontal neighbors or floor above
            elif (tile_rect.y >= room.y + room.height - self.tile_size * 2 and
                  (left_wall or right_wall or has_floor_inside)):
                wall_sides['bottom'].append(tile)
            
            # Left wall: at left edge of room bounds, has vertical neighbors or floor to right
            elif (tile_rect.x <= room.x + self.tile_size and
                  (top_wall or bottom_wall or has_floor_inside)):
                wall_sides['left'].append(tile)
            
            # Right wall: at right edge of room bounds, has vertical neighbors or floor to left
            elif (tile_rect.x >= room.x + room.width - self.tile_size * 2 and
                  (top_wall or bottom_wall or has_floor_inside)):
                wall_sides['right'].append(tile)
        
        # Create next opening (if next side is specified)
        if 'next' in opening_sides:
            next_side = opening_sides['next']
            if next_side in wall_sides and wall_sides[next_side]:
                opening_tiles = self._find_best_opening_tiles(wall_sides[next_side], room, opening_size)
                if opening_tiles:
                    for tile in opening_tiles:
                        if tile in room.wall_tiles:
                            room.wall_tiles.remove(tile)
                    
                    opening_x = opening_tiles[0]['rect'].x
                    opening_y = opening_tiles[0]['rect'].y
                    opening_type = 'ending' if self.current_room_index == self.total_rooms - 1 else 'next'
                    
                    # Determine orientation and dimensions based on side
                    if next_side in ['top', 'bottom']:
                        orientation = 'horizontal'
                        width = opening_size
                        height = self.tile_size
                    else:
                        orientation = 'vertical'
                        width = self.tile_size
                        height = opening_size
                    
                    self.opening_positions.append({
                        'x': opening_x, 'y': opening_y,
                        'width': width, 'height': height,
                        'orientation': orientation,
                        'type': opening_type,
                        'side': next_side
                    })
        
        # Create previous opening (if not first room)
        if 'previous' in opening_sides and self.current_room_index > 0:
            prev_side = opening_sides['previous']
            if prev_side in wall_sides and wall_sides[prev_side]:
                opening_tiles = self._find_best_opening_tiles(wall_sides[prev_side], room, opening_size)
                if opening_tiles:
                    for tile in opening_tiles:
                        if tile in room.wall_tiles:
                            room.wall_tiles.remove(tile)
                    
                    opening_x = opening_tiles[0]['rect'].x
                    opening_y = opening_tiles[0]['rect'].y
                    
                    # Determine orientation and dimensions based on side
                    if prev_side in ['top', 'bottom']:
                        orientation = 'horizontal'
                        width = opening_size
                        height = self.tile_size
                    else:
                        orientation = 'vertical'
                        width = self.tile_size
                        height = opening_size
                    
                    self.opening_positions.append({
                        'x': opening_x, 'y': opening_y,
                        'width': width, 'height': height,
                        'orientation': orientation,
                        'type': 'previous',
                        'side': prev_side
                    })
    
    def _get_opening_position_for_side(self, room, side, opening_size):
        """Get opening position in exact middle of wall with tile alignment"""
        wall_thickness = self.tile_size
        if side == 'top':
            opening_x = room.x + (room.width - opening_size) // 2
            # Align to tile grid
            opening_x = (opening_x // self.tile_size) * self.tile_size
            opening_y = room.y
            return (opening_x, opening_y, 'horizontal')
        
        elif side == 'bottom':
            opening_x = room.x + (room.width - opening_size) // 2
            opening_x = (opening_x // self.tile_size) * self.tile_size
            opening_y = room.y + room.height - wall_thickness
            return (opening_x, opening_y, 'horizontal')
        
        elif side == 'left':
            opening_x = room.x
            opening_y = room.y + (room.height - opening_size) // 2
            opening_y = (opening_y // self.tile_size) * self.tile_size
            return (opening_x, opening_y, 'vertical')
        
        elif side == 'right':
            opening_x = room.x + room.width - wall_thickness
            opening_y = room.y + (room.height - opening_size) // 2
            opening_y = (opening_y // self.tile_size) * self.tile_size
            return (opening_x, opening_y, 'vertical')
        
        return None
    
    def _create_opening_in_wall(self, room, opening_x, opening_y, opening_size, orientation):
        """Create an opening in standard room walls."""
        if hasattr(room, 'walls'):
            opening_rect = pygame.Rect(opening_x, opening_y, 
                                     room.wall_thickness if orientation == 'vertical' else opening_size,
                                     opening_size if orientation == 'vertical' else room.wall_thickness)
            
            # Find which wall intersects with the opening and split it
            new_walls = []
            for wall in room.walls:
                if wall.colliderect(opening_rect):
                    # Split the wall around the opening
                    if orientation == 'vertical':
                        # Split horizontal wall
                        if wall.top < opening_y:
                            new_walls.append(pygame.Rect(wall.left, wall.top, wall.width, opening_y - wall.top))
                        if wall.bottom > opening_y + opening_size:
                            new_walls.append(pygame.Rect(wall.left, opening_y + opening_size, wall.width, wall.bottom - (opening_y + opening_size)))
                    else:
                        # Split vertical wall
                        if wall.left < opening_x:
                            new_walls.append(pygame.Rect(wall.left, wall.top, opening_x - wall.left, wall.height))
                        if wall.right > opening_x + opening_size:
                            new_walls.append(pygame.Rect(opening_x + opening_size, wall.top, wall.right - (opening_x + opening_size), wall.height))
                else:
                    new_walls.append(wall)
            
            room.walls = new_walls
    
    def _find_best_opening_tiles(self, edge_tiles, room, opening_size):
        """Find the best position for an opening among edge tiles."""
        if not edge_tiles:
            return None

        # Calculate how many tiles we need
        tiles_needed = opening_size // self.tile_size
        
        # Sort tiles based on position
        first_tile = edge_tiles[0]['rect']
        is_horizontal = first_tile.y in [room.y, room.y + room.height - self.tile_size]
        
        if is_horizontal:
            edge_tiles.sort(key=lambda t: t['rect'].x)
        else:
            edge_tiles.sort(key=lambda t: t['rect'].y)
        
        # Find the longest consecutive run of tiles
        best_run = []
        current_run = [edge_tiles[0]]
        
        for i in range(1, len(edge_tiles)):
            prev_tile = edge_tiles[i-1]
            curr_tile = edge_tiles[i]
            
            # Check if tiles are consecutive
            if is_horizontal:
                consecutive = (curr_tile['rect'].x == prev_tile['rect'].x + self.tile_size)
            else:
                consecutive = (curr_tile['rect'].y == prev_tile['rect'].y + self.tile_size)
            
            if consecutive:
                current_run.append(curr_tile)
            else:
                if len(current_run) > len(best_run):
                    best_run = current_run
                current_run = [curr_tile]
        
        if len(current_run) > len(best_run):
            best_run = current_run
        
        # Select the best run that meets the requirement
        if len(best_run) >= tiles_needed:
            # Take center tiles
            start_index = (len(best_run) - tiles_needed) // 2
            return best_run[start_index:start_index + tiles_needed]
        
        # Fallback: take as many consecutive as possible
        return best_run[:tiles_needed] if best_run else None

    
    def _find_nearest_walkable_position(self, room, target_x, target_y, max_search_radius=300):
        """Find the nearest walkable position to the target coordinates using BFS."""
        # Convert to tile coordinates for grid-based search
        tile_x = int((target_x - room.x) / self.tile_size)
        tile_y = int((target_y - room.y) / self.tile_size)
        
        # BFS setup
        room_queue = deque([0])
        visited = set([0])

        while room_queue:
            room_idx = room_queue.popleft()
            
            # Generate and setup current room
            if self.rooms[room_idx] is None:
                self.rooms[room_idx] = self.room_generator.generate_random_room(0, 0)
            self.current_room_index = room_idx
            self._setup_current_room_connections()
            
            # Process children
            for child_idx in self.room_connections[room_idx]:
                if self.room_parent[child_idx] == room_idx and child_idx not in visited:
                    # Generate and setup child room BEFORE positioning
                    if self.rooms[child_idx] is None:
                        self.rooms[child_idx] = self.room_generator.generate_random_room(0, 0)
                    
                    # Setup child openings BEFORE positioning
                    self.current_room_index = child_idx
                    self._setup_current_room_connections()
                    
                    # Now position relative to parent
                    self._position_new_room(room_idx, child_idx)
                    visited.add(child_idx)
                    room_queue.append(child_idx)

    def _fallback_spawn_position(self, room):
        """Find any valid spawn position within a complex room by systematic search."""
        # For complex shaped rooms, search systematically
        if hasattr(room, 'is_floor_tile'):
            # Search in a grid pattern starting from room center
            center_x = room.x + room.width // 2
            center_y = room.y + room.height // 2
            
            # Create search pattern: center outward in expanding squares
            for radius in range(0, max(room.width, room.height) // (2 * self.tile_size)):
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if abs(dx) == radius or abs(dy) == radius:  # Only check perimeter of square
                            test_x = center_x + dx * self.tile_size
                            test_y = center_y + dy * self.tile_size
                            
                            # Check if position is valid
                            if room.is_floor_tile(test_x, test_y):
                                player_rect = pygame.Rect(test_x - 8, test_y - 8, 16, 16)
                                if not self._position_in_wall(player_rect, room):
                                    return (test_x - 8, test_y - 8)
        
        # Ultimate fallback: return room center
        center_x = room.x + room.width // 2 - 8
        center_y = room.y + room.height // 2 - 8
        return (center_x, center_y)

    def get_current_room(self):
        """Get the current room."""
        return self.rooms[self.current_room_index]
    
    def get_adjacent_rooms(self, index):
        """Return a list of rooms adjacent to the room at index (including itself)."""
        adjacent = [self.rooms[index]]
        
        # Add all connected rooms
        if index in self.room_connections:
            for connected_idx in self.room_connections[index]:
                adjacent.append(self.rooms[connected_idx])
        
        return adjacent
    

    def update_player_room(self, player_rect):
        """
        Update the current room index based on the player's position, but only check the current and directly connected rooms.
        Call this after the player moves. Handles cooldown to prevent rapid flicker.
        """
        now = pygame.time.get_ticks()
        if hasattr(self, 'last_transition_time'):
            if now - getattr(self, 'last_transition_time', 0) < 350:
                return  # Still in cooldown
        candidate_indices = self.get_adjacent_room_indices(self.current_room_index)
        for room_idx in candidate_indices:
            room = self.rooms.get(room_idx)
            if room is None:
                continue
            room_rect = pygame.Rect(room.x, room.y, room.width, room.height)
            if room_rect.colliderect(player_rect):
                if room_idx != self.current_room_index:
                    print(f"[DEBUG] Player moved from room {self.current_room_index} to {room_idx}")
                    self.previous_room_index = self.current_room_index
                    self.current_room_index = room_idx
                    self.last_transition_time = now
                break



    
    def get_opening_trigger_rects(self, camera_x=0, camera_y=0):
        """Return list of trigger rects for openings in current room"""
        trigger_rects = []
        current_room = self.get_current_room()
        
        for opening in self.opening_positions:
            width = opening.get('width', self.tile_size * 4)
            height = opening.get('height', self.tile_size)

            x = current_room.x + opening['x'] - camera_x
            y = current_room.y + opening['y'] - camera_y

            side = opening.get('side')
            if side == 'top':
                y -= self.tile_size
            elif side == 'bottom':
                y += self.tile_size
            elif side == 'left':
                x -= self.tile_size
            elif side == 'right':
                x += self.tile_size

            trigger_rect = pygame.Rect(x, y, width, height)
            trigger_rects.append((trigger_rect, opening.get('type')))
            
        return trigger_rects


    def _get_room_center_spawn(self, room):
        """Get position at center of room."""
        return (room.x + room.width//2 - 8, 
                room.y + room.height//2 - 8)

    def _get_connecting_opening_position(self):
        """Get spawn position near the opening connecting from previous room."""
        current_room = self.get_current_room()
        prev_room = self.rooms[self.previous_room_index]
        
        # Determine direction of movement
        moving_forward = self.current_room_index > self.previous_room_index
        opening_type = 'previous' if moving_forward else 'next'
        
        # Find the connecting opening
        for opening in self.opening_positions:
            if opening.get('type') == opening_type:
                # Position player 1 tile away from the opening
                if opening.get('side') == 'left':
                    return (opening['x'] + self.tile_size, 
                            opening['y'] + opening['height']//2 - 8)
                elif opening.get('side') == 'right':
                    return (opening['x'] - 16 - self.tile_size, 
                            opening['y'] + opening['height']//2 - 8)
                elif opening.get('side') == 'top':
                    return (opening['x'] + opening['width']//2 - 8,
                            opening['y'] + self.tile_size)
                elif opening.get('side') == 'bottom':
                    return (opening['x'] + opening['width']//2 - 8,
                            opening['y'] - 16 - self.tile_size)
        return None

    def _find_valid_spawn_position(self, room, x, y, max_radius=300):
        """Find valid spawn position using BFS with tile validation"""
        # Convert to tile coordinates
        tile_x = int((x - room.x) / self.tile_size)
        tile_y = int((y - room.y) / self.tile_size)
        
        queue = deque([(tile_x, tile_y, 0)])
        visited = set()
        
        while queue:
            tx, ty, dist = queue.popleft()
            world_x = room.x + tx * self.tile_size
            world_y = room.y + ty * self.tile_size
            
            # Position validation
            if self._is_valid_spawn_point(room, world_x, world_y):
                return (world_x - 8, world_y - 8)  # Player centering
                
            # Stop if exceeded search radius
            if dist * self.tile_size > max_radius:
                break
                
            # Explore neighbors
            for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                ntx, nty = tx + dx, ty + dy
                if (ntx, nty) not in visited:
                    # Check within room bounds
                    if (0 <= ntx < room.width // self.tile_size and 
                        0 <= nty < room.height // self.tile_size):
                        visited.add((ntx, nty))
                        queue.append((ntx, nty, dist + 1))
        return None

    def _is_valid_spawn_point(self, room, x, y):
        """Strict spawn validation"""
        player_rect = pygame.Rect(x - 8, y - 8, 16, 16)
        
        # 1. Must be within room boundaries
        room_rect = pygame.Rect(room.x, room.y, room.width, room.height)
        if not room_rect.contains(player_rect):
            return False
            
        # 2. Must not collide with walls
        if self._position_in_wall(player_rect, room):
            return False
            
        # 3. Must be on floor tile (for complex rooms)
        if hasattr(room, 'is_floor_tile'):
            return room.is_floor_tile(x, y)
            
        return True

    def get_player_spawn_position(self):
        """Get player spawn position for the current room"""
        if self.current_room_index == 0:
            # Special handling for first room - spawn in center
            first_room = self.rooms[0]
            spawn_x = first_room.x + first_room.width // 2 - 8  # Center player horizontally
            spawn_y = first_room.y + first_room.height // 2 - 8  # Center player vertically
            
            # Create a temporary player rect to check collisions
            player_rect = pygame.Rect(spawn_x, spawn_y, 16, 16)
            
            # If initial position is invalid, find nearest walkable position
            if self._position_in_wall(player_rect, first_room) or not self._is_valid_spawn_position(player_rect, first_room):
                final_spawn = self._find_nearest_walkable_position(first_room, spawn_x + 8, spawn_y + 8)

                if final_spawn:
                    # Adjust for player sprite top-left corner
                    return (final_spawn[0] - 8, final_spawn[1] - 8)
            
            return (spawn_x, spawn_y)
        else:
            # For other rooms, use the repositioning logic
            return self._reposition_player()
    
    def _is_valid_spawn_position(self, rect, room):
        """Check if a rectangle is a valid spawn position (not in walls and on valid floor)."""
        # First check if it's colliding with walls
        if self._position_in_wall(rect, room):
            return False
            
        # For complex shaped rooms, check if the center point is on valid floor
        center_x = rect.centerx
        center_y = rect.centery
        
        # Use room's floor validation if available
        if hasattr(room, 'is_floor_tile'):
            return room.is_floor_tile(center_x, center_y)
        else:
            # Fallback for simple rectangular rooms
            return (room.x <= center_x <= room.x + room.width and 
                   room.y <= center_y <= room.y + room.height)
    
    def _position_in_wall(self, rect, room):
        """Check if a rectangle is colliding with any walls."""
        if hasattr(room, 'wall_tiles'):
            for tile in room.wall_tiles:
                if rect.colliderect(tile['rect']):
                    return True
        elif hasattr(room, 'walls'):
            for wall in room.walls:
                if rect.colliderect(wall):
                    return True
        return False
    
    def _reposition_player(self):
        """Calculate player position at entrance of new room"""
        if self.previous_room_index is None:
            return self.get_spawn_position()
    
        # Get the new room
        new_room = self.get_current_room()
        
        # Find the entrance opening in the new room
        
        moving_forward = self.current_room_index > self.previous_room_index
        entrance_type = 'previous' if moving_forward else 'next'
        
        # Look for the entrance opening
        entrance_opening = None
        for opening in self.opening_positions:
            if opening.get('type') == entrance_type:
                entrance_opening = opening
                break
        
        if entrance_opening:
            # Calculate entrance position
            opening_width = entrance_opening.get('width', self.tile_size * 4)
            opening_height = entrance_opening.get('height', self.tile_size)
            opening_center_x = entrance_opening['x'] + opening_width // 2
            opening_center_y = entrance_opening['y'] + opening_height // 2
            
            # Determine offset based on opening side
            offset = self.tile_size * 1.5  # 1.5 tiles away from entrance
            
            if entrance_opening.get('side') == 'top':
                new_x = opening_center_x - 8  # Player width/2
                new_y = entrance_opening['y'] + opening_height + offset
            elif entrance_opening.get('side') == 'bottom':
                new_x = opening_center_x - 8
                new_y = entrance_opening['y'] - offset - 16  # Player height
            elif entrance_opening.get('side') == 'left':
                new_x = entrance_opening['x'] + opening_width + offset
                new_y = opening_center_y - 8
            elif entrance_opening.get('side') == 'right':
                new_x = entrance_opening['x'] - offset - 16
                new_y = opening_center_y - 8
            else:
                # Default to center of room
                new_x = new_room.x + new_room.width // 2 - 8
                new_y = new_room.y + new_room.height // 2 - 8
            
            return (new_x, new_y)
        
        # Fallback to room center
        return (
            new_room.x + new_room.width // 2 - 8,
            new_room.y + new_room.height // 2 - 8
        )

    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Render current room and adjacent rooms."""
        # Render current room
        self.get_current_room().render(surface, camera_x, camera_y, show_collision_rects=show_collision_rects)

        # Render adjacent rooms
        if self.current_room_index in self.room_connections:
            for connected_idx in self.room_connections[self.current_room_index]:
                self.rooms[connected_idx].render(surface, camera_x, camera_y, show_collision_rects=show_collision_rects)

        # Draw opening rects if debug enabled
        if show_collision_rects:
            # Draw all opening rects for current room
            room_index = self.current_room_index
            room = self.rooms[room_index]
            for opening in getattr(room, 'opening_triggers', []):
                pygame.draw.rect(surface, (255, 0, 0), opening['rect'].move(-camera_x, -camera_y), 2)
            
            # Draw trigger rects for openings
            for trigger_rect, opening_type in self.get_opening_trigger_rects(camera_x, camera_y):
                color = (255, 0, 0)  # Red for trigger rects
                pygame.draw.rect(surface, color, trigger_rect, 2)
                
                # Draw opening type text
                font = pygame.font.Font(None, 24)
                text = font.render(opening_type, True, (255, 255, 255))
                surface.blit(text, (trigger_rect.x, trigger_rect.y - 20))

    def _render_opening(self, surface, opening, camera_x, camera_y):
        """Render an opening as a visible gap with a decorative arch."""
        opening_rect = pygame.Rect(
            opening['x'] - camera_x,
            opening['y'] - camera_y,
            opening.get('width', self.tile_size * 4),
            opening.get('height', self.tile_size)
        )
        
        # Draw arch decoration
        arch_color = (80, 70, 60)
        arch_thickness = 3
        
        if opening.get('orientation') == 'horizontal':
            # Horizontal opening (top/bottom walls)
            pygame.draw.arc(
                surface, arch_color,
                (opening_rect.x - 10, opening_rect.y - 15, opening_rect.width + 20, 30),
                0, 3.14,  # Half circle
                arch_thickness
            )
        else:
            # Vertical opening (left/right walls)
            pygame.draw.arc(
                surface, arch_color,
                (opening_rect.x - 15, opening_rect.y - 10, 30, opening_rect.height + 20),
                1.57, 4.71,  # Half circle rotated
                arch_thickness
            )
            
    def transition_to_room(self, opening_type):
        """Transition to next or previous room with strict boundary checks."""
        current_time = pygame.time.get_ticks()
        
        # Add cooldown to prevent instant teleportation
        if hasattr(self, 'last_transition_time'):
            if current_time - self.last_transition_time < 300:  # 300ms cooldown
                return False
        
        # Store current room before transitioning
        prev_index = self.current_room_index
        success = False
        
        if opening_type == 'next' and self.current_room_index < self.total_rooms - 1:
            next_index = self.current_room_index + 1
            
            # Generate next room if it doesn't exist yet
            if next_index >= len(self.rooms):
                self.rooms.append(self._generate_room(next_index))
            
            self.current_room_index = next_index
            print(f"[DUNGEON] Moving to room {self.current_room_index + 1}/{self.total_rooms}")
            self._setup_current_room_connections()
            self.last_transition_time = current_time
            success = True
        
        elif opening_type == 'ending' and self.current_room_index == self.total_rooms - 1:
            print(f"[DUNGEON] Congratulations! You have completed all {self.total_rooms} rooms!")
            return False  # Game completed
        
        elif opening_type == 'previous' and self.current_room_index > 0:
            # Previous rooms are always generated, so no need to create
            self.current_room_index -= 1
            print(f"[DUNGEON] Moving back to room {self.current_room_index + 1}/{self.total_rooms}")
            self._setup_current_room_connections()
            self.last_transition_time = current_time
            success = True
        
        if success:
            # Validate new room boundaries
            new_room = self.get_current_room()
            if not self._validate_room_boundaries(new_room):
                # Revert on failure
                print(f"[DUNGEON] Room validation failed, reverting to room {prev_index + 1}")
                self.current_room_index = prev_index
                self._setup_current_room_connections()
                return False
                
        return success

    def _validate_room_boundaries(self, room):
        """Ensure room has valid openings within bounds"""
        room_rect = pygame.Rect(room.x, room.y, room.width, room.height)
        
        for opening in self.opening_positions:
            # Create opening rect with proper dimensions
            opening_rect = pygame.Rect(
                opening['x'], opening['y'],
                opening.get('width', opening.get('size', self.tile_size * 4)),
                opening.get('height', opening.get('size', self.tile_size))
            )
            
            # Check if opening is fully contained in room
            if not room_rect.contains(opening_rect):
                print(f"[VALIDATION] Opening out of bounds: {opening_rect} not in {room_rect}")
                return False
        
        return True
    
    def _validate_room_connection(self, prev_index, current_index):
        """Validate openings are perfectly aligned"""
        prev_room = self.rooms[prev_index]
        current_room = self.rooms[current_index]
    
        # Original rectangular room validation
        prev_opening = self._get_opening_rect(prev_room, 'next')
        current_opening = self._get_opening_rect(current_room, 'previous')
        
        if not prev_opening or not current_opening:
            return False
        
        # Check if openings are aligned within tolerance
        position_tolerance = self.tile_size // 2
        size_tolerance = self.tile_size
        
        # Position check
        if abs(prev_opening.centerx - current_opening.centerx) > position_tolerance:
            return False
        if abs(prev_opening.centery - current_opening.centery) > position_tolerance:
            return False
        
        # Size check
        if abs(prev_opening.width - current_opening.width) > size_tolerance:
            return False
        if abs(prev_opening.height - current_opening.height) > size_tolerance:
            return False
        
        return True


        
    def is_last_room(self):
        """Check if we're in the last room."""
        return self.current_room_index == self.total_rooms - 1
    
    def is_first_room(self):
        """Check if we're in the first room."""
        return self.current_room_index == 0
    
    def get_progress(self):
        """Get progress through the dungeon."""
        return (self.current_room_index + 1, self.total_rooms)
    
    def render_ui(self, surface):
        """Render UI elements like room counter and map."""
        font = pygame.font.Font(None, 36)
        small_font = pygame.font.Font(None, 24)
        
        # Room progress
        progress_text = f"Room {self.current_room_index + 1}/{self.total_rooms}"
        text_surface = font.render(progress_text, True, (255, 255, 255))
        surface.blit(text_surface, (20, 20))
        
        # Depth indicator
        depth = self.room_depth.get(self.current_room_index, 0)
        depth_text = f"Depth: {depth}"
        depth_surface = small_font.render(depth_text, True, (200, 200, 200))
        surface.blit(depth_surface, (20, 60))
        
        # Show connections
        if self.current_room_index in self.room_connections:
            connections = len(self.room_connections[self.current_room_index])
            conn_text = f"Paths: {connections}"
            conn_surface = small_font.render(conn_text, True, (180, 220, 180))
            surface.blit(conn_surface, (20, 90))
        
        # Show mini-map
        self._render_mini_map(surface)

    def _render_mini_map(self, surface):
        """Render a 3x3 grid mini-map centered on the current room, showing adjacent and next rooms."""
        map_size = 150
        map_margin = 20
        map_x = surface.get_width() - map_size - map_margin
        map_y = map_margin

        # Draw map background
        map_bg = pygame.Rect(map_x, map_y, map_size, map_size)
        pygame.draw.rect(surface, (40, 40, 60), map_bg)
        pygame.draw.rect(surface, (100, 100, 140), map_bg, 2)

        grid_size = 3
        cell_size = (map_size - 20) // grid_size
        grid_origin_x = map_x + 10
        grid_origin_y = map_y + 10

        # Center of grid
        center = (1, 1)
        current_idx = self.current_room_index

        # Build grid: (row, col) -> room index
        grid = [[None for _ in range(grid_size)] for _ in range(grid_size)]
        grid[center[0]][center[1]] = current_idx

        # Map directions to grid offsets
        dir_offsets = {
            'top': (-1, 0),
            'bottom': (1, 0),
            'left': (0, -1),
            'right': (0, 1)
        }

        # Place adjacent rooms in grid
        for conn_idx in self.room_connections.get(current_idx, []):
            # Try to determine direction from opening_sides if available
            side = None
            opening_sides = self.room_opening_sides.get(current_idx, {})
            if 'next' in opening_sides and isinstance(opening_sides['next'], dict):
                for child_idx, s in opening_sides['next'].items():
                    if child_idx == conn_idx:
                        side = s
                        break
            # Fallback: try parent relationship
            if side is None and self.room_parent.get(conn_idx) == current_idx:
                # Guess direction based on index difference (not always accurate)
                if conn_idx > current_idx:
                    side = 'right'
                else:
                    side = 'left'
            # Place in grid
            if side in dir_offsets:
                dr, dc = dir_offsets[side]
                r, c = center[0] + dr, center[1] + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    grid[r][c] = conn_idx

        # Show all ancestors (parents, grandparents, etc.) in the minimap as far as they fit
        parent_chain = []
        temp_idx = current_idx
        max_steps = grid_size * grid_size  # never more than grid cells
        for _ in range(max_steps):
            parent = self.room_parent.get(temp_idx)
            if parent is not None:
                parent_chain.append((parent, temp_idx))
                temp_idx = parent
            else:
                break

        # Place each parent in the grid if possible, following the chain
        prev_center = center
        for parent_idx, child_idx in parent_chain:
            # Try to find which side parent is on relative to its child
            side = None
            opening_sides = self.room_opening_sides.get(child_idx, {})
            if 'previous' in opening_sides:
                side = opening_sides['previous']
            if side in dir_offsets:
                dr, dc = dir_offsets[side]
                r, c = prev_center[0] + dr, prev_center[1] + dc
                if 0 <= r < grid_size and 0 <= c < grid_size:
                    if grid[r][c] is None:
                        grid[r][c] = parent_idx
                        prev_center = (r, c)
                    else:
                        break  # stop if cell is already filled

        # Draw grid cells
        font = pygame.font.SysFont(None, 18)
        for r in range(grid_size):
            for c in range(grid_size):
                cell_rect = pygame.Rect(
                    grid_origin_x + c * cell_size,
                    grid_origin_y + r * cell_size,
                    cell_size - 2,
                    cell_size - 2
                )
                room_idx = grid[r][c]
                if room_idx is not None and room_idx in self.rooms:
                    if room_idx == current_idx:
                        color = (255, 220, 50)  # Current room
                    elif room_idx == 0:
                        color = (50, 200, 80)   # Start room
                    elif not self.room_connections.get(room_idx) or len(self.room_connections.get(room_idx, [])) == 1:
                        color = (200, 100, 100)  # Dead end
                    else:
                        color = (220, 220, 220)  # Default
                    pygame.draw.rect(surface, color, cell_rect)
                    pygame.draw.rect(surface, (80, 80, 120), cell_rect, 1)
                    label = font.render(str(room_idx), True, (30, 30, 30))
                    surface.blit(label, (cell_rect.x + 2, cell_rect.y + 2))
                else:
                    pygame.draw.rect(surface, (60, 60, 80), cell_rect)
                    pygame.draw.rect(surface, (80, 80, 120), cell_rect, 1)

        # Draw grid lines
        for i in range(grid_size + 1):
            pygame.draw.line(surface, (100, 100, 140),
                             (grid_origin_x, grid_origin_y + i * cell_size),
                             (grid_origin_x + grid_size * cell_size, grid_origin_y + i * cell_size), 1)
            pygame.draw.line(surface, (100, 100, 140),
                             (grid_origin_x + i * cell_size, grid_origin_y),
                             (grid_origin_x + i * cell_size, grid_origin_y + grid_size * cell_size), 1)
