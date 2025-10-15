import pytest
import os
import sys
from datetime import date, datetime, time, timedelta
from sqlalchemy import create_engine
import sqlalchemy.orm as saorm

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modell import Base, mitarbeiter, Zeiteintrag, Abwesenheit, Benachrichtigungen


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine for each test"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test session for each test"""
    Session = saorm.sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_mitarbeiter(test_session):
    """Create a sample employee for testing"""
    m = mitarbeiter(
        name="Max Mustermann",
        password="test123",
        vertragliche_wochenstunden=40,
        geburtsdatum=date(1990, 1, 1),
        gleitzeit=0,
        letzter_login=date.today()
    )
    test_session.add(m)
    test_session.commit()
    return m


@pytest.fixture
def sample_zeiteintrag(test_session, sample_mitarbeiter):
    """Create a sample time entry for testing"""
    z = Zeiteintrag(
        mitarbeiter_id=sample_mitarbeiter.mitarbeiter_id,
        zeit=time(9, 0),
        datum=date.today(),
        validiert=False
    )
    test_session.add(z)
    test_session.commit()
    return z
