import pandas as pd
import numpy as np
import random



def run_cleaner():
    print("--- Service Management Tool ---")

    try:
        # Loading data
        print("--- Loading Data ---")
        # 1. LOAD DATA
        print("[1/7] Loading 'All inc 6 months.xlsx'...", end=" ")
        df = pd.read_excel('All inc 6 months.xlsx', engine='openpyxl')
        print("SUCCESS.")

        # ANONYMIZATION & DATA MASKING
        print("--- ANONYMIZATION & DATA MASKING ---")
        # 2. ANONYMIZATION & DATA MASKING
        print("[2/7] Masking PII and Anonymizing Company data...", end=" ")
        # Global replace company_name -> Company
        df = df.replace(to_replace=r'(?i)company_name', value='Company', regex=True)
        print("SUCCESS.")

        # 3. Replace 'Opened by' (Col J) with randomized names
        # Load names from the text files
        with open("../data/first_name.txt", "r", encoding="utf-8") as f:
            first_names = [line.strip() for line in f if line.strip()]

            with open("../data/last_name.txt", "r", encoding="utf-8") as f:
                last_names = [line.strip() for line in f if line.strip()]

        # Replace Opened_by with randomized full names
        df['Opened_by'] = [
            f"{random.choice(first_names)} {random.choice(last_names)}"
            for _ in range(len(df)) ]

        print("[3/7] Replacing 'Opened by' (Col J) with randomized names...")
        print("SUCCESS.")

        # 4. GENERATE INCIDENT NUMBERS (Col A)
        print("[4/7] Generating unique Incident Numbers (INCxxxxxxx)...", end=" ")
        # Generates a list of INC followed by 7 random digits
        df['Number'] = [f"INC{random.randint(1000000, 9999999)}" for _ in range(len(df))]
        print("SUCCESS.")

        # 5. DELETE SPECIFIED COLUMNS (Col E)
        print("[5/7] Removing unnecessary columns (Short Description)...", end=" ")
        # Drop Column E ('Short description')
        if 'E' in df.columns:
        df = df.drop(columns=['E'])
        print("SUCCESS.")

        # 6. DELETE SPECIFIC PATTERN
        print("[6/7] Removing 'any_name_text' patterns from all cells...", end=" ")
        # We replace it with an empty string
        ap_pattern = r'\(AP\d{7}\)'
        df = df.replace(to_replace=ap_pattern, value='', regex=True)
        print("SUCCESS.")

        # Agent assignment and Export
        print("--- Agent assignment and Expoty ---")
        # 7. AGENT ASSIGNMENT & EXPORT
        print("[7/7] Finalizing Agent Assignment and Export...", end=" ")
        # Create pool for Assigned To (Col G)
        agent_names = [f"{random.choice(first_names)} {random.choice(last_names)}" for _ in range(1015)]

        def assign_agent(group):
            g = str(group)
            if "L1" in g: return random.choice(agent_names[:40])
            if "L2" in g: return random.choice(agent_names[40:50])
            return random.choice(agent_names[50:])

        df['Opened'] = df['Assigned_to'].apply(assign_agent)

        df.to_excel('cleaned_6_months_temp.xlsx', index=False)
        print("SUCCESS.")

        print(f"\nReport generated: cleaned_6_months_temp.xlsx")

    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")


if __name__ == "__main__":
    run_cleaner()