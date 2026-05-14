#!/usr/bin/env python3
"""
Run database migrations from sql files
"""
import os
import sys
import psycopg2
from pathlib import Path

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://autocategory:autocategory123@postgres:5432/autocategory"
)

def run_migrations():
    """Run all SQL migration files in order"""
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        print("No migrations directory found")
        return True
    
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        print("No migration files found")
        return True
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create migrations tracking table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        for migration_file in migration_files:
            filename = migration_file.name
            
            # Check if already applied
            cursor.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s",
                (filename,)
            )
            
            if cursor.fetchone():
                print(f"  ⏭️  Skip {filename} (already applied)")
                continue
            
            print(f"  🔄 Running {filename}")
            
            # Read and execute migration
            with open(migration_file, 'r', encoding='utf-8') as f:
                sql = f.read()
            
            cursor.execute(sql)
            
            # Mark as applied
            cursor.execute(
                "INSERT INTO schema_migrations (filename) VALUES (%s)",
                (filename,)
            )
            
            print(f"  ✅ Applied {filename}")
        
        cursor.close()
        conn.close()
        
        print("✅ All migrations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    print("==> Running database migrations")
    success = run_migrations()
    sys.exit(0 if success else 1)
