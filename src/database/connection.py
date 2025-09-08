"""
Database connection helper for FastAPI dependency injection
"""

from sqlalchemy.orm import Session
from .db_manager import TradingDBManager

# Global database manager instance
db_manager = TradingDBManager()

def get_db_session() -> Session:
    """
    FastAPI dependency to provide database session
    """
    session = db_manager.Session()
    try:
        yield session
    finally:
        session.close()