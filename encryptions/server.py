import socket
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

class ServerRSA:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.private_key = None
        self.public_key = None
        self.generate_keys()
    
    def generate_keys(self):
        """Generate RSA key pair."""
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        """Return public key in PEM format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def get_message(self, client_socket):
        """Decrypt a message using the private key."""

        encrypted_message = client_socket.recv(4096)

        return self.private_key.decrypt(
            encrypted_message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def start_server(self):
        """Start the server and handle communication."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(1)
        print("[SERVER] Waiting for client connection...")

        conn, addr = server.accept()
        print(f"[SERVER] Connected to {addr}")

        conn.send(self.get_public_key_pem())
        print("[SERVER] Public key sent to the client.")


        decrypted_message = self.get_message(client_socket=conn)
        print(f"[SERVER] Decrypted message from client: {decrypted_message.decode()}")

        conn.close()
        server.close()


if __name__ == "__main__":
    server = ServerRSA()
    server.start_server()
