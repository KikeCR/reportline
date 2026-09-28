import pytest

from app import create_app


@pytest.fixture
def client(db):
    app = create_app()
    app.testing = True
    return app.test_client()
