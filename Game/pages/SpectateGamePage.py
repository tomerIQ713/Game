import pygame, threading, json, time
from frames.assets.button import Button
from chess_board import ChessBoard
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class SpectateGamePage(BasePage):
    """Read‑only board view for spectators. Receives FEN snapshots from the server.

    Expected server messages while in this page:
        • {"type":"spectate_update", "fen": <str>, "turn": "white"|"black"}
          – update the board position.
    """

    THEMES = [
        {"bg": (0, 0, 0),        "text": (255, 255, 255)},
        {"bg": (255, 255, 255),  "text": (0, 0, 0)},
        {"bg": (0, 70, 160),     "text": (255, 255, 255)}
    ]

    def __init__(self, manager, client, key, game_id, fen, turn):
        super().__init__(manager)
        self.client = client
        self.rsa_key = key
        self.game_id = game_id
        self.current_turn = turn or "white"

        self.chess = ChessBoard()
        if fen:
            self.chess.engine.set_fen(self.chess.board, fen)
        else:
            self.chess.set_board()

        self.square = 100
        self.board_px = 8 * self.square
        self.light = (240, 217, 181)
        self.dark = (181, 136, 99)
        self.piece_imgs = self._load_imgs("chess pieces")

        self.back_btn = Button(None, (1050, 780), "BACK",
                               pygame.font.SysFont(None, 40), "White", "Red")

        self.partial = ""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _listen_loop(self):
        while self.running:
            time.sleep(0.05)
            self.client.setblocking(False)
            try:
                data = self.client.recv(4096)
            except BlockingIOError:
                data = b""
            finally:
                self.client.setblocking(True)
            if not data:
                continue
            self.partial += data.decode("utf-8", "replace")
            objs, idx = self._parse_multi_json(self.partial)
            self.partial = self.partial[idx:]
            for obj in objs:
                self._handle_packet(obj)

    @staticmethod
    def _parse_multi_json(s):
        dec = json.JSONDecoder(); out = []; i = 0
        while i < len(s):
            while i < len(s) and s[i].isspace():
                i += 1
            if i >= len(s):
                break
            try:
                o, j = dec.raw_decode(s, i)
                out.append(o); i = j
            except json.JSONDecodeError:
                break
        return out, i

    def _handle_packet(self, msg):
        if msg.get("type") == "opponent_move":
            fen = msg.get("fen")
            if fen:
                self.chess.engine.set_fen(self.chess.board, fen)
            else:
                self.chess.make_move(tuple(msg["from"]), tuple(msg["to"]), self.current_turn)

            self.current_turn = "black" if self.current_turn == "white" else "white"

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.back_btn.checkForInput(mouse):
                    self.running = False
                    self.manager.set_current_page("SpectateLobbyPage", self.client, key=self.rsa_key)

    def update(self):
        pass  

    def draw(self):
        theme = self.THEMES[self.game_state.selected_theme]
        self.screen.fill(theme["bg"])
        self._draw_board()
        self._draw_pieces()

        info = f"Game ID: {self.game_id} • Turn: {self.current_turn.capitalize()}"
        txt = pygame.font.SysFont(None, 30).render(info, True, theme["text"])
        self.screen.blit(txt, (820, 50))

        self.back_btn.changeColor(pygame.mouse.get_pos())
        self.back_btn.update(self.screen)

    def _draw_board(self):
        for r in range(8):
            for c in range(8):
                col = self.light if (r + c) % 2 == 0 else self.dark
                pygame.draw.rect(self.screen, col,
                                 (c * self.square, r * self.square, self.square, self.square))

    def _draw_pieces(self):
        board = self.chess.get_normal_board()
        for r in range(8):
            for c in range(8):
                code = board[r][c]
                key = self._map_piece(code)
                if key in self.piece_imgs:
                    self.screen.blit(self.piece_imgs[key], (c * self.square, r * self.square))

    @staticmethod
    def _load_imgs(folder):
        imgs = {}
        for col in ("white", "black"):
            for name in ("king", "queen", "rook", "bishop", "knight", "pawn"):
                path = f"{folder}/{col}_{name}.png"
                try:
                    img = pygame.image.load(path).convert_alpha()
                    imgs[f"{col}_{name}"] = pygame.transform.scale(img, (100, 100))
                except pygame.error:
                    pass
        return imgs

    @staticmethod
    def _map_piece(code):
        if not code:
            return None
        col = "white" if code.endswith("W") else "black"
        base = code[:-1].lower()
        return f"{col}_{'pawn' if base == 'pown' else base}"

    def on_destroy(self):
        self.running = False
