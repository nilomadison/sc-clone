import pygame
import sys
import json
import os
from engine.grid import Grid
from engine.renderer import Renderer
from engine.systems import PowerSystem, GrowthSystem, DemandSystem
from engine.economy import EconomySystem

# Toolbar button configuration
TOOLBAR_HEIGHT = 60
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 40
BUTTON_MARGIN = 10

TOOLS = [
    ('residential', 'Residential', (0, 200, 0)),
    ('commercial', 'Commercial', (0, 0, 200)),
    ('industrial', 'Industrial', (200, 200, 0)),
    ('road', 'Road', (100, 100, 100)),
    ('power_plant', 'Power Plant', (200, 50, 0)),
    ('power_line', 'Power Line', (200, 180, 0)),
    ('grass', 'Bulldoze', (100, 50, 50)),
]

class Game:
    def __init__(self):
        pygame.init()
        self.screen_width = 1200
        self.screen_height = 800
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("SimCity Clone")
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.grid = Grid(100, 100) # 100x100 map
        self.renderer = Renderer(self.screen, self.grid)
        
        self.power_system = PowerSystem()
        self.growth_system = GrowthSystem()
        self.demand_system = DemandSystem()
        self.economy = EconomySystem()
        self.tick_timer = 0
        self.last_income = 0  # Track income for display
        
        # Notification system for user feedback
        self.notification_message = None
        self.notification_timer = 0
        
        self.current_tool = 'road'
        
        # Camera controls
        self.is_panning = False
        self.last_mouse_pos = (0, 0)
        
        # Drag placement for zones and roads
        self.drag_start = None  # (world_x, world_y) when drag started
        self.drag_end = None    # Current drag end position
        
        # Toolbar buttons
        self.buttons = []
        self._create_toolbar_buttons()
        
        self.font = pygame.font.SysFont(None, 20)
        self.font_large = pygame.font.SysFont(None, 28)

    def _create_toolbar_buttons(self):
        toolbar_y = self.screen_height - TOOLBAR_HEIGHT + (TOOLBAR_HEIGHT - BUTTON_HEIGHT) // 2
        start_x = BUTTON_MARGIN
        
        for i, (tool_id, label, color) in enumerate(TOOLS):
            btn_x = start_x + i * (BUTTON_WIDTH + BUTTON_MARGIN)
            rect = pygame.Rect(btn_x, toolbar_y, BUTTON_WIDTH, BUTTON_HEIGHT)
            self.buttons.append({
                'rect': rect,
                'tool': tool_id,
                'label': label,
                'color': color
            })

    def is_rci_tool(self):
        """Check if current tool is an RCI zone tool."""
        return self.current_tool in ['residential', 'commercial', 'industrial']

    def is_drag_tool(self):
        """Check if current tool uses drag-to-place."""
        return self.current_tool in ['residential', 'commercial', 'industrial', 'road']

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                # Check for Ctrl key modifiers
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_CTRL:
                    if event.key == pygame.K_s:
                        self.save_game()
                    elif event.key == pygame.K_l:
                        self.load_game()
                elif event.key == pygame.K_1: self.current_tool = 'residential'
                elif event.key == pygame.K_2: self.current_tool = 'commercial'
                elif event.key == pygame.K_3: self.current_tool = 'industrial'
                elif event.key == pygame.K_4: self.current_tool = 'road'
                elif event.key == pygame.K_5: self.current_tool = 'power_plant'
                elif event.key == pygame.K_6: self.current_tool = 'power_line'
                elif event.key == pygame.K_0: self.current_tool = 'grass'
                # Cancel drag if tool changes
                self.drag_start = None
                self.drag_end = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                
                # Check if clicking on toolbar
                if my >= self.screen_height - TOOLBAR_HEIGHT:
                    for btn in self.buttons:
                        if btn['rect'].collidepoint(mx, my):
                            self.current_tool = btn['tool']
                            # Cancel any ongoing drag
                            self.drag_start = None
                            self.drag_end = None
                            break
                elif event.button == 1:  # Left click - Use Tool
                    if self.is_drag_tool():
                        # Start drag placement
                        wx, wy = self.renderer.screen_to_world(mx, my)
                        self.drag_start = (wx, wy)
                        self.drag_end = (wx, wy)
                    else:
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

    def use_current_tool(self):
        mx, my = pygame.mouse.get_pos()
        # Don't build if clicking on toolbar
        if my >= self.screen_height - TOOLBAR_HEIGHT:
            return
        wx, wy = self.renderer.screen_to_world(mx, my)
        
        # Check if we can afford this
        if not self.economy.can_afford(self.current_tool):
            return  # Can't afford, do nothing
        
        if self.current_tool == 'power_line':
            if self.economy.deduct_cost(self.current_tool):
                self.grid.toggle_power_line(wx, wy)
        else:
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
            # Fill the entire rectangular area for RCI zones
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    if self.economy.can_afford(self.current_tool):
                        if self.economy.deduct_cost(self.current_tool):
                            self.grid.set_tile_type(x, y, self.current_tool)

    def _place_perimeter(self, min_x, min_y, max_x, max_y, tile_type):
        """Place tiles along the perimeter of a rectangle (no cost check)."""
        # Top edge
        for x in range(min_x, max_x + 1):
            self.grid.set_tile_type(x, min_y, tile_type)
        # Bottom edge
        for x in range(min_x, max_x + 1):
            self.grid.set_tile_type(x, max_y, tile_type)
        # Left edge (excluding corners already placed)
        for y in range(min_y + 1, max_y):
            self.grid.set_tile_type(min_x, y, tile_type)
        # Right edge (excluding corners already placed)
        for y in range(min_y + 1, max_y):
            self.grid.set_tile_type(max_x, y, tile_type)
    
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
            if self.economy.can_afford(tile_type):
                if self.economy.deduct_cost(tile_type):
                    self.grid.set_tile_type(x, y, tile_type)

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
        # Simulation ticks
        self.tick_timer += 1
        if self.tick_timer >= 60:  # Run simulation every 60 frames
            self.tick_timer = 0
            self.power_system.update(self.grid)
            self.growth_system.update(self.grid)
            self.demand_system.update(self.grid)
            self.last_income = self.economy.collect_taxes(self.grid)
        
        # Notification timer countdown
        if self.notification_timer > 0:
            self.notification_timer -= 1
            if self.notification_timer <= 0:
                self.notification_message = None

    def render(self):
        self.renderer.draw()
        
        # Draw Toolbar background
        toolbar_rect = pygame.Rect(0, self.screen_height - TOOLBAR_HEIGHT, self.screen_width, TOOLBAR_HEIGHT)
        pygame.draw.rect(self.screen, (40, 40, 50), toolbar_rect)
        pygame.draw.line(self.screen, (80, 80, 100), (0, self.screen_height - TOOLBAR_HEIGHT), 
                         (self.screen_width, self.screen_height - TOOLBAR_HEIGHT), 2)
        
        # Draw Toolbar buttons
        for btn in self.buttons:
            # Highlight selected tool
            if btn['tool'] == self.current_tool:
                pygame.draw.rect(self.screen, (255, 255, 255), btn['rect'].inflate(4, 4), 3)
            
            pygame.draw.rect(self.screen, btn['color'], btn['rect'])
            pygame.draw.rect(self.screen, (200, 200, 200), btn['rect'], 1)
            
            # Label
            label_surf = self.font.render(btn['label'], True, (255, 255, 255))
            label_rect = label_surf.get_rect(center=btn['rect'].center)
            self.screen.blit(label_surf, label_rect)
        
        # Draw current tool indicator at top
        tool_text = self.font_large.render(f'Selected: {self.current_tool.upper().replace("_", " ")}', True, (255, 255, 255))
        self.screen.blit(tool_text, (10, 10))
        
        # Stats - Money
        money_text = self.font_large.render(f'${self.economy.money:,}', True, (100, 255, 100))
        self.screen.blit(money_text, (10, 70))
        
        # Stats - Population
        total_pop = sum(tile.population for row in self.grid.tiles for tile in row)
        pop_text = self.font_large.render(f'Pop: {total_pop}', True, (255, 255, 255))
        self.screen.blit(pop_text, (self.screen_width - 200, 10))
        
        # Stats - Income per tick
        if self.last_income > 0:
            income_text = self.font.render(f'+${self.last_income}/tick', True, (150, 255, 150))
            self.screen.blit(income_text, (self.screen_width - 200, 35))
        
        # RCI Demand Bars
        self._draw_rci_bars()
        
        # Instructions
        instructions = "Keys 1-6, 0 | Left-click: Build | Right-drag: Pan | Ctrl+S: Save | Ctrl+L: Load"
        instr_surf = self.font.render(instructions, True, (180, 180, 180))
        self.screen.blit(instr_surf, (10, 40))
        
        # Draw drag preview or regular cursor
        drag_rect = self.get_drag_rect()
        if drag_rect:
            if self.current_tool == 'road':
                self.renderer.draw_road_preview(drag_rect)
            else:
                self.renderer.draw_rci_preview(drag_rect, self.current_tool)
        else:
            self.renderer.draw_cursor(pygame.mouse.get_pos())
        
        # Draw notification message
        if self.notification_message:
            notif_surf = self.font_large.render(self.notification_message, True, (255, 255, 100))
            notif_rect = notif_surf.get_rect(center=(self.screen_width // 2, 100))
            # Background for readability
            bg_rect = notif_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
            pygame.draw.rect(self.screen, (100, 100, 100), bg_rect, 2)
            self.screen.blit(notif_surf, notif_rect)
        
        pygame.display.flip()
    
    def _draw_rci_bars(self):
        """Draw RCI demand meter bars."""
        bar_width = 20
        bar_height = 60
        bar_x = self.screen_width - 80
        bar_y = 70
        
        colors = [
            ((0, 200, 0), self.demand_system.residential, 'R'),    # Green for Residential
            ((0, 100, 255), self.demand_system.commercial, 'C'),   # Blue for Commercial
            ((255, 200, 0), self.demand_system.industrial, 'I'),   # Yellow for Industrial
        ]
        
        for i, (color, demand, label) in enumerate(colors):
            x = bar_x + i * (bar_width + 5)
            
            # Background bar
            bg_rect = pygame.Rect(x, bar_y, bar_width, bar_height)
            pygame.draw.rect(self.screen, (40, 40, 40), bg_rect)
            
            # Demand bar (from center, positive goes up, negative goes down)
            center_y = bar_y + bar_height // 2
            bar_len = int(abs(demand) * (bar_height // 2))
            
            if demand >= 0:
                demand_rect = pygame.Rect(x + 2, center_y - bar_len, bar_width - 4, bar_len)
            else:
                demand_rect = pygame.Rect(x + 2, center_y, bar_width - 4, bar_len)
            
            if bar_len > 0:
                pygame.draw.rect(self.screen, color, demand_rect)
            
            # Center line
            pygame.draw.line(self.screen, (100, 100, 100), (x, center_y), (x + bar_width, center_y), 1)
            
            # Border
            pygame.draw.rect(self.screen, (100, 100, 100), bg_rect, 1)
            
            # Label
            label_surf = self.font.render(label, True, (255, 255, 255))
            self.screen.blit(label_surf, (x + 5, bar_y + bar_height + 2))
    
    def save_game(self, filepath='saves/city.json'):
        """Save the current game state to a JSON file."""
        # Ensure saves directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Serialize grid
        tiles_data = []
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                tile = self.grid.tiles[x][y]
                # Only save non-default tiles to reduce file size
                if tile.type != 'grass' or tile.has_power_line or tile.population > 0:
                    tiles_data.append({
                        'x': x,
                        'y': y,
                        'type': tile.type,
                        'has_power_line': tile.has_power_line,
                        'population': tile.population,
                    })
        
        save_data = {
            'version': '0.2.0',
            'grid': {
                'width': self.grid.width,
                'height': self.grid.height,
                'tiles': tiles_data,
            },
            'economy': self.economy.to_dict(),
            'camera': {
                'x': self.renderer.camera_x,
                'y': self.renderer.camera_y,
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        self.notification_message = "Game Saved!"
        self.notification_timer = 120  # 2 seconds at 60fps
    
    def load_game(self, filepath='saves/city.json'):
        """Load game state from a JSON file."""
        if not os.path.exists(filepath):
            self.notification_message = "No save file found!"
            self.notification_timer = 120
            return False
        
        try:
            with open(filepath, 'r') as f:
                save_data = json.load(f)
            
            # Reset grid
            self.grid = Grid(save_data['grid']['width'], save_data['grid']['height'])
            self.renderer.grid = self.grid
            
            # Restore tiles
            for tile_data in save_data['grid']['tiles']:
                x, y = tile_data['x'], tile_data['y']
                tile = self.grid.get_tile(x, y)
                if tile:
                    tile.type = tile_data['type']
                    tile.has_power_line = tile_data.get('has_power_line', False)
                    tile.population = tile_data.get('population', 0)
            
            # Restore economy
            self.economy.from_dict(save_data.get('economy', {}))
            
            # Restore camera
            camera_data = save_data.get('camera', {})
            self.renderer.camera_x = camera_data.get('x', 0)
            self.renderer.camera_y = camera_data.get('y', 0)
            
            # Run systems to update state
            self.power_system.update(self.grid)
            self.demand_system.update(self.grid)
            
            self.notification_message = "Game Loaded!"
            self.notification_timer = 120
            return True
        except Exception as e:
            self.notification_message = f"Load failed: {e}"
            self.notification_timer = 180
            return False

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()
