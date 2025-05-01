# network.py
import socket
import pickle
import threading

class NetworkClient:
    def __init__(self, host='127.0.0.1', port=50000):
        self.host = host
        self.port = port
        self.socket = None
        self.listener_thread = None
        self.incoming_messages = []
        self.connected = False

    def connect(self):
        """
        Connect to the server and start the background listener thread.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))
        self.connected = True
        print(f"Connected to server at {self.host}:{self.port}")

        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def listen(self):
        """
        Continuously read data from the server, store or handle it.
        """
        while True:
            try:
                data = self.socket.recv(4096)
                if not data:
                    break
                message = pickle.loads(data)
                self.incoming_messages.append(message)
            except OSError:
                break
            except Exception as e:
                print("Error in NetworkClient.listen:", e)
                break

        self.connected = False
        print("Disconnected from server.")

    def send(self, data):
        """
        Send data (dict, etc.) to the server.
        """
        if not self.connected:
            print("Not connected to server!")
            return
        try:
            self.socket.sendall(pickle.dumps(data))
        except Exception as e:
            print("Error sending data:", e)

    def close(self):
        if self.socket:
            self.socket.close()
        self.connected = False
        self.socket = None
