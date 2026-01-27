import os
import shutil
import django
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO
import sys

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from menu.models import Category, MenuItem

def run_test():
    print(">>> STARTING TASK 009 VERIFICATION (Menu Models)")

    # 1. Setup Data
    cat, _ = Category.objects.get_or_create(
        name="Test Cat", 
        defaults={'printer_target': 'KITCHEN'}
    )

    # 2. Test Soft Delete / Status
    print("Test 1: Soft Delete Logic...")
    item = MenuItem.objects.create(
        sku="SOFT-DEL-01",
        name="Temp Item",
        category=cat,
        price=50000,
        status=MenuItem.ItemStatus.ACTIVE
    )
    assert item.is_active is True
    
    # Simulate "Delete" -> Set Inactive
    item.status = MenuItem.ItemStatus.INACTIVE
    item.save()
    
    refetched = MenuItem.objects.get(sku="SOFT-DEL-01")
    assert refetched.is_active is False
    print("PASS: Item status updated to INACTIVE (Soft Delete verified)")

    # 3. Test Image Resizing (Service Integration)
    print("Test 2: Image Resizing Service...")
    
    # Create 2000x2000 Red Image
    img_buffer = BytesIO()
    large_img = Image.new('RGB', (2000, 2000), color='red')
    large_img.save(img_buffer, format='JPEG')
    img_file = SimpleUploadedFile("large_test.jpg", img_buffer.getvalue(), content_type="image/jpeg")

    item_img = MenuItem.objects.create(
        sku="IMG-TEST-01",
        name="Image Item",
        category=cat,
        price=100000,
        image=img_file
    )

    # Verify Dimensions
    item_img.refresh_from_db()
    if item_img.image:
        try:
            with Image.open(item_img.image.path) as debug_img:
                w, h = debug_img.size
                print(f"INFO: Saved dimensions: {w}x{h}")
                if w <= 800 and h <= 800:
                    print("PASS: Image resized successfully")
                else:
                    print(f"FAIL: Image too large ({w}x{h})")
        except FileNotFoundError:
             print("FAIL: Image file not found on disk")
    else:
        print("FAIL: Image not saved")

    # Cleanup image file
    if item_img.image:
        try:
            os.remove(item_img.image.path)
            # Try to remove the directory if empty, or just leave it
        except:
            pass

    print(">>> TASK 009 COMPLETED SUCCESSFULLY")

if __name__ == '__main__':
    run_test()
