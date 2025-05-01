import pygame
import os
import threading
import time
import json

from frames.assets.button import Button
from chess_board import ChessBoard
from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

class GameBoardPage(BasePage):
    def __init__(self, manager, client, selected_time_format, key):
        super().__init__(manager)
        self.client = client
        self.key = key
        self.screen = manager.screen

        self.board_width = 800
        self.board_height = 800
        self.square_size = self.board_width // 8

        self.white_color = (240, 217, 181)
        self.black_color = (181, 136, 99)

        self.selected_time_format = selected_time_format
        self.chess_board = ChessBoard()
        self.chess_board.set_board()

        self.piece_images = self.load_piece_images("chess pieces", self.square_size)

        self.selected_piece = None
        self.current_turn = "white"
        self.disable_clicks = False

        # Basic time logic
        base_time, increment = self.parse_time_format(self.selected_time_format)
        self.white_time = float(base_time)
        self.black_time = float(base_time)
        self.time_increment = increment
        self.last_update_ticks = pygame.time.get_ticks()

        self.leave_button = Button(
            image=None,
            pos=(1050, 780),
            text_input="LEAVE GAME",
            font=pygame.font.SysFont(None, 40),
            base_color="White",
            hovering_color="Red"
        )
        self.timer_font = pygame.font.SysFont(None, 40)

        # For receiving data from the server
        self.partial_buffer = ""
        self.running = True

        # Start a background thread to listen for server messages
        self.listen_thread = threading.Thread(target=self.listen_for_server_messages, daemon=True)
        self.listen_thread.start()

    def parse_time_format(self, time_format_str):
        if time_format_str == "Classical: 1 hour":
            return (60 * 60, 0)
        elif time_format_str == "Rapid: 30 min":
            return (30 * 60, 0)
        elif time_format_str == "Rapid: 10 min":
            return (10 * 60, 0)
        elif time_format_str == "Blitz: 3 + 1 min":
            return (3 * 60, 1)
        elif time_format_str == "Bullet: 1 + 1 min":
            return (1 * 60, 1)
        else:
            return (10 * 60, 0)

    def handle_events(self, events):
        if self.disable_clicks:
            return

        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.leave_button.checkForInput(mouse_pos):
                    self.leave_game()
                    return

                x, y = mouse_pos
                if 0 <= x < self.board_width and 0 <= y < self.board_height:
                    col = x // self.square_size
                    row = y // self.square_size
                    clicked_pos = (row, col)

                    if self.selected_piece is None:
                        piece_name, _ = self.chess_board.get_piece_possible_moves(clicked_pos)
                        if piece_name != "None":
                            # Check color matches current_turn
                            board_array = self.chess_board.get_normal_board()
                            piece_code = board_array[row][col]  # e.g., "BishopW"
                            color = "white" if piece_code.endswith("W") else "black"
                            if color == self.current_turn:
                                self.selected_piece = clicked_pos
                    else:
                        # Attempt the move
                        if self.chess_board.make_move(self.selected_piece, clicked_pos, self.current_turn):
                            # Add increment
                            if self.current_turn == "white":
                                self.white_time += self.time_increment
                            else:
                                self.black_time += self.time_increment

                            # Check for check or checkmate
                            in_check = self.chess_board.check_if_check()
                            if in_check != "N":
                                if self.chess_board.is_won(in_check):
                                    self.disable_clicks = True

                            # Send the move to the server
                            self.send_move_to_server({
                                "type": "move",
                                "from": [self.selected_piece[0], self.selected_piece[1]],
                                "to": [clicked_pos[0], clicked_pos[1]]
                            })

                            # Switch turns
                            if self.current_turn == "white":
                                self.current_turn = "black"
                            else:
                                self.current_turn = "white"

                        self.selected_piece = None

    def send_move_to_server(self, move_data):
        """
        Encrypt the move data and send it to the server.
        """
        move_json = json.dumps(move_data)
        encrypted = self.key.encrypt(
            move_json.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.client.send(encrypted)

    def listen_for_server_messages(self):
        """
        Background thread that continuously reads from the socket,
        accumulates partial JSON, and processes complete messages.
        """
        while self.running:
            time.sleep(0.1)  # slight delay to avoid busy loop
            self.receive_messages()

    def receive_messages(self):
        """
        Non-blocking read, parse any complete JSON objects.
        """
        try:
            self.client.setblocking(False)
            data = self.client.recv(4096)
        except:
            data = b''

        self.client.setblocking(True)
        if not data:
            return

        chunk = data.decode('utf-8', errors='replace')
        self.partial_buffer += chunk

        new_objects, offset = self.parse_multiple_json_objects(self.partial_buffer)
        self.partial_buffer = self.partial_buffer[offset:]

        for obj in new_objects:
            self.handle_server_message(obj)

    def parse_multiple_json_objects(self, data_str):
        """
        Attempt to parse multiple JSON objects from data_str.
        Return (list_of_objects, offset).
        """
        decoder = json.JSONDecoder()
        objs = []
        idx = 0
        length = len(data_str)

        while idx < length:
            while idx < length and data_str[idx].isspace():
                idx += 1
            if idx >= length:
                break
            try:
                obj, offset = decoder.raw_decode(data_str, idx)
                objs.append(obj)
                idx = offset
            except json.JSONDecodeError:
                break
        return objs, idx

    def handle_server_message(self, message):
        """
        Called for each JSON object from the server.
        """
        msg_type = message.get("type")
        if msg_type == "opponent_move":
            # Apply the opponent's move locally
            from_pos = message["from"]  # e.g. [row, col]
            to_pos = message["to"]
            # We assume the opponent's color is opposite our current_turn
            # or you can track whose side we're on. 
            # For this example, let's just do the opposite:
            opponent_color = "white" if self.current_turn == "black" else "black"

            self.chess_board.make_move(tuple(from_pos), tuple(to_pos), opponent_color)

            # Add time increment to opponent if desired
            # (In a real scenario, you'd need to track exactly which side is the opponent.)
            if opponent_color == "white":
                self.white_time += self.time_increment
                self.current_turn = "white"  # It's now white's turn again?
            else:
                self.black_time += self.time_increment
                self.current_turn = "black"

        # You might handle other message types here, e.g. "chat_message", "resign", etc.

    def leave_game(self):
        """
        Cleanup and go back to main menu.
        """
        self.running = False
        self.chess_board.reset_board()
        self.manager.set_current_page("MainMenuPage", self.client, key=self.key)

    def update(self):
        now_ticks = pygame.time.get_ticks()
        dt = (now_ticks - self.last_update_ticks) / 1000.0
        self.last_update_ticks = now_ticks

        if not self.disable_clicks:
            if self.current_turn == "white":
                self.white_time -= dt
                if self.white_time <= 0:
                    self.white_time = 0
                    self.disable_clicks = True
            else:
                self.black_time -= dt
                if self.black_time <= 0:
                    self.black_time = 0
                    self.disable_clicks = True

    def draw(self):
        THEMES = [
            {"bg": (0, 0, 0),        "text": (255, 255, 255)},
            {"bg": (255, 255, 255),  "text": (0, 0, 0)},
            {"bg": (0, 70, 160),     "text": (255, 255, 255)}
        ]
        
        theme_index = self.game_state.selected_theme
        theme = THEMES[theme_index]

        # Adjust button color if white theme
        if theme_index == 1:
            self.leave_button.base_color = (50, 50, 50)
            self.leave_button.hovering_color = (100, 100, 100)
        else:
            self.leave_button.base_color = "White"
            self.leave_button.hovering_color = "Red"

        self.screen.fill(theme["bg"])

        self.draw_board()
        self.draw_pieces()

        # Highlight selected piece + possible moves
        if self.selected_piece:
            row, col = self.selected_piece
            highlight_rect = (
                col * self.square_size,
                row * self.square_size,
                self.square_size,
                self.square_size
            )
            pygame.draw.rect(self.screen, (0, 255, 0), highlight_rect, 3)

            _, moves = self.chess_board.get_piece_possible_moves(self.selected_piece)
            for m in moves:
                r, c = m
                move_rect = (
                    c * self.square_size,
                    r * self.square_size,
                    self.square_size,
                    self.square_size
                )
                pygame.draw.rect(self.screen, (255, 0, 0), move_rect, 3)

        # Draw timers
        white_time_str = self.format_time(self.white_time)
        black_time_str = self.format_time(self.black_time)
        wsurf = self.timer_font.render(f"White: {white_time_str}", True, theme["text"])
        bsurf = self.timer_font.render(f"Black: {black_time_str}", True, theme["text"])
        self.screen.blit(wsurf, (850, 50))
        self.screen.blit(bsurf, (850, 100))

        # LEAVE button
        mouse_pos = pygame.mouse.get_pos()
        self.leave_button.changeColor(mouse_pos)
        self.leave_button.update(self.screen)

    def draw_board(self):
        for row in range(8):
            for col in range(8):
                color = self.white_color if (row + col) % 2 == 0 else self.black_color
                x = col * self.square_size
                y = row * self.square_size
                pygame.draw.rect(self.screen, color, (x, y, self.square_size, self.square_size))

    def draw_pieces(self):
        board = self.chess_board.get_normal_board()
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                piece_key = self.map_piece_name(piece)
                if piece_key and piece_key in self.piece_images:
                    x = col * self.square_size
                    y = row * self.square_size
                    self.screen.blit(self.piece_images[piece_key], (x, y))

    def load_piece_images(self, folder_path, square_size):
        piece_images = {}
        for color in ["white", "black"]:
            for piece_name in ["king", "queen", "rook", "bishop", "knight", "pawn"]:
                image_path = os.path.join(folder_path, f"{color}_{piece_name}.png")
                if os.path.exists(image_path):
                    img = pygame.image.load(image_path)
                    img = pygame.transform.scale(img, (square_size, square_size))
                    piece_images[f"{color}_{piece_name}"] = img
        return piece_images

    def map_piece_name(self, piece):
        """
        Convert a piece code like 'BishopW' or 'PownB' into 'white_bishop' or 'black_pawn'.
        """
        mapping = {
            "Rook": "rook",
            "Knight": "knight",
            "Bishop": "bishop",
            "Queen": "queen",
            "King": "king",
            "Pown": "pawn"
        }
        if piece:
            color = "white" if piece.endswith("W") else "black"
            base_name = piece[:-1]  # e.g. 'Bishop' from 'BishopW'
            piece_type = mapping.get(base_name, base_name.lower())
            return f"{color}_{piece_type}"
        return None

    def format_time(self, total_seconds):
        total_seconds = int(total_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def on_destroy(self):
        """
        Called if your framework calls 'destroy' or on exit. Stop the listen thread.
        """
        self.running = False
