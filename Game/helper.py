from base_piece import BasePiece
from pieces.Bishop import Bishop
from pieces.Knight import Knight
from pieces.King import King
from pieces.Rook import Rook
from pieces.Queen import Queen
from pieces.Pawn import Pown
import pygame
from termcolor import colored
import re

class Helper:
    """This class will simply execute a few simple operation, just for convenience"""

    def get_font(path, size):
        return pygame.font.Font(path, size)

    def split_text(text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)
        return lines

    def is_valid_username(username):
        if username[0].isdigit():
            return False
        if not re.match(r'^[a-zA-Z0-9 .\-\'_@]+$', username):
            return False
        return True

    def estimate_password_strength(password):
        length_points = min(10, len(password))
        variety_points = min(5, len(set(password)))
        pattern_penalty = 0

        if re.match(r'^[a-zA-Z]+$', password):
            pattern_penalty += 5
        if re.match(r'^\d+$', password):
            pattern_penalty += 5
        if re.match(r'^[!@#$%^&*()\-_=+\\|[\]{};:\'",.<>/?`~]+$', password):
            pattern_penalty += 5
        if re.match(r'(\d)\1+$', password):
            pattern_penalty += 5
        if re.match(r'([a-zA-Z])\1+$', password):
            pattern_penalty += 5
        if any(
            ord(password[i]) == ord(password[i+1]) - 1 == ord(password[i+2]) - 2
            for i in range(len(password) - 2)
        ):
            pattern_penalty += 10

        entropy = len(password) * (len(set(password)) ** 2)
        score = max(0, length_points + variety_points - pattern_penalty)
        return score, entropy

    def info_pass_str(password):
        score, entropy = Helper.estimate_password_strength(password)
        if score > 10:
            print(colored("PERFECT PASSWORD", 'green'))
        elif 5 < score <= 10:
            print(colored("THE PASSWORD IS OK", 'yellow'))
        else:
            print(colored("THE PASSWORD IS WEAK", 'red'))

    def set_all_pieces_on_board(self, board):
        self.set_white_pieces(board)
        self.set_black_pieces(board)

    def set_white_pieces(self, board):
        board[0][0] = Rook('W', (0, 0))
        board[0][1] = Knight('W', (0, 1))
        board[0][2] = Bishop('W', (0, 2))
        board[0][3] = Queen('W', (0, 3))
        board[0][4] = King('W', (0, 4))
        board[0][5] = Bishop('W', (0, 5))
        board[0][6] = Knight('W', (0, 6))
        board[0][7] = Rook('W', (0, 7))
        for col in range(8):
            board[1][col] = Pown('W', (1, col))

        return board
    
    def set_black_pieces(self, board):
        board[7][0] = Rook('B', (7, 0))
        board[7][1] = Knight('B', (7, 1))
        board[7][2] = Bishop('B', (7, 2))
        board[7][3] = Queen('B', (7, 3))
        board[7][4] = King('B', (7, 4))
        board[7][5] = Bishop('B', (7, 5))
        board[7][6] = Knight('B', (7, 6))
        board[7][7] = Rook('B', (7, 7))
        for col in range(8):
            board[6][col] = Pown('B', (6, col))

        return board
