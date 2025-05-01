import pygame
import sys
import os
import re
from assets.button import Button, RadioButton
from assets.textBoxInput import TextInputBox
from termcolor import colored
from CTkMessagebox import CTkMessagebox


current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_dir, ".."))

from chess_board import ChessBoard
from player import Player
from helper import Helper

pygame.init()

SCREEN = pygame.display.set_mode((1280, 720))
pygame.display.set_caption("Menu")

font50_s_25 = pygame.font.SysFont(None, 25)
font50_s_30 = pygame.font.SysFont(None, 30)
font50_s_50 = pygame.font.SysFont(None, 50)

BG = pygame.image.load("frames/assets/white.png")

pygame_icon = pygame.image.load('frames/assets/strategy.png')
pygame.display.set_icon(pygame_icon)

SELECTED_THEME = 0
THEMES = ["Default", "Light", "Blue"]

username = ""

def get_font(size): 
    return pygame.font.Font("frames/assets/font.ttf", size)

def split_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = ""
    
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    
    lines.append(current_line)
    return lines    

selected_time_format = None
selected_game_type = None

def play():
    global selected_time_format, selected_game_type, username

    time_formats_btns = [
        RadioButton(50, 280, 200, 60, font50_s_30, "Classical: 1 hour"),
        RadioButton(50, 360, 200, 60, font50_s_30, "Rapid: 30 min"),
        RadioButton(50, 440, 200, 60, font50_s_30, "Rapid: 10 min"),
        RadioButton(50, 520, 200, 60, font50_s_30, "Blitz: 3 + 1 min"),
        RadioButton(50, 600, 200, 60, font50_s_30, "Bullet: 1 + 1 min"),
    ]

    for rb in time_formats_btns:
        rb.setRadioButtons(time_formats_btns)
        if rb.get_text() == selected_time_format:
            rb.clicked = True
        else:
            rb.clicked = False

    time_formats_btns_group = pygame.sprite.Group(time_formats_btns)

    game_type_btns = [
        RadioButton(270, 280, 200, 60, font50_s_30, "Random"),
        RadioButton(270, 360, 200, 60, font50_s_30, "Play a friend")
    ]

    for rb in game_type_btns:
        rb.setRadioButtons(game_type_btns)
        if rb.get_text() == selected_game_type:
            rb.clicked = True
        else:
            rb.clicked = False

    game_type_btns_group = pygame.sprite.Group(game_type_btns)

    error_message = ""

    while True:
        PLAY_MOUSE_POS = pygame.mouse.get_pos()

        SCREEN.fill("black")

        PLAY_TEXT = get_font(25).render("What format do you want to play in?", True, "White")
        PLAY_RECT = PLAY_TEXT.get_rect(center=(640, 220))
        SCREEN.blit(PLAY_TEXT, PLAY_RECT)

        max_width = 800
        text = "* PLEASE NOTE THAT YOU SHOULD NOT START A GAME IF YOU ARE NOT READY. "
        lines = split_text(text, font50_s_25, max_width)
        y_offset = 320 - (len(lines) * font50_s_25.get_height() // 2)  

        for line in lines:
            rendered_text = font50_s_25.render(line, True, pygame.Color('White'))
            text_rect = rendered_text.get_rect(center=(860, y_offset))
            SCREEN.blit(rendered_text, text_rect)
            y_offset += font50_s_25.get_height() 
        
        rendered_text = font50_s_25.render("ENJOY THE GAME!", True, pygame.Color('White'))
        text_rect = rendered_text.get_rect(center=(860, y_offset + font50_s_25.get_height()))
        SCREEN.blit(rendered_text, text_rect)

        if error_message:
            ERROR_TEXT = font50_s_25.render(error_message, True, pygame.Color('Red'))
            ERROR_RECT = ERROR_TEXT.get_rect(center=(640, 700))
            SCREEN.blit(ERROR_TEXT, ERROR_RECT)

        START = Button(image=None, pos=(860, 400), 
                            text_input="Start", font=font50_s_50, base_color="White", hovering_color="Green")

        START.changeColor(PLAY_MOUSE_POS)
        START.update(SCREEN)

        PLAY_BACK = Button(image=None, pos=(640, 600), 
                            text_input="BACK", font=get_font(55), base_color="White", hovering_color="Green")

        PLAY_BACK.changeColor(PLAY_MOUSE_POS)
        PLAY_BACK.update(SCREEN)

        time_formats_btns_group.draw(SCREEN)
        game_type_btns_group.draw(SCREEN)

        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if PLAY_BACK.checkForInput(PLAY_MOUSE_POS):
                    # Save the selected options before going back
                    selected_time_format = next((rb.get_text() for rb in time_formats_btns if rb.clicked), None)
                    selected_game_type = next((rb.get_text() for rb in game_type_btns if rb.clicked), None)
                    main_menu()
                elif START.checkForInput(PLAY_MOUSE_POS):
                    # Check if any radio button is selected in both groups
                    if not any(rb.clicked for rb in time_formats_btns) or not any(rb.clicked for rb in game_type_btns):
                        error_message = "You must select both a time format and who you play against."
                    else:
                        # Find the selected options
                        selected_time_format = next(rb for rb in time_formats_btns if rb.clicked).get_text()
                        selected_game_type = next(rb for rb in game_type_btns if rb.clicked).get_text()
                        if selected_game_type == 'Random':
                            waiting_page_random(selected_time_format, selected_game_type)
                        else:
                            waiting_page_friend(selected_time_format, selected_game_type)
            
            time_formats_btns_group.update(event_list)
            game_type_btns_group.update(event_list)

        pygame.display.update()
    
def waiting_page_random(time_format, game_type):
    counter = 1
    start = False
    friends = False
    last_update = pygame.time.get_ticks()
    update_interval = 700  
    
    if game_type == 'Play a friend':
        friends = True
         
    while not start:
        PLAY_MOUSE_POS = pygame.mouse.get_pos()
        SCREEN.fill("black")

        current_time = pygame.time.get_ticks()
        if current_time - last_update > update_interval:
            counter = (counter % 3) + 1
            last_update = current_time

        OPTIONS_TEXT = get_font(45).render("Matchmaking" + '.'*counter, True, "White")
        OPTIONS_RECT = OPTIONS_TEXT.get_rect(center=(640, 260))
        SCREEN.blit(OPTIONS_TEXT, OPTIONS_RECT)
        

        INFO1_TEXT = get_font(25).render(f"Time Format: {time_format}", True, "White")
        INFO1_RECT = INFO1_TEXT.get_rect(center=(640, 340))
        SCREEN.blit(INFO1_TEXT, INFO1_RECT)

        INFO2_TEXT = get_font(25).render(f"Game Type: {game_type}", True, "White")
        INFO2_RECT = INFO2_TEXT.get_rect(center=(640, 390))
        SCREEN.blit(INFO2_TEXT, INFO2_RECT)


        GO_BACK = Button(image=None, pos=(500, 600), 
                            text_input="BACK", font=get_font(55), base_color="White", hovering_color="Green")

        GO_BACK.changeColor(PLAY_MOUSE_POS)
        GO_BACK.update(SCREEN)


        READY = Button(image=None, pos=(860, 600), 
                            text_input="Ready", font=get_font(55), base_color="White", hovering_color="Green")

        READY.changeColor(PLAY_MOUSE_POS)
        READY.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if GO_BACK.checkForInput(PLAY_MOUSE_POS):
                    play()
                elif READY.checkForInput(PLAY_MOUSE_POS):
                    accualy_start()

        pygame.display.update()


    ################
def accualy_start():
    WIDTH, HEIGHT = 800, 800
    SQUARE_SIZE = WIDTH // 8
    WHITE = (240, 217, 181) 
    BLACK = (181, 136, 99) 
    TEXT_COLOR = (0, 0, 0)

    chess_board = ChessBoard()
    chess_board.set_board()

    main(WIDTH, HEIGHT, WHITE, BLACK, SQUARE_SIZE, font50_s_25, chess_board, TEXT_COLOR)

def draw_board(screen, WHITE, BLACK, SQUARE_SIZE):
    for row in range(8):
        for col in range(8):
            color = WHITE if (row + col) % 2 == 0 else BLACK
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

import os
import pygame

# Load all piece images
def load_piece_images(folder_path, SQUARE_SIZE):
    piece_images = {}
    for color in ["white", "black"]:
        for piece_name in ["king", "queen", "rook", "bishop", "knight", "pawn"]:
            image_path = os.path.join(folder_path, f"{color}_{piece_name}.png")
            if os.path.exists(image_path):
                piece_images[f"{color}_{piece_name}"] = pygame.transform.scale(
                    pygame.image.load(image_path), (SQUARE_SIZE, SQUARE_SIZE)
                )
    return piece_images

# Draw pieces using images
def draw_pieces(screen, SQUARE_SIZE, board, piece_images):
    for row in range(8):
        for col in range(8):
            piece = board[row][col]
            piece_key = map_piece_name(piece)  # Map piece name to match `piece_images`
            if piece_key:
                piece_image = piece_images.get(piece_key)
                if piece_image:
                    screen.blit(piece_image, (col * SQUARE_SIZE, row * SQUARE_SIZE))
                else:
                    print(f"No image for {piece_key}")  # Debugging missing images


def map_piece_name(piece):
    mapping = {
        "Rook": "rook",
        "Knight": "knight",
        "Bishop": "bishop",
        "Queen": "queen",
        "King": "king",
        "Pown": "pawn"  
    }
    if piece:
        color = "white" if piece[-1] == "W" else "black"  
        base_name = piece[:-1]  
        return f"{color}_{mapping.get(base_name, base_name)}"  
    return None


def main(WIDTH, HEIGHT, WHITE, BLACK, SQUARE_SIZE, font, chess_board, TEXT_COLOR):
    pygame.init()  
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chess Game")
    clock = pygame.time.Clock()

    # Load piece images
    piece_images = load_piece_images("chess pieces", SQUARE_SIZE)

    selected_piece = None  
    current_turn = "white"
    disable_clicks = False  # Variable to disable/enable clicks
    print("Move:", current_turn)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if not disable_clicks:  # Only process clicks if clicks are enabled
                if event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    col = x // SQUARE_SIZE
                    row = y // SQUARE_SIZE
                    clicked_pos = (row, col)

                    if selected_piece is None:
                        piece_name, possible_moves = chess_board.get_piece_possible_moves(clicked_pos)

                        if piece_name != "None":  
                            piece = chess_board.get_normal_board()
                            piece_color = piece[row][col]
                            color = "white" if piece_color[-1] == "W" else "black"
                            if color == current_turn:
                                selected_piece = clicked_pos
                                print(f"Selected: {piece_name} at {clicked_pos}")
                    else:
                        if chess_board.make_move(selected_piece, clicked_pos):
                            print(f"Moved from {selected_piece} to {clicked_pos}")
                            
                            is_in_check = chess_board.check_if_check() # (White\Black\N)
                            if is_in_check != "N":
                                print(f"{is_in_check} is in check")

                                if chess_board.is_won(is_in_check):
                                    print(f"{is_in_check} is mated!")
                                    disable_clicks = True
                                else:
                                    print(f"{is_in_check} is not mated")
                            
                            current_turn = "black" if current_turn == "white" else "white"
                            print("Move:", current_turn)
                        else:
                            print(f"Invalid move from {selected_piece} to {clicked_pos}")
                        selected_piece = None  

        draw_board(screen, WHITE, BLACK, SQUARE_SIZE)
        draw_pieces(screen, SQUARE_SIZE, chess_board.get_normal_board(), piece_images)

        if selected_piece:
            pygame.draw.rect(screen, (0, 255, 0), (selected_piece[1] * SQUARE_SIZE, selected_piece[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)
            _, possible_moves = chess_board.get_piece_possible_moves(selected_piece)
            for move in possible_moves:
                pygame.draw.rect(screen, (255, 0, 0), (move[1] * SQUARE_SIZE, move[0] * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE), 3)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()



######################

def waiting_page_friend(time_format, game_type):
    me = Player("tomer")
    me.add_friend(Player("eitan"))
    me.add_friend(Player("Nadiv"))

    counter = 1
    start = False
    last_update = pygame.time.get_ticks()
    update_interval = 700

    while not start:
        PLAY_MOUSE_POS = pygame.mouse.get_pos()
        SCREEN.fill("black")

        current_time = pygame.time.get_ticks()
        if current_time - last_update > update_interval:
            counter = (counter % 3) + 1
            last_update = current_time

        OPTIONS_TEXT = get_font(30).render("Waititng for a friend to accept" + '.'*counter, True, "White")
        OPTIONS_RECT = OPTIONS_TEXT.get_rect(center=(640, 260))
        SCREEN.blit(OPTIONS_TEXT, OPTIONS_RECT)

        INFO1_TEXT = get_font(25).render(f"Time Format: {time_format}", True, "White")
        INFO1_RECT = INFO1_TEXT.get_rect(center=(640, 340))
        SCREEN.blit(INFO1_TEXT, INFO1_RECT)

        INFO2_TEXT = get_font(25).render(f"Game Type: {game_type}", True, "White")
        INFO2_RECT = INFO2_TEXT.get_rect(center=(640, 390))
        SCREEN.blit(INFO2_TEXT, INFO2_RECT)

        GO_BACK = Button(image=None, pos=(640, 600), 
                         text_input="BACK", font=get_font(55), base_color="White", hovering_color="Green")

        GO_BACK.changeColor(PLAY_MOUSE_POS)
        GO_BACK.update(SCREEN)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if GO_BACK.checkForInput(PLAY_MOUSE_POS):
                    play()

        pygame.display.update()

        # if
        # game_page()

def options():

    while True:
        SCREEN.fill("black")

        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()


        OPTIONS_TEXT = get_font(45).render("Options", True, "White")
        OPTIONS_RECT = OPTIONS_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(OPTIONS_TEXT, OPTIONS_RECT)

        THEME_BUTTON = Button(image=None, pos=(640, 250), 
                                text_input="Themes", font=get_font(45), base_color="White", hovering_color="Green")
        THEME_BUTTON.changeColor(OPTIONS_MOUSE_POS)
        THEME_BUTTON.update(SCREEN)


        PROFILE_BUTTON = Button(image=None, pos=(640, 350), 
                                text_input="Profile", font=get_font(45), base_color="White", hovering_color="Green")
        PROFILE_BUTTON.changeColor(OPTIONS_MOUSE_POS)
        PROFILE_BUTTON.update(SCREEN)

        PASSWORD_BUTTON = Button(image=None, pos=(640, 450), 
                                 text_input="Change Password", font=get_font(45), base_color="White", hovering_color="Green")
        PASSWORD_BUTTON.changeColor(OPTIONS_MOUSE_POS)
        PASSWORD_BUTTON.update(SCREEN)

        OPTIONS_BACK = Button(image=None, pos=(640, 600), 
                              text_input="BACK", font=get_font(55), base_color="White", hovering_color="Green")
        OPTIONS_BACK.changeColor(OPTIONS_MOUSE_POS)
        OPTIONS_BACK.update(SCREEN)


        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if OPTIONS_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    main_menu()
                if PROFILE_BUTTON.checkForInput(OPTIONS_MOUSE_POS):
                    profile_page()
                if PASSWORD_BUTTON.checkForInput(OPTIONS_MOUSE_POS):
                    change_password_page()
                
                if THEME_BUTTON.checkForInput(OPTIONS_MOUSE_POS):
                    themes_page()


        pygame.display.update()


def themes_page():
    global SELECTED_THEME

    theme_buttons = [
        RadioButton(525, 200, 200, 60, font50_s_30, "Default"),
        RadioButton(525, 280, 200, 60, font50_s_30, "Light"),
        RadioButton(525, 360, 200, 60, font50_s_30, "Blue"),
    ]

    for rb in theme_buttons:
        rb.setRadioButtons(theme_buttons)
        rb.clicked = False
    
    theme_buttons[SELECTED_THEME].clicked = True

    theme_buttons_group = pygame.sprite.Group(theme_buttons)
    
    while True:
        SCREEN.fill("black")

        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()

        theme_buttons_group.draw(SCREEN)

        
        THEME_TEXT = get_font(45).render("Choose a theme", True, "White")
        THEME_RECT = THEME_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(THEME_TEXT, THEME_RECT)

        OPTIONS_BACK = Button(image=None, pos=(640, 600), 
                              text_input="BACK", font=get_font(55), base_color="White", hovering_color="Green")
        OPTIONS_BACK.changeColor(OPTIONS_MOUSE_POS)
        OPTIONS_BACK.update(SCREEN)

        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if OPTIONS_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    selected = next((rb.get_text() for rb in theme_buttons if rb.clicked), None)
                    SELECTED_THEME = 0 if selected == 'Default' else SELECTED_THEME
                    SELECTED_THEME = 1 if selected == 'Light' else SELECTED_THEME
                    SELECTED_THEME = 2 if selected == 'Blue' else SELECTED_THEME
                    options()
            

            theme_buttons_group.update(event_list)

        pygame.display.update()

def profile_page():

    while True:
        SCREEN.fill("black")

        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()

        PROFILE_TEXT = get_font(45).render("Profile", True, "White")
        PROFILE_RECT = PROFILE_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(PROFILE_TEXT, PROFILE_RECT)


        ADD_FRIEND = Button(image=None, pos=(640, 600), 
                              text_input="Add a friend", font=get_font(30), base_color="White", hovering_color="Green")
        ADD_FRIEND.changeColor(OPTIONS_MOUSE_POS)
        ADD_FRIEND.update(SCREEN)


        OPTIONS_BACK = Button(image=None, pos=(640, 680), 
                              text_input="BACK", font=get_font(45), base_color="White", hovering_color="Green")
        OPTIONS_BACK.changeColor(OPTIONS_MOUSE_POS)
        OPTIONS_BACK.update(SCREEN)

        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if OPTIONS_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    options()
                elif ADD_FRIEND.checkForInput(OPTIONS_MOUSE_POS):
                    add_friend()

        pygame.display.update()

def add_friend():
    SCREEN.fill("black")

    OPTIONS_MOUSE_POS = pygame.mouse.get_pos()
    ADD_A_FRIEND = get_font(45).render("Add a friend", True, "White")
    PROFILE_RECT = ADD_A_FRIEND.get_rect(center=(640, 100))
    SCREEN.blit(ADD_A_FRIEND, PROFILE_RECT)
    
    ADD_FRIEND = Button(image=None, pos=(640, 600), 
                              text_input="Enter the friend's username: ", font=get_font(30), base_color="White", hovering_color="Green")
    ADD_FRIEND.changeColor(OPTIONS_MOUSE_POS)
    ADD_FRIEND.update(SCREEN)


    

def change_password_page():
    font = get_font(30)
    old_password_box = TextInputBox(600, 250, 400, 50, font)
    new_password_box = TextInputBox(600, 350, 400, 50, font)
    confirm_password_box = TextInputBox(600, 450, 400, 50, font)
    input_boxes = [old_password_box, new_password_box, confirm_password_box]
    
    error_message = ""

    while True:
        SCREEN.fill("black")

        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()

        CHANGE_PASS_TEXT = get_font(45).render("Change Password", True, "White")
        CHANGE_PASS_RECT = CHANGE_PASS_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(CHANGE_PASS_TEXT, CHANGE_PASS_RECT)

        OLD_PASS_TEXT = font.render("Old Password:", True, "White")
        OLD_PASS_RECT = OLD_PASS_TEXT.get_rect(center=(320, 275))
        SCREEN.blit(OLD_PASS_TEXT, OLD_PASS_RECT)

        NEW_PASS_TEXT = font.render("New Password:", True, "White")
        NEW_PASS_RECT = NEW_PASS_TEXT.get_rect(center=(320, 375))
        SCREEN.blit(NEW_PASS_TEXT, NEW_PASS_RECT)

        CONFIRM_PASS_TEXT = font.render("Confirm Password:", True, "White")
        CONFIRM_PASS_RECT = CONFIRM_PASS_TEXT.get_rect(center=(320, 475))
        SCREEN.blit(CONFIRM_PASS_TEXT, CONFIRM_PASS_RECT)

        for box in input_boxes:
            box.update()
            box.draw(SCREEN)

        CHANGE_PASS_BUTTON = Button(image=None, pos=(640, 550), 
                                    text_input="Change Password", font=get_font(45), base_color="White", hovering_color="Green")
        CHANGE_PASS_BUTTON.changeColor(OPTIONS_MOUSE_POS)
        CHANGE_PASS_BUTTON.update(SCREEN)

        OPTIONS_BACK = Button(image=None, pos=(640, 680), 
                              text_input="BACK", font=get_font(45), base_color="White", hovering_color="Green")
        OPTIONS_BACK.changeColor(OPTIONS_MOUSE_POS)
        OPTIONS_BACK.update(SCREEN)

        if error_message:
            ERROR_TEXT = font.render(error_message, True, "Red")
            ERROR_RECT = ERROR_TEXT.get_rect(center=(640, 620))
            SCREEN.blit(ERROR_TEXT, ERROR_RECT)

        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if OPTIONS_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    options()
                if CHANGE_PASS_BUTTON.checkForInput(OPTIONS_MOUSE_POS):
                    if not old_password_box.text or not new_password_box.text or not confirm_password_box.text:
                        error_message = "All fields are required!"
                    elif new_password_box.text != confirm_password_box.text:
                        error_message = "New passwords do not match!"
                    else:
                        info_pass_str(new_password_box.text)
                        error_message = "Password Changed Successfully!"
                        old_password_box.text = ""
                        new_password_box.text = ""
                        confirm_password_box.text = ""
                        old_password_box.txt_surface = font.render("", True, old_password_box.color)
                        new_password_box.txt_surface = font.render("", True, new_password_box.color)
                        confirm_password_box.txt_surface = font.render("", True, confirm_password_box.color)

            for box in input_boxes:
                box.handle_event(event)

        pygame.display.update()

def info_pass_str(password):
    score = estimate_password_strength(password)
    if score[0] > 10:
        print(colored(f"PERFECT PASSWORD", 'green'))
    elif score[0] <= 10 and score[0] > 5:
        print(colored(f"THE PASSOWRD IS OK", 'yellow'))
    elif score[0] < 5:
        print(colored(f"THE PASSWORD IS WEAK", 'red'))

def estimate_password_strength(password):
    length_points = min(10, len(password))  
    variety_points = min(5, len(set(password))) 
    pattern_penalty = 0

    if re.match(r'^[a-zA-Z]+$', password): 
        pattern_penalty += 5
    if re.match(r'^\d+$', password):  
        pattern_penalty += 5
    if re.match(r'^[!@#$%^&*()-_=+\\|[\]{};:\'",.<>/?`~]+$', password): 
        pattern_penalty += 5
    if re.match(r'(\d)\1+$', password): 
        pattern_penalty += 5
    if re.match(r'([a-zA-Z])\1+$', password):  
        pattern_penalty += 5
    if any(ord(password[i]) == ord(password[i+1]) - 1 == ord(password[i+2]) - 2 for i in range(len(password) - 2)):
        pattern_penalty += 10
    
    entropy = len(password) * (len(set(password)) ** 2)
    
    score = max(0, length_points + variety_points - pattern_penalty)
    
    return score, entropy




def login_page():
    global username
    pygame.display.set_caption('Welcome')

    font = get_font(20)
    username_b = TextInputBox(600, 250, 400, 50, font)
    password_b = TextInputBox(600, 350, 400, 50, font)
    input_boxes = [username_b, password_b]
    error_message = ""

    while True:
        SCREEN.fill("black")

        OPTIONS_MOUSE_POS = pygame.mouse.get_pos()

        MAIN_TEXT = get_font(45).render("Login | Signup", True, "White")
        MAIN_TEXT_RECT = MAIN_TEXT.get_rect(center=(640, 100))
        SCREEN.blit(MAIN_TEXT, MAIN_TEXT_RECT)

        USERNAME_TEXT = font.render("Username:", True, "White")
        USERNAME_TEXT_RECT = USERNAME_TEXT.get_rect(center=(320, 275))
        SCREEN.blit(USERNAME_TEXT, USERNAME_TEXT_RECT)

        PASS_TEXT = font.render("Password:", True, "White")
        PASS_RECT = PASS_TEXT.get_rect(center=(320, 375))
        SCREEN.blit(PASS_TEXT, PASS_RECT)

        for box in input_boxes:
            box.update()
            box.draw(SCREEN)

        LOGIN_BACK = Button(image=None, pos=(640, 680), 
                            text_input="LOGIN", font=get_font(45), base_color="White", hovering_color="Green")
        LOGIN_BACK.changeColor(OPTIONS_MOUSE_POS)
        LOGIN_BACK.update(SCREEN)

        if error_message:
            ERROR_TEXT = font.render(error_message, True, "Red")
            ERROR_RECT = ERROR_TEXT.get_rect(center=(640, 550))
            SCREEN.blit(ERROR_TEXT, ERROR_RECT)     

        event_list = pygame.event.get()
        for event in event_list:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.MOUSEBUTTONDOWN:
                if LOGIN_BACK.checkForInput(OPTIONS_MOUSE_POS):
                    if not username_b.text or not password_b.text:
                        error_message = "All fields are required!"
                    elif not is_valid_username(username_b.text):
                        error_message = "Invalid username format!"
                    else: 
                        username = username_b.text
                        info_pass_str(password_b.text)
                        main_menu()
            for box in input_boxes:
                box.handle_event(event)

        pygame.display.update()

def is_valid_username(username):
    if username[0].isdigit():
        return False

    if not re.match(r'^[a-zA-Z0-9 .\-\'_@]+$', username):
        return False
    return True 


def game_page():
    chess_board = ChessBoard()
    chess_board.set_board()
    piece_font = get_font(30)

    window_width, window_height = 1100, 800
    SCREEN = pygame.display.set_mode((window_width, window_height))

    while True:
        SCREEN.fill("black")

        draw_board(SCREEN, chess_board.get_board(), piece_font)
         
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        pygame.display.update()

def main_menu():
    global username
    while True:
        SCREEN.blit(BG, (0, 0))
        pygame.display.set_caption(f'Welcome, {username}')

        MENU_MOUSE_POS = pygame.mouse.get_pos()

        SCREEN.fill("black")

        MENU_TEXT = get_font(100).render("MAIN MENU", True, "#ffffff")
        MENU_RECT = MENU_TEXT.get_rect(center=(640, 100))

        PLAY_BUTTON = Button(image=pygame.image.load("frames/assets/Play Rect.png"), pos=(640, 250), 
                            text_input="PLAY", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        
        OPTIONS_BUTTON = Button(image=pygame.image.load("frames/assets/Options Rect.png"), pos=(640, 400), 
                            text_input="OPTIONS", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        
        QUIT_BUTTON = Button(image=pygame.image.load("frames/assets/Quit Rect.png"), pos=(640, 550), 
                            text_input="QUIT", font=get_font(75), base_color="#d7fcd4", hovering_color="White")
        

        OUT_BUTTON = Button(image=None, pos=(640, 700), 
                            text_input="SIGN OUT", font=get_font(25), base_color="#d7fcd4", hovering_color="White")

        SCREEN.blit(MENU_TEXT, MENU_RECT)

        for button in [PLAY_BUTTON, OPTIONS_BUTTON, QUIT_BUTTON, OUT_BUTTON]:
            button.changeColor(MENU_MOUSE_POS)
            button.update(SCREEN)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if PLAY_BUTTON.checkForInput(MENU_MOUSE_POS):
                    play()
                if OPTIONS_BUTTON.checkForInput(MENU_MOUSE_POS):
                    options()
                if QUIT_BUTTON.checkForInput(MENU_MOUSE_POS):
                    pygame.quit()
                    sys.exit()
                if OUT_BUTTON.checkForInput(MENU_MOUSE_POS):
                    login_page()


        pygame.display.update()

login_page()