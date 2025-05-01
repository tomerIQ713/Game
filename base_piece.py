class BasePiece:
    def __init__(self, color: str, position: tuple) -> None:
        self.color = color
        self.position = position

    def set_position(self, position: tuple) -> None:
        self.position = position
    
    def get_position(self) -> tuple:
        return self.position
