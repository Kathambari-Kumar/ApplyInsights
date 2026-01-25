from flask import Flask, render_template, redirect, url_for, request, Response
from email_fetcher import fetch_applied_jobs, save_to_db
import mysql.connector
from config import DB_CONFIG
import matplotlib.pyplot as plt
from io import BytesIO

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/extract")
def extract():
    data = fetch_applied_jobs()   # fetch from Gmail
    save_to_db(data)              # insert (duplicates ignored)
    return redirect(url_for("index"))

@app.route("/filter")
def filter_by_month():
    month = request.args.get("month", type=int)

    if month is None or month == 0:
        return render_template("index.html", alert="Please select a month.")

    # Step 1: fetch & update DB
    data = fetch_applied_jobs()
    save_to_db(data)

    # Step 2: filter results
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM applications
        WHERE MONTH(applied_date) = %s
        ORDER BY applied_date DESC
    """, (month,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if rows:
        return render_template("index.html", applications=rows)
    else:
        return render_template("index.html", alert="No jobs found for this month.")

def get_city_counts(month):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    ALL_CITIES = ["Stockholm", "Gothenburg", "Malmo", "Finspång", "Remote", "Unknown"]
    # Start with all cities = 0
    city_counts = {city: 0 for city in ALL_CITIES}

    query = """
        SELECT city 
        FROM applications
        WHERE MONTH(applied_date) = %s
    """
    cursor.execute(query, (month,))
    rows = cursor.fetchall()

    conn.close()
    # Update counts
    for row in rows:
        city = row["city"] if row["city"] else "Unknown"
        if city in city_counts:
            city_counts[city] += 1
        else:
            city_counts["Unknown"] += 1
    #cities = [row["city"] if row["city"] else "unknown" for row in rows]
    return city_counts

@app.route("/city_chart")
def city_chart():
    month = request.args.get("month", type=int)
    if month is None:
        print("no month")
        return render_template("index.html", alert="No month selected.")

    city_counts = get_city_counts(month)
    print(city_counts)

    if not city_counts or sum(city_counts.values()) == 0:
        return render_template("index.html", alert="No jobs found for this month.")

    # Create chart
    plt.figure(figsize=(6, 4))
    plt.bar(city_counts.keys(), city_counts.values(), color="skyblue")
    plt.title(f"Job Applications per City (Month {month})")
    plt.xlabel("City")
    plt.ylabel("Applications")
    plt.xticks(rotation=30)
    plt.tight_layout()

    # Convert to PNG
    img = BytesIO()
    plt.savefig(img, format="png")
    img.seek(0)
    plt.close()

    return Response(img.getvalue(), mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)