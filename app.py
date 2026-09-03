import os
from datetime import datetime, date
from functools import wraps

import requests
from flask import Flask, jsonify, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc


db = SQLAlchemy()


# ==================================================
# SEED DATA
# ==================================================

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


# ==================================================
# DATABASE MODEL
# ==================================================

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


# ==================================================
# API CONFIG
# ==================================================

API_BASE_URL = "https://v3.football.api-sports.io"

session = requests.Session()


# ==================================================
# MEMORY CACHE
# ==================================================

team_cache = {}
analysis_cache = {}


# ==================================================
# API REQUEST
# ==================================================

def football_api(endpoint, params=None):

    api_key = os.getenv("API_FOOTBALL_KEY")

    if not api_key:
        raise RuntimeError(
            "API_FOOTBALL_KEY environment variable is missing"
        )

    headers = {
        "x-apisports-key": api_key,
        "Accept": "application/json"
    }

    try:

        response = session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=headers,
            params=params or {},
            timeout=20
        )

        print(
            "API REQUEST:",
            endpoint,
            params,
            "STATUS:",
            response.status_code
        )

        response.raise_for_status()

        data = response.json()

        if data.get("errors"):
            raise RuntimeError(
                f"API-Football error: {data['errors']}"
            )

        return data.get("response", [])

    except requests.RequestException as e:
        raise RuntimeError(
            f"HTTP/API request failed: {str(e)}"
        )


# ==================================================
# FIND TEAM
# ==================================================

def find_team(team_name):

    cache_key = team_name.lower().strip()

    if cache_key in team_cache:
        return team_cache[cache_key]

    teams = football_api(
        "/teams",
        {
            "search": team_name
        }
    )

    if not teams:
        print("TEAM NOT FOUND:", team_name)
        return None

    normalized = team_name.lower().strip()

    # Exact match first
    for item in teams:

        team = item.get("team", {})

        name = team.get("name", "")

        if name.lower().strip() == normalized:

            result = {
                "id": team.get("id"),
                "name": name
            }

            team_cache[cache_key] = result

            print(
                "EXACT TEAM FOUND:",
                team_name,
                result
            )

            return result

    # Fallback first result
    team = teams[0].get("team", {})

    result = {
        "id": team.get("id"),
        "name": team.get("name")
    }

    team_cache[cache_key] = result

    print(
        "FALLBACK TEAM FOUND:",
        team_name,
        result
    )

    return result


# ==================================================
# TEAM LAST GAMES
# ==================================================

def get_team_last_games(team_id, limit=10):

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

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        is_home = home.get("id") == team_id

        if is_home:

            opponent = away.get("name", "")
            team_goals = home_goals
            opponent_goals = away_goals

        else:

            opponent = home.get("name", "")
            team_goals = away_goals
            opponent_goals = home_goals

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
            "date": fixture_info.get(
                "date",
                ""
            )[:10],
            "home": is_home
        })

    return games


# ==================================================
# HEAD TO HEAD
# ==================================================

def get_head_to_head(home_team, away_team):

    fixtures = football_api(
        "/fixtures/headtohead",
        {
            "h2h": (
                f"{home_team['id']}"
                f"-{away_team['id']}"
            ),
            "last": 20,
            "status": "FT-AET-PEN"
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

        if home_goals == away_goals:

            draws += 1

        else:

            home_team_was_home = (
                fixture_home.get("id")
                == home_team["id"]
            )

            if home_team_was_home:

                if home_goals > away_goals:
                    home_wins += 1
                else:
                    away_wins += 1

            else:

                if away_goals > home_goals:
                    home_wins += 1
                else:
                    away_wins += 1

        recent.append({
            "home": fixture_home.get("name"),
            "away": fixture_away.get("name"),
            "score": f"{home_goals}-{away_goals}",
            "date": fixture_info.get(
                "date",
                ""
            )[:10]
        })

    return {
        "total": total,
        "home_wins": home_wins,
        "draws": draws,
        "away_wins": away_wins,
        "recent": recent[:5]
    }


# ==================================================
# SERIALIZER
# ==================================================

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

        "updated_at": (
            m.updated_at.isoformat()
            if m.updated_at
            else None
        )
    }


# ==================================================
# CREATE APP
# ==================================================

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

    if database_url.startswith("postgres://"):

        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    app.config[
        "SQLALCHEMY_DATABASE_URI"
    ] = database_url

    app.config[
        "SQLALCHEMY_TRACK_MODIFICATIONS"
    ] = False

    db.init_app(app)


    # ==============================================
    # DATABASE SETUP
    # ==============================================

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


    # ==============================================
    # ADMIN AUTH
    # ==============================================

    def admin_required(fn):

        @wraps(fn)
        def wrapper(*args, **kwargs):

            token = (
                request.headers.get(
                    "X-Admin-Token"
                )
                or request.args.get("token")
            )

            expected = os.getenv(
                "ADMIN_TOKEN"
            )

            if (
                not expected
                or token != expected
            ):

                return jsonify({
                    "error": "Unauthorized"
                }), 401

            return fn(*args, **kwargs)

        return wrapper


    # ==============================================
    # HOME
    # ==============================================

    @app.get("/")
    def index():

        return render_template(
            "index.html"
        )


    # ==============================================
    # HEALTH
    # ==============================================

    @app.get("/health")
    def health():

        return jsonify({
            "status": "ok",
            "service": "sure-wins",
            "api_key_configured": bool(
                os.getenv("API_FOOTBALL_KEY")
            ),
            "time": datetime.utcnow().isoformat()
        })


    # ==============================================
    # MATCH LIST
    # ==============================================

    @app.get("/api/matches")
    def matches():

        tier = request.args.get("tier")

        q = Match.query

        if tier and tier != "ALL":

            q = q.filter_by(
                tier=tier
            )

        rows = q.order_by(
            desc(Match.confidence),
            Match.id
        ).all()

        return jsonify({
            "matches": [
                serialize(x)
                for x in rows
            ],
            "updated": (
                datetime.utcnow()
                .isoformat()
            )
        })


    # ==============================================
    # MATCH DETAIL
    # ==============================================

    @app.get(
        "/api/matches/<int:match_id>"
    )
    def match_detail(match_id):

        match = db.session.get(
            Match,
            match_id
        )

        if not match:
            abort(404)

        return jsonify(
            serialize(match)
        )


    # ==============================================
    # REAL MATCH ANALYSIS
    # ==============================================

    @app.get(
        "/api/matches/"
        "<int:match_id>/analysis"
    )
    def match_analysis(match_id):

        # Return cached analysis
        if match_id in analysis_cache:

            print(
                "RETURNING CACHED ANALYSIS:",
                match_id
            )

            return jsonify(
                analysis_cache[match_id]
            )


        match = db.session.get(
            Match,
            match_id
        )

        if not match:

            return jsonify({
                "error": "Match not found"
            }), 404


        try:

            print(
                "ANALYZING:",
                match.home,
                "VS",
                match.away
            )


            # Find teams
            home_team = find_team(
                match.home
            )

            away_team = find_team(
                match.away
            )


            if not home_team:

                return jsonify({
                    "error": (
                        f"Home team not found: "
                        f"{match.home}"
                    )
                }), 404


            if not away_team:

                return jsonify({
                    "error": (
                        f"Away team not found: "
                        f"{match.away}"
                    )
                }), 404


            # Get forms
            home_form = get_team_last_games(
                home_team["id"]
            )

            away_form = get_team_last_games(
                away_team["id"]
            )


            # Get H2H
            h2h = get_head_to_head(
                home_team,
                away_team
            )


            result = {

                "ok": True,

                "match": serialize(match),

                "teams": {
                    "home": home_team,
                    "away": away_team
                },

                "head_to_head": h2h,

                "home_form": home_form,

                "away_form": away_form,

                "source": "API-Football",

                "updated": (
                    datetime.utcnow()
                    .isoformat()
                )
            }


            # Cache successful result
            analysis_cache[
                match_id
            ] = result


            print(
                "ANALYSIS SUCCESS:",
                match_id
            )


            return jsonify(result)


        except Exception as error:

            print(
                "ANALYSIS ERROR:",
                repr(error)
            )

            return jsonify({

                "ok": False,

                "error": str(error),

                "match_id": match_id,

                "home": match.home,

                "away": match.away

            }), 500


    # ==============================================
    # ADMIN REFRESH
    # ==============================================

    @app.post(
        "/api/admin/refresh"
    )
    @admin_required
    def refresh():

        now = datetime.utcnow()

        Match.query.update({
            Match.updated_at: now
        })

        db.session.commit()

        # Clear analysis cache
        analysis_cache.clear()

        return jsonify({
            "ok": True,
            "message": "Refresh complete",
            "updated": now.isoformat()
        })


    return app


# ==================================================
# APP ENTRY
# ==================================================

app = create_app()


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                5000
            )
        )
    )
