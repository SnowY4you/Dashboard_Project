from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import timedelta
from calculations import calculate_metrics, get_fcr_gauges

app = Dash(__name__)

# Load and process data once at startup
raw_df = pd.read_excel('cleaned_6_months.xlsx')
df = calculate_metrics(raw_df)

# General Layout
app.layout = html.Div(
    style={'fontFamily': "Verdana", 'padding': '10px', 'backgroundColor': '#3f3f46'},
    children=[
        html.H1("Service Governance Dashboard",
                style={'textAlign': 'center', 'color': '#0C868A'}),

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
                    style={'width': '400px', 'marginBottom': '5px'}
                ),
                dcc.Graph(id="sla-prio-month-graph", style={'height': '350px'})
            ], style={'width': '40%', 'backgroundColor': '#BCC6CC', 'padding': '15px', 'borderRadius': '10px',
                      'boxShadow': '2px 2px 10px #ccc', 'marginRight': '1%', 'height': '430px'}),

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
                'boxShadow': '2px 2px 10px #ccc',
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
            'boxShadow': '2px 2px 10px #ccc',
            'marginTop': '20px'
        })
    ]
)


# --- HELPER: Seconds to HH:MM:SS ---
def seconds_to_hms(hours):
    if pd.isna(hours): return "00:00:00"
    td = timedelta(hours=hours)
    total_seconds = int(td.total_seconds())
    h, remainder = divmod(total_seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# --- Callbacks ---
# Callback for SLA per Priority
@app.callback(
    Output("sla-prio-month-graph", "figure"),
    Input("prio-dropdown", "value")
)
def update_sla_monthly(selected_prio):
    if selected_prio is None or df.empty:
        return go.Figure()

    prio_df = df[df['Priority'] == selected_prio].copy()
    if prio_df.empty: return go.Figure()

    prio_df['Month'] = prio_df['Created'].dt.strftime('%Y-%m')
    stats = prio_df.groupby('Month')['SLA'].apply(lambda x: (x == 'Compliant').mean() * 100).reset_index()
    stats.columns = ['Month', 'Compliance']

    fig = px.bar(stats, x='Month', y='Compliance',
                 color_discrete_sequence=['#4863A0'],
                 text=stats['Compliance'].apply(lambda x: f"{x:.1f}%"))

    fig.add_hline(y=90, line_dash="dash", line_color="#C83F49", opacity=0.5)
    fig.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font={'family': 'Verdana', 'color': '#000000'})
    return fig


# Callback for FCR Gauges
@app.callback(
    Output('fcr-gauges-container', 'children'),
    Input('month-dropdown', 'value')
)
def render_fcr_gauges(_):
    return get_fcr_gauges(df)



# Callback for MTTR Trend Analysis
@app.callback(
    [Output("mttr-trend-graph", "figure"),
     Output("data-completeness-note", "children")],
    Input("month-dropdown", "value")
)
def update_mttr_trend(selected_month):
    from calculations import get_mttr_trend_data
    trend_data = get_mttr_trend_data(df, selected_month)

    if trend_data.empty:
        return go.Figure(), "No data found for this month."

    fig = go.Figure()

    # --- Add Background Performance Bands ---
    # Excellent: 4–8h (Green)
    fig.add_hrect(y0=0, y1=8, fillcolor="#DCFCE7", opacity=0.6, layer="below", line_width=0)

    # Good: 8–15h (Light Green/Yellow)
    fig.add_hrect(y0=8, y1=15, fillcolor="#F0FDF4", opacity=0.4, layer="below", line_width=0)

    # Average / Typical: 15–25h (Yellow/Orange)
    fig.add_hrect(y0=15, y1=25, fillcolor="#FEFCE8", opacity=0.6, layer="below", line_width=0)

    # Needs Improvement: > 25h (Red)
    fig.add_hrect(y0=25, y1=150, fillcolor="#FFF1F2", opacity=0.6, layer="below", line_width=0)

    # MEAN LINE + BUBBLES (Size reflects volume)
    fig.add_trace(go.Scatter(
        x=trend_data['Day'],
        y=trend_data['mean'],
        name='Mean (Size = Volume)',
        mode='lines+markers',
        line=dict(color='#003366', width=2),
        marker=dict(
            size=trend_data['count'],
            sizemode='area',
            sizeref=2. * max(trend_data['count']) / (40.**2),
            sizemin=4,
            color='#003366',
            opacity=0.6
        ),
        customdata=trend_data[['mean_label', 'count']],
        hovertemplate='<b>Day %{x}</b><br>Mean: %{customdata[0]}<br>Resolved: %{customdata[1]} incidents<extra></extra>'
    ))

    # MEDIAN LINE
    fig.add_trace(go.Scatter(
        x=trend_data['Day'],
        y=trend_data['median'],
        name='Median',
        mode='lines',
        line=dict(color='#1BABB0', width=3, dash='dash'),
        customdata=trend_data['median_label'],
        hovertemplate='Median: %{customdata}<extra></extra>'
    ))

    fig.update_layout(
        hovermode='x unified',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(title="Day of Month", tickmode='linear', showgrid=False),
        yaxis=dict(title="Business Hours", gridcolor='rgba(0,0,0,0.1)'),
        font={'family': 'Verdana', 'color': '#003366'},
        margin=dict(l=40, r=40, t=40, b=40)
    )

    footer_content = [
        html.P([
            html.B("Performance Bands: "),
            html.Span("Excellent (4–8h)", style={'color': '#10B981'}), " | ",
            html.Span("Good (8–15h)", style={'color': '#059669'}), " | ",
            html.Span("Typical (15–25h)", style={'color': '#D97706'}), " | ",
            html.Span("Needs Improvement (>25h)", style={'color': '#DC2626'})
        ], style={'fontSize': '13px', 'fontWeight': 'bold', 'marginBottom': '5px'}),

        html.P([
            f"Bubble size indicates incident volume. Analysis for {selected_month} complete. ",
            html.Br(),
            "Note: Markers represent daily averages."
        ], style={'fontSize': '12px', 'color': '#64748b'})
    ]

    return fig, footer_content


if __name__ == "__main__":
    app.run(debug=True)