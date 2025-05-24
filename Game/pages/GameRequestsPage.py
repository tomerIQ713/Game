import pygame, json, select
from CTkMessagebox import CTkMessagebox

from frames.assets.button import Button
from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class GameRequestsPage(BasePage):
    """Inbox of incoming friend-game requests – now completely non-blocking."""

    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client, self.key = client, key
        self.font = self.get_font("frames/assets/font.ttf", 28)

        self.awaiting_list = True        
        self.partial       = ""          

        self.notice, self.notice_time = "", 0
        self.pending  = []              
        self.buttons  = []             

        self._ask_server_for_list()

        self.back_btn = Button(None, (640, 680), "BACK",
                               self.font, "White", "Green")

    def get_font(self, path, size): return pygame.font.Font(path, size)

    def _send_enc(self, obj):
        raw = json.dumps(obj, separators=(',', ':')).encode()
    
        if self.key is not None:
            enc = self.key.encrypt(
                raw,
                padding.OAEP(
                    mgf=padding.MGF1(hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                )
            )
            self.client.send(enc)
        else:
            self.client.send(raw)
    

    def _ask_server_for_list(self):
        self._send_enc({"type": "list_game_requests"})
        self.client.setblocking(False)        

    def _rebuild_buttons(self):
        self.buttons.clear()
        y = 260
        for req in self.pending:
            yes = Button(None, (800, y), "✔", self.font, "White", "Green")
            no  = Button(None, (870, y), "✖", self.font, "White", "Red")
            self.buttons.append((req["sender"], req["time_format"], yes, no))
            y += 60

    @staticmethod
    def _split_json(stream: str):
        dec, out, i, n = json.JSONDecoder(), [], 0, len(stream)
        while i < n:
            while i < n and stream[i].isspace(): i += 1
            if i >= n: break
            try:
                obj, j = dec.raw_decode(stream, i)
                out.append(obj); i = j
            except json.JSONDecodeError:
                break
        return out, i

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:

                if self.back_btn.checkForInput(mouse):
                    self.manager.set_current_page("ProfilePage",
                                                  self.client, key=self.key)
                    return

                for sender, tf, ybtn, nbtn in list(self.buttons):
                    if ybtn.checkForInput(mouse):
                        self._reply(sender, tf, True); return
                    if nbtn.checkForInput(mouse):
                        self._reply(sender, tf, False); return

    def _reply(self, sender, tfmt, accept):
        self._send_enc({"type": "respond_game_request",
                        "from_user": sender, "accept": accept})

        if accept:
            gs = self.game_state
            gs.friend_name_to_invite = sender
            gs.selected_time_format  = tfmt
            gs.selected_game_type    = "Play a friend"
            gs.is_inviter            = False  

            self.manager.set_current_page("WaitingPageFriend",
                                          self.client, key=self.key)
        else:
            self.notice = "Rejected!"
            self.notice_time = pygame.time.get_ticks()

    def update(self):
        if self.notice and pygame.time.get_ticks() - self.notice_time > 2000:
            self.notice = ""

        if self.awaiting_list:
            rdy, _, _ = select.select([self.client], [], [], 0)
            if not rdy:
                return
            try:
                chunk = self.client.recv(4096).decode("utf-8", "replace")
                print("[DEBUG] raw chunk:", chunk)      
            except BlockingIOError:
                return

            self.partial += chunk
            packets, idx = self._split_json(self.partial)
            self.partial = self.partial[idx:]

            for pkt in packets:
                if pkt.get("type") == "game_requests":
                    self.pending = pkt.get("list", [])
                    self._rebuild_buttons()
                    self.awaiting_list = False   

    def draw(self):
        th = [{"bg": (0,0,0), "text": (255,255,255)},
              {"bg": (255,255,255), "text": (0,0,0)},
              {"bg": (0,70,160), "text": (255,255,255)}][self.game_state.selected_theme]
        self.screen.fill(th["bg"])

        title = self.font.render("Incoming game requests", True, th["text"])
        self.screen.blit(title, title.get_rect(center=(640, 180)))

        mouse = pygame.mouse.get_pos()

        if not self.pending and not self.awaiting_list:
            empty = self.font.render("— none —", True, th["text"])
            self.screen.blit(empty, empty.get_rect(center=(640, 300)))

        base, hover = ((50,50,50),(100,100,100)) \
            if self.game_state.selected_theme == 1 else ("White","Green")

        for sender, tf, ybtn, nbtn in self.buttons:
            txt = self.font.render(f"{sender} – {tf}", True, th["text"])
            self.screen.blit(txt, (320, ybtn.rect.centery - txt.get_height()//2))

            for b in (ybtn, nbtn):
                b.base_color, b.hovering_color = base, hover
                b.changeColor(mouse); b.update(self.screen)

        self.back_btn.base_color, self.back_btn.hovering_color = base, hover
        self.back_btn.changeColor(mouse); self.back_btn.update(self.screen)

        if self.awaiting_list:
            dots = "." * ((pygame.time.get_ticks()//300)%4)
            msg  = self.font.render(f"Contacting server{dots}", True, th["text"])
            self.screen.blit(msg, msg.get_rect(center=(640, 240)))

        if self.notice:
            n = self.font.render(self.notice, True, th["text"])
            self.screen.blit(n, n.get_rect(center=(640, 220)))
