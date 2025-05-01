import socket
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization, hashes
import hashlib

class ClientRSA:
    def __init__(self, server_ip='127.0.0.1', server_port=12345):
        self.server_ip = server_ip
        self.server_port = server_port
        self.public_key = None
        

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((self.server_ip, self.server_port))

        

    def load_public_key(self, public_pem):
        """Load the server's public key from PEM format."""
        self.public_key = serialization.load_pem_public_key(public_pem)

    def encrypt_message(self, message):
        """Encrypt a message using the server's public key."""
        return self.public_key.encrypt(
            message.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def get_public_key(self):
        public_pem = self.client.recv(4096)
        self.load_public_key(public_pem)

    def send_encrypted_message(self, message):
        """receive the public key, and send an encrypted message."""

        self.get_public_key()


        encrypted_message = self.encrypt_message(message)
        print(encrypted_message)

        self.client.send(encrypted_message)
        print("[CLIENT] Encrypted message sent to the server.")

        self.client.close()
    
    def encrypt_md5(self, message):
        bytes = message.encode('utf-8')
        hash_object = hashlib.md5(bytes)
        return hash_object.hexdigest()

if __name__ == "__main__":
    client = ClientRSA()
    client.send_encrypted_message("Hello, Secure Server!")
