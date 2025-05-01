import socket
import threading
import json
import logging
import os
import sys
    
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from player import Player  
from database import DatabaseHandler

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class ChessServer:
    def __init__(self):
        logging.basicConfig(
            filename="app.log", 
            level=logging.DEBUG, 
            format="%(asctime)s - %(levelname)s - %(message)s"
        )
        
        self.host = '127.0.0.1'
        self.port = 5555

        self.db_handler = DatabaseHandler()
        self.server_socket = None

        # All connected clients: { client_socket: Player() }
        self.clients = {}

        # Track active games in a dict: game_id -> { "white": sock, "black": sock, "current_turn": "white"/"black" }
        self.active_games = {}

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server listening on {self.host}:{self.port}")

        self.generate_keys()
        print("GENERATED RSA KEYS")

        self.accept_clients()

    def accept_clients(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Client connected from {addr}")

            self.clients[client_socket] = Player()
            self.clients[client_socket].set_status("enc")

            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        # 1) Send public key
        self.set_encryption(client_socket)

        # 2) Login
        self.handle_login(client_socket)

        # 3) Handle further requests
        self.handle_req(client_socket)

    def handle_req(self, client_socket):
        while True:
            data = self.get_message(client_socket)
            if not data:
                logging.error("Empty data or client disconnected.")
                return

            try:
                received_dict = json.loads(data)
            except:
                logging.error("Failed to parse JSON from client.")
                continue

            msg_type = received_dict.get('type')

            if msg_type == "request_game":
                self.handle_game_request(
                    client_socket, 
                    received_dict.get('time'), 
                    received_dict.get('game_type'), 
                    received_dict.get('friend_username')
                )

            elif msg_type == "add_friend":
                self.handle_friend_add(client_socket, received_dict['username'])

            elif msg_type == "view_profile":
                self.handle_profile_view(client_socket)

            elif msg_type == "password_change":
                self.handle_password_change(
                    client_socket, 
                    old_password=received_dict['old_password'],
                    new_password=received_dict['new_password']
                )

            elif msg_type == "move":
                self.handle_game_move(client_socket, received_dict)

            else:
                logging.warning(f"Unknown request type: {msg_type}")

    # ---------------------------
    #    MATCHMAKING & GAMES
    # ---------------------------
    def handle_game_request(self, client_socket, time_format, game_type, other_username=None):
        """
        Put user in wait_for_game. If another user also waiting, match them -> start_game.
        """
        print(f"Got game request: {time_format}, {game_type}, friend: {other_username}")

        self.clients[client_socket].set_status(f"wait_for_game:{time_format}")

        matched_socket = None
        for s, p in self.clients.items():
            if s != client_socket and p.get_status() == f"wait_for_game:{time_format}":
                matched_socket = s
                break

        if matched_socket:
            print(f"Matched {self.clients[client_socket].get_username()} with {self.clients[matched_socket].get_username()}")
            self.start_game(client_socket, matched_socket, time_format)
        else:
            message = {"type": "game_update", "status": "WAITING"}
            self.send_message(client_socket, json.dumps(message).encode())

    def start_game(self, player1_socket, player2_socket, time_format):
        """
        We pick which socket is white or black, store them in active_games, and send OK.
        Let's assume player1 is 'white' and player2 is 'black'.
        """
        game_id = f"{id(player1_socket)}_{id(player2_socket)}"
        print(f"Game id: {game_id}")

        self.active_games[game_id] = {
            "white": player1_socket,
            "black": player2_socket,
            "current_turn": "white"
        }

        # Mark them ingame
        self.clients[player1_socket].set_status("ingame")
        self.clients[player2_socket].set_status("ingame")

        message = {"type": "game_update", "status": "OK"}
        self.send_message(player1_socket, json.dumps(message).encode())
        self.send_message(player2_socket, json.dumps(message).encode())

        print(f"Game started between {self.clients[player1_socket].get_username()} "
              f"and {self.clients[player2_socket].get_username()} (game_id = {game_id})")

    def handle_game_move(self, client_socket, move_data):
        """
        Move data format:
            {
              "type": "move",
              "from": [row1, col1],
              "to": [row2, col2]
            }
        We check if it's the correct player's turn, then forward to the opponent with "opponent_move".
        We also switch current_turn.
        """
        game_id = None
        player_color = None
        # 1) Find which active game this socket belongs to
        for gid, info in self.active_games.items():
            if info["white"] == client_socket:
                game_id = gid
                player_color = "white"
                break
            elif info["black"] == client_socket:
                game_id = gid
                player_color = "black"
                break

        if not game_id:
            print("handle_game_move: No active game found for this socket. Ignoring move.")
            return

        game_info = self.active_games[game_id]
        if game_info["current_turn"] != player_color:
            # Not this player's turn
            print(f"handle_game_move: Not {player_color}'s turn. Ignoring move.")
            # Optionally send an error
            error_msg = {
                "type": "move",
                "status": "ERROR",
                "reason": "Not your turn"
            }
            self.send_message(client_socket, json.dumps(error_msg).encode())
            return

        # 2) It's the correct turn, so forward the move to the opponent
        if player_color == "white":
            opponent_socket = game_info["black"]
            game_info["current_turn"] = "black"
        else:
            opponent_socket = game_info["white"]
            game_info["current_turn"] = "white"

        forward_message = {
            "type": "opponent_move",
            "from": move_data.get("from"),
            "to": move_data.get("to")
        }
        self.send_message(opponent_socket, json.dumps(forward_message).encode())

        print(f"Forwarded {player_color}'s move {forward_message} to opponent")

    # ---------------------------
    #     LOGIN & SIGNUP
    # ---------------------------
    def handle_login(self, client_socket):
        data = self.get_message(client_socket)
        if not data:
            logging.error("Empty data in handle_login()")
            return

        try:
            received_dict = json.loads(data)
        except:
            logging.error("Could not parse login data.")
            return

        msg_type = received_dict.get('type', '')
        if msg_type not in ["login_request", "signup_request"]:
            logging.error(f"Unknown login command {msg_type}")
            return

        username = received_dict['username']
        password = received_dict['password']
        self.clients[client_socket].set_status("login")

        if msg_type == "login_request":
            print("S: Step 1")
            try:
                self.db_handler.create_user(username, password)
                response = {"type": "login_request", "status": "OK"}
                client_socket.send(json.dumps(response).encode('utf-8'))

                self.clients[client_socket].set_username(username)
                self.clients[client_socket].set_status("main_menu")
                logging.info(f"User '{username}' logged in successfully.")
            except:
                if self.db_handler.verify_user_credentials(username, password):
                    print("S: Step 2")
                    response = {"type": "login_request", "status": "OK"}
                    client_socket.send(json.dumps(response).encode('utf-8'))

                    self.clients[client_socket].set_username(username)
                    self.clients[client_socket].set_status("main_menu")
                    logging.info(f"User '{username}' logged in successfully.")
                else:
                    response = {
                        "type": "login_request",
                        "status": "ERROR",
                        "reason": "Invalid credentials"
                    }
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    logging.info(f"Invalid login attempt for '{username}'.")

        elif msg_type == "signup_request":
            created = self.db_handler.create_user(username, password)
            if created:
                response = {"type": "signup_request", "status": "OK"}
                client_socket.send(json.dumps(response).encode('utf-8'))

                self.clients[client_socket].set_username(username)
                self.clients[client_socket].set_status("main_menu")
                logging.info(f"User '{username}' created and logged in.")
            else:
                response = {
                    "type": "signup_request",
                    "status": "ERROR",
                    "reason": "Username taken"
                }
                client_socket.send(json.dumps(response).encode('utf-8'))
                logging.info(f"Signup failed: '{username}' is already taken.")

    # ---------------------------
    #    FRIENDS & PROFILE
    # ---------------------------
    def handle_friend_add(self, client_socket, friend_username):
        current_username = self.clients[client_socket].get_username()
        print(f"Got a friend add request, from '{current_username}' to '{friend_username}'")

        friend_record = self.db_handler.get_user_by_username(friend_username)
        if not friend_record:
            print(f"Friend add failed: '{friend_username}' does not exist.")
            response = {
                "type": "add_friend",
                "status": "ERROR",
                "reason": "User does not exist"
            }
            self.send_message(client_socket, json.dumps(response).encode())
            return

        self.db_handler.update_friends(current_username, friend_username)
        self.clients[client_socket].add_friend(friend_username)

        response = {"type": "add_friend", "status": "OK"}
        self.send_message(client_socket, json.dumps(response).encode())
        print(f"'{friend_username}' added to '{current_username}' friends list in DB.")

    def handle_profile_view(self, client_socket):
        current_username = self.clients[client_socket].get_username()
        profile_info = self.db_handler.get_profile_info(current_username)

        if not profile_info:
            response = {
                "type": "profile_info",
                "status": "ERROR",
                "reason": "User not found"
            }
        else:
            response = {
                "type": "profile_info",
                "status": "OK",
                "games_played": profile_info["games"],
                "elo": profile_info["elo"],
                "as_white": profile_info["as_white"],
                "as_black": profile_info["as_black"],
                "friends": profile_info["friends"]
            }

        self.send_message(client_socket, json.dumps(response).encode())

    # ---------------------------
    #  PASSWORD CHANGE
    # ---------------------------
    def handle_password_change(self, client_socket, old_password, new_password):
        current_username = self.clients[client_socket].get_username()
        print(f"Got a password change request from '{current_username}' -> '{new_password}'")

        if not self.db_handler.verify_user_credentials(current_username, old_password):
            print("Old password does not match. Password update failed.")
            response = {
                "type": "password_change",
                "status": "ERROR",
                "reason": "Old password is incorrect"
            }
            self.send_message(client_socket, json.dumps(response).encode())
            return

        success = self.db_handler.update_password(current_username, new_password)
        if success:
            print("Password updated successfully.")
            response = {"type": "password_change", "status": "OK"}
        else:
            print("Password update failed. Possibly user not found?")
            response = {
                "type": "password_change",
                "status": "ERROR",
                "reason": "User not found"
            }

        self.send_message(client_socket, json.dumps(response).encode())

    # ---------------------------
    #   NETWORKING / ENCRYPTION
    # ---------------------------
    def send_message(self, client_socket, message):
        client_socket.send(message)

    def generate_keys(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def set_encryption(self, client_socket):
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        client_socket.send(pem)

    def get_message(self, client_socket):
        try:
            data = client_socket.recv(4096)
            if not data:
                return None

            decrypted = self.private_key.decrypt(
                data,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            return decrypted.decode('utf-8')
        except Exception as e:
            logging.error(f"Error receiving/decrypting message: {e}")
            return None

if __name__ == "__main__":
    server = ChessServer()
    server.start_server()
