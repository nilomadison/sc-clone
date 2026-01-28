import pygame
import sys
from engine.grid import Grid
from engine.renderer import Renderer
from engine.systems import PowerSystem, GrowthSystem

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
        self.tick_timer = 0
        
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
                if event.key == pygame.K_1: self.current_tool = 'residential'
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
        if self.current_tool == 'power_line':
            self.grid.toggle_power_line(wx, wy)
        else:
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
            self._place_perimeter(min_x, min_y, max_x, max_y, 'road')
        else:
            # Fill the entire rectangular area for RCI zones
            for x in range(min_x, max_x + 1):
                for y in range(min_y, max_y + 1):
                    self.grid.set_tile_type(x, y, self.current_tool)

    def _place_perimeter(self, min_x, min_y, max_x, max_y, tile_type):
        """Place tiles along the perimeter of a rectangle."""
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
        
        # Stats - Population
        total_pop = sum(tile.population for row in self.grid.tiles for tile in row)
        pop_text = self.font_large.render(f'Population: {total_pop}', True, (255, 255, 255))
        self.screen.blit(pop_text, (self.screen_width - 200, 10))
        
        # Instructions
        instructions = "Keys 1-6, 0 also work | Left-click: Build | Right-drag: Pan"
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
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()
