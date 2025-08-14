import pygame
import math
from game import assets
from game.util.ui import Button
from game.assets import get_font, get_image

class PowerUpMenu:
    """
    Vertical power-up selection menu with:
      - compact top-to-bottom list of names,
      - bottom description box showing the currently selected item's description,
      - expanded view when holding SPACE (or right mouse button) that hides/dims others and
        shows the full description and metadata.
    """

    PADDING = 24
    ITEM_HEIGHT = 64
    ITEM_SPACING = 12
    DESC_BOX_HEIGHT = 160
    SCROLL_MARGIN = 2  # how many items from edges before auto-scrolling

    def __init__(self, powerups, player, on_select_callback, engine=None):
        self.powerups = list(powerups)
        self.player = player
        self.on_select_callback = on_select_callback
        self.engine = engine

        # UI state
        self.selected_index = 0
        self.start_index = 0  # for vertical scrolling
        self.buttons = []  # created by _create_buttons(surface)
        self.active = True
        self.background_snapshot = None

        # fonts + caching
        self._font = assets.get_font("game/assets/fonts/CinzelDecorative-Black.ttf", 20)
        self._small_font = assets.get_font("game/assets/fonts/CinzelDecorative-Black.ttf", 14)
        self._desc_cache = {}  # key: (idx, max_width) -> surface
        self._last_surface_size = None
        self._last_powerup_names = [p.name for p in self.powerups]

    # --------------------------
    # Helpers: text wrapping & caching
    # --------------------------
    def _wrap_text_to_surface(self, font, text, max_width, color=(200, 255, 200)):
        """
        Wrap text into multiple lines that fit in max_width and return a surface.
        Uses caching to avoid re-wrapping each frame.
        """
        key = (text, font.get_linesize(), max_width)
        # We use manual cache per-instance; include max_width since wrapping depends on width
        cached = self._desc_cache.get(key)
        if cached:
            return cached

        words = text.split(" ")
        lines = []
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            w_surf = font.render(test, True, color)
            if w_surf.get_width() <= max_width or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)

        # render lines into a surface
        line_height = font.get_linesize()
        surf_h = line_height * len(lines)
        surf = pygame.Surface((max_width, surf_h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))
        y = 0
        for line in lines:
            surf.blit(font.render(line, True, color), (0, y))
            y += line_height

        self._desc_cache[key] = surf
        return surf

    def _invalidate_cache_if_needed(self, surface):
        """
        If surface size or powerups list changed, clear cached surfaces and recreate buttons later.
        """
        size = surface.get_size()
        names = [p.name for p in self.powerups]
        if size != self._last_surface_size or names != self._last_powerup_names:
            self._desc_cache.clear()
            self.buttons = []
            self._last_surface_size = size
            self._last_powerup_names = names

    # --------------------------
    # Layout creation
    # --------------------------
    def _create_buttons(self, surface):
        """
        Create vertical buttons based on current surface size.
        This will be called whenever the surface size or powerup list changes.
        """
        screen_w, screen_h = surface.get_size()
        # area we allocate to list: from top padding to screen_h - description box - padding
        available_h = screen_h - self.DESC_BOX_HEIGHT - (self.PADDING * 2)
        btn_h = self.ITEM_HEIGHT
        spacing = self.ITEM_SPACING

        # button width - leave some padding around
        btn_w = min(640, screen_w - self.PADDING * 2)

        # calculate x start centered
        x = (screen_w - btn_w) // 2
        y_start = self.PADDING

        self.buttons = []
        for i, powerup in enumerate(self.powerups):
            rect = pygame.Rect(x, y_start + i * (btn_h + spacing), btn_w, btn_h)
            callback = (lambda p=powerup: self.select_powerup(p))
            btn = Button(powerup.name, rect, callback)
            # we also attach some extra metadata
            btn.powerup_index = i
            self.buttons.append(btn)

        # compute how many items can be visible in the list area
        per_item_total = btn_h + spacing
        self._visible_count = max(1, available_h // per_item_total)
        # ensure start_index + visible_count covers selected_index
        self._ensure_selected_visible()

    def _ensure_selected_visible(self):
        # keep selected in view by adjusting start_index
        if not self.buttons:
            return
        if self.selected_index < self.start_index:
            self.start_index = self.selected_index
        elif self.selected_index >= self.start_index + self._visible_count:
            self.start_index = self.selected_index - self._visible_count + 1

        # clamp
        max_start = max(0, len(self.buttons) - self._visible_count)
        self.start_index = max(0, min(self.start_index, max_start))

    # --------------------------
    # Drawing
    # --------------------------
    def draw(self, surface):
        """
        Draw the menu onto `surface`.
        Compact mode: vertical list + bottom description box.
        Expanded mode (hold SPACE or right mouse button): dim others and center full view.
        """
        if not self.active:
            return

        # invalidate caches if size changed or powerup list changed
        self._invalidate_cache_if_needed(surface)
        if not self.buttons:
            self._create_buttons(surface)

        screen_w, screen_h = surface.get_size()
        mouse_pos = pygame.mouse.get_pos()

        # background overlay
        overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        overlay.fill((10, 10, 10, 180))
        surface.blit(overlay, (0, 0))

        # detect whether expanded/focused view is requested
        keys = pygame.key.get_pressed()
        holding_space = keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[2]  # right-click or space
        expanded = holding_space

        # Draw visible buttons (top-to-bottom)
        per_item_total = self.ITEM_HEIGHT + self.ITEM_SPACING
        # compute list area start
        list_x = self.buttons[0].rect.x
        list_y = self.buttons[0].rect.y
        btn_w = self.buttons[0].rect.width
        visible_rects = []
        for visible_i in range(self._visible_count):
            real_idx = self.start_index + visible_i
            if real_idx >= len(self.buttons):
                break
            btn = self.buttons[real_idx]
            # compute on-screen rect (since buttons were laid out with absolute y)
            rect = pygame.Rect(btn.rect.x, list_y + visible_i * per_item_total, btn.rect.width, btn.rect.height)
            btn.rect = rect  # update rect so event-handling works with displayed positions

            # determine hover/select
            selected = (real_idx == self.selected_index)
            hovered = rect.collidepoint(mouse_pos)

            # dim other items if expanded
            if expanded and not selected:
                # draw dimmed background
                dim = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                dim.fill((30, 30, 30, 200))
                surface.blit(dim, rect.topleft)

                # still draw name but faded
                btn.draw(surface, mouse_pos, selected=False)
                s_surf = self._small_font.render(self.powerups[real_idx].name, True, (120, 120, 120))
                surface.blit(s_surf, (rect.x + 18, rect.centery - s_surf.get_height() // 2))
            else:
                btn.draw(surface, mouse_pos, selected=selected)

            visible_rects.append(rect)

            # update selection from hover (only update when not holding keyboard navigation)
            if hovered:
                self.selected_index = real_idx

        # Draw bottom description area (compact mode only)
        if not expanded:
            desc_box_rect = pygame.Rect(self.PADDING, screen_h - self.DESC_BOX_HEIGHT - self.PADDING,
                                        screen_w - self.PADDING * 2, self.DESC_BOX_HEIGHT)
            # draw a semi-opaque panel
            panel = pygame.Surface((desc_box_rect.width, desc_box_rect.height), pygame.SRCALPHA)
            panel.fill((12, 12, 12, 230))
            # border
            pygame.draw.rect(panel, (80, 80, 80), panel.get_rect(), 2)
            surface.blit(panel, desc_box_rect.topleft)

            # header: name + meta on left
            selected = self.powerups[self.selected_index]
            name_surf = self._font.render(selected.name, True, (230, 230, 200))
            surface.blit(name_surf, (desc_box_rect.x + 16, desc_box_rect.y + 12))

            meta = f"Tier: {getattr(selected, 'tier', 'N/A')}   Theme: {getattr(selected, 'theme', '')}"
            meta_surf = self._small_font.render(meta, True, (180, 180, 180))
            surface.blit(meta_surf, (desc_box_rect.x + 16, desc_box_rect.y + 12 + name_surf.get_height() + 6))

            # draw wrapped description inside the remaining area
            desc_max_w = desc_box_rect.width - 32
            desc_max_h = desc_box_rect.height - (12 + name_surf.get_height() + 6 + meta_surf.get_height() + 8)
            desc_surf = self._wrap_text_to_surface(self._small_font, selected.description, desc_max_w)
            # clip if too tall
            if desc_surf.get_height() > desc_max_h:
                # create a clipped surface with mask
                clip = pygame.Surface((desc_max_w, desc_max_h), pygame.SRCALPHA)
                clip.blit(desc_surf, (0, 0))
                surface.blit(clip, (desc_box_rect.x + 16, desc_box_rect.y + desc_box_rect.height - desc_max_h - 12))
            else:
                surface.blit(desc_surf, (desc_box_rect.x + 16, desc_box_rect.y + 12 + name_surf.get_height() + 6 + meta_surf.get_height() + 6))

        else:
            # Expanded view: center a larger panel with full description and details
            panel_w = min(900, screen_w - self.PADDING * 4)
            panel_h = min(520, screen_h - self.PADDING * 4)
            panel_x = (screen_w - panel_w) // 2
            panel_y = (screen_h - panel_h) // 2
            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill((18, 18, 18, 245))
            pygame.draw.rect(panel, (110, 110, 110), panel.get_rect(), 2)
            surface.blit(panel, (panel_x, panel_y))

            selected = self.powerups[self.selected_index]
            # name
            name_surf = self._font.render(selected.name, True, (240, 240, 220))
            surface.blit(name_surf, (panel_x + 20, panel_y + 20))

            # meta row
            meta = f"Tier: {getattr(selected, 'tier', 'N/A')}   Theme: {getattr(selected, 'theme', '')}"
            meta_surf = self._small_font.render(meta, True, (200, 200, 200))
            surface.blit(meta_surf, (panel_x + 20, panel_y + 20 + name_surf.get_height() + 8))

            # full description area
            desc_x = panel_x + 20
            desc_y = panel_y + 20 + name_surf.get_height() + 8 + meta_surf.get_height() + 8
            desc_w = panel_w - 40
            desc_h = panel_h - (desc_y - panel_y) - 20
            desc_surf = self._wrap_text_to_surface(self._small_font, selected.description, desc_w)
            # center vertically if small
            if desc_surf.get_height() < desc_h:
                surface.blit(desc_surf, (desc_x, desc_y))
            else:
                # clip
                clip = pygame.Surface((desc_w, desc_h), pygame.SRCALPHA)
                clip.blit(desc_surf, (0, 0))
                surface.blit(clip, (desc_x, desc_y))

            # optionally show a small "press to accept" hint
            hint = self._small_font.render("Press ENTER or click to select. Release SPACE to return.", True, (160, 160, 160))
            surface.blit(hint, (panel_x + 20, panel_y + panel_h - hint.get_height() - 12))

    # --------------------------
    # Event handling (for embedding in main loop)
    # --------------------------
    def handle_event(self, event):
        """Call this from your main loop when the menu is active."""
        if not self.active:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected_index = max(0, self.selected_index - 1)
                # adjust start index for scrolling
                if self.selected_index < self.start_index + self.SCROLL_MARGIN:
                    self.start_index = max(0, self.start_index - 1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected_index = min(len(self.powerups) - 1, self.selected_index + 1)
                if self.selected_index >= self.start_index + self._visible_count - self.SCROLL_MARGIN:
                    self.start_index = min(len(self.powerups) - self._visible_count, self.start_index + 1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                # Both ENTER and SPACE select the powerup.
                self.select_powerup(self.powerups[self.selected_index])
            elif event.key == pygame.K_ESCAPE:
                self.active = False

        elif event.type == pygame.MOUSEMOTION:
            # update hover selection
            mouse_pos = event.pos
            for i, btn in enumerate(self.buttons):
                if btn.rect.collidepoint(mouse_pos):
                    self.selected_index = i
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # left click
                for i, btn in enumerate(self.buttons):
                    if btn.rect.collidepoint(event.pos):
                        self.select_powerup(self.powerups[i])
                        break
            elif event.button == 4:  # wheel up
                self.selected_index = max(0, self.selected_index - 1)
                if self.selected_index < self.start_index + self.SCROLL_MARGIN:
                    self.start_index = max(0, self.start_index - 1)
            elif event.button == 5:  # wheel down
                self.selected_index = min(len(self.powerups) - 1, self.selected_index + 1)
                if self.selected_index >= self.start_index + self._visible_count - self.SCROLL_MARGIN:
                    self.start_index = min(len(self.powerups) - self._visible_count, self.start_index + 1)

    # --------------------------
    # Modal menu runner (optional)
    # --------------------------
    def run_menu(self):
        """
        Run the menu as a modal loop. If engine is not provided, this method will raise.
        Use handle_event/draw in your main loop if you want non-blocking behavior.
        """
        if not self.engine:
            raise RuntimeError("run_menu() requires a GameEngine instance assigned to self.engine")

        screen = self.engine.screen
        # take a static snapshot
        self.background_snapshot = screen.copy()
        self.active = True
        clock = pygame.time.Clock()

        # create buttons (in case not created yet)
        self._create_buttons(screen)

        while self.active:
            dt = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.active = False
                    # your engine should probably handle quitting; we keep behavior similar to original
                else:
                    self.handle_event(event)

            # draw the background snapshot
            if self.background_snapshot:
                screen.blit(self.background_snapshot, (0, 0))
            else:
                screen.fill((0, 0, 0))

            # draw menu and flip
            self.draw(screen)
            pygame.display.flip()

        # at end, menu is no longer active (either because selected or escape)
        self.active = False

    # --------------------------
    # Selection callback
    # --------------------------
    def select_powerup(self, powerup):
        print(f"[DEBUG] PowerUpMenu: Selected power-up '{powerup.name}' (Theme: {getattr(powerup, 'theme', None)}, Tier: {getattr(powerup, 'tier', None)})")
        self.active = False
        # call user-supplied callback (safely)
        try:
            self.on_select_callback(powerup)
        except Exception as e:
            print("[ERROR] Exception in on_select_callback:", e)
