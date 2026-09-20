import sqlite3
import hashlib

DB_NAME = "ledgeragent.db"


# ==========================================
# Hash password
# ==========================================

def hash_password(password):

    return hashlib.sha256(
        password.encode()
    ).hexdigest()


# ==========================================
# Authenticate user
# ==========================================

def authenticate_user(username, password):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    password_hash = hash_password(password)

    cursor.execute("""
        SELECT id, username, role
        FROM users
        WHERE username = ?
        AND password_hash = ?
    """, (
        username,
        password_hash
    ))

    user = cursor.fetchone()

    conn.close()

    if user:

        return {
            "id": user[0],
            "username": user[1],
            "role": user[2]
        }

    return None


# ==========================================
# Test authentication
# ==========================================

if __name__ == "__main__":

    print("===== LEDGERAGENT AUTHENTICATION TEST =====")

    username = input("Username: ")
    password = input("Password: ")

    user = authenticate_user(username, password)

    if user:

        print("\n✅ LOGIN SUCCESSFUL")

        print("User ID :", user["id"])
        print("Username:", user["username"])
        print("Role    :", user["role"])

    else:

        print("\n❌ INVALID USERNAME OR PASSWORD")