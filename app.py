import dash
from dash import html

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("Ứng dụng Dash đầu tiên của bạn")
])

server = app.server  # 💡 Quan trọng cho Render dùng Gunicorn
