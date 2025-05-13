import pygame, os, threading, time, json
from frames.assets.button import Button
from chess_board import ChessBoard
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class GameBoardPage(BasePage):
    THEMES = [
        {"bg": (0, 0, 0), "text": (255, 255, 255)},
        {"bg": (255, 255, 255), "text": (0, 0, 0)},
        {"bg": (0, 70, 160), "text": (255, 255, 255)},
    ]

    # ──────────────────────────────────────────────────────────────
    def __init__(self,
                 manager,
                 client,
                 selected_time_format,
                 key,
                 player_color,
                 current_turn,
                 game_id=None):
        super().__init__(manager)

        # ---------- networking / identification ----------
        self.client = client
        self.rsa_pubkey = key
        self.player_color = player_color         # "white" | "black"
        self.current_turn = current_turn         # whose move now
        self.game_id = game_id
        self.selected_time_format = selected_time_format  # keep!

        # ---------- chess model ----------
        self.chess_board = ChessBoard()
        self.chess_board.set_board()
        self.chess = self.chess_board            # secondary alias
        self.selected_piece = None
        self.disable_clicks = (self.player_color != self.current_turn)

        # ---------- time control ----------
        base, inc = self.parse_time_format(self.selected_time_format)
        self.timers = {"white": float(base), "black": float(base)}
        self.time_increment = inc
        self.last_ticks = pygame.time.get_ticks()

        # ---------- board drawing ----------
        self.board_px = 800
        self.square = self.board_px // 8
        self.light = (240, 217, 181)
        self.dark = (181, 136, 99)
        self.piece_images = self.load_imgs("chess pieces")

        # ---------- fonts / UI ----------
        self.timer_font = pygame.font.SysFont(None, 40)
        self.leave_btn = Button(
            image=None, pos=(1050, 780), text_input="LEAVE GAME",
            font=pygame.font.SysFont(None, 40),
            base_color="White", hovering_color="Red")

        # ---------- async listen thread ----------
        self.partial = ""
        self.running = True
        threading.Thread(target=self.listen_loop, daemon=True).start()

    # ──────────────────────────────────────────────────────────────
    #                 PARSE TIME FORMAT
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def parse_time_format(text: str):
        if not text:
            return 600, 0
        if "hour" in text.lower():
            return 3600, 0
        if "Rapid: 30" in text:
            return 30 * 60, 0
        if text.startswith("Rapid"):
            return 10 * 60, 0
        if text.startswith("Blitz"):
            return 3 * 60, 1
        if text.startswith("Bullet"):
            return 60, 1
        return 600, 0      # default 10 min rapid

    # ──────────────────────────────────────────────────────────────
    #                       NETWORKING
    # ──────────────────────────────────────────────────────────────
    def listen_loop(self):
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
            packets, idx = self.parse_multi_json(self.partial)
            self.partial = self.partial[idx:]
            for pkt in packets:
                self.handle_msg(pkt)

    @staticmethod
    def parse_multi_json(s):
        dec, out, i, n = json.JSONDecoder(), [], 0, len(s)
        while i < n:
            while i < n and s[i].isspace():
                i += 1
            if i >= n:
                break
            try:
                o, j = dec.raw_decode(s, i)
                out.append(o); i = j
            except json.JSONDecodeError:
                break
        return out, i

        # ──────────────────────────────────────────────────────────────
    def handle_msg(self, msg):
        """
        Process packets from the server.
        For a player window we *ignore* the optional 'fen' so our board keeps
        real piece objects; spectators use a different page that loads FEN.
        """
        if msg.get("type") != "opponent_move":
            return

        # 1. update board by incremental move
        self.apply_move(tuple(msg["from"]), tuple(msg["to"]))

        # 2. increment opponent's clock
        self.timers[self.current_turn] += self.time_increment

        # 3. flip turn & enable clicks if it's now our move
        self.current_turn = "black" if self.current_turn == "white" else "white"
        self.disable_clicks = (self.player_color != self.current_turn)



    # ---------- send helper ----------
    def enc_send(self, obj):
        raw = json.dumps(obj, separators=(',', ':')).encode()
        enc = self.rsa_pubkey.encrypt(
            raw,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                         algorithm=hashes.SHA256(),
                         label=None))
        self.client.send(enc)

    send_message = enc_send    # alias used elsewhere

    # ──────────────────────────────────────────────────────────────
    #                         EVENTS
    # ──────────────────────────────────────────────────────────────
    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.leave_btn.checkForInput(mouse):
                    self.running = False
                    self.manager.set_current_page("MainMenuPage",
                                                  client=self.client,
                                                  key=self.rsa_pubkey)
                    return

                if (not self.disable_clicks and
                        mouse[0] < self.board_px and mouse[1] < self.board_px):
                    col, row = mouse[0] // self.square, mouse[1] // self.square
                    pos = (row, col)
                    if self.selected_piece is None:
                        name, _ = self.chess.get_piece_possible_moves(pos)
                        if name != "None":
                            code = self.chess.get_normal_board()[row][col]
                            if (code.endswith("W") and self.player_color == "white") or \
                               (code.endswith("B") and self.player_color == "black"):
                                self.selected_piece = pos
                    else:
                        if self.try_local_move(self.selected_piece, pos):
                            pass
                        self.selected_piece = None

    # ──────────────────────────────────────────────────────────────
    #                      MOVE HANDLING
    # ──────────────────────────────────────────────────────────────
    def try_local_move(self, frm, to):
        if not self.chess_board.make_move(frm, to, self.current_turn):
            return False

        self.timers[self.current_turn] += self.time_increment

        fen_now = self.chess_board.engine.board_to_fen(
            self.chess_board.get_normal_board(),
            turn=("B" if self.current_turn == "white" else "W"))

        pkt = {
            "type": "move",
            "game_id": self.game_id,
            "from": list(frm),
            "to":   list(to),
            "clock": round(self.timers[self.current_turn], 2),
            "fen":  fen_now,
        }
        self.enc_send(pkt)

        self.current_turn = "black" if self.current_turn == "white" else "white"
        self.disable_clicks = True
        return True

    def apply_move(self, frm, to):
        self.chess_board.make_move(frm, to, self.current_turn)

    # ──────────────────────────────────────────────────────────────
    #                    UPDATE / DRAW
    # ──────────────────────────────────────────────────────────────
    def update(self):
        now = pygame.time.get_ticks()
        dt = (now - self.last_ticks) / 1000
        self.last_ticks = now
        if self.player_color == self.current_turn and not self.disable_clicks:
            self.timers[self.player_color] = max(0, self.timers[self.player_color] - dt)

    def draw(self):
        th = self.THEMES[self.game_state.selected_theme]
        self.screen.fill(th["bg"])
        self.draw_board()
        self.draw_pieces()

        # highlight
        if self.selected_piece:
            r, c = self.selected_piece
            pygame.draw.rect(self.screen, (0, 255, 0),
                             (c * self.square, r * self.square, self.square, self.square), 3)
            _, moves = self.chess.get_piece_possible_moves(self.selected_piece)
            for mr, mc in moves:
                pygame.draw.rect(self.screen, (255, 0, 0),
                                 (mc * self.square, mr * self.square, self.square, self.square), 3)

        # clocks & info
        for i, col in enumerate(("white", "black")):
            t = int(self.timers[col])
            txt = f"{col.capitalize()}: {t // 60:02}:{t % 60:02}"
            surf = self.timer_font.render(txt, True, th["text"])
            self.screen.blit(surf, (820, 50 + i * 40))

        side = self.timer_font.render(f"You are {self.player_color.capitalize()}",
                                      True, th["text"])
        self.screen.blit(side, (820, 140))

        # leave button
        self.leave_btn.changeColor(pygame.mouse.get_pos())
        self.leave_btn.update(self.screen)

    # ---------- draw helpers ----------
    def draw_board(self):
        for r in range(8):
            for c in range(8):
                col = self.light if (r + c) % 2 == 0 else self.dark
                pygame.draw.rect(self.screen, col,
                                 (c * self.square, r * self.square, self.square, self.square))

    def draw_pieces(self):
        board = self.chess.get_normal_board()
        for r in range(8):
            for c in range(8):
                code = board[r][c]
                key = self.map_piece(code)
                if key in self.piece_images:
                    self.screen.blit(self.piece_images[key],
                                     (c * self.square, r * self.square))

    @staticmethod
    def load_imgs(folder):
        imgs = {}
        for col in ("white", "black"):
            for name in ("king", "queen", "rook", "bishop", "knight", "pawn"):
                path = os.path.join(folder, f"{col}_{name}.png")
                if os.path.exists(path):
                    img = pygame.transform.scale(pygame.image.load(path), (100, 100))
                    imgs[f"{col}_{name}"] = img
        return imgs

    @staticmethod
    def map_piece(code):
        if not code:
            return None
        col = "white" if code.endswith("W") else "black"
        base = code[:-1].lower().replace("pown", "pawn")
        return f"{col}_{base}"

    # ---------- clean-up ----------
    def on_destroy(self):
        self.running = False
