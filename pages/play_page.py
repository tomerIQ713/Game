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

class PlayPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.font_25 = pygame.font.SysFont(None, 25)
        self.font_30 = pygame.font.SysFont(None, 30)
        self.font_50 = pygame.font.SysFont(None, 50)

        self.key = key

        self.client = client

        self.time_format_btns = [
            RadioButton(50, 280, 200, 60, self.font_30, "Classical: 1 hour"),
            RadioButton(50, 360, 200, 60, self.font_30, "Rapid: 30 min"),
            RadioButton(50, 440, 200, 60, self.font_30, "Rapid: 10 min"),
            RadioButton(50, 520, 200, 60, self.font_30, "Blitz: 3 + 1 min"),
            RadioButton(50, 600, 200, 60, self.font_30, "Bullet: 1 + 1 min"),
        ]
        for rb in self.time_format_btns:
            rb.setRadioButtons(self.time_format_btns)
        self.time_format_group = pygame.sprite.Group(self.time_format_btns)

        self.game_type_btns = [
            RadioButton(270, 280, 200, 60, self.font_30, "Random"),
            RadioButton(270, 360, 200, 60, self.font_30, "Play a friend")
        ]
        for rb in self.game_type_btns:
            rb.setRadioButtons(self.game_type_btns)
        self.game_type_group = pygame.sprite.Group(self.game_type_btns)

        self.error_message = ""

        self.start_button = Button(
            image=None, pos=(860, 400),
            text_input="Start", font=self.font_50,
            base_color="White", hovering_color="Green"
        )
        self.back_button = Button(
            image=None, pos=(640, 600),
            text_input="BACK", font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White", hovering_color="Green"
        )

    def get_font(self, path, size):
        return pygame.font.Font(path, size)


    def split_text(self, text, font, max_width):
        words = text.split(' ')
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word + " "
        lines.append(current_line)
        return lines
    
    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.game_state.selected_time_format = next(
                        (rb.get_text() for rb in self.time_format_btns if rb.clicked), None
                    )
                    self.game_state.selected_game_type = next(
                        (rb.get_text() for rb in self.game_type_btns if rb.clicked), None
                    )
                    self.manager.set_current_page("MainMenuPage", self.client,  key = self.key)

                elif self.start_button.checkForInput(mouse_pos):
                    if (not any(rb.clicked for rb in self.time_format_btns) or
                        not any(rb.clicked for rb in self.game_type_btns)):
                        self.error_message = "Select both a time format and who you play against."
                    else:
                        self.game_state.selected_time_format = next(
                            rb for rb in self.time_format_btns if rb.clicked
                        ).get_text()
                        self.game_state.selected_game_type = next(
                            rb for rb in self.game_type_btns if rb.clicked
                        ).get_text()



                        message = {"type" : "request_game",
                                               "time" : self.game_state.selected_time_format,
                                                 "game_type" : self.game_state.selected_game_type, 
                                                  "friend_username" : None}
                        self.send_message(message)
                        # If random, go to waiting page random
                        if self.game_state.selected_game_type == "Random":
                            self.manager.set_current_page("WaitingPageRandom", client = self.client, key = self.key)
                        else:
                            # If friend, first go to InviteFriendPage
                            self.manager.set_current_page("InviteFriendPage", client = self.client, key = self.key)

            self.time_format_group.update(events)
            self.game_type_group.update(events)



    
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

        # If white theme, darken start/back
        if theme_index == 1:
            self.start_button.base_color = (50, 50, 50)
            self.start_button.hovering_color = (100, 100, 100)
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
        else:
            self.start_button.base_color = "White"
            self.start_button.hovering_color = "Green"
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"

        # Title
        title_surf = self.get_font("frames/assets/font.ttf", 25).render(
            "What format do you want to play in?", True, theme["text"]
        )
        title_rect = title_surf.get_rect(center=(640, 220))
        self.screen.blit(title_surf, title_rect)

        max_width = 800
        text = "* PLEASE NOTE THAT YOU SHOULD NOT START A GAME IF YOU ARE NOT READY."
        lines = self.split_text(text, self.font_25, max_width)
        y_offset = 320 - (len(lines) * self.font_25.get_height() // 2)
        for line in lines:
            rendered_text = self.font_25.render(line, True, theme["text"])
            text_rect = rendered_text.get_rect(center=(860, y_offset))
            self.screen.blit(rendered_text, text_rect)
            text_rect = rendered_text.get_rect(center=(860, y_offset))
            self.screen.blit(rendered_text, text_rect)
            y_offset += self.font_25.get_height()

        enjoy_text = self.font_25.render("ENJOY THE GAME!", True, theme["text"])
        enjoy_rect = enjoy_text.get_rect(center=(860, y_offset + self.font_25.get_height()))
        self.screen.blit(enjoy_text, enjoy_rect)

        if self.error_message:
            err_surf = self.font_25.render(self.error_message, True, (255, 0, 0))
            err_rect = err_surf.get_rect(center=(640, 700))
            self.screen.blit(err_surf, err_rect)

        self.start_button.changeColor(pygame.mouse.get_pos())
        self.start_button.update(self.screen)
        self.back_button.changeColor(pygame.mouse.get_pos())
        self.back_button.update(self.screen)

        self.time_format_group.draw(self.screen)
        self.game_type_group.draw(self.screen)