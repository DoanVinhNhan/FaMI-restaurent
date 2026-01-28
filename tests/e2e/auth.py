from playwright.sync_api import Page, expect

class AuthHelper:
    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def login(self, username: str = "admin", password: str = "password"):
        """
        Logs in the user via the login page.
        """
        self.page.goto(f"{self.base_url}/login/")
        self.page.fill("input[name='username']", username)
        self.page.fill("input[name='password']", password)
        self.page.click("button[type='submit']")
        
        # Check for error message
        if self.page.locator(".alert-danger").is_visible():
            error_text = self.page.inner_text(".alert-danger")
            raise Exception(f"Login failed with error: {error_text}")

        # Wait for redirection to dashboard or meaningful content
        # Adjust selector based on actual dashboard content
        expect(self.page).to_have_url(f"{self.base_url}/dashboard/")
        print(f"DEBUG: Post-Login Cookies: {self.page.context.cookies()}")
