import json
import mysql.connector
import os
from datetime import datetime

# --- CONFIG ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',  # CHANGE PASSWORD HERE
    'database': 'odp_platform'
}

# Path to users.json (relative to project root)
JSON_FILE_PATH = os.path.join(os.path.dirname(__file__), '../web/data/users.json')

def migrate():
    print("Starting data migration...")

    # 1. Check JSON file
    if not os.path.exists(JSON_FILE_PATH):
        print(f"File not found: {JSON_FILE_PATH}")
        return

    try:
        # 2. Connect to MySQL
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("Database connected.")

        # 3. Load old data
        with open(JSON_FILE_PATH, 'r') as f:
            users_data = json.load(f)

        print(f"Found {len(users_data)} users.")

        count_users = 0
        count_res = 0

        # 4. Insert data
        for username, info in users_data.items():

            # Parse created time
            created_at = info.get('created_at', datetime.now().isoformat())
            try:
                created_at_dt = datetime.fromisoformat(created_at)
            except:
                created_at_dt = datetime.now()

            # Insert or update user
            sql_user = """
                INSERT INTO users (username, email, password_hash, role, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE email=VALUES(email)
            """
            cursor.execute(sql_user, (
                username,
                info.get('email', ''),
                info.get('password', ''),
                info.get('role', 'user'),
                created_at_dt
            ))

            # Get user ID
            user_id = cursor.lastrowid
            if not user_id:
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                user_id = cursor.fetchone()[0]

            count_users += 1

            # Insert reservations
            for res in info.get('reservations', []):
                sql_res = """
                    INSERT IGNORE INTO reservations
                    (id, user_id, vm_count, duration_minutes, status,
                     created_at, expires_at, nodes, final_stats, packages)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_res, (
                    res.get('id'),
                    user_id,
                    res.get('vm_count', 1),
                    res.get('duration', 60),
                    res.get('status', 'expired'),
                    res.get('created_at'),
                    res.get('expires_at'),
                    json.dumps(res.get('nodes', [])),
                    json.dumps(res.get('final_stats', {})),
                    json.dumps(res.get('packages', []))
                ))
                count_res += 1

        conn.commit()
        print(f"Done. Imported {count_users} users and {count_res} reservations.")

    except mysql.connector.Error as err:
        print(f"MySQL error: {err}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
