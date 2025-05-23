# ────────────────────────────────────────────────────────────────────
#  pages/AnalysisPage.py
#  Game replay with Stockfish eval + best move + scrollable move list
#  Revision-6  (scroll support for long games)
# ────────────────────────────────────────────────────────────────────
import os, threading, traceback
import pygame, chess
from base_page import BasePage
from frames.assets.button import Button
from ChessEngine import ChessEngine

# ────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────
def _nice_score_white(score_obj: chess.engine.PovScore) -> str:
    """Positive = White is better, negative = Black is better."""
    if score_obj.is_mate():
        side = "White" if score_obj.mate() > 0 else "Black"
        return f"{side} mates in {abs(score_obj.mate())}"
    cp = score_obj.score()
    return "N/A" if cp is None else f"{cp/100:.2f}"

def _load_imgs(folder: str):
    imgs = {}
    for col in ("white", "black"):
        for pc in ("king","queen","rook","bishop","knight","pawn"):
            pth = os.path.join(folder,f"{col}_{pc}.png")
            if os.path.isfile(pth):
                imgs[f"{col}_{pc}"] = pygame.transform.scale(
                    pygame.image.load(pth), (100,100))
    return imgs

def _piece_key(sym: str):
    col = "white" if sym[-1]=="W" else "black"
    name = {"K":"king","Q":"queen","R":"rook",
            "B":"bishop","N":"knight","P":"pawn"}[sym[0].upper()]
    return f"{col}_{name}"

# ────────────────────────────────────────────────────────────────────
class AnalysisPage(BasePage):
    LIGHT, DARK = (240,217,181), (181,136,99)

    ROW_H        = 22
    LIST_TOP_Y   = 240
    LIST_X       = 820
    LIST_HEIGHT  = 750 - LIST_TOP_Y     # until just above “Result” text

    def __init__(self, manager, move_history, player_color,
                 result, client, key, engine_depth=14):
        super().__init__(manager)

        # ————— state ——————————————————————————————
        self.move_history = move_history         # list of ply tuples
        self.player_color = (player_color or "white").lower()
        self.result       = result
        self.client, self.key = client, key

        # ————— board visuals ——————————————————————
        self.board_px, self.sq_px = 800, 100
        self.flip_board = self.player_color.startswith("b")
        self.images     = _load_imgs("chess pieces")

        font = lambda s: pygame.font.SysFont(None, s)
        self.f_sm, self.f_md, self.f_lg = map(font,(26,30,42))

        self.btn_left  = Button(None,(820,170),"<",   self.f_lg,"White","Green")
        self.btn_right = Button(None,(950,170),">",   self.f_lg,"White","Green")
        self.btn_back  = Button(None,(1030,780),"BACK",self.f_lg,"White","Red")

        # ————— chess & engine ————————————————————
        self.board  = chess.Board()
        self.index  = len(move_history)                  # start at last ply
        n           = len(move_history)+1
        self.evals  = ["…"]*n
        self.best   = ["…"]*n

        # scrolling state
        self.rows_visible = self.LIST_HEIGHT // self.ROW_H
        self.list_top_idx = max(0, self.index - self.rows_visible + 1)

        self.depth  = engine_depth
        self.engine = ChessEngine(depth=self.depth)

        threading.Thread(target=self._analyse, daemon=True).start()

    # ——— engine analysis thread ———————————————————————
    def _analyse(self):
        try:
            eng   = self.engine._open()
            limit = chess.engine.Limit(depth=self.depth)
            tmp   = chess.Board()

            for ply in range(len(self.move_history)+1):
                info           = eng.analyse(tmp, limit)
                self.evals[ply] = _nice_score_white(info["score"].white())
                pv = info.get("pv")
                self.best[ply] = tmp.san(pv[0]) if pv else "—"

                if ply < len(self.move_history):
                    frm,to,_ = self.move_history[ply]
                    tmp.push(chess.Move.from_uci(self._tuple2uci((frm,to))))
        except Exception as e:
            print("[AnalysisPage] Engine error:", e)
            traceback.print_exc()
            self.evals = ["N/A"]*len(self.evals)
            self.best  = ["—"] *len(self.best)
        finally:
            try: eng.quit()
            except: pass

    # ——— utilities ————————————————————————————————
    @staticmethod
    def _tuple2uci(move):
        (r1,c1),(r2,c2) = move
        s = lambda r,c: chess.square(c,r)
        return chess.square_name(s(r1,c1))+chess.square_name(s(r2,c2))

    def _board_to_gui(self,pos):
        r,c=pos
        return (r if self.flip_board else 7-r, c)

    # ——— scrolling helpers ————————————————————————
    def _ensure_visible(self):
        """Auto-scroll so current ply stays in view."""
        if self.index < self.list_top_idx:
            self.list_top_idx = self.index
        elif self.index >= self.list_top_idx + self.rows_visible:
            self.list_top_idx = self.index - self.rows_visible + 1

    def _scroll(self, delta_rows: int):
        max_top = max(0, len(self.move_history) - self.rows_visible)
        self.list_top_idx = max(0, min(max_top, self.list_top_idx + delta_rows))

    # ——— navigation ————————————————————————————————
    def _jump(self, idx):
        idx = max(0, min(len(self.move_history), idx))
        if idx == self.index: return
        self.board = chess.Board()
        for frm,to,_ in self.move_history[:idx]:
            self.board.push(chess.Move.from_uci(self._tuple2uci((frm,to))))
        self.index = idx
        self._ensure_visible()

    # ——— event handling ————————————————————————————
    def handle_events(self, evts):
        mouse = pygame.mouse.get_pos()
        for e in evts:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_back.checkForInput(mouse):
                    self.manager.set_current_page("MainMenuPage",
                                                  client=self.client,key=self.key)
                    return
                if self.btn_left.checkForInput(mouse):  self._jump(self.index-1)
                if self.btn_right.checkForInput(mouse): self._jump(self.index+1)

            elif e.type == pygame.MOUSEWHEEL:
                # wheel over move list scrolls list; elsewhere navigates board
                if mouse[0] >= self.LIST_X:
                    self._scroll(-e.y)            # y=1 scroll up
                else:
                    self._jump(self.index - e.y)

            elif e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_LEFT,pygame.K_a):  self._jump(self.index-1)
                elif e.key in (pygame.K_RIGHT,pygame.K_d): self._jump(self.index+1)
                elif e.key == pygame.K_PAGEUP:           self._scroll(-self.rows_visible)
                elif e.key == pygame.K_PAGEDOWN:         self._scroll(self.rows_visible)

    # ——— drawing ————————————————————————————————
    def draw(self):
        self.screen.fill((25,25,25))

        # 1. squares
        for gr in range(8):
            br = gr if self.flip_board else 7-gr
            for c in range(8):
                pygame.draw.rect(
                    self.screen,
                    self.LIGHT if (br+c)%2==0 else self.DARK,
                    (c*self.sq_px,gr*self.sq_px,self.sq_px,self.sq_px))

        # 2. pieces
        for sq in chess.SQUARES:
            p=self.board.piece_at(sq)
            if not p: continue
            key=_piece_key(p.symbol()+("W" if p.color else "B"))
            r,c = chess.square_rank(sq), chess.square_file(sq)
            gr,gc = self._board_to_gui((r,c))
            self.screen.blit(self.images[key],
                             (gc*self.sq_px, gr*self.sq_px))

        # 3. move list (scrollable)
        y = self.LIST_TOP_Y
        start = self.list_top_idx
        end   = min(len(self.move_history), start + self.rows_visible)
        for i in range(start, end):
            frm,to,_ = self.move_history[i]
            colour = (200,200,30) if i+1==self.index else (230,230,230)
            txt = f"{i+1:>2}. {self._tuple2uci((frm,to))}"
            self.screen.blit(self.f_sm.render(txt,True,colour),(self.LIST_X,y))
            y += self.ROW_H

        # 4. evaluation & best move
        self.screen.blit(self.f_md.render(
            f"Score: {self.evals[self.index]}",True,(255,255,255)),
            (self.LIST_X,60))
        self.screen.blit(self.f_md.render(
            f"Best move: {self.best[self.index]}",True,(180,230,255)),
            (self.LIST_X,90))

        # 5. result & buttons
        self.screen.blit(self.f_md.render(f"Result: {self.result}",
                                          True,(255,255,255)), (10,750))
        for b in (self.btn_left,self.btn_right,self.btn_back):
            b.changeColor(pygame.mouse.get_pos()); b.update(self.screen)

    def update(self): pass
