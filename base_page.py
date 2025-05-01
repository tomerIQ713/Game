class BasePage:
    def __init__(self, manager):
        self.manager = manager
        self.game_state = manager.game_state
        self.screen = manager.screen

    def handle_events(self, events):
        pass

    def update(self):
        pass

    def draw(self):
        pass