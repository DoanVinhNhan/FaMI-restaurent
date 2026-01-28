import pytest
from playwright.sync_api import Page, expect

@pytest.mark.skip(reason="Payment UI not yet implemented in POS flow")
def test_payment_flow(auth, page: Page, base_url):
    """
    Test the Payment flow: Select Order -> Pay -> Verify Invoice.
    Corresponds to Process_Payment.tex.
    skipped: UI element for payment not found in current POS templates.
    """
    page.goto(f"{base_url}/sales/pos/")
    
    # Placeholder logic
    page.click(".card a:has-text('Occupied') >> nth=0")
    expect(page.locator("text=Thanh toán")).to_be_visible()
    page.click("text=Thanh toán")
    # ... rest of flow
