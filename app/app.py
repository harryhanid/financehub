# app.py
from datetime import timedelta
from flask import Flask, redirect, url_for
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import config
from database import init_db

def create_app(testing=False):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"]            = config.JWT_SECRET
    app.config["JWT_ACCESS_TOKEN_EXPIRES"]  = timedelta(hours=config.JWT_ACCESS_HOURS)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=config.JWT_REFRESH_DAYS)
    app.config["JWT_TOKEN_LOCATION"]        = ["headers", "cookies"]
    app.config["JWT_COOKIE_SECURE"]         = False
    app.config["JWT_COOKIE_CSRF_PROTECT"]   = False
    app.config["JWT_ACCESS_COOKIE_NAME"]    = "fh_access"
    app.config["JWT_REFRESH_COOKIE_NAME"]   = "fh_refresh"
    app.config["SECRET_KEY"]               = config.FLASK_SECRET
    app.config["TESTING"]                  = testing

    JWTManager(app)
    CORS(app, supports_credentials=True)

    from auth.routes import bp as auth_bp
    from modules.dashboard.routes import bp as dashboard_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp)

    from modules.beasiswa.routes import bp as beasiswa_bp
    app.register_blueprint(beasiswa_bp)

    from modules.payment_memo.routes import bp as memo_bp
    app.register_blueprint(memo_bp)

    from modules.payment_application.routes import bp as payapp_bp
    app.register_blueprint(payapp_bp)

    from modules.etf_payment_application.routes import bp as etf_pa_bp
    app.register_blueprint(etf_pa_bp)

    from modules.users.routes import bp as users_bp
    app.register_blueprint(users_bp)

    from modules.beasiswa.api import beasiswa_api
    app.register_blueprint(beasiswa_api)

    from modules.payment_memo.api import memo_api
    app.register_blueprint(memo_api)

    from modules.coming_soon.routes import coming_soon_bp
    app.register_blueprint(coming_soon_bp)

    @app.route("/")
    def index():
        return redirect(url_for("auth.login_page"))

    if not testing:
        init_db()
    return app
