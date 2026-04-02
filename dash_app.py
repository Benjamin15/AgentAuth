import dash
from dash import html, dcc, Input, Output, State, ALL
from dash.exceptions import PreventUpdate
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Agent, AuditLog, Integration, AgentPermission
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta


# IMPORTANT: requests_pathname_prefix must match the FastAPI mount path
app = dash.Dash(
    __name__, 
    requests_pathname_prefix='/dashboard/', 
    external_stylesheets=['/assets/style.css'],
    suppress_callback_exceptions=True
)

# Define layout components
def get_sidebar():
    return html.Div(className="sidebar", children=[
        html.H2("AgentAuth"),
        html.Button("Dashboard", id="nav-dashboard", className="nav-link"),
        html.Button("Agents", id="nav-agents", className="nav-link active"),
        html.Button("Integrations", id="nav-integrations", className="nav-link"),
        html.Button("Audit Logs", id="nav-logs", className="nav-link"),
    ])

def get_dashboard_view():
    db = SessionLocal()
    total_reqs = db.query(AuditLog).count()
    denied_reqs = db.query(AuditLog).filter(AuditLog.response_status == 403).count()
    active_agents = db.query(Agent).filter(Agent.is_frozen == False).count()
    
    # Data for charts
    logs = db.query(AuditLog).all()
    db.close()
    
    if not logs:
        return html.Div([html.H1("Dashboard"), html.P("No data available yet.")])
        
    df = pd.DataFrame([{
        'timestamp': l.timestamp,
        'service': l.target_service,
        'status': l.response_status,
        'agent_id': l.agent_id
    } for l in logs])
    
    # 1. Success Rate Chart
    df['result'] = df['status'].apply(lambda x: "Success" if x == 200 else "Error/Denied")
    fig_pie = px.pie(df, names='result', hole=.5, 
                     color_discrete_sequence=['#10b981', '#ef4444'],
                     template='plotly_dark')
    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)

    # 2. Service Distribution
    fig_services = px.bar(df.groupby('service').size().reset_index(name='count'), 
                          x='service', y='count', template='plotly_dark',
                          color_discrete_sequence=['#3b82f6'])
    fig_services.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    # 3. Time Series
    df['hour'] = df['timestamp'].dt.to_period('h').astype(str)
    timeseries = df.groupby('hour').size().reset_index(name='count')
    fig_time = px.line(timeseries, x='hour', y='count', template='plotly_dark',
                       color_discrete_sequence=['#3b82f6'])
    fig_time.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    return html.Div(className="animated", children=[
        html.H1("Analytics Overview"),
        html.Div(className="metrics-grid", children=[
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Total Requests", className="metric-label"),
                html.Span(str(total_reqs), className="metric-value")
            ]),
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Access Denied", className="metric-label"),
                html.Span(str(denied_reqs), className="metric-value", style={"color": "var(--danger-color)"})
            ]),
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Active Agents", className="metric-label"),
                html.Span(str(active_agents), className="metric-value")
            ]),
        ]),
        
        html.Div(className="dashboard-row", children=[
            html.Div(className="glass-panel dashboard-col", children=[
                html.H3("Requests Over Time"),
                dcc.Graph(figure=fig_time, config={'displayModeBar': False})
            ]),
        ]),
        html.Div(className="dashboard-row", children=[
            html.Div(className="glass-panel dashboard-col", children=[
                html.H3("Success vs Denied"),
                dcc.Graph(figure=fig_pie, config={'displayModeBar': False})
            ]),
            html.Div(className="glass-panel dashboard-col", children=[
                html.H3("Hits by Integration"),
                dcc.Graph(figure=fig_services, config={'displayModeBar': False})
            ]),
        ])
    ])

def get_agents_view():

    db = SessionLocal()
    agents = db.query(Agent).all()
    
    # 1. Creation Form
    creation_form = html.Div(className="glass-panel", style={"marginBottom": "40px", "border": "1px dashed var(--accent-color)"}, children=[
        html.H3("Add New Agent"),
        html.Div(style={"display": "flex", "gap": "10px", "marginBottom": "10px"}, children=[
            dcc.Input(id="new-agent-name", type="text", placeholder="Agent Name (e.g. Email Bot)", 
                      style={"flex": "1", "padding": "10px", "borderRadius": "8px", "background": "rgba(0,0,0,0.2)", "color": "white", "border": "1px solid var(--glass-border)"}),
            dcc.Input(id="new-agent-desc", type="text", placeholder="Description (optional)", 
                      style={"flex": "2", "padding": "10px", "borderRadius": "8px", "background": "rgba(0,0,0,0.2)", "color": "white", "border": "1px solid var(--glass-border)"}),
            html.Button("Create Agent", id="create-agent-btn", className="btn-premium")
        ]),
        html.Div(id="creation-status", style={"color": "#10b981", "fontSize": "0.9rem"})
    ])

    # 1b. Fetch active integrations for the dropdowns
    integrations = db.query(Integration).filter(Integration.is_active == True).all()
    integration_options = [{"label": i.name.capitalize(), "value": i.name} for i in integrations]

    # 2. Agent Cards
    agent_cards_list = []
    for agent in agents:
        status_text = "(FROZEN)" if agent.is_frozen else "(ACTIVE)"
        
        # Permissions Tags
        perm_tags = []
        for perm in agent.permissions:
            perm_tags.append(html.Span([
                perm.scope,
                html.Span(" ×", id={'type': 'revoke-perm', 'agent': agent.id, 'scope': perm.scope}, className="delete-icon")
            ], className="permission-tag"))

        agent_cards_list.append(html.Div(className="glass-panel", style={"marginBottom": "20px"}, children=[
            html.Div(style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}, children=[
                html.Div([
                    html.H3(f"{agent.name} {status_text}"),
                    html.P(agent.description, style={"color": "var(--text-muted)", "fontSize": "0.9rem", "marginTop": "-10px"})
                ]),
                html.Button(
                    "Unfreeze" if agent.is_frozen else "Kill Switch (Freeze)",
                    id={'type': 'freeze-btn', 'index': agent.id},
                    className="btn-premium btn-danger" if not agent.is_frozen else "btn-premium"
                )
            ]),
            
            # Permissions Section
            html.Div(style={"marginTop": "10px", "borderTop": "1px solid var(--glass-border)", "paddingTop": "10px"}, children=[
                html.Label("Authorized Scopes:", style={"fontSize": "0.8rem", "color": "var(--text-muted)", "display": "block"}),
                html.Div(perm_tags if perm_tags else html.Em("No permissions granted.", style={"fontSize": "0.8rem", "color": "var(--danger-color)"}), style={"marginBottom": "15px"}),
                
                # Add Permission UI
                html.Div(style={"display": "flex", "gap": "10px", "alignItems": "center"}, children=[
                    dcc.Dropdown(
                        id={'type': 'perm-dropdown', 'index': agent.id},
                        options=integration_options,
                        placeholder="Select scope...",
                        style={"flex": "1", "background": "transparent", "color": "black"} 
                    ),
                    html.Button("Grant", id={'type': 'grant-btn', 'index': agent.id}, className="btn-premium", style={"padding": "5px 15px", "fontSize": "0.8rem"}),
                    html.Button("📈 Stats", id={'type': 'stats-btn', 'index': agent.id}, className="btn-premium", style={"padding": "5px 15px", "fontSize": "0.8rem", "background": "#6366f1"})
                ])
            ]),

            html.P([
                html.Span("API Key: ", style={"color": "var(--text-muted)", "fontSize": "0.8rem"}),
                html.Code(agent.api_key, style={"background": "rgba(0,0,0,0.3)", "padding": "4px 8px", "borderRadius": "4px", "fontSize": "0.8rem"})
            ], style={"marginTop": "15px"})
        ]))
        
    db.close()
        
    return html.Div([
        html.H1("AI Agents"),
        html.P("Manage non-human identities accessing your APIs."),
        creation_form,
        html.Div(agent_cards_list, id="agents-container")
    ], className="animated")


def get_agent_stats_view(agent_id):
    db = SessionLocal()
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        db.close()
        return html.Div("Agent not found.")
    
    logs = db.query(AuditLog).filter(AuditLog.agent_id == agent_id).all()
    db.close()
    
    if not logs:
        return html.Div([
            html.Button("← Back to Agents", id="back-to-agents", className="btn-premium", style={"marginBottom": "20px"}),
            html.H1(f"Analytics for {agent.name}"),
            html.P("No audit logs available for this agent yet.")
        ])
        
    df = pd.DataFrame([{
        'timestamp': l.timestamp,
        'service': l.target_service,
        'status': l.response_status
    } for l in logs])
    
    # KPIs
    total_hits = len(logs)
    success_rate = (len(df[df['status'] == 200]) / total_hits) * 100 if total_hits > 0 else 0
    top_service = df['service'].value_counts().idxmax() if total_hits > 0 else "N/A"

    # Time Series for THIS agent
    df['hour'] = df['timestamp'].dt.to_period('h').astype(str)
    timeseries = df.groupby('hour').size().reset_index(name='count')
    fig_time = px.line(timeseries, x='hour', y='count', template='plotly_dark',
                       title="Request Volume (Last 24h)", color_discrete_sequence=['#8b5cf6'])
    fig_time.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    # Service Distribution for THIS agent
    fig_pie = px.pie(df, names='service', template='plotly_dark',
                     hole=.4, title="Service Usage", color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')

    return html.Div(className="animated", children=[
        html.Button("← Back to Agents", id={'type': 'back-btn', 'index': 'agents'}, className="btn-premium", style={"marginBottom": "20px"}),
        html.H1(f"Analytics for {agent.name}"),
        html.P(agent.description, style={"color": "var(--text-muted)", "marginTop": "-10px"}),
        
        html.Div(className="metrics-grid", children=[
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Total Hits", className="metric-label"),
                html.Span(str(total_hits), className="metric-value")
            ]),
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Success Rate", className="metric-label"),
                html.Span(f"{success_rate:.1f}%", className="metric-value", style={"color": "#10b981"})
            ]),
            html.Div(className="glass-panel metric-card", children=[
                html.Span("Top Service", className="metric-label"),
                html.Span(top_service.capitalize(), className="metric-value", style={"color": "var(--accent-color)"})
            ]),
        ]),
        
        html.Div(className="dashboard-row", children=[
            html.Div(className="glass-panel dashboard-col", children=[
                dcc.Graph(figure=fig_time, config={'displayModeBar': False})
            ]),
            html.Div(className="glass-panel dashboard-col", children=[
                dcc.Graph(figure=fig_pie, config={'displayModeBar': False})
            ]),
        ])
    ])

def get_logs_view():
    db = SessionLocal()
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all()
    db.close()
    
    log_rows = []
    for log in logs:
        log_rows.append(html.Tr([
            html.Td(log.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
            html.Td(f"Agent #{log.agent_id}"),
            html.Td(log.target_service),
            html.Td(log.response_status),
            html.Td(str(log.request_details))
        ]))
        
    return html.Div([
        html.H1("Global Audit Logs"),
        html.Div(className="glass-panel", children=[
            html.Table(style={"width": "100%", "textAlign": "left", "borderCollapse": "collapse"}, children=[
                html.Thead(html.Tr([html.Th("Time"), html.Th("Agent"), html.Th("Service"), html.Th("Status"), html.Th("Details")])),
                html.Tbody(log_rows)
            ])
        ])
    ], className="animated")

def get_integrations_view():
    db = SessionLocal()
    gemini = db.query(Integration).filter(Integration.name == "gemini").first()
    db.close()
    
    current_key = gemini.provider_key if gemini else ""
    
    return html.Div([
        html.H1("Connect Providers"),
        html.P("Set your master API keys here. They are hidden from your agents."),
        html.Div(className="glass-panel", children=[
            html.H3("Google Gemini"),
            html.P("Enter your Gemini API Key:", style={"color": "var(--text-muted)"}),
            dcc.Input(id="gemini-key-input", type="password", value=current_key, placeholder="AIzaSy...", 
                      style={"width": "100%", "padding": "12px", "borderRadius": "8px", "border": "1px solid var(--glass-border)", "background": "rgba(0,0,0,0.2)", "color": "white", "marginBottom": "15px"}),
            html.Button("Save Gemini Key", id="save-gemini-btn", className="btn-premium"),
            html.Div(id="save-status", style={"marginTop": "10px", "color": "#10b981"})
        ])
    ], className="animated")



app.layout = html.Div(className="app-container", children=[
    get_sidebar(),
    html.Div(id="page-content", className="main-content", children=get_dashboard_view()),
    dcc.Interval(id='dashboard-interval', interval=30*1000, n_intervals=0),
    dcc.Store(id='active-agent-id', data=None), # Store currently viewed agent ID
    dcc.Location(id='url', refresh=False)
])

# Callbacks
@app.callback(
    Output("page-content", "children"),
    Output("active-agent-id", "data"),
    Input("nav-dashboard", "n_clicks"),
    Input("nav-agents", "n_clicks"),
    Input("nav-integrations", "n_clicks"),
    Input("nav-logs", "n_clicks"),
    Input({'type': 'back-btn', 'index': ALL}, 'n_clicks'),
    Input({'type': 'stats-btn', 'index': ALL}, 'n_clicks'),
    State("active-agent-id", "data"),
    prevent_initial_call=True
)
def render_page(dash_clicks, agents_clicks, int_clicks, logs_clicks, back_clicks, stats_clicks, active_agent_id):
    ctx = dash.callback_context
    if not ctx.triggered:
        return get_dashboard_view(), None
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Check if a dictionary ID was triggered (Stats button)
    try:
        t_id = dash.callback_context.triggered_id
        if isinstance(t_id, dict):
            if t_id.get("type") == "stats-btn":
                agent_id = t_id["index"]
                return get_agent_stats_view(agent_id), agent_id
            if t_id.get("type") == "back-btn" and t_id.get("index") == "agents":
                return get_agents_view(), None
    except:
        pass

    if button_id == "nav-logs":
        return get_logs_view(), None
    if button_id == "nav-integrations":
        return get_integrations_view(), None
    if button_id == "nav-agents":
        return get_agents_view(), None
        
    return get_dashboard_view(), None

@app.callback(
    Output("save-status", "children"),
    Input("save-gemini-btn", "n_clicks"),
    State("gemini-key-input", "value"),
    prevent_initial_call=True
)
def save_gemini_key(n_clicks, key_value):
    if not n_clicks:
        raise PreventUpdate
    db = SessionLocal()
    gemini = db.query(Integration).filter(Integration.name == "gemini").first()
    if not gemini:
        gemini = Integration(name="gemini")
        db.add(gemini)
    gemini.provider_key = key_value
    db.commit()
    db.close()
    return "✅ Gemini Key saved successfully!"

@app.callback(
    Output("agents-container", "children"),

    Output("creation-status", "children"),
    Input({'type': 'freeze-btn', 'index': ALL}, 'n_clicks'),
    Input("create-agent-btn", "n_clicks"),
    Input({'type': 'grant-btn', 'index': ALL}, 'n_clicks'),
    Input({'type': 'revoke-perm', 'agent': ALL, 'scope': ALL}, 'n_clicks'),
    State("new-agent-name", "value"),
    State("new-agent-desc", "value"),
    State({'type': 'perm-dropdown', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def handle_agent_dashboard(freeze_clicks, create_clicks, grant_clicks, revoke_clicks, new_name, new_desc, dropdown_values):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
        
    t_id = ctx.triggered_id
    db = SessionLocal()
    status_msg = ""
    
    # 1. Handle Creation (Single ID)
    if t_id == "create-agent-btn":
        if not new_name:
            db.close()
            return dash.no_update, "❌ Name is required"
        new_agent = Agent(name=new_name, description=new_desc or "")
        db.add(new_agent)
        db.commit()
        status_msg = f"✅ Agent '{new_name}' created!"
        
    # 2. Handle Dictionary IDs (Freeze, Grant, Revoke)
    elif isinstance(t_id, dict):
        t_type = t_id.get('type')
        
        if t_type == 'freeze-btn':
            agent_id = t_id['index']
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.is_frozen = not agent.is_frozen
                db.commit()
                
        elif t_type == 'grant-btn':
            agent_id = t_id['index']
            # Find the dropdown value corresponding to this agent_id
            scope = None
            # dropdown_values is State(...) which is index 2 among States? 
            # In Dash ALL States, it's a list. We need to match it using ctx.states_list
            states = ctx.states_list
            # dropdown_values was the 3rd State altogether? No, it's the 3rd *argument* to callback that is a State.
            # actually check States: new-agent-name (1), new-agent-desc (2), perm-dropdown (3)
            # So dropdown_values is a list. And ctx.states_list[2] contains the list of dicts with ids.
            for s_item in ctx.states_list[2]:
                if s_item['id']['index'] == agent_id:
                    scope = s_item['value']
                    break
            
            if scope:
                existing = db.query(AgentPermission).filter(AgentPermission.agent_id == agent_id, AgentPermission.scope == scope).first()
                if not existing:
                    db.add(AgentPermission(agent_id=agent_id, scope=scope))
                    db.commit()
                    
        elif t_type == 'revoke-perm':
            agent_id = t_id['agent']
            scope = t_id['scope']
            perm = db.query(AgentPermission).filter(AgentPermission.agent_id == agent_id, AgentPermission.scope == scope).first()
            if perm:
                db.delete(perm)
                db.commit()
            
    db.close()
    
    # Re-render agents
    updated_view = get_agents_view()
    agents_list_children = dash.no_update
    for child in updated_view.children:
        if getattr(child, 'id', None) == "agents-container":
            agents_list_children = child.children
            break
            
    return agents_list_children, status_msg

if __name__ == '__main__':
    app.run_server(debug=True)
