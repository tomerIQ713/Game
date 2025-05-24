
from helper import Helper
from pieces.King import King
from ChessEngine import ChessEngine
from pieces.Pawn  import Pown          
from pieces.Queen import Queen         


class ChessBoard:
    def __init__(self):
        self.helper = Helper()
        self.engine = ChessEngine()
        self.set_board()
        self.update_fen()

    def set_board(self):
        self.board = [[None] * 8 for _ in range(8)]
        self.helper.set_all_pieces_on_board(self.board)
        self.update_fen()

    def get_normal_board(self):
        board_codes = []
        for row in self.board:
            row_codes = []
            for cell in row:
                if cell is None or isinstance(cell, str):
                    row_codes.append(cell)
                else:
                    row_codes.append(f"{cell.__class__.__name__}{cell.color}")
            board_codes.append(row_codes)
        return board_codes


    def update_fen(self):
        self.fen = self.engine.board_to_fen(self.get_normal_board())

    def get_piece_possible_moves(self, pos):
        r, c = pos
        p = self.board[r][c]
        if p is None or isinstance(p, str):
            return ("None", [])
        return (p.__class__.__name__, p.get_possible_moves(self.board))

    def make_move(self, frm, to, turn_color):
        piece = self.board[frm[0]][frm[1]]
        if piece is None:
            return False
        
        if isinstance(piece, King) and frm[0] == to[0] and abs(to[1] - frm[1]) == 2:
            rook_col = 7 if to[1] > frm[1] else 0
            return self._try_castling(frm, (frm[0], rook_col), turn_color)

        _, legal = self.get_piece_possible_moves(frm)
        if to not in legal:
            return False
        
        captured = self.board[to[0]][to[1]]
        self._move_piece(frm, to)
        if self._in_check(turn_color):
            self._move_piece(to, frm)
            self.board[to[0]][to[1]] = captured
            return False

        if isinstance(piece, Pown):
            promote_row = 7 if piece.color == 'W' else 0
            if to[0] == promote_row:
                self.board[to[0]][to[1]] = Queen(piece.color, to)

        self.update_fen()
        return True


    def _try_castling(self, king_pos, rook_pos, color):
        king = self.board[king_pos[0]][king_pos[1]]
        rook = self.board[rook_pos[0]][rook_pos[1]]

        if (not isinstance(king, King) or rook is None or
                getattr(king, "has_moved", False) or
                getattr(rook, "has_moved", False)):
            return False

        step = 1 if rook_pos[1] > king_pos[1] else -1
        path = []
        c = king_pos[1] + step
        while c != rook_pos[1]:
            path.append((king_pos[0], c))
            c += step
        if any(self.board[r][c] is not None for r, c in path):
            return False

        king_steps = path[:2] 
        if self._in_check(color) or any(self._square_attacked(sq, color) for sq in king_steps):
            return False

        new_king = king_steps[-1]
        new_rook = (rook_pos[0], new_king[1] - step)
        self._move_piece(king_pos, new_king)
        self._move_piece(rook_pos, new_rook)
        king.has_moved = True
        rook.has_moved = True
        self.update_fen()
        return True

    def _move_piece(self, frm, to):
        obj = self.board[frm[0]][frm[1]]
        self.board[frm[0]][frm[1]] = None
        if obj and not isinstance(obj, str):
            obj.set_position(to)
            if hasattr(obj, "has_moved"):
                obj.has_moved = True
        self.board[to[0]][to[1]] = obj

    def _find_king(self, color):
        target = "W" if color == "white" else "B"
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if isinstance(p, King) and p.color == target:
                    return (r, c)
        return None

    def _square_attacked(self, square, defender_color):
        enemy = "B" if defender_color == "white" else "W"
        for r in range(8):
            for c in range(8):
                p = self.board[r][c]
                if p is None or isinstance(p, str) or p.color != enemy:
                    continue
                raw = p.get_possible_moves(self.board)
                moves = raw[1] if isinstance(raw, tuple) else raw
                if square in moves:
                    return True
        return False

    def _in_check(self, color):
        ksq = self._find_king(color)
        return ksq is None or self._square_attacked(ksq, color)
