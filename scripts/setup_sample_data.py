import pandas as pd
import numpy as np
import os

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_survey_data(n=20):
    # Drivers:
    # Q1-Q3: Psych Safety (1-5)
    # Q4-Q5: Manager Support (1-5)
    # Q6: Comp (1-5)
    # Q7-Q8: Role Ambiguity (1-5) [Reverse? No, low is good usually, but let's assume High=Ambiguous=Bad]
    # Q9: Workload (1-5) [High=Heavy=Bad]

    data = {
        "Q1": np.random.randint(1, 6, n),
        "Q2": np.random.randint(2, 6, n), # Skew slightly higher
        "Q3": np.random.randint(1, 5, n),
        "Q4": np.random.randint(3, 6, n),
        "Q5": np.random.randint(3, 6, n),
        "Q6": np.random.randint(1, 4, n), # Low comp satisfaction
        "Q7": np.random.randint(2, 5, n),
        "Q8": np.random.randint(2, 5, n),
        "Q9": np.random.randint(4, 6, n), # High workload
        "Department": np.random.choice(["Sales", "Eng", "HR"], n)
    }
    
    # Introduce some missing values
    df = pd.DataFrame(data)
    df.loc[0, "Q1"] = np.nan
    df.loc[1, "Q9"] = np.nan
    
    df.to_csv(os.path.join(DATA_DIR, "sample_survey.csv"), index=False)
    print("Generated sample_survey.csv")

def generate_kpi_data():
    # Monthly data for 6 months
    dates = pd.date_range(start="2023-01-01", periods=6, freq="M")
    
    data = []
    for dept in ["Sales", "Eng", "HR"]:
        base_to = 0.10 if dept == "Sales" else 0.05
        base_ot = 30 if dept == "Eng" else 10
        
        for d in dates:
            # Random variations
            turnover = max(0, base_to + np.random.normal(0, 0.02))
            overtime = max(0, base_ot + np.random.normal(0, 5))
            
            data.append({
                "Date": d,
                "Department": dept,
                "turnover_rate_junior": turnover,
                "avg_overtime_hours": overtime,
                "manager_overtime": overtime * 1.5 # Managers work more
            })
            
    df = pd.DataFrame(data)
    df.to_csv(os.path.join(DATA_DIR, "sample_kpi.csv"), index=False)
    print("Generated sample_kpi.csv")

if __name__ == "__main__":
    generate_survey_data()
    generate_kpi_data()
