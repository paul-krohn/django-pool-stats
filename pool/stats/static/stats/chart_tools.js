
function ChartOptions({display_label=false}={}) {
    this.maintainAspectRatio = false;
    this.legend = {
        display: false,
    };
    this.scales = {
        xAxes: [{
            display: true,
            type: 'time',
            scaleLabel: {
                display: display_label,
                labelString: 'Month',
            }
        }],
        yAxes:[{
            suggestedMin: 1200,
            suggestedMax: 1200
        }],
    };
}

function Dataset({data=[], color='#5C7EBB'}={}) {
    this.backgroundColor = color;
    this.borderColor = color;
    // this.label = false;
    this.data = data;
    this.pointStyle = 'circle';
    this.fill = false;
    this.lineTension = 0;

}

function playerEloChart(element) {

    let player = element.attr('data-player');
    let season = element.attr('data-season');

    addEloGraphLine(element, player, season);

}

function addEloGraphLine(element, player, season) {

    $.ajax({url: `/stats/player_elo_history/${player}/${season}/`, success: function(data){

        let config = {
            type: 'line',
            data: {
                datasets: [new Dataset({data: data})],
            },
            options: new ChartOptions(),
        };
        new Chart(element, config);

    }}
    );
}
