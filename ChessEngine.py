import chess
import chess.engine

class ChessEngine:
    def __init__(self, stockfish_path="stockfish/stockfish.exe", depth=20):
        """
        Initialize the ChessEngine with Stockfish path and analysis depth.
        """
        self.stockfish_path = stockfish_path
        self.depth = depth
    

    def get_best_moves(self, fen, top_n=3):
        """
        Analyzes a FEN position and returns the top `top_n` best moves.
        """
        engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        board = chess.Board(fen)

        info = engine.analyse(board, chess.engine.Limit(depth=self.depth), multipv=top_n)
        engine.quit()

        best_moves = []
        for entry in info:
            move = entry["pv"][0]
            if move in board.legal_moves:
                best_moves.append((board.san(move), entry["score"].relative.score()))
            else:
                best_moves.append((move.uci(), entry["score"].relative.score()))

        return best_moves

    def board_to_fen(self, board, turn="W", castling="KQkq", en_passant="-", halfmove="0", fullmove="1"):
        """
        Convert a list-of-lists chess board into a FEN string.
        """
        piece_map = {
            "RookW": "R", "KnightW": "N", "BishopW": "B", "QueenW": "Q", "KingW": "K", "PownW": "P",
            "RookB": "r", "KnightB": "n", "BishopB": "b", "QueenB": "q", "KingB": "k", "PownB": "p"
        }

        if all(all(cell is None for cell in row) for row in board):
            print("Error: The board is completely empty! Returning default starting position.")
            return "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  

        fen_rows = []
        for row in board:
            empty = 0
            fen_row = ""
            for cell in row:
                if cell is None:
                    empty += 1
                else:
                    if empty > 0:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += piece_map[cell] if cell in piece_map else "?"
            if empty > 0:
                fen_row += str(empty)
            fen_rows.append(fen_row)

        fen_board = "/".join(fen_rows[::-1])
        turn_fen = "w" if turn == "W" else "b"
        return f"{fen_board} {turn_fen} {castling} {en_passant} {halfmove} {fullmove}"


    def evaluate_position(self, fen):
        """
        Use Stockfish to analyze a given FEN position and return evaluation.
        """
        try:
            engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
            board = chess.Board(fen)

            info = engine.analyse(board, chess.engine.Limit(depth=self.depth))
            engine.quit()

            score = info["score"].relative
            if score.is_mate():
                mate_in = score.mate()
                return f"{'White' if mate_in > 0 else 'Black'} is winning by checkmate in {abs(mate_in)} moves!"

            return f"Evaluation: {score.score() / 100}"

        except chess.engine.EngineTerminatedError:
            return "Stockfish crashed! Check if your Stockfish path is correct."
        except Exception as e:
            return f"Unexpected error: {e}"


    def evaluate_move(self, fen, move_uci):
        """
        Evaluates a specific move by comparing Stockfish's evaluation before and after the move.
        """
        engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        board = chess.Board(fen)

        info_before = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score_before = info_before["score"].relative.score()

        try:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                return f"Illegal move: {move_uci}"
            board.push(move)
        except Exception as e:
            return f"Invalid move format: {e}"

        info_after = engine.analyse(board, chess.engine.Limit(depth=self.depth))
        score_after = info_after["score"].relative.score()
        engine.quit()

        best_after = self.get_best_moves(board.fen(), top_n=1)
        best_move_after = best_after[0][0] if best_after else "Unknown"

        score_difference = score_after - score_before
        analysis = f"Move: {move_uci} ({board.san(move) if move in board.legal_moves else move_uci})\n"
        analysis += f"Evaluation before move: {score_before} centipawns\n"
        analysis += f"Evaluation after move: {score_after} centipawns\n"
        analysis += f"Score change: {score_difference} centipawns\n"
        analysis += f"Best move after this position: {best_move_after}\n"

        if score_difference > 50:
            analysis += "Great move! It improves your position significantly. 👍"
        elif score_difference > 0:
            analysis += "Good move! Your position slightly improves. ✅"
        elif score_difference > -50:
            analysis += "Inaccuracy! The move is not the best but not a blunder. 🤔"
        elif score_difference > -200:
            analysis += "Mistake! The move worsens your position. ❌"
        else:
            analysis += "Blunder! This move loses significant advantage. 🚨"

        return analysis

    def tuple_to_uci(self, move_tuple):
        """
        Converts a tuple move ((row1, col1), (row2, col2)) to UCI notation.
        """
        def square_index(row, col):
            return chess.square(col, 7 - row)

        from_square = square_index(*move_tuple[0])
        to_square = square_index(*move_tuple[1])

        return chess.SQUARE_NAMES[from_square] + chess.SQUARE_NAMES[to_square]