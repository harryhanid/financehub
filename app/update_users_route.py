import re

with open("C:/Financehub/app/modules/users/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# Change imports to use jwt_html_required instead of html_admin_required for index
if "from auth.middleware import html_admin_required, json_admin_required" in content:
    content = content.replace("from auth.middleware import html_admin_required, json_admin_required", "from auth.middleware import html_admin_required, json_admin_required, jwt_html_required, is_admin")

old_index = """@bp.route("/")
@html_admin_required
def index():
    return render_template("users/index.html", users=get_users(),
                           active_page="users", use_unified_header=True, **_ctx())"""

new_index = """@bp.route("/")
@jwt_html_required
def index():
    ctx = _ctx()
    # Check if admin
    if ctx.get("current_role") == "admin" or ctx.get("current_user") == "admin":
        return render_template("users/index.html", users=get_users(),
                               active_page="users", use_unified_header=True, **ctx)
    else:
        # Non-admin sees their profile
        return render_template("users/profile.html", active_page="users", use_unified_header=True, **ctx)"""

if "@html_admin_required\ndef index():" in content:
    content = content.replace(old_index, new_index)
    with open("C:/Financehub/app/modules/users/routes.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated users index route!")
else:
    print("Could not find old index block string!")
