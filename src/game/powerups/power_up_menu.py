import pygame
import random
from game import assets
from game.util.ui import Button
from game.assets import get_font, get_image

class PowerUpMenu:
	def __init__(self, powerups, player, on_select_callback, engine=None):
		"""
		powerups: list of PowerUp objects to choose from
		player: Player instance
		on_select_callback: function(powerup) called when a powerup is selected
		engine: GameEngine instance (for screen snapshot)
		"""
		self.powerups = powerups
		self.player = player
		self.on_select_callback = on_select_callback
		self.selected_index = 0
		self.buttons = []
		# Buttons will be created when draw() is called, with the correct surface size
		self.active = True
		self._cached_font = assets.get_font("game/assets/fonts/CinzelDecorative-Black.ttf", 18)
		self._cached_desc_surfs = None
		self._last_surface_size = None
		self._last_powerup_names = [p.name for p in powerups]
		self.engine = engine
		self.background_snapshot = None

	def _create_buttons(self, surface):
		# Layout buttons horizontally centered using actual surface size
		screen_width, screen_height = surface.get_size()
		btn_width = 320
		btn_height = 80
		spacing = 40
		total_width = btn_width * len(self.powerups) + spacing * (len(self.powerups) - 1)
		x_start = (screen_width - total_width) // 2
		y = screen_height // 2 - btn_height // 2
		self.buttons = []
		for i, powerup in enumerate(self.powerups):
			rect = (x_start + i * (btn_width + spacing), y, btn_width, btn_height)
			btn = Button(powerup.name, rect, lambda p=powerup: self.select_powerup(p))
			self.buttons.append(btn)
		self._last_surface_size = surface.get_size()
		self._last_powerup_names = [p.name for p in self.powerups]

	def draw(self, surface):
		# Only recreate buttons if surface size or powerup list changes
		surface_size = surface.get_size()
		powerup_names = [p.name for p in self.powerups]
		if (not self.buttons or self._last_surface_size != surface_size or self._last_powerup_names != powerup_names):
			self._create_buttons(surface)
			self._cached_desc_surfs = None  # Invalidate cached descriptions

		# Draw semi-transparent background
		overlay = pygame.Surface(surface_size, pygame.SRCALPHA)
		overlay.fill((20, 20, 20, 180))
		surface.blit(overlay, (0, 0))

		# Draw buttons
		mouse_pos = pygame.mouse.get_pos()
		for i, btn in enumerate(self.buttons):
			selected = (i == self.selected_index)
			btn.draw(surface, mouse_pos, selected=selected)

		# Cache description surfaces if not already cached
		if self._cached_desc_surfs is None:
			self._cached_desc_surfs = []
			for i, powerup in enumerate(self.powerups):
				desc_surf = self._cached_font.render(powerup.description, True, (200, 255, 200))
				self._cached_desc_surfs.append(desc_surf)

		# Draw descriptions below buttons
		for i, desc_surf in enumerate(self._cached_desc_surfs):
			btn_rect = self.buttons[i].rect
			desc_rect = desc_surf.get_rect(center=(btn_rect.centerx, btn_rect.bottom + 24))
			surface.blit(desc_surf, desc_rect)

	def run_menu(self):
		"""Run the power up menu with its own event loop and static background, similar to pause menu."""
		if self.engine:
			self.background_snapshot = self.engine.screen.copy()
		else:
			# Fallback: fill with black
			self.background_snapshot = None
		running_menu = True
		selected_index = 0
		mouse_active = False
		clock = pygame.time.Clock()
		# Create buttons
		surface = self.engine.screen if self.engine else None
		if surface:
			self._create_buttons(surface)
		while running_menu:
			dt = clock.tick(60) / 1000.0
			mouse_pos = pygame.mouse.get_pos()
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running_menu = False
					self.active = False
				elif event.type == pygame.KEYDOWN:
					if event.key in (pygame.K_LEFT, pygame.K_a):
						selected_index = max(0, selected_index - 1)
						mouse_active = False
					elif event.key in (pygame.K_RIGHT, pygame.K_d):
						selected_index = min(len(self.buttons)-1, selected_index + 1)
						mouse_active = False
					elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
						self.select_powerup(self.powerups[selected_index])
						running_menu = False
				elif event.type == pygame.MOUSEMOTION:
					mouse_active = True
					for i, btn in enumerate(self.buttons):
						if btn.rect.collidepoint(mouse_pos):
							selected_index = i
							break
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
					for i, btn in enumerate(self.buttons):
						if btn.rect.collidepoint(mouse_pos):
							self.select_powerup(self.powerups[i])
							running_menu = False
			# Draw static background
			if self.background_snapshot:
				self.engine.screen.blit(self.background_snapshot, (0, 0))
			else:
				self.engine.screen.fill((0, 0, 0))
			# Draw menu overlay and UI
			self.draw(self.engine.screen)
			pygame.display.flip()

	def handle_event(self, event):
		if not self.active:
			return
		if event.type == pygame.KEYDOWN:
			if event.key == pygame.K_LEFT:
				self.selected_index = max(0, self.selected_index - 1)
			elif event.key == pygame.K_RIGHT:
				self.selected_index = min(2, self.selected_index + 1)
			elif event.key == pygame.K_RETURN:
				self.select_powerup(self.powerups[self.selected_index])
		elif event.type == pygame.MOUSEBUTTONDOWN:
			for i, btn in enumerate(self.buttons):
				if btn.rect.collidepoint(event.pos):
					self.select_powerup(self.powerups[i])

	def select_powerup(self, powerup):
		print(f"[DEBUG] PowerUpMenu: Selected power-up '{powerup.name}' (Theme: {powerup.theme}, Tier: {powerup.tier})")
		self.active = False
		self.on_select_callback(powerup)