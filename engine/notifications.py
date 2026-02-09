"""
Notification System for SimCity Clone v0.4.0

Manages toast notifications for game events like fires, budget warnings, etc.
"""

import pygame


class Notification:
    """A single notification message."""
    
    def __init__(self, message, notif_type='info', duration=300):
        self.message = message
        self.notif_type = notif_type  # 'fire', 'budget', 'collapse', 'info'
        self.duration = duration  # Frames to display
        self.remaining = duration
        self.alpha = 0  # For fade in/out
    
    def update(self):
        """Update notification state. Returns True if still active."""
        self.remaining -= 1
        
        # Fade in during first 30 frames
        if self.duration - self.remaining < 30:
            self.alpha = min(255, int((self.duration - self.remaining) / 30 * 255))
        # Fade out during last 30 frames
        elif self.remaining < 30:
            self.alpha = max(0, int(self.remaining / 30 * 255))
        else:
            self.alpha = 255
        
        return self.remaining > 0


class NotificationSystem:
    """System for managing and displaying toast notifications."""
    
    MAX_VISIBLE = 3  # Maximum notifications shown at once
    NOTIFICATION_HEIGHT = 60
    NOTIFICATION_WIDTH = 300
    MARGIN = 10
    
    # Notification type colors
    COLORS = {
        'fire': (200, 60, 60),       # Red for fire
        'budget': (200, 180, 60),    # Yellow for budget
        'collapse': (150, 150, 150), # Gray for collapse
        'info': (60, 120, 200),      # Blue for info
    }
    
    # Icons (simple colored shapes)
    ICONS = {
        'fire': '🔥',
        'budget': '💰',
        'collapse': '🏚',
        'info': 'ℹ',
    }

    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.notifications = []
        
        # Track recent events to avoid spam
        self.fire_notification_cooldown = 0
        self.budget_notification_cooldown = 0
        self.last_fire_count = 0

    def add(self, message, notif_type='info', duration=300):
        """Add a new notification to the queue."""
        notif = Notification(message, notif_type, duration)
        self.notifications.append(notif)
        
        # Limit queue size
        while len(self.notifications) > self.MAX_VISIBLE + 2:
            self.notifications.pop(0)

    def update(self, game=None):
        """Update all notifications and check for new events."""
        # Update existing notifications
        self.notifications = [n for n in self.notifications if n.update()]
        
        # Update cooldowns
        if self.fire_notification_cooldown > 0:
            self.fire_notification_cooldown -= 1
        if self.budget_notification_cooldown > 0:
            self.budget_notification_cooldown -= 1
        
        # Check for game events if game reference provided
        if game:
            self._check_fire_events(game)
            self._check_budget_events(game)

    def _check_fire_events(self, game):
        """Check for fire-related events."""
        if not hasattr(game, 'fire_system'):
            return
        
        fire_count = game.fire_system.get_fire_count()
        
        # Fire started
        if fire_count > 0 and self.last_fire_count == 0:
            if self.fire_notification_cooldown <= 0:
                self.add("Fire reported in the city!", 'fire', 240)
                self.fire_notification_cooldown = 300  # 5 second cooldown
        
        # Fire spreading
        elif fire_count > 3 and fire_count > self.last_fire_count + 2:
            if self.fire_notification_cooldown <= 0:
                self.add("Fire is spreading!", 'fire', 180)
                self.fire_notification_cooldown = 300
        
        # Fire extinguished
        elif fire_count == 0 and self.last_fire_count > 0:
            self.add("Fire has been extinguished", 'info', 180)
        
        self.last_fire_count = fire_count

    def _check_budget_events(self, game):
        """Check for budget-related events."""
        if not hasattr(game, 'economy'):
            return
        
        economy = game.economy
        
        # Low treasury warning
        if economy.money < 1000 and economy.money > 0:
            if self.budget_notification_cooldown <= 0:
                self.add("Treasury is running low!", 'budget', 300)
                self.budget_notification_cooldown = 600  # 10 second cooldown
        
        # Bankrupt
        elif economy.money <= 0:
            if self.budget_notification_cooldown <= 0:
                self.add("City is bankrupt!", 'budget', 300)
                self.budget_notification_cooldown = 600

    def notify_building_collapse(self, x, y):
        """Called when a building collapses."""
        self.add(f"Building collapsed at ({x}, {y})", 'collapse', 240)

    def notify_service_underfunded(self, service_name):
        """Called when a service is underfunded."""
        if self.budget_notification_cooldown <= 0:
            self.add(f"{service_name} is underfunded!", 'budget', 240)
            self.budget_notification_cooldown = 600

    def render(self, screen, font):
        """Render all visible notifications."""
        visible = self.notifications[-self.MAX_VISIBLE:]
        
        for i, notif in enumerate(reversed(visible)):
            self._render_notification(screen, font, notif, i)

    def _render_notification(self, screen, font, notif, index):
        """Render a single notification."""
        # Position from bottom-right
        x = self.screen_width - self.NOTIFICATION_WIDTH - self.MARGIN
        y = self.screen_height - 100 - (index + 1) * (self.NOTIFICATION_HEIGHT + self.MARGIN)
        
        # Background
        bg_color = self.COLORS.get(notif.notif_type, (60, 60, 60))
        bg_surface = pygame.Surface((self.NOTIFICATION_WIDTH, self.NOTIFICATION_HEIGHT), pygame.SRCALPHA)
        bg_surface.fill((*bg_color, int(notif.alpha * 0.85)))
        
        # Border
        pygame.draw.rect(bg_surface, (255, 255, 255, int(notif.alpha * 0.5)), 
                        (0, 0, self.NOTIFICATION_WIDTH, self.NOTIFICATION_HEIGHT), 2)
        
        screen.blit(bg_surface, (x, y))
        
        # Text
        if notif.alpha > 50:  # Only render text if visible enough
            text_color = (255, 255, 255, notif.alpha)
            text_surface = font.render(notif.message, True, (255, 255, 255))
            text_surface.set_alpha(notif.alpha)
            
            # Center text vertically, left-aligned with padding
            text_x = x + 15
            text_y = y + (self.NOTIFICATION_HEIGHT - text_surface.get_height()) // 2
            screen.blit(text_surface, (text_x, text_y))
