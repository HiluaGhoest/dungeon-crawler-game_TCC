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
            print(f"[DEBUG][Effect] {self.__class__.__name__} is dealing {self.damage_per_tick} damage to {target}")
            target.take_damage(self.damage_per_tick)
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
