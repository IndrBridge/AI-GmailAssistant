import sqlite3
import os
from pathlib import Path

def run_migration():
    # Get the database path
    db_path = Path(__file__).parent.parent / "app.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    print(f"Running migration on database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Read and execute the SQL script
        sql_path = Path(__file__).parent / "add_name_to_users.sql"
        with open(sql_path, 'r') as f:
            sql = f.read()
            cursor.execute(sql)
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
