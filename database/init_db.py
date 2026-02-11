from database.db import Base, engine
# MUST import models here so they register with Base.metadata
from database import models 

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("DATABASE TABLES CREATED / VERIFIED")