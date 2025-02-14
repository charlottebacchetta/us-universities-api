from flask import Flask, request, jsonify, Response
import pandas as pd
import os

app = Flask(__name__)

# Load dataset
DATASET_PATH = "top-200-universities-in-north-america.csv"
if os.path.exists(DATASET_PATH):
    df = pd.read_csv(DATASET_PATH)
else:
    df = pd.DataFrame()  # Empty DataFrame if file is missing

# Ensure Rank is used as the unique identifier
if "Rank" in df.columns:
    df = df.rename(columns={"Rank": "id"})
    df["id"] = df["id"].astype(float)

# Convert numerical columns to proper format
numerical_columns = ["id", "Established", "Academic Staff", "Number of Students", "Minimum Tuition cost", "Volumes in the library", "Endowment"]

# Clean Endowment column (convert from '$1.5B' to float)
if "Endowment" in df.columns:
    df["Endowment"] = df["Endowment"].astype(str).str.replace("$", "").str.replace("B", "e9").str.replace("M", "e6")
    df["Endowment"] = pd.to_numeric(df["Endowment"], errors='coerce').fillna(0).astype(float)

# Convert all other numerical columns to float, handling missing values
for col in numerical_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(float)  # Convert to float and fill NaNs with 0

@app.route("/universities", methods=["GET"])
def list_universities():
    """List universities with optional filtering and format selection."""
    if df.empty:
        return jsonify({"error": "Dataset not loaded."}), 500
    
    # Filtering
    filters = request.args.to_dict()
    categorical_columns = ["Name", "Country"]
    
    result_df = df.copy()
    for filter_col, filter_val in filters.items():
        if filter_col in numerical_columns:
            try:
                # Ensure the filter value has a valid format
                if not (filter_val.startswith(">") or filter_val.startswith("<") or filter_val.startswith("=")):
                    return jsonify({"error": "Invalid filter format. Use '>', '<', or '=' at the start of numeric values."}), 400
                
                # Handle numerical filters with <, >, = operators
                if filter_val.startswith(">"):
                    result_df = result_df[result_df[filter_col] > float(filter_val[1:])]
                elif filter_val.startswith("<"):
                    result_df = result_df[result_df[filter_col] < float(filter_val[1:])]
                elif filter_val.startswith("="):
                    result_df = result_df[result_df[filter_col] == float(filter_val[1:])]
            except ValueError:
                return jsonify({"error": f"Invalid numerical value for column {filter_col}: {filter_val}"}), 400
        elif filter_col in categorical_columns:
            if not isinstance(filter_val, str):
                return jsonify({"error": f"Invalid categorical value for column {filter_col}: {filter_val}"}), 400
            # Handle text filtering with a warning for partial matches
            matched_results = result_df[result_df[filter_col].astype(str).str.contains(filter_val, case=False, na=False)]
            if matched_results.empty:
                return jsonify({"message": f"No exact match found for {filter_col}. Returning partial matches."}), 200
            result_df = matched_results
        else:
            return jsonify({"error": f"Invalid filter column: {filter_col}"}), 400
    
    # Output format
    output_format = request.args.get("format", "json")
    if output_format == "csv":
        csv_data = result_df.to_csv(index=False)
        return Response(csv_data, mimetype="text/csv")
    else:
        return jsonify(result_df.to_dict(orient="records"))

@app.route("/universities/<int:univ_id>", methods=["GET"])
def get_university(univ_id):
    """Retrieve a single university by ID."""
    if df.empty:
        return jsonify({"error": "Dataset not loaded."}), 500
    
    result = df[df["id"] == univ_id]
    if result.empty:
        return jsonify({"error": "University not found."}), 404
    return jsonify(result.to_dict(orient="records")[0])

if __name__ == "__main__":
    app.run(debug=True)
