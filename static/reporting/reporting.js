// reporting.js
// Utilities for reporting pages: chart click handlers, spinner

(function () {
    function formatCurrency(value) {
        try {
            return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
        } catch (e) {
            return value;
        }
    }

    function showSpinner() {
        const spinner = document.getElementById('reportSpinner');
        if (spinner) spinner.classList.remove('d-none');
    }

    function hideSpinner() {
        const spinner = document.getElementById('reportSpinner');
        if (spinner) spinner.classList.add('d-none');
    }

    function buildParamsFromSelectors(endpoint, opts, label) {
        const startEl = document.querySelector(opts.startSelector || '#startDate');
        const endEl = document.querySelector(opts.endSelector || '#endDate');
        const start = startEl ? startEl.value : '';
        const end = endEl ? endEl.value : '';
        const params = new URLSearchParams();
        if (start) params.append('start_date', start);
        if (end) params.append('end_date', end);
        if (label) params.append('item', label);
        return `${endpoint}?${params.toString()}`;
    }

    function bindChartClickHandlers(chartInstance, opts) {
        if (!chartInstance || !chartInstance.canvas) return;
        const canvas = chartInstance.canvas;
        canvas.style.cursor = 'pointer';

        canvas.addEventListener('click', function (evt) {
            const points = chartInstance.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);
            if (!points.length) return;
            const first = points[0];
            const idx = first.index;
            const label = chartInstance.data.labels[idx];

            const url = buildParamsFromSelectors(opts.endpoint, opts, label);
            // Use HTMX if available to load partial
            if (window.htmx) {
                showSpinner();
                htmx.ajax('GET', url, { target: '#reportResults', swap: 'innerHTML' });
                // hideSpinner handled by HTMX events (if wired) or after a timeout fallback
                setTimeout(hideSpinner, 2000);
            } else {
                // Fallback to fetch
                showSpinner();
                fetch(url)
                    .then(r => r.text())
                    .then(html => document.getElementById('reportResults').innerHTML = html)
                    .catch(err => console.error(err))
                    .finally(() => hideSpinner());
            }
        });
    }

    // Expose functions globally
    window.Reporting = {
        bindChartClickHandlers: bindChartClickHandlers,
        showSpinner: showSpinner,
        hideSpinner: hideSpinner,
        formatCurrency: formatCurrency
    };
})();