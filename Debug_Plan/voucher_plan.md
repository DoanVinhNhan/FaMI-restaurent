# Kế hoạch bổ sung tính năng Voucher (Promotion) — Thanh toán

## Tóm tắt (mục tiêu) ✅
- Ghi nhận chi tiết khuyến mãi trên hóa đơn và giao dịch: lưu `promotion`, `discount_amount`, `original_total`.
- Cho phép preview / apply mã khuyến mãi trước khi commit (dry-run) từ giao diện `payment_form.html` (hỗ trợ POST `apply_promo` hoặc HTMX/AJAX).

---

## Hiện trạng (tóm tắt kết quả đọc mã)
- Logic tính khuyến mãi hiện nằm ở `PromotionEngine.apply_promotion` (trả về số tiền giảm, áp dụng cho toàn bộ `order.total_amount`).
- `PaymentController.process_payment` khi có `promo_code` sẽ gọi `apply_promotion` rồi trực tiếp trừ `order.total_amount` và lưu order (commit) trước khi tạo `Invoice` và `Transaction`.
- `views.process_payment` có trường hợp `if 'apply_promo' in request.POST: pass` — chưa implement.
- Giao diện `payment_form.html` có input `promo_code` nhưng không có nút áp dụng rõ ràng (hoặc chức năng AJAX/HTMX để preview).
- Thiếu lưu trữ thông tin `promotion` / `discount` trên `Invoice` (và Transaction) — hiện chỉ có `Invoice.final_total`.

---

## Thiết kế chi tiết các thay đổi

### 1) Model changes (DB)
- File: `sales/models.py`
- Thêm fields vào `Invoice` (Ưu tiên lưu ở `Invoice` để giữ snapshot hoá đơn lúc thanh toán):

```py
# imports: Decimal
from decimal import Decimal

class Invoice(models.Model):
    # existing fields ...
    promotion = models.ForeignKey(
        'sales.Promotion', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    original_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
```

- Optionally, thêm trường ngắn gọn trên `Transaction` để trace:

```py
class Transaction(models.Model):
    promotion = models.ForeignKey('sales.Promotion', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
```

**Migrations:** tạo migration cho các field mới. Không cần data migration ngoại trừ set giá trị mặc định `0.00`.


### 2) Service changes (Business logic)
- File: `sales/services.py` (PaymentController and PromotionEngine)

A. PromotionEngine
- Mở rộng `apply_promotion(code, order)` để:
  - Hỗ trợ promo theo item: nếu `Promotion.eligible_items` không rỗng, chỉ tính discount trên các `OrderDetail` tương ứng.
  - Trả về tuple/structure (discount_amount, promotion_instance) — hoặc vẫn trả số tiền và cho caller lấy object nếu cần.

B. PaymentController.process_payment
- Thực hiện thay đổi để:
  - Trước khi sửa `order.total_amount`, lưu `original_total = order.total_amount`.
  - Tính `discount = PromotionEngine.apply_promotion(...)`.
  - Tính `final_required = max(Decimal('0.00'), original_total - discount)`.
  - Với `amount < final_required`: tạo Transaction FAILED (kèm `promotion` và `discount_amount` nếu có) và trả về lỗi.
  - Khi thanh toán thành công: 
    - Tạo Transaction (thêm `promotion` và `discount_amount` vào Transaction nếu bạn chọn lưu) — cần lưu `reference_code` như hiện tại.
    - Tạo Invoice với fields: order, final_total=final_required, payment_method, promotion, discount_amount, original_total.
    - **Compatibility:** Có 2 lựa chọn: (a) giữ hiện trạng cập nhật `order.total_amount -= discount` để tương thích với test hiện có, hoặc (b) không thay đổi `order.total_amount` mà chỉ lưu snapshot vào `Invoice`. Đề xuất: **LƯU original_total vào Invoice và vẫn cập nhật `order.total_amount` (để không phá test / workflows hiện tại)**.
  - Gọi `print_receipt(order, tx.pk)` vẫn như cũ.


### 3) Views / UX (Preview apply_promo)
- File: `sales/views.py` — `process_payment`

A. Implement `apply_promo` branch
- Nếu `request.method == 'POST'` và `'apply_promo' in request.POST`:
  - Lấy `promo_code`, gọi `PromotionEngine.apply_promotion(promo_code, order)` để tính `discount` (dry-run, không save order).
  - Chuẩn bị context: `promo_code`, `discount`, `new_total = order.total_amount - discount`.
  - Show flash message nếu code không hợp lệ.
  - Render lại `payment_form.html` với các giá trị này (status 200) để cashier xem tổng sau khi áp dụng.
  - (Tùy chọn HTMX) Nếu request là HTMX, trả partial HTML (thẻ summary) để cập nhật phần hiển thị giá tiền.

B. Main submit behavior
- Khi xử lý thanh toán thực sự (không phải `apply_promo`), dùng code trong PaymentController để finalize, lưu thông tin promotion vào Invoice/Transaction.


### 4) Template changes (Frontend)
- File: `sales/templates/sales/payment_form.html`

A. Thêm nút "Áp dụng mã" bên cạnh input `promo_code`:
```html
<div class="input-group">
  <input type="text" name="promo_code" class="form-control" ...>
  <button type="submit" name="apply_promo" class="btn btn-outline-secondary">Áp dụng</button>
</div>
```
- Hiển thị khu vực summary khi có `discount` trong context:
```html
{% if discount %}
  <div class="alert alert-info">
    Discount: ${{ discount }} — New Total: ${{ new_total }}
  </div>
{% endif %}
```
- JS / UX: khi dùng 'apply_promo' bằng HTMX/AJAX, cập nhật phần summary và `received_amount.min` nếu payment method = CASH.


### 5) Tests (Unit + Integration)
- File: `sales/tests/test_payment_process.py`

Thêm/Chỉnh các test sau:
1. test_apply_promo_preview (POST với `apply_promo`) — assert response chứa `discount` và `new_total` tương ứng, order không bị thay đổi.
2. test_promotion_application_updated (process_payment with promo) — assert: result.success, `Invoice` được tạo với `promotion`, `discount_amount`, `original_total`, `final_total` đúng; `Transaction` có `status=SUCCESS` và (tùy) có `discount_amount`.
3. test_transaction_failed_with_promo_insufficient_payment — test khi áp promo mà khách đưa thiếu tiền, Transaction FAILED được tạo với thông tin promotion.
4. test_promotion_only_affects_eligible_items — tạo promotion chỉ cho một item and assert discount tính đúng.

Chỉnh test hiện tại `test_promotion_application` để kiểm tra thêm các trường invoice/trx.


### 6) Migration & Backwards compatibility
- Tạo migration file cho các fields mới.
- Không cần data migration; default `0.00` cho numeric fields.
- Document breaking changes: nếu downstream code phụ thuộc `order.total_amount` thay đổi behavior, cần kiểm tra. Vì đề xuất vẫn cập nhật `order.total_amount` để giữ tương thích.


### 7) Tasks & Work breakdown (ước lượng)
1. Add model fields + migrations (0.5d)
2. Update `PromotionEngine` to support eligible_items (0.25d)
3. Update `PaymentController.process_payment` to store original_total/discount and pass promotion to Invoice/Transaction (0.5d)
4. Implement `apply_promo` behavior in `views.process_payment` and add server-side rendering and HTMX-friendly partial (0.5d)
5. Template changes + JS for UX (0.5d)
6. Add/modify unit tests and run test suite (0.5d)
7. Manual QA: run through POS flows, edge cases, DB migration checks (0.5d)

Tổng: ~3.25 ngày (có thể chia nhỏ thành 3-4 PR nhỏ để review dễ hơn).


### 8) Edge cases & Security
- Ensure `Promotion.is_valid()` still checked (date range, active flag).
- Prevent double-apply: If order already has a `promotion`/`discount` stored (or order.status != Pending/Cooking), do not allow reapplying. Provide a clear message.
- Race conditions: `process_payment` already uses `select_for_update()`; ensure `apply_promo` dry-run doesn't create inconsistent state (dry-run must not lock the row indefinitely).


### 9) PR checklist
- [ ] Model changes + migrations created
- [ ] Services updated and covered by unit tests (edge cases)
- [ ] `apply_promo` implemented and template updated
- [ ] Tests added/updated and passing
- [ ] Manual QA (POS flows, multiple promos, invalid codes)
- [ ] Changelog entry


---

## Ví dụ snippets (ghi nhớ kiểm tra coding style):
- `PaymentController.process_payment` (pseudocode):
```py
original = order.total_amount
discount = Decimal('0.00')
promo_obj = None
if promo_code:
    discount = PromotionEngine.apply_promotion(promo_code, order)
    try:
        promo_obj = Promotion.objects.get(promo_code=promo_code)
    except Promotion.DoesNotExist:
        promo_obj = None
final_required = max(Decimal('0.00'), original - discount)
# check amount, create tx, invoice with promotion=promo_obj, discount_amount=discount, original_total=original
# optionally update order.total_amount = final_required; order.save()
```

---

## Ghi chú cuối
- Nếu bạn muốn, tôi có thể bắt đầu bằng PR nhỏ: (A) thêm các field model + migration + test; hoặc (B) implement `apply_promo` UX (view+template) trước. Chọn 1 trong 2 để tôi triển khai.

---

File tạo: `Debug_Plan/voucher_plan.md`

---

### Implementation status (quick log)
- [x] Add model fields to `Invoice` and `Transaction` (migration created: `0009_invoice_promotion.py`).
- [x] Update `PaymentController.process_payment` to record `promotion`, `discount_amount`, `original_total` on `Invoice` and `promotion`, `discount_amount` on `Transaction`.
- [x] Update unit tests in `sales/tests/test_payment_process.py` to verify snapshot behavior and failed transaction logging.

Next: Implement (B) `apply_promo` dry-run UX and related tests.


