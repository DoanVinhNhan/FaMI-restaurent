import pytest
from playwright.sync_api import Page, expect
import time

def test_menu_create_edit_delete(auth, page: Page, base_url):
    """
    Test the full lifecycle of a menu item: Create -> Edit -> Delete (Soft).
    Corresponds to Manage_Menu_Pricing.tex scenarios.
    """
    
    # 1. Navigate to Menu List
    page.goto(f"{base_url}/menu/")
    expect(page).to_have_title("Quản lý Thực đơn - FaMÌ")
    
    # 2. Add New Item
    page.click("text=Thêm Món mới")
    expect(page).to_have_url(f"{base_url}/menu/create/")
    
    # Fill Form
    sku = f"TEST-{int(time.time())}"
    page.fill("input[name='sku']", sku)
    page.fill("input[name='name']", f"Test Dish {sku}")
    page.fill("textarea[name='description']", "Delicious test dish description.")
    
    # Select Category (Assuming at least one exists, index 1)
    # If select has no options, this might fail, but let's assume seed data
    page.select_option("select[name='category']", index=1) 
    
    page.select_option("select[name='status']", "ACTIVE")
    
    # Price
    page.fill("input[name='selling_price']", "50000")
    
    # Save
    page.click("button[type='submit']")
    
    # Verify Redirect and Success
    # Debug: Print URL if not expected
    try:
        expect(page).to_have_url(f"{base_url}/menu/")
    except AssertionError:
        print(f"DEBUG: Redirected to {page.url}")
        print(f"DEBUG: Cookies: {page.context.cookies()}")
        # print(f"DEBUG: Page Content: {page.content()}")
        raise
    
    expect(page.locator(f"text={sku}")).to_be_visible()
    expect(page.locator(f"text=Test Dish {sku}")).to_be_visible()
    
    # 3. Edit Item
    # Click Edit button for this specific item row
    # Use reliable locator: Row containing SKU -> Edit button
    row = page.locator(f"tr:has-text('{sku}')")
    row.locator("a[title='Chỉnh sửa']").click()
    
    # Modify Name and Price
    page.fill("input[name='name']", f"Updated Dish {sku}")
    
    # Note: Price might be readonly or in a separate form depending on implementation
    # Based on form template, price is shown if price_form is present. 
    # Usually Edit view might not show price form if using Price History logic, 
    # but let's assume simple edit or we just edit name.
    
    page.click("button[type='submit']")
    
    # Verify Update
    expect(page).to_have_url(f"{base_url}/menu/")
    expect(page.locator(f"text=Updated Dish {sku}")).to_be_visible()
    
    # 4. Delete Item (Soft Delete / Deactivate)
    row = page.locator(f"tr:has-text('{sku}')")
    row.locator("a[title='Ngừng bán']").click()
    
    # Verify Confirm Page
    expect(page.locator("text=Bạn có chắc chắn muốn xóa/ngừng bán món ăn này?")).to_be_visible()
    page.click("button[type='submit']")
    
    # Verify Item Status Changed or Removed from Active List
    # If view=active (default), it should disappear
    expect(page).to_have_url(f"{base_url}/menu/")
    expect(page.locator(f"text={sku}")).not_to_be_visible()
    
    # Check 'All' view to see if it is there but Inactive
    page.click("text=Tất cả")
    expect(page.locator(f"tr:has-text('{sku}')")).to_contain_text("Ngừng bán")
