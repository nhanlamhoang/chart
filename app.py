# app.py

import dash
from dash import html

# Tạo đối tượng Dash
app = dash.Dash(__name__)

# Gắn layout
app.layout = html.Div([
    html.H1("Ứng dụng Dash đầu tiên của bạn")
])

# Gắn server để Gunicorn có thể nhận ra
server = app.server  # <-- DÒNG NÀY QUAN TRỌNG!

# KHÔNG gọi app.run()
