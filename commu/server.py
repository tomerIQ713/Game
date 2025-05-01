# server.py
import socket
import threading
import pickle
import os

HOST = '127.0.0.1'
PORT = 50000
USERS_FILE = "users.txt"

class ChessServer:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server listening on {self.host}:{self.port}")

        self.load_users()

        self.clients = []


        self.current_turn = "white"


        threading.Thread(target=self.accept_clients, daemon=True).start()

    def load_users(self):
        """
        Load users from a simple text file.
        Format: each line =>  username:password
        We'll store it in a dict: self.users[username] = password
        """
        self.users = {}
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if ':' in line:
                        uname, pwd = line.split(':', 1)
                        self.users[uname] = pwd

    def save_users(self):
        """
        Persist the self.users dictionary to a file.
        """
        with open(USERS_FILE, "w") as f:
            for uname, pwd in self.users.items():
                f.write(f"{uname}:{pwd}\n")

    def accept_clients(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Client connected from {addr}")

            self.clients.append(client_socket)

            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()

    def handle_client(self, client_socket):
        """
        Handle messages from this client in a loop.
        For example, 'login' messages, moves, resign, etc.
        """
        while True:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break

                message = pickle.loads(data)
                

            except Exception as e:
                print("Error in handle_client:", e)
                break

        print("A client disconnected.")
        client_socket.close()

    def process_login(self, username, password):
        """
        If user doesn't exist, create a new record.
        If user exists, check the password.
        Return (success, reason).
        """
        if username in self.users:
            # user already exists
            if self.users[username] == password:
                return True, f"Welcome back {username}!"
            else:
                return False, "Incorrect password."
        else:
            # create new user
            self.users[username] = password
            self.save_users()
            return True, f"New user created. Welcome, {username}!"

    def broadcast(self, data):
        """
        Send the same data to all clients.
        """
        for c in self.clients:
            try:
                c.sendall(pickle.dumps(data))
            except:
                pass

if __name__ == "__main__":
    ChessServer()
