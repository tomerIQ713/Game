from base_piece import BasePiece

class Bishop(BasePiece):
    def __init__(self, color: str, position: tuple) -> None:
        super().__init__(color, position)

    def get_possible_moves(self, board) -> list:
        row, col = self.position
        possible_moves = []
    
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]  # Diagonal directions
    
        for dr, dc in directions:
            for i in range(1, 8):
                next_row, next_col = row + i * dr, col + i * dc
    
                if 0 <= next_row < 8 and 0 <= next_col < 8:  # Check board boundaries
                    target_piece = board[next_row][next_col]
    
                    if target_piece:
                        # Stop moving further in this direction if any piece is encountered
                        if target_piece.color != self.color:  # Enemy piece
                            possible_moves.append((next_row, next_col))
                        break
                    else:
                        # Empty square, add it to possible moves
                        possible_moves.append((next_row, next_col))
                else:
                    break  # Out of bounds, stop checking this direction
                
        return possible_moves
