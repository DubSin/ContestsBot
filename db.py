import sqlite3


class BoTDb:
    def __init__(self, db):
        self.db = sqlite3.connect(db)
        self.cursor = self.db.cursor()

    def add_user(self, user_id, name):
        try:
            self.cursor.execute("INSERT INTO 'event_members' ('user_id', 'user_name') VALUES (?, ?)", (user_id, name))
            return self.db.commit()
        except sqlite3.IntegrityError:
            pass

    def add_event(self, date, time, text, image, fake):
        try:
            datetime = date + " " + time
            self.cursor.execute("INSERT INTO 'event_list' ('datetime', 'event_text', 'image', 'fake') VALUES (?, ?, "
                                "?, ?)",
                                (datetime, text, image, fake))
            return self.db.commit()
        except sqlite3.IntegrityError:
            pass

    def event_exists(self):
        result = self.cursor.execute("SELECT * FROM `event_list`")
        return bool(len(result.fetchall()))

    def del_event(self):
        self.cursor.execute("DELETE FROM 'event_list'")
        self.cursor.execute("DELETE FROM 'event_members'")
        return self.db.commit()

    def get_event_details(self):
        result = self.cursor.execute("SELECT * FROM `event_list`")
        return result.fetchone()

    def get_members(self):
        result = self.cursor.execute("SELECT user_id, user_name FROM `event_members`")
        return result.fetchall()

    def get_member_by_id(self, user_name):
        result = self.cursor.execute("SELECT user_id FROM `event_members` WHERE `user_name` = ?", (user_name,))
        return result.fetchone()
