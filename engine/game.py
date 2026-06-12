import pygame
import sys

from engine import save
from engine.clock import GameClock
from engine.crime import CrimeSystem
from engine.decay import DecaySystem
from engine.disasters import DISASTERS, MESSAGES as DISASTER_MESSAGES, DisasterSystem
from engine.economy import EconomySystem
from engine.fire import FireSystem
from engine.grid import Grid
from engine.land_value import LandValueSystem
from engine.notifications import NotificationSystem
from engine.renderer import Renderer
from engine.systems import DemandSystem, GrowthSystem, PowerSystem
from engine.tiles import TILE_TYPES, TOOL_ORDER, ZONE_TYPES
from engine.ui import TOOLBAR_HEIGHT, UI

# Frames per simulation tick at 1x/2x/3x speed
SPEED_FRAMES = [60, 30, 20]


class Game:
    def __init__(self):
        pygame.init()
        self.screen_width = 1200
        self.screen_height = 800
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("SimCity Clone")

        self.pygame_clock = pygame.time.Clock()
        self.running = True

        self.grid = Grid(100, 100)  # 100x100 map
        self.renderer = Renderer(self.screen, self.grid)

        self.power_system = PowerSystem()
        self.growth_system = GrowthSystem()
        self.demand_system = DemandSystem()
        self.crime_system = CrimeSystem()
        self.land_value_system = LandValueSystem()
        self.fire_system = FireSystem()
        self.decay_system = DecaySystem()
        self.disaster_system = DisasterSystem()
        self.economy = EconomySystem()

        # Simulation clock: pause, speed, and the in-game calendar
        self.clock = GameClock()
        self.tick_timer = 0
        self.paused = False
        self.speed_index = 0  # Index into SPEED_FRAMES

        self.last_income = 0  # Last month's tax income, for display
        self.total_population = 0  # Cached per tick for the HUD

        self.notifications = NotificationSystem(self.screen_width, self.screen_height)

        # Data overlays, budget panel, and disasters panel
        self.current_overlay = None  # None, 'crime', 'land_value', 'power', 'fire'
        self.show_budget = False
        self.budget_selection = 0  # 0=tax, 1=police funding, 2=fire funding
        self.show_disasters = False

        self.current_tool = 'road'

        # Camera controls
        self.is_panning = False
        self.last_mouse_pos = (0, 0)

        # Drag placement for zones and roads
        self.drag_start = None  # (world_x, world_y) when drag started
        self.drag_end = None    # Current drag end position
        self.last_paint_pos = None  # Last tile painted during drag-paint

        self.ui = UI(self)

        # Tool hotkeys from the registry ('1'-'8', '0')
        self.hotkey_tools = {
            pygame.key.key_code(TILE_TYPES[tool]['hotkey']): tool
            for tool in TOOL_ORDER if TILE_TYPES[tool]['hotkey']
        }

    def _compute_population(self):
        return sum(self.grid.tiles[x][y].population for x, y in
                   self.grid.positions(*ZONE_TYPES))

    def is_rci_tool(self):
        """Check if current tool is an RCI zone tool."""
        return self.current_tool in ZONE_TYPES

    def is_drag_tool(self):
        """Check if current tool uses drag-to-place."""
        return self.current_tool in ZONE_TYPES or self.current_tool == 'road'

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # Check if clicking on toolbar
                if my >= self.screen_height - TOOLBAR_HEIGHT:
                    tool = self.ui.toolbar_click(mx, my)
                    if tool:
                        self.current_tool = tool
                        # Cancel any ongoing drag
                        self.drag_start = None
                        self.drag_end = None
                elif event.button == 1:  # Left click - Use Tool
                    if self.is_drag_tool():
                        # Start drag placement
                        wx, wy = self.renderer.screen_to_world(mx, my)
                        self.drag_start = (wx, wy)
                        self.drag_end = (wx, wy)
                    else:
                        self.last_paint_pos = None
                        self.use_current_tool()
                elif event.button == 3:  # Right click - Pan start or cancel drag
                    if self.drag_start:
                        # Cancel drag
                        self.drag_start = None
                        self.drag_end = None
                    else:
                        self.is_panning = True
                        self.last_mouse_pos = pygame.mouse.get_pos()

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1 and self.drag_start:
                    # Complete drag placement
                    mx, my = event.pos
                    if my < self.screen_height - TOOLBAR_HEIGHT:
                        wx, wy = self.renderer.screen_to_world(mx, my)
                        self.drag_end = (wx, wy)
                        self.place_drag_zone()
                    self.drag_start = None
                    self.drag_end = None
                elif event.button == 1:
                    self.last_paint_pos = None
                elif event.button == 3:
                    self.is_panning = False

            elif event.type == pygame.MOUSEMOTION:
                mx, my = pygame.mouse.get_pos()
                if self.is_panning:
                    dx = self.last_mouse_pos[0] - mx
                    dy = self.last_mouse_pos[1] - my
                    self.renderer.camera_x += dx
                    self.renderer.camera_y += dy
                    self.last_mouse_pos = (mx, my)
                elif self.drag_start:
                    # Update drag end position
                    if my < self.screen_height - TOOLBAR_HEIGHT:
                        wx, wy = self.renderer.screen_to_world(mx, my)
                        self.drag_end = (wx, wy)
                elif pygame.mouse.get_pressed()[0]:  # Drag to paint (non-drag tools)
                    if my < self.screen_height - TOOLBAR_HEIGHT:
                        self.use_current_tool()

    def _handle_keydown(self, event):
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            if event.key == pygame.K_s:
                self.save_game()
            elif event.key == pygame.K_l:
                self.load_game()
        # Disaster selection while the disasters panel is open (1-4)
        elif self.show_disasters and pygame.K_1 <= event.key <= pygame.K_4:
            name = DISASTERS[event.key - pygame.K_1]
            self.disaster_system.trigger(name, self.grid, self.fire_system)
            self.show_disasters = False
        # Tool selection
        elif event.key in self.hotkey_tools:
            self.current_tool = self.hotkey_tools[event.key]
        # Data overlays
        elif event.key == pygame.K_c:
            self.current_overlay = 'crime' if self.current_overlay != 'crime' else None
        elif event.key == pygame.K_v:
            self.current_overlay = 'land_value' if self.current_overlay != 'land_value' else None
        elif event.key == pygame.K_p:
            self.current_overlay = 'power' if self.current_overlay != 'power' else None
        elif event.key == pygame.K_f:
            self.current_overlay = 'fire' if self.current_overlay != 'fire' else None
        elif event.key == pygame.K_ESCAPE:
            self.current_overlay = None
            self.show_budget = False
            self.show_disasters = False
        # Disasters panel
        elif event.key == pygame.K_d:
            self.show_disasters = not self.show_disasters
        # Pause and simulation speed
        elif event.key == pygame.K_SPACE:
            self.paused = not self.paused
        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_index = max(0, self.speed_index - 1)
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.speed_index = min(len(SPEED_FRAMES) - 1, self.speed_index + 1)
        # Budget panel
        elif event.key == pygame.K_b:
            self.show_budget = not self.show_budget
        elif event.key == pygame.K_UP and self.show_budget:
            self.budget_selection = (self.budget_selection - 1) % 3
        elif event.key == pygame.K_DOWN and self.show_budget:
            self.budget_selection = (self.budget_selection + 1) % 3
        elif event.key == pygame.K_LEFT and self.show_budget:
            self._adjust_budget_value(-1)
        elif event.key == pygame.K_RIGHT and self.show_budget:
            self._adjust_budget_value(1)
        # Cancel drag if tool changes
        self.drag_start = None
        self.drag_end = None

    def use_current_tool(self):
        mx, my = pygame.mouse.get_pos()
        # Don't build if clicking on toolbar
        if my >= self.screen_height - TOOLBAR_HEIGHT:
            return
        wx, wy = self.renderer.screen_to_world(mx, my)
        # Don't re-apply to the same tile while drag-painting
        if (wx, wy) == self.last_paint_pos:
            return
        self.last_paint_pos = (wx, wy)
        self.apply_tool(wx, wy)

    def apply_tool(self, wx, wy):
        """Apply the current tool at world coordinates. Charges only on real changes."""
        tile = self.grid.get_tile(wx, wy)
        if tile is None:
            return

        if self.current_tool == 'power_line':
            if self.economy.deduct_cost(self.current_tool):
                self.grid.toggle_power_line(wx, wy)
        else:
            # No-op if the tile is already this type (also makes bulldozing grass free)
            if tile.type == self.current_tool:
                return
            if self.economy.deduct_cost(self.current_tool):
                self.grid.set_tile_type(wx, wy, self.current_tool)

    def place_drag_zone(self):
        """Place tiles based on drag from start to end."""
        if not self.drag_start or not self.drag_end:
            return

        x1, y1 = self.drag_start
        x2, y2 = self.drag_end

        # Normalize coordinates (ensure min <= max)
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        if self.current_tool == 'road':
            # Place roads along the perimeter only
            self._place_perimeter_with_cost(min_x, min_y, max_x, max_y, 'road')
        else:
            # Fill the entire rectangular area for RCI zones (empty land only)
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    self._place_on_grass(x, y, self.current_tool)

    def _place_on_grass(self, x, y, tile_type):
        """Place a tile only on empty grass, charging on success."""
        tile = self.grid.get_tile(x, y)
        if tile is None or tile.type != 'grass':
            return
        if self.economy.deduct_cost(tile_type):
            self.grid.set_tile_type(x, y, tile_type)

    def _place_perimeter_with_cost(self, min_x, min_y, max_x, max_y, tile_type):
        """Place tiles along the perimeter with cost deduction."""
        positions = []
        # Top edge
        for x in range(min_x, max_x + 1):
            positions.append((x, min_y))
        # Bottom edge (skip if same as top)
        if max_y != min_y:
            for x in range(min_x, max_x + 1):
                positions.append((x, max_y))
        # Left edge (excluding corners)
        for y in range(min_y + 1, max_y):
            positions.append((min_x, y))
        # Right edge (excluding corners, skip if same as left)
        if max_x != min_x:
            for y in range(min_y + 1, max_y):
                positions.append((max_x, y))

        for x, y in positions:
            self._place_on_grass(x, y, tile_type)

    def get_drag_rect(self):
        """Get the current drag rectangle in world coordinates, or None if not dragging."""
        if not self.drag_start or not self.drag_end:
            return None

        x1, y1 = self.drag_start
        x2, y2 = self.drag_end

        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        return (min_x, min_y, max_x, max_y)

    def update(self):
        self.notifications.update(self)

        if self.paused:
            return

        # Simulation ticks
        self.tick_timer += 1
        if self.tick_timer >= SPEED_FRAMES[self.speed_index]:
            self.tick_timer = 0
            self.power_system.update(self.grid)
            self.growth_system.update(self.grid, self.demand_system)
            self.demand_system.update(self.grid, self.economy.tax_rate)
            self.crime_system.update(self.grid)
            self.land_value_system.update(self.grid)
            self.disaster_system.update(self.grid, self.fire_system)
            self.fire_system.update(self.grid, self.economy)
            self.decay_system.update(self.grid, self.economy)
            self.total_population = self._compute_population()

            # Monthly budget settlement
            if self.clock.advance():
                self.last_income = self.economy.collect_monthly_taxes(
                    self.grid, GameClock.TICKS_PER_MONTH)
                self.economy.deduct_monthly_upkeep(self.grid)

            self._drain_system_events()

    def _drain_system_events(self):
        """Forward system events (collapses, disasters) to notifications."""
        for system in (self.fire_system, self.decay_system, self.disaster_system):
            for event in system.events:
                if event[0] == 'collapse':
                    self.notifications.notify_building_collapse(event[1], event[2])
                elif event[0] == 'disaster':
                    self.notifications.add(DISASTER_MESSAGES[event[1]], 'fire', 300)
            system.events.clear()

    def render(self):
        self.renderer.draw(overlay_mode=self.current_overlay)

        # Draw drag preview or regular cursor
        drag_rect = self.get_drag_rect()
        if drag_rect:
            if self.current_tool == 'road':
                self.renderer.draw_road_preview(drag_rect)
            else:
                self.renderer.draw_rci_preview(drag_rect, self.current_tool)
        else:
            self.renderer.draw_cursor(pygame.mouse.get_pos())

        if self.disaster_system.active:
            self.renderer.draw_disaster(self.disaster_system.active)

        self.ui.draw(self.screen)

        pygame.display.flip()

    def _adjust_budget_value(self, direction):
        """Adjust the currently selected budget value."""
        if self.budget_selection == 0:  # Tax rate
            self.economy.tax_rate = max(1, min(20, self.economy.tax_rate + direction))
        elif self.budget_selection == 1:  # Police funding
            current = self.economy.service_funding['police']
            new_value = max(0.0, min(1.0, current + direction * 0.1))
            self.economy.service_funding['police'] = new_value
            if new_value < 0.5:
                self.notifications.notify_service_underfunded('Police Department')
        elif self.budget_selection == 2:  # Fire funding
            current = self.economy.service_funding['fire']
            new_value = max(0.0, min(1.0, current + direction * 0.1))
            self.economy.service_funding['fire'] = new_value
            if new_value < 0.5:
                self.notifications.notify_service_underfunded('Fire Department')

    def save_game(self, filepath=save.DEFAULT_PATH):
        message = save.save_game(self, filepath)
        self.notifications.add(message, 'info', 120)

    def load_game(self, filepath=save.DEFAULT_PATH):
        ok, message = save.load_game(self, filepath)
        self.notifications.add(message, 'info', 120 if ok else 180)
        return ok

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.pygame_clock.tick(60)

        pygame.quit()
        sys.exit()
