import sqlite3
import json
import bcrypt  

DB_NAME = "chess_app.db"

class DatabaseHandler:
    def __init__(self, db_path: str = DB_NAME):
        """
        Initialize the database handler. By default, uses 'chess_app.db'.
        """
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """
        Create the 'users' table if it doesn't exist.
        
        Columns:
          id           -> INTEGER PRIMARY KEY AUTOINCREMENT
          username     -> TEXT (unique)
          password     -> TEXT (hashed password)
          games        -> INTEGER
          elo          -> INTEGER
          friends      -> TEXT (JSON list)
          as_white_w   -> INTEGER
          as_white_d   -> INTEGER
          as_white_l   -> INTEGER
          as_black_w   -> INTEGER
          as_black_d   -> INTEGER
          as_black_l   -> INTEGER
        """
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                games INTEGER NOT NULL DEFAULT 0,
                elo INTEGER NOT NULL DEFAULT 1200,
                friends TEXT DEFAULT '[]',

                as_white_w INTEGER NOT NULL DEFAULT 0,
                as_white_d INTEGER NOT NULL DEFAULT 0,
                as_white_l INTEGER NOT NULL DEFAULT 0,

                as_black_w INTEGER NOT NULL DEFAULT 0,
                as_black_d INTEGER NOT NULL DEFAULT 0,
                as_black_l INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS friend_requests (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                sender   TEXT NOT NULL,
                receiver TEXT NOT NULL,
                status   TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'rejected')),
                UNIQUE(sender, receiver)
            );
            """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                sender      TEXT NOT NULL,
                receiver    TEXT NOT NULL,
                time_format TEXT NOT NULL,                 -- e.g. "5+3"
                status      TEXT NOT NULL
                      CHECK(status IN ('pending','accepted','rejected')),
                UNIQUE(sender, receiver, status)           -- prevent spam
            );
            """)


        connection.commit()
        connection.close()

    def verify_user_credentials(self, username: str, plain_password: str) -> bool:
        """
        Check if user exists in DB, then compare password with hashed password.
        """
        user = self.get_user_by_username(username)
        if not user:
            return False
        stored_hash = user["password"]
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash)

    def create_user(self, username: str, plain_password: str) -> bool:
        """
        Create a new user. Return False if username is taken.
        """
        if self.get_user_by_username(username) is not None:
            return False

        hashed_pw = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt())

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?);",
            (username, hashed_pw)
        )
        connection.commit()
        connection.close()
        return True

    def get_user_by_username(self, username: str):
        """
        Fetch a user record by username. Return dict or None.
        """
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        connection.close()

        if row:
            return self._row_to_dict(row)
        return None

    def update_password(self, username: str, new_plain_password: str) -> bool:
        """
        Update password for the given username. Return True if successful.
        """
        user = self.get_user_by_username(username)
        if not user:
            return False

        hashed_pw = bcrypt.hashpw(new_plain_password.encode('utf-8'), bcrypt.gensalt())

        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET password = ? WHERE username = ?;",
            (hashed_pw, username)
        )
        connection.commit()
        connection.close()
        return True

    def update_friends(self, current_username: str, new_friend_username: str) -> bool:
        """
        Add a friend to the current user's friend list (stored as JSON array of usernames).
        """
        user = self.get_user_by_username(current_username)
        if not user:
            return False

        # Convert existing JSON to Python list
        try:
            friends_list = json.loads(user["friends"])
        except:
            friends_list = []

        # Append if not already in the list
        if new_friend_username not in friends_list:
            friends_list.append(new_friend_username)

        # Save back to DB
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE users SET friends = ? WHERE username = ?;",
            (json.dumps(friends_list), current_username)
        )
        connection.commit()
        connection.close()
        return True

    def get_profile_info(self, username: str) -> dict:
        """
        Retrieve profile info: games, elo, friends, as_white, as_black.
        Return {} if user not found.
        """
        user = self.get_user_by_username(username)
        if not user:
            return {}

        return {
            "games": user["games"],
            "elo": user["elo"],
            "friends": json.loads(user["friends"]) if user["friends"] else [],
            "as_white": [user["as_white_w"], user["as_white_d"], user["as_white_l"]],
            "as_black": [user["as_black_w"], user["as_black_d"], user["as_black_l"]]
        }

    def _row_to_dict(self, row: tuple) -> dict:
        """
        Convert a row tuple into a dict of user fields.
        Matches columns in SELECT * FROM users.
        """
        return {
            'id': row[0],
            'username': row[1],
            'password': row[2],
            'games': row[3],
            'elo': row[4],
            'friends': row[5],
            'as_white_w': row[6],
            'as_white_d': row[7],
            'as_white_l': row[8],
            'as_black_w': row[9],
            'as_black_d': row[10],
            'as_black_l': row[11]
        }
    
    # ─────────────────────────────────────────────────────────────
    # Friend-request helpers
    # ─────────────────────────────────────────────────────────────
    def send_friend_request(self, sender: str, receiver: str) -> bool:
        """
        Insert a new pending request sender → receiver.
        Return False if self-request, already friends, or duplicate.
        """
        if sender == receiver:
            return False
    
        with sqlite3.connect(self.db_path) as c:
            # already friends?
            cur = c.execute("SELECT friends FROM users WHERE username=?", (sender,))
            row = cur.fetchone()
            if not row:
                return False
            friends = json.loads(row[0] or "[]")
            if receiver in friends:
                return False
    
            try:
                c.execute("INSERT INTO friend_requests(sender, receiver, status) "
                          "VALUES (?,?, 'pending')", (sender, receiver))
                return True
            except sqlite3.IntegrityError:
                return False   # duplicate request
    
    
    def get_pending_requests(self, username: str) -> list[str]:
        """Return a list of usernames who sent requests to *username*."""
        with sqlite3.connect(self.db_path) as c:
            cur = c.execute(
                "SELECT sender FROM friend_requests "
                "WHERE receiver=? AND status='pending'", (username,))
            return [r[0] for r in cur.fetchall()]
    
    
    def accept_request(self, sender: str, receiver: str) -> None:
        """Mark request accepted and add each user to the other’s friends list."""
        with sqlite3.connect(self.db_path) as c:
            c.execute("UPDATE friend_requests SET status='accepted' "
                      "WHERE sender=? AND receiver=?", (sender, receiver))
    
            for a, b in ((sender, receiver), (receiver, sender)):
                cur = c.execute("SELECT friends FROM users WHERE username=?", (a,))
                friends = json.loads(cur.fetchone()[0] or "[]")
                if b not in friends:
                    friends.append(b)
                c.execute("UPDATE users SET friends=? WHERE username=?",
                          (json.dumps(friends), a))
    
    
    def reject_request(self, sender: str, receiver: str) -> None:
        """Simply mark the request as rejected."""
        with sqlite3.connect(self.db_path) as c:
            c.execute("UPDATE friend_requests SET status='rejected' "
                      "WHERE sender=? AND receiver=?", (sender, receiver))
    
        # ─────────────────────────────────────────────────────────────
    # Friend-game request helpers
    # ─────────────────────────────────────────────────────────────
    def send_game_request(self, sender: str, receiver: str,
                          time_format: str) -> bool:
        if sender == receiver:
            return False
        with sqlite3.connect(self.db_path) as c:
            # must already be friends
            cur = c.execute("SELECT friends FROM users WHERE username=?", (sender,))
            row = cur.fetchone()
            if not row:
                return False
            friends = json.loads(row[0] or "[]")
            if receiver not in friends:
                return False
            try:
                c.execute("""
                    INSERT INTO game_requests(sender, receiver, time_format, status)
                    VALUES (?,?,?, 'pending')
                """, (sender, receiver, time_format))
                return True
            except sqlite3.IntegrityError:
                return False
    
    
    def get_pending_game_requests(self, username: str) -> list[dict]:
        """Return list of {sender, time_format} dicts."""
        with sqlite3.connect(self.db_path) as c:
            cur = c.execute("""
                SELECT sender, time_format
                FROM game_requests
                WHERE receiver=? AND status='pending'
            """, (username,))
            return [{"sender": r[0], "time_format": r[1]} for r in cur.fetchall()]
    
    
    def accept_game_request(self, sender: str, receiver: str) -> str | None:
        with sqlite3.connect(self.db_path) as c:
            # 1) fetch time-format of the pending request
            cur = c.execute("""
                SELECT time_format FROM game_requests
                WHERE sender=? AND receiver=? AND status='pending'
            """, (sender, receiver))
            row = cur.fetchone()
            if not row:
                return None
            time_format = row[0]
    
            # 2) remove any previous 'accepted' rows for the same two users
            c.execute("""
                DELETE FROM game_requests
                WHERE sender=? AND receiver=? AND status='accepted'
            """, (sender, receiver))
    
            # 3) mark THIS row as accepted
            c.execute("""
                UPDATE game_requests
                SET status='accepted'
                WHERE sender=? AND receiver=? AND status='pending'
            """, (sender, receiver))
    
            return time_format

    
    
    def reject_game_request(self, sender: str, receiver: str) -> None:
        with sqlite3.connect(self.db_path) as c:
            c.execute("""
                UPDATE game_requests SET status='rejected'
                WHERE sender=? AND receiver=? AND status='pending'
            """, (sender, receiver))
    