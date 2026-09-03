import os
import logging
from datetime import datetime, date
from functools import wraps

import requests
from flask import Flask, jsonify, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc


# --------------------------------------------------
# SETUP
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)

db = SQLAlchemy()

API_BASE_URL = "https://v3.football.api-sports.io"

TEAM_CACHE = {}
ANALYSIS_CACHE = {}


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
# TEAM NAME ALIASES
# --------------------------------------------------

TEAM_ALIASES = {
    "Barcelona": "Barcelona",
    "Manchester City": "Manchester City",
    "RB Leipzig": "RB Leipzig",
    "Inter Miami": "Inter Miami",
    "Atlético Madrid": "Atletico Madrid",
    "Athletic Bilbao": "Athletic Club",
    "Philadelphia Union": "Philadelphia Union",
    "CF Montréal": "Montreal",
    "Vancouver Whitecaps": "Vancouver Whitecaps",
    "St. Louis City": "St. Louis City",
    "FC Cincinnati": "FC Cincinnati",
    "DC United": "DC United",
    "Club América": "America",
    "Tigres UANL": "Tigres",
}


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
# API FOOTBALL REQUEST
# --------------------------------------------------

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

    url = f"{API_BASE_URL}{endpoint}"

    logging.info(
        "API request: %s params=%s",
        endpoint,
        params
    )

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=20
        )

    except requests.RequestException as e:

        logging.exception("API connection error")

        raise RuntimeError(
            f"Could not connect to API-Football: {str(e)}"
        )


    logging.info(
        "API response status: %s",
        response.status_code
    )


    try:
        data = response.json()

    except ValueError:

        logging.error(
            "Invalid JSON from API: %s",
            response.text[:500]
        )

        raise RuntimeError(
            f"API returned invalid JSON (HTTP {response.status_code})"
        )


    if response.status_code != 200:

        logging.error(
            "API HTTP error: %s",
            data
        )

        raise RuntimeError(
            f"API HTTP {response.status_code}: "
            f"{data.get('message') or data.get('errors') or data}"
        )


    errors = data.get("errors")

    if errors:

        logging.error(
            "API-Football errors: %s",
            errors
        )

        raise RuntimeError(
            f"API-Football error: {errors}"
        )


    result = data.get("response")

    if result is None:
        result = []

    logging.info(
        "API returned %s results",
        len(result) if isinstance(result, list) else "unknown"
    )

    return result


# --------------------------------------------------
# FIND TEAM
# --------------------------------------------------

def find_team(team_name):

    if team_name in TEAM_CACHE:
        return TEAM_CACHE[team_name]


    search_name = TEAM_ALIASES.get(
        team_name,
        team_name
    )


    teams = football_api(
        "/teams",
        {
            "search": search_name
        }
    )


    if not teams:

        logging.warning(
            "No team found for: %s",
            team_name
        )

        return None


    normalized_original = team_name.lower().strip()
    normalized_search = search_name.lower().strip()


    # Exact match priority
    for item in teams:

        team = item.get("team", {})

        api_name = team.get(
            "name",
            ""
        ).lower().strip()

        if api_name == normalized_original:

            result = {
                "id": team.get("id"),
                "name": team.get("name"),
                "logo": team.get("logo")
            }

            TEAM_CACHE[team_name] = result

            return result


        if api_name == normalized_search:

            result = {
                "id": team.get("id"),
                "name": team.get("name"),
                "logo": team.get("logo")
            }

            TEAM_CACHE[team_name] = result

            return result


    # First result fallback
    team = teams[0].get("team", {})

    result = {
        "id": team.get("id"),
        "name": team.get("name"),
        "logo": team.get("logo")
    }

    TEAM_CACHE[team_name] = result

    return result


# --------------------------------------------------
# GET TEAM LAST GAMES
# --------------------------------------------------

def get_team_last_games(team_id, limit=10):

    fixtures = football_api(
        "/fixtures",
        {
            "team": team_id,
            "last": limit
        }
    )


    games = []


    for fixture in fixtures:

        fixture_info = fixture.get(
            "fixture",
            {}
        )

        status = fixture_info.get(
            "status",
            {}
        ).get("short")


        # Only completed games
        if status not in ["FT", "AET", "PEN"]:
            continue


        teams = fixture.get(
            "teams",
            {}
        )

        goals = fixture.get(
            "goals",
            {}
        )


        home = teams.get(
            "home",
            {}
        )

        away = teams.get(
            "away",
            {}
        )


        home_goals = goals.get("home")
        away_goals = goals.get("away")


        if home_goals is None or away_goals is None:
            continue


        is_home = home.get("id") == team_id


        if is_home:

            team_goals = home_goals
            opponent_goals = away_goals
            opponent = away.get("name")

        else:

            team_goals = away_goals
            opponent_goals = home_goals
            opponent = home.get("name")


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


        if len(games) >= limit:
            break


    return games


# --------------------------------------------------
# HEAD TO HEAD
# --------------------------------------------------

def get_head_to_head(home_team, away_team):

    fixtures = football_api(
        "/fixtures/headtohead",
        {
            "h2h":
                f"{home_team['id']}-{away_team['id']}",
            "last": 20
        }
    )


    total = 0
    home_wins = 0
    away_wins = 0
    draws = 0

    recent = []


    for fixture in fixtures:

        fixture_info = fixture.get(
            "fixture",
            {}
        )

        status = fixture_info.get(
            "status",
            {}
        ).get("short")


        if status not in ["FT", "AET", "PEN"]:
            continue


        teams = fixture.get(
            "teams",
            {}
        )

        goals = fixture.get(
            "goals",
            {}
        )


        fixture_home = teams.get(
            "home",
            {}
        )

        fixture_away = teams.get(
            "away",
            {}
        )


        home_goals = goals.get("home")
        away_goals = goals.get("away")


        if home_goals is None or away_goals is None:
            continue


        total += 1


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

        "match_date":
            m.match_date.isoformat()
            if m.match_date
            else None,

        "analysis": m.analysis,

        "updated_at":
            m.updated_at.isoformat()
            if m.updated_at
            else None
    }


# --------------------------------------------------
# CREATE APP
# --------------------------------------------------

def create_app():

    app = Flask(__name__)


    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY",
        "change-me"
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


    # ------------------------------------------
    # DATABASE SETUP
    # ------------------------------------------

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


    # ------------------------------------------
    # ADMIN AUTH
    # ------------------------------------------

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


            if not expected or token != expected:

                return jsonify({
                    "error": "Unauthorized"
                }), 401


            return fn(*args, **kwargs)


        return wrapper


    # ------------------------------------------
    # HOME
    # ------------------------------------------

    @app.get("/")
    def index():

        return render_template(
            "index.html"
        )


    # ------------------------------------------
    # HEALTH
    # ------------------------------------------

    @app.get("/health")
    def health():

        return jsonify({
            "status": "ok",
            "api_key_configured":
                bool(os.getenv(
                    "API_FOOTBALL_KEY"
                )),
            "time":
                datetime.utcnow().isoformat()
        })


    # ------------------------------------------
    # MATCHES
    # ------------------------------------------

    @app.get("/api/matches")
    def matches():

        tier = request.args.get("tier")

        query = Match.query


        if tier and tier != "ALL":

            query = query.filter_by(
                tier=tier
            )


        rows = query.order_by(
            desc(Match.confidence),
            Match.id
        ).all()


        return jsonify({

            "matches":
                [serialize(x) for x in rows],

            "updated":
                datetime.utcnow().isoformat()

        })


    # ------------------------------------------
    # SINGLE MATCH
    # ------------------------------------------

    @app.get("/api/matches/<int:match_id>")
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


    # ------------------------------------------
    # MATCH ANALYSIS
    # ------------------------------------------

    @app.get(
        "/api/matches/<int:match_id>/analysis"
    )
    def match_analysis(match_id):

        match = db.session.get(
            Match,
            match_id
        )


        if not match:

            return jsonify({
                "error": "Match not found"
            }), 404


        # Return cached analysis
        if match_id in ANALYSIS_CACHE:

            logging.info(
                "Returning cached analysis for %s",
                match_id
            )

            return jsonify(
                ANALYSIS_CACHE[match_id]
            )


        try:

            logging.info(
                "Starting analysis: %s vs %s",
                match.home,
                match.away
            )


            # TEAM LOOKUP

            home_team = find_team(
                match.home
            )

            away_team = find_team(
                match.away
            )


            if not home_team:

                return jsonify({
                    "error":
                        f"Could not find team: {match.home}"
                }), 404


            if not away_team:

                return jsonify({
                    "error":
                        f"Could not find team: {match.away}"
                }), 404


            # Each section is isolated so one
            # failed API call doesn't destroy
            # the entire analysis

            try:

                home_form = get_team_last_games(
                    home_team["id"]
                )

            except Exception as e:

                logging.exception(
                    "Home form failed"
                )

                home_form = []


            try:

                away_form = get_team_last_games(
                    away_team["id"]
                )

            except Exception as e:

                logging.exception(
                    "Away form failed"
                )

                away_form = []


            try:

                h2h = get_head_to_head(
                    home_team,
                    away_team
                )

            except Exception as e:

                logging.exception(
                    "H2H failed"
                )

                h2h = {
                    "total": 0,
                    "home_wins": 0,
                    "draws": 0,
                    "away_wins": 0,
                    "recent": []
                }


            result = {

                "match":
                    serialize(match),

                "teams": {
                    "home": home_team,
                    "away": away_team
                },

                "head_to_head":
                    h2h,

                "home_form":
                    home_form,

                "away_form":
                    away_form,

                "source":
                    "API-Football",

                "updated":
                    datetime.utcnow().isoformat()

            }


            ANALYSIS_CACHE[
                match_id
            ] = result


            logging.info(
                "Analysis successful: %s",
                match_id
            )


            return jsonify(result)


        except Exception as error:

            logging.exception(
                "ANALYSIS FAILED"
            )


            return jsonify({

                "error":
                    "Analysis unavailable",

                "details":
                    str(error),

                "match":
                    f"{match.home} vs {match.away}"

            }), 500


    # ------------------------------------------
    # ADMIN REFRESH
    # ------------------------------------------

    @app.post("/api/admin/refresh")
    @admin_required
    def refresh():

        now = datetime.utcnow()


        Match.query.update({
            Match.updated_at: now
        })


        db.session.commit()


        # Clear caches

        TEAM_CACHE.clear()
        ANALYSIS_CACHE.clear()


        return jsonify({

            "ok": True,

            "message":
                "Cache cleared and refresh completed.",

            "updated":
                now.isoformat()

        })


    return app


# --------------------------------------------------
# APP
# --------------------------------------------------

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
