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

class ThemesPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.font_30 = pygame.font.SysFont(None, 30)

        self.key = key
    
        self.client = client
        self.themes_buttons = [
            RadioButton(525, 200, 200, 60, self.font_30, "Default"),
            RadioButton(525, 280, 200, 60, self.font_30, "White"),
            RadioButton(525, 360, 200, 60, self.font_30, "Blue"),
        ]
        for rb in self.themes_buttons:
            rb.setRadioButtons(self.themes_buttons)
        self.radio_group = pygame.sprite.Group(self.themes_buttons)

        idx = self.game_state.selected_theme
        if 0 <= idx < len(self.themes_buttons):
            self.themes_buttons[idx].clicked = True

        self.back_button = Button(
            image=None,
            pos=(640, 600),
            text_input="BACK",
            font=self.get_font("frames/assets/font.ttf", 55),
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
                    selected = next((rb.get_text() for rb in self.themes_buttons if rb.clicked), None)
                    if selected == "Default":
                        self.game_state.selected_theme = 0
                    elif selected == "White":
                        self.game_state.selected_theme = 1
                    elif selected == "Blue":
                        self.game_state.selected_theme = 2

                    self.manager.set_current_page("OptionsPage", self.client,  key = self.key)

        self.radio_group.update(events)

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
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
        else:
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"

        theme_text = pygame.font.SysFont(None, 45).render("Choose a theme", True, theme["text"])
        theme_rect = theme_text.get_rect(center=(640, 100))
        self.screen.blit(theme_text, theme_rect)

        self.radio_group.draw(self.screen)

        mouse_pos = pygame.mouse.get_pos()
        self.back_button.changeColor(mouse_pos)
        self.back_button.update(self.screen)