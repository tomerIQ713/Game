
import os, json, time, threading, pygame, chess
from frames.assets.button import Button
from chess_board import ChessBoard
from base_page import BasePage
from ChessEngine import ChessEngine
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


class GameBoardPage(BasePage):
    THEMES = [
        {"bg": (0, 0, 0),        "text": (255, 255, 255)},
        {"bg": (255, 255, 255),  "text": (0,   0,   0)},
        {"bg": (0, 70, 160),     "text": (255, 255, 255)},
    ]

    # ──────────────────────────────────────────────────────────────
    def __init__(self, manager, client, selected_time_format,
                 key, player_color, current_turn,
                 game_id=None, vs_engine=False, engine_depth=16):
        super().__init__(manager)

        self.vs_engine    = vs_engine
        self.client       = client
        self.rsa_pubkey   = key
        self.player_color = player_color
        self.current_turn = current_turn
        self.game_id      = game_id
        self.selected_time_format = selected_time_format
        self.flip_board   = (self.player_color == "white")  

        self.chess_board    = ChessBoard()
        self.selected_piece = None
        self.disable_clicks = (self.player_color != self.current_turn)

        self.move_history  = []          
        self.history_index = 0
        self.last_move     = None         

        base, inc          = self.parse_time_format(self.selected_time_format)
        self.timers        = {"white": float(base), "black": float(base)}
        self.time_increment= inc
        self._clock_last   = time.time()

        self.board_px      = 800
        self.square        = self.board_px // 8
        self.light, self.dark = (240, 217, 181), (181, 136, 99)
        self.piece_images  = self.load_imgs("chess pieces")

        self.font_medium   = pygame.font.SysFont(None, 40)
        self.arrow_left    = Button(None,(805,200),"<", self.font_medium,"White","Green")
        self.arrow_right   = Button(None,(960,200),">", self.font_medium,"White","Green")
        self.leave_btn     = Button(None,(1050,780),"LEAVE GAME", self.font_medium,"White","Red")

        self.game_over     = False
        self.winner        = None
        self.analyze_btn   = None

        self.engine_bot    = ChessEngine(depth=engine_depth) if vs_engine else None

        self.partial_buffer = ""
        self.running = True
        if not self.vs_engine and self.client:
            threading.Thread(target=self.listen_loop, daemon=True).start()

        if self.vs_engine and self.player_color == "black":
            threading.Thread(target=self._engine_move, daemon=True).start()

        threading.Thread(target=self._clock_loop, daemon=True).start()

    def _clock_loop(self):
        """Updates the active player’s clock and stops the game
        immediately when somebody’s flag falls."""
        while self.running:
            now = time.time()
            dt  = now - self._clock_last
            self._clock_last = now

            if (self.history_index == len(self.move_history)) and (not self.game_over):
                side = self.current_turn
                self.timers[side] = max(0, self.timers[side] - dt)

                if self.timers[side] == 0:
                    self.game_over  = True
                    self.winner     = "White" if side == "black" else "Black"
                    self.disable_clicks = True
                    self.analyze_btn = Button(
                        None, (930, 640), "ANALYZE GAME",
                        self.font_medium, "White", "Green")

                    self._enc_send({
                        "type":   "time_out",
                        "game_id": self.game_id,
                        "loser":   side,
                        "winner":  self.winner.lower()
                    })

            time.sleep(0.05)    

    @staticmethod
    def parse_time_format(text):
        if not text: return 600, 0
        lower = text.lower()
        if "hour" in lower:          return 3600, 0
        if "rapid: 30" in text:      return 30*60, 0
        if text.startswith("Rapid"): return 10*60, 0
        if text.startswith("Blitz"): return 3*60, 1
        if text.startswith("Bullet"):return 60, 1
        return 600, 0

    @staticmethod
    def load_imgs(folder):
        imgs = {}
        for col in ("white", "black"):
            for name in ("king","queen","rook","bishop","knight","pawn"):
                p = os.path.join(folder, f"{col}_{name}.png")
                if os.path.exists(p):
                    imgs[f"{col}_{name}"] = pygame.transform.scale(
                        pygame.image.load(p), (100, 100))
        return imgs

    def board_to_gui(self, pos): r,c = pos; return (7-r, c) if self.flip_board else (r, c)
    def gui_to_board(self, pos): r,c = pos; return (7-r, c) if self.flip_board else (r, c)

    @staticmethod
    def _code_to_key(code):
        if not code: return None
        colour = "white" if code[-1].upper() == "W" else "black"
        piece  = code[:-1].lower().replace("pown","pawn")
        piece  = {"p":"pawn","r":"rook","n":"knight",
                  "b":"bishop","q":"queen","k":"king"}.get(piece, piece)
        return f"{colour}_{piece}"


    def _decode_multi_json(self, s):
        dec, out, i, n = json.JSONDecoder(), [], 0, len(s)
        while i < n:
            while i < n and s[i].isspace(): i += 1
            if i >= n: break
            try:
                obj, j = dec.raw_decode(s, i)
                out.append(obj); i = j
            except json.JSONDecodeError:
                break
        return out, i

    def listen_loop(self):
        while self.running:
            time.sleep(0.05)
            self.client.setblocking(False)
            try:
                data = self.client.recv(4096)
            except BlockingIOError:
                data = b""
            finally:
                self.client.setblocking(True)
            if not data:
                continue
            self.partial_buffer += data.decode("utf-8", "replace")
            packets, idx = self._decode_multi_json(self.partial_buffer)
            self.partial_buffer = self.partial_buffer[idx:]
            for pkt in packets:
                self._handle_packet(pkt)

    def _handle_packet(self, msg):
        t = msg.get("type")
        if t == "opponent_move":
            if self.history_index != len(self.move_history):
                self.history_index = len(self.move_history)
                self._rebuild_board()

            mover = self.current_turn
            frm, to = tuple(msg["from"]), tuple(msg["to"])
            self._apply_move(frm, to)
            self.move_history.append((frm, to, mover))
            self.history_index = len(self.move_history)
            self.timers[mover] += self.time_increment
            self.current_turn = "black" if mover == "white" else "white"
            self.disable_clicks = (self.player_color != self.current_turn)
            self._check_game_end()

        elif t == "time_out":
            if not self.game_over:
                self.game_over = True
                self.winner = msg.get("winner", "").capitalize()
                self.disable_clicks = True
                self.analyze_btn = Button(
                    None, (930, 640), "ANALYZE GAME",
                    self.font_medium, "White", "Green")

    def _enc_send(self, obj):
        if self.vs_engine or not self.client or not self.rsa_pubkey:
            return
        raw = json.dumps(obj, separators=(',', ':')).encode()
        enc = self.rsa_pubkey.encrypt(
            raw,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                         algorithm=hashes.SHA256(), label=None))
        self.client.send(enc)

    def _apply_move(self,frm,to):
        self.chess_board.make_move(frm,to,self.current_turn)
        self.last_move=(frm,to)        

    def _try_local_move(self,frm,to):
        if not self.chess_board.make_move(frm,to,self.current_turn):
            return False
        self.last_move=(frm,to)
        self.timers[self.current_turn]+=self.time_increment
        self.move_history.append((frm,to,self.current_turn))
        self.history_index=len(self.move_history)
        fen_now=self.chess_board.engine.board_to_fen(
            self.chess_board.get_normal_board(),
            turn=("B" if self.current_turn=="white" else "W"))
        self._enc_send({"type":"move","game_id":self.game_id,
                        "from":list(frm),"to":list(to),
                        "clock":round(self.timers[self.current_turn],2),
                        "fen":fen_now})
        self.current_turn="black" if self.current_turn=="white" else "white"
        self.disable_clicks=self.vs_engine or True
        self._check_game_end()
        if self.vs_engine and not self.game_over:
            threading.Thread(target=self._engine_move,daemon=True).start()
        return True

    def _engine_move(self):
        time.sleep(0.3)
        fen=self.chess_board.engine.board_to_fen(
            self.chess_board.get_normal_board(),
            turn=('W' if self.current_turn=='white' else 'B'))
        best=self.engine_bot.get_best_moves(fen,1)[0][0]
        board=chess.Board(fen)
        try: mv=chess.Move.from_uci(best)
        except: mv=board.parse_san(best)
        brd=lambda sq:(chess.square_rank(sq), chess.square_file(sq))
        frm,to=brd(mv.from_square), brd(mv.to_square)
        self._apply_move(frm,to)
        self.move_history.append((frm,to,self.current_turn))
        self.history_index=len(self.move_history)
        self.timers[self.current_turn]+=self.time_increment
        self.current_turn=self.player_color
        self.disable_clicks=False
        self._check_game_end()

    def _check_game_end(self):
        if self.game_over: 
            return

        fen = self.chess_board.engine.board_to_fen(
            self.chess_board.get_normal_board(),
            turn=('W' if self.current_turn=='white' else 'B'))

        board = chess.Board(fen)
        if board.is_game_over():
            self.game_over = True
            res = board.result()  
            if res == "1-0":
                self.winner = "White"
            elif res == "0-1":
                self.winner = "Black"
            else:
                self.winner = "Draw"

            if self.client and not self.vs_engine:
                self._enc_send({
                    "type":    "game_result",
                    "game_id": self.game_id,
                    "result":  self.winner.lower()  
                })

            self.disable_clicks = True
            self.analyze_btn = Button(
                None, (930, 640), "ANALYZE GAME",
                self.font_medium, "White", "Green")

    def handle_events(self,events):
        mouse=pygame.mouse.get_pos()
        for ev in events:
            if ev.type==pygame.MOUSEBUTTONDOWN:
                if self.leave_btn.checkForInput(mouse):
                    self.running=False
                    self.manager.set_current_page("MainMenuPage",
                        client=self.client,key=self.rsa_pubkey); return
                if self.game_over and self.analyze_btn and self.analyze_btn.checkForInput(mouse):
                    self.running=False
                    self.manager.set_current_page("AnalysisPage",
                        move_history=self.move_history,
                        player_color=self.player_color,
                        result=self.winner, client = self.client, key = self.rsa_pubkey); return
                if self.arrow_left.checkForInput(mouse) and self.history_index>0:
                    self.history_index-=1; self._rebuild_board()
                elif self.arrow_right.checkForInput(mouse) and self.history_index<len(self.move_history):
                    self.history_index+=1; self._rebuild_board()
                if (not self.disable_clicks and
                    self.history_index==len(self.move_history) and
                    mouse[0]<self.board_px and mouse[1]<self.board_px):
                    col_gui,row_gui=mouse[0]//self.square, mouse[1]//self.square
                    pos_board=self.gui_to_board((row_gui,col_gui))
                    if self.selected_piece is None:
                        name,_=self.chess_board.get_piece_possible_moves(pos_board)
                        if name!="None":
                            code=self.chess_board.get_normal_board()[pos_board[0]][pos_board[1]]
                            if (code and ((code.endswith("W") and self.player_color=="white") or
                                          (code.endswith("B") and self.player_color=="black"))):
                                self.selected_piece=pos_board
                    else:
                        self._try_local_move(self.selected_piece,pos_board)
                        self.selected_piece=None
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_LEFT and self.history_index>0:
                    self.history_index-=1; self._rebuild_board()
                elif ev.key==pygame.K_RIGHT and self.history_index<len(self.move_history):
                    self.history_index+=1; self._rebuild_board()

    def update(self):
        pass      

    def draw(self):
        th=self.THEMES[getattr(self.game_state,"selected_theme",0)%3]
        self.screen.fill(th["bg"])
        self._draw_board()

        if self.history_index==len(self.move_history) and self.last_move:
            for sq in self.last_move:
                gr,gc=self.board_to_gui(sq)
                overlay=pygame.Surface((self.square,self.square),pygame.SRCALPHA)
                overlay.fill((255,255,0,80))                # yellow with alpha
                self.screen.blit(overlay,(gc*self.square,gr*self.square))

        self._draw_pieces()

        if self.selected_piece:
            gr,gc=self.board_to_gui(self.selected_piece)
            pygame.draw.rect(self.screen,(0,255,0),
                             (gc*self.square,gr*self.square,self.square,self.square),3)
            _,moves=self.chess_board.get_piece_possible_moves(self.selected_piece)
            for mr,mc in moves:
                gr2,gc2=self.board_to_gui((mr,mc))
                pygame.draw.rect(self.screen,(255,0,0),
                                 (gc2*self.square,gr2*self.square,
                                  self.square,self.square),3)

        for idx,col in enumerate(("white","black")):
            t=int(self.timers[col]); txt=f"{col.capitalize()}: {t//60:02}:{t%60:02}"
            self.screen.blit(self.font_medium.render(txt,True,th["text"]),
                             (820,50+idx*40))
        self.screen.blit(self.font_medium.render(f"You are {self.player_color.capitalize()}",
                                                 True,th["text"]),(820,140))
        status=("Live" if self.history_index==len(self.move_history)
                else "Start position" if self.history_index==0
                else f"Move {self.history_index}/{len(self.move_history)}")
        colour=(0,255,0) if status=="Live" else (255,0,0)
        self.screen.blit(self.font_medium.render(status,True,colour),(840,180))

        for btn,active in ((self.arrow_left,self.history_index>0),
                           (self.arrow_right,self.history_index<len(self.move_history))):
            btn.base_color="White" if active else (120,120,120)
            btn.hovering_color="Green" if active else (120,120,120)
            btn.changeColor(pygame.mouse.get_pos()); btn.update(self.screen)

        self.leave_btn.changeColor(pygame.mouse.get_pos()); self.leave_btn.update(self.screen)
        if self.game_over:
            self.screen.blit(self.font_medium.render(f"Result: {self.winner}",
                                                     True,(255,215,0)),(820,600))
            self.analyze_btn.changeColor(pygame.mouse.get_pos()); self.analyze_btn.update(self.screen)

    def _draw_board(self):
        for gr in range(8):
            br=7-gr if self.flip_board else gr
            for c in range(8):
                col=self.light if (br+c)%2==0 else self.dark
                pygame.draw.rect(self.screen,col,
                                 (c*self.square,gr*self.square,self.square,self.square))

    def _draw_pieces(self):
        board=self.chess_board.get_normal_board()
        for br in range(8):
            for c in range(8):
                code=board[br][c]; key=self._code_to_key(code)
                if key and key in self.piece_images:
                    gr=7-br if self.flip_board else br
                    self.screen.blit(self.piece_images[key],
                                     (c*self.square,gr*self.square))

    def _rebuild_board(self):
        self.chess_board.set_board()
        for frm,to,_ in self.move_history[:self.history_index]:
            self.chess_board.make_move(frm,to,"white")   
        self.last_move=None
        if self.history_index>0:
            last=self.move_history[self.history_index-1]
            self.last_move=(last[0],last[1])
