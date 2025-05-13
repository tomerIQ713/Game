import pygame
import json
from termcolor import colored  # still used for password strength elsewhere
from CTkMessagebox import CTkMessagebox

from frames.assets.button import Button, RadioButton
from frames.assets.textBoxInput import TextInputBox
from base_page import BasePage

from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes


class PlayPage(BasePage):
    """Select time‑control & game‑type – now with a **Spectate** section."""

    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client = client
        self.key = key

        # ────────────────── fonts & colours ──────────────────
        self.font_25 = pygame.font.SysFont(None, 25)
        self.font_30 = pygame.font.SysFont(None, 30)
        self.font_50 = pygame.font.SysFont(None, 50)

        # ────────────────── time‑format radio buttons ──────────────────
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

        # ────────────────── game‑type radio buttons ──────────────────
        self.game_type_btns = [
            RadioButton(270, 280, 200, 60, self.font_30, "Random"),
            RadioButton(270, 360, 200, 60, self.font_30, "Play a friend"),
            RadioButton(270, 440, 200, 60, self.font_30, "Spectate")  # NEW
        ]
        for rb in self.game_type_btns:
            rb.setRadioButtons(self.game_type_btns)
        self.game_type_group = pygame.sprite.Group(self.game_type_btns)

        # ────────────────── action buttons ──────────────────
        self.start_button = Button(
            image=None, pos=(860, 400), text_input="Start",
            font=self.font_50, base_color="White", hovering_color="Green")
        self.back_button = Button(
            image=None, pos=(640, 600), text_input="BACK",
            font=self.get_font("frames/assets/font.ttf", 55),
            base_color="White", hovering_color="Green")

        self.error_message = ""

    # ------------------------------------------------------------------
    def get_font(self, path, size):
        return pygame.font.Font(path, size)

    # ------------------------------------------------------------------
    def send_message(self, message_dict):
        raw = json.dumps(message_dict)
        enc = self.key.encrypt(
            raw.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        self.client.send(enc)

    # ------------------------------------------------------------------
    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                # ---------- BACK ----------
                if self.back_button.checkForInput(mouse):
                    self.game_state.selected_time_format = next(
                        (rb.get_text() for rb in self.time_format_btns if rb.clicked), None)
                    self.game_state.selected_game_type = next(
                        (rb.get_text() for rb in self.game_type_btns if rb.clicked), None)
                    self.manager.set_current_page("MainMenuPage", self.client, key=self.key)

                # ---------- START ----------
                elif self.start_button.checkForInput(mouse):
                    if not any(rb.clicked for rb in self.game_type_btns):
                        self.error_message = "Select a game type (Random / Friend / Spectate)."
                        continue

                    selected_type = next(rb.get_text() for rb in self.game_type_btns if rb.clicked)

                    if selected_type != "Spectate" and not any(rb.clicked for rb in self.time_format_btns):
                        self.error_message = "Select a time format.";
                        continue

                    # Save selections to global state
                    self.game_state.selected_game_type = selected_type
                    self.game_state.selected_time_format = (
                        next((rb.get_text() for rb in self.time_format_btns if rb.clicked), None)
                        if selected_type != "Spectate" else None)

                    # ---- branch by game type ----
                    if selected_type == "Spectate":
                        # Go straight to lobby of live games
                        self.manager.set_current_page(
                            "SpectateLobbyPage", client=self.client, key=self.key)
                    else:
                        if selected_type == "Random":
                            # ask server immediately for random pairing
                            self.send_message({
                                "type": "request_game",
                                "time": self.game_state.selected_time_format,
                                "game_type": "Random",
                                "friend_username": None
                            })
                            self.manager.set_current_page("WaitingPageRandom",
                                                          client=self.client, key=self.key)
                        else:  # "Play a friend"
                            # no packet yet – will be sent from InviteFriendPage
                            self.manager.set_current_page("InviteFriendPage",
                                                          client=self.client, key=self.key)
                    

            # pass events to radio groups
            self.time_format_group.update(events)
            self.game_type_group.update(events)

    # ------------------------------------------------------------------
    def update(self):
        pass

    # ------------------------------------------------------------------
    def draw(self):
        THEMES = [
            {"bg": (0, 0, 0), "text": (255, 255, 255)},
            {"bg": (255, 255, 255), "text": (0, 0, 0)},
            {"bg": (0, 70, 160), "text": (255, 255, 255)}
        ]
        theme = THEMES[self.game_state.selected_theme]
        self.screen.fill(theme["bg"])

        # colours of buttons for light theme
        dark_base = (50, 50, 50)
        dark_hover = (100, 100, 100)
        if self.game_state.selected_theme == 1:
            for btn in (self.start_button, self.back_button):
                btn.base_color, btn.hovering_color = dark_base, dark_hover
        else:
            self.start_button.base_color = self.back_button.base_color = "White"
            self.start_button.hovering_color = self.back_button.hovering_color = "Green"

        # -------- TITLE --------
        title = self.get_font("frames/assets/font.ttf", 25).render(
            "Choose your game:", True, theme["text"])
        self.screen.blit(title, title.get_rect(center=(640, 200)))

        # -------- subtitle for formats --------
        subtitle = self.font_25.render("Time Control", True, theme["text"])
        self.screen.blit(subtitle, subtitle.get_rect(center=(150, 250)))

        subtitle2 = self.font_25.render("Game Type", True, theme["text"])
        self.screen.blit(subtitle2, subtitle2.get_rect(center=(370, 250)))

        # helpful footnote
        foot = self.font_25.render("ENJOY THE GAME!", True, theme["text"])
        self.screen.blit(foot, foot.get_rect(center=(860, 650)))

        # error message if any
        if self.error_message:
            err = self.font_25.render(self.error_message, True, (255, 0, 0))
            self.screen.blit(err, err.get_rect(center=(640, 700)))

        # draw radio groups & buttons
        self.time_format_group.draw(self.screen)
        self.game_type_group.draw(self.screen)

        for btn in (self.start_button, self.back_button):
            btn.changeColor(pygame.mouse.get_pos())
            btn.update(self.screen)
