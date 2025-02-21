import pandas as pd
import os

def clean_endowment_column(df):
    """Cleans the 'Endowment' column, converting '$1.5B' format to numeric."""
    if "Endowment" in df.columns:
        df["Endowment"] = df["Endowment"].astype(str).str.replace("$", "", regex=True)
        df["Endowment"] = df["Endowment"].str.replace("B", "e9").str.replace("M", "e6")
        df["Endowment"] = pd.to_numeric(df["Endowment"], errors="coerce").fillna(0)
    return df


def load_and_clean_data(dataset_path):
    """Loads and cleans the dataset."""
    if os.path.exists(dataset_path):
        df = pd.read_csv(dataset_path, encoding='latin1')  # or try 'ISO-8859-1'
    else:
        return pd.DataFrame()  # Return empty DataFrame if file is missing

    # Ensure Rank is used as a unique identifier
    if "Rank" in df.columns:
        df = df.rename(columns={"Rank": "id"})
        df["id"] = df["id"].astype(float)

    # Convert numerical columns
    numerical_columns = ["id", "Established", "Academic Staff", "Number of Students", 
                         "Minimum Tuition cost", "Volumes in the library", "Endowment"]
    
    for col in numerical_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Clean Endowment column
    df = clean_endowment_column(df)

    return df
