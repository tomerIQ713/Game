
import pathlib
import chess
import chess.engine


class ChessEngine:

    def __init__(self, stockfish_path="stockfish/stockfish.exe", depth=20):
        path = pathlib.Path(stockfish_path)
        if not path.is_file():
            raise FileNotFoundError(f"Stockfish binary not found at {path}")
        self.stockfish_path = str(path)
        self.depth = depth


    def _open(self):
        """Return a running SimpleEngine; caller must close()."""
        return chess.engine.SimpleEngine.popen_uci(self.stockfish_path)


    def get_best_moves(self, fen: str, top_n: int = 3):
        board = chess.Board(fen)
        engine = self._open()
        info = engine.analyse(board, chess.engine.Limit(depth=self.depth),
                              multipv=top_n)
        engine.quit()

        best = []
        for entry in info:
            move = entry["pv"][0]
            score = entry["score"].relative.score()
            best.append((board.san(move) if move in board.legal_moves else move.uci(),
                         score))
        return best

    def board_to_fen(self, board_2d, turn="W", castling="KQkq",
                     en_passant="-", halfmove="0", fullmove="1"):
        piece_map = {
            "RookW": "R", "KnightW": "N", "BishopW": "B",
            "QueenW": "Q", "KingW": "K", "PownW": "P",
            "RookB": "r", "KnightB": "n", "BishopB": "b",
            "QueenB": "q", "KingB": "k", "PownB": "p"
        }

        if all(all(cell is None for cell in row) for row in board_2d):
            return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

        fen_rows = []
        for row in board_2d:
            run, fen_row = 0, ""
            for cell in row:
                if cell is None:
                    run += 1
                else:
                    if run:
                        fen_row += str(run)
                        run = 0
                    fen_row += piece_map.get(cell, "?")
            if run:
                fen_row += str(run)
            fen_rows.append(fen_row)

        board_part = "/".join(fen_rows[::-1])
        return f"{board_part} {'w' if turn == 'W' else 'b'} {castling} {en_passant} {halfmove} {fullmove}"

    def evaluate_position(self, fen: str):
        engine = self._open()
        board = chess.Board(fen)
        info = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        engine.quit()

        score = info["score"].relative
        if score.is_mate():
            moves = abs(score.mate())
            winner = "White" if score.mate() > 0 else "Black"
            return f"{winner} mates in {moves}"
        return f"Evaluation: {score.score() / 100:.2f}"

    def set_fen(self, board_2d, fen: str):
        """
        In-place update of your 8×8 list-of-lists `board_2d`
        to match *fen*.

        board_2d comes from ChessBoard.board and contains either None or
        string codes like 'RookW', 'PownB', ...
        """
        piece_rev = {
            'R': 'RookW',   'N': 'KnightW', 'B': 'BishopW',
            'Q': 'QueenW',  'K': 'KingW',   'P': 'PownW',
            'r': 'RookB',   'n': 'KnightB', 'b': 'BishopB',
            'q': 'QueenB',  'k': 'KingB',   'p': 'PownB'
        }

        rows = fen.split()[0].split('/')
        if len(rows) != 8:
            raise ValueError("Bad FEN for set_fen")

        for r in range(8):
            for c in range(8):
                board_2d[r][c] = None

        for fen_r, row_str in enumerate(rows):
            board_r = 7 - fen_r         
            col = 0
            for ch in row_str:
                if ch.isdigit():
                    col += int(ch)
                else:
                    board_2d[board_r][col] = piece_rev.get(ch, None)
                    col += 1

    def evaluate_move(self, fen: str, move_uci: str):
        engine = self._open()
        board = chess.Board(fen)

        before = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score_before = before["score"].relative.score()

        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            engine.quit()
            return f"Illegal move: {move_uci}"

        board.push(move)    
        after = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        engine.quit()

        score_after = after["score"].relative.score()
        diff = score_after - score_before

        best_reply = self.get_best_moves(board.fen(), 1)[0][0]
        verdict = ("Great move! 👍"   if diff >  50 else
                   "Good move! ✅"    if diff >   0 else
                   "Inaccuracy 🤔"    if diff > -50 else
                   "Mistake ❌"       if diff > -200 else
                   "Blunder 🚨")

        return (f"{board.san(move)} ({move_uci})\n"
                f"Δ = {diff:+} cp\n"
                f"Best reply: {best_reply}\n"
                f"{verdict}")

    @staticmethod
    def tuple_to_uci(move_tuple):
        """((row, col), (row, col))  ->  \"e2e4\" (0-based rows/cols)."""
        def sq(r, c):
            return chess.square(c, 7 - r)
        return chess.square_name(sq(*move_tuple[0])) + chess.square_name(sq(*move_tuple[1]))
