import pytest
import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from data_cleaning import clean_endowment_column

def test_clean_endowment_column():
    """Test that endowment values are correctly converted to numeric format."""
    data = {"Endowment": ["$1.5B", "$500M", "None", "$2.3B"]}
    df = pd.DataFrame(data)
    cleaned_df = clean_endowment_column(df)

    assert cleaned_df["Endowment"][0] == 1.5e9
    assert cleaned_df["Endowment"][1] == 500e6
    assert cleaned_df["Endowment"][2] == 0  # 'None' should be converted to 0
    assert cleaned_df["Endowment"][3] == 2.3e9
