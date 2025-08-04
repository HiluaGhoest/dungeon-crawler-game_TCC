import pygame
import random
import math
from collections import deque
from game.room import Room
from game.room_generator import RoomGenerator

class DungeonNode:
    """Represents a room in the branching dungeon tree."""
    def __init__(self, room, depth, is_true_ending=False):
        self.room = room
        self.children = []
        self.depth = depth
        self.is_true_ending = is_true_ending
        self.parent = None

class BranchingDungeon:
    """Manages a branching dungeon with multiple paths and one true ending."""
    
    def __init__(self, tile_size=20, max_depth=5, max_children=3):
        self.tile_size = tile_size
        self.max_depth = max_depth
        self.max_children = max_children
        self.room_generator = RoomGenerator(tile_size=tile_size)
        self.root = None
        self.current_node = None
        self.rooms = []
        self.true_ending_room = None
        self.visited_rooms = set()
        
        # Generate the dungeon tree
        self._generate_dungeon_tree()
        
    def _generate_dungeon_tree(self):
        """Generate the branching dungeon tree structure."""
        # Create root room
        root_room = self.room_generator.generate_rectangular_room(
            0, 0, min_width=12, max_width=18, min_height=12, max_height=16, is_first_room=True
        )
        root_node = DungeonNode(root_room, 0)
        self.root = root_node
        self.current_node = root_node
        self.rooms.append(root_room)
        
        # Generate tree using BFS
        queue = deque([root_node])
        while queue:
            current = queue.popleft()
            
            # Stop if we've reached max depth
            if current.depth >= self.max_depth:
                continue
                
            # Determine number of children (1-3)
            num_children = random.randint(1, min(self.max_children, self.max_depth - current.depth))
            
            # Generate child rooms
            for i in range(num_children):
                # Create new room
                new_room = self.room_generator.generate_random_room(0, 0)
                
                # Position relative to parent
                direction = random.choice(['right', 'bottom', 'left', 'top'])
                self._position_child_room(current.room, new_room, direction)
                
                # Create node
                is_true_ending = False
                if current.depth == self.max_depth - 1 and i == 0 and not self.true_ending_room:
                    is_true_ending = True
                    self.true_ending_room = new_room
                    
                child_node = DungeonNode(new_room, current.depth + 1, is_true_ending)
                child_node.parent = current
                current.children.append(child_node)
                self.rooms.append(new_room)
                
                # Add to queue if not at max depth
                if child_node.depth < self.max_depth - 1:
                    queue.append(child_node)
        
        # Set up connections for all rooms
        self._setup_all_connections()
        
    def _position_child_room(self, parent_room, child_room, direction):
        """Position a child room relative to its parent with safe randomization."""
        gap = self.tile_size * 3  # Gap between rooms
        
        # Ensure child room fits within parent's dimensions for alignment
        max_offset_x = max(0, parent_room.width - child_room.width)
        max_offset_y = max(0, parent_room.height - child_room.height)
        
        if direction == 'right':
            child_room.x = parent_room.x + parent_room.width + gap
            child_room.y = parent_room.y + (random.randint(0, max_offset_y) if max_offset_y > 0 else 0)
        elif direction == 'left':
            child_room.x = parent_room.x - child_room.width - gap
            child_room.y = parent_room.y + (random.randint(0, max_offset_y) if max_offset_y > 0 else 0)
        elif direction == 'bottom':
            child_room.x = parent_room.x + (random.randint(0, max_offset_x) if max_offset_x > 0 else 0)
            child_room.y = parent_room.y + parent_room.height + gap
        elif direction == 'top':
            child_room.x = parent_room.x + (random.randint(0, max_offset_x) if max_offset_x > 0 else 0)
            child_room.y = parent_room.y - child_room.height - gap
        
        # Fallback to center alignment if randomization wasn't possible
        if direction in ['right', 'left'] and max_offset_y <= 0:
            child_room.y = parent_room.y + (parent_room.height - child_room.height) // 2
        elif direction in ['bottom', 'top'] and max_offset_x <= 0:
            child_room.x = parent_room.x + (parent_room.width - child_room.width) // 2
    
    def _setup_all_connections(self):
        """Set up connections for all rooms in the dungeon."""
        # BFS through all rooms to set up connections
        queue = deque([self.root])
        visited = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            # Set up openings for this room
            self._setup_room_connections(current.room, current.parent, current.children)
            
            # Add children to queue
            for child in current.children:
                queue.append(child)
    
    def _setup_room_connections(self, room, parent, children):
        """Set up openings for a room based on its parent and children."""
        # Restore original walls
        if hasattr(room, 'original_wall_tiles'):
            room.wall_tiles = room.original_wall_tiles.copy()
        
        # Create opening for parent if exists
        if parent:
            parent_direction = self._get_relative_direction(room, parent.room)
            self._create_opening(room, parent_direction, 'previous')
        
        # Create openings for children
        for child in children:
            child_direction = self._get_relative_direction(room, child.room)
            self._create_opening(room, child_direction, 'next')
        
        # Mark as visited
        self.visited_rooms.add(id(room))
    
    def _get_relative_direction(self, room1, room2):
        """Determine the direction of room2 relative to room1."""
        # Calculate center points
        cx1 = room1.x + room1.width / 2
        cy1 = room1.y + room1.height / 2
        cx2 = room2.x + room2.width / 2
        cy2 = room2.y + room2.height / 2
        
        # Calculate differences
        dx = cx2 - cx1
        dy = cy2 - cy1
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            return 'right' if dx > 0 else 'left'
        else:
            return 'bottom' if dy > 0 else 'top'
    
    def _create_opening(self, room, direction, opening_type):
        """Create an opening in the specified direction."""
        opening_size = self.tile_size * 4
        
        if direction == 'right':
            opening_x = room.x + room.width
            opening_y = room.y + (room.height - opening_size) // 2
            orientation = 'vertical'
        elif direction == 'left':
            opening_x = room.x - self.tile_size
            opening_y = room.y + (room.height - opening_size) // 2
            orientation = 'vertical'
        elif direction == 'bottom':
            opening_x = room.x + (room.width - opening_size) // 2
            opening_y = room.y + room.height
            orientation = 'horizontal'
        elif direction == 'top':
            opening_x = room.x + (room.width - opening_size) // 2
            opening_y = room.y - self.tile_size
            orientation = 'horizontal'
        else:
            return
        
        # Create the opening
        if hasattr(room, 'wall_tiles'):
            # For tiled rooms, remove wall tiles in the opening area
            opening_rect = pygame.Rect(opening_x, opening_y, 
                                      self.tile_size if orientation == 'vertical' else opening_size,
                                      opening_size if orientation == 'vertical' else self.tile_size)
            
            # Find and remove wall tiles within the opening area
            tiles_to_remove = []
            for tile in room.wall_tiles[:]:
                if opening_rect.colliderect(tile['rect']):
                    tiles_to_remove.append(tile)
            
            for tile in tiles_to_remove:
                room.wall_tiles.remove(tile)
    
    def get_current_room(self):
        """Get the current room the player is in."""
        return self.current_node.room if self.current_node else None
    
    def check_opening_transitions(self, player_rect):
        """Check if player is walking through any openings to transition rooms."""
        current_room = self.get_current_room()
        if not current_room:
            return None
            
        # Check transitions to child rooms
        for child in self.current_node.children:
            direction = self._get_relative_direction(current_room, child.room)
            opening_rect = self._get_opening_rect(current_room, direction, 'next')
            
            if opening_rect and opening_rect.colliderect(player_rect):
                self.current_node = child
                return 'next'
        
        # Check transition to parent room
        if self.current_node.parent:
            direction = self._get_relative_direction(current_room, self.current_node.parent.room)
            opening_rect = self._get_opening_rect(current_room, direction, 'previous')
            
            if opening_rect and opening_rect.colliderect(player_rect):
                self.current_node = self.current_node.parent
                return 'previous'
        
        return None
    
    def _get_opening_rect(self, room, direction, opening_type):
        """Get the rectangle for an opening in the specified direction."""
        opening_size = self.tile_size * 4
        
        if direction == 'right':
            return pygame.Rect(
                room.x + room.width, 
                room.y + (room.height - opening_size) // 2,
                self.tile_size,
                opening_size
            )
        elif direction == 'left':
            return pygame.Rect(
                room.x - self.tile_size,
                room.y + (room.height - opening_size) // 2,
                self.tile_size,
                opening_size
            )
        elif direction == 'bottom':
            return pygame.Rect(
                room.x + (room.width - opening_size) // 2,
                room.y + room.height,
                opening_size,
                self.tile_size
            )
        elif direction == 'top':
            return pygame.Rect(
                room.x + (room.width - opening_size) // 2,
                room.y - self.tile_size,
                opening_size,
                self.tile_size
            )
        return None
    
    def is_true_ending(self):
        """Check if the player is in the true ending room."""
        return self.current_node and self.current_node.is_true_ending
    
    def render(self, surface, camera_x=0, camera_y=0, show_collision_rects=False):
        """Render all rooms in the dungeon."""
        # Render all rooms
        for room in self.rooms:
            room.render(surface, camera_x, camera_y, show_collision_rects)
            
        # Highlight current room
        current_room = self.get_current_room()
        if current_room:
            highlight_rect = pygame.Rect(
                current_room.x - camera_x,
                current_room.y - camera_y,
                current_room.width,
                current_room.height
            )
            pygame.draw.rect(surface, (100, 255, 100, 100), highlight_rect, 3)
            
        # Highlight true ending room
        if self.true_ending_room:
            ending_rect = pygame.Rect(
                self.true_ending_room.x - camera_x,
                self.true_ending_room.y - camera_y,
                self.true_ending_room.width,
                self.true_ending_room.height
            )
            pygame.draw.rect(surface, (255, 100, 100, 100), ending_rect, 3)
    
    def render_minimap(self, surface, width=200, height=200):
        """Render a minimap of the dungeon."""
        if not self.rooms:
            return
            
        # Find bounds of all rooms
        min_x = min(room.x for room in self.rooms)
        max_x = max(room.x + room.width for room in self.rooms)
        min_y = min(room.y for room in self.rooms)
        max_y = max(room.y + room.height for room in self.rooms)
        
        # Calculate scale
        scale_x = width / (max_x - min_x)
        scale_y = height / (max_y - min_y)
        scale = min(scale_x, scale_y)
        
        # Draw all rooms
        for room in self.rooms:
            # Calculate minimap position
            x = (room.x - min_x) * scale
            y = (room.y - min_y) * scale
            w = room.width * scale
            h = room.height * scale
            
            # Draw room
            color = (100, 100, 200)  # Blue for regular rooms
            if room == self.get_current_room():
                color = (100, 255, 100)  # Green for current room
            elif room == self.true_ending_room:
                color = (255, 100, 100)  # Red for true ending
                
            pygame.draw.rect(surface, color, (x, y, w, h))
            pygame.draw.rect(surface, (200, 200, 200), (x, y, w, h), 1)
            
        # Draw connections
        for room in self.rooms:
            if id(room) not in self.visited_rooms:
                continue
                
            # Draw connections to children
            for direction in ['right', 'left', 'bottom', 'top']:
                opening_rect = self._get_opening_rect(room, direction, 'next')
                if opening_rect:
                    # Calculate center of opening
                    center_x = (opening_rect.x + opening_rect.width/2 - min_x) * scale
                    center_y = (opening_rect.y + opening_rect.height/2 - min_y) * scale
                    
                    # Draw connection line in direction
                    if direction == 'right':
                        end_x = center_x + 10
                        end_y = center_y
                    elif direction == 'left':
                        end_x = center_x - 10
                        end_y = center_y
                    elif direction == 'bottom':
                        end_x = center_x
                        end_y = center_y + 10
                    elif direction == 'top':
                        end_x = center_x
                        end_y = center_y - 10
                        
                    pygame.draw.line(surface, (200, 200, 100), (center_x, center_y), (end_x, end_y), 2)