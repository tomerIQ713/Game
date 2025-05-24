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
        self.host, self.port = "192.168.1.201", 5555
        self.server_socket = None
        self.db = DatabaseHandler()

        self.clients: dict[socket.socket, Player] = {}

        self.active_games: dict[str, dict] = {}

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

    
    def _main_loop(self, sock):
        while True:
            msg = self._recv_json(sock)
            if msg is None:
                break
            t = msg.get("type")

            if t == "request_game":
                self._queue_for_game(sock, msg["time"], msg["game_type"],
                                     msg.get("friend_username"))

            elif t == "move":
                self._relay_move(sock, msg)

            elif t == "time_out":
                self._handle_time_out(sock, msg["game_id"],
                                      msg["loser"], msg["winner"])

            elif t == "list_games":
                self._handle_list_games(sock)

            elif t == "spectate_request":
                self._handle_spectate_request(sock, msg["game_id"])

            elif t == "add_friend":
                self._handle_add_friend(sock, msg["username"])

            elif t == "list_friend_requests":
                self._handle_list_friend_requests(sock)

            elif t == "respond_friend_request":
                self._handle_respond_friend(sock, msg["from_user"], msg["accept"])

            elif t == "send_game_request":
                self._handle_send_game_request(sock,
                                               msg["to"], msg["time_format"])

            elif t == "list_game_requests":
                self._handle_list_game_requests(sock)

            elif t == "respond_game_request":
                self._handle_respond_game_request(sock,
                                                  msg["from_user"], msg["accept"])
            elif t == "password_change":
                self._handle_password_change(sock, msg)

            elif t == "view_profile":
                self._handle_view_profile(sock)
            
            elif t == "game_result":
                self._handle_game_result(sock, msg)

            else:
                self._send_json(sock, {"type": "error",
                                       "msg": f"Unknown cmd {t}"})
    
    def _handle_send_game_request(self, sock, target, time_fmt):
        me = self.clients[sock].get_username()
        ok = self.db.send_game_request(me, target, time_fmt)
        self._send_json(sock, {
            "type": "send_game_request_ack",
            "success": ok,
            "msg": "Request sent!" if ok else "Cannot send request."
        })
    
    def _handle_password_change(self, sock, msg):
        """
        Handle a password-change request.  Expects:
          { "type":"password_change",
            "old_password": "<old>",
            "new_password": "<new>" }
        Replies with status OK or ERROR+reason.
        """
        user = self.clients[sock].username
        old  = msg.get("old_password","")
        new  = msg.get("new_password","")

        if not self.db.verify_user_credentials(user, old):
            return self._send_json(sock, {
                "type":   "password_change",
                "status": "ERROR",
                "reason": "Old password incorrect"
            })

        if self.db.update_password(user, new):
            return self._send_json(sock, {
                "type":   "password_change",
                "status": "OK"
            })
        else:
            return self._send_json(sock, {
                "type":   "password_change",
                "status": "ERROR",
                "reason": "Could not update password"
            })


    
    def _find_socket_by_username(self, uname):
        for s, c in self.clients.items():
            if c.get_username() == uname:
                return s
        return None

    def _handle_game_result(self, sock, msg):
        """
        msg = { "type":"game_result",
                "game_id": "...",
                "result":  "white"|"black"|"draw" }
        """
        gid    = msg.get("game_id")
        result = msg.get("result")
        info   = self.active_games.get(gid)
        if not info or result not in ("white","black","draw"):
            return

        packet = {"type":"game_end","result":result}
        for s in (info["white"], info["black"], *info.get("spectators",[])):
            try:
                self._send_json(s, packet)
            except OSError:
                pass

        white_user = self.clients[info["white"]].get_username()
        black_user = self.clients[info["black"]].get_username()
        self.db.record_game_result(white_user, black_user, result)

        self.active_games.pop(gid, None)


    def _handle_time_out(self, sock, gid, loser, winner):
        """
        Extend your existing time-out handler:
          • Notify clients
          • THEN call record_game_result(white,black,'white' or 'black')
          • Finally remove the game.
        """
        info = self.active_games.get(gid)
        if not info:
            return

        # 1) standard notifications (same as before)
        packet = {"type": "time_out", "loser": loser, "winner": winner}
        for s in (info["white"], info["black"], *info.get("spectators",[])):
            try: self._send_json(s, packet)
            except: pass

        # 2) record in DB
        white_user = self.clients[info["white"]].get_username()
        black_user = self.clients[info["black"]].get_username()
        # winner == 'white' or 'black'
        self.db.record_game_result(white_user, black_user, winner)

        # 3) remove
        self.active_games.pop(gid, None)


    def _handle_list_game_requests(self, sock):
        me  = self.clients[sock].get_username()
        lst = self.db.get_pending_game_requests(me)
        self._send_json(sock, {"type": "game_requests", "list": lst})

    def _handle_respond_game_request(self, sock, sender, accept: bool):
        me = self.clients[sock].get_username()
    
        if accept:
            time_fmt = self.db.accept_game_request(sender, me)
            if not time_fmt:
                self._send_json(sock, {"type": "respond_game_ack", "ok": False})
                return
    
            self._send_json(sock, {"type": "respond_game_ack", "ok": True})
    
            peer_sock = self._find_socket_by_username(sender)
            if peer_sock:
                self._send_json(peer_sock, {"type": "respond_game_ack", "ok": True})
    
            self._queue_for_game(sock,       time_fmt, "friend_game",
                                 friend_username=sender)
            if peer_sock:
                self._queue_for_game(peer_sock, time_fmt, "friend_game",
                                     friend_username=me)
    
        else: 
            self.db.reject_game_request(sender, me)
            self._send_json(sock, {"type": "respond_game_ack", "ok": True})


    
    def _handle_add_friend(self, sock, target):
        me  = self.clients[sock].get_username()
        ok  = self.db.send_friend_request(me, target)
        out = {"type": "add_friend_ack",
               "success": ok,
               "msg": "Request sent!" if ok else "Cannot send request."}
        self._send_json(sock, out)

    def _handle_list_friend_requests(self, sock):
        me   = self.clients[sock].get_username()
        lst  = self.db.get_pending_requests(me)
        self._send_json(sock, {"type": "friend_requests", "list": lst})
    
    def _handle_respond_friend(self, sock, sender, accept: bool):
        me = self.clients[sock].get_username()
        if accept:
            self.db.accept_request(sender, me)
        else:
            self.db.reject_request(sender, me)
        self._send_json(sock, {"type": "respond_friend_ack", "ok": True})


    def _handle_view_profile(self, sock):
        """
        Send the logged-in user’s profile to the client.

        Packet format expected by progfile_page.py:
            {
                "type"        : "profile_info",
                "games_played": int,
                "elo"         : int,
                "friends"     : list[str],        
                "as_white"    : [w, d, l],
                "as_black"    : [w, d, l]
            }
        """

        username = self.clients[sock].get_username()
        stats    = self.db.get_profile_info(username)         

        if not stats:
            self._send_json(sock, {"type": "error",
                                   "msg":  "Profile not found"})
            return

        packet = {
            "type":         "profile_info",
            "games_played": stats["games"],     
            "elo":          stats["elo"],
            "friends":      stats["friends"],
            "as_white":     stats["as_white"],
            "as_black":     stats["as_black"]
        }
        self._send_json(sock, packet)


    def _queue_for_game(self, sock, time_format, game_type,
                    friend_username: str | None = None):
        """
        Put *sock* in the appropriate queue.

        › game_type == "Random"      →   use the global random queue  
        › game_type == "friend_game" →   pair with friend_username
        """
        self.clients[sock].set_status(f"waiting:{time_format}")
        opp = next((s for s, p in self.clients.items()
                    if s is not sock and p.get_status() == f"waiting:{time_format}"), None)
        if opp:
            self._start_game(sock, opp, time_format)
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
        if "fen" in data:                 
            packet["fen"] = data["fen"]
            info["fen"] = data["fen"]

        opp = info["black"] if mover == "white" else info["white"]
        self._send_json(opp, packet)
        self._send_json(sock, {"type": "move_ack", "status": "OK"})

        for spec in list(info["spectators"]):
            try:
                self._send_json(spec, packet)
            except OSError:               
                info["spectators"].remove(spec)

        info["current_turn"] = "black" if mover == "white" else "white"

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
