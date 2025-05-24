import pygame, re, json, socket
from termcolor import colored
from frames.assets.button import Button
from frames.assets.textBoxInput import TextInputBox
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

class ChangePasswordPage(BasePage):
    """
    Screen for changing the logged-in user’s password.
    Sends a `password_change` packet and displays success/error.
    """

    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client        = client
        self.key           = key
        self.error_message = ""

        self.font_30 = pygame.font.SysFont(None, 30)

        self.old_password_box     = TextInputBox(600, 250, 400, 50, self.font_30)
        self.new_password_box     = TextInputBox(600, 350, 400, 50, self.font_30)
        self.confirm_password_box = TextInputBox(600, 450, 400, 50, self.font_30)
        self.input_boxes = [
            self.old_password_box,
            self.new_password_box,
            self.confirm_password_box
        ]

        self.change_button = Button(image=None, pos=(640, 550), text_input="Change Password",
                                     font=pygame.font.SysFont(None, 45), base_color="White", hovering_color="Green")
        self.back_button   = Button(image=None, pos=(640, 680), text_input="BACK",
                                     font=pygame.font.SysFont(None, 45), base_color="White", hovering_color="Green")

    def send_message(self, message: dict):
        """
        JSON-encode `message` and send it, RSA-encrypted if `self.key` is set.
        """
        raw = json.dumps(message, separators=(',', ':')).encode('utf-8')
        try:
            if self.key:
                raw = self.key.encrypt(
                    raw,
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                 algorithm=hashes.SHA256(), label=None)
                )
            self.client.sendall(raw)
        except OSError:
            self.error_message = "Network error – could not send."

    def recive_message(self) -> dict:
        """
        Receive a JSON response (plain text) from the server.
        Returns an empty dict on error.
        """
        try:
            data = self.client.recv(4096)
            return json.loads(data.decode('utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("OptionsPage", self.client, key=self.key)
                    return

                if self.change_button.checkForInput(mouse_pos):
                    old_pass     = self.old_password_box.text
                    new_pass     = self.new_password_box.text
                    confirm_pass = self.confirm_password_box.text

                    # validation
                    if not old_pass or not new_pass or not confirm_pass:
                        self.error_message = "All fields are required!"
                    elif new_pass != confirm_pass:
                        self.error_message = "New passwords do not match!"
                    else:
                        score, _ = self.estimate_password_strength(new_pass)
                        if score <= 5:
                            print("Password is too weak!")

                        packet = {
                            "type":        "password_change",
                            "old_password": old_pass,
                            "new_password": new_pass
                        }
                        self.send_message(packet)

                        acc = self.recive_message()
                        if acc.get('status') == "OK":
                            self.error_message = "Password changed successfully!"
                        else:
                            reason = acc.get('reason') or "Password change failed!"
                            self.error_message = reason

                        for box in self.input_boxes:
                            box.text = ""
                            box.txt_surface = self.font_30.render("", True, box.color)

            for box in self.input_boxes:
                box.handle_event(event)

    def update(self):
        for box in self.input_boxes:
            box.update()

    def estimate_password_strength(self, password):
        length_points = min(10, len(password))
        variety_points = min(5, len(set(password)))
        pattern_penalty = 0

        if re.match(r'^[a-zA-Z]+$', password):
            pattern_penalty += 5
        if re.match(r'^\d+$', password):
            pattern_penalty += 5
        if re.match(r'^[!@#$%^&*()\-_=+\\|[\]{};:\'",.<>/?`~]+$', password):
            pattern_penalty += 5
        if re.match(r'(\d)\1+$', password):
            pattern_penalty += 5
        if re.match(r'([a-zA-Z])\1+$', password):
            pattern_penalty += 5
        if any(
            ord(password[i]) == ord(password[i+1]) - 1 == ord(password[i+2]) - 2
            for i in range(len(password) - 2)
        ):
            pattern_penalty += 10

        entropy = len(password) * (len(set(password)) ** 2)
        score = max(0, length_points + variety_points - pattern_penalty)
        return score, entropy

    def draw(self):
        self.screen.fill((30, 30, 30))

        title = pygame.font.SysFont(None, 45).render("Change Password", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(640, 150)))

        font = self.font_30
        labels = ["Old Password:", "New Password:", "Confirm Password:"]
        y_pos = [250, 350, 450]
        for txt, y in zip(labels, y_pos):
            surf = font.render(txt, True, (255, 255, 255))
            self.screen.blit(surf, surf.get_rect(center=(320, y+15)))

        for box in self.input_boxes:
            box.draw(self.screen)

        for btn in (self.change_button, self.back_button):
            btn.changeColor(pygame.mouse.get_pos())
            btn.update(self.screen)
            
        if self.error_message:
            err = font.render(self.error_message, True, (255, 80, 80))
            self.screen.blit(err, err.get_rect(center=(640, 600)))