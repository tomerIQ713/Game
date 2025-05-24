from base_piece import BasePiece

class Rook(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)
        self.has_moved = False 

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []

        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]

        for dr, dc in directions:
            for step in range(1, 8): 
                next_row, next_col = row + dr * step, col + dc * step
                if 0 <= next_row < 8 and 0 <= next_col < 8:
                    target_piece = board[next_row][next_col]
                    if not target_piece: 
                        possible_moves.append((next_row, next_col))
                    elif target_piece.color != self.color:  
                        possible_moves.append((next_row, next_col))
                        break
                    else:
                        break
                else:
                    break

        return possible_moves

    def move(self, position):
        self.position = position
        self.has_moved = True  

