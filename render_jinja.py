from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("app/templates"))
template = env.get_template("payment_memo/index.html")
# We just render it without variables, they will default to empty
try:
    html = template.render()
    with open("rendered.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved rendered.html via Jinja directly")
except Exception as e:
    print("Error:", e)
