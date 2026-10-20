import os

# Set test configuration before importing app.py (which creates the app at import time).
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("MAX_CONTENT_LENGTH", "1024")

from app import app
from data import alchemy
from model.user import UserModel
from werkzeug.security import check_password_hash


def setup_function():
    with app.app_context():
        alchemy.drop_all()
        alchemy.create_all()


def test_signup_hashes_password_and_never_returns_it():
    client = app.test_client()
    password = "S3nh@ComAcentuação"
    response = client.post(
        "/signup",
        json={"username": "gabriel", "password": password},
    )

    assert response.status_code == 201
    assert "password" not in response.get_json()

    with app.app_context():
        account = UserModel.find_by_name("gabriel")
        assert account is not None
        assert account.password != password
        assert check_password_hash(account.password, password)


def test_signup_rejects_short_password():
    response = app.test_client().post(
        "/signup",
        json={"username": "gabriel", "password": "curta"},
    )
    assert response.status_code == 400


def test_signup_rejects_invalid_json_body():
    response = app.test_client().post(
        "/signup",
        data="not-json",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_signup_rejects_duplicate_username():
    client = app.test_client()
    payload = {"username": "gabriel", "password": "S3nh@Forte123"}
    assert client.post("/signup", json=payload).status_code == 201
    assert client.post("/signup", json=payload).status_code == 409


def test_request_body_limit_is_enforced():
    response = app.test_client().post(
        "/signup",
        data=(" " * 2048),
        content_type="application/json",
    )
    assert response.status_code == 413
