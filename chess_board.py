from helper import Helper
from pieces.King import King, Rook
from ChessEngine import ChessEngine

class ChessBoard:
    def __init__(self):
        """
        Initializes an 8x8 chess board with all positions set to None.
        Also initializes a helper and a chess engine to manage the board state.
        """
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.helper = Helper()
        self.engine = ChessEngine()
        self.fen = self.engine.board_to_fen(self.get_normal_board())
        
    
    def get_best_moves(self, number_of_moves: int) -> list[tuple[str, int]]:
        """
        Retrieves the best possible moves based on the current board state.
        
        PARAMETERS:
            - number_of_moves: Number of top moves to retrieve.
        
        RETURNS:
            - A list of best moves recommended by the chess engine.
        """
        return self.engine.get_best_moves(self.fen, number_of_moves)

    def evaluate_position(self) -> None:
        """
        Evaluates the current board position and returns a numerical score.
        
        RETURNS:
            - Evaluation score based on the engine's algorithm.
        """
        return self.engine.evaluate_position(self.fen)
    
    def evaluate_move(self, move) -> tuple[int, int]:
        """
        Evaluates a specific move on the board.
        
        PARAMETERS:
            - move: The move to be evaluated (tuple format before conversion).
        
        RETURNS:
            - The evaluation score for the given move.
        """
        move = self.engine.tuple_to_uci(move)
        return self.engine.evaluate_move(self.fen, move)

    def set_board(self) -> None:
        """
        Places all pieces on the board in their starting positions.
        """
        self.helper.set_all_pieces_on_board(self.board)
    
    def set_helper(self, helper: Helper) -> None:
        """
        Sets a new helper object for board manipulation.
        
        PARAMETERS:
            - helper: Instance of the Helper class.
        """
        self.helper = helper
    
    def find_rook_pos(self, from_pos):
        if from_pos == (0, 4):
            pass

        elif from_pos == (7, 4):
            pass

    def make_move(self, from_pos: tuple[int, int], to_pos: tuple[int, int], current_turn) -> bool:
        """
        Moves a piece from 'from_pos' to 'to_pos' if the move is valid.

        PARAMETERS:
            - from_pos: Tuple indicating the current position of the piece.
            - to_pos: Tuple indicating the target position.

        RETURNS:
            - True if the move is successful, False otherwise.
        """
        print(f"Trying to move {from_pos} to {to_pos}")

        piece = self.board[from_pos[0]][from_pos[1]]
        if piece is None:
            print("No piece at from_pos.")
            return False

        if isinstance(piece, King):
            castling_moves, rook_positions = piece.get_castling_moves(self.board)
            if to_pos in castling_moves:
                idx = castling_moves.index(to_pos)
                rook_pos = rook_positions[idx]

                return self.perform_castling(from_pos, rook_pos)


        if to_pos not in self.get_piece_possible_moves(from_pos)[1]:
            print("Move not approved")
            return False

        self.put_piece(from_pos, to_pos)

        self.fen = self.engine.board_to_fen(self.get_normal_board())
        return True


    def get_piece_possible_moves(self, position: tuple[int, int]) -> tuple[str, list[tuple[int, int]]]:
        """
        Retrieves the possible moves for a piece at the given position.
        
        PARAMETERS:
            - position: Tuple indicating the position of the piece.
        
        RETURNS:
            - Tuple containing the piece type and a list of valid move positions.
        """
        row, col = position
        piece = self.board[row][col]
        if piece is None:
            return ("None", [])
        return (piece.__class__.__name__, piece.get_possible_moves(self.board))

    def put_piece(self, from_pos, to_pos) -> None:
        """
        Moves a piece from 'from_pos' to 'to_pos' and updates the board.
        """
        piece = self.board[from_pos[0]][from_pos[1]]
        print(f"Move made, {from_pos} -> {to_pos}, Piece: {piece.__class__.__name__}")
        self.put_and_switch(from_pos, to_pos, piece)

        if hasattr(piece, "has_moved"):
            piece.has_moved = True


    

    
    def put_and_switch(self, from_pos: tuple[int, int], to_pos: tuple[int, int], piece) -> None:
        """
        Switches the piece from its old position to a new position.
        
        PARAMETERS:
            - from_pos: Tuple indicating the current position of the piece.
            - to_pos: Tuple indicating the target position.
            - piece: The piece being moved.
        """
        self.board[from_pos[0]][from_pos[1]] = None
        piece.set_position(to_pos)
        self.board[to_pos[0]][to_pos[1]] = piece
        
    def perform_castling(self, king_pos: tuple[int, int], rook_pos: tuple[int, int]) -> bool:
        if rook_pos is None:
            return False

        king = self.board[king_pos[0]][king_pos[1]]
        if not isinstance(king, King) or not king.can_castle:
            return False

        if rook_pos[1] > king_pos[1]: 
            new_king_pos = (king_pos[0], king_pos[1] + 2)
            new_rook_pos = (rook_pos[0], rook_pos[1] - 2)
        else: 
            new_king_pos = (king_pos[0], king_pos[1] - 2)
            new_rook_pos = (rook_pos[0], rook_pos[1] + 3)

        # Move the king
        self.put_piece(king_pos, new_king_pos)
        # Move the rook
        self.put_piece(rook_pos, new_rook_pos)

        # The king can no longer castle
        king.can_castle = False
        king.has_moved = True

        # Also mark the rook as moved
        rook = self.board[new_rook_pos[0]][new_rook_pos[1]]
        if isinstance(rook, Rook):
            rook.has_moved = True

        # Update FEN if you use it
        self.fen = self.engine.board_to_fen(self.get_normal_board())
        print("Castling performed successfully.")
        return True


    
    def check_if_check(self):
        board = self.get_normal_board()
        white_king_pos = None
        black_king_pos = None

        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece:  
                    if 'KingW' in piece:
                        white_king_pos = (row, col)
                    elif 'KingB' in piece:
                        black_king_pos = (row, col)

        

        if white_king_pos and self.is_check_for_king(white_king_pos, 'W', board):
            return "white"  
        elif black_king_pos and self.is_check_for_king(black_king_pos, 'B', board):
            return "black"  
        return "N"  

    def is_check_for_king(self, king_pos, color, board):
        king_row, king_col = king_pos

        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece and piece[-1] != color: 
                    piece_class_name, possible_moves = self.get_piece_possible_moves((row, col))

                    if (king_row, king_col) in possible_moves:
                        return True
        return False
    
    def is_player_in_check(self, color: str) -> bool:
        """
        Returns True if the 'color' player's king is in check.
        """
        board = self.get_normal_board()
        # Find the color's king
        king_pos = None
        king_suffix = "W" if color == "white" else "B"

        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece and piece.endswith(f"King{king_suffix}"):
                    king_pos = (row, col)
                    break

        if king_pos is None:
            return False 

        return self.is_check_for_king(king_pos, king_suffix, board)
    

    def is_won(self, color):
        board = self.get_normal_board()

        white_king_pos = None
        black_king_pos = None

        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece:  
                    if 'KingW' in piece:
                        white_king_pos = (row, col)
                    elif 'KingB' in piece:
                        black_king_pos = (row, col)
        
        king_pos = white_king_pos if color == 'White' else black_king_pos

        if self.get_piece_possible_moves(king_pos)[1] == [] and self.is_check_for_king(king_pos, color, board):
            return True



        return self.is_checkmate(king_pos, color, board)
    


    def is_checkmate(self, king_pos, color, board):
        color = "W" if color == "White" else "B"

        if not self.is_check_for_king(king_pos, color, board):
            return False  # If not in check, it's not checkmate

        king_piece_name, king_moves = self.get_piece_possible_moves(king_pos)

        if king_piece_name != "King":
            return False  # Invalid input

        # Check all of the king's possible moves
        for move in king_moves:
            move_row, move_col = move

            if not (0 <= move_row < 8 and 0 <= move_col < 8):  # Out of bounds
                continue

            target_piece = board[move_row][move_col]
            if target_piece and target_piece[-1] == color:  # Friendly piece
                continue

            # Simulate the move to see if the king is still in check
            simulated_board = [row[:] for row in board]  # Copy the board
            simulated_board[king_pos[0]][king_pos[1]] = None  # Remove the king from its current position
            simulated_board[move_row][move_col] = f"King{color}"  # Place the king in the new position

            if not self.is_check_for_king((move_row, move_col), color, simulated_board):
                print(simulated_board)
                return False  # Not checkmate if the king can move safely
        

        for i in range(8):
            for j in range(8):
                piece = board[i][j]
                piece_name, possible_moves = self.get_piece_possible_moves((i, j))
                for move in possible_moves:
                    move_row, move_col = move

                    if not (0 <= move_row < 8 and 0 <= move_col < 8):  # Out of bounds
                        continue

                    target_piece = board[move_row][move_col]
                    if target_piece and target_piece[-1] == color:  # Friendly piece
                        continue
                    
                    # Simulate the move to see if the king is still in check
                    simulated_board = [row[:] for row in board]  # Copy the board
                    simulated_board[i][j] = None  # Remove the king from its current position
                    simulated_board[move_row][move_col] = f"{piece_name}{color}"  # Place the king in the new position

                    if not self.is_check_for_king(king_pos, color, simulated_board):
                        print(simulated_board)
                        return False


        # If no valid moves found and the king is still in check, it's checkmate
        return True
    
    def get_board(self):
        """
        Returns the current board state.
        """
        return self.board

    def reset_board(self) -> None:
        """
        Resets the board to its initial state.
        """
        self.board = [[None for _ in range(8)] for _ in range(8)]
        self.set_board()
    
    def print_board(self) -> None:
        """
        Prints the board state in a readable format.
        """
        for row in self.get_board():
            print([str(piece.__class__.__name__) + piece.color if piece else None for piece in row])
    
    def get_normal_board(self):
        """
        Returns a simplified representation of the board.
        """
        lst = []
        for row in self.get_board():
            lst.append([str(piece.__class__.__name__) + piece.color if piece else None for piece in row])
        return lst

    def get_helper(self) -> Helper:
        """
        Returns the current helper instance.
        """
        return self.helper

if __name__ == "__main__":
    chess_board = ChessBoard()
    chess_board.set_board()
    chess_board.print_board()

    print(chess_board.evaluate_position())
    print(chess_board.get_best_moves(10))
