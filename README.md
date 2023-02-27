<!DOCTYPE html>
<html>
<head>
  <title>Chart Example</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <canvas id="line-chart"></canvas>
  <canvas id="bar-chart"></canvas>
  <script>
    var data = {{ data | tojson }};
    
    // Line chart
    var lineChart = new Chart(document.getElementById('line-chart'), {
      type: 'line',
      data: {
        labels: Object.keys(data['TCL']),
        datasets: Object.keys(data).map(function(key) {
          return {
            label: key,
            data: Object.values(data[key]),
            fill: false,
            borderColor: '#' + (Math.random() * 0xFFFFFF << 0).toString(16).padStart(6, '0'),
          };
        }),
      },
      options: {
        title: {
          display: true,
          text: 'Line Chart',
        },
      },
    });

    // Bar chart
    var barChart = new Chart(document.getElementById('bar-chart'), {
      type: 'bar',
      data: {
        labels: Object.keys(data['TCL']),
        datasets: Object.keys(data).map(function(key) {
          return {
            label: key,
            data: Object.values(data[key]),
            backgroundColor: '#' + (Math.random() * 0xFFFFFF << 0).toString(16).padStart(6, '0'),
          };
        }),
      },
      options: {
        title: {
          display: true,
          text: 'Bar Chart',
        },
        scales: {
          yAxes: [{
            ticks: {
              beginAtZero: true,
            },
          }],
        },
      },
    });
  </script>
</body>
</html>
