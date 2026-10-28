from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader("app/templates"))
env.globals["url_for"] = lambda endpoint, **kwargs: "/"
env.globals["get_flashed_messages"] = lambda **kwargs: []
template = env.get_template("payment_memo/index.html")
try:
    html = template.render(session={"role":"superadmin","username":"admin"})
    with open("rendered.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved rendered.html via Jinja directly")
except Exception as e:
    print("Error:", e)
