import time

class Effect:
    """Base class for all effects."""
    def __init__(self, duration=1.0, level=1):
        self.duration = duration
        self.level = level
        self.start_time = time.time()
        self.active = True

    def apply(self, target):
        """Apply the effect to the target."""
        print(f"[DEBUG][Effect] Applying {self.__class__.__name__} to {target}")
        pass

    def update(self, target):
        """Update the effect (called every frame/tick)."""
        pass

    def is_expired(self):
        return (time.time() - self.start_time) > self.duration

class DamageEffect(Effect):
    """Base class for damage-dealing effects."""
    def __init__(self, damage_per_tick=1, tick_interval=1.0, duration=3.0, level=1):
        super().__init__(duration=duration, level=level)
        self.damage_per_tick = damage_per_tick
        self.tick_interval = tick_interval
        self.last_tick = time.time()

    def update(self, target):
        now = time.time()
        print(f"[DEBUG][Effect] Updating {self.__class__.__name__} for {target}")
        if now - self.last_tick >= self.tick_interval and self.active:
            print(f"[DEBUG][Effect] {self.__class__.__name__} tick: dealing damage to {target}")
            self.last_tick = now
            self.deal_damage(target)
        if self.is_expired():
            print(f"[DEBUG][Effect] {self.__class__.__name__} expired for {target}")
            self.active = False

    def deal_damage(self, target):
        if hasattr(target, 'take_damage'):
            # Color override for subclasses
            color = None
            if self.__class__.__name__ == 'PoisonEffect':
                color = (160, 32, 240)  # purple
            elif self.__class__.__name__ == 'IgniteEffect':
                color = (255, 140, 0)  # orange
            if color:
                target.damage_color_override = color
            print(f"[DEBUG][Effect] {self.__class__.__name__} is dealing {self.damage_per_tick} damage to {target}")
            target.take_damage(self.damage_per_tick)
            if color:
                target.damage_color_override = None
            print(f"[Effect] {self.__class__.__name__} dealt {self.damage_per_tick} damage to {target}")

class HealingEffect(Effect):
    """Base class for healing effects."""
    def __init__(self, heal_per_tick=1, tick_interval=1.0, duration=3.0, level=1):
        super().__init__(duration=duration, level=level)
        self.heal_per_tick = heal_per_tick
        self.tick_interval = tick_interval
        self.last_tick = time.time()

    def update(self, target):
        now = time.time()
        if now - self.last_tick >= self.tick_interval and self.active:
            self.last_tick = now
            self.heal(target)
        if self.is_expired():
            self.active = False

    def heal(self, target):
        if hasattr(target, 'restore_health'):
            target.restore_health(self.heal_per_tick)
            print(f"[Effect] {self.__class__.__name__} healed {self.heal_per_tick} health for {target}")

class UtilityEffect(Effect):

    """Base class for utility effects (e.g., speed, stun, etc.)."""
    def __init__(self, duration=3.0, level=1):
        super().__init__(duration=duration, level=level)

    def apply(self, target):
        pass

    def update(self, target):
        pass

class IgniteEffect(DamageEffect):
    """Ignite effect: deals fire damage over time and increases vulnerability."""
    default_spread_radius = 0  # Class variable for spreading flames
    def __init__(self, damage_per_tick=1, tick_interval=1.0, duration=3.0, vulnerability=1.5, spread_radius=None, level=1):
        super().__init__(
            damage_per_tick=damage_per_tick,
            tick_interval=tick_interval,
            duration=duration,
            level=level
        )
        self.vulnerability = vulnerability  # Damage multiplier
        self.spread_radius = spread_radius if spread_radius is not None else IgniteEffect.default_spread_radius  # For spreading flames

    def apply(self, target):
        print(f"[DEBUG][Effect] Ignite applied to {target} for {self.duration}s at level {self.level}")
        # Set vulnerability multiplier on target
        target.fire_vulnerability = self.vulnerability

    def update(self, target):
        print(f"[DEBUG][Effect] IgniteEffect update for {target}")
        now = time.time()
        if now - self.last_tick >= self.tick_interval and self.active:
            self.last_tick = now
            self.deal_damage(target)
            # Spread flames if enabled
            if self.spread_radius > 0:
                self.spread_flames(target)
        if self.is_expired():
            self.remove(target)

    def spread_flames(self, target):
        # Use engine.enemies if available, else room.enemies
        enemies = None
        if hasattr(target, 'engine') and hasattr(target.engine, 'enemies'):
            enemies = target.engine.enemies
        elif hasattr(target, 'room') and hasattr(target.room, 'enemies'):
            enemies = target.room.enemies
        if enemies:
            for enemy in enemies:
                if enemy is not target:
                    dist = ((enemy.x - target.x) ** 2 + (enemy.y - target.y) ** 2) ** 0.5
                    if dist <= self.spread_radius:
                        if not any(isinstance(e, IgniteEffect) for e in getattr(enemy, 'effects', [])):
                            ignite = IgniteEffect(
                                damage_per_tick=self.damage_per_tick,
                                tick_interval=self.tick_interval,
                                duration=self.duration,
                                vulnerability=self.vulnerability,
                                spread_radius=0,
                                level=self.level
                            )
                            enemy.add_effect(ignite)
                            print(f"[DEBUG][Effect] Ignite spread to {enemy}")

    def remove(self, target):
        # Remove vulnerability multiplier
        if hasattr(target, 'fire_vulnerability'):
            del target.fire_vulnerability
            print(f"[DEBUG][Effect] Ignite expired: vulnerability removed from {target}")

class PoisonEffect(DamageEffect):

    """Poison effect: deals damage over time."""
    def __init__(self, damage_per_tick=2, tick_interval=1.0, duration=5.0, level=1):
        # Increase damage and duration based on level
        super().__init__(
            damage_per_tick=damage_per_tick,
            tick_interval=tick_interval,
            duration=duration,
            level=level
        )
        
    def apply(self, target):
        print(f"[DEBUG][Effect] Poison applied to {target} for {self.duration}s at level {self.level}")
        # Optionally, add a status to the target for UI

    def update(self, target):
        print(f"[DEBUG][Effect] PoisonEffect update for {target}")
        super().update(target)
        # Optionally, add poison visual effect here

class SlowEffect(UtilityEffect):
    """Reduces target's movement speed temporarily."""
    def __init__(self, duration=3.0, speed_multiplier=0.7, level=1):
        super().__init__(duration=duration, level=level)
        self.speed_multiplier = speed_multiplier
        self.original_speed_multiplier = None

    def apply(self, target):
        # Save original multiplier if not already set
        if not hasattr(target, 'speed_multiplier'):
            target.speed_multiplier = 1.0
        self.original_speed_multiplier = target.speed_multiplier
        target.speed_multiplier *= self.speed_multiplier
        print(f"[Effect] SlowEffect applied: speed_multiplier set to {target.speed_multiplier} for {target}")

    def update(self, target):
        # No update needed for constant slow
        if self.is_expired():
            self.remove(target)

    def remove(self, target):
        # Restore original speed multiplier
        if self.original_speed_multiplier is not None:
            target.speed_multiplier = self.original_speed_multiplier
            print(f"[Effect] SlowEffect expired: speed_multiplier restored to {target.speed_multiplier} for {target}")