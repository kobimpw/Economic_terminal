
// Render diff chart inside tile
function renderTileDiffChart(content, data) {
    const canvas = content.querySelector('.diff-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const comparison = data.comparison;

    // Destroy existing chart if any
    if (canvas._chart) {
        canvas._chart.destroy();
    }

    canvas._chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: comparison.dates,
            datasets: [
                {
                    label: 'Actual Diff',
                    data: comparison.actual_diff,
                    backgroundColor: 'rgba(5, 150, 105, 0.7)',
                    borderColor: '#059669',
                    borderWidth: 1
                },
                {
                    label: 'Predicted Diff',
                    data: comparison.predict_diff,
                    backgroundColor: 'rgba(26, 86, 219, 0.7)',
                    borderColor: '#1a56db',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { display: true, grid: { display: false }, ticks: { font: { size: 9 } } },
                y: { display: true, grid: { color: '#f3f4f6' }, ticks: { font: { size: 9 } } }
            }
        }
    });
}
