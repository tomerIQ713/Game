import pygame
import sys
import os
import re
from termcolor import colored
from CTkMessagebox import CTkMessagebox

from frames.assets.button import Button, RadioButton
from frames.assets.textBoxInput import TextInputBox

from chess_board import ChessBoard
from player import Player
from helper import Helper

from base_page import BasePage

import json

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes

class ProfilePage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        
        self.key = key
        self.client = client
        self.add_friend_btn = Button(
            image=None, pos=(640, 600),
            text_input="Add a friend", font=self.get_font("frames/assets/font.ttf", 30),
            base_color="White", hovering_color="Green"
        )
        self.back_button = Button(
            image=None, pos=(640, 680),
            text_input="BACK", font=self.get_font("frames/assets/font.ttf", 45),
            base_color="White", hovering_color="Green"
        )

        message = {"type" : "view_profile"}
        self.send_message(message)

        self.data = self.recive_message()
        print(self.data)



    
    def recive_message(self):
        message = self.client.recv(4096).decode()
        return json.loads(message)
    

    
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("OptionsPage", self.client,  key = self.key)
                elif self.add_friend_btn.checkForInput(mouse_pos):
                    self.manager.set_current_page("AddFriendPage", self.client,  key = self.key)

    def update(self):
        pass

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
        self.screen.fill(theme["bg"])

        if theme_index == 1:
            self.add_friend_btn.base_color = (50, 50, 50)
            self.add_friend_btn.hovering_color = (100, 100, 100)
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
        else:
            self.add_friend_btn.base_color = "White"
            self.add_friend_btn.hovering_color = "Green"
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"

        profile_text = self.get_font("frames/assets/font.ttf", 45).render("Profile", True, theme["text"])
        profile_rect = profile_text.get_rect(center=(640, 100))
        self.screen.blit(profile_text, profile_rect)

        text1 = f"Games played: {self.data['games_played']}"
        profile_info1 = self.get_font("frames/assets/font.ttf", 20).render(text1, True, theme["text"])
        profile_text_rect1 = profile_info1.get_rect(center=(640, 200))
        self.screen.blit(profile_info1, profile_text_rect1)

        text2 = f"Elo: {self.data['elo']}"
        profile_info2 = self.get_font("frames/assets/font.ttf", 20).render(text2, True, theme["text"])
        profile_text_rect2 = profile_info2.get_rect(center=(640, 240))
        self.screen.blit(profile_info2, profile_text_rect2)


        text3 = f"Score as white(win-draw-loss): {self.data['as_white']}"
        profile_info3 = self.get_font("frames/assets/font.ttf", 20).render(text3, True, theme["text"])
        profile_text_rect3 = profile_info3.get_rect(center=(640, 280))
        self.screen.blit(profile_info3, profile_text_rect3)

        text4 = f"Score as black(win-draw-loss): {self.data['as_black']}"
        profile_info4 = self.get_font("frames/assets/font.ttf", 20).render(text4, True, theme["text"])
        profile_text_rect4 = profile_info4.get_rect(center=(640, 320))
        self.screen.blit(profile_info4, profile_text_rect4)

        text5 = f"Friends: {self.data['friends']}"
        profile_info5 = self.get_font("frames/assets/font.ttf", 20).render(text5, True, theme["text"])
        profile_text_rect5 = profile_info5.get_rect(center=(640, 360))
        self.screen.blit(profile_info5, profile_text_rect5)


        self.add_friend_btn.changeColor(pygame.mouse.get_pos())
        self.add_friend_btn.update(self.screen)

        self.back_button.changeColor(pygame.mouse.get_pos())
        self.back_button.update(self.screen)
    
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