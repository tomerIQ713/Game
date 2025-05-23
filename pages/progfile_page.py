import pygame, json, select
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from frames.assets.button import Button
from base_page import BasePage


class ProfilePage(BasePage):
    """
    User profile screen: shows basic stats and lets the player
    navigate to friend-/game-request pages.
    """

    SOCKET_POLL = 0          # seconds for select(); 0 = non-blocking

    # ───────────────────────────────────────────────────────────
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client, self.key = client, key

        self.data           = None     # filled when server replies
        self.partial_buffer = ""       # holds split / concatenated JSON

        # ── fonts & buttons ─────────────────────────────────────
        f30 = self.get_font("frames/assets/font.ttf", 30)
        f45 = self.get_font("frames/assets/font.ttf", 45)

        self.add_friend_btn = Button(
            image=None, pos=(640, 500),
            text_input="Add a friend", font=f30,
            base_color="White", hovering_color="Green"
        )
        self.req_btn = Button(
            image=None, pos=(640, 560),
            text_input="Friend requests", font=f30,
            base_color="White", hovering_color="Green"
        )
        self.game_req_btn = Button(
            image=None, pos=(640, 620),
            text_input="Game requests", font=f30,
            base_color="White", hovering_color="Green"
        )
        self.back_btn = Button(
            image=None, pos=(640, 700),
            text_input="BACK", font=f45,
            base_color="White", hovering_color="Green"
        )

        # ── ask server for the profile once ─────────────────────
        self._send_enc({"type": "view_profile",
                        "username": self.game_state.username})

    # ────────────────── helpers ────────────────────────────────
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def _send_enc(self, obj: dict):
        """JSON-encode + RSA-encrypt and send to server."""
        plaintext = json.dumps(obj).encode()
        cipher = self.key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.client.send(cipher)

    @staticmethod
    def _split_json(stream: str):
        """Return (objects, next_index) from concatenated JSON text."""
        dec, out, i, n = json.JSONDecoder(), [], 0, len(stream)
        while i < n:
            while i < n and stream[i].isspace():
                i += 1
            if i >= n:
                break
            try:
                obj, j = dec.raw_decode(stream, i)
                out.append(obj)
                i = j
            except json.JSONDecodeError:
                break
        return out, i

    def _read_socket(self):
        """Non-blocking read; fills self.data when profile arrives."""
        rdy, _, _ = select.select([self.client], [], [], self.SOCKET_POLL)
        if not rdy:
            return
        try:
            chunk = self.client.recv(4096)
        except BlockingIOError:
            return
        if not chunk:
            return                                  # socket closed

        self.partial_buffer += chunk.decode("utf-8", "replace")
        packets, idx = self._split_json(self.partial_buffer)
        self.partial_buffer = self.partial_buffer[idx:]

        for p in packets:
            if p.get("type") == "profile_info":
                self.data = p
            if p.get("type") == "error":
                self.data = {"error": p.get("msg", "Unknown")}

    # ───────────────── pygame loop methods ─────────────────────
    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.back_btn.checkForInput(mouse_pos):
                    self.manager.set_current_page("OptionsPage",
                                                  self.client, key=self.key)

                elif self.req_btn.checkForInput(mouse_pos):
                    self.manager.set_current_page("FriendRequestsPage",
                                                  self.client, key=self.key)

                elif self.game_req_btn.checkForInput(mouse_pos):
                    self.manager.set_current_page("GameRequestsPage",
                                                  self.client, key=self.key)

                elif self.add_friend_btn.checkForInput(mouse_pos):
                    self.manager.set_current_page("AddFriendPage",
                                                  self.client, key=self.key)

    def update(self):
        if self.data is None:
            self._read_socket()

    def draw(self):
        THEMES = [
            {"bg": (0, 0, 0),       "text": (255, 255, 255)},  # dark
            {"bg": (255, 255, 255), "text": (0, 0, 0)},        # light
            {"bg": (0, 70, 160),    "text": (255, 255, 255)}   # blue
        ]
        theme = THEMES[self.game_state.selected_theme]
        self.screen.fill(theme["bg"])

        # adapt button colours for light theme
        dark_btn, hover_btn = ((50, 50, 50), (100, 100, 100)) \
                              if self.game_state.selected_theme == 1 \
                              else ("White", "Green")
        for b in (self.add_friend_btn, self.req_btn,
                  self.game_req_btn, self.back_btn):
            b.base_color, b.hovering_color = dark_btn, hover_btn

        # ---- title -------------------------------------------------
        title = self.get_font("frames/assets/font.ttf", 45)\
                .render("Profile", True, theme["text"])
        self.screen.blit(title, title.get_rect(center=(640, 100)))

        # ---- stats -------------------------------------------------
        if self.data is None:
            lines = ["Loading profile …"]
        elif "error" in self.data:
            lines = [self.data["error"]]
        else:
            lines = [
                f"Games played: {self.data.get('games_played', 0)}",
                f"Elo: {self.data.get('elo', '—')}",
                f"Score as white (W-D-L): {self.data.get('as_white', ['?','?','?'])}",
                f"Score as black (W-D-L): {self.data.get('as_black', ['?','?','?'])}",
                f"Friends: {self.data.get('friends', 0)}"
            ]

        font20 = self.get_font("frames/assets/font.ttf", 20)
        for i, txt in enumerate(lines):
            surf = font20.render(str(txt), True, theme["text"])
            self.screen.blit(surf, surf.get_rect(center=(640, 200 + i * 40)))

        # ---- buttons ------------------------------------------------
        mouse_pos = pygame.mouse.get_pos()
        for b in (self.add_friend_btn, self.req_btn,
                  self.game_req_btn, self.back_btn):
            b.changeColor(mouse_pos)
            b.update(self.screen)
