# app.py

import dash
from dash import html

# tạo đối tượng app là callable
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Ứng dụng Dash đầu tiên của bạn")
])

# KHÔNG gọi app.run() hoặc app.run_server()
# vì Render sẽ tự làm qua gunicorn
