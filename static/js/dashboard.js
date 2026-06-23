document.addEventListener('DOMContentLoaded', () => {

    const chartCanvas = document.getElementById('sentimentChart');

    if (!chartCanvas) return;

    const positif =
        parseInt(chartCanvas.dataset.positif) || 0;

    const netral =
        parseInt(chartCanvas.dataset.netral) || 0;

    const negatif =
        parseInt(chartCanvas.dataset.negatif) || 0;

    new Chart(chartCanvas, {

        type: 'doughnut',

        data: {

            labels: [
                'Positif',
                'Netral',
                'Negatif'
            ],

            datasets: [{

                data: [
                    positif,
                    netral,
                    negatif
                ],

                backgroundColor: [
                    '#10b981', // Hijau
                    '#f59e0b', // Kuning
                    '#ef4444'  // Merah
                ],

                borderWidth: 0

            }]
        },

        options: {

            responsive: true,

            maintainAspectRatio: true,

            cutout: '70%',

            plugins: {

                legend: {

                    position: 'bottom',

                    labels: {

                        padding: 20,

                        font: {
                            size: 14
                        }

                    }

                },

                tooltip: {

                    callbacks: {

                        label: function(context) {

                            const total =
                                context.dataset.data.reduce(
                                    (a, b) => a + b,
                                    0
                                );

                            const value =
                                context.raw;

                            const percentage =
                                total > 0
                                    ? ((value / total) * 100).toFixed(2)
                                    : 0;

                            return `${context.label}: ${value} (${percentage}%)`;
                        }

                    }

                }

            }

        }

    });

});