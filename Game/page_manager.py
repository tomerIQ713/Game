import pygame
import sys
from game_state import GameState

class PageManager:
    def __init__(self, screen_width=1100, screen_height=600):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Menu")

        self.bg_image = pygame.image.load("frames/assets/white.png").convert()
        self.icon_image = pygame.image.load("frames/assets/strategy.png")
        pygame.display.set_icon(self.icon_image)

        self.font_small = pygame.font.SysFont(None, 25)
        self.font_medium = pygame.font.SysFont(None, 30)
        self.font_large = pygame.font.SysFont(None, 50)
        self.custom_font = pygame.font.Font("frames/assets/font.ttf", 50)

        self.game_state = GameState()

        self.pages = {}
        self.current_page = None

        self.clock = pygame.time.Clock()

    def register_page(self, page_name, page_class):
        self.pages[page_name] = page_class

    def set_current_page(self, page_name, *args, **kwargs):
        """
        If page_name isn't found, page_class will be None -> TypeError
        So ensure you spelled it exactly the same as in register_page calls.
        """
        page_class = self.pages.get(page_name)
        if page_class is None:
            raise ValueError(f"No page registered under the name '{page_name}'!")
        self.current_page = page_class(self, *args, **kwargs)

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

            if not running:
                break

            if self.current_page:
                self.current_page.handle_events(events)
                self.current_page.update()
                self.current_page.draw()

            pygame.display.update()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()