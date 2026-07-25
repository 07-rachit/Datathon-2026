import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app import models, auth

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    user = models.User(
        name="Admin Test",
        email="admin@test.local",
        hashed_password=auth.hash_password("password123"),
        role=models.RoleEnum.admin,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def investigator_user(db_session):
    user = models.User(
        name="Investigator Test",
        email="investigator@test.local",
        hashed_password=auth.hash_password("password123"),
        role=models.RoleEnum.investigator,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def viewer_user(db_session):
    user = models.User(
        name="Viewer Test",
        email="viewer@test.local",
        hashed_password=auth.hash_password("password123"),
        role=models.RoleEnum.viewer,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user):
    token = auth.create_access_token({"sub": admin_user.id, "role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def investigator_headers(investigator_user):
    token = auth.create_access_token({"sub": investigator_user.id, "role": investigator_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user):
    token = auth.create_access_token({"sub": viewer_user.id, "role": viewer_user.role.value})
    return {"Authorization": f"Bearer {token}"}
