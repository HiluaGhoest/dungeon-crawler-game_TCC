class Perk:
    """Classe base para perks permanentes que podem ser adquiridos na loja."""
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def apply(self, player):
        """Aplica o efeito do perk ao jogador."""
        pass

class HealthBoostPerk(Perk):
    def __init__(self):
        super().__init__("Health Boost", "Aumenta a vida máxima do jogador.")

    def apply(self, player):
        player.max_health += 5
        player.health = player.max_health

class SpeedBoostPerk(Perk):
    def __init__(self):
        super().__init__("Speed Boost", "Aumenta a velocidade de movimento do jogador.")

    def apply(self, player):
        player.speed += 0.1

class DamageBoostPerk(Perk):
    def __init__(self):
        super().__init__("Damage Boost", "Aumenta o dano das armas do jogador.")

    def apply(self, player):
        import os, json
        level = 1
        perks_save_path = "perks.json"
        if os.path.exists(perks_save_path):
            try:
                with open(perks_save_path, "r") as f:
                    perks = json.load(f)
                    for p in perks:
                        if isinstance(p, dict) and p.get("name") == "Damage Boost":
                            level = p.get("level", 1)
                            break
            except Exception:
                level = 1
        player.damage_multiplier = 1.0 + 0.2 * level
