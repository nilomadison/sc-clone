import pygame

# Colors
COLOR_GRASS = (139, 90, 43)  # Brown - to differentiate from residential green
COLOR_ROAD = (105, 105, 105)
COLOR_RESIDENTIAL = (0, 255, 0)
COLOR_COMMERCIAL = (0, 0, 255)
COLOR_INDUSTRIAL = (255, 255, 0)
COLOR_POWER_PLANT = (255, 69, 0)
COLOR_POWER_LINE = (255, 215, 0)
COLOR_POLICE = (0, 100, 255)
COLOR_HIGHLIGHT = (255, 255, 255)
COLOR_GRID_LINES = (50, 50, 50)

TILE_SIZE = 32

class Renderer:
    def __init__(self, screen, grid):
        self.screen = screen
        self.grid = grid
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0 # Placeholder for now, simplistic implementation
        self.screen_width, self.screen_height = screen.get_size()

    def world_to_screen(self, world_x, world_y):
        screen_x = (world_x * TILE_SIZE) - self.camera_x
        screen_y = (world_y * TILE_SIZE) - self.camera_y
        return screen_x, screen_y

    def screen_to_world(self, screen_x, screen_y):
        world_x = (screen_x + self.camera_x) // TILE_SIZE
        world_y = (screen_y + self.camera_y) // TILE_SIZE
        return int(world_x), int(world_y)

    def draw(self, overlay_mode=None):
        self.screen.fill((0, 0, 0)) # Clear with black

        # Determine visible range to optimize rendering
        start_col = max(0, int(self.camera_x // TILE_SIZE))
        end_col = min(self.grid.width, int((self.camera_x + self.screen_width) // TILE_SIZE) + 1)
        start_row = max(0, int(self.camera_y // TILE_SIZE))
        end_row = min(self.grid.height, int((self.camera_y + self.screen_height) // TILE_SIZE) + 1)

        for x in range(start_col, end_col):
            for y in range(start_row, end_row):
                tile = self.grid.get_tile(x, y)
                if not tile: continue

                sx, sy = self.world_to_screen(x, y)
                rect = (sx, sy, TILE_SIZE, TILE_SIZE)

                base_color = COLOR_GRASS
                if tile.type == 'road': base_color = COLOR_ROAD
                elif tile.type == 'residential': base_color = COLOR_RESIDENTIAL
                elif tile.type == 'commercial': base_color = COLOR_COMMERCIAL
                elif tile.type == 'industrial': base_color = COLOR_INDUSTRIAL
                elif tile.type == 'power_plant': base_color = COLOR_POWER_PLANT
                elif tile.type == 'police': base_color = COLOR_POLICE
                
                # Adjust color based on population (Darker = Empty, Brighter = Full)
                final_color = list(base_color)
                
                if tile.type in ['residential', 'commercial', 'industrial']:
                    pop_factor = 0.5 + (tile.population / 20.0) # 0.5 to 1.0
                    final_color = [c * pop_factor for c in final_color]
                    
                    if not tile.is_powered and tile.population > 0:
                        final_color = [c * 0.5 for c in final_color]
                    elif not tile.is_powered:
                         final_color = [c * 0.5 for c in final_color]

                pygame.draw.rect(self.screen, final_color, rect)
                
                # Draw power line as overlay if tile has power line
                if tile.has_power_line:
                    pygame.draw.rect(self.screen, COLOR_POWER_LINE, (sx + TILE_SIZE//2 - 2, sy, 4, TILE_SIZE))
                    pygame.draw.rect(self.screen, COLOR_POWER_LINE, (sx, sy + TILE_SIZE//2 - 2, TILE_SIZE, 4))
                
                # Draw grid lines
                pygame.draw.rect(self.screen, COLOR_GRID_LINES, rect, 1)

                # Draw missing power indicator
                if tile.needs_power and not tile.is_powered:
                    off_x = sx + TILE_SIZE - 9
                    off_y = sy + 2
                    
                    bolt_points = [
                        (off_x + 6, off_y),
                        (off_x + 2, off_y + 4),
                        (off_x + 5, off_y + 4),
                        (off_x + 1, off_y + 9),
                        (off_x + 5, off_y + 5),
                        (off_x + 2, off_y + 5),
                    ]
                    pygame.draw.polygon(self.screen, (255, 0, 0), bolt_points)
                    pygame.draw.lines(self.screen, (200, 0, 0), True, bolt_points, 1)
                
                # Draw data overlay if active
                if overlay_mode:
                    self._draw_overlay_tile(tile, sx, sy, overlay_mode)

    def _draw_overlay_tile(self, tile, sx, sy, overlay_mode):
        """Draw data overlay on a single tile."""
        overlay_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        
        if overlay_mode == 'crime':
            # Red overlay for crime level
            intensity = int(tile.crime_level * 200)
            overlay_surface.fill((255, 0, 0, intensity))
        elif overlay_mode == 'land_value':
            # Green for high value, red for low value
            value_normalized = tile.land_value / 100.0
            if value_normalized > 0.5:
                # High value = green
                intensity = int((value_normalized - 0.5) * 2 * 150)
                overlay_surface.fill((0, 255, 0, intensity))
            else:
                # Low value = red
                intensity = int((0.5 - value_normalized) * 2 * 150)
                overlay_surface.fill((255, 0, 0, intensity))
        elif overlay_mode == 'power':
            if tile.is_powered:
                overlay_surface.fill((255, 255, 0, 100))  # Yellow for powered
            elif tile.needs_power:
                overlay_surface.fill((255, 0, 0, 150))  # Red for needs power but unpowered
        
        self.screen.blit(overlay_surface, (sx, sy))

    def draw_cursor(self, mouse_pos):
        mx, my = mouse_pos
        wx, wy = self.screen_to_world(mx, my)
        sx, sy = self.world_to_screen(wx, wy)
        
        # Highlight cursor tile
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, (sx, sy, TILE_SIZE, TILE_SIZE), 2)

    def draw_rci_preview(self, world_rect, zone_type):
        """Draw a preview of the RCI zone being placed."""
        min_x, min_y, max_x, max_y = world_rect
        
        # Get the zone color
        if zone_type == 'residential':
            zone_color = COLOR_RESIDENTIAL
        elif zone_type == 'commercial':
            zone_color = COLOR_COMMERCIAL
        elif zone_type == 'industrial':
            zone_color = COLOR_INDUSTRIAL
        else:
            zone_color = COLOR_HIGHLIGHT
        
        preview_width = (max_x - min_x + 1) * TILE_SIZE
        preview_height = (max_y - min_y + 1) * TILE_SIZE
        
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                sx, sy = self.world_to_screen(x, y)
                preview_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                preview_surface.fill((*zone_color, 128))
                self.screen.blit(preview_surface, (sx, sy))
        
        start_sx, start_sy = self.world_to_screen(min_x, min_y)
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, 
                        (start_sx, start_sy, preview_width, preview_height), 3)

    def draw_road_preview(self, world_rect):
        """Draw a preview of roads being placed along the perimeter."""
        min_x, min_y, max_x, max_y = world_rect
        
        perimeter_tiles = set()
        
        for x in range(min_x, max_x + 1):
            perimeter_tiles.add((x, min_y))
            perimeter_tiles.add((x, max_y))
        
        for y in range(min_y, max_y + 1):
            perimeter_tiles.add((min_x, y))
            perimeter_tiles.add((max_x, y))
        
        for x, y in perimeter_tiles:
            sx, sy = self.world_to_screen(x, y)
            preview_surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            preview_surface.fill((*COLOR_ROAD, 160))
            self.screen.blit(preview_surface, (sx, sy))
        
        preview_width = (max_x - min_x + 1) * TILE_SIZE
        preview_height = (max_y - min_y + 1) * TILE_SIZE
        start_sx, start_sy = self.world_to_screen(min_x, min_y)
        pygame.draw.rect(self.screen, COLOR_HIGHLIGHT, 
                        (start_sx, start_sy, preview_width, preview_height), 3)
