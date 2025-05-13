# utils/socket_json.py
import json, socket

def recv_json_line(sock: socket.socket) -> dict:
    """
    Receive a single JSON object terminated by '\n'.
    Keeps any extra bytes in an internal buffered file object,
    so multiple packets in one TCP chunk are handled correctly.
    """
    if not hasattr(sock, "_json_fp"):
        # buffer size 0 = system default; binary read/write
        sock._json_fp = sock.makefile("rwb", buffering=0)
    line = sock._json_fp.readline()      # blocks until newline
    if not line:
        raise ConnectionResetError("Socket closed by peer")
    return json.loads(line.decode())
