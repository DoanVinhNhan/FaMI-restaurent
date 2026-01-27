import os
import django

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from core.models import User, AuditLog
from core.services import AuditService

def run_verification():
    print("--- 1. Creating Test User ---")
    user, created = User.objects.get_or_create(username='test_manager', defaults={'role': 'MANAGER'})
    if created:
        print(f"Created user: {user.username}")
    else:
        print(f"Found user: {user.username}")

    print("\n--- 2. Executing AuditService.log_action ---")
    AuditService.log_action(
        action=AuditLog.ActionType.UPDATE,
        target_model="MenuItem",
        target_object_id="101",
        actor=user,
        changes={"price": {"old": 50000, "new": 55000}},
        ip_address="127.0.0.1"
    )

    print("\n--- 3. Verifying Database Record ---")
    log = AuditLog.objects.last()
    
    if log:
        print(f"SUCCESS: Log found!")
        print(f"ID: {log.id}")
        print(f"Actor: {log.actor.username}")
        print(f"Action: {log.action}")
        print(f"Changes: {log.changes}")
    else:
        print("FAILURE: No log found.")

if __name__ == '__main__':
    run_verification()
