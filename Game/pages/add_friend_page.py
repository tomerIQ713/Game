import pygame

from frames.assets.button import Button
from frames.assets.textBoxInput import TextInputBox

from helper import Helper

from base_page import BasePage

import json

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes


class AddFriendPage(BasePage):
    """
    Now has a "SUBMIT" button to actually handle the friend request.
    """
    def __init__(self, manager, client, key):
        super().__init__(manager)

        self.key = key
        
        self.client = client
        self.font_20 = self.get_font("frames/assets/font.ttf", 20)
        
        self.friend_input = TextInputBox(440, 350, 400, 50, self.font_20)
        self.input_boxes = [self.friend_input]

        self.back_button = Button(
            image=None, pos=(640, 600),
            text_input="BACK", font=self.get_font("frames/assets/font.ttf", 30),
            base_color="White", hovering_color="Green"
        )

        self.submit_button = Button(
            image=None, pos=(640, 500),
            text_input="SUBMIT",
            font=self.get_font("frames/assets/font.ttf", 30),
            base_color="White", hovering_color="Green"
        )

        self.message = ""
    
        
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.back_button.checkForInput(mouse_pos):
                    self.manager.set_current_page("ProfilePage", self.client,  key = self.key)

                elif self.submit_button.checkForInput(mouse_pos):
                    friend_name = self.friend_input.text.strip()
                    if friend_name:
                        self.message = f"Friend request sent to '{friend_name}'!"
                        message = {"type" : "add_friend", "username" : friend_name}
                        self.send_message(message)
                        
                    else:
                        self.message = "Please enter a friend's name."

            for box in self.input_boxes:
                box.handle_event(event)
            

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
            self.back_button.base_color = (50, 50, 50)
            self.back_button.hovering_color = (100, 100, 100)
            self.submit_button.base_color = (50, 50, 50)
            self.submit_button.hovering_color = (100, 100, 100)
        else:
            self.back_button.base_color = "White"
            self.back_button.hovering_color = "Green"
            self.submit_button.base_color = "White"
            self.submit_button.hovering_color = "Green"

        add_friend_text = self.get_font("frames/assets/font.ttf", 45).render("Add a friend", True, theme["text"])
        add_friend_rect = add_friend_text.get_rect(center=(640, 100))
        self.screen.blit(add_friend_text, add_friend_rect)

        # Label
        label_text = self.font_20.render("Enter the friend's username:", True, theme["text"])
        label_rect = label_text.get_rect(center=(640, 300))
        self.screen.blit(label_text, label_rect)

        for box in self.input_boxes:
            box.draw(self.screen)

        mouse_pos = pygame.mouse.get_pos()
        self.submit_button.changeColor(mouse_pos)
        self.submit_button.update(self.screen)

        self.back_button.changeColor(mouse_pos)
        self.back_button.update(self.screen)

        if self.message:
            msg_surf = self.font_20.render(self.message, True, (255, 0, 0))
            msg_rect = msg_surf.get_rect(center=(640, 650))
            self.screen.blit(msg_surf, msg_rect)