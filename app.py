import os
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

    api_key = os.getenv(
        "API_FOOTBALL_KEY"
    )

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
            params or {},
            "STATUS:",
            response.status_code
        )

        response.raise_for_status()

        data = response.json()

        errors = data.get(
            "errors",
            {}
        )

        if errors:

            raise RuntimeError(
                f"API-Football error: {errors}"
            )

        return data.get(
            "response",
            []
        )

    except requests.Timeout:

        raise RuntimeError(
            "API request timed out"
        )

    except requests.RequestException as error:

        raise RuntimeError(
            f"HTTP/API request failed: {str(error)}"
        )

    except ValueError:

        raise RuntimeError(
            "API returned invalid JSON"
        )


# ==================================================
# TEAM NAME ALIASES
# ==================================================

TEAM_ALIASES = {

    "barcelona": "Barcelona",
    "manchester city": "Manchester City",
    "rb leipzig": "RB Leipzig",
    "inter miami": "Inter Miami",
    "atlético madrid": "Atletico Madrid",
    "athletic bilbao": "Athletic Club",
    "werder bremen": "Werder Bremen",
    "st. louis city": "St. Louis City",
    "cf montréal": "Montreal",
    "club américa": "America",
    "tigres uanl": "Tigres",
    "dc united": "DC United"
}


# ==================================================
# NORMALIZE TEAM NAME
# ==================================================

def normalize_team_name(name):

    name = name.lower().strip()

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
        "ü": "u",
        ".": "",
        "-": " ",
        "  ": " "
    }

    for old, new in replacements.items():

        name = name.replace(
            old,
            new
        )

    return name.strip()


# ==================================================
# FIND TEAM
# ==================================================

def find_team(team_name):

    cache_key = normalize_team_name(
        team_name
    )

    if cache_key in team_cache:

        print(
            "TEAM CACHE HIT:",
            team_name
        )

        return team_cache[cache_key]


    search_name = TEAM_ALIASES.get(
        team_name.lower(),
        team_name
    )


    teams = football_api(
        "/teams",
        {
            "search": search_name
        }
    )


    if not teams:

        print(
            "TEAM NOT FOUND:",
            team_name
        )

        return None


    normalized_target = normalize_team_name(
        team_name
    )


    # ----------------------------------------------
    # EXACT MATCH
    # ----------------------------------------------

    for item in teams:

        team = item.get(
            "team",
            {}
        )

        api_name = team.get(
            "name",
            ""
        )

        if (
            normalize_team_name(api_name)
            == normalized_target
        ):

            result = {
                "id": team.get("id"),
                "name": api_name,
                "logo": team.get("logo")
            }

            team_cache[
                cache_key
            ] = result

            print(
                "EXACT TEAM FOUND:",
                team_name,
                result
            )

            return result


    # ----------------------------------------------
    # PARTIAL MATCH
    # ----------------------------------------------

    for item in teams:

        team = item.get(
            "team",
            {}
        )

        api_name = team.get(
            "name",
            ""
        )

        normalized_api = normalize_team_name(
            api_name
        )

        if (
            normalized_target in normalized_api
            or normalized_api in normalized_target
        ):

            result = {
                "id": team.get("id"),
                "name": api_name,
                "logo": team.get("logo")
            }

            team_cache[
                cache_key
            ] = result

            print(
                "PARTIAL TEAM FOUND:",
                team_name,
                result
            )

            return result


    # ----------------------------------------------
    # FALLBACK
    # ----------------------------------------------

    team = teams[0].get(
        "team",
        {}
    )

    result = {
        "id": team.get("id"),
        "name": team.get("name"),
        "logo": team.get("logo")
    }

    team_cache[
        cache_key
    ] = result

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

        teams = fixture.get(
            "teams",
            {}
        )

        goals = fixture.get(
            "goals",
            {}
        )

        fixture_info = fixture.get(
            "fixture",
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


        home_goals = goals.get(
            "home"
        )

        away_goals = goals.get(
            "away"
        )


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
                fixture_info.get(
                    "date",
                    ""
                )[:10]
            ),

            "home": is_home

        })


    return games


# ==================================================
# FORM STATISTICS
# ==================================================

def calculate_form_stats(games):

    wins = sum(
        1
        for game in games
        if game["result"] == "W"
    )

    draws = sum(
        1
        for game in games
        if game["result"] == "D"
    )

    losses = sum(
        1
        for game in games
        if game["result"] == "L"
    )

    total = len(games)

    points = (
        wins * 3
        + draws
    )

    possible_points = total * 3

    percentage = 0

    if possible_points > 0:

        percentage = round(
            (
                points / possible_points
            ) * 100
        )


    return {

        "wins": wins,

        "draws": draws,

        "losses": losses,

        "total": total,

        "points": points,

        "percentage": percentage

    }


# ==================================================
# HEAD TO HEAD
# ==================================================

def get_head_to_head(
    home_team,
    away_team
):

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

        teams = fixture.get(
            "teams",
            {}
        )

        goals = fixture.get(
            "goals",
            {}
        )

        fixture_info = fixture.get(
            "fixture",
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


        home_goals = goals.get(
            "home"
        )

        away_goals = goals.get(
            "away"
        )


        if (
            home_goals is None
            or away_goals is None
        ):

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
                fixture_info.get(
                    "date",
                    ""
                )[:10]
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
# DYNAMIC PREDICTION INSIGHT
# ==================================================

def generate_prediction_insight(

    home_name,
    away_name,

    home_form,
    away_form,

    h2h,

    confidence

):

    home_stats = calculate_form_stats(
        home_form
    )

    away_stats = calculate_form_stats(
        away_form
    )


    insights = []


    # ----------------------------------------------
    # HOME TEAM FORM
    # ----------------------------------------------

    if home_stats["total"] > 0:

        if home_stats["wins"] >= 7:

            insights.append(
                f"{home_name} enters this matchup in "
                f"excellent form, winning "
                f"{home_stats['wins']} of their last "
                f"{home_stats['total']} matches."
            )

        elif home_stats["wins"] >= 5:

            insights.append(
                f"{home_name} has shown solid recent form "
                f"with {home_stats['wins']} wins from their "
                f"last {home_stats['total']} matches."
            )

        elif home_stats["losses"] >= 6:

            insights.append(
                f"{home_name} has struggled recently, "
                f"losing {home_stats['losses']} of their "
                f"last {home_stats['total']} matches."
            )


    # ----------------------------------------------
    # AWAY TEAM FORM
    # ----------------------------------------------

    if away_stats["total"] > 0:

        if away_stats["wins"] >= 7:

            insights.append(
                f"{away_name} also arrives in excellent "
                f"form with {away_stats['wins']} wins in "
                f"{away_stats['total']} recent matches."
            )

        elif away_stats["losses"] >= 6:

            insights.append(
                f"{away_name} has struggled for consistency, "
                f"recording {away_stats['losses']} defeats "
                f"in their last {away_stats['total']} games."
            )


    # ----------------------------------------------
    # COMPARE FORM
    # ----------------------------------------------

    if (
        home_stats["total"] > 0
        and away_stats["total"] > 0
    ):

        difference = (
            home_stats["points"]
            - away_stats["points"]
        )


        if difference >= 6:

            insights.append(
                f"Overall recent momentum strongly favors "
                f"{home_name}."
            )

        elif difference <= -6:

            insights.append(
                f"Recent momentum favors {away_name}, "
                f"who have collected more points over "
                f"their recent matches."
            )

        else:

            insights.append(
                "Recent form between both teams is "
                "relatively competitive."
            )


    # ----------------------------------------------
    # HEAD TO HEAD
    # ----------------------------------------------

    if h2h["total"] >= 2:

        if (
            h2h["home_wins"]
            > h2h["away_wins"]
        ):

            insights.append(
                f"{home_name} also holds the stronger "
                f"recent head-to-head record, winning "
                f"{h2h['home_wins']} of "
                f"{h2h['total']} meetings."
            )


        elif (
            h2h["away_wins"]
            > h2h["home_wins"]
        ):

            insights.append(
                f"{away_name} has the stronger recent "
                f"head-to-head record, winning "
                f"{h2h['away_wins']} of "
                f"{h2h['total']} meetings."
            )


        else:

            insights.append(
                "Recent head-to-head meetings have been "
                "closely balanced."
            )


    # ----------------------------------------------
    # FALLBACK
    # ----------------------------------------------

    if not insights:

        insights.append(
            f"Available recent data suggests a competitive "
            f"match between {home_name} and {away_name}."
        )


    # ----------------------------------------------
    # FINAL RESULT
    # ----------------------------------------------

    return {

        "text": " ".join(
            insights[:3]
        ),

        "home_form": home_stats,

        "away_form": away_stats,

        "confidence": confidence

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
# CREATE APPLICATION
# ==================================================

def create_app():

    app = Flask(__name__)


    # ==============================================
    # CONFIG
    # ==============================================

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


            for (
                home,
                away,
                confidence,
                tier,
                region
            ) in SEED:


                db.session.add(

                    Match(

                        home=home,

                        away=away,

                        confidence=confidence,

                        tier=tier,

                        region=region,

                        match_date=date.today(),

                        analysis=(
                            "Live match analysis will be "
                            "generated from recent form "
                            "and head-to-head data."
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

            "api_key_configured": bool(
                os.getenv(
                    "API_FOOTBALL_KEY"
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


        query = Match.query


        if (
            tier
            and tier != "ALL"
        ):

            query = query.filter_by(
                tier=tier
            )


        rows = query.order_by(

            desc(
                Match.confidence
            ),

            Match.id

        ).all()


        return jsonify({

            "matches": [

                serialize(row)

                for row in rows

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
    # LIVE MATCH ANALYSIS
    # ==============================================

    @app.get(
        "/api/matches/"
        "<int:match_id>/analysis"
    )
    def match_analysis(match_id):


        # ------------------------------------------
        # RETURN CACHE
        # ------------------------------------------

        if match_id in analysis_cache:

            print(
                "RETURNING CACHED ANALYSIS:",
                match_id
            )


            return jsonify(
                analysis_cache[match_id]
            )


        # ------------------------------------------
        # GET MATCH
        # ------------------------------------------

        match = db.session.get(
            Match,
            match_id
        )


        if not match:

            return jsonify({

                "ok": False,

                "error": "Match not found"

            }), 404


        try:


            print(
                "================================"
            )

            print(
                "ANALYZING MATCH:",
                match.home,
                "VS",
                match.away
            )

            print(
                "================================"
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

                return jsonify({

                    "ok": False,

                    "error": (
                        f"Home team not found: "
                        f"{match.home}"
                    )

                }), 404


            if not away_team:

                return jsonify({

                    "ok": False,

                    "error": (
                        f"Away team not found: "
                        f"{match.away}"
                    )

                }), 404


            # --------------------------------------
            # GET RECENT FORM
            # --------------------------------------

            home_form = get_team_last_games(
                home_team["id"],
                10
            )


            away_form = get_team_last_games(
                away_team["id"],
                10
            )


            # --------------------------------------
            # GET HEAD TO HEAD
            # --------------------------------------

            h2h = get_head_to_head(

                home_team,

                away_team

            )


            # --------------------------------------
            # GENERATE DYNAMIC INSIGHT
            # --------------------------------------

            prediction_insight = (
                generate_prediction_insight(

                    match.home,

                    match.away,

                    home_form,

                    away_form,

                    h2h,

                    match.confidence

                )
            )


            # --------------------------------------
            # BUILD RESPONSE
            # --------------------------------------

            result = {

                "ok": True,


                "match": serialize(
                    match
                ),


                "teams": {

                    "home": home_team,

                    "away": away_team

                },


                "prediction_insight": (
                    prediction_insight
                ),


                "head_to_head": h2h,


                "home_form": home_form,


                "away_form": away_form,


                "source": (
                    "API-Football"
                ),


                "updated": (

                    datetime.utcnow()
                    .isoformat()

                )

            }


            # --------------------------------------
            # CACHE RESULT
            # --------------------------------------

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


        return jsonify({

            "ok": True,

            "message": (
                "Refresh complete. "
                "Analysis cache cleared."
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
