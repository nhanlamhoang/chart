import dash
from dash import html
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H1("Hello Dash!", className="text-primary"),
    html.P("Dash is working with Bootstrap Components!", className="lead")
])
