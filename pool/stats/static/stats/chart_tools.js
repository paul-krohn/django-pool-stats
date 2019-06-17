let chart_options = {
    maintainAspectRatio: false,
    legend: {
        display: false,
    },
    scales: {
        xAxes: [{
            display: true,
            type: 'time',
            scaleLabel: {
                display: false,
                labelString: 'Month',
            }
        }],
        yAxes:[{
            suggestedMin: 1200,
            suggestedMax: 1200
        }],
    }
};

function playerEloChart(element) {

    let player = element.attr('data-player');
    let season = element.attr('data-season');

    $.ajax({url: `/stats/player_elo_history/${player}/${season}/`, success: function(data){

        let config = {
            type: 'line',
            data: {
                datasets: [{
                    backgroundColor: '#5C7EBB',
                    borderColor: '#5C7EBB',
                    label: false,
                    data: data,
                    pointStyle: 'circle',
                    fill: false,
                    lineTension: 0,
                }]
            },
            options: chart_options,
        };
        new Chart(element, config);

    }}
    );
}
