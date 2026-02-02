from peewee import SqliteDatabase, PostgresqlDatabase
import os

# Use your existing logic to determine DB type
if os.getenv('DB_HOST'):
    db = PostgresqlDatabase(
        'instagram_farm',
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        host=os.getenv('DB_HOST'),
        port=5432
    )
else:
    db = SqliteDatabase('instagram_farm.db')

def migrate():
    print("Adding 'group_name' to Account table...")
    try:
        db.connect()
        # Add column (nullable)
        db.execute_sql("ALTER TABLE account ADD COLUMN group_name TEXT DEFAULT NULL")
        print("Success.")
    except Exception as e:
        print(f"Migration error (Column likely exists): {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
