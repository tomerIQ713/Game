from base_piece import BasePiece
from pieces.Rook import Rook

class King(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)
        self.can_castle = True
        self.has_moved = False

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, 1), (1, -1), (-1, -1)
        ]

        for dr, dc in directions:
            next_row, next_col = row + dr, col + dc
            if 0 <= next_row < 8 and 0 <= next_col < 8:
                target_piece = board[next_row][next_col]
                if not target_piece or target_piece.color != self.color:
                    possible_moves.append((next_row, next_col))

        castling_moves, _ = self.get_castling_moves(board)
        possible_moves.extend(castling_moves)

        return possible_moves

    def get_castling_moves(self, board) -> tuple[list, list]:
        """
        Returns a tuple:
          (list_of_castling_squares, list_of_rook_positions)
        That can be used by the ChessBoard to perform castling.
        """
        if not self.can_castle or self.has_moved:
            return ([], [])

        row, col = self.position
        castling_moves = []
        rook_positions = []


        if col + 1 < 7: 
            if all(board[row][i] is None for i in range(col + 1, 7)):
                if isinstance(board[row][7], Rook) and not board[row][7].has_moved:
                    castling_moves.append((row, 6))
                    rook_positions.append((row, 7))

        if col - 1 > 0:
            if all(board[row][i] is None for i in range(1, col) if i != col):
                if isinstance(board[row][0], Rook) and not board[row][0].has_moved:
                    castling_moves.append((row, 2))
                    rook_positions.append((row, 0))

        return (castling_moves, rook_positions)
