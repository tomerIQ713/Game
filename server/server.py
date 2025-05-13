# server/server.py
import socket, threading, json, logging, os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from player import Player
from database import DatabaseHandler

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes


class ChessServer:
    """
    • Sends its public RSA key immediately after each TCP connection.
    • Accepts either RSA-encrypted JSON or plain JSON.
    • Creates an account automatically on the first login attempt if it
      doesn’t exist yet.
    • Supports: matchmaking, moves, game list for spectators, live spectating.
    """

    def __init__(self):
        logging.basicConfig(filename="app.log",
                            level=logging.DEBUG,
                            format="%(asctime)s | %(levelname)s | %(message)s")
        self.host, self.port = "127.0.0.1", 5555
        self.server_socket = None
        self.db = DatabaseHandler()

        self.clients: dict[socket.socket, Player] = {}
        # active_games[gid] = {
        #     "white": sock, "black": sock,
        #     "current_turn": "white"|"black",
        #     "time_format": str,
        #     "spectators": [sock, ...],
        #     "fen": str | None
        # }
        self.active_games: dict[str, dict] = {}

    # ──────────────────────────────────────────────────────────────
    #                   LIFECYCLE
    # ──────────────────────────────────────────────────────────────
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        print(f"Server running on {self.host}:{self.port}")

        self._make_rsa_keys()

        while True:
            sock, addr = self.server_socket.accept()
            self.clients[sock] = Player()
            print(f"Client {addr} connected")
            threading.Thread(target=self._client_thread,
                             args=(sock,), daemon=True).start()

    def _client_thread(self, sock: socket.socket):
        try:
            self._send_public_key(sock)
            if not self._handle_login(sock):
                return
            self._main_loop(sock)
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            self._cleanup(sock)

    # ──────────────────────────────────────────────────────────────
    #                   LOGIN
    # ──────────────────────────────────────────────────────────────
    def _handle_login(self, sock) -> bool:
        pkt = self._recv_json(sock)
        if not pkt:
            return False

        cmd  = pkt.get("type")
        user = pkt.get("username", "")
        pwd  = pkt.get("password", "")

        if cmd == "login_request":
            if self.db.verify_user_credentials(user, pwd) or self.db.create_user(user, pwd):
                return self._login_ok(sock, user, cmd)
            self._login_fail(sock, cmd, "Invalid password")
            return False

        if cmd == "signup_request":
            if self.db.create_user(user, pwd):
                return self._login_ok(sock, user, cmd)
            self._login_fail(sock, cmd, "Username taken")
            return False

        self._send_json(sock, {"type": "error", "msg": f"Bad login cmd {cmd}"})
        return False

    def _login_ok(self, sock, username, cmd):
        self.clients[sock].set_username(username)
        self.clients[sock].set_status("main_menu")
        self._send_json(sock, {"type": cmd, "status": "OK"})
        print(f"{username} logged in")
        return True

    def _login_fail(self, sock, cmd, reason):
        self._send_json(sock, {"type": cmd, "status": "ERROR", "reason": reason})

    # ──────────────────────────────────────────────────────────────
    #               MAIN MESSAGE LOOP
    # ──────────────────────────────────────────────────────────────
    def _main_loop(self, sock):
        while True:
            msg = self._recv_json(sock)
            if msg is None:
                break
            t = msg.get("type")
            if t == "request_game":
                self._queue_for_game(sock, msg["time"], msg["game_type"], msg.get("friend_username"))
            elif t == "move":
                self._relay_move(sock, msg)
            elif t == "list_games":
                self._handle_list_games(sock)
            elif t == "spectate_request":
                self._handle_spectate_request(sock, msg["game_id"])
            else:
                self._send_json(sock, {"type": "error", "msg": f"Unknown cmd {t}"})

    # ──────────────────────────────────────────────────────────────
    #                 MATCHMAKING
    # ──────────────────────────────────────────────────────────────
    def _queue_for_game(self, sock, time_fmt, game_type, friend=None):
        self.clients[sock].set_status(f"waiting:{time_fmt}")
        opp = next((s for s, p in self.clients.items()
                    if s is not sock and p.get_status() == f"waiting:{time_fmt}"), None)
        if opp:
            self._start_game(sock, opp, time_fmt)
        else:
            self._send_json(sock, {"type": "game_update", "status": "WAITING"})

    def _start_game(self, white, black, time_fmt):
        gid = f"{id(white)}_{id(black)}"
        self.active_games[gid] = {
            "white": white,
            "black": black,
            "current_turn": "white",
            "time_format": time_fmt,
            "spectators": [],
            "fen": None
        }
        for s, col in ((white, "white"), (black, "black")):
            self.clients[s].set_status("ingame")
            self._send_json(s, {
                "type": "game_start",
                "game_id": gid,
                "color": col,
                "time_format": time_fmt,
                "current_turn": "white"
            })
        print(f"Game {gid} started")

    # ──────────────────────────────────────────────────────────────
    #                 LIVE GAME LIST / SPECTATE
    # ──────────────────────────────────────────────────────────────
    def _handle_list_games(self, sock):
        games = []
        for gid, info in self.active_games.items():
            games.append({
                "game_id": gid,
                "white": self.clients[info["white"]].get_username(),
                "black": self.clients[info["black"]].get_username(),
                "time_format": info.get("time_format", "-")
            })
        self._send_json(sock, {"type": "games_list", "games": games})

    def _handle_spectate_request(self, sock, game_id):
        info = self.active_games.get(game_id)
        if not info:
            self._send_json(sock, {"type": "spectate_accept",
                                   "status": "ERROR", "reason": "Game not found"})
            return
        info.setdefault("spectators", []).append(sock)
        self._send_json(sock, {"type": "spectate_accept",
                               "status": "OK",
                               "game_id": game_id,
                               "fen": info.get("fen"),
                               "color_to_move": info["current_turn"]})

    # ──────────────────────────────────────────────────────────────
    #                 MOVE RELAY
    # ──────────────────────────────────────────────────────────────
    def _relay_move(self, sock, data):
        gid = data.get("game_id")
        info = self.active_games.get(gid)
        if not info:
            self._send_json(sock, {"type": "move_ack", "status": "ERROR", "reason": "No such game"})
            return

        mover = "white" if info["white"] is sock else "black"
        if info["current_turn"] != mover:
            self._send_json(sock, {"type": "move_ack", "status": "ERROR", "reason": "Not your turn"})
            return

        packet = {
            "type": "opponent_move",
            "from": data["from"],
            "to":   data["to"],
            "clock": data.get("clock")
        }
        if "fen" in data:                 # include latest snapshot
            packet["fen"] = data["fen"]
            info["fen"] = data["fen"]

        opp = info["black"] if mover == "white" else info["white"]
        self._send_json(opp, packet)
        self._send_json(sock, {"type": "move_ack", "status": "OK"})

        # broadcast to spectators
        for spec in list(info["spectators"]):
            try:
                self._send_json(spec, packet)
            except OSError:               # drop dead sockets
                info["spectators"].remove(spec)

        info["current_turn"] = "black" if mover == "white" else "white"

    # ──────────────────────────────────────────────────────────────
    #           ENCRYPTION  /  IO HELPERS
    # ──────────────────────────────────────────────────────────────
    def _make_rsa_keys(self):
        self._priv = rsa.generate_private_key(65537, 2048)
        self._pub  = self._priv.public_key()

    def _send_public_key(self, sock):
        pem = self._pub.public_bytes(serialization.Encoding.PEM,
                                     serialization.PublicFormat.SubjectPublicKeyInfo)
        sock.send(pem)

    def _recv_json(self, sock):
        try:
            raw = sock.recv(4096)
            if not raw:
                return None
            if raw.lstrip()[:1] in (b'{', b'['):
                return json.loads(raw.decode("utf-8"))

            try:
                plain = self._priv.decrypt(
                    raw,
                    padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                                 algorithm=hashes.SHA256(), label=None))
                return json.loads(plain.decode("utf-8"))
            except (ValueError, TypeError):
                logging.warning("Undecipherable packet dropped")
                return None
        except Exception as e:
            logging.error(f"_recv_json exception: {e}")
            return None

    def _send_json(self, sock, obj: dict):
        try:
            sock.send(json.dumps(obj, separators=(',', ':')).encode("utf-8"))
        except OSError:
            pass

    # ──────────────────────────────────────────────────────────────
    #                   CLEAN-UP
    # ──────────────────────────────────────────────────────────────
    def _cleanup(self, sock):
        print("Client disconnected")
        try:
            sock.close()
        except OSError:
            pass
        self.clients.pop(sock, None)
        for gid in [g for g, i in self.active_games.items() if sock in (i["white"], i["black"])]:
            del self.active_games[gid]


if __name__ == "__main__":
    ChessServer().start_server()
