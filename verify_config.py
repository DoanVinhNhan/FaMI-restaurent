import os
import django
import logging
from django.conf import settings
from pathlib import Path

def verify_setup() -> None:
    """
    Verifies the Django configuration, environment loading, and logging setup.
    """
    print("[-] Initializing Django setup...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
    try:
        django.setup()
        print("[+] Django setup successful.")
    except Exception as e:
        print(f"[!] Django setup failed: {e}")
        return

    # 1. Verify Timezone
    print(f"[-] Checking Timezone... Expected: Asia/Ho_Chi_Minh, Actual: {settings.TIME_ZONE}")
    if settings.TIME_ZONE == 'Asia/Ho_Chi_Minh':
        print("[+] Timezone is correct.")
    else:
        print("[!] Timezone incorrect.")

    # 2. Verify Apps
    required_apps = ['core', 'inventory', 'menu', 'sales', 'kitchen', 'reports', 'rest_framework']
    print(f"[-] Checking Installed Apps...")
    missing_apps = [app for app in required_apps if app not in str(settings.INSTALLED_APPS)]
    if not missing_apps:
        print("[+] All modular apps are registered.")
    else:
        print(f"[!] Missing apps: {missing_apps}")

    # 3. Verify Logging
    print("[-] Testing Logging configuration...")
    logger = logging.getLogger('django')
    log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'fami.log')
    
    # Log a warning (should go to file)
    test_message = "FaMÌ Configuration Verification Test Warning"
    logger.warning(test_message)

    if os.path.exists(log_file_path):
        with open(log_file_path, 'r') as f:
            content = f.read()
            if test_message in content:
                print(f"[+] Log file created and writable at {log_file_path}")
            else:
                print("[!] Log file exists but message not found.")
    else:
        print(f"[!] Log file not found at {log_file_path}")

    # 4. Verify Custom User Model Config
    print(f"[-] Checking Auth User Model... Configured: {settings.AUTH_USER_MODEL}")
    if settings.AUTH_USER_MODEL == 'core.User':
        print("[+] AUTH_USER_MODEL configured correctly.")
    else:
        print("[!] AUTH_USER_MODEL is incorrect.")

if __name__ == "__main__":
    verify_setup()
