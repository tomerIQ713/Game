class GameState:
    def __init__(self):
        self.username = ""
        self.selected_theme = 0
        self.themes = ["Default", "White", "Blue"]
        self.selected_time_format = None
        self.selected_game_type = None
        self.friend_name_to_invite = None  # We store the friend's name here if "Play a friend"
