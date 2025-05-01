from base_piece import BasePiece

class Pown(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)
        self.has_moved = False

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []

        # First move allows moving two squares
        direction = 1 if self.color == 'W' else -1

        # One square move
        if 0 <= row + direction <= 7 and board[row + direction][col] is None:
            possible_moves.append((row + direction, col))

        # Two square move (only if the pawn hasn't moved yet)
        if not self.has_moved:
            if 0 <= row + 2 * direction <= 7 and board[row + 2 * direction][col] is None:
                possible_moves.append((row + 2 * direction, col))

        # Diagonal captures
        for delta_col in (-1, 1):
            next_row, next_col = row + direction, col + delta_col
            if 0 <= next_row <= 7 and 0 <= next_col <= 7:
                target_piece = board[next_row][next_col]
                if target_piece and target_piece.color != self.color:
                    possible_moves.append((next_row, next_col))

        return possible_moves

    def set_position(self, position):
        self.position = position
        self.has_moved = True  # Mark as moved when the pawn moves
