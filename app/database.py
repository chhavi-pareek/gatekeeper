"""
Database configuration and connection management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# SQLite database file path
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gaas_gateway.db")

# Create SQLite engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize the database by creating all tables.
    """
    # Import all models to ensure they're registered with Base.metadata
    # Import at function level to avoid circular imports
    from app.models import Gateway, Route, User, Service, UsageLog, ApiKey, RequestHash, MerkleRoot
    from sqlalchemy import inspect, text
    
    Base.metadata.create_all(bind=engine)
    
    # Check if api_key_revealed column exists in users table, add it if missing
    inspector = inspect(engine)
    if 'users' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('users')]
        if 'api_key_revealed' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN api_key_revealed BOOLEAN DEFAULT 0"))
                conn.commit()
    
    # ApiKey table is created automatically by Base.metadata.create_all
    # Existing User.api_key entries will continue to work via backward compatibility in get_current_user
    
    # Check if new rate limit override columns exist in api_keys table, add them if missing
    if 'api_keys' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('api_keys')]
        if 'rate_limit_requests' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE api_keys ADD COLUMN rate_limit_requests INTEGER"))
                conn.commit()
        if 'rate_limit_window_seconds' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE api_keys ADD COLUMN rate_limit_window_seconds INTEGER"))
                conn.commit()
        # Check if new billing columns exist in api_keys table, add them if missing
        if 'price_per_request' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE api_keys ADD COLUMN price_per_request REAL DEFAULT 0.001"))
                conn.commit()
        if 'total_cost' not in columns:
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE api_keys ADD COLUMN total_cost REAL DEFAULT 0.0"))
                conn.commit()