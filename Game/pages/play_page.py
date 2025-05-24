
import pygame, json
from frames.assets.button import Button, RadioButton
from base_page import BasePage
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class PlayPage(BasePage):
    """Select time control, game type, difficulty **and** colour vs. engine."""

    def __init__(self, manager, client, key):
        super().__init__(manager)
        self.client, self.key = client, key
        self.error = ""

        self.font_30 = pygame.font.SysFont(None, 30)
        self.font_50 = pygame.font.SysFont(None, 50)

        self.time_radio = [
            RadioButton(50, y, 240, 50, self.font_30, label)
            for y, label in zip(
                (250, 310, 370, 430, 490),
                ("Classical: 1 hour",
                 "Rapid: 30 min",
                 "Rapid: 10 min",
                 "Blitz: 3 + 1 min",
                 "Bullet: 1 + 1 min"))
        ]
        for rb in self.time_radio:
            rb.setRadioButtons(self.time_radio)

        self.type_radio = [
            RadioButton(320, y, 220, 50, self.font_30, label)
            for y, label in zip(
                (250, 310, 370, 430),
                ("Random", "Play a friend", "Spectate", "Computer"))
        ]
        for rb in self.type_radio:
            rb.setRadioButtons(self.type_radio)

        self.diff_radio = [
            RadioButton(580, y, 160, 50, self.font_30, lab)
            for y, lab in zip((250, 310, 370), ("Easy", "Medium", "Hard"))
        ]
        for rb in self.diff_radio:
            rb.setRadioButtons(self.diff_radio)

        self.color_radio = [
            RadioButton(760, 250, 160, 50, self.font_30, "Play White"),
            RadioButton(760, 310, 160, 50, self.font_30, "Play Black"),
        ]
        for rb in self.color_radio:
            rb.setRadioButtons(self.color_radio)

        self.start_btn = Button(
            image=None, pos=(930, 500), text_input="START",
            font=self.font_50, base_color="White", hovering_color="Green")
        self.back_btn = Button(
            image=None, pos=(120, 700), text_input="BACK",
            font=self.font_50, base_color="White", hovering_color="Red")

    def _enc_send(self, obj: dict) -> bool:
        """RSA-encrypt `obj` Unless `self.key` is None (fallback to plain);
        returns False on socket error."""
        if not self.client:
            self.error = "No connection to server."
            return False

        raw = json.dumps(obj, separators=(',', ':')).encode()
        try:
            if self.key:
                raw = self.key.encrypt(
                    raw,
                    padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                 algorithm=hashes.SHA256(), label=None))
            self.client.send(raw)
            return True
        except OSError:
            self.error = "Network error – could not send."
            return False


    def handle_events(self, events):
        mouse = pygame.mouse.get_pos()

        for grp in (self.time_radio, self.type_radio,
                    self.diff_radio, self.color_radio):
            pygame.sprite.Group(grp).update(events)

        for ev in events:
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if self.back_btn.checkForInput(mouse):
                    self.manager.set_current_page("MainMenuPage",
                                                  client=self.client,
                                                  key=self.key)
                    return
                
                if self.start_btn.checkForInput(mouse):
                    type_sel = next((rb for rb in self.type_radio if rb.clicked), None)
                    if not type_sel:
                        self.error = "Select a game type."
                        return
                    gtype = type_sel.get_text()

                    time_sel = next((rb for rb in self.time_radio if rb.clicked), None)
                    if gtype not in ("Spectate", "Computer") and not time_sel:
                        self.error = "Select a time format."
                        return
                    tlabel = time_sel.get_text() if time_sel else "Classical: 1 hour"

                    self.game_state.selected_time_format = tlabel
                    self.game_state.selected_game_type   = gtype

                    if gtype == "Random":
                        if self._enc_send({"type": "request_game",
                                           "time": tlabel,
                                           "game_type": "Random"}):
                            self.manager.set_current_page("WaitingPageRandom",
                                                          client=self.client,
                                                          key=self.key)
                        return

                    if gtype == "Play a friend":
                        self.manager.set_current_page("InviteFriendPage",
                                                      client=self.client,
                                                      key=self.key)
                        return

                    if gtype == "Spectate":
                        self.manager.set_current_page("SpectateLobbyPage",
                                                      client=self.client,
                                                      key=self.key)
                        return

                    diff_sel = next((rb for rb in self.diff_radio if rb.clicked), None)
                    if not diff_sel:
                        self.error = "Select difficulty."
                        return
                    depth = {"Easy": 6, "Medium": 12, "Hard": 20}[diff_sel.get_text()]

                    col_sel = next((rb for rb in self.color_radio if rb.clicked), None)
                    if not col_sel:
                        self.error = "Choose White or Black."
                        return
                    play_white   = (col_sel.get_text() == "Play White")
                    player_color = "white" if play_white else "black"

                    self.manager.set_current_page(
                        "GameBoardPage",
                        client=None, key=None,
                        selected_time_format=tlabel,
                        player_color=player_color,
                        current_turn="white",       
                        game_id="local",
                        vs_engine=True,
                        engine_depth=depth)
                    return  

    def update(self): pass

    def draw(self):
        self.screen.fill((40, 40, 40))

        self.screen.blit(self.font_50.render("Choose your game", True, (255, 255, 255)),
                         (50, 150))

        pygame.sprite.Group(self.time_radio).draw(self.screen)
        pygame.sprite.Group(self.type_radio).draw(self.screen)

        if any(rb.clicked and rb.get_text() == "Computer" for rb in self.type_radio):
            pygame.sprite.Group(self.diff_radio).draw(self.screen)
            pygame.sprite.Group(self.color_radio).draw(self.screen)

        for btn in (self.start_btn, self.back_btn):
            btn.changeColor(pygame.mouse.get_pos())
            btn.update(self.screen)

        if self.error:
            surf = self.font_30.render(self.error, True, (255, 80, 80))
            self.screen.blit(surf, (320, 650))
