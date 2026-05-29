document.addEventListener('DOMContentLoaded', () => {

    const chartCanvas = document.getElementById('sentimentChart');

    if (!chartCanvas) return;

    const positif =
        parseInt(chartCanvas.dataset.positif) || 0;

    const negatif =
        parseInt(chartCanvas.dataset.negatif) || 0;

    new Chart(chartCanvas, {

        type: 'doughnut',

        data: {

            labels: [
                'Positif',
                'Negatif'
            ],

            datasets: [{

                data: [
                    positif,
                    negatif
                ],

                backgroundColor: [
                    '#10b981',
                    '#ef4444'
                ],

                borderWidth: 0

            }]
        },

        options: {

            responsive: true,

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

                }

            }

        }

    });

});