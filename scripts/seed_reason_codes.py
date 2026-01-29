import os
import django
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fami_project.settings")
django.setup()

from kitchen.models import ReasonCode

reasons = [
    ("BURNED", "Food was burned during cooking"),
    ("DROPPED", "Item was dropped on the floor"),
    ("EXPIRED", "Ingredient passed expiration date"),
    ("WRONG_ORDER", "Prepared incorrectly / wrong order"),
    ("SPOILED", "Spoiled / Quality check failed"),
    ("TESTING", "Used for recipe testing / QA"),
]

created_count = 0
for code, desc in reasons:
    obj, created = ReasonCode.objects.get_or_create(code=code, defaults={'description': desc})
    if created:
        print(f"Created ReasonCode: {code}")
        created_count += 1
    else:
        pass # print(f"ReasonCode already exists: {code}")

print(f"Finished. Created {created_count} new reason codes.")
if created_count == 0:
    print(f"Existing codes: {[r.code for r in ReasonCode.objects.all()]}")
