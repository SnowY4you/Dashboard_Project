from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import timedelta
from calculations import calculate_metrics, get_fcr_gauges, detect_metric_anomaly, get_mttr_trend_data

app = Dash(__name__)

data_file = r'D:\OneDrive\Python\Dashboard_Project\data\cleaned_6_months.xlsx'

# Load and process data once at startup
raw_df = pd.read_excel(data_file)
df = calculate_metrics(raw_df)

# General Layout
app.layout = html.Div(
    style={'fontFamily': "Verdana", 'padding': '10px', 'backgroundColor': '#3f3f46', 'minHeight': '100vh'},
    children=[
        html.H1("Service Governance Dashboard",
                style={'textAlign': 'center', 'color': '#0C868A', 'marginBottom': '20px'}),

        # --- ANOMALY ALERT BAR ---
        html.Div(id='anomaly-alert-bar', style={
            'display': 'flex',
            'justifyContent': 'space-between',
            'marginBottom': '20px',
            'gap': '20px'
        }),

        # TOP SECTION: SLA and FCR Side-by-Side
        html.Div([

            # LEFT: SLA Compliance
            html.Div([
                html.H4("SLA Compliance by Priority", style={'margin': '5px 0', 'textAlign': 'center'}),
                html.P("Select Priority:", style={'fontSize': '12px', 'margin': '0'}),
                dcc.Dropdown(
                    id="prio-dropdown",
                    options=[{'label': f"Priority {i}", 'value': i} for i in sorted(df['Priority'].unique()) if
                             pd.notnull(i)],
                    value=df['Priority'].unique()[0] if not df['Priority'].empty else None,
                    clearable=False,
                    style={'width': '100%', 'marginBottom': '5px'}
                ),
                dcc.Graph(id="sla-prio-month-graph", style={'height': '330px'})
            ], style={'width': '40%', 'backgroundColor': '#BCC6CC', 'padding': '15px', 'borderRadius': '10px',
                      'boxShadow': '2px 2px 10px rgba(0,0,0,0.3)', 'height': '430px'}),

            # RIGHT: FCR Gauges
            html.Div([
                html.H4("Monthly First Contact Resolution (FCR) - 95% Target",
                        style={'margin': '5px 0', 'textAlign': 'center', 'color': '#000000'}),

                html.Div(id='fcr-gauges-container', style={
                    'display': 'flex',
                    'flexWrap': 'wrap',
                    'justifyContent': 'center',
                    'alignItems': 'center',
                    'height': '380px'
                })
            ], style={
                'width': '58%',
                'backgroundColor': '#BCC6CC',
                'padding': '15px',
                'borderRadius': '10px',
                'boxShadow': '2px 2px 10px rgba(0,0,0,0.3)',
                'height': '430px'
            }),

        ], style={'display': 'flex', 'marginBottom': '20px', 'alignItems': 'stretch'}),

        # BOTTOM SECTION: MTTR Trend Analysis
        html.Div([
            html.H4("MTTR Trend Analysis (Mean vs. Median)",
                    style={'margin': '5px 0 0 0', 'textAlign': 'center', 'color': '#000000'}),

            html.Div([
                html.P("Select Month:", style={'fontSize': '12px', 'margin': '0'}),
                dcc.Dropdown(
                    id='month-dropdown',
                    options=[
                        {'label': 'October 2023', 'value': '2023-10'},
                        {'label': 'November 2023', 'value': '2023-11'},
                        {'label': 'December 2023', 'value': '2023-12'},
                        {'label': 'January 2024', 'value': '2024-01'},
                        {'label': 'February 2024', 'value': '2024-02'},
                        {'label': 'March 2024', 'value': '2024-03'},
                    ],
                    value='2024-03',
                    clearable=False,
                    style={'width': '250px', 'marginBottom': '10px'}
                ),
            ]),

            dcc.Graph(id="mttr-trend-graph"),

            html.Div(id='data-completeness-note',
                     style={'marginTop': '15px', 'textAlign': 'center'})

        ], style={
            'backgroundColor': '#BCC6CC',
            'padding': '15px',
            'borderRadius': '10px',
            'boxShadow': '2px 2px 10px rgba(0,0,0,0.3)',
            'marginTop': '20px'
        })
    ]
)


# --- CALLBACKS ---

# 1. Callback for Anomaly Alerts
@app.callback(
    Output('anomaly-alert-bar', 'children'),
    Input('prio-dropdown', 'value')
)
def update_anomaly_alerts(selected_prio):
    # --- 1. SLA Anomaly Check ---
    prio_df = df[df['Priority'] == selected_prio].copy()
    prio_df['Month'] = prio_df['Created'].dt.to_period('M')
    sla_trends = prio_df.groupby('Month')['SLA'].apply(lambda x: (x == 'Compliant').mean() * 100)
    sla_status, sla_color = detect_metric_anomaly(sla_trends)

    # --- 2. FCR Anomaly Check ---
    l1_groups = ['Service Desk L1 Sweden', 'Service Desk L1 Finland', 'Service Desk L1 Denmark',
                 'Service Desk L1 Norge', 'Service Desk L1 English']
    resolution_codes = ['Solved (Permanently)', 'Solved Remotely (Permanently)']
    fcr_df = df[df['First_Assignment_group'].astype(str).str.strip().isin(l1_groups)].copy()
    fcr_df['Month_Period'] = fcr_df['Created'].dt.to_period('M')

    fcr_trends = fcr_df.groupby('Month_Period').apply(
        lambda g: (len(g[g['Resolution_code'].astype(str).str.strip().isin(resolution_codes)]) / len(g) * 100)
        if len(g) > 0 else 0
    )
    fcr_status, fcr_color = detect_metric_anomaly(fcr_trends)

    # --- LOGGING BRANCH TRIGGER ---
    # We trigger the log for both metrics
    from calculations import log_anomaly
    log_anomaly(f"SLA Priority {selected_prio}", sla_status, sla_color)
    log_anomaly("Global FCR", fcr_status, fcr_color)

    # Return UI
    return [
        html.Div([
            html.P(f"P{selected_prio} SLA Health", style={'margin': '0', 'fontSize': '12px', 'fontWeight': 'bold'}),
            html.H3(sla_status, style={'margin': '0', 'color': sla_color, 'fontSize': '20px'})
        ], style={'backgroundColor': '#BCC6CC', 'padding': '15px', 'borderRadius': '10px', 'width': '48%',
                  'textAlign': 'center', 'boxShadow': '2px 2px 5px rgba(0,0,0,0.2)'}),

        html.Div([
            html.P("Global FCR Health", style={'margin': '0', 'fontSize': '12px', 'fontWeight': 'bold'}),
            html.H3(fcr_status, style={'margin': '0', 'color': fcr_color, 'fontSize': '20px'})
        ], style={'backgroundColor': '#BCC6CC', 'padding': '15px', 'borderRadius': '10px', 'width': '48%',
                  'textAlign': 'center', 'boxShadow': '2px 2px 5px rgba(0,0,0,0.2)'})
    ]


# 2. Callback for SLA per Priority Graph
@app.callback(
    Output("sla-prio-month-graph", "figure"),
    Input("prio-dropdown", "value")
)
def update_sla_monthly(selected_prio):
    if selected_prio is None or df.empty:
        return go.Figure()

    prio_df = df[df['Priority'] == selected_prio].copy()
    prio_df['Month'] = prio_df['Created'].dt.strftime('%Y-%m')
    stats = prio_df.groupby('Month')['SLA'].apply(lambda x: (x == 'Compliant').mean() * 100).reset_index()
    stats.columns = ['Month', 'Compliance']

    fig = px.bar(stats, x='Month', y='Compliance',
                 color_discrete_sequence=['#4863A0'],
                 text=stats['Compliance'].apply(lambda x: f"{x:.1f}%"))

    fig.add_hline(
        y=90,
        line_dash="dash",
        line_color="#C83F49",
        opacity=0.5,
        annotation_text="Target 90%",
        annotation_position="top left"
    )
    fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font={'family': 'Verdana', 'color': '#000000'}, margin=dict(l=20, r=20, t=30, b=20))
    fig.update_yaxes(range=[0, 105])
    return fig


# 3. Callback for FCR Gauges
@app.callback(
    Output('fcr-gauges-container', 'children'),
    Input('month-dropdown', 'value')
)
def render_fcr_gauges(_):
    return get_fcr_gauges(df)


# 4. Callback for MTTR Trend Analysis
@app.callback(
    [Output("mttr-trend-graph", "figure"),
     Output("data-completeness-note", "children")],
    Input("month-dropdown", "value")
)
def update_mttr_trend(selected_month):
    trend_data = get_mttr_trend_data(df, selected_month)

    if trend_data.empty:
        return go.Figure(), "No data found for this month."

    fig = go.Figure()

    # Background Performance Bands
    fig.add_hrect(y0=0, y1=8, fillcolor="#DCFCE7", opacity=0.6, layer="below", line_width=0)
    fig.add_hrect(y0=8, y1=15, fillcolor="#F0FDF4", opacity=0.4, layer="below", line_width=0)
    fig.add_hrect(y0=15, y1=25, fillcolor="#FEFCE8", opacity=0.6, layer="below", line_width=0)
    fig.add_hrect(y0=25, y1=150, fillcolor="#FFF1F2", opacity=0.6, layer="below", line_width=0)

    # MEAN LINE + BUBBLES
    fig.add_trace(go.Scatter(
        x=trend_data['Day'], y=trend_data['mean'], name='Mean', mode='lines+markers',
        line=dict(color='#003366', width=2),
        marker=dict(
            size=trend_data['count'], sizemode='area',
            sizeref=2. * max(trend_data['count']) / (40. ** 2), sizemin=4,
            color='#003366', opacity=0.6
        ),
        customdata=trend_data[['mean_label', 'count']],
        hovertemplate='<b>Day %{x}</b><br>Mean: %{customdata[0]}<br>Resolved: %{customdata[1]}<extra></extra>'
    ))

    # MEDIAN LINE
    fig.add_trace(go.Scatter(
        x=trend_data['Day'], y=trend_data['median'], name='Median', mode='lines',
        line=dict(color='#1BABB0', width=3, dash='dash'),
        customdata=trend_data['median_label'],
        hovertemplate='Median: %{customdata}<extra></extra>'
    ))

    fig.update_layout(
        hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Day of Month", tickmode='linear', showgrid=False),
        yaxis=dict(title="Business Hours", gridcolor='rgba(0,0,0,0.1)'),
        font={'family': 'Verdana', 'color': '#003366'}, margin=dict(l=40, r=40, t=40, b=40)
    )

    footer = [
        html.P([
            html.B("Performance Bands: "),
            html.Span("Excellent (4–8h)", style={'color': '#10B981'}), " | ",
            html.Span("Good (8–15h)", style={'color': '#059669'}), " | ",
            html.Span("Typical (15–25h)", style={'color': '#D97706'}), " | ",
            html.Span("Needs Improvement (>25h)", style={'color': '#DC2626'})
        ], style={'fontSize': '13px', 'fontWeight': 'bold'}),
        html.P(f"Analysis for {selected_month} complete.", style={'fontSize': '12px', 'color': '#64748b'})
    ]

    return fig, footer


if __name__ == "__main__":
    app.run(debug=True)