from base_piece import BasePiece

class Queen(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []

        directions = [
            (0, 1), (0, -1), (1, 0), (-1, 0), 
            (1, 1), (1, -1), (-1, 1), (-1, -1) 
        ]

        for dr, dc in directions:
            for i in range(1, 8):
                next_row, next_col = row + i * dr, col + i * dc
                if 0 <= next_row <= 7 and 0 <= next_col <= 7:
                    target_piece = board[next_row][next_col]
                    if target_piece is None:
                        possible_moves.append((next_row, next_col))
                    elif target_piece.color != self.color:
                        possible_moves.append((next_row, next_col))
                        break
                    else:
                        break
                else:
                    break 

        return possible_moves
