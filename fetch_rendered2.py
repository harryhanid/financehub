from flask import Flask, render_template
import os

app = Flask(__name__, template_folder="app/templates")

@app.route("/")
def index():
    return render_template("payment_memo/index.html")

with app.app_context():
    try:
        html = render_template("payment_memo/index.html")
        with open("rendered.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Rendered HTML saved")
    except Exception as e:
        print("Error:", e)
