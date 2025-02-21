from flask import Flask, request, jsonify
import pandas as pd
import os
from data_cleaning import load_and_clean_data  # Import function from new module

app = Flask(__name__)

# Load and clean dataset
df = load_and_clean_data("top-200-universities-in-north-america.csv")


@app.route("/universities", methods=["GET"])
def get_universities():
    """Fetches all universities."""
    return jsonify(df.to_dict(orient="records"))


@app.route("/university/<int:univ_id>", methods=["GET"])
def get_university(univ_id):
    """Fetch a single university by ID."""
    university = df[df["id"] == univ_id]
    if university.empty:
        return jsonify({"error": "University not found"}), 404
    return jsonify(university.to_dict(orient="records")[0])


if __name__ == "__main__":
    app.run(debug=True)
