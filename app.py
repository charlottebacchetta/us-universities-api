# app.py
import os
import re
import pandas as pd
from flask import Flask, request, jsonify, make_response
from data_cleaning import load_and_clean_data  # your existing loader

app = Flask(__name__)

# ---------- Load data & normalize ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "top-200-universities-in-north-america.csv")

df = load_and_clean_data(DATA_PATH).copy()

# Ensure an integer ID exists
if "id" not in df.columns:
    df = df.reset_index(drop=True)
    df.insert(0, "id", (df.index + 1).astype(int))
else:
    df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)

# Rename to snake_case for clean query params
RENAME_MAP = {
    "Name": "name",
    "Country": "country",
    "Established": "established",
    "Academic Staff": "academic_staff",
    "Number of Students": "number_of_students",
    "Minimum Tuition cost": "min_tuition_cost",
    "Volumes in the library": "volumes_in_library",
    "Endowment": "endowment",
}
df = df.rename(columns=RENAME_MAP)

# Coerce numerics safely (these may or may not exist depending on CSV)
NUM_COLS = [
    "established",
    "academic_staff",
    "number_of_students",
    "min_tuition_cost",
    "volumes_in_library",
    "endowment",
]
for c in NUM_COLS:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

ALLOWED_SORT = {"id", "name", "country", *NUM_COLS}


# ---------- Helpers ----------
def _parse_number(token: str):
    """Parse '2k', '5m', '5b', '12345' into a float."""
    if token is None:
        return None
    t = token.strip().lower().replace(",", "")
    m = re.match(r"^([0-9]*\.?[0-9]+)\s*([kmb])?$", t)
    if not m:
        return None
    val = float(m.group(1))
    suf = m.group(2)
    if suf == "k":
        val *= 1_000
    elif suf == "m":
        val *= 1_000_000
    elif suf == "b":
        val *= 1_000_000_000
    return val


FIELD_ALIASES = {
    "established": "established",
    "founded": "established",
    "academic staff": "academic_staff",
    "staff": "academic_staff",
    "students": "number_of_students",
    "number of students": "number_of_students",
    "tuition": "min_tuition_cost",
    "minimum tuition cost": "min_tuition_cost",
    "volumes": "volumes_in_library",
    "library volumes": "volumes_in_library",
    "volumes in the library": "volumes_in_library",
    "endowment": "endowment",
    "country": "country",
    "name": "name",
}

def _normalize_field(token: str):
    if not token:
        return None
    token = token.strip().lower()
    if token in FIELD_ALIASES:
        return FIELD_ALIASES[token]
    for k, v in FIELD_ALIASES.items():
        if token in k or k in token:
            return v
    return None


# ---------- Routes ----------
@app.get("/")
def index():
    return {
        "message": "University API is running",
        "endpoints": {
            "/universities": "List/query universities",
            "/university/<id>": "Get one university",
            "/nlq?q=...": "Natural-language query",
            "/schema": "List fields and types",
            "/help": "Usage guide",
            "/health": "Health check",
        },
        "try_examples": [
            "/universities?min_endowment=5",
            "/universities?country=us&min_number_of_students=30000&sort_by=established&order=asc&limit=10",
            "/nlq?q=founded%20before%201900%20with%20staff%20over%202k",
        ],
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    return {
        "fields": [
            {"name": c, "dtype": str(df[c].dtype)} for c in df.columns
        ],
        "sortable": sorted(ALLOWED_SORT),
        "numeric": [c for c in NUM_COLS if c in df.columns],
    }

@app.get("/help")
def help_():
    return {
        "message": "Welcome to the University API with Natural-Language Queries!",
        "how_to_use": "Use /universities with query params, or /nlq?q=... with plain-English queries.",
        "examples": [
            "/universities?min_endowment=5",
            "/universities?country=us&min_number_of_students=30000&sort_by=established&order=asc&limit=10",
            "/nlq?q=founded before 1900 with staff over 2k",
            "/nlq?q=universities with endowment > 5b",
            "/nlq?q=top 10 us universities by students",
            "/nlq?q=canada students between 20000 and 40000 sort by endowment desc",
            "/nlq?q=name contains tech top 5 by library volumes",
        ],
        "supported_patterns": {
            "Country filter": "in <country> OR country <country>",
            "Name filter": "name contains <text> OR containing '<text>'",
            "Between range": "<field> between A and B",
            "Inequalities": "<field> > N, >= N, < N, <= N, over/under/at least/at most/more than/less than",
            "Founded": "founded/established before YEAR OR after YEAR",
            "Sorting": "by <field> [asc|desc] OR sort by <field> [asc|desc]",
            "Top/first/last": "top N, first N, last N",
        },
        "fields_supported": [
            "established", "academic_staff", "number_of_students",
            "min_tuition_cost", "volumes_in_library", "endowment",
            "country", "name"
        ],
        "numeric_suffixes": {"k": "×1,000", "m": "×1,000,000", "b": "×1,000,000,000"},
        "notes": [
            "Default limit is 50 results unless you specify 'top N' (in /nlq) or set 'limit='.",
            "Queries are case-insensitive.",
            "This is rule-based: stick to the patterns above.",
        ],
    }

@app.get("/universities")
def get_universities():
    """
    Query params (all optional)

    Text contains:
      country=<str>, name=<str>

    Numeric ranges (each supports min_*/max_*):
      min_established / max_established
      min_academic_staff / max_academic_staff
      min_number_of_students / max_number_of_students
      min_min_tuition_cost / max_min_tuition_cost
      min_volumes_in_library / max_volumes_in_library
      min_endowment / max_endowment

    Sorting & pagination:
      sort_by=<field in /schema 'sortable'>, order=asc|desc
      limit=<int, default 50>, offset=<int, default 0>
    """
    res = df.copy()

    # --- text filters ---
    country = request.args.get("country")
    name = request.args.get("name")
    if country and "country" in res.columns:
        res = res[res["country"].astype(str).str.contains(country, case=False, na=False)]
    if name and "name" in res.columns:
        res = res[res["name"].astype(str).str.contains(name, case=False, na=False)]

    # --- numeric range filters helper ---
    def apply_range(frame: pd.DataFrame, col: str) -> pd.DataFrame:
        if col not in frame.columns:
            return frame
        min_v = request.args.get(f"min_{col}")
        max_v = request.args.get(f"max_{col}")
        out = frame.copy()
        out[col] = pd.to_numeric(out[col], errors="coerce")
        if min_v is not None:
            out = out[out[col] >= pd.to_numeric(min_v, errors="coerce")]
        if max_v is not None:
            out = out[out[col] <= pd.to_numeric(max_v, errors="coerce")]
        return out

    for col in NUM_COLS:
        res = apply_range(res, col)

    # --- sorting ---
    sort_by = request.args.get("sort_by")
    order = (request.args.get("order") or "asc").lower()
    if sort_by in ALLOWED_SORT:
        res = res.sort_values(sort_by, ascending=(order != "desc"), na_position="last")

    # --- pagination ---
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)
    total = int(res.shape[0])
    res = res.iloc[offset: offset + limit]

    response = make_response(jsonify(res.to_dict(orient="records")))
    response.headers["X-Total-Count"] = str(total)
    return response

@app.get("/university/<int:univ_id>")
def get_university(univ_id: int):
    row = df[df["id"] == univ_id]
    if row.empty:
        return jsonify({"error": "University not found"}), 404
    return jsonify(row.to_dict(orient="records")[0])

# ---------- Natural-language query ----------
@app.get("/nlq")
def nlq():
    """
    Natural-language query, e.g.:
      /nlq?q=founded before 1900 with staff over 2k
      /nlq?q=universities with endowment > 5b
      /nlq?q=top 10 us universities by students
      /nlq?q=canada students between 20000 and 40000 sort by endowment desc
      /nlq?q=name contains tech top 5 by library volumes
    Returns JSON array and X-Total-Count header.
    """
    q = (request.args.get("q") or "").strip()
    res = df.copy()

    # Country filter: "in <country>" or "country <country>"
    m = re.search(r"\b(in|country)\s+([a-zA-Z]+)\b", q, re.I)
    if m and "country" in res.columns:
        country = m.group(2)
        res = res[res["country"].astype(str).str.contains(country, case=False, na=False)]

    # Name contains: "name contains X" or 'containing "X"'
    m = re.search(r'(name\s+contains|containing)\s+"?([a-z0-9 \-]+)"?', q, re.I)
    if m and "name" in res.columns:
        needle = m.group(2).strip()
        res = res[res["name"].astype(str).str.contains(needle, case=False, na=False)]

    # Between: "<field> between A and B"
    for m in re.finditer(r"([a-z ]+)\s+between\s+([0-9kmb\.,]+)\s+and\s+([0-9kmb\.,]+)", q, re.I):
        field = _normalize_field(m.group(1))
        lo = _parse_number(m.group(2))
        hi = _parse_number(m.group(3))
        if field in NUM_COLS and field in res.columns:
            tmp = pd.to_numeric(res[field], errors="coerce")
            if lo is not None:
                res = res[tmp >= lo]
            if hi is not None:
                res = res[tmp <= hi]

    # Inequalities: "<field> > N", ">= N", "< N", "<= N", "over/under N", etc.
    for m in re.finditer(
        r"([a-z ]+?)\s*(>=|>|≤|<=|<|at\s+least|over|more\s+than|at\s+most|under|less\s+than)\s*([0-9kmb\.,]+)",
        q, re.I
    ):
        raw_field, op, raw_num = m.group(1), m.group(2).lower(), m.group(3)
        field = _normalize_field(raw_field)
        val = _parse_number(raw_num)
        if field in NUM_COLS and field in res.columns and val is not None:
            tmp = pd.to_numeric(res[field], errors="coerce")
            if op in (">", "over", "more than"):
                res = res[tmp > val]
            elif op in (">=", "at least"):
                res = res[tmp >= val]
            elif op in ("<", "under", "less than"):
                res = res[tmp < val]
            elif op in ("<=", "≤", "at most"):
                res = res[tmp <= val]

    # Founded before/after: "founded/established before|after YEAR"
    m = re.search(r"(founded|established)\s+(before|after)\s+([0-9]{3,4})", q, re.I)
    if m and "established" in res.columns:
        when = int(m.group(3))
        how = m.group(2).lower()
        tmp = pd.to_numeric(res["established"], errors="coerce")
        res = res[tmp < when] if how == "before" else res[tmp > when]

    # Sorting: "by <field> (asc|desc)" or "sort by <field> ..."
    m = re.search(r"(sort\s+by|by)\s+([a-z ]+?)(\s+(asc|desc))?\b", q, re.I)
    if m:
        field = _normalize_field(m.group(2))
        order = (m.group(4) or "desc").lower()
        if field and field in res.columns:
            res = res.sort_values(field, ascending=(order == "asc"), na_position="last")

    # Top/first/last N
    m_top = re.search(r"\b(top|first)\s+([0-9]+)\b", q, re.I)
    m_last = re.search(r"\b(last)\s+([0-9]+)\b", q, re.I)
    limit = None
    if m_top:
        limit = int(m_top.group(2))
    if m_last:
        limit = int(m_last.group(2))
        res = res.iloc[::-1]
    # Default cap to avoid huge dumps
    if limit is None:
        limit = 50
    res = res.head(limit)

    response = make_response(jsonify(res.to_dict(orient="records")))
    response.headers["X-Total-Count"] = str(int(res.shape[0]))
    return response


# ---------- Entrypoint ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
