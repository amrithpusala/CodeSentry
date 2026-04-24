"""
Intentional bugs for CodeSentry demo — DO NOT merge to production.
"""

import os
import sqlite3

# Bug 1: Hardcoded secrets
API_KEY = "sk-prod-abc123XYZsecretkey9999"
DB_PASSWORD = "superSecretP@ssw0rd!"


# Bug 2: SQL injection — user input concatenated directly into query
def get_user(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    return cursor.fetchall()


# Bug 3: Divide by zero — no guard on denominator
def compute_average(total, count):
    return total / count


# Bug 4: Unclosed file handle — open() without close() or context manager
def read_config(path):
    f = open(path, "r")
    data = f.read()
    return data


# Bug 5: Command injection — os.system with unsanitized user input
def ping_host(hostname):
    os.system("ping -c 1 " + hostname)


# Bug 6: O(n^3) when O(n) would do — finds duplicates with triple nested loop
def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(len(items)):
            for k in range(len(items)):
                if i != j and items[i] == items[j] and items[j] == items[k]:
                    if items[i] not in duplicates:
                        duplicates.append(items[i])
    return duplicates


# Bug 7: Memory-wasteful — builds entire list in memory instead of yielding
def read_large_file(path):
    lines = []
    with open(path, "r") as f:
        for line in f:
            lines.append(line.strip())
    return lines

