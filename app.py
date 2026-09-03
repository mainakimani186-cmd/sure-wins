import os
from datetime import datetime, date
from functools import wraps
from flask import Flask, jsonify, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc

db = SQLAlchemy()

SEED = [
("Barcelona","Valencia",86,"Very High","Global"),("Manchester City","Coventry City",84,"Very High","Global"),
("RB Leipzig","Werder Bremen",78,"High","Europe"),("Inter Miami","Atlanta United",76,"High","North America"),
("Atlético Madrid","Athletic Bilbao",72,"High","Europe"),("Tai Po FC","HK Rangers",70,"High","Asia"),
("Philadelphia Union","CF Montréal",69,"High","North America"),("Vancouver Whitecaps","St. Louis City",67,"High","North America"),
("FC Cincinnati","DC United",64,"Good","North America"),("Fluminense","Vasco da Gama",63,"Good","South America"),
("Coritiba","Mirassol",61,"Good","South America"),("Flamengo","Remo",60,"Good","South America"),
("Palmeiras","Botafogo",59,"Good","South America"),("Club América","Tijuana",57,"Moderate","North America"),
("Tigres UANL","Necaxa",56,"Moderate","North America"),("Brentford","Sunderland",55,"Moderate","Europe"),
("Fulham","Crystal Palace",54,"Moderate","Europe"),("Newcastle United","Bournemouth",53,"Moderate","Europe"),
("Anderlecht","Genk",52,"Moderate","Europe"),("Swansea City","Wrexham",51,"Moderate","Europe")
]

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    home = db.Column(db.String(120), nullable=False)
    away = db.Column(db.String(120), nullable=False)
    confidence = db.Column(db.Integer, nullable=False)
    tier = db.Column(db.String(30), nullable=False)
    region = db.Column(db.String(60))
    match_date = db.Column(db.Date)
    analysis = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
    database_url = os.getenv("DATABASE_URL", "sqlite:///surewins.db")
    # Render/Postgres may use postgres:// while SQLAlchemy expects postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        if Match.query.count() == 0:
            now = datetime.utcnow()
            for h,a,p,t,r in SEED:
                db.session.add(Match(home=h,away=a,confidence=p,tier=t,region=r,
                    match_date=date.today(),analysis=f"{h} is currently ranked as a {t.lower()} consensus pick.",
                    updated_at=now))
            db.session.commit()

    def admin_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.headers.get("X-Admin-Token") or request.args.get("token")
            expected = os.getenv("ADMIN_TOKEN")
            if not expected or token != expected:
                return jsonify({"error":"Unauthorized"}), 401
            return fn(*args, **kwargs)
        return wrapper

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status":"ok","service":"sure-wins","time":datetime.utcnow().isoformat()})

    @app.get("/api/matches")
    def matches():
        tier = request.args.get("tier")
        q = Match.query
        if tier and tier != "ALL":
            q = q.filter_by(tier=tier)
        rows = q.order_by(desc(Match.confidence), Match.id).all()
        return jsonify({"matches":[serialize(x) for x in rows],"updated":datetime.utcnow().isoformat()})

    @app.get("/api/matches/<int:match_id>")
    def match_detail(match_id):
        m = db.session.get(Match, match_id)
        if not m: abort(404)
        return jsonify(serialize(m))

    @app.post("/api/admin/refresh")
    @admin_required
    def refresh():
        # Production integration point:
        # Fetch fixtures/prediction data from a licensed provider,
        # calculate consensus, then UPSERT Match rows.
        now = datetime.utcnow()
        Match.query.update({Match.updated_at: now})
        db.session.commit()
        return jsonify({"ok":True,"message":"Refresh hook executed. Connect your data provider here.","updated":now.isoformat()})

    return app

def serialize(m):
    return {
        "id":m.id,"home":m.home,"away":m.away,"confidence":m.confidence,
        "tier":m.tier,"region":m.region,"match_date":m.match_date.isoformat() if m.match_date else None,
        "analysis":m.analysis,"updated_at":m.updated_at.isoformat()
    }

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
