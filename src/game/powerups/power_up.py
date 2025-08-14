# --- Fire Power-Up Effects ---
import random
from game.effects import IgniteEffect


import random
from game.effects import PoisonEffect, SlowEffect

class PowerUp:
    """
    Represents a single power-up in the game.
    """
    def __init__(self, name, description, effect_func, theme, tier):
        self.name = name
        self.description = description
        self.effect_func = effect_func  # Function to apply the effect
        self.theme = theme  # e.g., 'Poison', 'Fire', etc.
        self.tier = tier  # 1-5, position in the tree
        self.next_powerup = None  # Link to next power-up in the tree

    def apply(self, player, *args, **kwargs):
        print(f"[DEBUG] PowerUp: Applying effect for '{self.name}' to player.")
        self.effect_func(player, *args, **kwargs)
        print(f"[DEBUG] PowerUp: Effect for '{self.name}' executed.")

class PowerUpTree:

    """
    Represents a tree of power-ups for a specific theme.
    """
    def __init__(self, theme):
        self.theme = theme
        self.powerups = []  # List of PowerUp objects, ordered by tier

    def add_powerup(self, powerup):
        """Add a power-up to the tree, linking it to the previous one."""
        if self.powerups:
            self.powerups[-1].next_powerup = powerup
        self.powerups.append(powerup)

    def get_available_powerups(self, current_tier):
        """Return the next available power-ups for selection (by tier)."""
        return [p for p in self.powerups if p.tier == current_tier + 1]

    def get_powerup_by_tier(self, tier):
        for p in self.powerups:
            if p.tier == tier:
                return p
        return None
    
def ignition_effect(player):
    """Tier 1: Weapon hits have a chance to ignite enemies."""
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous ignite_chance effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'ignite_chance']
            def ignite_chance(enemy):
                # Only add IgniteEffect if not already present
                if not any(isinstance(e, IgniteEffect) for e in getattr(enemy, 'effects', [])):
                    ignite = IgniteEffect(
                        damage_per_tick=1,
                        tick_interval=1.0,
                        duration=3.0,
                        vulnerability=1.0,
                        level=1
                    )
                    enemy.add_effect(ignite)
                    print(f"[DEBUG] Ignition: Ignited {enemy} by weapon hit.")
            ignite_chance._effect_type = 'ignite_chance'
            weapon.effects.append(ignite_chance)
            print(f"[DEBUG] Weapon: Added IgniteEffect (1/1 chance) to weapon {weapon}.")

def burning_vulnerability_effect(player):
    """Tier 2: Ignited enemies take 1 damage/sec and 1.5x damage from all sources."""
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous burning_vulnerability effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'burning_vulnerability']
            def apply_burning_vulnerability(enemy):
                updated = False
                for effect in getattr(enemy, 'effects', []):
                    if isinstance(effect, IgniteEffect):
                            effect.vulnerability = 1.5
                            effect.apply(enemy)  # Ensure fire_vulnerability is updated
                            updated = True
                            print(f"[DEBUG] Burning Vulnerability: Updated vulnerability to 1.5 for {enemy}")
                if not updated:
                    ignite = IgniteEffect(
                        damage_per_tick=1,
                        tick_interval=1.0,
                        duration=3.0,
                        vulnerability=1.5,
                        level=2
                    )
                    enemy.add_effect(ignite)
                    print(f"[DEBUG] Ignition: Ignited {enemy} by weapon hit.")
            apply_burning_vulnerability._effect_type = 'burning_vulnerability'
            weapon.effects.append(apply_burning_vulnerability)
            print(f"[DEBUG] Weapon: Added Burning Vulnerability effect to weapon {weapon}.")
            # ...existing code...

    # Already handled by IgniteEffect
    pass

def spreading_flames_effect(player):
    """Tier 3: Ignited enemies spread ignite to nearby enemies."""
    # Set the default spread radius for all future IgniteEffects
    from game.effects import IgniteEffect
    IgniteEffect.default_spread_radius = 200
    # Optionally, update existing IgniteEffects on all enemies in current room
    # If player.current_room and enemies are accessible:
    current_room = getattr(player, 'current_room', None)
    if current_room and hasattr(current_room, 'enemies'):
        for enemy in current_room.enemies:
            for effect in getattr(enemy, 'effects', []):
                if isinstance(effect, IgniteEffect):
                    effect.spread_radius = 200
                    print(f"[DEBUG] SpreadingFlames: {enemy} can now spread flames.")

def inferno_weakness_effect(player):
    """Tier 4: Ignited enemies take 3x damage from all sources."""
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous inferno_weakness effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'inferno_weakness']
            def apply_burning_vulnerability(enemy):
                updated = False
                for effect in getattr(enemy, 'effects', []):
                    if isinstance(effect, IgniteEffect):
                            effect.vulnerability = 3.0
                            effect.apply(enemy)  # Ensure fire_vulnerability is updated
                            updated = True
                            print(f"[DEBUG] Burning Vulnerability: Updated vulnerability to 3.0 for {enemy}")
                if not updated:
                    ignite = IgniteEffect(
                        damage_per_tick=1,
                        tick_interval=1.0,
                        duration=3.0,
                        vulnerability=3.0,
                        level=4
                    )
                    enemy.add_effect(ignite)
                    print(f"[DEBUG] Ignition: Ignited {enemy} by weapon hit.")
            apply_burning_vulnerability._effect_type = 'inferno_weakness'
            weapon.effects.append(apply_burning_vulnerability)
            print(f"[DEBUG] Weapon: Added Burning Vulnerability effect to weapon {weapon}.")

def explosion_catalyst_effect(player):
    """Tier 5: 1/4 chance to instantly kill an enemy on hit."""
    import random
    for weapon in getattr(player, 'weapons', []):
        if weapon and hasattr(weapon, 'effects'):
            # Remove previous explosion_catalyst effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'explosion_catalyst']
            def instant_kill_chance(enemy, damage_dealt=0):
                if random.randint(1, 4) == 1:
                    enemy.take_damage(2147483647)  # Insta-kill by dealing max 32-bit signed int damage
                    print(f"[DEBUG] ExplosionCatalyst: {enemy} instantly killed!")
            instant_kill_chance._effect_type = 'explosion_catalyst'
            weapon.effects.append(instant_kill_chance)

# Fire Power-Up Tree
fire1 = PowerUp('Ignition', 'Weapon hits have a chance to ignite enemies.', ignition_effect, 'Fire', 1)
fire2 = PowerUp('Burning Vulnerability', 'Ignited enemies take 1 damage/sec and 1.5x damage from all sources.', burning_vulnerability_effect, 'Fire', 2)
fire3 = PowerUp('Spreading Flames', 'Ignited enemies spread ignite to nearby enemies.', spreading_flames_effect, 'Fire', 3)
fire4 = PowerUp('Inferno Weakness', 'Ignited enemies take 3x damage from all sources.', inferno_weakness_effect, 'Fire', 4)
fire5 = PowerUp('Explosion Catalyst', '1/4 chance to instantly kill an enemy on hit. Triggers Volatile Reaction', explosion_catalyst_effect, 'Fire', 5)
fire_tree = PowerUpTree('Fire')
fire_tree.add_powerup(fire1)
fire_tree.add_powerup(fire2)
fire_tree.add_powerup(fire3)
fire_tree.add_powerup(fire4)
fire_tree.add_powerup(fire5)

# Poison Power-Up Effects
def poison_effect(player):
    """Tier 1: Every shot applies poison."""
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous poison_effect effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'poison_effect']
            def poison_chance(enemy):
                if random.randint(1, 4) == 1:
                    poison = PoisonEffect(
                        damage_per_tick=2,
                        tick_interval=1.0,
                        duration=3.0,
                        level=1
                    )
                    enemy.add_effect(poison)
            poison_chance._effect_type = 'poison_effect'
            weapon.effects.append(poison_chance)
            print(f"[DEBUG] Weapon: Added PoisonEffect (1/4 chance) to weapon {weapon}.")

def toxic_barrage_effect(player):
    """Tier 2: Poison ticks faster (reduced tick interval)."""
    import random
    from game.effects import PoisonEffect
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous toxic_barrage effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'toxic_barrage']
            def poison_chance(enemy):
                if random.randint(1, 4) == 1:
                    poison = PoisonEffect(
                        damage_per_tick=2,
                        tick_interval=0.5,
                        duration=3.0,
                        level=2
                    )
                    enemy.add_effect(poison)
            poison_chance._effect_type = 'toxic_barrage'
            weapon.effects.append(poison_chance)
            print(f"[DEBUG] Weapon: Added Toxic Barrage PoisonEffect (1/4 chance) to weapon {weapon}.")

def lingering_toxins_effect(player):
    """Tier 3: Poison lasts longer (increased duration)."""
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous lingering_toxins effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'lingering_toxins']
            def poison_chance(enemy):
                if random.randint(1, 3) == 1:
                    poison = PoisonEffect(
                        damage_per_tick=4,
                        tick_interval=0.5,
                        duration=6.0,
                        level=3
                    )
                    enemy.add_effect(poison)
            poison_chance._effect_type = 'lingering_toxins'
            weapon.effects.append(poison_chance)
            print(f"[DEBUG] Weapon: Added Lingering Toxins PoisonEffect (1/3 chance) to weapon {weapon}.")

def paralyzing_venom_effect(player):
    """Tier 4: Poisoned enemies have reduced movement speed."""
    import random
    from game.effects import PoisonEffect, SlowEffect
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous paralyzing_venom effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'paralyzing_venom']
            def poison_and_slow(enemy):
                if random.randint(1, 3) == 1:
                    poison = PoisonEffect(
                        damage_per_tick=4,
                        tick_interval=0.5,
                        duration=6.0,
                        level=4
                    )
                    slow = SlowEffect(duration=6.0, speed_multiplier=0.2, level=1)
                    enemy.add_effect(poison)
                    enemy.add_effect(slow)
            poison_and_slow._effect_type = 'paralyzing_venom'
            weapon.effects.append(poison_and_slow)
            print(f"[DEBUG] Weapon: Added Paralyzing Venom PoisonEffect and SlowEffect (1/3 chance) to weapon {weapon}.")

def volatile_reaction_effect(player):
    """Tier 5: Se explosion_catalyst_effect para ativado em um inimigo envenenado, espalha PoisonEffect para inimigos próximos."""
    from game.effects import PoisonEffect
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Remove previous volatile_reaction effects
            weapon.effects = [e for e in weapon.effects if getattr(e, '_effect_type', None) != 'volatile_reaction']
            import random
            def spread_toxin_on_explosion(enemy, damage_dealt=0):
                print("[DEBUG] spread_toxin_on_explosion called")  # Adicione este print para testar
                if damage_dealt >= 2147483647 or getattr(enemy, 'is_dead', False):
                    print("[DEBUG] explosion_catalyst_effect triggered")  # Outro print para garantir
                    # Remova a condição de random para testar
                    current_room = getattr(player, 'current_room', None)
                    if current_room and hasattr(current_room, 'enemies'):
                        for other_enemy in current_room.enemies:
                            if other_enemy != enemy:
                                poison = PoisonEffect(
                                    damage_per_tick=4,
                                    tick_interval=0.5,
                                    duration=6.0,
                                    level=5
                                )
                                other_enemy.add_effect(poison)
                                print(f"[DEBUG] ToxicSpread: {other_enemy} foi envenenado pela explosão de {enemy}.")
            spread_toxin_on_explosion._effect_type = 'volatile_reaction'
            weapon.effects.append(spread_toxin_on_explosion)
            print(f"[DEBUG] Weapon: Adicionado efeito de espalhamento de toxina na explosão para {weapon}.")

# Power-up tree
poison1 = PowerUp('Poison Shot', 'Every shot has a chance to apply poison.', poison_effect, 'Poison', 1)
poison2 = PowerUp('Toxic Barrage', 'Poison ticks faster.', toxic_barrage_effect, 'Poison', 2)
poison3 = PowerUp('Lingering Toxins', 'Poison lasts longer and deal double damage.', lingering_toxins_effect, 'Poison', 3)
poison4 = PowerUp('Paralyzing Venom', 'Poisoned enemies have reduced movement speed.', paralyzing_venom_effect, 'Poison', 4)
poison5 = PowerUp('Volatile Reaction', 'Poisoned enemies hit by fire create a gas explosion, damaging nearby enemies.', volatile_reaction_effect, 'Poison', 5)
tree = PowerUpTree('Poison')
tree.add_powerup(poison1)
tree.add_powerup(poison2)
tree.add_powerup(poison3)
tree.add_powerup(poison4)
tree.add_powerup(poison5)
