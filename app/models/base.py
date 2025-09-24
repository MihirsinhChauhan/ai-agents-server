"""
SQLAlchemy Base Model

Provides the declarative base for SQLAlchemy models used in the application.
This is separate from Pydantic models which are used for API serialization.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the base class for all SQLAlchemy models
Base = declarative_base()