import pygame, json
from frames.assets.button import Button
from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

class FriendRequestsPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client = client
        self.key    = key
        self.font   = pygame.font.Font("frames/assets/font.ttf", 28)

        self.pending = []
        self._refresh()

    def _send(self, obj):   
        data = json.dumps(obj).encode()
        enc  = self.key.encrypt(data,
                                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                             algorithm=hashes.SHA256(),
                                             label=None))
        self.client.send(enc)

    def _recv(self):
        """Receive a plain-JSON packet sent by the server."""
        raw = self.client.recv(4096)
        return json.loads(raw.decode())      

    def _refresh(self):
        self._send({"type": "list_friend_requests"})
        pkt = self._recv()
        self.pending = pkt.get("list", [])

        self.buttons = []
        y = 220
        for name in self.pending:
            self.buttons.append((
                name,
                Button(image=None, pos=(500, y),
                       text_input="Accept", font=self.font,
                       base_color="White", hovering_color="Green"),
                Button(image=None, pos=(780, y),
                       text_input="No.", font=self.font,
                       base_color="White", hovering_color="Red")
            ))
            y += 70

        self.back_btn = Button(image=None, pos=(640, 680),
                               text_input="BACK", font=self.font,
                               base_color="White", hovering_color="Green")

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                for name, yes_btn, no_btn in self.buttons:
                    if yes_btn.checkForInput(mouse):
                        self._reply(name, True)
                    if no_btn.checkForInput(mouse):
                        self._reply(name, False)
                if self.back_btn.checkForInput(mouse):
                    self.manager.set_current_page("ProfilePage",
                                                  self.client, key=self.key)

    def _reply(self, from_user, accept):
        self._send({"type": "respond_friend_request",
                    "from_user": from_user,
                    "accept": accept})
        self._refresh()       

    def draw(self):
        self.manager.screen.fill((0, 0, 0))
        title = self.font.render("Pending friend requests", True, "White")
        self.manager.screen.blit(title, (640 - title.get_width()//2, 140))

        for name, yes_btn, no_btn in self.buttons:
            lbl = self.font.render(name, True, "White")
            self.manager.screen.blit(lbl, (350, yes_btn.rect.centery - lbl.get_height()//2))
            yes_btn.update(self.manager.screen)
            no_btn.update(self.manager.screen)

        self.back_btn.update(self.manager.screen)
