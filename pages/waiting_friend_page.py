import pygame, json, select
from CTkMessagebox import CTkMessagebox
from frames.assets.button import Button
from base_page import BasePage


class WaitingPageFriend(BasePage):
    DOT_INTERVAL = 700      # ms between “…” animation steps
    SOCKET_POLL  = 0        # non-blocking select()

    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client, self.key = client, key
        self.counter, self.last = 1, pygame.time.get_ticks()
        self.partial = ""     # buffer for split JSON packets

        self.cancel_btn = Button(
            image=None, pos=(640, 620), text_input="CANCEL",
            font=self.get_font("frames/assets/font.ttf", 50),
            base_color="White", hovering_color="Green")

    # ───────── helpers ─────────
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    @staticmethod
    def split_json(stream: str):
        """Extract consecutive JSON objects from *stream*."""
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

    # ───────── pygame loop ─────────
    def handle_events(self, events):
        if any(e.type == pygame.MOUSEBUTTONDOWN and
               self.cancel_btn.checkForInput(pygame.mouse.get_pos())
               for e in events):
            self.manager.set_current_page("ProfilePage",
                                          self.client, key=self.key)

    def update(self):
        # animate the “…” every DOT_INTERVAL ms
        if pygame.time.get_ticks() - self.last > self.DOT_INTERVAL:
            self.counter = self.counter % 3 + 1
            self.last = pygame.time.get_ticks()

        # non-blocking read from socket
        rdy, _, _ = select.select([self.client], [], [], self.SOCKET_POLL)
        if not rdy:
            return

        chunk = self.client.recv(4096)
        if not chunk:         # peer closed?
            return
        self.partial += chunk.decode("utf-8", "replace")

        packets, idx = self.split_json(self.partial)
        self.partial = self.partial[idx:]        # keep any leftovers

        for pkt in packets:
            # ←― accept both spellings
            if pkt.get("type") in ("start_game", "game_start"):
                gs = self.game_state
                gs.selected_time_format = pkt["time_format"]
                gs.game_id              = pkt["game_id"]
                gs.my_color             = pkt["color"]

                self.manager.set_current_page(
                    "GameBoardPage", self.client,
                    selected_time_format=pkt["time_format"],
                    key=self.key,
                    player_color=pkt["color"],
                    current_turn="white",
                    game_id=pkt["game_id"])
                return

            if pkt.get("type") == "error":
                CTkMessagebox(title="Server error",
                              message=pkt.get("msg", "Unknown error"),
                              icon="cancel")
                self.manager.set_current_page("ProfilePage",
                                              self.client, key=self.key)
                return

    def draw(self):
        theme = [
            {"bg": (0, 0, 0),   "text": (255, 255, 255)},   # Dark
            {"bg": (255, 255, 255), "text": (0, 0, 0)},     # Light
            {"bg": (0, 70, 160), "text": (255, 255, 255)}   # Blue
        ][self.game_state.selected_theme]
        self.screen.fill(theme["bg"])

        inviter = (self.game_state.is_inviter is True)
        dots = "." * self.counter
        if inviter:
            friend = self.game_state.friend_name_to_invite or "???"
            msg = f"Waiting for {friend} to accept{dots}"
        else:
            msg = f"Setting up the game{dots}"

        font30 = self.get_font("frames/assets/font.ttf", 30)
        surf   = font30.render(msg, True, theme["text"])
        self.screen.blit(surf, surf.get_rect(center=(640, 260)))

        # show extra details only to the inviter
        if inviter:
            font25 = self.get_font("frames/assets/font.ttf", 25)
            for i, txt in enumerate((
                f"Time Format: {self.game_state.selected_time_format}",
                f"Game Type:  {self.game_state.selected_game_type}"
            )):
                s = font25.render(txt, True, theme["text"])
                self.screen.blit(s, s.get_rect(center=(640, 360 + i * 40)))

        self.cancel_btn.changeColor(pygame.mouse.get_pos())
        self.cancel_btn.update(self.screen)
