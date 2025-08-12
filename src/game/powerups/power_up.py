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

    def apply(self, player):
        print(f"[DEBUG] PowerUp: Applying effect for '{self.name}' to player.")
        self.effect_func(player)
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

# Example usage:
def poison_effect(player):
    from game.effects import PoisonEffect
    for weapon in getattr(player, 'weapons', []):
        if weapon:
            if not hasattr(weapon, 'effects'):
                weapon.effects = []
            # Only add if not already present
            if not any(isinstance(e, PoisonEffect) for e in weapon.effects):
                poison = PoisonEffect(
                    damage_per_tick=2,
                    tick_interval=1.0,
                    duration=3.0,
                    level=player.get_powerup_tier('Poison') if hasattr(player, 'get_powerup_tier') else 1
                )
                weapon.effects.append(poison)
                print(f"[DEBUG] Weapon: Added PoisonEffect to weapon {weapon}. Effects: {weapon.effects}")
poison1 = PowerUp('Poison Shot', 'Every 2 shots apply poison.', poison_effect, 'Poison', 1)
poison2 = PowerUp('Toxic Barrage', 'Every shot applies poison.', poison_effect, 'Poison', 2)
tree = PowerUpTree('Poison')
tree.add_powerup(poison1)
tree.add_powerup(poison2)
