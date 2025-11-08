#!/usr/bin/env python3
"""
Migrate placement tables to latest schema
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.database import engine
from sqlalchemy import text

def migrate():
    print("="*60)
    print("PLACEMENT TABLES MIGRATION")
    print("="*60)
    
    with engine.connect() as conn:
        print("\n1. Dropping old placement tables...")
        try:
            conn.execute(text("DROP TABLE IF EXISTS placement_plans CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS placement_profiles CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS placement_users CASCADE;"))
            conn.commit()
            print("   ✓ Old tables dropped")
        except Exception as e:
            print(f"   ⚠ Error dropping tables: {e}")
        
        print("\n2. Creating new placement tables...")
        from app.config.database import Base
        from app.models import placement_models
        
        Base.metadata.create_all(bind=engine)
        print("   ✓ New tables created")
        
        print("\n3. Verifying schema...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        if 'placement_plans' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('placement_plans')]
            print(f"   ✓ placement_plans columns: {columns}")
        
        if 'placement_profiles' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('placement_profiles')]
            print(f"   ✓ placement_profiles columns: {columns}")
        
        if 'placement_users' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('placement_users')]
            print(f"   ✓ placement_users columns: {columns}")
    
    print("\n" + "="*60)
    print("✅ MIGRATION COMPLETE")
    print("="*60)
    print("\nYou can now restart the server:")
    print("  uvicorn app.main:app --reload\n")

if __name__ == "__main__":
    confirm = input("⚠️  This will drop and recreate placement tables. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        migrate()
    else:
        print("Cancelled.")
