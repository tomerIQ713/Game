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

class MainMenuPage(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client = client  # Store the client socket for future communication
        self.key = key

        self.play_button = Button(
            image=pygame.image.load("frames/assets/Play Rect.png"),
            pos=(640, 250),
            text_input="PLAY",
            font=self.get_font("frames/assets/font.ttf", 75),
            base_color="#d7fcd4",
            hovering_color="White"
        )
        self.options_button = Button(
            image=pygame.image.load("frames/assets/Options Rect.png"),
            pos=(640, 400),
            text_input="OPTIONS",
            font=self.get_font("frames/assets/font.ttf", 75),
            base_color="#d7fcd4",
            hovering_color="White"
        )
        self.quit_button = Button(
            image=pygame.image.load("frames/assets/Quit Rect.png"),
            pos=(640, 550),
            text_input="QUIT",
            font=self.get_font("frames/assets/font.ttf", 75),
            base_color="#d7fcd4",
            hovering_color="White"
        )
        self.signout_button = Button(
            image=None,
            pos=(640, 700),
            text_input="SIGN OUT",
            font=self.get_font("frames/assets/font.ttf", 25),
            base_color="#d7fcd4",
            hovering_color="White"
        )

        
    def get_font(self, path, size):
        return pygame.font.Font(path, size)
    
    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.play_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("PlayPage", client=self.client, key = self.key)  # Pass socket to PlayPage
                elif self.options_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("OptionsPage", client=self.client,  key = self.key)
                elif self.quit_button.checkForInput(mouse_pos):
                    pygame.quit()
                    sys.exit()
                
                elif self.play_friend_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("InviteFriendPage",
                                  client=self.client, key=self.key)

                elif self.signout_button.checkForInput(mouse_pos):
                    self.client.close()  # Close socket on signout
                    self.manager.set_current_page("LoginPage")



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

        if theme_index == 1:  # White theme
            color_base = (50, 50, 50)
            color_hover = (100, 100, 100)
        else:
            color_base = "#d7fcd4"
            color_hover = "White"

        self.play_button.base_color = color_base
        self.play_button.hovering_color = color_hover
        self.options_button.base_color = color_base
        self.options_button.hovering_color = color_hover
        self.quit_button.base_color = color_base
        self.quit_button.hovering_color = color_hover
        self.signout_button.base_color = color_base
        self.signout_button.hovering_color = color_hover

        self.screen.fill(theme["bg"])
        pygame.display.set_caption(f"Welcome, {self.game_state.username}")

        menu_surf = self.get_font("frames/assets/font.ttf", 100).render("MAIN MENU", True, theme["text"])
        menu_rect = menu_surf.get_rect(center=(640, 100))
        self.screen.blit(menu_surf, menu_rect)

        mouse_pos = pygame.mouse.get_pos()
        for btn in [self.play_button, self.options_button, self.quit_button, self.signout_button]:
            btn.changeColor(mouse_pos)
            btn.update(self.screen)
        