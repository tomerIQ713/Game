import pygame
import sys
import os
import re
from termcolor import colored
from CTkMessagebox import CTkMessagebox

from base_page import BasePage
from frames.assets.button import Button
from frames.assets.textBoxInput import TextInputBox

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

import socket
import json
import hashlib

class LoginPage(BasePage):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = pygame.font.SysFont(None, 30)
        self.username_box = TextInputBox(600, 250, 400, 50, self.font)
        self.password_box = TextInputBox(600, 350, 400, 50, self.font)
        self.input_boxes = [self.username_box, self.password_box]
        self.error_message = ""

        self.client = socket.socket()
        print(1)
        self.client.connect(("192.168.1.201", 5555))
        print(2)
        self.public_key = serialization.load_pem_public_key(self.client.recv(4096))

        self.login_button = Button(
            image=None, pos=(640, 680),
            text_input="LOGIN", font=pygame.font.SysFont(None, 45),
            base_color="White", hovering_color="Green"
        )

    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for e in events:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.login_button.checkForInput(mouse):
                    self.try_login()
            for box in self.input_boxes:
                box.handle_event(e)
                
    def try_login(self):
        if not self.username_box.text or not self.password_box.text:
            self.error_message = "All fields are required!"
            return

        msg = {"type": "login_request",
               "username": self.username_box.text,
               "password": self.password_box.text}

        payload = json.dumps(msg, separators=(',', ':')).encode()
        cipher = self.public_key.encrypt(
            payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                         algorithm=hashes.SHA256(),
                         label=None)
        )
        self.client.send(cipher)

        reply = self.client.recv(1024).decode("utf-8")
        if not reply:
            self.error_message = "Server closed connection"
            return

        resp = json.loads(reply)
        if resp.get("status") == "OK":
            self.manager.set_current_page("MainMenuPage",
                                          client=self.client,
                                          key=self.public_key)
        else:
            self.error_message = resp.get("reason", "Login failed")

    def send_message(self, message):
        """
        JSON-encode and then encrypt with the server's public key.
        """
        message_str = json.dumps(message)
        encrypted_message = self.encrypt_message(message_str)
        self.client.send(encrypted_message)

    def encrypt_message(self, message):
        """
        Encrypt a message using the server's public key.
        """
        return self.public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def load_public_key(self, public_pem):
        """
        Load the server's public key from PEM format.
        """
        self.public_key = serialization.load_pem_public_key(public_pem)

    def get_public_key(self):
        public_pem = self.client.recv(4096)
        self.load_public_key(public_pem)

    def is_valid_username(self, username):
        """
        Optional helper to check username format.
        """
        if not username:
            return False
        if username[0].isdigit():
            return False
        if not re.match(r'^[a-zA-Z0-9 .\-\'_@]+$', username):
            return False
        return True

    def estimate_password_strength(self, password):
        """
        Example password strength estimation (not super robust).
        """
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

    def info_pass_str(self, password):
        """
        Just prints color-coded message about password strength.
        """
        score, entropy = self.estimate_password_strength(password)
        if score > 10:
            print(colored("PERFECT PASSWORD", 'green'))
        elif 5 < score <= 10:
            print(colored("THE PASSWORD IS OK", 'yellow'))
        else:
            print(colored("THE PASSWORD IS WEAK", 'red'))

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
        theme_index = self.game_state.selected_theme
        theme = THEMES[theme_index]

        if theme_index == 1:
            self.login_button.base_color = (50, 50, 50)
            self.login_button.hovering_color = (100, 100, 100)
        else:
            self.login_button.base_color = "White"
            self.login_button.hovering_color = "Green"

        self.screen.fill(theme["bg"])
        main_surf = pygame.font.SysFont(None, 45).render(
            "Login | Signup", True, theme["text"]
        )
        main_rect = main_surf.get_rect(center=(640, 100))
        self.screen.blit(main_surf, main_rect)

        font_small = pygame.font.SysFont(None, 30)

        uname_label = font_small.render("Username:", True, theme["text"])
        uname_rect = uname_label.get_rect(center=(320, 275))
        self.screen.blit(uname_label, uname_rect)

        pass_label = font_small.render("Password:", True, theme["text"])
        pass_rect = pass_label.get_rect(center=(320, 375))
        self.screen.blit(pass_label, pass_rect)

        for box in self.input_boxes:
            box.draw(self.screen)

        self.login_button.changeColor(pygame.mouse.get_pos())
        self.login_button.update(self.screen)

        if self.error_message:
            err_font = pygame.font.SysFont(None, 20)
            err_surf = err_font.render(self.error_message, True, (255, 0, 0))
            err_rect = err_surf.get_rect(center=(640, 550))
            self.screen.blit(err_surf, err_rect)
