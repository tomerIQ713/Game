import pygame
import sys
import os
import re
import threading
import time
import json

from termcolor import colored
from CTkMessagebox import CTkMessagebox

from frames.assets.button import Button, RadioButton
from frames.assets.textBoxInput import TextInputBox

from chess_board import ChessBoard
from player import Player
from helper import Helper

from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes


class WaitingPageRandom(BasePage):
    def __init__(self, manager, client, key):
        super().__init__(manager)

        # Networking
        self.client = client
        self.key = key

        # We'll store any partially received data here
        self.partial_buffer = ""

        # Thread control
        self.match_thread = None
        self.match_searching = False  # A flag to indicate if we are currently searching.

        # UI elements
        self.counter = 1
        self.update_interval = 700
        self.last_update = pygame.time.get_ticks()

        self.go_back_button = Button(
            image=None,
            pos=(500, 600),
            text_input="BACK",
            font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White",
            hovering_color="Green"
        )
        self.ready_button = Button(
            image=None,
            pos=(860, 600),
            text_input="Ready",
            font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White",
            hovering_color="Green"
        )

        print("[DEBUG] WaitingPageRandom initialized.")

    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.go_back_button.checkForInput(mouse_pos):
                    print("[DEBUG] 'BACK' button clicked.")
                    if self.match_searching:
                        print("[DEBUG] Currently matchmaking, sending LEAVE status to server.")
                        self.send_message({"type": "game_update", "status": "LEAVE"})
                        self.match_searching = False
                    self.manager.set_current_page("PlayPage", self.client, self.key)

                elif self.ready_button.checkForInput(mouse_pos):
                    print("[DEBUG] 'READY' button clicked.")
                    if not self.match_searching:
                        self.match_searching = True
                        print("[DEBUG] Setting match_searching to True, sending request_game to server.")
                        self.send_message({
                            "type": "request_game",
                            "time": self.game_state.selected_time_format,
                            "game_type": "Random"
                        })
                        print("[DEBUG] Spawning check_for_match thread.")
                        self.match_thread = threading.Thread(target=self.check_for_match, daemon=True)
                        self.match_thread.start()

    def check_for_match(self):
        """
        Polls the server every 2 s.
        • On {"type":"game_start", …}  →  opens the board and PASSES the info along.
        • Keeps compatibility with legacy {"type":"game_update","status":"OK"}.
        """
        print("[DEBUG] check_for_match thread started")
        while self.match_searching:
            time.sleep(2)
            for msg in self.receive_messages():
                print("[DEBUG] Received:", msg)

                # ── preferred packet ──
                if msg.get("type") == "game_start":
                    self.match_searching = False     # stop the thread
                    self.manager.set_current_page(
                        "GameBoardPage",
                        self.client,
                        selected_time_format=msg["time_format"],
                        key=self.key,
                        player_color=msg["color"],
                        current_turn=msg["current_turn"],
                        game_id=msg["game_id"]
                    )
                    return

                # ── legacy packet (still supported) ──
                if msg.get("type") == "game_update":
                    st = msg.get("status")
                    if st == "OK":
                        self.match_searching = False
                        self.manager.set_current_page(
                            "GameBoardPage",
                            self.client,
                            selected_time_format=self.game_state.selected_time_format,
                            key=self.key,
                            player_color="white",          # fallback assumption
                            current_turn="white",
                            game_id=None
                        )
                        return
                    if st == "WAITING":
                        print("[DEBUG] Waiting for opponent…")
                    if st == "LEAVE":
                        self.match_searching = False
                        return
        print("[DEBUG] check_for_match thread ended")



    def send_message(self, message_dict):
        """
        JSON-encode the message, encrypt it, and send it via self.client.
        """
        message_str = json.dumps(message_dict)
        print(f"[DEBUG] Sending message to server: {message_str}")
        encrypted_message = self.key.encrypt(
            message_str.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        print(f"[DEBUG] Encrypted message length: {len(encrypted_message)} bytes.")
        self.client.send(encrypted_message)

    def receive_messages(self):
        """
        Reads from the socket in non-blocking mode, appends data to self.partial_buffer,
        and attempts to decode multiple JSON objects if they're all strung together.
        Returns a list of fully parsed JSON objects (dicts).
        """

        # We'll store any fully parsed objects in this list
        parsed_objects = []

        try:
            self.client.setblocking(False)
            data = self.client.recv(4096)
            if not data:
                # If there's no data, return empty list
                print("[DEBUG] Socket returned no data.")
                return []
            
            # Convert raw bytes to string, then append to our partial buffer
            chunk = data.decode('utf-8')
            print(f"[DEBUG] Raw chunk received (len={len(chunk)}): {chunk}")
            self.partial_buffer += chunk

            # Attempt to parse out multiple JSON objects from partial_buffer
            new_objects, offset = self.parse_multiple_json_objects(self.partial_buffer)
            parsed_objects.extend(new_objects)

            # Remove everything we've successfully parsed from the buffer
            self.partial_buffer = self.partial_buffer[offset:]

        except Exception as e:
            print(f"[DEBUG] Exception during receive_messages: {e}")
        finally:
            self.client.setblocking(True)

        return parsed_objects

    def parse_multiple_json_objects(self, data_str):
        """
        Tries to parse multiple JSON objects from the given string.
        Returns (list_of_objects, offset) where offset is how far we got in data_str.
        If there's partial data left that wasn't enough for a full object, we leave it for next time.
        """
        objs = []
        idx = 0
        length = len(data_str)
        decoder = json.JSONDecoder()

        while idx < length:
            # Skip whitespace
            while idx < length and data_str[idx].isspace():
                idx += 1
            if idx >= length:
                break

            try:
                # Attempt to decode one JSON object
                obj, offset = decoder.raw_decode(data_str, idx)
                objs.append(obj)
                idx = offset
            except json.JSONDecodeError:
                # We hit incomplete data; break so we can retry next time
                break

        return objs, idx

    def update(self):
        # Animate the "..." for "Matchmaking..."
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
        
        theme_index = self.game_state.selected_theme
        theme = THEMES[theme_index]
        self.screen.fill(theme["bg"])

        # Set button colors based on theme
        if theme_index == 1:
            self.go_back_button.base_color = (50, 50, 50)
            self.go_back_button.hovering_color = (100, 100, 100)
            self.ready_button.base_color = (50, 50, 50)
            self.ready_button.hovering_color = (100, 100, 100)
        else:
            self.go_back_button.base_color = "White"
            self.go_back_button.hovering_color = "Green"
            self.ready_button.base_color = "White"
            self.ready_button.hovering_color = "Green"

        font_45 = self.get_font("frames/assets/font.ttf", 45)
        dots_text = "Matchmaking" + '.' * self.counter if self.match_searching else "Waiting Page"
        text_surface = font_45.render(dots_text, True, theme["text"])
        text_rect = text_surface.get_rect(center=(640, 260))
        self.screen.blit(text_surface, text_rect)

        font_25 = self.get_font("frames/assets/font.ttf", 25)
        info1 = font_25.render(f"Time Format: {self.game_state.selected_time_format}", True, theme["text"])
        info1_rect = info1.get_rect(center=(640, 340))
        self.screen.blit(info1, info1_rect)

        info2 = font_25.render(f"Game Type: {self.game_state.selected_game_type}", True, theme["text"])
        info2_rect = info2.get_rect(center=(640, 390))
        self.screen.blit(info2, info2_rect)

        # Render buttons
        self.go_back_button.changeColor(pygame.mouse.get_pos())
        self.go_back_button.update(self.screen)

        self.ready_button.changeColor(pygame.mouse.get_pos())
        self.ready_button.update(self.screen)
