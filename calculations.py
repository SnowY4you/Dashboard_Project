import pandas as pd
import numpy as np
from datetime import timedelta, datetime  # Added datetime here
import plotly.graph_objects as go
from dash import html, dcc
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# --- LOGGING SETUP ---
logging.basicConfig(
    filename='service_alerts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global tracker to prevent email spam (Cool-down: 4 hours)
last_alert_sent = {}

# --- EMAIL CONFIG (Update these with your details) ---
SMTP_SERVER = "smtp.your-office365.com"
SMTP_PORT = 587
SENDER_EMAIL = "alerts@yourcompany.com"
RECEIVER_EMAIL = "manager@yourcompany.com"
EMAIL_PASSWORD = "your-app-password"


# --- HELPERS ---

def send_email_alert(subject, body):
    """Sends a formatted email alert via SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


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

    time_range = pd.date_range(start=start, end=end, freq='min')
    day_of_week = time_range.weekday
    hour = time_range.hour

    weekday_mask = (day_of_week <= 4) & (hour >= 7) & (hour < 18)
    weekend_mask = (day_of_week >= 5) & (hour >= 8) & (hour < 16)

    valid_minutes = time_range[weekday_mask | weekend_mask]
    return timedelta(minutes=len(valid_minutes))


# --- ANOMALY & LOGGING LOGIC ---

def detect_metric_anomaly(series, sigma_threshold=2):
    """
    Identifies outliers using Z-Score and sigma_threshold.
    """
    if len(series) < 3:
        return "INSUFFICIENT DATA", "#64748b"

    baseline = series[:-1]
    current = series.iloc[-1]

    mu = baseline.mean()
    std = baseline.std() if baseline.std() != 0 else 0.001

    z_score = (current - mu) / std

    # Logic using the sigma_threshold parameter
    if z_score < -(sigma_threshold + 1):  # e.g., < -3
        return "CRITICAL PERFORMANCE DROP", "#F70D1A"
    elif z_score < -sigma_threshold:  # e.g., < -2
        return "UNUSUAL DECREASE", "#FFBF00"
    elif z_score > sigma_threshold:
        return "SIGNIFICANT IMPROVEMENT", "#228B22"
    else:
        return "STABLE PERFORMANCE", "#0C868A"


def log_anomaly(metric_name, status, color):
    """Logs to file and triggers email on critical anomalies."""
    global last_alert_sent

    # Only act if status is not stable
    if color in ["#F70D1A", "#FFBF00"]:
        severity = "CRITICAL" if color == "#F70D1A" else "WARNING"
        now = datetime.now()

        # Log to file (Always)
        logging.warning(f"[{severity}] {metric_name}: {status}")

        # Email Trigger (Critical only + Cool-down)
        if severity == "CRITICAL":
            last_time = last_alert_sent.get(metric_name)
            if last_time is None or (now - last_time) > timedelta(hours=4):
                subj = f"🚨 SLA ALERT: {metric_name}"
                body = f"Anomaly Detected: {status}\nTime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
                send_email_alert(subj, body)
                last_alert_sent[metric_name] = now


# --- CORE DASHBOARD FUNCTIONS ---

def calculate_metrics(df):
    df = df.copy()
    df['Created'] = pd.to_datetime(df['Created'])
    df['Resolved'] = pd.to_datetime(df['Resolved'])
    business_timedeltas = df.apply(get_swedish_business_hours, axis=1)
    df['Resolution_duration'] = business_timedeltas.apply(format_duration)
    df['MTTR'] = business_timedeltas.dt.total_seconds() / 3600
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
    prev_val = None

    for m in months:
        month_df = df[df['Month_Period'] == m]
        l1_started = month_df[month_df['First_Assignment_group'].astype(str).str.strip().isin(l1_groups)]

        fcr_tickets = l1_started[
            (l1_started['Assignment_group'].astype(str).str.strip().isin(l1_groups)) &
            (l1_started['Resolution_code'].astype(str).str.strip().isin(resolution_codes))
            ]

        val = (len(fcr_tickets) / len(l1_started) * 100) if len(l1_started) > 0 else 0

        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=val,
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
                    {'range': [0, 80], 'color': "#F70D1A"},
                    {'range': [80, 95], 'color': "#FFBF00"},
                    {'range': [95, 100], 'color': "#228B22"}
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
        prev_val = val

    return gauge_list


def get_mttr_trend_data(df, selected_month):
    """Filters and aggregates MTTR stats."""
    df_copy = df.copy()
    df_copy['Month_Str'] = df_copy['Created'].dt.strftime('%Y-%m')
    filtered_df = df_copy[df_copy['Month_Str'] == selected_month].copy()

    if filtered_df.empty:
        return pd.DataFrame()

    filtered_df['Day'] = filtered_df['Created'].dt.day
    mttr_stats = filtered_df.groupby('Day')['MTTR'].agg(['mean', 'median', 'count']).reset_index()
    mttr_stats = mttr_stats.sort_values('Day')

    def hours_to_hms(h):
        if pd.isna(h): return "00:00:00"
        td = timedelta(hours=h)
        return format_duration(td)

    mttr_stats['mean_label'] = mttr_stats['mean'].apply(hours_to_hms)
    mttr_stats['median_label'] = mttr_stats['median'].apply(hours_to_hms)

    return mttr_stats


# Setup logging configuration
logging.basicConfig(
    filename='service_alerts.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def send_email_alert(subject, body):
    """Sends a formatted email alert."""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        logging.error(f"Failed to send email: {e}")


# Global dictionary to prevent spam (Cool-down)
last_alert_sent = {}


def log_anomaly(metric_name, status, color):
    """Logs to file and sends email if critical."""
    global last_alert_sent

    if color == "#F70D1A":  # CRITICAL ONLY
        severity = "CRITICAL"
        current_time = datetime.now()

        # Check if we've already emailed about this metric in the last 4 hours
        last_time = last_alert_sent.get(metric_name)
        if last_time is None or (current_time - last_time) > timedelta(hours=4):
            # 1. Log to File
            logging.critical(f"{metric_name} - {status}")

            # 2. Send Email
            subject = f"🚨 GOVERNANCE ALERT: {metric_name}"
            body = f"""
            Automatic Anomaly Detection Alert
            ----------------------------------
            Metric: {metric_name}
            Status: {status}
            Detected At: {current_time.strftime('%Y-%m-%d %H:%M:%S')}

            Please check the Service Governance Dashboard for details.
            """
            send_email_alert(subject, body)

            # Update last sent time
            last_alert_sent[metric_name] = current_time