import pytest
from playwright.sync_api import Page, expect
import time

def test_pos_order_flow(auth, page: Page, base_url):
    """
    Test the POS Order flow: Select Table -> Add Items -> Submit -> Verify Kitchen Status.
    Corresponds to Manage_Order.tex scenarios.
    """
    
    # 1. Navigate to POS Dashboard
    page.goto(f"{base_url}/sales/pos/")
    import re
    expect(page).to_have_title(re.compile(r"FaM.*POS"))
    
    # 2. Select a Table (Assume Table 1 exists and is Available)
    # We look for a table card. 
    # Adjust selector based on pos_index.html, assuming simple links or cards
    # Let's pick the first available table
    page.click(".card a:has-text('Available') >> nth=0")
    
    # 3. Add Item to Cart
    # Wait for menu to load
    expect(page.locator("text=Đơn hàng")).to_be_visible()
    
    # Click on the first menu item card to add it
    # The card has hx-post, but clicking it should trigger the request
    # Playwright click triggers the event.
    page.click(".menu-item-card >> nth=0")
    
    # 4. Verify Item in Cart
    # Wait for htmx swap
    expect(page.locator("#cart-container .list-group-item")).to_have_count(1)
    
    # Get item name to confirm
    item_name = page.inner_text(".menu-item-card h6 >> nth=0")
    expect(page.locator("#cart-container")).to_contain_text(item_name)
    
    # 5. Submit Order
    page.click("button:has-text('Gửi xuống Bếp')")
    
    # 6. Verify Redirect and Status
    # Should redirect back to POS Index
    expect(page).to_have_url(f"{base_url}/sales/pos/")
    
    # Verify Table Status changed to Occupied
    # We need to find the same table again. 
    # Assuming we clicked the first one, now it should be Occupied.
    # We might need a more robust way to identify the table, e.g. T-01
    # For now, check if ANY table is Occupied (assuming clean state or we just made one)
    expect(page.locator("text=Occupied")).to_be_visible()

def test_pos_remove_item(auth, page: Page, base_url):
    """
    Test adding and removing an item from the cart.
    """
    page.goto(f"{base_url}/sales/pos/")
    page.click(".card a:has-text('Available') >> nth=0")
    
    # Add Item
    page.click(".menu-item-card >> nth=0")
    expect(page.locator("#cart-container .list-group-item")).to_have_count(1)
    
    # Remove Item
    # Finds the trash button in the cart
    page.click("#cart-container button .bi-trash")
    
    # Verify Cart Empty
    expect(page.locator("#cart-container")).to_contain_text("Giỏ hàng trống")
