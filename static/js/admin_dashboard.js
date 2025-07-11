document.addEventListener('DOMContentLoaded', function() {
    // Only initialize the chart if the element exists
    const userGrowthCanvas = document.getElementById('userGrowthChart');
    if (!userGrowthCanvas) return;

    const userGrowthCtx = userGrowthCanvas.getContext('2d');
    
    // Default data in case chartData is not defined
    const defaultLabels = Array.from({length: 30}, (_, i) => {
        const date = new Date();
        date.setDate(date.getDate() - (29 - i));
        return date.toLocaleDateString('en-US', {month: 'short', day: 'numeric'});
    });
    
    // Use the chartData from the template or fall back to defaults
    const chartLabels = window.chartData?.labels || defaultLabels;
    const chartDataPoints = window.chartData?.data || Array(30).fill(0).map(() => Math.floor(Math.random() * 100));
    const chartMax = window.chartData?.max || 100;
    
    new Chart(userGrowthCtx, {
        type: 'line',
        data: {
            labels: chartLabels,
            datasets: [{
                label: 'Total Users',
                data: chartDataPoints,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointBackgroundColor: '#4f46e5',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1f2937',
                    titleFont: { weight: '600', size: 13 },
                    bodyFont: { size: 13 },
                    padding: 12,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return ' ' + context.parsed.y + ' users';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false, drawBorder: false },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 12 }
                    }
                },
                y: {
                    grid: {
                        color: '#f3f4f6',
                        drawBorder: false,
                        borderDash: [5, 5]
                    },
                    ticks: {
                        color: '#6b7280',
                        font: { size: 12 },
                        padding: 10,
                        callback: function(value) {
                            return value % 10 === 0 ? value : '';
                        }
                    },
                    min: 0,
                    max: chartMax
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
});
