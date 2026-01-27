import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django.setup()

from core.models import SettingGroup, SystemSetting
from core.utils import ConfigurationManager

def run_verification():
    print("--- Starting Verification for Task 004 ---")

    # 1. Clean up previous test data
    SystemSetting.objects.all().delete()
    SettingGroup.objects.all().delete()
    ConfigurationManager.reload_config()

    # 2. Create a Setting Group
    group = SettingGroup.objects.create(
        group_name="Financials",
        description="Tax and Currency settings"
    )
    print(f"PASS: Created Group '{group.group_name}'")

    # 3. Create Settings with different types
    # Float Setting (Tax)
    SystemSetting.objects.create(
        setting_key="TAX_RATE",
        setting_value="0.10",
        data_type=SystemSetting.DataType.FLOAT,
        group=group
    )
    
    # Boolean Setting (Enable Tips)
    SystemSetting.objects.create(
        setting_key="ENABLE_TIPS",
        setting_value="True",
        data_type=SystemSetting.DataType.BOOLEAN,
        group=group
    )

    # JSON Setting (Currency Config)
    SystemSetting.objects.create(
        setting_key="CURRENCY_CONFIG",
        setting_value='{"symbol": "$", "code": "USD"}',
        data_type=SystemSetting.DataType.JSON,
        group=group
    )
    print("PASS: Created Settings (Float, Boolean, JSON)")

    # 4. Verify ConfigurationManager Retrieval & Type Casting
    tax = ConfigurationManager.get_setting("TAX_RATE")
    tips = ConfigurationManager.get_setting("ENABLE_TIPS")
    currency = ConfigurationManager.get_setting("CURRENCY_CONFIG")

    assert isinstance(tax, float), f"Tax should be float, got {type(tax)}"
    assert tax == 0.10, f"Tax should be 0.10, got {tax}"
    print("PASS: ConfigurationManager cast FLOAT correctly.")

    assert isinstance(tips, bool), f"Tips should be bool, got {type(tips)}"
    assert tips is True, "Tips should be True"
    print("PASS: ConfigurationManager cast BOOLEAN correctly.")

    assert isinstance(currency, dict), f"Currency should be dict, got {type(currency)}"
    assert currency['code'] == "USD", "Currency JSON parse failed"
    print("PASS: ConfigurationManager cast JSON correctly.")

    # 5. Verify Caching (Simulate by changing DB directly vs Manager)
    # The Manager should hit cache and return old value if we manipulate DB directly without using Manager.set_setting
    # However, for this test, let's verify set_setting updates correctly.
    
    success = ConfigurationManager.set_setting("TAX_RATE", 0.15)
    assert success is True, "set_setting failed"
    
    new_tax = ConfigurationManager.get_setting("TAX_RATE")
    assert new_tax == 0.15, f"Expected 0.15 after update, got {new_tax}"
    print("PASS: ConfigurationManager.set_setting updated value and cache.")

    # 6. Default value check
    missing = ConfigurationManager.get_setting("NON_EXISTENT", default="DEFAULT")
    assert missing == "DEFAULT", "Default value logic failed"
    print("PASS: Default value returned for missing key.")

    print("\n--- ALL VERIFICATIONS PASSED ---")

if __name__ == "__main__":
    run_verification()
