import pandas as pd
import numpy as np
from datetime import timedelta
import plotly.graph_objects as go
from dash import html, dcc


# --- HELPERS ---
# Format Duration
def format_duration(td):
    """Formats a timedelta into DD:HH:MM:SS."""
    if pd.isnull(td) or td < timedelta(0):
        return "00:00:00:00"
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days:02}:{hours:02}:{minutes:02}:{seconds:02}"

def get_swedish_business_hours(row):
    """Calculates business time based on Swedish work windows."""
    start, end = row['Created'], row['Resolved']
    if pd.isnull(start) or pd.isnull(end) or end <= start:
        return timedelta(0)

    # Use 'min' frequency for precision
    time_range = pd.date_range(start=start, end=end, freq='min')
    day_of_week = time_range.weekday
    hour = time_range.hour

    # Mon-Fri: 07-18 | Sat-Sun: 08-16
    weekday_mask = (day_of_week <= 4) & (hour >= 7) & (hour < 18)
    weekend_mask = (day_of_week >= 5) & (hour >= 8) & (hour < 16)

    valid_minutes = time_range[weekday_mask | weekend_mask]
    return timedelta(minutes=len(valid_minutes))


# --- CORE DASHBOARD FUNCTIONS ---

def calculate_metrics(df):
    """Performs the bulk processing for MTTR and SLA."""
    df = df.copy()
    df['Created'] = pd.to_datetime(df['Created'])
    df['Resolved'] = pd.to_datetime(df['Resolved'])

    # Calculate Business Time
    business_timedeltas = df.apply(get_swedish_business_hours, axis=1)
    df['Resolution_duration'] = business_timedeltas.apply(format_duration)
    df['MTTR'] = business_timedeltas.dt.total_seconds() / 3600

    # SLA Logic
    targets = {'1': 4, '2': 8, '3': 120, '4': 240}

    def check_sla(row):
        prio = str(row['Priority'])
        p_digit = next((s for s in prio if s.isdigit()), '3')
        return "Compliant" if row['MTTR'] <= targets.get(p_digit, 120) else "Breach"

    df['SLA'] = df.apply(check_sla, axis=1)
    return df


def get_fcr_gauges(df):
    """Generates a list of 6 monthly FCR gauges with speedometer style."""
    if df.empty:
        return [html.P("No data available for FCR.")]

    l1_groups = ['Service Desk L1 Sweden', 'Service Desk L1 Finland', 'Service Desk L1 Denmark',
                 'Service Desk L1 Norge', 'Service Desk L1 English']
    resolution_codes = ['Solved (Permanently)', 'Solved Remotely (Permanently)']

    df['Created'] = pd.to_datetime(df['Created'], errors='coerce')
    df = df.dropna(subset=['Created'])
    df['Month_Period'] = df['Created'].dt.to_period('M')

    months = sorted(df['Month_Period'].unique())[-6:]
    gauge_list = []

    # Track previous value for the delta arrow comparison
    prev_val = None

    for m in months:
        month_df = df[df['Month_Period'] == m]
        l1_started = month_df[month_df['First_Assignment_group'].astype(str).str.strip().isin(l1_groups)]

        fcr_tickets = l1_started[
            (l1_started['Assignment_group'].astype(str).str.strip().isin(l1_groups)) &
            (l1_started['Resolution_code'].astype(str).str.strip().isin(resolution_codes))
            ]

        val = (len(fcr_tickets) / len(l1_started) * 100) if len(l1_started) > 0 else 0

        # Create the Figure
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=val,
            # Delta compares this month to the previous month in the loop
            delta={
                'reference': prev_val if prev_val is not None else val,
                'relative': False,
                'increasing': {'color': "#228B22"},
                'decreasing': {'color': "#F70D1A"},
                'position': "top",
                'font': {'size': 15}
            },
            number={
                'suffix': "%",
                'font': {'size': 22, 'color': '#000000', 'family': 'Verdana'}
            },
            title={'text': f"<b>{m.strftime('%b %Y')}</b>", 'font': {'size': 14, 'color': '#334155'}},
            gauge={
                'shape': "angular",
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#B7C0C7"},
                'bar': {'color': "black", 'thickness': 0.15},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "#CAD3D9",
                'steps': [
                    {'range': [0, 80], 'color': "#F70D1A"},  # Red zone
                    {'range': [80, 95], 'color': "#FFBF00"},  # Yellow zone
                    {'range': [95, 100], 'color': "#228B22"}  # Green zone
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 1,
                    'value': 95
                }
            }
        ))

        fig.update_layout(
            height=180,
            margin=dict(l=15, r=15, t=50, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            font={'family': "Verdana"}
        )

        gauge_list.append(html.Div(
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            style={'width': '33%', 'display': 'inline-block'}
        ))

        # Update prev_val for the next month's delta comparison
        prev_val = val

    return gauge_list


def get_mttr_trend_data(df, selected_month):
    """Filters and aggregates MTTR stats with volume counts for bubble sizing."""
    df_copy = df.copy()
    df_copy['Month_Str'] = df_copy['Created'].dt.strftime('%Y-%m')
    filtered_df = df_copy[df_copy['Month_Str'] == selected_month].copy()

    if filtered_df.empty:
        return pd.DataFrame()

    filtered_df['Day'] = filtered_df['Created'].dt.day

    # Aggregating Mean, Median, AND Count (Volume)
    mttr_stats = filtered_df.groupby('Day')['MTTR'].agg(['mean', 'median', 'count']).reset_index()
    mttr_stats = mttr_stats.sort_values('Day')

    def hours_to_hms(h):
        if pd.isna(h): return "00:00:00"
        td = timedelta(hours=h)
        # Assuming format_duration is defined in your helper functions
        return format_duration(td)

    mttr_stats['mean_label'] = mttr_stats['mean'].apply(hours_to_hms)
    mttr_stats['median_label'] = mttr_stats['median'].apply(hours_to_hms)

    return mttr_stats