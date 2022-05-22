import os
import sqlite3
from time import sleep
from pathlib import Path
sleep(20)

class SQL:
    def __init__(self, database):
        def dict_factory(cursor, row):
            dictionary = {}
            for idx, col in enumerate(cursor.description):
                dictionary[col[0]] = row[idx]
            return dictionary
        self.connection = sqlite3.connect(database, timeout=100, check_same_thread=False)
        self.connection.execute('PRAGMA journal_mode = WAL;')
        self.connection.execute('PRAGMA synchronous = OFF;')
        self.connection.row_factory = dict_factory
        self.cursor = self.connection.cursor()

    def close(self):
        self.connection.close()

    def request(self, sql, fetchone=None):
        with self.connection:
            self.cursor.execute(sql)
        result = self.cursor.fetchone() if fetchone else self.cursor.fetchall()
        return dict(result) if result and fetchone else result


def insert_items(record: dict):
    values = []
    for key, value in record.items():
        if value is None:
            values.append('NULL')
        elif type(value) == dict:
            values.append(f'"{value}"')
        else:
            values.append(f"'{value}'")
    return ', '.join(values)


def emoji_summary(folder_path):
    all_values = []
    for path in os.listdir(folder_path):
        if path.startswith('emoji_set') and path.endswith('.db'):
            emoji_db = SQL(folder_path.joinpath(path))
            records = emoji_db.request('SELECT * FROM emoji')
            for record in records:
                all_values.append(f"({insert_items(record)})")
            emoji_db.close()
    all_values.clear()
    return all_values


def emoji_generation(path=Path(__file__).resolve().parent):
    db = SQL(path.joinpath('emoji.db'))
    db.request(f'CREATE TABLE IF NOT EXISTS emoji (key TEXT UNIQUE, emoji TEXT, data TEXT)')
    db.request(f"REPLACE INTO emoji (key, emoji, data) VALUES {', '.join(emoji_summary(path))}")
    db.close()
    return path.joinpath('emoji.db')


emojis_path = emoji_generation()
