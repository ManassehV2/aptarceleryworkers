import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#default to sqllite in memory for testing if DB_CONNECTION_STRING empty
SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL = os.getenv("DB_CONNECTION_STRING", "sqlite:///:memory:")



engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()