import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# For local development
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:1234@localhost:5432/exam_prep_db"

# Fix postgres:// to postgresql://
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Force IPv4 for Supabase (add sslmode and prefer_ipv4)
if DATABASE_URL and "supabase.co" in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"
    
    # Use connection pooler for better compatibility
    if "pooler.supabase.com" not in DATABASE_URL:
        print("⚠️  Warning: Use connection pooler URL for better stability")

print(f"📊 Database: {DATABASE_URL[:50]}...")

# Create engine with IPv4 preference
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection health
    pool_size=5,
    max_overflow=10,
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10
    } if "supabase" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
