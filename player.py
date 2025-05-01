from helper import Helper

class Player:
    def __init__(self) -> None:
        self.username = ""

        self.as_white: list[int, int, int] = [0, 0, 0] # Win-loss-Draw
        self.as_black: list[int, int, int] = [0, 0, 0]

        self.status = "NO STATUS"

        self.games: int = 0

        self.elo: int = 1000

        self.friends: list[Player] = []

        self.helper = Helper()
    
    def set_status(self, status):
        self.status = status
    
    def __str__(self) -> str:
        return f"{self.username}: \nTotal Games played: {self.games}\nElo(Rating): {self.elo}\n" + f"As white: {self.as_white}, As black: {self.as_black}\n" + f"Friends: {self.friends}"
    
    def get_games_played(self):
        return self.games

    def set_username(self, username):
        self.username = username
    
    def get_username(self):
        return self.username
    
    def get_status(self):
        return self.status

    def add_game(self, color, state) -> None:
        self.games += 1
        self.as_white, self.as_black = self.helper.add_game(color, state, self.as_white, self.as_black)
    
    def add_friend(self, player_username) -> None:
        print(f"Friend '{player_username}' added to '{self.username}'")
        self.friends.append(player_username)
    
    def remove_friend(self, player) -> None:
        print(f"Friend removed from '{self.username}'")
        self.friends.remove(player)
    
    def get_elo(self) -> int:
        return self.elo
    
    def update_elo(self, other_player_rating, state : str) -> None:
        print(f"Elo updated:{self.elo} -> ", end='')
        self.elo = self.helper.update_elo_rating(self.elo, other_player_rating, state)
        print(self.elo)

    def get_friends(self) -> tuple[list, int]:
        return (self.friends, len(self.friends))

    def get_as_white(self):
        return self.as_white

    def get_as_black(self):
        return self.as_black

