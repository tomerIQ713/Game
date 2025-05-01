import pygame
import logging

from page_manager import PageManager
from pages.login_page import LoginPage
from pages.main_menu_page import MainMenuPage
from pages.play_page import PlayPage
from pages.invite_friend_page import InviteFriendPage
from pages.waiting_random_page import WaitingPageRandom
from pages.waiting_friend_page import WaitingPageFriend
from pages.game_board_page import GameBoardPage
from pages.options_page import OptionsPage
from pages.theme_page import ThemesPage
from pages.progfile_page import ProfilePage
from pages.add_friend_page import AddFriendPage
from pages.change_password_page import ChangePasswordPage

def main():
    pygame.init()

    manager = PageManager(screen_width=1300, screen_height=840)

    manager.register_page("LoginPage", LoginPage)
    manager.register_page("MainMenuPage", MainMenuPage)
    manager.register_page("PlayPage", PlayPage)
    manager.register_page("InviteFriendPage", InviteFriendPage)  
    manager.register_page("WaitingPageRandom", WaitingPageRandom)
    manager.register_page("WaitingPageFriend", WaitingPageFriend)
    manager.register_page("GameBoardPage", GameBoardPage)
    manager.register_page("OptionsPage", OptionsPage)
    manager.register_page("ThemesPage", ThemesPage)
    manager.register_page("ProfilePage", ProfilePage)
    manager.register_page("AddFriendPage", AddFriendPage)
    manager.register_page("ChangePasswordPage", ChangePasswordPage)
    
    manager.set_current_page("LoginPage")
    manager.run()

if __name__ == "__main__":
    main()
 