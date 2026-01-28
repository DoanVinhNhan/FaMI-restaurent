import pytest
from playwright.sync_api import Page
from tests.e2e.auth import AuthHelper

# Default base URL if not specified in pytest.ini or command line
# Assuming Django runserver runs on localhost:8000
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

@pytest.fixture(scope="session")
def base_url():
    return DEFAULT_BASE_URL

@pytest.fixture(scope="function")
def auth(page: Page, base_url):
    """
    Fixture to provide authenticated access.
    Usage: def test_something(auth): ...
    """
    helper = AuthHelper(page, base_url)
    helper.login() # Default admin login
    return helper

@pytest.fixture(scope="function")
def page_context(page: Page, base_url):
    """
    Fixture providing page and base_url for non-auth tests.
    """
    return page, base_url
