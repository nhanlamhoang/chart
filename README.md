<!DOCTYPE html>
<html>
  <head>
    <title>Bar Chart Example</title>
    <style>
      #chart {
        width: 500px;
        height: 300px;
        background-color: #f5f5f5;
        border: 1px solid #ccc;
        padding: 10px;
      }
      .bar {
        width: 50px;
        height: 0;
        background-color: #0099ff;
        margin-right: 10px;
        display: inline-block;
        vertical-align: bottom;
        transition: height 0.5s ease;
      }
    </style>
  </head>
  <body>
    <div id="chart">
      <div class="bar" style="height: 36%"></div>
      <div class="bar" style="height: 75%"></div>
      <div class="bar" style="height: 134%"></div>
      <div class="bar" style="height: 25%"></div>
    </div>
    <script>
      const bars = document.querySelectorAll('.bar');
      bars.forEach(bar => {
        bar.style.height = bar.getAttribute('style').split(':')[1];
      });
    </script>
  </body>
</html>
