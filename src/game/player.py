
import math
import time
import pygame
from pygame import gfxdraw
from game.weapons.weapon import Weapon
from game.weapons.melee_weapons import MeleeWeapon
from game.weapons.ranged_weapons import RangedWeapon
from game.util.ui import ease_out_cubic
from game.assets import get_image, load_audio
import random

from game.util.sound_manager import SoundManager

class Player:
    def add_status(self, status_name, **kwargs):
        print(f"[DEBUG] Player: Adding status '{status_name}' with {kwargs}")
        if not hasattr(self, 'status_effects'):
            self.status_effects = {}
        self.status_effects[status_name] = kwargs
        print(f"[DEBUG] Player: Current status effects: {self.status_effects}")
    # Cache for footprint surfaces: (radius, alpha, side) -> Surface
    _footprint_surface_cache = {}
    # Cache for shadow surfaces: (width, height, alpha) -> Surface
    _shadow_surface_cache = {}
    # Cache for player body surfaces: (width, height, color, alpha) -> Surface
    _player_surface_cache = {}
    # Cache for death chunk surfaces: (size, color, alpha) -> Surface
    _death_chunk_surface_cache = {}
    # Cache for slot images by size
    _slot_image_cache = {}
    # Cache for horseshoe images by size and rotation
    _horseshoe_image_cache = {}
    _pickup_sound = load_audio('game/sounds/effects/change_weapons.wav')
    _swap_weapon_sound = load_audio('game/sounds/effects/change_weapons.wav')
    _die_sound = load_audio('game/sounds/effects/player_die.wav')
    _hit_sound = load_audio('game/sounds/effects/player_hit.wav')
    _pickup_sound.set_volume(2.0)
    _swap_weapon_sound.set_volume(2.0)
    def __init__(self, x, y, speed=5, color=(255, 255, 255), size=16):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.size = size
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.interact_key_pressed = False
        self.immunity_timer = 0.0
        self.immunity_duration = 0.3  # seconds of immunity after taking damage
        self._fire_powerup_timer = 0.0
        self._fire_powerup_interval = 1.0  # seconds between Ignition effect applications
        # Swing state now handled by weapon (if MeleeWeapon)

        # Health, Stamina
        self.max_health = 100
        self.health = self.max_health
        self.display_health = self.health

        self.max_stamina = 100
        self.stamina = self.max_stamina
        self.display_stamina = self.stamina

        # Player Weapons (3 slots)
        self.weapons = [None, None, None]  # 3 weapon slots
        self.active_weapon_index = 0
        self.weapon_origin = None  # pilar de onde veio a arma, se aplicável

        self.eye_bob_timer = 0.0        # controla o tempo do bob
        self.eye_bob_amplitude = 0.5    # altura máxima do bob (pixels)
        self.eye_bob_speed = 0.01        # velocidade do bob (ciclos por segundo)

        self.blink_timer = 0.0          # controla o tempo do piscar
        self.blink_interval = 3.0       # tempo entre piscadas (segundos)
        self.blink_duration = 0.2       # duração do piscar (segundos)
        self.is_blinking = False

        self.sprite = None  # Disable sprite rendering to allow animation
        self.color = color  # Use the provided color

        self.dropped_weapons = []  # List of (weapon, position)

        # Footprints system
        self.footprints = []  # List of (x, y, timestamp, side)
        self._last_footprint_pos = (self.x, self.y)
        self._footprint_distance = 18  # Minimum distance to leave a new footprint
        self._footprint_side = "left"  # Alternates between 'left' and 'right'

        # Power-up system
        self.powerups = {}  # theme -> current tier (int)
        self.active_powerup_effects = set()  # Set of effect functions to apply
        self.attack_held = False  # Track if attack button is held

        # Aplica perks salvos ao jogador
        self.apply_perk_levels()

    def get_powerup_tier(self, theme):
            """Get current tier for a theme."""
            return self.powerups.get(theme, 0)

    def apply_powerup(self, powerup, mouse_pos=None, enemies=None):
        print(f"[DEBUG] Player: Applying power-up '{powerup.name}' (Theme: {powerup.theme}, Tier: {powerup.tier})")
        self.powerups[powerup.theme] = powerup.tier
        if not hasattr(self, 'stored_powerup_effects'):
            self.stored_powerup_effects = set()
        if not hasattr(self, 'active_powerup_effects'):
            self.active_powerup_effects = set()
        # Determine effect type from theme or effect_func
        effect_type = None
        if hasattr(powerup, 'theme') and powerup.theme:
            if powerup.theme.lower() == 'poison':
                try:
                    from game.effects import PoisonEffect
                    effect_type = PoisonEffect
                except ImportError:
                    effect_type = None
            # Add more themes here as needed
            if powerup.theme.lower() == 'fire':
                try:
                    from game.effects import FireEffect
                    effect_type = FireEffect
                except ImportError:
                    effect_type = None
        # Fallback: try effect_func name
        if not effect_type and hasattr(powerup, 'effect_func') and powerup.effect_func:
            func_name = powerup.effect_func.__name__
            if 'poison' in func_name:
                try:
                    from game.effects import PoisonEffect
                    effect_type = PoisonEffect
                except ImportError:
                    effect_type = None
            if 'fire' in func_name:
                try:
                    from game.effects import FireEffect
                    effect_type = FireEffect
                except ImportError:
                    effect_type = None
        # Store effect type and function in sets to avoid duplicates
        if effect_type:
            self.stored_powerup_effects.add(effect_type)
            print(f"[DEBUG][Player] Stored power-up effect type: {effect_type}")
        if hasattr(powerup, 'effect_func') and powerup.effect_func:
            self.active_powerup_effects.add(powerup.effect_func)
        print(f"[DEBUG] Player: Calling effect function for '{powerup.name}'")
        powerup.apply(self)
        print(f"[DEBUG] Player: Power-up '{powerup.name}' applied. Current powerups: {self.powerups}")

    def has_powerup(self, theme, tier):
        return self.powerups.get(theme, 0) >= tier

    
    def apply_perk_levels(self, perks_save_path="perks.json"):
        """Aplica os efeitos dos perks salvos conforme o nível."""
        import os, json
        if os.path.exists(perks_save_path):
            try:
                with open(perks_save_path, "r") as f:
                    perks = json.load(f)
                for p in perks:
                    if not isinstance(p, dict):
                        continue
                    name = p.get("name")
                    level = p.get("level", 1)
                    if name == "Health Boost":
                        self.max_health = 100 + 5 * level
                        self.health = self.max_health
                        self.display_health = self.health
                    elif name == "Speed Boost":
                        self.speed = 5 + 0.1 * level
                    elif name == "Damage Boost":
                        self.damage_multiplier = 1.0 + 0.05 * level
            except Exception:
                pass

    def render_weapon_hud(self, surface, screen_width, screen_height):
        # HUD: 3 squares at bottom right, using images for slots and weapon sprites
        base_slot_size = 32 * 1.5
        selected_scale = 1.25
        spacing = 12 * 2
        margin = 24 * 2
        total_width = base_slot_size * 3 + spacing * 2
        x_start = screen_width - margin - total_width
        y = screen_height - margin - base_slot_size

        # Use cached slot images
        from game.assets import get_image, get_font
        selected_img_raw = get_image("hotbar_selected", "game/assets/sprites/ui/hotbar/selected.png")
        not_selected_img_raw = get_image("hotbar_not_selected", "game/assets/sprites/ui/hotbar/not_selected.png")

        # Calculate fixed slot centers
        slot_centers = []
        for i in range(3):
            cx = x_start + i * (base_slot_size + spacing) + base_slot_size // 2
            cy = y + base_slot_size // 2
            slot_centers.append((cx, cy))

        # Animate slot transitions with ease_out_cubic
        if not hasattr(self, '_hud_slot_progress'):
            self._hud_slot_progress = [0.0, 0.0, 0.0]
        for i in range(3):
            target = 1.0 if i == self.active_weapon_index else 0.0
            self._hud_slot_progress[i] += (target - self._hud_slot_progress[i]) * 0.2
            eased = ease_out_cubic(self._hud_slot_progress[i])

            slot_size = int(base_slot_size + (base_slot_size * (selected_scale - 1) * eased))
            cx, cy = slot_centers[i]
            rect = pygame.Rect(0, 0, slot_size, slot_size)
            rect.center = (cx, cy)

            # Draw slot background image with animation (cache scaled images)
            if selected_img_raw and not_selected_img_raw:
                img_key = ("selected" if i == self.active_weapon_index else "not_selected", slot_size)
                if img_key not in Player._slot_image_cache:
                    img = selected_img_raw if i == self.active_weapon_index else not_selected_img_raw
                    Player._slot_image_cache[img_key] = pygame.transform.smoothscale(img, (slot_size, slot_size))
                img_scaled = Player._slot_image_cache[img_key]
                surface.blit(img_scaled, rect)
            else:
                color = (255, 255, 0) if i == self.active_weapon_index else (180, 180, 180)
                border = 6 if i == self.active_weapon_index else 3
                pygame.draw.rect(surface, color, rect, border)

            weapon = self.weapons[i]
            # Only draw slot number if no weapon in slot
            if weapon is None:
                font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", int(slot_size * 0.5))
                num_surface = font.render(str(i+1), True, (255,255,255))
                num_rect = num_surface.get_rect(center=rect.center)
                surface.blit(num_surface, num_rect)

            # Draw weapon HUD: use custom method if available, else default sprite
            if weapon is not None:
                padding = int(slot_size * 0.18)
                sprite_size = int((slot_size - 2 * padding) * (0.9 + 0.1 * eased))
                # If weapon has custom HUD rendering, use it
                if hasattr(weapon, 'render_hud_sprite'):
                    weapon.render_hud_sprite(surface, rect, sprite_size)
                elif hasattr(weapon, 'sprite') and weapon.sprite is not None:
                    # Cache weapon sprite scaling
                    if not hasattr(weapon, '_hud_sprite_cache'):
                        weapon._hud_sprite_cache = {}
                    if sprite_size not in weapon._hud_sprite_cache:
                        weapon._hud_sprite_cache[sprite_size] = pygame.transform.smoothscale(weapon.sprite, (sprite_size, sprite_size))
                    weapon_img = weapon._hud_sprite_cache[sprite_size]
                    sprite_rect = weapon_img.get_rect(center=rect.center)
                    surface.blit(weapon_img, sprite_rect)
                    

    def render_weapon_info_overlay(self, surface, camera_x=0, camera_y=0, room=None, zoom=1.0):
        """
        Renders weapon info overlay above dropped weapons (and pillar weapons if desired) when player is in pickup range.
        Overlay appears between player and weapon, origin bottom left/right depending on player side.
        """

        px = self.x + self.size // 2
        py = self.y + self.size // 2
        pickup_radius = max(32 * 2, self.size)

        # Font for overlay
        from game.assets import FONTS
        info_font = FONTS["overlay"]

        # Overlay position: always on right side above weapon HUD
        screen_width = surface.get_width()
        margin = 24 * 2
        base_slot_size = 32 * 1.5
        spacing = 12 * 2
        total_width = base_slot_size * 3 + spacing * 2
        hud_x_start = screen_width - margin - total_width
        hud_y = surface.get_height() - margin - base_slot_size
        width = 180
        overlay_x = hud_x_start + total_width // 2 - width // 2  # Centered above HUD
        overlay_y = hud_y - 80  # Above HUD
        box_color = (30, 30, 30)
        border_color = (255, 255, 255)
        border_radius = 8

        # --- Dropped weapons ---
        for weapon, pos in self.dropped_weapons:
            wx, wy = pos
            dist = math.hypot(px - wx, py - wy)
            if dist < pickup_radius:
                # Info to show (customize as needed)
                info_lines = []
                if hasattr(weapon, 'name'):
                    info_lines.append(str(weapon.name))
                if hasattr(weapon, 'damage'):
                    info_lines.append(f"Damage: {getattr(weapon, 'damage')}")
                if hasattr(weapon, 'type'):
                    info_lines.append(f"Type: {getattr(weapon, 'type')}")
                # Add more stats as needed

                height = 20 + 22 * len(info_lines)
                rect = pygame.Rect(overlay_x, overlay_y, width, height)
                pygame.draw.rect(surface, box_color, rect, border_radius=border_radius)
                pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)

                # Draw text
                for i, line in enumerate(info_lines):
                    text_surface = info_font.render(line, True, (255, 255, 255))
                    text_rect = text_surface.get_rect()
                    text_rect.topleft = (rect.x + 10, rect.y + 10 + i * 22)
                    surface.blit(text_surface, text_rect)

        # --- Pillar weapons and perks ---
        if room and hasattr(room, 'pillar_tiles'):
            interaction_radius = 32
            player_center = self.rect.center
            for pillar in room.pillar_tiles:
                dx = pillar.rect.centerx - player_center[0]
                dy = pillar.rect.centery - player_center[1]
                dist = (dx ** 2 + dy ** 2) ** 0.5
                # Overlay para armas
                if dist <= interaction_radius and hasattr(pillar, 'weapon') and pillar.weapon:
                    weapon = pillar.weapon
                    info_lines = []
                    if hasattr(weapon, 'name'):
                        info_lines.append(str(weapon.name))
                    if hasattr(weapon, 'damage'):
                        info_lines.append(f"Damage: {getattr(weapon, 'damage')}")
                    if hasattr(weapon, 'type'):
                        info_lines.append(f"Type: {getattr(weapon, 'type')}")
                    height = 20 + 22 * len(info_lines)
                    rect = pygame.Rect(overlay_x, overlay_y, width, height)
                    pygame.draw.rect(surface, box_color, rect, border_radius=border_radius)
                    pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)
                    for i, line in enumerate(info_lines):
                        text_surface = info_font.render(line, True, (255, 255, 255))
                        text_rect = text_surface.get_rect()
                        text_rect.topleft = (rect.x + 10, rect.y + 10 + i * 22)
                        surface.blit(text_surface, text_rect)
                # Overlay para perks
                if dist <= interaction_radius and hasattr(pillar, 'perk') and pillar.perk:
                    perk = pillar.perk
                    info_lines = [str(perk.name)]
                    height = 20 + 22 * len(info_lines)
                    rect = pygame.Rect(overlay_x, overlay_y, width, height)
                    pygame.draw.rect(surface, box_color, rect, border_radius=border_radius)
                    pygame.draw.rect(surface, border_color, rect, 2, border_radius=border_radius)
                    for i, line in enumerate(info_lines):
                        text_surface = info_font.render(line, True, (255, 255, 255))
                        text_rect = text_surface.get_rect()
                        text_rect.topleft = (rect.x + 10, rect.y + 10 + i * 22)
                        surface.blit(text_surface, text_rect)

    def drop_weapon(self):
        weapon = self.get_active_weapon()
        if weapon is not None:
            # Drop weapon above player
            drop_x = self.x + self.size // 2
            drop_y = self.y - self.size // 2
            self.dropped_weapons.append((weapon, (drop_x, drop_y)))
            self.weapons[self.active_weapon_index] = None

    def set_position(self, x, y):
        """Set player position directly"""
        self.x = x
        self.y = y
        self.rect.topleft = (x, y)

    def try_interact_with_pillars(self, rooms):
        interaction_radius = 32
        player_center = self.rect.center
        for room in rooms:
            for pillar in room.pillar_tiles:
                dx = pillar.rect.centerx - player_center[0]
                dy = pillar.rect.centery - player_center[1]
                dist = (dx ** 2 + dy ** 2) ** 0.5
                if dist <= interaction_radius:
                    # If pillar has a weapon, try to pick it up in the next available slot
                    if hasattr(pillar, 'weapon') and pillar.weapon:
                        empty_slot = None
                        for i, w in enumerate(self.weapons):
                            if w is None:
                                empty_slot = i
                                break
                        if empty_slot is not None:
                            self.weapons[empty_slot] = pillar.weapon
                            pillar.weapon = None
                        # else: all slots full, do nothing
                    else:
                        # Se for PerkPillar, passar o stardust_manager
                        from game.engine import stardust_manager
                        if hasattr(pillar, 'perk') and pillar.perk:
                            pillar.interact(self, stardust_manager=stardust_manager)
                        else:
                            pillar.interact(self)

    def attack(self, camera_x=0, camera_y=0, zoom=1.0, projectiles=None, enemies=None):
        weapon = self.get_active_weapon()
        if not weapon:
            return False
        angle = self.get_mouse_angle(camera_x, camera_y, zoom)
        player_center = (self.x, self.y)
        if isinstance(weapon, RangedWeapon):
            if projectiles is None:
                return False
            # Ranged weapons: let projectile handle damage, but agora passa o multiplicador de dano
            damage_multiplier = getattr(self, 'damage_multiplier', 1.0)
            return weapon.attack(player_center, angle, projectiles=projectiles, enemies=enemies, damage_multiplier=damage_multiplier)
        elif isinstance(weapon, MeleeWeapon):
            # Damage enemies in range and arc
            hit = False
            # --- Corrige para aplicar dano durante a fase 2 do swing ---
            if enemies:
                attack_range = getattr(weapon, 'attack_range', 80)
                attack_angle = angle
                arc_width = math.radians(70)  # 70 degree arc
                damage = getattr(weapon, 'damage', 10) * getattr(self, 'damage_multiplier', 1.0)
                # Adiciona controle para não atingir o mesmo inimigo mais de uma vez por swing
                if not hasattr(weapon, '_already_hit_enemies') or weapon.swing_phase == 0:
                    weapon._already_hit_enemies = set()
                for enemy in enemies:
                    dx = enemy.x + enemy.size/2 - player_center[0]
                    dy = enemy.y + enemy.size/2 - player_center[1]
                    dist = math.hypot(dx, dy)
                    if dist <= attack_range:
                        angle_to_enemy = math.atan2(dy, dx)
                        diff = abs((angle_to_enemy - attack_angle + math.pi) % (2*math.pi) - math.pi)
                        if diff < arc_width/2:
                            if hasattr(weapon, 'can_deal_damage') and weapon.can_deal_damage():
                                # Só aplica dano se ainda não atingiu esse inimigo nesse swing
                                if enemy not in weapon._already_hit_enemies:
                                    enemy.take_damage(damage)
                                    weapon.apply_effects(enemy)
                                    weapon._already_hit_enemies.add(enemy)
                                    hit = True
                # Limpa lista de inimigos atingidos ao terminar o swing
                if weapon.swing_phase == 0 and hasattr(weapon, '_already_hit_enemies'):
                    weapon._already_hit_enemies.clear()
            # O ataque só inicia o swing, o dano é processado acima
            return weapon.attack(player_center, angle, enemies=enemies, attack_held=self.attack_held) or hit
        return False

    def get_active_weapon(self):
        weapon = self.weapons[self.active_weapon_index] if 0 <= self.active_weapon_index < len(self.weapons) else None
        # Apply stored power-up effects to weapon if not already present
        if weapon and hasattr(self, 'stored_powerup_effects'):
            for effect in self.stored_powerup_effects:
                if effect and effect not in weapon.effects:
                    weapon.effects.append(effect)
                    print(f"[DEBUG][Player] Applied stored effect {effect} to weapon {weapon}")
        return weapon

    @property
    def weapon(self):
        # For backward compatibility
        return self.get_active_weapon()

    @weapon.setter
    def weapon(self, value):
        # Set weapon in current slot
        self.weapons[self.active_weapon_index] = value

    def try_pickup_weapon(self):
    # Pickup sound is preloaded at class level
        # Find the first empty slot
        empty_slot = None
        for i, w in enumerate(self.weapons):
            if w is None:
                empty_slot = i
                break
        if empty_slot is None:
            return False  # No empty slot available
        px = self.x + self.size // 2
        py = self.y + self.size // 2
        pickup_radius = max(32 * 2, self.size)
        for idx, (weapon, pos) in enumerate(self.dropped_weapons):
            wx, wy = pos
            dist = math.hypot(px - wx, py - wy)
            if dist < pickup_radius:
                self.weapons[empty_slot] = weapon
                del self.dropped_weapons[idx]
                # Play pickup sound
                if Player._pickup_sound:
                    try:
                        SoundManager.get_instance().play_sfx(Player._pickup_sound)
                    except Exception:
                        pass
                self.apply_effects_to_all_weapons()  # Ensure new weapon gets all effects
                return True
        return False

    def handle_input(self, rooms=None):
        if rooms is None:
            rooms = []

        keys = pygame.key.get_pressed()
        old_x, old_y = self.x, self.y
        new_x, new_y = self.x, self.y

        # Weapon switching (1, 2, 3)
        prev_weapon_index = self.active_weapon_index
        if keys[pygame.K_1]:
            self.active_weapon_index = 0
        elif keys[pygame.K_2]:
            self.active_weapon_index = 1
        elif keys[pygame.K_3]:
            self.active_weapon_index = 2
        # Play swap sound if weapon changed
        if self.active_weapon_index != prev_weapon_index:
            if Player._swap_weapon_sound:
                SoundManager.get_instance().play_sfx(Player._swap_weapon_sound)
            self.apply_effects_to_all_weapons()

        # Drop weapon (Q)
        if keys[pygame.K_q]:
            if not hasattr(self, '_q_pressed') or not self._q_pressed:
                self._q_pressed = True
                self.drop_weapon()
        else:
            self._q_pressed = False

        # Pick up weapon (E)
        if keys[pygame.K_e]:
            if not hasattr(self, '_e_pressed') or not self._e_pressed:
                self._e_pressed = True
                self.try_pickup_weapon()
        else:
            self._e_pressed = False

        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        moving = (keys[pygame.K_w] or keys[pygame.K_UP] or
                keys[pygame.K_s] or keys[pygame.K_DOWN] or
                keys[pygame.K_a] or keys[pygame.K_LEFT] or
                keys[pygame.K_d] or keys[pygame.K_RIGHT])
        
        if keys[pygame.K_e]:
            if not self.interact_key_pressed:
                self.interact_key_pressed = True
                self.try_interact_with_pillars(rooms)
        else:
            self.interact_key_pressed = False

        if sprinting and moving and self.stamina > 0:
            self.use_stamina(0.7)
            move_speed = self.speed
        else:
            move_speed = self.speed * 0.5

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            new_y -= move_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            new_y += move_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            new_x -= move_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            new_x += move_speed

        mouse_buttons = pygame.mouse.get_pressed()
        self.attack_held = mouse_buttons[0]  # True if left mouse button is held
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

        # --- Footprints logic ---
        moved_dist = math.hypot(self.x - self._last_footprint_pos[0], self.y - self._last_footprint_pos[1])
        if moved_dist > self._footprint_distance:
            # Alternate footprint side
            offset = self.size // 4
            # Determine movement direction (angle)
            dx = self.x - self._last_footprint_pos[0]
            dy = self.y - self._last_footprint_pos[1]
            angle = math.atan2(dy, dx) if dx != 0 or dy != 0 else 0
            # Perpendicular offset for left/right
            perp_angle = angle + (math.pi / 2 if self._footprint_side == "left" else -math.pi / 2)
            fp_x = int(self.x + self.size // 2 + math.cos(perp_angle) * offset)
            fp_y = int(self.y + self.size // 2 + math.sin(perp_angle) * offset)
            self.footprints.append((fp_x, fp_y, time.time(), self._footprint_side))
            self._last_footprint_pos = (self.x, self.y)
            self._footprint_side = "right" if self._footprint_side == "left" else "left"

    def get_mouse_angle(self, camera_x=0, camera_y=0, zoom=1.0):
        mouse_x, mouse_y = pygame.mouse.get_pos()

        # Convert mouse screen position to world coordinates
        world_mouse_x = (mouse_x / zoom) + camera_x
        world_mouse_y = (mouse_y / zoom) + camera_y

        player_center_x = self.x + self.size // 2
        player_center_y = self.y + self.size // 2

        dx = world_mouse_x - player_center_x
        dy = world_mouse_y - player_center_y

        angle = math.atan2(dy, dx)
        return angle  # in radians

    
    def _check_collision(self, player_rect, rooms):
        # First check against room bounding box
        for room in rooms:
            room_rect = pygame.Rect(room.x, room.y, room.width, room.height)
            if not room_rect.colliderect(player_rect):
                continue  # Skip rooms not near player

            # Only check walls close to the player
            nearby_walls = []
            for wall in room.get_wall_rects():
                # Check if wall is within a certain distance from the player
                # Use a margin (e.g., 64px) around the player
                margin = 64
                expanded_player_rect = player_rect.inflate(margin, margin)
                if expanded_player_rect.colliderect(wall):
                    nearby_walls.append(wall)

            for wall in nearby_walls:
                if player_rect.colliderect(wall):
                    return True
        return False
    
        # Example methods to modify attributes safely
    def take_damage(self, amount):
        if self.immunity_timer <= 0.0:
            self.health = max(0, self.health - amount)
            print(f"Player took {amount} damage! Current health: {self.health}")
            self.immunity_timer = self.immunity_duration
            if self._hit_sound:
                SoundManager.get_instance().play_sfx(self._hit_sound)
            if self.health <= 0:
                self.die()
        else:
            print("Player is immune to damage!")

    def restore_health(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def use_stamina(self, amount):
        self.stamina = max(0, self.stamina - amount)

    def restore_stamina(self, amount):
        self.stamina = min(self.max_stamina, self.stamina + amount)

    def _draw_vertical_bar_with_layers(self, surface, x, y, height, current, max_val,
                        base_color, mid_color, top_color,
                        invert=False, line_width=8, circle_radius=12, radius=4, label=None, font=None, value=None):
        
        fill_ratio = max(0.0, min(current / max(1, max_val), 1.0))

        # Clamp so the bar never fills the last 50px at the end (bottom for normal, top for inverted)
        min_bar_margin = 50
        if invert:
            # Inverted: fill from top to bottom (depletes from top)
            fill_height = int(height * fill_ratio)
            fill_height = max(0, fill_height - min_bar_margin)
            bar_top = y
        else:
            # Normal: fill from bottom to top (depletes from bottom)
            fill_height = int(height * fill_ratio)
            fill_height = min(fill_height, height - min_bar_margin)
            bar_top = y + (height - fill_height)

        # Center X for bar layers
        center_x = x + line_width // 2


        full_width = line_width

        # Draw the capsule ends ONCE for the whole bar, then draw each layer as a rect only
        pill_radius = full_width // 2
        # Only draw the capsule ends if the bar is tall enough
        if fill_height > 0:
            if fill_height <= full_width:
                # If the bar is very short, just draw an ellipse
                pygame.draw.ellipse(surface, base_color, (x, bar_top, full_width, fill_height))
            else:
                # Draw top and bottom circles (ends)
                pygame.draw.ellipse(surface, base_color, (x, bar_top, full_width, full_width))
                pygame.draw.ellipse(surface, base_color, (x, bar_top + fill_height - full_width, full_width, full_width))
                # Draw the center rect (between the circles)
                pygame.draw.rect(surface, base_color, (x, bar_top + pill_radius, full_width, fill_height - 2 * pill_radius))

        # Now draw the layers as rectangles only (no round ends)
        layer1_x = x
        layer1_width = int(full_width * 0.25)
        self._draw_bar_layer(surface,
            x=layer1_x,
            y=bar_top,
            width=layer1_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=base_color,
            radius=radius,
            draw_capsule_ends=False
        )

        layer2_x = x + int(full_width * 0.25)
        layer2_width = int(full_width * 0.5)
        self._draw_bar_layer(surface,
            x=layer2_x,
            y=bar_top,
            width=layer2_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=mid_color,
            radius=radius,
            draw_capsule_ends=False
        )

        layer3_x = x + int(full_width * 0.75)
        layer3_width = int(full_width * 0.25)
        self._draw_bar_layer(surface,
            x=layer3_x,
            y=bar_top,
            width=layer3_width,
            height=fill_height,
            current=current,
            max_val=max_val,
            color=top_color,
            radius=radius,
            draw_capsule_ends=False
        )




        # --- Draw horseshoe/arc using asset image (white) ---
        circle_x = center_x
        circle_y = y if invert else y + height
        arc_radius = circle_radius
        # Use cached horseshoe asset
        from game.assets import get_image
        horseshoe_img = get_image("horseshoe", "game/assets/sprites/ui/horseshoe.png")
        if horseshoe_img:
            # Cache horseshoe image by size and rotation
            cache_key = (arc_radius, invert)
            if cache_key not in Player._horseshoe_image_cache:
                scale_factor = (arc_radius * 2) / max(horseshoe_img.get_width(), horseshoe_img.get_height())
                new_size = (int(horseshoe_img.get_width() * scale_factor), int(horseshoe_img.get_height() * scale_factor))
                img = pygame.transform.smoothscale(horseshoe_img, new_size)
                if invert:
                    img = pygame.transform.rotate(img, 180)
                Player._horseshoe_image_cache[cache_key] = img
            horseshoe_img_cached = Player._horseshoe_image_cache[cache_key]
            img_rect = horseshoe_img_cached.get_rect(center=(circle_x, circle_y))
            surface.blit(horseshoe_img_cached, img_rect)
        else:
            # Fallback: draw a simple white circle if asset missing
            pygame.draw.circle(surface, (255,255,255), (circle_x, circle_y), arc_radius, 2)

        # --- Draw value/max and label to the right of the horseshoe ---
        if label and font and value is not None:
            # Value text (larger)
            value_font = font
            value_text = f"{int(value)}/{int(max_val)}"
            value_surface = value_font.render(value_text, True, (255, 255, 255))
            # Reserve space for the widest possible value text (e.g., '100/100')
            max_value_text = f"{int(max_val)}/{int(max_val)}"
            max_value_surface = value_font.render(max_value_text, True, (255, 255, 255))
            max_value_rect = max_value_surface.get_rect()
            value_rect = value_surface.get_rect()
            # Label text (smaller, but same custom font)
            from game.assets import get_font
            label_font = get_font("game/assets/fonts/CinzelDecorative-Black.ttf", max(12, font.get_height() // 2))
            label_surface = label_font.render(label, True, (255, 255, 255))
            label_rect = label_surface.get_rect()

            # Reserve a fixed area for the value text, so the label and value never move
            reserved_x = circle_x + arc_radius + 12
            reserved_y = circle_y
            # Center the reserved area vertically on the circle_y
            reserved_rect = pygame.Rect(0, 0, max_value_rect.width, max_value_rect.height)
            reserved_rect.midleft = (reserved_x, reserved_y)

            # Center the actual value_surface inside the reserved area
            value_rect.center = reserved_rect.center

            # Label positioning: always relative to the reserved area, not the value_rect
            if label.lower() == "health":
                # Label above reserved area
                label_rect.midbottom = (reserved_rect.centerx, reserved_rect.top - 2)
            elif label.lower() == "stamina":
                # Label below reserved area
                label_rect.midtop = (reserved_rect.centerx, reserved_rect.bottom + 2)
            else:
                # Default: to the right of reserved area
                label_rect.midleft = (reserved_rect.right + 8, reserved_rect.centery)

            surface.blit(value_surface, value_rect)
            surface.blit(label_surface, label_rect)




    def _draw_bar_layer(self, surface, x, y, width, height, current, max_val, color, radius=5, draw_capsule_ends=False):
        # Make sure width/height are valid
        width = max(1, int(width))
        height = max(1, int(height))

        x = int(x)
        y = int(y)

        # Draw as a rectangle with rounded ends (capsule shape)
        # Use border_radius to make the ends round
        border_radius = min(width, height) // 2 if width > 1 and height > 1 else 0
        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=border_radius)

    def render_bars(self, surface, screen_height):
        bar_x = 20
        bar_y = 20
        bar_height = screen_height - 40

        white = (255, 255, 255)
        base = (255, 255, 255)
        mid = (255, 255, 255)
        top = (255, 255, 255)

        # Use cached custom font
        from game.assets import FONTS, get_font
        custom_font = FONTS["bar"]

        self._draw_vertical_bar_with_layers(
            surface, bar_x, bar_y, bar_height,
            current=self.display_health,
            max_val=self.max_health,
            base_color=base,
            mid_color=mid,
            top_color=top,
            invert=False,
            label="Health",
            font=custom_font,
            value=self.display_health
        )

        # STAMINA (top, inverted)
        self._draw_vertical_bar_with_layers(
            surface, bar_x + 30, bar_y, bar_height,
            current=self.display_stamina,
            max_val=self.max_stamina,
            base_color=base,
            mid_color=mid,
            top_color=top,
            invert=True,
            label="Stamina",
            font=custom_font,
            value=self.display_stamina
        )

        # Stardust Counter UI below the minimap, centered horizontally to the minimap
        try:
            from game.engine import stardust_manager
            stardust_value = stardust_manager.stardust
        except Exception:
            stardust_value = 0
        stardust_font = get_font("game/assets/fonts/CinzelDecorative-Regular.ttf", 28)
        stardust_text = f"{stardust_value}"
        text_surface = stardust_font.render(stardust_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect()
        # Get minimap position from dungeon.py
        map_size = 150
        map_margin = 20
        map_x = surface.get_width() - map_size - map_margin
        map_y = map_margin
        # Position Stardust below minimap, centered horizontally
        circle_radius = 6
        spacing = 8
        center_x = map_x + map_size // 2
        stardust_y = map_y + map_size + spacing + text_rect.height // 2
        # Center text horizontally to minimap
        text_rect.centerx = center_x + circle_radius // 2
        text_rect.centery = stardust_y
        # Circle to the left of the number, centered vertically
        circle_x = text_rect.left - spacing - circle_radius
        circle_y = text_rect.centery
        surface.blit(text_surface, text_rect)
        pygame.draw.circle(surface, (255, 255, 255), (circle_x, circle_y), circle_radius)


    def update(self, rooms=None, dt=0.016, enemies=None ):
        self.handle_input(rooms)
        # Update immunity timer
        if self.immunity_timer > 0.0:
            self.immunity_timer -= dt
            if self.immunity_timer < 0.0:
                self.immunity_timer = 0.0

        # Regenerate stamina if not sprinting or moving
        keys = pygame.key.get_pressed()
        is_moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d] or \
                    keys[pygame.K_UP] or keys[pygame.K_DOWN] or keys[pygame.K_LEFT] or keys[pygame.K_RIGHT]
        sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if not (sprinting and is_moving):
            self.restore_stamina(0.5)  # só regenera se não estiver sprintando *e* se movendo

        def safe_lerp(current, target, speed, dt):
            delta = (target - current) * speed * dt
            if not (isinstance(delta, float) and (delta != delta or delta == float('inf') or delta == float('-inf'))):
                # Snap to target if very close to avoid visual "stall"
                if abs(target - current) < 0.5:
                    return target
                return current + delta
            return target

        speed = 10

        self.display_health = safe_lerp(self.display_health, self.health, speed, dt)

        # Clamp stamina between 0 and max_stamina
        self.stamina = max(0, min(self.stamina, self.max_stamina))

        # If stamina is at boundaries, sync display immediately, else interpolate
        if self.stamina <= 0:
            self.display_stamina = 0
        elif self.stamina >= self.max_stamina:
            self.display_stamina = self.max_stamina
        else:
            self.display_stamina = safe_lerp(self.display_stamina, self.stamina, speed, dt)

        # Swing logic now handled by weapon
        weapon = self.get_active_weapon()

        # Weapon handles damage/effects application itself using _already_hit_enemies logic
        if weapon and hasattr(weapon, 'update'):
            weapon.update(dt, enemies=enemies, attack_held=self.attack_held)

        # Atualiza bob dos olhos
        self.eye_bob_timer += dt
        if self.eye_bob_timer > 1.0 / self.eye_bob_speed:
            self.eye_bob_timer -= 1.0 / self.eye_bob_speed

        # Atualiza piscar
        self.blink_timer += dt
        if not self.is_blinking and self.blink_timer >= self.blink_interval:
            self.is_blinking = True
            self.blink_timer = 0.0
        elif self.is_blinking and self.blink_timer >= self.blink_duration:
            self.is_blinking = False
            self.blink_timer = 0.0

    # Death animation support: fade out and shrink
    def render(self, surface, camera_x=0, camera_y=0, rooms=None, zoom=1.0, show_collision_rects=False, dt=0.016):
                # Check if we should draw death animation instead of normal player
        if hasattr(self, 'is_dead') and self.is_dead:
            self.draw_death_animation(surface, camera_x, camera_y)
            return  # Always skip normal drawing when dead
        # Death animation: fade out and shrink
        death_t = getattr(self, '_death_anim_progress', None)
        fade_alpha = 255
        shrink_scale = 1.0
        if death_t is not None:
            fade_alpha = int(255 * (1.0 - death_t))
            shrink_scale = max(0.2, 1.0 - 0.7 * death_t)

        from game.util.light import create_soft_player_light
        # Calculate render position with camera offset
        render_x = self.x - camera_x
        render_y = self.y - camera_y

        # Get room walls for light collision
        wall_rects = []
        if rooms:
            for room in rooms:
                if not hasattr(room, 'get_wall_rects'):
                    continue
                for wall in room.get_wall_rects():
                    screen_wall = pygame.Rect(
                        wall.x - camera_x,
                        wall.y - camera_y,
                        wall.width,
                        wall.height
                    )
                    wall_rects.append(screen_wall)
            # Performance: limit walls for lighting
            if len(wall_rects) > 150:
                player_center_x = render_x + self.size // 2
                player_center_y = render_y + self.size // 2
                walls_with_distance = [
                    ((wall.x + wall.width // 2 - player_center_x) ** 2 + (wall.y + wall.height // 2 - player_center_y) ** 2, wall)
                    for wall in wall_rects
                ]
                walls_with_distance.sort(key=lambda x: x[0])
                wall_rects = [wall for _, wall in walls_with_distance[:100]]

        # Render soft light around player
        create_soft_player_light(
            surface,
            render_x + self.size // 2,
            render_y + self.size // 2,
            radius=100,
            wall_rects=wall_rects
        )

        # --- Render player shadow ---
        shadow_width = int(self.size * 0.9 * shrink_scale)
        shadow_height = int(self.size * 0.4 * shrink_scale)
        shadow_x = render_x + (self.size * shrink_scale - shadow_width) // 2
        shadow_y = render_y + self.size * shrink_scale - shadow_height // 2
        shadow_alpha = int(80 * (fade_alpha / 255))
        shadow_key = (shadow_width, shadow_height, shadow_alpha)
        if shadow_key not in Player._shadow_surface_cache:
            shadow_surf = pygame.Surface((shadow_width, shadow_height), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, shadow_width, shadow_height))
            Player._shadow_surface_cache[shadow_key] = shadow_surf
        else:
            shadow_surf = Player._shadow_surface_cache[shadow_key]
        surface.blit(shadow_surf, (shadow_x, shadow_y))

        # --- Render footprints ---
        footprint_color = (200, 200, 200)
        footprint_radius = max(2, self.size // 6)
        max_footprints = 60
        fade_time = 1.0  # seconds before footprint fades
        now = time.time()
        # Only keep recent footprints
        self.footprints = [fp for fp in self.footprints if now - fp[2] < fade_time]
        for fp_x, fp_y, fp_time, fp_side in self.footprints[-max_footprints:]:
            alpha = max(0, 255 - int((now - fp_time) / fade_time * 255))
            cache_key = (footprint_radius, alpha, fp_side)
            if cache_key not in Player._footprint_surface_cache:
                footprint_surf = pygame.Surface((footprint_radius*2, footprint_radius*2), pygame.SRCALPHA)
                pygame.draw.ellipse(
                    footprint_surf,
                    (*footprint_color, alpha),
                    (0, footprint_radius//2, footprint_radius*2, footprint_radius)
                )
                if fp_side == "right":
                    footprint_surf = pygame.transform.flip(footprint_surf, True, False)
                Player._footprint_surface_cache[cache_key] = footprint_surf
            else:
                footprint_surf = Player._footprint_surface_cache[cache_key]
            surface.blit(footprint_surf, (fp_x - footprint_radius - camera_x, fp_y - footprint_radius - camera_y))

        # --- Get mouse position once ---
        mouse_screen_x, mouse_screen_y = pygame.mouse.get_pos()
        mouse_virtual_x = mouse_screen_x / zoom
        mouse_virtual_y = mouse_screen_y / zoom
        world_mouse_x = mouse_virtual_x + camera_x
        world_mouse_y = mouse_virtual_y + camera_y

        player_center_x = self.x + self.size // 2
        player_center_y = self.y + self.size // 2
        player_center = (player_center_x, player_center_y)

        # Weapon rendering delegated to weapon class
        weapon = self.get_active_weapon()
        if weapon and hasattr(weapon, 'render'):
            angle = self.get_mouse_angle(camera_x, camera_y, zoom)
            # Pass dt to weapon.render if it accepts it
            try:
                weapon.render(surface, player_center, angle, camera_x, camera_y, zoom, dt=dt)
            except TypeError:
                weapon.render(surface, player_center, angle, camera_x, camera_y, zoom)

        # Render dropped weapons above player at correct size
        dropped_weapon_size = 32  # or use self.size if you want player size
        for dropped_weapon, pos in self.dropped_weapons:
            if hasattr(dropped_weapon, 'render_static'):
                # Pass the intended size for dropped weapons
                try:
                    dropped_weapon.render_static(surface, (pos[0] - camera_x, pos[1] - camera_y), camera_x, camera_y, zoom, size=dropped_weapon_size)
                except TypeError:
                    # Fallback for older render_static signatures
                    dropped_weapon.render_static(surface, (pos[0] - camera_x, pos[1] - camera_y), camera_x, camera_y, zoom)

        # --- pega posição do mouse no mundo ---
        mouse_virtual_x_world = mouse_screen_x / zoom + camera_x
        mouse_virtual_y_world = mouse_screen_y / zoom + camera_y

        dx = mouse_virtual_x_world - player_center_x

        eye_offset = 2
        if dx > 5:
            eye_shift = eye_offset
        elif dx < -5:
            eye_shift = -eye_offset
        else:
            eye_shift = 0

        render_x = self.x - camera_x
        render_y = self.y - camera_y

        # --- bob timer já atualizado no update(dt), aqui só calcula o offset ---
        eye_bob_offset = (self.eye_bob_amplitude + 3) * math.sin(self.eye_bob_timer * 2 * math.pi * (self.eye_bob_speed + 0.5))

        # Corpo: encolhe a altura baseado no bob e na animação de morte
        new_height = int(self.size * shrink_scale - abs(eye_bob_offset) * 0.5 * shrink_scale)
        new_width = int(self.size * shrink_scale + abs(eye_bob_offset) * 0.5 * 2 * shrink_scale)

        base_y = render_y + self.size * shrink_scale
        new_y = base_y - new_height

        base_x = render_x + self.size * shrink_scale / 2
        new_x = base_x - new_width / 2

        player_rect = pygame.Rect(new_x, new_y, new_width, new_height)
        player_key = (new_width, new_height, tuple(self.color), fade_alpha)
        if player_key not in Player._player_surface_cache:
            player_surf = pygame.Surface((new_width, new_height), pygame.SRCALPHA)
            player_surf.fill((*self.color, fade_alpha))
            Player._player_surface_cache[player_key] = player_surf
        else:
            player_surf = Player._player_surface_cache[player_key]
        surface.blit(player_surf, player_rect)

        # Olhos
        eye_size = 2
        eye_y_base = render_y + 5 * shrink_scale
        eye_y = eye_y_base
        left_eye_x = render_x + 5 * shrink_scale + eye_shift
        right_eye_x = render_x + self.size * shrink_scale - 5 * shrink_scale - eye_size + eye_shift
        if self.is_blinking:
            eye_height = 0
        else:
            eye_height = int(2 * shrink_scale)
        eye_alpha = fade_alpha
        eye_color = (0, 0, 0, eye_alpha)
        eye_surf = pygame.Surface((eye_size, eye_height), pygame.SRCALPHA)
        eye_surf.fill(eye_color)
        surface.blit(eye_surf, (left_eye_x, eye_y))
        surface.blit(eye_surf, (right_eye_x, eye_y))

    def die(self):
        # Play player death sound
        if Player._die_sound:
            SoundManager.get_instance().play_sfx(Player._die_sound)
        # Death animation: pixel explosion
        self.is_dead = True
        self.death_timer = 0.0
        self.death_duration = 0.5  # total animation time
        self.death_chunks = []
        n_chunks = 6
        base_color = tuple(max(0, int(c * 0.8)) for c in self.color)
        center_x = self.x + self.size // 2
        center_y = self.y + self.size // 2
        for i in range(n_chunks):
            angle = 2 * math.pi * i / n_chunks + random.uniform(-0.2, 0.2)
            speed = random.uniform(5, 11)
            chunk_size = self.size // 3
            chunk_x = center_x - chunk_size // 2
            chunk_y = center_y - chunk_size // 2
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            self.death_chunks.append({
                'x': chunk_x,
                'y': chunk_y,
                'dx': dx,
                'dy': dy,
                'size': chunk_size,
                'color': base_color,
                'alpha': 255,
                'timer': 0.0
            })
        # Trigger game over screen
        if hasattr(self, 'engine') and hasattr(self.engine, 'show_game_over_screen'):
            self.engine.show_game_over_screen()
        else:
            print("Game Over!")

    def update_death_animation(self, dt):
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer'):
            self.death_timer += dt
            if hasattr(self, 'death_chunks'):
                for chunk in self.death_chunks:
                    chunk['x'] += chunk['dx'] * dt * 60
                    chunk['y'] += chunk['dy'] * dt * 60
                    chunk['timer'] += dt
                    # Fade out
                    chunk['alpha'] = max(0, 255 - int((chunk['timer'] / self.death_duration) * 255))
            if self.death_timer >= self.death_duration:
                self.death_timer = self.death_duration
                # Optionally, remove player or freeze input

    def draw_death_animation(self, surface, camera_x=0, camera_y=0):
        if getattr(self, 'is_dead', False) and hasattr(self, 'death_timer') and hasattr(self, 'death_chunks'):
            for chunk in self.death_chunks:
                cache_key = (chunk['size'], tuple(chunk['color']), chunk['alpha'])
                if cache_key not in Player._death_chunk_surface_cache:
                    chunk_surf = pygame.Surface((chunk['size'], chunk['size']), pygame.SRCALPHA)
                    pygame.draw.rect(chunk_surf, (*chunk['color'], chunk['alpha']), (0, 0, chunk['size'], chunk['size']))
                    Player._death_chunk_surface_cache[cache_key] = chunk_surf
                else:
                    chunk_surf = Player._death_chunk_surface_cache[cache_key]
                draw_x = int(chunk['x'] - camera_x)
                draw_y = int(chunk['y'] - camera_y)
                surface.blit(chunk_surf, (draw_x, draw_y))
            return True
        return False
    def apply_effects_to_all_weapons(self):
        """
        Apply all stored powerup effect types to every weapon in the player's inventory.
        Ensures no duplicate effect types are added and updates effect parameters if tier changes.
        """
        if not hasattr(self, 'stored_powerup_effects'):
            self.stored_powerup_effects = set()
        for weapon in self.weapons:
            if weapon is not None:
                print(f"[DEBUG][Player] Weapon {weapon} has effects: {weapon.effects}")
                print(f"[DEBUG][Player] Checking stored effect types {self.stored_powerup_effects}")
                for effect_type in self.stored_powerup_effects:
                    found = False
                    for e in weapon.effects:
                        if isinstance(e, effect_type):
                            found = True
                            # Update effect parameters if possible
                            if effect_type.__name__ == 'PoisonEffect':
                                if hasattr(e, 'level'):
                                    e.level = self.get_powerup_tier('Poison')
                                if hasattr(e, 'damage_per_tick'):
                                    e.damage_per_tick = 2
                                if hasattr(e, 'tick_interval'):
                                    e.tick_interval = 1.0
                                if hasattr(e, 'duration'):
                                    e.duration = 3.0
                            elif effect_type.__name__ == 'FireEffect':
                                if hasattr(e, 'level'):
                                    e.level = self.get_powerup_tier('Fire')
                                if hasattr(e, 'damage_per_tick'):
                                    e.damage_per_tick = 3
                                if hasattr(e, 'tick_interval'):
                                    e.tick_interval = 1.0
                                if hasattr(e, 'duration'):
                                    e.duration = 2.0
                            # Add more effect types here as needed
                            print(f"[DEBUG][Player] Updated effect {e} on weapon {weapon}")
                    if not found:
                        # Create new effect instance
                        if effect_type.__name__ == 'PoisonEffect':
                            effect_instance = effect_type(
                                damage_per_tick=2,
                                tick_interval=1.0,
                                duration=3.0,
                                level=self.get_powerup_tier('Poison') if hasattr(self, 'get_powerup_tier') else 1
                            )
                        elif effect_type.__name__ == 'FireEffect':
                            effect_instance = effect_type(
                                damage_per_tick=3,
                                tick_interval=1.0,
                                duration=2.0,
                                level=self.get_powerup_tier('Fire') if hasattr(self, 'get_powerup_tier') else 1
                            )
                        else:
                            effect_instance = effect_type()
                        weapon.effects.append(effect_instance)
                        print(f"[DEBUG][Player] Applied stored effect {effect_instance} to weapon {weapon}")

    def update_powerup_effects(self, dt, mouse_pos, enemies):
        """
        Call fire tier 1 effect (Ignition) every interval with latest mouse_pos and enemies.
        Call this from your game loop.
        """
        if self.get_powerup_tier('Fire') >= 1:
            self._fire_powerup_timer += dt
            if self._fire_powerup_timer >= self._fire_powerup_interval:
                self._fire_powerup_timer = 0.0
                for effect_func in self.active_powerup_effects:
                    if getattr(effect_func, '__name__', '') == 'ignition_effect':
                        effect_func(self, mouse_pos, enemies)
                        break
