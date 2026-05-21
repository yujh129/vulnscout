import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from vulnscout.models.db import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
