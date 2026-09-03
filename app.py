import os
import time
from datetime import datetime, date, timedelta
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
# FOOTBALL-DATA.ORG CONFIG
# ==================================================

API_BASE_URL = "https://api.football-data.org/v4"

session = requests.Session()


# ==================================================
# CACHE
# ==================================================

team_cache = {}
analysis_cache = {}

# Cache API responses to protect free API limit
api_cache = {}

# Cache lifetime in seconds
CACHE_TTL = 3600


# ==================================================
# TEAM NAME ALIASES
# ==================================================

TEAM_ALIASES = {
    "barcelona": [
        "FC Barcelona",
        "Barcelona"
    ],

    "manchester city": [
        "Manchester City FC",
        "Manchester City"
    ],

    "coventry city": [
        "Coventry City FC",
        "Coventry City"
    ],

    "rb leipzig": [
        "RB Leipzig"
    ],

    "werder bremen": [
        "SV Werder Bremen",
        "Werder Bremen"
    ],

    "atlético madrid": [
        "Atlético de Madrid",
        "Atletico Madrid",
        "Atlético Madrid"
    ],

    "athletic bilbao": [
        "Athletic Club",
        "Athletic Bilbao"
    ],

    "inter miami": [
        "Inter Miami CF",
        "Inter Miami"
    ],

    "atlanta united": [
        "Atlanta United FC",
        "Atlanta United"
    ],

    "brentford": [
        "Brentford FC",
        "Brentford"
    ],

    "fulham": [
        "Fulham FC",
        "Fulham"
    ],

    "crystal palace": [
        "Crystal Palace FC",
        "Crystal Palace"
    ],

    "newcastle united": [
        "Newcastle United FC",
        "Newcastle United"
    ],

    "bournemouth": [
        "AFC Bournemouth",
        "Bournemouth"
    ],

    "valencia": [
        "Valencia CF",
        "Valencia"
    ]
}


# ==================================================
# API REQUEST
# ==================================================

def football_api(endpoint, params=None):

    api_key = os.getenv("FOOTBALL_DATA_API_KEY")

    if not api_key:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY environment variable is missing"
        )

    params = params or {}

    cache_key = (
        endpoint,
        tuple(sorted(params.items()))
    )

    # Return cached response
    if cache_key in api_cache:

        cached = api_cache[cache_key]

        if time.time() - cached["time"] < CACHE_TTL:
            print("CACHE HIT:", endpoint)
            return cached["data"]

    headers = {
        "X-Auth-Token": api_key,
        "Accept": "application/json"
    }

    try:

        response = session.get(
            f"{API_BASE_URL}{endpoint}",
            headers=headers,
            params=params,
            timeout=25
        )

        print(
            "FOOTBALL-DATA REQUEST:",
            endpoint,
            params,
            "STATUS:",
            response.status_code
        )

        if not response.ok:

            try:
                error_data = response.json()
            except Exception:
                error_data = response.text

            raise RuntimeError(
                f"Football-data API error "
                f"({response.status_code}): "
                f"{error_data}"
            )

        data = response.json()

        api_cache[cache_key] = {
            "data": data,
            "time": time.time()
        }

        return data

    except requests.RequestException as e:

        raise RuntimeError(
            f"HTTP request failed: {str(e)}"
        )


# ==================================================
# NORMALIZE TEAM NAME
# ==================================================

def normalize_name(name):

    if not name:
        return ""

    replacements = {
        "á": "a",
        "à": "a",
        "ä": "a",
        "â": "a",
        "é": "e",
        "è": "e",
        "ë": "e",
        "í": "i",
        "ï": "i",
        "ó": "o",
        "ö": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n"
    }

    value = name.lower().strip()

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = value.replace(" fc", "")
    value = value.replace(" cf", "")
    value = value.replace(" afc", "")
    value = value.replace(".", "")
    value = value.replace("-", " ")

    return " ".join(value.split())


# ==================================================
# LOAD TEAM CATALOG
# ==================================================

def get_all_teams():

    cache_key = "__ALL_TEAMS__"

    if cache_key in team_cache:
        return team_cache[cache_key]

    teams = []
    offset = 0
    limit = 100

    # We load a reasonable catalog once
    # and cache it in memory.
    for _ in range(10):

        data = football_api(
            "/teams",
            {
                "limit": limit,
                "offset": offset
            }
        )

        batch = data.get("teams", [])

        if not batch:
            break

        teams.extend(batch)

        if len(batch) < limit:
            break

        offset += limit

    team_cache[cache_key] = teams

    print(
        "TEAM CATALOG LOADED:",
        len(teams)
    )

    return teams


# ==================================================
# FIND TEAM
# ==================================================

def find_team(team_name):

    cache_key = normalize_name(team_name)

    if cache_key in team_cache:
        return team_cache[cache_key]

    aliases = TEAM_ALIASES.get(
        team_name.lower(),
        [team_name]
    )

    normalized_aliases = [
        normalize_name(x)
        for x in aliases
    ]

    teams = get_all_teams()

    # EXACT MATCH
    for team in teams:

        team_name_api = team.get("name", "")
        normalized_api = normalize_name(
            team_name_api
        )

        if normalized_api in normalized_aliases:

            result = {
                "id": team.get("id"),
                "name": team_name_api,
                "shortName": team.get(
                    "shortName",
                    team_name_api
                ),
                "crest": team.get("crest")
            }

            team_cache[cache_key] = result

            print(
                "TEAM FOUND:",
                team_name,
                "=>",
                result
            )

            return result

    # PARTIAL MATCH
    for team in teams:

        team_name_api = team.get("name", "")
        normalized_api = normalize_name(
            team_name_api
        )

        for alias in normalized_aliases:

            if (
                alias in normalized_api
                or normalized_api in alias
            ):

                result = {
                    "id": team.get("id"),
                    "name": team_name_api,
                    "shortName": team.get(
                        "shortName",
                        team_name_api
                    ),
                    "crest": team.get("crest")
                }

                team_cache[cache_key] = result

                print(
                    "PARTIAL TEAM FOUND:",
                    team_name,
                    "=>",
                    result
                )

                return result

    print("TEAM NOT FOUND:", team_name)

    return None


# ==================================================
# GET TEAM MATCHES
# ==================================================

def get_team_matches(team_id):

    today = date.today()

    # Go back roughly 18 months
    date_from = today - timedelta(days=550)

    data = football_api(
        f"/teams/{team_id}/matches",
        {
            "dateFrom": date_from.isoformat(),
            "dateTo": today.isoformat(),
            "status": "FINISHED",
            "limit": 100
        }
    )

    return data.get("matches", [])


# ==================================================
# TEAM LAST 10 GAMES
# ==================================================

def get_team_last_games(team_id, limit=10):

    matches = get_team_matches(team_id)

    matches = sorted(
        matches,
        key=lambda x: x.get(
            "utcDate",
            ""
        ),
        reverse=True
    )

    games = []

    for match in matches:

        home = match.get(
            "homeTeam",
            {}
        )

        away = match.get(
            "awayTeam",
            {}
        )

        score = match.get(
            "score",
            {}
        )

        full_time = score.get(
            "fullTime",
            {}
        )

        home_goals = full_time.get("home")
        away_goals = full_time.get("away")

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        is_home = (
            home.get("id") == team_id
        )

        if is_home:

            opponent = away.get(
                "name",
                ""
            )

            team_goals = home_goals
            opponent_goals = away_goals

        else:

            opponent = home.get(
                "name",
                ""
            )

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

            "score": (
                f"{team_goals}-{opponent_goals}"
            ),

            "date": (
                match.get(
                    "utcDate",
                    ""
                )[:10]
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

    # Get historical matches for home team
    matches = get_team_matches(
        home_team["id"]
    )

    total = 0
    home_wins = 0
    away_wins = 0
    draws = 0

    recent = []

    for match in matches:

        fixture_home = match.get(
            "homeTeam",
            {}
        )

        fixture_away = match.get(
            "awayTeam",
            {}
        )

        # Check if both teams participated
        team_ids = {
            fixture_home.get("id"),
            fixture_away.get("id")
        }

        if (
            home_team["id"] not in team_ids
            or away_team["id"] not in team_ids
        ):
            continue

        full_time = (
            match.get("score", {})
            .get("fullTime", {})
        )

        home_goals = full_time.get("home")
        away_goals = full_time.get("away")

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        total += 1

        if home_goals == away_goals:

            draws += 1

        else:

            requested_home_is_home = (
                fixture_home.get("id")
                == home_team["id"]
            )

            if requested_home_is_home:

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

            "home": fixture_home.get(
                "name"
            ),

            "away": fixture_away.get(
                "name"
            ),

            "score": (
                f"{home_goals}-{away_goals}"
            ),

            "date": (
                match.get(
                    "utcDate",
                    ""
                )[:10]
            )
        })

    recent = sorted(
        recent,
        key=lambda x: x["date"],
        reverse=True
    )

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
                or request.args.get(
                    "token"
                )
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

            "provider": "football-data.org",

            "api_key_configured": bool(
                os.getenv(
                    "FOOTBALL_DATA_API_KEY"
                )
            ),

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

        q = Match.query

        if (
            tier
            and tier != "ALL"
        ):

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

        # Cached result
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

                "error":
                    "Match not found"

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

                    "ok": False,

                    "error": (
                        f"Home team not found "
                        f"in football-data.org: "
                        f"{match.home}"
                    )

                }), 404


            if not away_team:

                return jsonify({

                    "ok": False,

                    "error": (
                        f"Away team not found "
                        f"in football-data.org: "
                        f"{match.away}"
                    )

                }), 404


            # Get forms
            home_form = (
                get_team_last_games(
                    home_team["id"]
                )
            )

            away_form = (
                get_team_last_games(
                    away_team["id"]
                )
            )


            # Get H2H
            h2h = get_head_to_head(
                home_team,
                away_team
            )


            result = {

                "ok": True,

                "match": serialize(
                    match
                ),

                "teams": {

                    "home": home_team,

                    "away": away_team
                },

                "head_to_head": h2h,

                "home_form": home_form,

                "away_form": away_form,

                "source": (
                    "football-data.org"
                ),

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


            return jsonify(
                result
            )


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

        # Clear caches
        analysis_cache.clear()
        team_cache.clear()
        api_cache.clear()

        return jsonify({

            "ok": True,

            "message":
                "Refresh complete",

            "updated":
                now.isoformat()
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
