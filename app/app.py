# app.py
import os
from datetime import timedelta
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import config
from database import init_db

DB_UNREACHABLE_MSG = "Database tidak terjangkau. Periksa koneksi internet lalu coba lagi."


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

    # Version every url_for('static', ...) with the file's mtime so browsers
    # pick up changed CSS/JS right after a deploy instead of a stale cached copy.
    @app.url_defaults
    def _static_cache_bust(endpoint, values):
        if endpoint == "static" and "v" not in values:
            try:
                values["v"] = int(os.path.getmtime(os.path.join(app.static_folder, values["filename"])))
            except (OSError, KeyError):
                pass

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

    from modules.budget.routes import bp as budget_bp
    app.register_blueprint(budget_bp)

    from modules.sahabat_etf.routes import bp as sahabat_etf_bp
    app.register_blueprint(sahabat_etf_bp)

    from modules.bank.routes import bp as bank_bp
    app.register_blueprint(bank_bp)

    from modules.sponsorship.routes import bp as sponsorship_bp
    app.register_blueprint(sponsorship_bp)

    from modules.sop.routes import bp as sop_bp
    app.register_blueprint(sop_bp)

    from modules.users.routes import bp as users_bp
    app.register_blueprint(users_bp)

    from modules.backup.routes import bp as backup_bp
    app.register_blueprint(backup_bp)
    
    from modules.general_ledger.routes import bp as gl_bp
    app.register_blueprint(gl_bp)

    from modules.management_report.routes import bp as mr_bp
    app.register_blueprint(mr_bp)

    from modules.spt_badan.routes import bp as spt_bp
    app.register_blueprint(spt_bp)

    from modules.beasiswa.api import beasiswa_api
    app.register_blueprint(beasiswa_api)

    from modules.payment_memo.api import memo_api
    app.register_blueprint(memo_api)

    from modules.coming_soon.routes import coming_soon_bp
    app.register_blueprint(coming_soon_bp)

    from format_utils import format_rupiah
    app.jinja_env.filters["rupiah"] = lambda v, with_prefix=True: format_rupiah(v, "Rp " if with_prefix else "")

    _BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]

    def tgl(value, with_time=False):
        """'2026-10-23T20:59:12' -> '23 Okt 2026' (or '23 Okt 2026, 20:59')."""
        if not value:
            return "–"
        s = str(value)
        try:
            y, m, d = int(s[0:4]), int(s[5:7]), int(s[8:10])
        except ValueError:
            return s
        out = f"{d} {_BULAN[m - 1]} {y}"
        if with_time and len(s) >= 16:
            out += f", {s[11:16]}"
        return out
    app.jinja_env.filters["tgl"] = tgl

    _ACRONYMS = {"hr", "it", "sop", "gl", "pa", "pam", "etf", "smt"}
    app.jinja_env.filters["slug_label"] = lambda s: " ".join(
        w.upper() if w in _ACRONYMS else w.capitalize() for w in str(s or "").replace("_", "-").split("-") if w)

    @app.context_processor
    def inject_nav_modules():
        from modules.dashboard.routes import (
            DASHBOARD_TABS, MODULE_SUBTABS,
            PAYMENT_MEMO_SUBTABS_SMT, PAYMENT_MEMO_SUBTABS_DEFAULT,
        )
        from flask_jwt_extended import get_jwt
        from flask import session
        try:
            get_jwt()
        except Exception:
            return {"nav_modules": []}
        # Beasiswa is ETF-only, Sponsorship is SMT-only — hide the module that
        # doesn't apply to the active company instead of showing a dead link.
        company_code = session.get("company_code")
        hidden_keys = set()
        if company_code == "ETF":
            hidden_keys.add("sponsorship")
        elif company_code == "SMT":
            hidden_keys.add("beasiswa")

        def _subtabs_for(key):
            if key == "payment_memo":
                return PAYMENT_MEMO_SUBTABS_SMT if company_code == "SMT" else PAYMENT_MEMO_SUBTABS_DEFAULT
            return MODULE_SUBTABS.get(key, [])

        nav_modules = [
            {"name": name, "url": url_for(endpoint), "key": key, "subtabs": _subtabs_for(key)}
            for name, endpoint, key in DASHBOARD_TABS
            if key not in hidden_keys
        ]
        return {"nav_modules": nav_modules}

    from fhdb.errors import OperationalError as DbUnreachable

    @app.errorhandler(DbUnreachable)
    def db_unreachable(e):
        # Database (Supabase lewat HTTPS) tidak terjangkau: 503 tanpa mengulang request.
        app.logger.warning("Database tidak terjangkau: %s", e)
        wants_json = request.path.startswith("/api") or "/api/" in request.path or request.is_json or (
            request.accept_mimetypes.best == "application/json")
        if wants_json:
            return jsonify({"error": DB_UNREACHABLE_MSG}), 503
        return render_template("db_unavailable.html", message=DB_UNREACHABLE_MSG), 503

    if config.DB_STATS_HEADER:
        import fhdb

        @app.before_request
        def _fh_db_stats_reset():
            fhdb.reset_stats()

        @app.after_request
        def _fh_db_stats_header(resp):
            resp.headers["X-FH-DB-Calls"] = str(fhdb.stats.calls)
            resp.headers["X-FH-DB-Seconds"] = f"{fhdb.stats.seconds:.3f}"
            resp.headers["X-FH-DB-Max-Call-Seconds"] = f"{fhdb.stats.max_seconds:.3f}"
            return resp

    @app.route("/")
    def index():
        return redirect(url_for("auth.login_page"))

    if not testing:
        # DB tidak terjangkau saat start (internet putus / Supabase down): jangan matikan proses;
        # tiap request yang butuh DB mendapat 503 dari db_unreachable(). Konfigurasi yang hilang
        # (SUPABASE_URL / SUPABASE_SERVICE_KEY -> ValueError) sengaja tetap gagal cepat saat start.
        try:
            init_db()
        except DbUnreachable as e:
            app.logger.warning("init_db dilewati, database tidak terjangkau saat start: %s", e)
        
        # --- Scheduler Setup ---
        # Ensure we only run scheduler in the main werkzeug process if reloading, or if debug is off
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
            try:
                from apscheduler.schedulers.background import BackgroundScheduler
                from tasks.flow_backup import run_flow_backups
                
                scheduler = BackgroundScheduler()
                
                def scheduled_backup_job():
                    with app.app_context():
                        run_flow_backups()
                        
                # Run at 17:00 on Mon-Fri
                scheduler.add_job(func=scheduled_backup_job, trigger="cron", day_of_week="mon-fri", hour=17, minute=0)

                # Backup harian isi database ke config.DB_BACKUP_ROOT (Y:), retensi 30 hari.
                # scheduled_db_backup tidak pernah melempar: DB tidak terjangkau -> warning, error lain -> log.
                from tasks.db_backup import register_db_backup_job
                register_db_backup_job(scheduler)
                scheduler.start()
                app.logger.info("APScheduler started successfully.")
            except ImportError:
                app.logger.warning("APScheduler is not installed. Background tasks will not run.")

    return app
