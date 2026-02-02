import sqlite3
import os

DB_FILE = 'instagram_farm.db'
OUTPUT_FILE = 'recovered_targets.txt'

def export_targets():
    if not os.path.exists(DB_FILE):
        print(f"Error: {DB_FILE} not found.")
        return

    print(f"Connecting to {DB_FILE}...")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Select only pending ones so we don't re-follow people
    try:
        cursor.execute("SELECT username FROM target WHERE status = 'pending'")
        rows = cursor.fetchall()
        
        if not rows:
            print("No pending targets found.")
            return

        print(f"Found {len(rows)} pending targets. Saving to {OUTPUT_FILE}...")
        
        with open(OUTPUT_FILE, 'w') as f:
            for row in rows:
                clean_name = row[0].strip()
                if clean_name:
                    f.write(f"{clean_name}\n")
        
        print("Done! You can now delete the database safely.")

    except Exception as e:
        print(f"Error extracting: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_targets()
