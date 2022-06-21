import sqlite3
from sqlite3 import Error
import json


# param db_file: the database we want to connect to
# return conn: a Connection object that represents the db_file database
# create a db connection to the SQLite database specified by db_file
def create_connection(db_file):

    conn = None

    try:
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = 1")
        print("Connection to SQLite established")

    except Error as e:
        print(e)

    return conn


# this creates all the tables in the memoSystem database
# param conn: Connection object
# param sql_create_statement: CREATE TABLE statement
def create_table(conn, sql_create_statement):
    try:
        cursor = conn.cursor()
        cursor.execute(sql_create_statement)

    except Error as e:
        print(e)


def create_memo_statement():
    memo_table_statement = '''CREATE TABLE IF NOT EXISTS memos(
                                id INTEGER PRIMARY KEY,
                                content TEXT,
                                last_edited_by TEXT NOT NULL,
                                FOREIGN KEY (last_edited_by) REFERENCES sessions (id)
                                );'''
    return memo_table_statement


def create_sessions_statement():
    session_table_statement = '''CREATE TABLE IF NOT EXISTS sessions(
                                    id TEXT PRIMARY KEY
                                    );'''
    return session_table_statement


def get_session_by_id(conn, session_id):

    rows = None

    select_statement = '''SELECT * FROM sessions 
                          WHERE id = ?'''
    try:
        cursor = conn.cursor()
        cursor.execute(select_statement, (session_id,))
        rows = cursor.fetchall()

    except Error as e:
        print("Failed to query sessions table in database.\n")
        print(e)

    return rows


def get_memo_by_id(conn, memo_id):

    rows = None

    select_statement = '''SELECT * FROM memos
                          WHERE id = ?'''

    try:
        cursor = conn.cursor()
        cursor.execute(select_statement, (memo_id,))
        rows = cursor.fetchall()

    except Error as e:
        print("Failed to query memo table in database\n")
        print(e)

    return rows


def get_all_memos(conn):

    rows = None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memos")
        rows = cursor.fetchall()

    except Error as e:
        print("Fetching memos failed.")
        print(e)

    return rows


def add_memo(conn, content, session_id):
    last_row = None

    insert_statement = "INSERT INTO memos(content, last_edited_by) VALUES(?,?)"
    try:
        cursor = conn.cursor()
        cursor.execute(insert_statement, (content, session_id))
        conn.commit()
        last_row = cursor.lastrowid

    except Error as e:
        print("Failed to add memo to database.\n")
        print(e)

    return last_row


def add_session(conn, session_id):
    last_row = None

    insert_statement = "INSERT INTO sessions(id) VALUES(?)"
    try:
        cursor = conn.cursor()
        cursor.execute(insert_statement, (session_id,))
        conn.commit()
        last_row = cursor.lastrowid

    except Error as e:
        print("Failed to add session to database.\n")
        print(e)

    return last_row


def update_memo_by_id(conn, memo_id, session_id, content):
    success = 0

    update_statement = '''UPDATE memos
                          SET content = ?, last_edited_by = ?
                          WHERE id = ?'''
    try:
        cursor = conn.cursor()
        cursor.execute(update_statement, (content, session_id, memo_id))
        conn.commit()
        success = 1
    except Error as e:
        print("Failed to update memos")
        print(e)

    return success


def delete_memo_by_id(conn, memo_id):
    success = 0

    delete_statement = "DELETE FROM memos WHERE id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(delete_statement, (memo_id,))
        conn.commit()
        success = 1
    except Error as e:
        print("Failed to delete memo from database.\n")
        print(e)

    return success


def delete_session_by_id(conn, session_id):
    success = 0

    delete_statement = "DELETE FROM memos WHERE id = ?"
    try:
        cursor = conn.cursor()
        cursor.execute(delete_statement, (session_id,))
        conn.commit()
        success = 1
    except Error as e:
        print("Failed to delete session from database.\n")
        print(e)

    return success


def delete_all_memos(conn):
    delete_statement = "DELETE FROM memos"
    try:
        cursor = conn.cursor()
        cursor.execute(delete_statement)
        conn.commit()
    except Error as e:
        print("Failed to delete all memos.\n")
        print(e)


def to_dict_json(keys, values):
    data = {}
    all_data = []
    for value in values:
        for _ in value:
            data = dict(zip(keys, value))
        all_data.append(data)
    return json.dumps(all_data, indent=4)
