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


class WaitingPageFriend(BasePage):
    """
    Waits for friend acceptance, showing friend_name_to_invite from game_state.
    """
    def __init__(self, manager, client, key):
        super().__init__(manager)
        
        self.client = client
        self.counter = 1
        self.update_interval = 700
        self.last_update = pygame.time.get_ticks()

        self.go_back_button = Button(
            image=None, pos=(640, 600),
            text_input="BACK", font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White", hovering_color="Green"
        )
    
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.go_back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("PlayPage", self.client)

    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update > self.update_interval:
            self.counter = (self.counter % 3) + 1
            self.last_update = current_time

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


        THEMES.append(
                
            12)
        
        theme_index = self.game_state.selected_theme
        theme = THEMES[theme_index]
        self.screen.fill(theme["bg"])

        if theme_index == 1:
            self.go_back_button.base_color = (50, 50, 50)
            self.go_back_button.hovering_color = (100, 100, 100)
        else:
            self.go_back_button.base_color = "White"
            self.go_back_button.hovering_color = "Green"

        friend_name = self.game_state.friend_name_to_invite or "???"

        font_30 = self.get_font("frames/assets/font.ttf", 30)
        dots_text = f"Waiting for friend '{friend_name}' to accept" + '.' * self.counter
        wait_surf = font_30.render(dots_text, True, theme["text"])
        wait_rect = wait_surf.get_rect(center=(640, 250))
        self.screen.blit(wait_surf, wait_rect)

        font_25 = self.get_font("frames/assets/font.ttf", 25)
        info1 = font_25.render(f"Time Format: {self.game_state.selected_time_format}", True, theme["text"])
        info1_rect = info1.get_rect(center=(640, 350))
        self.screen.blit(info1, info1_rect)

        info2 = font_25.render(f"Game Type: {self.game_state.selected_game_type}", True, theme["text"])
        info2_rect = info2.get_rect(center=(640, 400))
        self.screen.blit(info2, info2_rect)

        mouse_pos = pygame.mouse.get_pos()
        self.go_back_button.changeColor(mouse_pos)
        self.go_back_button.update(self.screen)
