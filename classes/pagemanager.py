import pygame
import sys

from game_state import GameState


class PageManager:
    def __init__(self, screen_width, screen_height):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.pages = {}
        self.current_page = None

    def register_page(self, name, page_class):
        """Register a page without initializing it."""
        self.pages[name] = page_class

    def set_current_page(self, name, **kwargs):
        """Initialize and switch to a new page, passing parameters if needed."""
        if name in self.pages:
            self.current_page = self.pages[name](self, **kwargs)  # Pass parameters dynamically
        else:
            print(f"Error: Page '{name}' not found.")

    def run(self):
        """Main loop to handle events, update, and draw pages."""
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            self.current_page.handle_events(events)
            self.current_page.update()
            self.current_page.draw()
            pygame.display.flip()
