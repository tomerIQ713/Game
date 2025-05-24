from base_piece import BasePiece

class Knight(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []

        moves = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]

        for dr, dc in moves:
            next_row, next_col = row + dr, col + dc
            if 0 <= next_row <= 7 and 0 <= next_col <= 7:
                target_piece = board[next_row][next_col]
                if not target_piece or target_piece.color != self.color:
                    possible_moves.append((next_row, next_col))

        return possible_moves
    