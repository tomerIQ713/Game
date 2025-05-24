
import pygame, json
from frames.assets.button import Button
from frames.assets.textBoxInput import TextInputBox
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class InviteFriendPage(BasePage):
    """
    Page where user types the friend's name and clicks  INVITE.
    Then we switch to WaitingPageFriend.
    """
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client, self.key = client, key

        self.font_20 = pygame.font.Font("frames/assets/font.ttf", 20)
        self.friend_input = TextInputBox(440, 350, 400, 50, self.font_20)
        self.input_boxes = [self.friend_input]

        self.invite_button = Button(
            image=None, pos=(640, 500), text_input="INVITE",
            font=pygame.font.Font("frames/assets/font.ttf", 40),
            base_color="White", hovering_color="Green")
        self.back_button = Button(
            image=None, pos=(640, 600), text_input="BACK",
            font=pygame.font.Font("frames/assets/font.ttf", 40),
            base_color="White", hovering_color="Green")

        self.error_message = ""
        self.status_text  = ""

    def _send_enc(self, obj):
        raw = json.dumps(obj, separators=(',', ':')).encode()
        enc = self.key.encrypt(
            raw,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                         algorithm=hashes.SHA256(),
                         label=None))
        self.client.send(enc)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN:

                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("PlayPage",
                                                  self.client, key=self.key)

                elif self.invite_button.checkForInput(mouse_pos):
                    friend_name = self.friend_input.text.strip()
                    if not friend_name:
                        self.error_message = "Please enter a friend's name!"
                        continue

                    gs = self.game_state
                    gs.friend_name_to_invite = friend_name
                    gs.is_inviter            = True

                    time_fmt = gs.selected_time_format or "Classical: 1 hour"

                    packet = {
                        "type":        "send_game_request",
                        "to":          friend_name,
                        "time_format": time_fmt
                    }
                    print("[DEBUG] sending", packet)
                    self._send_enc(packet)

                    ack = json.loads(self.client.recv(4096).decode())
                    self.status_text = ack.get("msg", "")

                    self.manager.set_current_page("WaitingPageFriend",
                                                  self.client, key=self.key)

            for box in self.input_boxes:
                box.handle_event(ev)

    def update(self):
        for box in self.input_boxes:
            box.update()

    def draw(self):
        theme = [
            {"bg": (0, 0, 0),       "text": (255, 255, 255)},
            {"bg": (255, 255, 255), "text": (0,   0,   0)},
            {"bg": (0, 70, 160),    "text": (255, 255, 255)}
        ][self.game_state.selected_theme]
        self.screen.fill(theme["bg"])

        label = pygame.font.Font("frames/assets/font.ttf", 40).render(
            "Invite a friend", True, theme["text"])
        self.screen.blit(label, label.get_rect(center=(640, 150)))

        instruct = self.font_20.render(
            "Enter the friend's username you want to invite:",
            True, theme["text"])
        self.screen.blit(instruct, instruct.get_rect(center=(640, 300)))

        for box in self.input_boxes:
            box.draw(self.screen)

        for btn in (self.invite_button, self.back_button):
            btn.changeColor(pygame.mouse.get_pos())
            btn.update(self.screen)

        if self.error_message:
            err = self.font_20.render(self.error_message, True, (255, 0, 0))
            self.screen.blit(err, err.get_rect(center=(640, 700)))

        if self.status_text:
            msg = self.font_20.render(self.status_text, True, (220, 50, 50))
            self.screen.blit(msg, msg.get_rect(center=(640, 560)))
