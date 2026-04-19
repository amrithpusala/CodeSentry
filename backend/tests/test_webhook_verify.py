# webhook verification test — intentionally contains issues for CodeSentry to catch

import os
import sqlite3

SECRET_KEY = "hardcoded-secret-1234"  # hardcoded secret
DB_PATH = "/tmp/test.db"


def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # SQL injection: user input concatenated directly into query
    query = "SELECT * FROM users WHERE id = " + str(user_id)
    cursor.execute(query)
    return cursor.fetchone()


def process_items(items):
    results = []
    for i in range(len(items)):
        # O(n^2): searching the list inside a loop
        for j in range(len(items)):
            if items[i] == items[j] and i != j:
                results.append(items[i])
    return results


def divide(a, b):
    # missing zero-division check
    return a / b


def read_file(filename):
    # path traversal: unsanitized filename passed directly
    with open("/var/data/" + filename, "r") as f:
        return f.read()
