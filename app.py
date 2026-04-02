from dash import Dash
import dash_bootstrap_components as dbc
from flask import Flask

# Initialize Flask Server
server = Flask(__name__)

# Initialize Dash App
app = Dash(__name__, server=server, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "AgentAuth"
