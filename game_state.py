class GameState:
    def __init__(self):
        self.username = ""
        self.selected_theme = 0           # 0=dark, 1=light, 2=blue
        self.themes = ["Default", "White", "Blue"]

        # friend-game flow -----------------------------------------
        self.selected_time_format   = None
        self.selected_game_type     = None
        self.friend_name_to_invite  = None     # username string
        self.is_inviter             = None     # True / False / None
        # -----------------------------------------------------------
