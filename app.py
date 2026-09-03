import os
import time
from datetime import datetime, date
from functools import wraps

import requests
from flask import Flask, jsonify, render_template, request, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc


# ==================================================
# DATABASE
# ==================================================

db = SQLAlchemy()


# ==================================================
# DEMO / INITIAL PICKS
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
    ("Swansea City", "Wrexham", 51, "Moderate", "Europe"),
]


# ==================================================
# TEAM NAME ALIASES
# ==================================================

TEAM_ALIASES = {
    "RB Leipzig": "RB Leipzig",
    "Inter Miami": "Inter Miami",
    "CF Montréal": "Montreal",
    "DC United": "DC United",
    "Club América": "America",
    "Tigres UANL": "Tigres",
    "Tai Po FC": "Tai Po",
    "HK Rangers": "Hong Kong Rangers",
    "St. Louis City": "St. Louis City",
}


# ==================================================
# DATABASE MODEL
# ==================================================

class Match(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    home = db.Column(
        db.String(120),
        nullable=False
    )

    away = db.Column(
        db.String(120),
        nullable=False
    )

    confidence = db.Column(
        db.Integer,
        nullable=False
    )

    tier = db.Column(
        db.String(30),
        nullable=False
    )

    region = db.Column(
        db.String(60)
    )

    match_date = db.Column(
        db.Date
    )

    analysis = db.Column(
        db.Text
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# ==================================================
# API CONFIGURATION
# ==================================================

API_BASE_URL = "https://v3.football.api-sports.io"

API_TIMEOUT = 20

# Cache API results for 10 minutes
CACHE_SECONDS = 600

analysis_cache = {}


# ==================================================
# API HELPER
# ==================================================

def football_api(endpoint, params=None):
    """
    Safe API-Football request helper.
    """

    api_key = os.getenv("API_FOOTBALL_KEY")

    if not api_key:
        raise RuntimeError(
            "API_FOOTBALL_KEY is not configured"
        )

    headers = {
        "x-apisports-key": api_key
    }

    url = f"{API_BASE_URL}{endpoint}"

    try:

        print(
            f"[API] REQUEST {endpoint} "
            f"PARAMS={params}"
        )

        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=API_TIMEOUT
        )

        print(
            f"[API] STATUS {response.status_code}"
        )

        # HTTP errors
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError:
            raise RuntimeError(
                "API returned invalid JSON"
            )

        api_errors = data.get("errors")

        if api_errors:

            print(
                f"[API] ERRORS {api_errors}"
            )

            raise RuntimeError(
                f"API-Football error: {api_errors}"
            )

        results = data.get("response", [])

        print(
            f"[API] SUCCESS "
            f"RESULTS={len(results)}"
        )

        return results

    except requests.Timeout:

        raise RuntimeError(
            "API request timed out"
        )

    except requests.RequestException as error:

        print(
            f"[API] REQUEST FAILED: {repr(error)}"
        )

        raise RuntimeError(
            f"API request failed: {str(error)}"
        )


# ==================================================
# TEAM NAME NORMALIZATION
# ==================================================

def normalize_name(name):

    if not name:
        return ""

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    value = name.lower().strip()

    for old, new in replacements.items():
        value = value.replace(old, new)

    remove_words = [
        " fc",
        " cf",
        " afc",
        " sc",
        ".",
        "'",
        "-"
    ]

    for word in remove_words:
        value = value.replace(word, "")

    return " ".join(value.split())


# ==================================================
# FIND TEAM
# ==================================================

def find_team(team_name):
    """
    Find the best matching team from API-Football.
    """

    search_name = TEAM_ALIASES.get(
        team_name,
        team_name
    )

    print(
        f"[TEAM] Searching: "
        f"{team_name} -> {search_name}"
    )

    teams = football_api(
        "/teams",
        {
            "search": search_name
        }
    )

    if not teams:

        print(
            f"[TEAM] No results: {team_name}"
        )

        return None

    wanted = normalize_name(search_name)

    # Exact normalized match
    for item in teams:

        team = item.get("team", {})

        api_name = team.get("name", "")

        if normalize_name(api_name) == wanted:

            print(
                f"[TEAM] Exact match: "
                f"{api_name} "
                f"ID={team.get('id')}"
            )

            return {
                "id": team.get("id"),
                "name": api_name
            }

    # Partial match
    for item in teams:

        team = item.get("team", {})

        api_name = team.get("name", "")

        normalized_api = normalize_name(api_name)

        if (
            wanted in normalized_api
            or normalized_api in wanted
        ):

            print(
                f"[TEAM] Partial match: "
                f"{api_name} "
                f"ID={team.get('id')}"
            )

            return {
                "id": team.get("id"),
                "name": api_name
            }

    # Log alternatives
    available = []

    for item in teams[:5]:

        team = item.get("team", {})

        available.append(
            {
                "id": team.get("id"),
                "name": team.get("name")
            }
        )

    print(
        f"[TEAM] No exact match. "
        f"Available: {available}"
    )

    # Last fallback
    first = teams[0].get("team", {})

    if not first.get("id"):
        return None

    return {
        "id": first.get("id"),
        "name": first.get("name")
    }


# ==================================================
# GET TEAM LAST GAMES
# ==================================================

def get_team_last_games(
    team_id,
    limit=10
):
    """
    Get recent completed games.
    """

    # Request more than needed because some
    # recent fixtures may not be finished.
    fixtures = football_api(
        "/fixtures",
        {
            "team": team_id,
            "last": 20
        }
    )

    games = []

    completed_statuses = [
        "FT",
        "AET",
        "PEN"
    ]

    for fixture in fixtures:

        fixture_info = fixture.get(
            "fixture",
            {}
        )

        status = fixture_info.get(
            "status",
            {}
        ).get("short")

        # Ignore unfinished matches
        if status not in completed_statuses:
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

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        is_home = (
            home.get("id") == team_id
        )

        opponent = (
            away.get("name")
            if is_home
            else home.get("name")
        )

        team_goals = (
            home_goals
            if is_home
            else away_goals
        )

        opponent_goals = (
            away_goals
            if is_home
            else home_goals
        )

        if team_goals > opponent_goals:
            result = "W"

        elif team_goals < opponent_goals:
            result = "L"

        else:
            result = "D"

        games.append({
            "result": result,
            "opponent": opponent,
            "score": (
                f"{team_goals}-{opponent_goals}"
            ),
            "date": (
                fixture_info
                .get("date", "")[:10]
            ),
            "home": is_home
        })

        if len(games) >= limit:
            break

    return games


# ==================================================
# HEAD TO HEAD
# ==================================================

def get_head_to_head(
    home_team,
    away_team
):
    """
    Calculate head-to-head statistics.
    """

    fixtures = football_api(
        "/fixtures/headtohead",
        {
            "h2h": (
                f"{home_team['id']}"
                f"-{away_team['id']}"
            ),
            "last": 50
        }
    )

    total = 0
    home_wins = 0
    away_wins = 0
    draws = 0

    recent = []

    completed_statuses = [
        "FT",
        "AET",
        "PEN"
    ]

    for fixture in fixtures:

        fixture_info = fixture.get(
            "fixture",
            {}
        )

        status = fixture_info.get(
            "status",
            {}
        ).get("short")

        if status not in completed_statuses:
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

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        total += 1

        fixture_home_id = (
            fixture_home.get("id")
        )

        fixture_away_id = (
            fixture_away.get("id")
        )

        # Draw
        if home_goals == away_goals:

            draws += 1

        # Original home team won
        elif (
            fixture_home_id
            == home_team["id"]
        ):

            if home_goals > away_goals:
                home_wins += 1
            else:
                away_wins += 1

        # Original away team won
        elif (
            fixture_away_id
            == home_team["id"]
        ):

            if away_goals > home_goals:
                home_wins += 1
            else:
                away_wins += 1

        recent.append({
            "home": fixture_home.get("name"),
            "away": fixture_away.get("name"),
            "score": (
                f"{home_goals}-{away_goals}"
            ),
            "date": (
                fixture_info
                .get("date", "")[:10]
            )
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

def serialize(match):

    return {
        "id": match.id,
        "home": match.home,
        "away": match.away,
        "confidence": match.confidence,
        "tier": match.tier,
        "region": match.region,

        "match_date": (
            match.match_date.isoformat()
            if match.match_date
            else None
        ),

        "analysis": match.analysis,

        "updated_at": (
            match.updated_at.isoformat()
            if match.updated_at
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

    # Render PostgreSQL compatibility
    if database_url.startswith(
        "postgres://"
    ):
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
    # DATABASE INITIALIZATION
    # ==============================================

    with app.app_context():

        db.create_all()

        if Match.query.count() == 0:

            now = datetime.utcnow()

            for (
                home,
                away,
                confidence,
                tier,
                region
            ) in SEED:

                match = Match(

                    home=home,
                    away=away,

                    confidence=confidence,
                    tier=tier,
                    region=region,

                    match_date=date.today(),

                    analysis=(
                        f"{home} is currently ranked "
                        f"as a {tier.lower()} "
                        f"consensus pick."
                    ),

                    updated_at=now
                )

                db.session.add(match)

            db.session.commit()

            print(
                "[DATABASE] Seeded initial matches"
            )


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

            return fn(
                *args,
                **kwargs
            )

        return wrapper


    # ==============================================
    # HOME PAGE
    # ==============================================

    @app.get("/")
    def index():

        return render_template(
            "index.html"
        )


    # ==============================================
    # HEALTH CHECK
    # ==============================================

    @app.get("/health")
    def health():

        return jsonify({
            "status": "ok",
            "service": "sure-wins",
            "time": (
                datetime.utcnow()
                .isoformat()
            )
        })


    # ==============================================
    # MATCH LIST
    # ==============================================

    @app.get("/api/matches")
    def matches():

        tier = request.args.get(
            "tier"
        )

        query = Match.query

        if tier and tier != "ALL":

            query = query.filter_by(
                tier=tier
            )

        rows = (
            query
            .order_by(
                desc(Match.confidence),
                Match.id
            )
            .all()
        )

        return jsonify({

            "matches": [
                serialize(match)
                for match in rows
            ],

            "updated": (
                datetime.utcnow()
                .isoformat()
            )
        })


    # ==============================================
    # SINGLE MATCH
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
    # MATCH ANALYSIS
    # ==============================================

    @app.get(
        "/api/matches/"
        "<int:match_id>/analysis"
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


        # ------------------------------------------
        # CACHE CHECK
        # ------------------------------------------

        cached = analysis_cache.get(
            match_id
        )

        if cached:

            age = (
                time.time()
                - cached["timestamp"]
            )

            if age < CACHE_SECONDS:

                print(
                    f"[CACHE] Hit for "
                    f"match {match_id}"
                )

                return jsonify(
                    cached["data"]
                )


        try:

            print(
                f"\n========== ANALYSIS =========="
            )

            print(
                f"MATCH: "
                f"{match.home} vs {match.away}"
            )


            # --------------------------------------
            # FIND TEAMS
            # --------------------------------------

            home_team = find_team(
                match.home
            )

            away_team = find_team(
                match.away
            )

            if not home_team:

                raise RuntimeError(
                    f"Could not find home team: "
                    f"{match.home}"
                )

            if not away_team:

                raise RuntimeError(
                    f"Could not find away team: "
                    f"{match.away}"
                )


            # --------------------------------------
            # GET TEAM FORMS
            # --------------------------------------

            try:

                home_form = (
                    get_team_last_games(
                        home_team["id"]
                    )
                )

            except Exception as error:

                print(
                    f"[WARNING] Home form failed: "
                    f"{error}"
                )

                home_form = []


            try:

                away_form = (
                    get_team_last_games(
                        away_team["id"]
                    )
                )

            except Exception as error:

                print(
                    f"[WARNING] Away form failed: "
                    f"{error}"
                )

                away_form = []


            # --------------------------------------
            # GET HEAD TO HEAD
            # --------------------------------------

            try:

                h2h = get_head_to_head(
                    home_team,
                    away_team
                )

            except Exception as error:

                print(
                    f"[WARNING] H2H failed: "
                    f"{error}"
                )

                h2h = {
                    "total": 0,
                    "home_wins": 0,
                    "draws": 0,
                    "away_wins": 0,
                    "recent": []
                }


            # --------------------------------------
            # BUILD RESPONSE
            # --------------------------------------

            result = {

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


            # --------------------------------------
            # SAVE CACHE
            # --------------------------------------

            analysis_cache[match_id] = {

                "timestamp": time.time(),

                "data": result
            }


            print(
                "[ANALYSIS] SUCCESS"
            )

            print(
                "==============================\n"
            )


            return jsonify(result)


        except Exception as error:

            print(
                "[ANALYSIS ERROR]",
                repr(error)
            )

            return jsonify({

                "error": (
                    "Analysis unavailable"
                ),

                "details": str(error),

                "match": {
                    "home": match.home,
                    "away": match.away
                }

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

            "message": (
                "Refresh completed and "
                "analysis cache cleared."
            ),

            "updated": now.isoformat()
        })


    return app


# ==================================================
# APPLICATION ENTRY
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
