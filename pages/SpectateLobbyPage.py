import pygame, threading, time, json
from frames.assets.button import Button
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class SpectateLobbyPage(BasePage):
    """Shows a live list of games; click one → start spectating."""

    REFRESH_SEC = 3      # poll interval
    LIST_TOP   = 260     # y-pos where the list starts
    ROW_H      = 50      # row height

    # ──────────────────────────────────────────────────────────────
    #                            INIT
    # ──────────────────────────────────────────────────────────────
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client  = client
        self.rsa_key = key

        # fonts
        self.font_30 = pygame.font.SysFont(None, 30)
        self.font_25 = pygame.font.SysFont(None, 25)
        self.font_20 = pygame.font.SysFont(None, 20)

        # UI buttons
        self.refresh_btn = Button(None, (250, 200), "Refresh",
                                  self.font_30, "White", "Green")
        self.back_btn = Button(None, (1030, 690), "BACK",
                               self.font_30, "White", "Green")

        # state
        self.games        = []
        self.selected_idx = None
        self.partial      = ""
        self.running      = True

        # background polling thread
        threading.Thread(target=self._poll_loop, daemon=True).start()

        # FIRST request immediately
        self._enc_send({"type": "list_games"})

    # ──────────────────────────────────────────────────────────────
    #                      NETWORK HELPERS
    # ──────────────────────────────────────────────────────────────
    def _enc_send(self, obj: dict):
        """Encrypt & send a packet; swallow broken sockets."""
        try:
            raw = json.dumps(obj, separators=(',', ':')).encode()
            enc = self.rsa_key.encrypt(
                raw,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                             algorithm=hashes.SHA256(), label=None))
            self.client.send(enc)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            self.running = False   # stop polling loop

    def _poll_loop(self):
        t_next = time.time() + self.REFRESH_SEC
        while self.running:
            if time.time() >= t_next:
                self._enc_send({"type": "list_games"})
                t_next = time.time() + self.REFRESH_SEC
            time.sleep(0.1)
            self._receive_packets()

    def _receive_packets(self):
        try:
            self.client.setblocking(False)
            data = self.client.recv(4096)
        except (BlockingIOError, ConnectionAbortedError, ConnectionResetError):
            data = b""
        finally:
            self.client.setblocking(True)

        if not data:
            return
        self.partial += data.decode("utf-8", "replace")
        objs, idx = self._parse_multi_json(self.partial)
        self.partial = self.partial[idx:]
        for obj in objs:
            self._handle_msg(obj)

    @staticmethod
    def _parse_multi_json(s):
        dec, out, i, n = json.JSONDecoder(), [], 0, len(s)
        while i < n:
            while i < n and s[i].isspace():
                i += 1
            if i >= n:
                break
            try:
                o, j = dec.raw_decode(s, i)
                out.append(o)
                i = j
            except json.JSONDecodeError:
                break
        return out, i

    # ──────────────────────────────────────────────────────────────
    #                        MESSAGE HANDLERS
    # ──────────────────────────────────────────────────────────────
    def _handle_msg(self, msg):
        t = msg.get("type")
        if t == "games_list":
            self.games = msg.get("games", [])
        elif t == "spectate_accept" and msg.get("status") == "OK":
            self.manager.set_current_page(
                "SpectateGamePage", self.client,
                key=self.rsa_key,
                game_id=msg["game_id"],
                fen=msg["fen"],
                turn=msg["color_to_move"]
            )

    # ──────────────────────────────────────────────────────────────
    #                           EVENTS
    # ──────────────────────────────────────────────────────────────
    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.back_btn.checkForInput(mouse):
                    self.running = False
                    self.manager.set_current_page("PlayPage",
                                                  self.client, key=self.rsa_key)
                    return
                if self.refresh_btn.checkForInput(mouse):
                    self._enc_send({"type": "list_games"})

                row = self._row_from_mouse(mouse)
                if row is not None and row < len(self.games):
                    self.selected_idx = row
                    self._enc_send({"type": "spectate_request",
                                    "game_id": self.games[row]["game_id"]})

    def _row_from_mouse(self, mouse):
        x, y = mouse
        if 150 <= x <= 1130 and y >= self.LIST_TOP:
            return (y - self.LIST_TOP) // self.ROW_H
        return None

    # ──────────────────────────────────────────────────────────────
    #                         DRAW
    # ──────────────────────────────────────────────────────────────
    def draw(self):
        theme = [
            {"bg": (0, 0, 0), "text": (255, 255, 255)},
            {"bg": (255, 255, 255), "text": (0, 0, 0)},
            {"bg": (0, 70, 160), "text": (255, 255, 255)}
        ][self.game_state.selected_theme]
        self.screen.fill(theme["bg"])

        title = self.font_30.render("Live Games", True, theme["text"])
        self.screen.blit(title, title.get_rect(center=(640, 150)))

        headers, xs = ["White", "Black", "Time", "Game ID"], [200, 450, 700, 950]
        for h, x in zip(headers, xs):
            surf = self.font_25.render(h, True, theme["text"])
            self.screen.blit(surf, surf.get_rect(center=(x, self.LIST_TOP - 30)))

        for idx, g in enumerate(self.games):
            y = self.LIST_TOP + idx * self.ROW_H
            if idx == self.selected_idx:
                pygame.draw.rect(self.screen, (100, 100, 100),
                                 pygame.Rect(150, y, 960, self.ROW_H))
            row_txt = [g.get("white", "-"), g.get("black", "-"),
                       g.get("time_format", "-"), g.get("game_id", "-")]
            for txt, x in zip(row_txt, xs):
                self.screen.blit(
                    self.font_20.render(str(txt), True, theme["text"]),
                    (x - 50, y + 14))

        for btn in (self.refresh_btn, self.back_btn):
            btn.changeColor(pygame.mouse.get_pos())
            btn.update(self.screen)

    # ──────────────────────────────────────────────────────────────
    def update(self):
        pass

    def on_destroy(self):
        self.running = False
