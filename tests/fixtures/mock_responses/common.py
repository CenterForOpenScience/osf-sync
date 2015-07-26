from sqlalchemy import orm, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base

engine = create_engine('sqlite://')
Base.metadata.create_all(engine)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)