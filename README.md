# 🎓 Arnav & Charlotte's University API

🚀 **Creating our first API using Flask**

This project is a simple API built with Flask, using data from the **Top 200 Universities in North America** dataset. It lets users access and filter university data, with helpful routes for schema, health, and even natural-language queries.

---

## 📌 Features

- Clean **REST endpoints** to list universities or fetch one by ID
- **Filtering** by country and name (contains), plus numeric ranges (established year, staff, students, tuition, library volumes, endowment)
- **Sorting & pagination** (`sort_by`, `order`, `limit`, `offset`)
- **Natural-language query** endpoint (`/nlq`) with simple patterns (e.g., “founded before 1900”, “endowment > 5b”, “top 10 by students”)
- **Schema** and **health** endpoints
- Returns `X-Total-Count` header for list responses

---

## 📂 Dataset

We are using the dataset from **Kaggle**:

🔗 **[Top 200 Universities in North America](https://www.kaggle.com/datasets/puzanov/top-200-universities-in-north-america)**
