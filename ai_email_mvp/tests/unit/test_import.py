import pytest
from fastapi.testclient import TestClient

def test_import_fastapi():
    assert TestClient is not None