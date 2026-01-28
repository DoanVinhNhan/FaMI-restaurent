# Plan: Cải thiện Phân hệ Báo cáo & Thống kê (Drill-down, Spinner, Export, Chart handlers, Formatting)

Ngày: 2026-01-28
Tác giả: GitHub Copilot

---

Mục tiêu: Thêm và cải thiện các tính năng sau trong phân hệ `reporting`:
- Drill-down từ charts / top-items → danh sách orders (HTMX GET to new endpoint) ✅
- Loading states & empty-state CTAs (spinner / feedback) ✅
- Export CSV cho `inventory` và `waste` ✅
- Chart click handlers (client-side) — show modal hoặc replace `#reportResults` with drilldown table ✅
- Number/currency formatting trên frontend (Intl.NumberFormat) ✅

---

## 1) Tóm tắt hiện trạng (đã đọc mã)
- Business logic: `reporting/services.py` (class `ReportController`) chứa các hàm tổng hợp dữ liệu: `generate_sales_report`, `generate_inventory_variance_report`, `generate_waste_report`, `export_sales_to_csv`.
- Views: `reporting/views.py` có `report_dashboard`, `sales_report_view`, `inventory_report_view`, `waste_report_view`, `ChartDataAPIView`.
- Templates: `reporting/templates/reporting/dashboard.html`, partials: `reporting/partials/sales_results.html`, `inventory_results.html`, `waste_results.html`.
- Frontend: Dashboard sử dụng **HTMX** để load partials và **Chart.js** cho charts. Hiện chưa có drilldown, spinner hay chart click handler, và chỉ có CSV export cho sales.

---

## 2) Chi tiết thay đổi & bước triển khai
Mỗi mục bao gồm: files cần chỉnh, behavior, code-snippets mẫu, tests, acceptance criteria.

### A. Drill-down từ Chart / Top Items → Danh sách Orders (HTMX)
- Tập trung: khi user click vào một bar/point trên chart hoặc một row `Top Selling Items`, hiển thị danh sách các `Order` liên quan (date range, item filter).

Files thay đổi:
- Backend:
  - `reporting/views.py` -> Thêm view `sales_drilldown_view(request: HttpRequest)` (HTMX friendly) trả partial template `reporting/partials/sales_drilldown.html`.
  - `reporting/urls.py` -> Thêm route: `path('sales/drilldown/', views.sales_drilldown_view, name='sales_drilldown')`.
  - `reporting/services.py` -> Thêm method `get_orders_for_item(start_date, end_date, menu_item_name, limit, page)` (supports pagination).

- Frontend:
  - `reporting/templates/reporting/partials/sales_results.html` -> thêm link/button "View Orders" cho từng item (htmx GET to `reporting:sales_drilldown` with params).
  - `reporting/templates/reporting/partials/sales_drilldown.html` (new) -> table of orders for that item (order id, date, total, payment method, invoice/promotion snapshot) and pagination controls.
  - `static/reporting/reporting.js` -> add function to handle chart clicks: perform fetch to `reporting:sales_drilldown` using `htmx` or `fetch` and inject into `#reportResults` or modal.

Code snippet (view skeleton):
```py
@login_required
@user_passes_test(is_reporting_viewer)
def sales_drilldown_view(request):
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')
    item = request.GET.get('item')
    page = int(request.GET.get('page', 1))

    orders_page = ReportController.get_orders_for_item(start, end, item, page=page)
    return render(request, 'reporting/partials/sales_drilldown.html', {'orders': orders_page, 'item': item})
```

Tests:
- Unit: test `get_orders_for_item` with and without item filter.
- View: test `sales_drilldown_view` returns 200 and contains expected order ids.
- Integration: simulate HTMX GET and assert it updates `#reportResults` (could be in E2E).

Acceptance criteria:
- Clicking on chart top-item loads drilldown partial into `#reportResults` without full page reload.
- Drilldown supports pagination and date filters.

---

### B. Loading states & empty-state CTAs
- UX: show spinner on HTMX partial loads and while Chart API is fetching; show helpful message and CTA when result empty.

Files change:
- `reporting/templates/reporting/dashboard.html`:
  - Add spinner markup e.g. `<div id="reportSpinner" class="d-none spinner-overlay" role="status">...</div>` and include `static/reporting/reporting.js`.
- `static/reporting/reporting.js` (new): functions `showSpinner()` / `hideSpinner()` and attach to HTMX events (`htmx:beforeRequest`, `htmx:afterSwap`) and to Chart fetch start/finish.
- CSS: create `static/reporting/reporting.css` for `.spinner-overlay` and optionally add to base static includes.

Implementation notes:
- HTMX fires `htmx:beforeRequest` / `htmx:afterRequest` events — attach spinner toggles.
- Chart fetch wrapper should toggle spinner as well.

Tests:
- Unit JS test (optional): verify spinner toggles on events (use Jest/Playwright).
- E2E: test that spinner is visible when clicking report button and disappears after results shown.

Acceptance criteria:
- Spinner appears on report load and chart fetch; disappears when results are loaded.
- Empty result shows message + CTA to broaden date range or export (if possible).

---

### C. Export CSV cho inventory & waste
- Implement CSV export endpoints similar to sales export.

Files change:
- Backend: `reporting/services.py` -> add `export_inventory_to_csv(tickets)` and `export_waste_to_csv(waste_data)`.
- Views: `reporting/views.py` -> in `inventory_report_view` and `waste_report_view`, check `export=csv` param and return CSV response.
- Templates: add Export CSV button to partial headers `inventory_results.html` and `waste_results.html`.

Code snippet (view sample):
```py
if export == 'csv' and tickets:
    csv_content = ReportController.export_inventory_to_csv(tickets)
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_report_{start}_{end}.csv"'
    return response
```

Tests:
- Unit: test export functions produce CSV with expected headers and lines.
- View: test GET with `export=csv` returns `Content-Disposition` and CSV content.

Acceptance criteria:
- User can export inventory and waste reports to CSV from dashboard.

---

### D. Chart click handlers (client-side)
- Implement robust client JS that binds to Chart.js events and uses HTMX or fetch to get drilldown.

Files change:
- `static/reporting/reporting.js` (new) — functions:
  - `bindChartClickHandlers(chartInstance, options)`
  - `onChartClickHandler(evt, activeElements)` → map clicked label to item name / date and call HTMX GET or fetch.
  - Spinner integration and error handling.
- `reporting/templates/reporting/dashboard.html` include script near bottom:
```html
<script src="{% static 'reporting/reporting.js' %}"></script>
<script>bindChartClickHandlers(revenueChartInstance, {endpoint: '{% url 'reporting:sales_drilldown' %}'});</script>
```

Tests:
- E2E: click a chart bar and assert drilldown table appears.

Acceptance criteria:
- Chart click opens drilldown for that label (date/item), correct params sent.

---

### E. Number / Currency formatting (Intl.NumberFormat)
- Format numbers on client-side in charts and summary cards for better UX (vi-VN currency style used in dashboard).

Files change:
- `reporting/templates/reporting/dashboard.html` — in JS chart rendering use `new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value)` for ticks & tooltips.
- In `partials/*.html` for table cells use `|floatformat:2` or custom template filter `currency` for server-side fallback.

Tests:
- Snapshot tests on rendered partials (assert currency formatted strings present).

Acceptance criteria:
- Chart axes labels, tooltips and table currency fields display localized formatting.

---

## 3) Testing strategy
- Unit tests (python): `reporting/tests/` add tests for `ReportController.get_orders_for_item`, `export_inventory_to_csv`, `export_waste_to_csv`, `sales_drilldown_view`, `ChartDataAPIView`.
- Integration/E2E: Playwright or Selenium tests for flows:
  - Open dashboard → click Sales → click a Top Item chart → check drilldown content.
  - Change date range → verify content updates and spinner shows.
  - Export inventory/waste CSV → assert headers & content.

## 4) Backwards compatibility & edge cases
- Keep existing sales export behavior compatible.
- If data volume high, return paginated results for drilldown; consider server-side limit (e.g., 50 rows/page).
- Timezone considerations for date filters (use `timezone` aware datetimes consistently).
- Permissions: only `is_reporting_viewer` roles can hit drilldown/export endpoints.

## 5) Work breakdown & estimates
1. Add backend drilldown API & service method (0.5 day)
2. Create `sales_drilldown.html` partial and wire into `sales_results.html` (0.25 day)
3. Implement export CSV for inventory & waste (0.25 day)
4. Create `static/reporting/reporting.js` with chart click + spinner handlers (0.5 day)
5. Add spinner CSS & integrate HTMX spinner hooks (0.25 day)
6. Add tests (unit + integration) and run suite (0.5 day)
7. Add E2E Playwright tests (0.75 day)

Tổng: ~3 days (can be split into multiple PRs: backend, template/partial, JS/spinner, tests)

## 6) PR checklist
- [ ] Backend: new views + services + unit tests
- [ ] Templates: updated partials + drilldown partial
- [ ] Static: `reporting.js` + CSS spinner added and included
- [ ] Export: inventory/waste CSV and tests
- [ ] E2E tests for drilldown and spinner
- [ ] Docs/README update describing new endpoints and UI behavior

---

## 7) Implementation notes / snippets
- Use HTMX attributes for small integration: e.g. button `<button hx-get="{% url 'reporting:sales_drilldown' %}?item={{ item.menu_item__name }}&start_date={{ summary.start_date }}&end_date={{ summary.end_date }}" hx-target="#reportResults">View Orders</button>`
- Chart click handler skeleton (JS):
```js
function onChartClick(evt, elements) {
  if (!elements.length) return;
  const index = elements[0].index;
  const label = this.data.labels[index];
  // call HTMX
  htmx.ajax('GET', `/reporting/sales/drilldown/?item=${encodeURIComponent(label)}&start_date=${start}&end_date=${end}`, {target:'#reportResults'});
}
```

---

Nếu bạn đồng ý, tôi sẽ bắt đầu với PR đầu tiên: **(1) Drill-down backend + partial + simple HTMX button** (kèm unit tests). Chọn **Yes** để tôi tiếp tục và tôi sẽ thực hiện theo các bước trong Plan và cập nhật `Debug_Plan/reporting_plan.md` với trạng thái công việc từng bước khi hoàn thành.
