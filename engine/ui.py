"""
In-game UI: toolbar, HUD, RCI demand meter, notifications, and budget panel.

The UI reads game state and draws it; all mutation stays in Game (input
handling) and the systems.
"""

import pygame

from engine.disasters import DISASTERS
from engine.tiles import TILE_TYPES, TOOL_ORDER

TOOLBAR_HEIGHT = 60
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 10


class UI:
    def __init__(self, game):
        self.game = game
        self.font = pygame.font.SysFont(None, 20)
        self.font_large = pygame.font.SysFont(None, 28)
        self.buttons = []
        self._create_toolbar_buttons()

    def _create_toolbar_buttons(self):
        toolbar_y = (self.game.screen_height - TOOLBAR_HEIGHT +
                     (TOOLBAR_HEIGHT - BUTTON_HEIGHT) // 2)
        for i, tool_id in enumerate(TOOL_ORDER):
            config = TILE_TYPES[tool_id]
            btn_x = BUTTON_MARGIN + i * (BUTTON_WIDTH + BUTTON_MARGIN)
            self.buttons.append({
                'rect': pygame.Rect(btn_x, toolbar_y, BUTTON_WIDTH, BUTTON_HEIGHT),
                'tool': tool_id,
                'label': config['label'],
                'color': config['button_color'],
            })

    def toolbar_click(self, mx, my):
        """Return the tool id under the cursor, or None."""
        for btn in self.buttons:
            if btn['rect'].collidepoint(mx, my):
                return btn['tool']
        return None

    def draw(self, screen):
        self._draw_toolbar(screen)
        self._draw_hud(screen)
        self._draw_rci_bars(screen)
        self.game.notifications.render(screen, self.font)
        if self.game.show_budget:
            self._draw_budget_panel(screen)
        if self.game.show_disasters:
            self._draw_disasters_panel(screen)

    def _draw_toolbar(self, screen):
        game = self.game
        toolbar_rect = pygame.Rect(0, game.screen_height - TOOLBAR_HEIGHT,
                                   game.screen_width, TOOLBAR_HEIGHT)
        pygame.draw.rect(screen, (40, 40, 50), toolbar_rect)
        pygame.draw.line(screen, (80, 80, 100),
                         (0, game.screen_height - TOOLBAR_HEIGHT),
                         (game.screen_width, game.screen_height - TOOLBAR_HEIGHT), 2)

        for btn in self.buttons:
            # Highlight selected tool
            if btn['tool'] == game.current_tool:
                pygame.draw.rect(screen, (255, 255, 255), btn['rect'].inflate(4, 4), 3)

            pygame.draw.rect(screen, btn['color'], btn['rect'])
            pygame.draw.rect(screen, (200, 200, 200), btn['rect'], 1)

            label_surf = self.font.render(btn['label'], True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=btn['rect'].center)
            screen.blit(label_surf, label_rect)

    def _draw_hud(self, screen):
        game = self.game

        # Selected tool
        tool_text = self.font_large.render(
            f'Selected: {game.current_tool.upper().replace("_", " ")}',
            True, (255, 255, 255))
        screen.blit(tool_text, (10, 10))

        # Instructions
        instructions = ("1-8,0: Tools | C/V/P/F: Overlays | B: Budget | D: Disasters | "
                        "Space: Pause | -/+: Speed | Ctrl+S/L: Save/Load")
        instr_surf = self.font.render(instructions, True, (180, 180, 180))
        screen.blit(instr_surf, (10, 40))

        # Money
        money_text = self.font_large.render(f'${game.economy.money:,}', True, (100, 255, 100))
        screen.blit(money_text, (10, 70))

        # Date and speed / pause state
        if game.paused:
            status = f'{game.clock.date_string}  [PAUSED]'
            status_color = (255, 150, 150)
        else:
            status = f'{game.clock.date_string}  [{game.speed_index + 1}x]'
            status_color = (255, 255, 255)
        date_text = self.font_large.render(status, True, status_color)
        screen.blit(date_text, (10, 100))

        # Overlay mode
        if game.current_overlay:
            overlay_text = self.font.render(
                f'Overlay: {game.current_overlay.upper().replace("_", " ")}',
                True, (255, 200, 100))
            screen.blit(overlay_text, (10, 130))

        # Population
        pop_text = self.font_large.render(f'Pop: {game.total_population}', True, (255, 255, 255))
        screen.blit(pop_text, (game.screen_width - 200, 10))

        # Monthly income
        if game.last_income > 0:
            income_text = self.font.render(f'+${game.last_income}/mo', True, (150, 255, 150))
            screen.blit(income_text, (game.screen_width - 200, 35))

        # Power load (red when over capacity = brownouts)
        power = game.power_system
        if power.capacity > 0 or power.used > 0:
            over = power.used >= power.capacity
            power_color = (255, 100, 100) if over else (255, 255, 150)
            power_text = self.font.render(
                f'Power: {power.used}/{power.capacity}', True, power_color)
            screen.blit(power_text, (game.screen_width - 200, 52))

    def _draw_rci_bars(self, screen):
        """Draw RCI demand meter bars."""
        game = self.game
        bar_width = 20
        bar_height = 60
        bar_x = game.screen_width - 80
        bar_y = 70

        colors = [
            ((0, 200, 0), game.demand_system.residential, 'R'),    # Green for Residential
            ((0, 100, 255), game.demand_system.commercial, 'C'),   # Blue for Commercial
            ((255, 200, 0), game.demand_system.industrial, 'I'),   # Yellow for Industrial
        ]

        for i, (color, demand, label) in enumerate(colors):
            x = bar_x + i * (bar_width + 5)

            # Background bar
            bg_rect = pygame.Rect(x, bar_y, bar_width, bar_height)
            pygame.draw.rect(screen, (40, 40, 40), bg_rect)

            # Demand bar (from center, positive goes up, negative goes down)
            center_y = bar_y + bar_height // 2
            bar_len = int(abs(demand) * (bar_height // 2))

            if demand >= 0:
                demand_rect = pygame.Rect(x + 2, center_y - bar_len, bar_width - 4, bar_len)
            else:
                demand_rect = pygame.Rect(x + 2, center_y, bar_width - 4, bar_len)

            if bar_len > 0:
                pygame.draw.rect(screen, color, demand_rect)

            # Center line and border
            pygame.draw.line(screen, (100, 100, 100), (x, center_y), (x + bar_width, center_y), 1)
            pygame.draw.rect(screen, (100, 100, 100), bg_rect, 1)

            label_surf = self.font.render(label, True, (255, 255, 255))
            screen.blit(label_surf, (x + 5, bar_y + bar_height + 2))

    def _draw_budget_panel(self, screen):
        """Draw the budget panel overlay."""
        game = self.game
        panel_width = 320
        panel_height = 280
        panel_x = (game.screen_width - panel_width) // 2
        panel_y = (game.screen_height - panel_height) // 2

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, (30, 30, 40), panel_rect)
        pygame.draw.rect(screen, (100, 100, 120), panel_rect, 3)

        title = self.font_large.render("CITY BUDGET", True, (255, 255, 255))
        screen.blit(title, (panel_x + 90, panel_y + 10))

        y_offset = panel_y + 50

        treasury_text = self.font_large.render(
            f"Treasury: ${game.economy.money:,}", True, (100, 255, 100))
        screen.blit(treasury_text, (panel_x + 20, y_offset))

        y_offset += 35

        def draw_selection(y, selected):
            if selected:
                pygame.draw.polygon(screen, (255, 255, 100), [
                    (panel_x + 8, y + 4),
                    (panel_x + 16, y + 10),
                    (panel_x + 8, y + 16),
                ])

        # Tax Rate
        draw_selection(y_offset, game.budget_selection == 0)
        tax_color = (255, 255, 100) if game.budget_selection == 0 else (255, 255, 255)
        tax_text = self.font_large.render(f"Tax Rate: {game.economy.tax_rate}%", True, tax_color)
        screen.blit(tax_text, (panel_x + 20, y_offset))

        y_offset += 30

        # Police Funding
        draw_selection(y_offset, game.budget_selection == 1)
        police_pct = int(game.economy.service_funding['police'] * 100)
        police_color = (255, 255, 100) if game.budget_selection == 1 else (255, 255, 255)
        police_text = self.font.render(f"Police Funding: {police_pct}%", True, police_color)
        screen.blit(police_text, (panel_x + 20, y_offset))
        bar_x = panel_x + 180
        bar_width = 100
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y_offset + 2, bar_width, 12))
        pygame.draw.rect(screen, (0, 100, 255),
                         (bar_x, y_offset + 2,
                          int(bar_width * game.economy.service_funding['police']), 12))

        y_offset += 25

        # Fire Funding
        draw_selection(y_offset, game.budget_selection == 2)
        fire_pct = int(game.economy.service_funding['fire'] * 100)
        fire_color = (255, 255, 100) if game.budget_selection == 2 else (255, 255, 255)
        fire_text = self.font.render(f"Fire Funding: {fire_pct}%", True, fire_color)
        screen.blit(fire_text, (panel_x + 20, y_offset))
        pygame.draw.rect(screen, (60, 60, 60), (bar_x, y_offset + 2, bar_width, 12))
        pygame.draw.rect(screen, (178, 34, 34),
                         (bar_x, y_offset + 2,
                          int(bar_width * game.economy.service_funding['fire']), 12))

        y_offset += 35

        income_text = self.font.render(
            f"Income: +${game.last_income}/mo", True, (150, 255, 150))
        screen.blit(income_text, (panel_x + 20, y_offset))

        y_offset += 22

        upkeep_text = self.font.render(
            f"Upkeep: -${game.economy.last_upkeep}/mo", True, (255, 150, 150))
        screen.blit(upkeep_text, (panel_x + 20, y_offset))

        y_offset += 30

        controls = self.font.render("Up/Down: Select | Left/Right: Adjust", True, (150, 150, 150))
        screen.blit(controls, (panel_x + 30, y_offset))

        y_offset += 20

        close_text = self.font.render("Press B or Esc to close", True, (150, 150, 150))
        screen.blit(close_text, (panel_x + 70, y_offset))

    def _draw_disasters_panel(self, screen):
        """Draw the disasters panel overlay."""
        game = self.game
        panel_width = 280
        panel_height = 90 + len(DISASTERS) * 28
        panel_x = (game.screen_width - panel_width) // 2
        panel_y = (game.screen_height - panel_height) // 2

        panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        pygame.draw.rect(screen, (40, 25, 25), panel_rect)
        pygame.draw.rect(screen, (150, 80, 80), panel_rect, 3)

        title = self.font_large.render("DISASTERS", True, (255, 200, 200))
        screen.blit(title, (panel_x + 80, panel_y + 12))

        y_offset = panel_y + 50
        for i, name in enumerate(DISASTERS):
            entry = self.font.render(f"{i + 1}: {name.title()}", True, (255, 255, 255))
            screen.blit(entry, (panel_x + 40, y_offset))
            y_offset += 28

        close_text = self.font.render("Press D or Esc to close", True, (150, 150, 150))
        screen.blit(close_text, (panel_x + 55, y_offset + 5))
