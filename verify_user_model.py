import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from core.models import User, UserRole

def verify_core_user() -> None:
    """
    Verifies the creation of a user with specific roles and fields.
    """
    print("--- STARTING VERIFICATION: CORE USER MODEL ---")

    # 1. Clean up previous test run
    username = "test_manager"
    if User.objects.filter(username=username).exists():
        User.objects.get(username=username).delete()
        print(f"Cleaned up existing user: {username}")

    # 2. Create a new Manager user
    try:
        manager = User.objects.create_user(
            username=username,
            email="manager@fami.com",
            password="SecurePassword123!",
            role=UserRole.MANAGER,
            employee_code="MGR-001"
        )
        print(f"Successfully created user: {manager}")
    except Exception as e:
        print(f"FAILED to create user: {e}")
        return

    # 3. Verify Fields
    retrieved_user = User.objects.get(username=username)
    
    # Check Role
    if retrieved_user.role == "MANAGER":
        print("PASS: Role is correctly saved as MANAGER.")
    else:
        print(f"FAIL: Role mismatch. Expected MANAGER, got {retrieved_user.role}")

    # Check Employee Code
    if retrieved_user.employee_code == "MGR-001":
        print("PASS: Employee Code is correctly saved as MGR-001.")
    else:
        print(f"FAIL: Employee Code mismatch. Expected MGR-001, got {retrieved_user.employee_code}")

    # Check Helper Method
    if retrieved_user.is_manager():
        print("PASS: is_manager() method returned True.")
    else:
        print("FAIL: is_manager() method returned False.")

    print("--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    verify_core_user()
