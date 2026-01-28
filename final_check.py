
import sqlite3
import os

def check_db(path, table):
    if not os.path.exists(path):
        print(f"File {path} NOT FOUND")
        return
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        res = cursor.fetchone()
        if res:
            print(f"Table {table} in {path}: OK")
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  Rows count: {count}")
        else:
            print(f"Table {table} in {path}: MISSING")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"  Existing tables: {tables}")
        conn.close()
    except Exception as e:
        print(f"Error checking {path}: {e}")

def check_js_syntax(path):
    if not os.path.exists(path):
        print(f"File {path} NOT FOUND")
        return
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    braces = 0
    brackets = 0
    parens = 0
    for i, char in enumerate(content):
        if char == '{': braces += 1
        if char == '}': braces -= 1
        if char == '[': brackets += 1
        if char == ']': brackets -= 1
        if char == '(': parens += 1
        if char == ')': parens -= 1
        
        if braces < 0:
            print(f"Unmatched '}}' at index {i}")
            break
        if brackets < 0:
            print(f"Unmatched ']' at index {i}")
            break
        if parens < 0:
            print(f"Unmatched ')' at index {i}")
            break
            
    if braces == 0 and brackets == 0 and parens == 0:
        print(f"JS Braces balance: OK")
    else:
        print(f"JS Balance issue: Braces={braces}, Brackets={brackets}, Parens={parens}")

print("--- DB CHECK ---")
check_db("data/gielda_earning.db", "sp500_earning")
check_db("data/economic_calendar.db", "economic_events")

print("\n--- JS CHECK ---")
check_js_syntax("static/app.js")
