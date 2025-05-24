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


class OptionsPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)

        self.key = key

        self.client = client
        self.font_45 = pygame.font.SysFont(None, 45)
        self.back_button = Button(
            image=None,
            pos=(640, 600),
            text_input="BACK",
            font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White",
            hovering_color="Green"
        )
        self.theme_button = Button(
            image=None,
            pos=(640, 250),
            text_input="Themes",
            font=pygame.font.SysFont(None, 45),
            base_color="White",
            hovering_color="Green"
        )
        self.profile_button = Button(
            image=None,
            pos=(640, 350),
            text_input="Profile",
            font=pygame.font.SysFont(None, 45),
            base_color="White",
            hovering_color="Green"
        )
        self.password_button = Button(
            image=None,
            pos=(640, 450),
            text_input="Change Password",
            font=pygame.font.SysFont(None, 45),
            base_color="White",
            hovering_color="Green"
        )
    
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("MainMenuPage", self.client,  key = self.key)
                elif self.theme_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("ThemesPage", self.client,  key = self.key)
                elif self.profile_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("ProfilePage", self.client,  key = self.key)
                elif self.password_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("ChangePasswordPage", self.client,  key = self.key)

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
            base_c = (50, 50, 50)
            hover_c = (100, 100, 100)
        else:
            base_c = "White"
            hover_c = "Green"

        self.back_button.base_color = base_c
        self.back_button.hovering_color = hover_c
        self.theme_button.base_color = base_c
        self.theme_button.hovering_color = hover_c
        self.profile_button.base_color = base_c
        self.profile_button.hovering_color = hover_c
        self.password_button.base_color = base_c
        self.password_button.hovering_color = hover_c

        options_text = pygame.font.SysFont(None, 45).render("Options", True, theme["text"])
        options_rect = options_text.get_rect(center=(640, 100))
        self.screen.blit(options_text, options_rect)

        mouse_pos = pygame.mouse.get_pos()
        for btn in [self.theme_button, self.profile_button, self.password_button, self.back_button]:
            btn.changeColor(mouse_pos)
            btn.update(self.screen)