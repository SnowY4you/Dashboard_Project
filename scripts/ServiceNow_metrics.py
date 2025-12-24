import requests
import pandas as pd

# --- This is just an example script. ---

# -----------------------------
# CONFIGURATION
# -----------------------------
# --- ServiceNow connection details ---
INSTANCE = "https://yourinstance.service-now.com"
USER = "your_username"
PASSWORD = "your_password"

# --- Table you want to query ---
TABLE = "incident"

# --- Fields you want to retrieve ---
FIELDS = [
    "number",
    "state",
    "priority",
    "assignment_group",
    "priority",
    "u_first_assignment_group", # (custom field? often assignment_group or u_first_assignment_group)
    "cmdb_ci", # Configuration_item
    "assignment_group",
    "assigned_to",
    "opened_at", # Opened
    "opened_by",
    "contact_type",
    "contact_type",
    "caller_id", # Caller
    "sys_created_on", # Created
    "resolved_at", # Resolved
    "closed_at", # Closed
    "close_code", # Resolution_code
    "reopened_count",
    "assigned_count",
    "business_duration" # Resolution_duration
]
# Optional: add filters (example: last 30 days)
QUERY = "" # leave empty for all records


# -----------------------------
# BUILD URL
# -----------------------------
# Convert list to comma-separated string
FIELDS_STR = ",".join(FIELDS)

BASE_URL = (
    f"{INSTANCE}/api/now/table/{TABLE}" 
    f"?sysparm_fields={FIELDS_STR}" 
    f"&sysparm_query={QUERY}" f"&sysparm_limit=10000"
)


# ----------------------------- # FETCH ALL RECORDS (pagination) # -----------------------------
def fetch_all_records(url):
    all_results = []
    next_url = url

    while next_url:
        response = requests.get(
            next_url,
            auth=(USER, PASSWORD),
            headers={"Accept": "application/json"}
        )

        if response.status_code != 200:
            print("Error:", response.status_code, response.text)
            break

        data = response.json()
        all_results.extend(data["result"])

        # Check for pagination link
        next_link = response.links.get("next")
        next_url = next_link["url"] if next_link else None

    return all_results


print("Fetching data from ServiceNow…")
records = fetch_all_records(BASE_URL)

print(f"Retrieved {len(records)} records")

# -----------------------------
# CONVERT TO DATAFRAME
# -----------------------------
df = pd.DataFrame(records)

# -----------------------------
# EXPORT
# -----------------------------
df.to_excel("servicenow_export.xlsx", index=False)
df.to_csv("servicenow_export.csv", index=False)

print("Export complete: servicenow_export.xlsx / servicenow_export.csv")
