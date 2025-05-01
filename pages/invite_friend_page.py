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

class InviteFriendPage(BasePage):
    """
    Page where user types the friend's name + clicks 'INVITE.'
    Then we go to WaitingPageFriend.
    """
    def __init__(self, manager, client, key):
        super().__init__(manager)

        self.key =  key
        
        self.client = client
        self.font_20 = self.get_font("frames/assets/font.ttf", 20)
        self.friend_input = TextInputBox(440, 350, 400, 50, self.font_20)
        self.input_boxes = [self.friend_input]

        self.invite_button = Button(
            image=None, pos=(640, 500),
            text_input="INVITE",
            font=self.get_font("frames/assets/font.ttf", 40),
            base_color="White", hovering_color="Green"
        )
        self.back_button = Button(
            image=None, pos=(640, 600),
            text_input="BACK",
            font=self.get_font("frames/assets/font.ttf", 40),
            base_color="White",
            hovering_color="Green"
        )

        self.error_message = ""

    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("PlayPage", self.client)
                elif self.invite_button.checkForInput(mouse_pos):
                    friend_name = self.friend_input.text.strip()
                    if friend_name:
                        self.game_state.friend_name_to_invite = friend_name
                        self.manager.set_current_page("WaitingPageFriend", self.client, self.key)
                    else:
                        self.error_message = "Please enter a friend's name!"

            for box in self.input_boxes:
                box.handle_event(event)

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
        self.screen.fill(theme["bg"])

        if theme_index == 1:
            self.invite_button.base_color = (50, 50, 50)
            self.invite_button.hovering_color = (100, 100, 100)
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
        else:
            self.invite_button.base_color = "White"
            self.invite_button.hovering_color = "Green"
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"

        label_surf = self.get_font("frames/assets/font.ttf", 40).render("Invite a friend", True, theme["text"])
        label_rect = label_surf.get_rect(center=(640, 150))
        self.screen.blit(label_surf, label_rect)

        instruct_surf = self.font_20.render("Enter the friend's username you want to invite:", True, theme["text"])
        instruct_rect = instruct_surf.get_rect(center=(640, 300))
        self.screen.blit(instruct_surf, instruct_rect)

        for box in self.input_boxes:
            box.draw(self.screen)

        self.invite_button.changeColor(pygame.mouse.get_pos())
        self.invite_button.update(self.screen)

        self.back_button.changeColor(pygame.mouse.get_pos())
        self.back_button.update(self.screen)

        if self.error_message:
            err_surf = self.font_20.render(self.error_message, True, (255,0,0))
            err_rect = err_surf.get_rect(center=(640, 700))
            self.screen.blit(err_surf, err_rect)
