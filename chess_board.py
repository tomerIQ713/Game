from helper import Helper
from pieces.King import King, Rook
from ChessEngine import ChessEngine


class ChessBoard:
    """
    Pure board representation + move legality.
    All turn / timer / network logic lives outside this class.
    """
    def __init__(self):
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.helper = Helper()
        self.engine = ChessEngine()
        self.set_board()   # fill starting pieces
        self.update_fen()

    # ---------------- BASIC GETTERS ----------------
    def get_board(self):
        return self.board

        # ------------------------------------------------------------------
    def get_normal_board(self):
        """
        Return a board snapshot as
            [[ 'RookW', None, 'PownB', ...], ... ]
        Works whether the internal board cells hold piece objects or the
        compact string codes inserted by set_fen() for spectators.
        """
        rows = []
        for row in self.board:
            out_row = []
            for cell in row:
                if cell is None:
                    out_row.append(None)
                elif isinstance(cell, str):            # already a code
                    out_row.append(cell)
                else:                                  # real piece object
                    out_row.append(f"{cell.__class__.__name__}{cell.color}")
            rows.append(out_row)
        return rows


    # ---------------- ENGINE HELPERS ---------------
    def update_fen(self):
        self.fen = self.engine.board_to_fen(self.get_normal_board())

    def get_best_moves(self, n):
        return self.engine.get_best_moves(self.fen, n)

    def evaluate_position(self):
        return self.engine.evaluate_position(self.fen)

    def evaluate_move(self, move):
        return self.engine.evaluate_move(self.fen, self.engine.tuple_to_uci(move))

    # ---------------- INITIAL SET-UP ---------------
    def set_board(self):
        self.helper.set_all_pieces_on_board(self.board)
        self.update_fen()

    # ---------------- MOVE HANDLING ----------------
    def make_move(self, frm, to, _turn_color):
        piece = self.board[frm[0]][frm[1]]
        if piece is None:
            return False

        # castling special case
        if isinstance(piece, King):
            casts, rooks = piece.get_castling_moves(self.board)
            if to in casts:
                return self.perform_castling(frm, rooks[casts.index(to)])

        _, legal = self.get_piece_possible_moves(frm)
        if to not in legal:
            return False

        self._move_piece(frm, to)
        self.update_fen()
        return True

    def _move_piece(self, frm, to):
        piece = self.board[frm[0]][frm[1]]
        self.board[frm[0]][frm[1]] = None
        piece.set_position(to)
        self.board[to[0]][to[1]] = piece
        if hasattr(piece, "has_moved"):
            piece.has_moved = True

    def perform_castling(self, king_pos, rook_pos):
        if rook_pos is None:
            return False
        king = self.board[king_pos[0]][king_pos[1]]
        if not isinstance(king, King) or not king.can_castle:
            return False

        kingside = rook_pos[1] > king_pos[1]
        new_king = (king_pos[0], king_pos[1] + 2) if kingside else (king_pos[0], king_pos[1] - 2)
        new_rook = (rook_pos[0], rook_pos[1] - 2) if kingside else (rook_pos[0], rook_pos[1] + 3)

        self._move_piece(king_pos, new_king)
        self._move_piece(rook_pos, new_rook)
        king.can_castle = False
        self.board[new_rook[0]][new_rook[1]].has_moved = True
        self.update_fen()
        return True

    # --------------- MOVE GENERATION ---------------
    def get_piece_possible_moves(self, position):
        """
        Returns (piece_name, list_of_moves).
        Handles both real Piece instances and plain string codes
        that spectators store after set_fen().
        """
        r, c = position
        piece = self.board[r][c]

        if piece is None or isinstance(piece, str):     # ← new guard
            return ("None", [])

        return (piece.__class__.__name__, piece.get_possible_moves(self.board))


    # --------------- CHECK / MATE UTIL -------------
    # (same as your original; omitted for brevity or keep if needed)
