import pygame
import re
from termcolor import colored

from frames.assets.button import Button
from frames.assets.textBoxInput import TextInputBox

from helper import Helper

from base_page import BasePage


import json

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

class ChangePasswordPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)

        self.key = key
        
        self.client = client
        self.font_30 = pygame.font.SysFont(None, 30)
        self.old_password_box = TextInputBox(600, 250, 400, 50, self.font_30)
        self.new_password_box = TextInputBox(600, 350, 400, 50, self.font_30)
        self.confirm_password_box = TextInputBox(600, 450, 400, 50, self.font_30)
        self.input_boxes = [self.old_password_box, self.new_password_box, self.confirm_password_box]
        self.error_message = ""

        self.change_button = Button(
            image=None, pos=(640, 550),
            text_input="Change Password",
            font=pygame.font.SysFont(None, 45),
            base_color="White",
            hovering_color="Green"
        )
        self.back_button = Button(
            image=None, pos=(640, 680),
            text_input="BACK",
            font=pygame.font.SysFont(None, 45),
            base_color="White",
            hovering_color="Green"
        )
    
    def send_message(self, message):
        message = json.dumps(message)
        encrypted_message = self.encrypt_message(message)
        self.client.send(encrypted_message)

    def encrypt_message(self, message):
        """Encrypt a message using the server's public key."""
        return self.key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    
            
    def get_font(self, path, size):
        return pygame.font.Font(path, size)
        
    def info_pass_str(self, password):
        score, entropy = self.estimate_password_strength(password)
        if score > 10:
            print(colored("PERFECT PASSWORD", 'green'))
        elif 5 < score <= 10:
            print(colored("THE PASSWORD IS OK", 'yellow'))
        else:
            print(colored("THE PASSWORD IS WEAK", 'red'))
    
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


    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("OptionsPage", self.client,  key = self.key)
                if self.change_button.checkForInput(mouse_pos):
                    old_pass = self.old_password_box.text
                    new_pass = self.new_password_box.text
                    confirm_pass = self.confirm_password_box.text

                    if not old_pass or not new_pass or not confirm_pass:
                        self.error_message = "All fields are required!"
                    elif new_pass != confirm_pass:
                        self.error_message = "New passwords do not match!"
                    else:
                        self.info_pass_str(new_pass)



                        message = {"type": "password_change", "old_password" : old_pass ,"new_password" : new_pass}
                        self.send_message(message)

                        acc = self.recive_message()
                        if acc['status'] == "OK":
                            self.error_message = "Password Changed Successfully!"
                        else:
                            self.error_message = "Old password incorrect."



                        for box in self.input_boxes:
                            box.text = ""
                            box.txt_surface = self.font_30.render("", True, box.color)
            for box in self.input_boxes:
                box.handle_event(event)

    def recive_message(self):
        message = self.client.recv(4096).decode()
        return json.loads(message)

    def update(self):
        for box in self.input_boxes:
            box.update()

    def draw(self):

        THEMES = [
            {
                "bg": (0, 0, 0),          
                "text": (255, 255, 255)
            },
            {
                "bg": (255, 255, 255),
                "text": (0, 0, 0)
            },
            {
                "bg": (0, 70, 160),
                "text": (255, 255, 255)
            }
        ]

        
        mouse_pos = pygame.mouse.get_pos()
        theme_index = self.game_state.selected_theme
        theme = THEMES[theme_index]
        self.screen.fill(theme["bg"])

        if theme_index == 1:
            self.change_button.base_color = (50, 50, 50)
            self.change_button.hovering_color = (100, 100, 100)
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
        else:
            self.change_button.base_color = "White"
            self.change_button.hovering_color = "Green"
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"

        change_pass_text = pygame.font.SysFont(None, 45).render("Change Password", True, theme["text"])
        change_pass_rect = change_pass_text.get_rect(center=(640, 100))
        self.screen.blit(change_pass_text, change_pass_rect)

        font_30 = self.font_30
        old_pass_label = font_30.render("Old Password:", True, theme["text"])
        old_pass_rect = old_pass_label.get_rect(center=(320, 275))
        self.screen.blit(old_pass_label, old_pass_rect)

        new_pass_label = font_30.render("New Password:", True, theme["text"])
        new_pass_rect = new_pass_label.get_rect(center=(320, 375))
        self.screen.blit(new_pass_label, new_pass_rect)

        confirm_pass_label = font_30.render("Confirm Password:", True, theme["text"])
        confirm_pass_rect = confirm_pass_label.get_rect(center=(320, 475))
        self.screen.blit(confirm_pass_label, confirm_pass_rect)

        for box in self.input_boxes:
            box.draw(self.screen)

        self.change_button.changeColor(mouse_pos)
        self.change_button.update(self.screen)

        self.back_button.changeColor(mouse_pos)
        self.back_button.update(self.screen)

        if self.error_message:
            error_text = font_30.render(self.error_message, True, (255, 0, 0))
            error_rect = error_text.get_rect(center=(640, 620))
            self.screen.blit(error_text, error_rect)