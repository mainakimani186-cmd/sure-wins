import os
from datetime import datetime, date
from functools import wraps

import requests
from flask import Flask, jsonify, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc

db = SQLAlchemy()

# --------------------------------------------------
# DEMO / INITIAL MATCH PICKS
# --------------------------------------------------

SEED = [
    ("Barcelona", "Valencia", 86, "Very High", "Global"),
    ("Manchester City", "Coventry City", 84, "Very High", "Global"),
    ("RB Leipzig", "Werder Bremen", 78, "High", "Europe"),
    ("Inter Miami", "Atlanta United", 76, "High", "North America"),
    ("Atlético Madrid", "Athletic Bilbao", 72, "High", "Europe"),
    ("Tai Po FC", "HK Rangers", 70, "High", "Asia"),
    ("Philadelphia Union", "CF Montréal", 69, "High", "North America"),
    ("Vancouver Whitecaps", "St. Louis City", 67, "High", "North America"),
    ("FC Cincinnati", "DC United", 64, "Good", "North America"),
    ("Fluminense", "Vasco da Gama", 63, "Good", "South America"),
    ("Coritiba", "Mirassol", 61, "Good", "South America"),
    ("Flamengo", "Remo", 60, "Good", "South America"),
    ("Palmeiras", "Botafogo", 59, "Good", "South America"),
    ("Club América", "Tijuana", 57, "Moderate", "North America"),
    ("Tigres UANL", "Necaxa", 56, "Moderate", "North America"),
    ("Brentford", "Sunderland", 55, "Moderate", "Europe"),
    ("Fulham", "Crystal Palace", 54, "Moderate", "Europe"),
    ("Newcastle United", "Bournemouth", 53, "Moderate", "Europe"),
    ("Anderlecht", "Genk", 52, "Moderate", "Europe"),
    ("Swansea City", "Wrexham", 51, "Moderate", "Europe")
]


# --------------------------------------------------
# DATABASE MODEL
# --------------------------------------------------

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    home = db.Column(db.String(120), nullable=False)
    away = db.Column(db.String(120), nullable=False)

    confidence = db.Column(db.Integer, nullable=False)
    tier = db.Column(db.String(30), nullable=False)
    region = db.Column(db.String(60))

    match_date = db.Column(db.Date)
    analysis = db.Column(db.Text)

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# --------------------------------------------------
# API FOOTBALL CONFIGURATION
# --------------------------------------------------

API_BASE_URL = "https://v3.football.api-sports.io"


def football_api(endpoint, params=None):
    """
    Makes a secure request to API-Football.
    API key stays on the server and is never sent
    to the browser.
    """

    api_key = os.getenv("API_FOOTBALL_KEY")

    if not api_key:
        raise Exception("API_FOOTBALL_KEY is not configured")

    headers = {
        "x-apisports-key": api_key
    }

    response = requests.get(
        f"{API_BASE_URL}{endpoint}",
        headers=headers,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    # API-Football sometimes returns useful errors here
    if data.get("errors"):
        raise Exception(str(data["errors"]))

    return data.get("response", [])


# --------------------------------------------------
# FIND TEAM ID
# --------------------------------------------------

def find_team(team_name):
    """
    Searches API-Football for a team and returns
    its ID and official name.
    """

    teams = football_api(
        "/teams",
        {"search": team_name}
    )

    if not teams:
        return None

    # Prefer exact name match
    normalized = team_name.lower().strip()

    for item in teams:
        team = item.get("team", {})

        if team.get("name", "").lower() == normalized:
            return {
                "id": team.get("id"),
                "name": team.get("name")
            }

    # Otherwise use first search result
    team = teams[0].get("team", {})

    return {
        "id": team.get("id"),
        "name": team.get("name")
    }


# --------------------------------------------------
# FORMAT LAST MATCHES
# --------------------------------------------------

def get_team_last_games(team_id, team_name, limit=10):
    """
    Gets the team's last completed matches.
    """

    fixtures = football_api(
        "/fixtures",
        {
            "team": team_id,
            "last": limit,
            "status": "FT-AET-PEN"
        }
    )

    games = []

    for fixture in fixtures:

        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        fixture_info = fixture.get("fixture", {})

        home = teams.get("home", {})
        away = teams.get("away", {})

        home_name = home.get("name", "")
        away_name = away.get("name", "")

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        is_home = home.get("id") == team_id

        opponent = away_name if is_home else home_name

        team_goals = home_goals if is_home else away_goals
        opponent_goals = away_goals if is_home else home_goals

        if team_goals is None or opponent_goals is None:
            continue

        if team_goals > opponent_goals:
            result = "W"
        elif team_goals < opponent_goals:
            result = "L"
        else:
            result = "D"

        games.append({
            "result": result,
            "opponent": opponent,
            "score": f"{team_goals}-{opponent_goals}",
            "date": fixture_info.get("date", "")[:10],
            "home": is_home
        })

    return games


# --------------------------------------------------
# HEAD TO HEAD
# --------------------------------------------------

def get_head_to_head(home_team, away_team):
    """
    Gets historical meetings between two teams.
    """

    fixtures = football_api(
        "/fixtures/headtohead",
        {
            "h2h": f"{home_team['id']}-{away_team['id']}",
            "last": 50
        }
    )

    total = 0
    home_wins = 0
    away_wins = 0
    draws = 0

    recent = []

    for fixture in fixtures:

        teams = fixture.get("teams", {})
        goals = fixture.get("goals", {})
        fixture_info = fixture.get("fixture", {})

        fixture_home = teams.get("home", {})
        fixture_away = teams.get("away", {})

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        total += 1

        # Determine winner based on the actual teams,
        # regardless of who was home in that historical fixture

        if home_goals == away_goals:
            draws += 1

        elif fixture_home.get("id") == home_team["id"]:
            if home_goals > away_goals:
                home_wins += 1
            else:
                away_wins += 1

        elif fixture_away.get("id") == home_team["id"]:
            if away_goals > home_goals:
                home_wins += 1
            else:
                away_wins += 1

        recent.append({
            "home": fixture_home.get("name"),
            "away": fixture_away.get("name"),
            "score": f"{home_goals}-{away_goals}",
            "date": fixture_info.get("date", "")[:10]
        })

    return {
        "total": total,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "recent": recent[:5]
    }


# --------------------------------------------------
# CREATE APP
# --------------------------------------------------

def create_app():

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "change-me-in-production"
    )

    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite:///surewins.db"
    )

    # Render/Postgres compatibility
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)


    # ----------------------------------------------
    # INITIAL DATABASE SETUP
    # ----------------------------------------------

    with app.app_context():

        db.create_all()

        if Match.query.count() == 0:

            now = datetime.utcnow()

            for h, a, p, t, r in SEED:

                db.session.add(
                    Match(
                        home=h,
                        away=a,
                        confidence=p,
                        tier=t,
                        region=r,
                        match_date=date.today(),
                        analysis=(
                            f"{h} is currently ranked as "
                            f"a {t.lower()} consensus pick."
                        ),
                        updated_at=now
                    )
                )

            db.session.commit()


    # ----------------------------------------------
    # ADMIN AUTH
    # ----------------------------------------------

    def admin_required(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):

            token = (
                request.headers.get("X-Admin-Token")
                or request.args.get("token")
            )

            expected = os.getenv("ADMIN_TOKEN")

            if not expected or token != expected:
                return jsonify(
                    {"error": "Unauthorized"}
                ), 401

            return fn(*args, **kwargs)

        return wrapper


    # ----------------------------------------------
    # PAGES
    # ----------------------------------------------

    @app.get("/")
    def index():
        return render_template("index.html")


    # ----------------------------------------------
    # HEALTH CHECK
    # ----------------------------------------------

    @app.get("/health")
    def health():

        return jsonify({
            "status": "ok",
            "service": "sure-wins",
            "time": datetime.utcnow().isoformat()
        })


    # ----------------------------------------------
    # MATCH LIST
    # ----------------------------------------------

    @app.get("/api/matches")
    def matches():

        tier = request.args.get("tier")

        q = Match.query

        if tier and tier != "ALL":
            q = q.filter_by(tier=tier)

        rows = q.order_by(
            desc(Match.confidence),
            Match.id
        ).all()

        return jsonify({
            "matches": [serialize(x) for x in rows],
            "updated": datetime.utcnow().isoformat()
        })


    # ----------------------------------------------
    # SINGLE MATCH
    # ----------------------------------------------

    @app.get("/api/matches/<int:match_id>")
    def match_detail(match_id):

        m = db.session.get(Match, match_id)

        if not m:
            abort(404)

        return jsonify(serialize(m))


    # ----------------------------------------------
    # REAL MATCH ANALYSIS
    # ----------------------------------------------

    @app.get("/api/matches/<int:match_id>/analysis")
    def match_analysis(match_id):

        match = db.session.get(Match, match_id)

        if not match:
            return jsonify({
                "error": "Match not found"
            }), 404

        try:

            # Find real API team IDs
            home_team = find_team(match.home)
            away_team = find_team(match.away)

            if not home_team or not away_team:
                return jsonify({
                    "error": "Could not find one or both teams",
                    "home": match.home,
                    "away": match.away
                }), 404


            # Get real data
            home_form = get_team_last_games(
                home_team["id"],
                home_team["name"]
            )

            away_form = get_team_last_games(
                away_team["id"],
                away_team["name"]
            )

            h2h = get_head_to_head(
                home_team,
                away_team
            )


            return jsonify({

                "match": serialize(match),

                "teams": {
                    "home": home_team,
                    "away": away_team
                },

                "head_to_head": h2h,

                "home_form": home_form,

                "away_form": away_form,

                "source": "API-Football",

                "updated": datetime.utcnow().isoformat()
            })


        except requests.RequestException as error:

            return jsonify({
                "error": "Football data provider unavailable",
                "details": str(error)
            }), 502

        except Exception as error:

            return jsonify({
                "error": "Analysis unavailable",
                "details": str(error)
            }), 500


    # ----------------------------------------------
    # ADMIN REFRESH
    # ----------------------------------------------

    @app.post("/api/admin/refresh")
    @admin_required
    def refresh():

        now = datetime.utcnow()

        Match.query.update({
            Match.updated_at: now
        })

        db.session.commit()

        return jsonify({
            "ok": True,
            "message": (
                "Refresh hook executed."
            ),
            "updated": now.isoformat()
        })


    return app


# --------------------------------------------------
# SERIALIZER
# --------------------------------------------------

def serialize(m):

    return {
        "id": m.id,
        "home": m.home,
        "away": m.away,
        "confidence": m.confidence,
        "tier": m.tier,
        "region": m.region,

        "match_date": (
            m.match_date.isoformat()
            if m.match_date
            else None
        ),

        "analysis": m.analysis,

        "updated_at": m.updated_at.isoformat()
    }


# --------------------------------------------------
# APP ENTRY
# --------------------------------------------------

app = create_app()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
