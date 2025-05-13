import pygame, json
from frames.assets.button import Button
from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from frames.assets.textBoxInput import TextInputBox
from CTkMessagebox import CTkMessagebox


class SendGameRequestPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client = client
        self.key    = key
        self.font   = pygame.font.Font("frames/assets/font.ttf", 28)

        self.name_box = TextInputBox(440, 300, 400, 40, self.font, "Friend username")
        self.time_box = TextInputBox(440, 380, 400, 40, self.font, "Time (e.g. 5+3)")
        self.send_btn = Button(None, (640, 460), "SEND", self.font, "White", "Green")
        self.back_btn = Button(None, (640, 540), "BACK", self.font, "White", "Green")

    # networking helpers (encrypt on send, plain on recv)
    def _send(self, obj):
        enc = self.key.encrypt(json.dumps(obj).encode(),
                               padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                            algorithm=hashes.SHA256(),
                                            label=None))
        self.client.send(enc)

    def _recv_ack(self):
        pkt = json.loads(self.client.recv(4096).decode())
        CTkMessagebox(title="Game request",
                      message=pkt.get("msg", "Unknown"),
                      icon="check" if pkt.get("success") else "cancel")

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.send_btn.checkForInput(mouse):
                    self._send({"type": "send_game_request",
                                "to": self.name_box.text,
                                "time_format": self.time_box.text})
                    self._recv_ack()
                if self.back_btn.checkForInput(mouse):
                    self.manager.set_current_page("ProfilePage",
                                                  self.client, key=self.key)
            self.name_box.handle_event(e)
            self.time_box.handle_event(e)

    def draw(self):
        self.screen.fill((0, 0, 0))
        self.name_box.draw(self.screen)
        self.time_box.draw(self.screen)
        for b in (self.send_btn, self.back_btn):
            b.changeColor(pygame.mouse.get_pos())
            b.update(self.screen)