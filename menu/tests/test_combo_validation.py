from django.test import TestCase
from django.core.exceptions import ValidationError
from menu.models import MenuItem, ComboComponent, Category
from menu.forms import ComboComponentFormSet

class ComboValidationTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Test', printer_target='KITCHEN')
        # create a combo item
        self.combo = MenuItem.objects.create(sku='C001', name='Combo 1', category=self.cat, price=100.0, is_combo=True, status='ACTIVE')

    def test_model_prevents_self_reference(self):
        cc = ComboComponent(combo=self.combo, item=self.combo, quantity=1)
        with self.assertRaises(ValidationError):
            cc.full_clean()

    def test_formset_rejects_self_reference(self):
        # Simulate POST data for inline formset trying to add the combo as its own component
        data = {
            'combocomponent_set-TOTAL_FORMS': '1',
            'combocomponent_set-INITIAL_FORMS': '0',
            'combocomponent_set-MIN_NUM_FORMS': '0',
            'combocomponent_set-MAX_NUM_FORMS': '1000',
            'combocomponent_set-0-item': str(self.combo.pk),
            'combocomponent_set-0-quantity': '1',
        }
        formset = ComboComponentFormSet(data, instance=self.combo)
        self.assertFalse(formset.is_valid())
        # Check that the non form error contains our validation message
        errors = str(formset.non_form_errors()) + ' ' + ' '.join(str(f.errors) for f in formset.forms)
        self.assertIn('A combo cannot include itself', errors)

    def test_deleting_empty_extra_forms_allowed(self):
        # Create an item to actually add as a single component
        item = MenuItem.objects.create(sku='I001', name='Item 1', category=self.cat, price=10.0, status='ACTIVE')
        # Simulate a formset with 5 total forms where we fill only the first, and mark others as deleted
        data = {
            'combocomponent_set-TOTAL_FORMS': '5',
            'combocomponent_set-INITIAL_FORMS': '0',
            'combocomponent_set-MIN_NUM_FORMS': '0',
            'combocomponent_set-MAX_NUM_FORMS': '1000',
            # Form 0 -> valid component
            'combocomponent_set-0-item': str(item.pk),
            'combocomponent_set-0-quantity': '1',
            # Form 1-4 -> empty extras, user clicks delete on them (simulate marking them for deletion)
            'combocomponent_set-1-DELETE': 'on',
            'combocomponent_set-2-DELETE': 'on',
            'combocomponent_set-3-DELETE': 'on',
            'combocomponent_set-4-DELETE': 'on',
        }
        formset = ComboComponentFormSet(data, instance=self.combo)
        self.assertTrue(formset.is_valid())
        # After saving, only one ComboComponent should be created
        formset.save()
        self.assertEqual(self.combo.combo_components.count(), 1)