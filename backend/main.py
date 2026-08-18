import os

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import psycopg

from psycopg.rows import dict_row

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from openpyxl import load_workbook
from pydantic import BaseModel


# =========================
# FastAPI
# =========================

app = FastAPI()


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 파일 경로
# =========================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

FRONTEND_DIR = PROJECT_DIR / "frontend"

EXCEL_PATH = BASE_DIR / "data" / "matches.xlsx"
RESULTS_PATH = BASE_DIR / "data" / "results.xlsx"
PLAYER_RANKINGS_PATH = BASE_DIR / "data" / "player_rankings.xlsx"
PLAYOFFS_PATH = BASE_DIR / "data" / "playoffs.xlsx"

# =========================
# NEXON Open API
# =========================

NEXON_API_KEY = os.getenv(
    "NEXON_API_KEY"
)

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

NEXON_API_BASE_URL = (
    "https://open.api.nexon.com/fconline/v1"
)

# =========================
# FC Online 선수 메타데이터
# =========================

SPID_METADATA_CACHE = None


def get_spid_metadata():

    global SPID_METADATA_CACHE


    if SPID_METADATA_CACHE is not None:
        return SPID_METADATA_CACHE


    url = (
        "https://open.api.nexon.com/"
        "static/fconline/meta/spid.json"
    )


    response = httpx.get(
        url,
        timeout=20.0,
    )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail="선수 메타데이터 조회 실패",
        )


    SPID_METADATA_CACHE = {
        player["id"]: player["name"]
        for player in response.json()
    }


    return SPID_METADATA_CACHE


def get_player_name(
    sp_id,
    spid_metadata,
):

    return spid_metadata.get(
        sp_id,
        f"알 수 없는 선수 ({sp_id})",
    )


def get_player_image_url(sp_id):

    return (
        "https://fco.dn.nexoncdn.co.kr/"
        "live/externalAssets/common/"
        f"playersAction/p{sp_id}.png"
    )


# =========================
# PostgreSQL
# =========================

def parse_kst_datetime(value):

    if isinstance(value, datetime):
        parsed = value

    else:
        parsed = datetime.fromisoformat(value)


    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=ZoneInfo("Asia/Seoul")
        )


    return parsed.astimezone(
        ZoneInfo("Asia/Seoul")
    )

def get_participant_ouid(
    participant_id,
    fc_nickname,
    saved_ouid,
):

    if saved_ouid:
        return saved_ouid


    ouid = get_ouid_by_nickname(
        fc_nickname
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE participants

                SET
                    ouid = %s,
                    updated_at = NOW()

                WHERE id = %s
                """,
                (
                    ouid,
                    participant_id,
                ),
            )


        connection.commit()


    return ouid


def get_db_connection():

    if not DATABASE_URL:

        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL이 설정되지 않았습니다.",
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )

def save_series_player_stats(
    series_id,
    team_a_id,
    nickname_a,
    team_b_id,
    nickname_b,
    player_stats,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            for player in player_stats:

                # =========================
                # FC 닉네임 -> 참가자 ID
                # =========================

                if (
                    player["nickname"]
                    == nickname_a
                ):

                    participant_id = (
                        team_a_id
                    )

                elif (
                    player["nickname"]
                    == nickname_b
                ):

                    participant_id = (
                        team_b_id
                    )

                else:

                    continue


                cursor.execute(
                    """
                    INSERT INTO series_player_stats (
                        series_id,
                        participant_id,

                        sp_id,
                        player_name,

                        sets_played,

                        rating_total,
                        average_rating,

                        goals,
                        assists,

                        image_url
                    )

                    VALUES (
                        %s,
                        %s,

                        %s,
                        %s,

                        %s,

                        %s,
                        %s,

                        %s,
                        %s,

                        %s
                    )

                    ON CONFLICT (
                        series_id,
                        participant_id,
                        player_name
                    )

                    DO UPDATE SET
                        sp_id =
                            EXCLUDED.sp_id,

                        sets_played =
                            EXCLUDED.sets_played,

                        rating_total =
                            EXCLUDED.rating_total,

                        average_rating =
                            EXCLUDED.average_rating,

                        goals =
                            EXCLUDED.goals,

                        assists =
                            EXCLUDED.assists,

                        image_url =
                            EXCLUDED.image_url,

                        updated_at =
                            NOW()
                    """,
                    (
                        series_id,
                        participant_id,

                        player["sp_id"],
                        player["player_name"],

                        player["sets_played"],

                        player["rating_total"],
                        player["average_rating"],

                        player["goals"],
                        player["assists"],

                        player["image_url"],
                    ),
                )


        connection.commit()

def save_series_mvp(
    series_id,
    participant_id,
    mvp,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO series_mvp (
                    series_id,
                    participant_id,

                    sp_id,
                    player_name,

                    sets_played,

                    rating_total,
                    average_rating,

                    goals,
                    assists,

                    image_url
                )

                VALUES (
                    %s,
                    %s,

                    %s,
                    %s,

                    %s,

                    %s,
                    %s,

                    %s,
                    %s,

                    %s
                )

                ON CONFLICT (
                    series_id
                )

                DO UPDATE SET

                    participant_id =
                        EXCLUDED.participant_id,

                    sp_id =
                        EXCLUDED.sp_id,

                    player_name =
                        EXCLUDED.player_name,

                    sets_played =
                        EXCLUDED.sets_played,

                    rating_total =
                        EXCLUDED.rating_total,

                    average_rating =
                        EXCLUDED.average_rating,

                    goals =
                        EXCLUDED.goals,

                    assists =
                        EXCLUDED.assists,

                    image_url =
                        EXCLUDED.image_url
                """,
                (
                    series_id,
                    participant_id,

                    mvp["sp_id"],
                    mvp["player_name"],

                    mvp["sets_played"],

                    mvp["rating_total"],
                    mvp["average_rating"],

                    mvp["goals"],
                    mvp["assists"],

                    mvp["image_url"],
                ),
            )


        connection.commit()

def initialize_database():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:


            # =========================
            # 참가자
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS participants (
                    id BIGSERIAL PRIMARY KEY,

                    fcl_name VARCHAR(50)
                        NOT NULL
                        UNIQUE,

                    fc_nickname VARCHAR(100)
                        UNIQUE,

                    ouid VARCHAR(100)
                        UNIQUE,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
                """
            )


            # =========================
            # SERIES
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series (
                    id BIGSERIAL PRIMARY KEY,

                    series_type VARCHAR(20)
                        NOT NULL,

                    team_a_id BIGINT
                        NOT NULL
                        REFERENCES participants(id),

                    team_b_id BIGINT
                        NOT NULL
                        REFERENCES participants(id),

                    match_type INTEGER
                        NOT NULL
                        DEFAULT 40,

                    scheduled_date DATE,

                    round_number INTEGER,

                    started_at TIMESTAMPTZ
                        NOT NULL,

                    completed_at TIMESTAMPTZ,

                    status VARCHAR(20)
                        NOT NULL
                        DEFAULT 'active',

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CHECK (
                        team_a_id <> team_b_id
                    ),

                    CHECK (
                        series_type IN (
                            '프리시즌',
                            '정규리그'
                        )
                    ),

                    CHECK (
                        status IN (
                            'scheduled',
                            'active',
                            'completed',
                            'cancelled'
                        )
                    )
                )
                """
            )


            # =========================
            # SERIES 세트
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series_sets (
                    id BIGSERIAL PRIMARY KEY,

                    series_id BIGINT
                        NOT NULL
                        REFERENCES series(id)
                        ON DELETE CASCADE,

                    set_number INTEGER
                        NOT NULL,

                    nexon_match_id VARCHAR(100)
                        NOT NULL
                        UNIQUE,

                    played_at TIMESTAMPTZ
                        NOT NULL,

                    team_a_score INTEGER
                        NOT NULL,

                    team_b_score INTEGER
                        NOT NULL,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    UNIQUE (
                        series_id,
                        set_number
                    ),

                    CHECK (
                        set_number
                        BETWEEN 1 AND 3
                    ),

                    CHECK (
                        team_a_score >= 0
                    ),

                    CHECK (
                        team_b_score >= 0
                    )
                )
                """
            )


            # =========================
            # SERIES MVP
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series_mvp (
                    series_id BIGINT
                        PRIMARY KEY
                        REFERENCES series(id)
                        ON DELETE CASCADE,

                    participant_id BIGINT
                        NOT NULL
                        REFERENCES participants(id),

                    sp_id BIGINT
                        NOT NULL,

                    player_name VARCHAR(100)
                        NOT NULL,

                    sets_played INTEGER
                        NOT NULL,

                    rating_total NUMERIC(6, 2)
                        NOT NULL,

                    average_rating NUMERIC(5, 2)
                        NOT NULL,

                    goals INTEGER
                        NOT NULL,

                    assists INTEGER
                        NOT NULL,

                    image_url TEXT,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
                """
            )

                        # =========================
            # SERIES 선수 기록
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series_player_stats (
                    id BIGSERIAL PRIMARY KEY,

                    series_id BIGINT
                        NOT NULL
                        REFERENCES series(id)
                        ON DELETE CASCADE,

                    participant_id BIGINT
                        NOT NULL
                        REFERENCES participants(id),

                    sp_id BIGINT
                        NOT NULL,

                    player_name VARCHAR(100)
                        NOT NULL,

                    sets_played INTEGER
                        NOT NULL,

                    rating_total NUMERIC(6, 2)
                        NOT NULL,

                    average_rating NUMERIC(5, 2)
                        NOT NULL,

                    goals INTEGER
                        NOT NULL,

                    assists INTEGER
                        NOT NULL,

                    image_url TEXT,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    UNIQUE (
                        series_id,
                        participant_id,
                        player_name
                    )
                )
                """
            )


        connection.commit()


    seed_participants()

def seed_participants():

    participant_data = [
        (
            "문권기",
            "공기",
        ),
        (
            "이준석",
            "똭똭",
        ),
        (
            "주은성",
            "펜쉬차일드",
        ),
        (
            "이상",
            "지수사",
        ),
        (
            "서종원",
            "붉은심장베컴",
        ),
    ]


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            for (
                fcl_name,
                fc_nickname,
            ) in participant_data:

                cursor.execute(
                    """
                    INSERT INTO participants (
                        fcl_name,
                        fc_nickname
                    )

                    VALUES (
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        fcl_name
                    )

                    DO UPDATE SET

                        fc_nickname =
                            COALESCE(
                                EXCLUDED.fc_nickname,
                                participants.fc_nickname
                            ),

                        updated_at = NOW()
                    """,
                    (
                        fcl_name,
                        fc_nickname,
                    ),
                )


        connection.commit()

def get_nexon_headers():

    if not NEXON_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="NEXON_API_KEY가 설정되지 않았습니다.",
        )

    return {
        "x-nxopen-api-key": NEXON_API_KEY,
    }

def get_ouid_by_nickname(nickname):

    response = httpx.get(
        f"{NEXON_API_BASE_URL}/id",
        headers=get_nexon_headers(),
        params={
            "nickname": nickname,
        },
        timeout=10.0,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()["ouid"]


def get_user_match_ids(
    ouid,
    match_type,
    limit=50,
):

    response = httpx.get(
        f"{NEXON_API_BASE_URL}/user/match",
        headers=get_nexon_headers(),
        params={
            "ouid": ouid,
            "matchtype": match_type,
            "offset": 0,
            "limit": limit,
        },
        timeout=10.0,
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()

def get_match_detail(
    match_id,
):

    response = httpx.get(
        f"{NEXON_API_BASE_URL}/match-detail",
        headers=get_nexon_headers(),
        params={
            "matchid": match_id,
        },
        timeout=10.0,
    )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


    return response.json()

# =========================
# FCL SERIES MVP 계산
# =========================

def calculate_series_mvp_from_matches(
    matches,
):

    spid_metadata = get_spid_metadata()

    player_totals = {}


    for match_data in matches:

        for match_info in match_data["matchInfo"]:

            nickname = match_info["nickname"]


            fcl_name = next(
                (
                    name
                    for name, fc_nickname
                    in FCONLINE_NICKNAMES.items()
                    if fc_nickname == nickname
                ),
                nickname,
            )


            for player in match_info["player"]:

                status = player["status"]

                rating = float(
                    status["spRating"]
                )


                # 출전하지 않은 선수 제외
                if rating <= 0:
                    continue


                sp_id = player["spId"]

                player_name = get_player_name(
                    sp_id,
                    spid_metadata,
                )


                # 같은 실제 선수는 시즌 카드가 달라도
                # 한 선수로 합산
                player_key = (
                    nickname,
                    player_name,
                )


                if player_key not in player_totals:

                    player_totals[player_key] = {
                        "nickname": nickname,
                        "fcl_name": fcl_name,

                        "player_name": player_name,
                        "sp_id": sp_id,

                        "sets_played": 0,

                        "rating_total": 0,
                        "ratings": [],

                        "goals": 0,
                        "assists": 0,

                        "best_single_rating":
                            rating,
                    }


                record = player_totals[
                    player_key
                ]


                # 다른 시즌 카드를 사용했다면
                # 가장 높은 평점을 받은 카드 이미지 사용
                if (
                    rating
                    >
                    record[
                        "best_single_rating"
                    ]
                ):

                    record[
                        "best_single_rating"
                    ] = rating

                    record["sp_id"] = sp_id


                record["sets_played"] += 1

                record["rating_total"] += (
                    rating
                )

                record["ratings"].append(
                    rating
                )

                record["goals"] += int(
                    status["goal"]
                )

                record["assists"] += int(
                    status["assist"]
                )


    # =========================
    # 전체 선수 기록
    # =========================

    all_player_stats = []


    for record in player_totals.values():

        record["rating_total"] = round(
            record["rating_total"],
            2,
        )


        record["average_rating"] = round(
            record["rating_total"]
            / record["sets_played"],
            2,
        )


        record["image_url"] = (
            get_player_image_url(
                record["sp_id"]
            )
        )


        record.pop(
            "best_single_rating",
            None,
        )


        all_player_stats.append(
            record
        )


    # =========================
    # MVP 후보
    # 최소 2세트 출전
    # =========================

    mvp_rankings = [
        player
        for player in all_player_stats
        if player["sets_played"] >= 2
    ]


    mvp_rankings.sort(
        key=lambda player: (
            -player["rating_total"],
            -player["goals"],
            -player["assists"],
            -player["average_rating"],
        )
    )


    if not mvp_rankings:

        return (
            None,
            [],
            all_player_stats,
        )


    return (
        mvp_rankings[0],
        mvp_rankings,
        all_player_stats,
    )

# =========================
# FCL 3세트 MVP 테스트
# =========================

@app.get("/api/fconline/series-mvp-test")
def get_series_mvp_test():

    match_ids = [
        "6a81cdffa962a502d85e1eaa",
        "6a81cb89bdd2ff3b3f6807a8",
        "6a81c8f6115d94f2dc8ca43c",
    ]


    matches = [
        get_match_detail(match_id)
        for match_id in match_ids
    ]


    matches.sort(
        key=lambda match:
            match["matchDate"]
    )


    (
        mvp,
        ranking,
        player_stats,
    ) = calculate_series_mvp_from_matches(
        matches
    )


    return {
        "mvp": mvp,
        "ranking": ranking,
        "player_stats": player_stats,
    }


# =========================
# 참가자
# =========================

PARTICIPANTS = [
    "문권기",
    "이준석",
    "주은성",
    "이상",
    "서종원",
]

FCONLINE_NICKNAMES = {
    "문권기": "공기",
    "이준석": "똭똭",
    "주은성": "펜쉬차일드",
    "이상": "지수사",
    "서종원": "붉은심장베컴",
}


class SeriesStartRequest(BaseModel):
    team_a: str
    team_b: str

    series_type: str = "프리시즌"

    scheduled_date: str | None = None
    round_number: int | None = None

    # 테스트할 때 과거 시각 지정용
    # 실제 운영에서는 사용하지 않을 예정
    test_started_at: str | None = None

class ManualSeriesCompleteRequest(BaseModel):

    set1_team_a: int
    set1_team_b: int

    set2_team_a: int
    set2_team_b: int

    set3_team_a: int
    set3_team_b: int

class HistorySeriesImportRequest(BaseModel):
    team_a: str
    team_b: str
    match_date: str

def get_round_number(match_index):
    return (match_index // 5) + 1

# =========================
# 전체 경기 일정
# =========================

@app.get("/api/matches")
def get_matches():

    match_map = {}


    # =========================================
    # 1. 기존 Excel 일정
    # =========================================

    workbook = load_workbook(
        EXCEL_PATH
    )

    worksheet = workbook[
        "경기일정"
    ]


    regular_match_index = 0


    for row in worksheet.iter_rows(
        min_row=2,
        max_col=4,
        values_only=True,
    ):

        (
            match_date,
            team_a,
            team_b,
            match_type,
        ) = row


        if match_date is None:
            continue


        if hasattr(
            match_date,
            "strftime"
        ):

            match_date = (
                match_date.strftime(
                    "%Y-%m-%d"
                )
            )


        match_date = str(
            match_date
        )


        if match_type is None:

            match_type = (
                "정규리그"
            )


        if (
            match_type
            == "프리시즌"
        ):

            round_number = None

        else:

            round_number = (
                get_round_number(
                    regular_match_index
                )
            )

            regular_match_index += 1


        teams = sorted(
            [
                team_a,
                team_b,
            ]
        )


        match_key = (
            match_date,
            match_type,
            teams[0],
            teams[1],
        )


        match_map[
            match_key
        ] = {
            "series_id": None,
            "source": "excel",

            "date":
                match_date,

            "round":
                round_number,

            "match_type":
                match_type,

            "team_a":
                team_a,

            "team_b":
                team_b,

            "status": None,
        }


    workbook.close()


    # =========================================
    # 2. Neon 친선전 일정
    # =========================================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id
                        AS series_id,

                    s.scheduled_date,
                    s.status,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE
                    s.series_type =
                        '프리시즌'

                    AND
                    s.scheduled_date
                        IS NOT NULL

                    AND
                    s.status <>
                        'cancelled'

                ORDER BY
                    s.scheduled_date,
                    s.id
                """
            )


            series_rows = (
                cursor.fetchall()
            )


    for series_row in series_rows:

        match_date = (
            series_row[
                "scheduled_date"
            ].isoformat()
        )


        team_a = (
            series_row[
                "team_a"
            ]
        )

        team_b = (
            series_row[
                "team_b"
            ]
        )


        teams = sorted(
            [
                team_a,
                team_b,
            ]
        )


        match_key = (
            match_date,
            "프리시즌",
            teams[0],
            teams[1],
        )


        # DB 데이터 우선
        match_map[
            match_key
        ] = {
            "series_id":
                series_row[
                    "series_id"
                ],

            "source":
                "database",

            "date":
                match_date,

            "round":
                None,

            "match_type":
                "프리시즌",

            "team_a":
                team_a,

            "team_b":
                team_b,

            "status":
                series_row[
                    "status"
                ],
        }


    # =========================================
    # 날짜 빠른 순
    # =========================================

    matches = list(
        match_map.values()
    )


    matches.sort(
        key=lambda match: (
            match["date"],
            match["team_a"],
            match["team_b"],
        )
    )


    return matches


# =========================
# 오늘 경기
# =========================

@app.get("/api/matches/today")
def get_today_matches():

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date().isoformat()


    matches = get_matches()


    return [
        match

        for match
        in matches

        if match["date"]
        == today
    ]


# =========================
# 경기 결과
# =========================

@app.get("/api/results")
def get_results():
    workbook = load_workbook(RESULTS_PATH)
    worksheet = workbook["경기결과"]

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    results = []

    regular_match_index = 0

    for row in worksheet.iter_rows(
        min_row=2,
        max_col=10,
        values_only=True,
    ):
        (
            match_date,
            team_a,
            set1_team_a,
            set1_team_b,
            set2_team_a,
            set2_team_b,
            set3_team_a,
            set3_team_b,
            team_b,
            match_type,
        ) = row


        if match_date is None:
            continue


        if match_type is None:
            match_type = "정규리그"


        # ----------------------------------
        # 라운드 계산
        # 프리시즌은 라운드 계산에서 제외
        # ----------------------------------

        if match_type == "프리시즌":
            round_number = None

        else:
            round_number = get_round_number(
                regular_match_index
            )

            regular_match_index += 1


        if hasattr(match_date, "date"):
            match_date = match_date.date()


        # 오늘 경기와 미래 경기는 결과에서 제외
        if match_date >= today:
            continue


        scores = [
            set1_team_a,
            set1_team_b,
            set2_team_a,
            set2_team_b,
            set3_team_a,
            set3_team_b,
        ]


        # 세트 점수가 전부 입력된 경기만 출력
        if any(score is None for score in scores):
            continue


        team_a_total_score = (
            set1_team_a
            + set2_team_a
            + set3_team_a
        )

        team_b_total_score = (
            set1_team_b
            + set2_team_b
            + set3_team_b
        )


        results.append(
            {
                "date": match_date.strftime(
                    "%Y-%m-%d"
                ),

                "round": round_number,

                "match_type": match_type,

                "team_a": team_a,

                "team_b": team_b,

                "team_a_score": team_a_total_score,

                "team_b_score": team_b_total_score,

                "sets": [
                    {
                        "set": 1,
                        "team_a_score": set1_team_a,
                        "team_b_score": set1_team_b,
                    },
                    {
                        "set": 2,
                        "team_a_score": set2_team_a,
                        "team_b_score": set2_team_b,
                    },
                    {
                        "set": 3,
                        "team_a_score": set3_team_a,
                        "team_b_score": set3_team_b,
                    },
                ],
            }
        )


    workbook.close()

    return results

# =========================
# 팀 순위
# Excel + Neon PostgreSQL
# =========================

@app.get("/api/standings")
def get_standings():

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    # =========================
    # 기본 순위 데이터
    # =========================

    standings = {}


    for participant in PARTICIPANTS:

        standings[participant] = {
            "name": participant,

            # SERIES 수
            "played": 0,

            # 세트 기준
            "wins": 0,
            "draws": 0,
            "losses": 0,

            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,

            "points": 0,
        }


    # =========================
    # 경기 중복 판별 키
    # =========================

    def make_match_key(
        match_date,
        team_a,
        team_b,
    ):

        teams = sorted(
            [
                team_a,
                team_b,
            ]
        )


        return (
            match_date.isoformat(),
            teams[0],
            teams[1],
        )


    # =========================
    # 실제 순위 반영 함수
    # =========================

    def apply_match_result(
        team_a,
        team_b,
        sets,
    ):

        if (
            team_a not in standings
            or
            team_b not in standings
        ):
            return


        # FCL 정규리그는 3세트
        if len(sets) != 3:
            return


        team_a_record = (
            standings[team_a]
        )

        team_b_record = (
            standings[team_b]
        )


        # SERIES 경기 수
        team_a_record["played"] += 1
        team_b_record["played"] += 1


        # =========================
        # 세트별 계산
        # =========================

        for (
            team_a_score,
            team_b_score,
        ) in sets:

            team_a_score = int(
                team_a_score
            )

            team_b_score = int(
                team_b_score
            )


            # 득점 / 실점
            team_a_record[
                "goals_for"
            ] += team_a_score

            team_a_record[
                "goals_against"
            ] += team_b_score


            team_b_record[
                "goals_for"
            ] += team_b_score

            team_b_record[
                "goals_against"
            ] += team_a_score


            # =========================
            # 팀A 승
            # =========================

            if (
                team_a_score
                >
                team_b_score
            ):

                team_a_record[
                    "wins"
                ] += 1

                team_a_record[
                    "points"
                ] += 3

                team_b_record[
                    "losses"
                ] += 1


            # =========================
            # 팀B 승
            # =========================

            elif (
                team_a_score
                <
                team_b_score
            ):

                team_b_record[
                    "wins"
                ] += 1

                team_b_record[
                    "points"
                ] += 3

                team_a_record[
                    "losses"
                ] += 1


            # =========================
            # 무승부
            # =========================

            else:

                team_a_record[
                    "draws"
                ] += 1

                team_b_record[
                    "draws"
                ] += 1


                team_a_record[
                    "points"
                ] += 1

                team_b_record[
                    "points"
                ] += 1


    # =========================================
    # 1. Neon 정규리그 결과
    #
    # DB를 우선으로 계산
    # =========================================

    database_series = {}


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id
                        AS series_id,

                    s.scheduled_date,
                    s.started_at,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b,

                    ss.set_number,
                    ss.team_a_score,
                    ss.team_b_score

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                JOIN series_sets AS ss
                    ON ss.series_id =
                        s.id

                WHERE
                    s.status = 'completed'

                    AND
                    s.series_type = '정규리그'

                ORDER BY
                    s.id,
                    ss.set_number
                """
            )


            database_rows = (
                cursor.fetchall()
            )


    # =========================
    # SERIES별 묶기
    # =========================

    for row in database_rows:

        series_id = row[
            "series_id"
        ]


        if (
            series_id
            not in database_series
        ):

            database_series[
                series_id
            ] = {
                "scheduled_date":
                    row[
                        "scheduled_date"
                    ],

                "started_at":
                    row[
                        "started_at"
                    ],

                "team_a":
                    row[
                        "team_a"
                    ],

                "team_b":
                    row[
                        "team_b"
                    ],

                "sets": [],
            }


        database_series[
            series_id
        ][
            "sets"
        ].append(
            (
                row[
                    "team_a_score"
                ],

                row[
                    "team_b_score"
                ],
            )
        )


    # DB에 존재하는 경기 키
    database_match_keys = set()


    # =========================
    # Neon 결과 순위 반영
    # =========================

    for series_data in (
        database_series.values()
    ):

        match_date = (
            series_data[
                "scheduled_date"
            ]
        )


        # 예전 테스트 데이터 보호
        if match_date is None:

            match_date = (
                parse_kst_datetime(
                    series_data[
                        "started_at"
                    ]
                ).date()
            )


        # 미래 경기 보호
        if match_date > today:
            continue


        sets = series_data[
            "sets"
        ]


        if len(sets) != 3:
            continue


        match_key = (
            make_match_key(
                match_date,
                series_data[
                    "team_a"
                ],
                series_data[
                    "team_b"
                ],
            )
        )


        database_match_keys.add(
            match_key
        )


        apply_match_result(
            series_data[
                "team_a"
            ],

            series_data[
                "team_b"
            ],

            sets,
        )


    # =========================================
    # 2. 기존 Excel 결과
    # =========================================

    workbook = load_workbook(
        RESULTS_PATH
    )

    worksheet = workbook[
        "경기결과"
    ]


    for row in worksheet.iter_rows(
        min_row=2,
        max_col=10,
        values_only=True,
    ):

        (
            match_date,

            team_a,

            set1_team_a,
            set1_team_b,

            set2_team_a,
            set2_team_b,

            set3_team_a,
            set3_team_b,

            team_b,

            match_type,
        ) = row


        # 빈 행
        if match_date is None:
            continue


        # 경기구분 비어 있으면 정규리그
        if match_type is None:

            match_type = (
                "정규리그"
            )


        # =========================
        # 정규리그만 순위 반영
        # =========================

        if (
            match_type
            != "정규리그"
        ):
            continue


        # =========================
        # 날짜 변환
        # =========================

        if hasattr(
            match_date,
            "date"
        ):

            match_date = (
                match_date.date()
            )


        elif isinstance(
            match_date,
            str
        ):

            try:

                match_date = (
                    datetime.strptime(
                        match_date,
                        "%Y-%m-%d",
                    ).date()
                )

            except ValueError:

                continue


        # 미래 경기 제외
        if match_date > today:
            continue


        # =========================
        # 3세트 확인
        # =========================

        scores = [
            set1_team_a,
            set1_team_b,

            set2_team_a,
            set2_team_b,

            set3_team_a,
            set3_team_b,
        ]


        if any(
            score is None
            for score in scores
        ):
            continue


        # =========================
        # Neon과 중복이면 Excel 제외
        #
        # DB 데이터 우선
        # =========================

        match_key = (
            make_match_key(
                match_date,
                team_a,
                team_b,
            )
        )


        if (
            match_key
            in database_match_keys
        ):
            continue


        sets = [
            (
                set1_team_a,
                set1_team_b,
            ),
            (
                set2_team_a,
                set2_team_b,
            ),
            (
                set3_team_a,
                set3_team_b,
            ),
        ]


        apply_match_result(
            team_a,
            team_b,
            sets,
        )


    workbook.close()


    # =========================
    # 득실차
    # =========================

    for record in standings.values():

        record[
            "goal_difference"
        ] = (
            record[
                "goals_for"
            ]
            -
            record[
                "goals_against"
            ]
        )


    # =========================
    # 동률 시 참가자 기본 순서
    # =========================

    participant_order = {
        participant: index

        for index, participant
        in enumerate(
            PARTICIPANTS
        )
    }


    # =========================
    # 순위
    #
    # 1. 승점
    # 2. 득실차
    # 3. 득점
    # =========================

    sorted_standings = sorted(
        standings.values(),

        key=lambda record: (
            -record["points"],

            -record[
                "goal_difference"
            ],

            -record[
                "goals_for"
            ],

            participant_order[
                record["name"]
            ],
        ),
    )


    # =========================
    # 순위 번호
    # =========================

    for index, record in enumerate(
        sorted_standings,
        start=1,
    ):

        record["rank"] = index


    return sorted_standings

# =========================
# 선수 득점 순위
# Neon PostgreSQL
# 정규리그만 집계
# =========================

@app.get("/api/player-rankings")
def get_player_rankings():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    p.fcl_name,

                    p.fc_nickname
                        AS nickname,

                    sps.player_name,

                    MAX(
                        sps.image_url
                    )
                        AS image_url,

                    SUM(
                        sps.sets_played
                    )
                        AS sets_played,

                    SUM(
                        sps.rating_total
                    )
                        AS rating_total,

                    SUM(
                        sps.goals
                    )
                        AS goals,

                    SUM(
                        sps.assists
                    )
                        AS assists

                FROM series_player_stats
                    AS sps

                JOIN series AS s
                    ON s.id =
                        sps.series_id

                JOIN participants AS p
                    ON p.id =
                        sps.participant_id

                WHERE
                    s.status = 'completed'

                    AND
                    s.series_type = '정규리그'

                GROUP BY
                    p.id,
                    p.fcl_name,
                    p.fc_nickname,
                    sps.player_name

                ORDER BY
                    SUM(
                        sps.goals
                    ) DESC,

                    SUM(
                        sps.assists
                    ) DESC,

                    SUM(
                        sps.rating_total
                    ) DESC,

                    sps.player_name ASC
                """
            )


            rows = cursor.fetchall()


    players = []


    for row in rows:

        sets_played = int(
            row["sets_played"]
        )


        rating_total = float(
            row["rating_total"]
        )


        if sets_played > 0:

            average_rating = round(
                rating_total
                / sets_played,
                2,
            )

        else:

            average_rating = 0


        players.append(
            {
                # 기존 players.js 호환용
                # 선수 시즌 정보는
                # 아직 DB에 따로 저장하지 않음
                "season": "-",

                "fcl_name":
                    row["fcl_name"],

                "nickname":
                    row["nickname"],

                "player_name":
                    row["player_name"],

                "image_url":
                    row["image_url"],

                "sets_played":
                    sets_played,

                "rating_total":
                    round(
                        rating_total,
                        2,
                    ),

                "average_rating":
                    average_rating,

                "goals":
                    int(
                        row["goals"]
                    ),

                "assists":
                    int(
                        row["assists"]
                    ),
            }
        )


    # =========================
    # 순위
    # =========================

    for index, player in enumerate(
        players,
        start=1,
    ):

        player["rank"] = index


    return players

# =========================
# 플레이오프 일정
# =========================

@app.get("/api/playoffs")
def get_playoffs():

    workbook = load_workbook(
        PLAYOFFS_PATH
    )

    worksheet = workbook["플레이오프"]

    playoffs = []


    for row in worksheet.iter_rows(
        min_row=2,
        max_col=4,
        values_only=True,
    ):

        (
            match_date,
            stage,
            team_a,
            team_b,
        ) = row


        if match_date is None:
            continue


        if hasattr(match_date, "strftime"):
            match_date = match_date.strftime(
                "%Y-%m-%d"
            )


        playoffs.append(
            {
                "date": str(match_date),
                "stage": stage,
                "team_a": team_a,
                "team_b": team_b,
            }
        )


    workbook.close()

    return playoffs

# =========================
# FC Online
# OUID 테스트
# =========================

@app.get(
    "/api/fconline/ouid/{nickname}"
)
def get_fconline_ouid(
    nickname: str,
):

    url = (
        f"{NEXON_API_BASE_URL}/id"
    )

    try:

        with httpx.Client(
            timeout=10.0
        ) as client:

            response = client.get(
                url,
                headers=get_nexon_headers(),
                params={
                    "nickname": nickname,
                },
            )

    except httpx.RequestError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "NEXON Open API 연결에 "
                "실패했습니다."
            ),
        ) from error


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


    return response.json()

# =========================
# FC Online 최근 매치 조회
# =========================

@app.get(
    "/api/fconline/matches/{nickname}"
)
def get_fconline_matches(
    nickname: str,
    matchtype: int,
    limit: int = 20,
):

    # 1. 닉네임 -> OUID
    ouid_response = httpx.get(
        f"{NEXON_API_BASE_URL}/id",
        headers=get_nexon_headers(),
        params={
            "nickname": nickname,
        },
        timeout=10.0,
    )

    if ouid_response.status_code != 200:
        raise HTTPException(
            status_code=ouid_response.status_code,
            detail=ouid_response.text,
        )

    ouid = ouid_response.json()["ouid"]


    # 2. OUID -> 최근 매치 ID
    match_response = httpx.get(
        f"{NEXON_API_BASE_URL}/user/match",
        headers=get_nexon_headers(),
        params={
            "ouid": ouid,
            "matchtype": matchtype,
            "offset": 0,
            "limit": limit,
        },
        timeout=10.0,
    )

    if match_response.status_code != 200:
        raise HTTPException(
            status_code=match_response.status_code,
            detail=match_response.text,
        )


    return {
        "nickname": nickname,
        "ouid": ouid,
        "matches": match_response.json(),
    }


# =========================
# FC Online 매치 종류
# =========================

@app.get("/api/fconline/match-types")
def get_fconline_match_types():

    url = (
        "https://open.api.nexon.com/"
        "static/fconline/meta/matchtype.json"
    )

    try:
        with httpx.Client(
            timeout=10.0
        ) as client:

            response = client.get(url)

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="매치 종류 정보를 불러오지 못했습니다.",
        ) from error


    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


    return response.json()

# =========================
# FC Online 맞대결 탐색 테스트
# =========================

@app.get("/api/fconline/head-to-head-test")
def get_head_to_head_test():

    lee_nickname = "똭똭"
    seo_nickname = "붉은심장베컴"

    lee_ouid = get_ouid_by_nickname(
        lee_nickname
    )

    seo_ouid = get_ouid_by_nickname(
        seo_nickname
    )


    # 일반 1vs1에서 사용할 가능성이 있는
    # 매치 종류를 전부 검색
    match_types = {
        30: "리그 친선",
        40: "클래식 1on1",
        50: "공식경기",
        60: "공식 친선",
    }


    head_to_head_matches = []


    for match_type, description in (
        match_types.items()
    ):

        lee_matches = get_user_match_ids(
            lee_ouid,
            match_type,
        )

        seo_matches = get_user_match_ids(
            seo_ouid,
            match_type,
        )


        seo_match_set = set(
            seo_matches
        )


        # 똭똭 기록 순서를 유지하면서
        # 두 사람에게 공통으로 존재하는 matchId
        common_matches = [
            match_id
            for match_id in lee_matches
            if match_id in seo_match_set
        ]


        if common_matches:

            head_to_head_matches.append(
                {
                    "match_type": match_type,
                    "description": description,
                    "match_ids": common_matches,
                }
            )


    return {
        "team_a": {
            "fcl_name": "이준석",
            "nickname": lee_nickname,
        },

        "team_b": {
            "fcl_name": "서종원",
            "nickname": seo_nickname,
        },

        "matches": head_to_head_matches,
    }

# =========================
# FC Online 매치 상세 테스트
# =========================

@app.get(
    "/api/fconline/match-detail-test/{match_id}"
)
def get_match_detail_test(
    match_id: str,
):

    response = httpx.get(
        f"{NEXON_API_BASE_URL}/match-detail",
        headers=get_nexon_headers(),
        params={
            "matchid": match_id,
        },
        timeout=10.0,
    )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )


    return response.json()

# =========================
# FCL 3세트 분석 테스트
# =========================

@app.get("/api/fconline/series-test")
def get_series_test():

    match_ids = [
        "6a81cdffa962a502d85e1eaa",
        "6a81cb89bdd2ff3b3f6807a8",
        "6a81c8f6115d94f2dc8ca43c",
    ]

    series_matches = []


    for match_id in match_ids:

        response = httpx.get(
            f"{NEXON_API_BASE_URL}/match-detail",
            headers=get_nexon_headers(),
            params={
                "matchid": match_id,
            },
            timeout=10.0,
        )


        if response.status_code != 200:

            raise HTTPException(
                status_code=response.status_code,
                detail=response.text,
            )


        match_data = response.json()

        participants = []


        for match_info in match_data["matchInfo"]:

            player_data = []


            for player in match_info["player"]:

                status = player["status"]


                # 출전하지 않은 선수 제외
                if status["spRating"] <= 0:
                    continue


                player_data.append(
                    {
                        "sp_id": player["spId"],
                        "rating": status["spRating"],
                        "goal": status["goal"],
                        "assist": status["assist"],
                    }
                )


            participants.append(
                {
                    "nickname": match_info["nickname"],

                    "score": (
                        match_info["shoot"][
                            "goalTotalDisplay"
                        ]
                    ),

                    "players": player_data,
                }
            )


        series_matches.append(
            {
                "match_id": match_data["matchId"],
                "date": match_data["matchDate"],
                "match_type": match_data["matchType"],
                "participants": participants,
            }
        )


    # 실제 시간 순서
    series_matches.sort(
        key=lambda match: match["date"]
    )


    return series_matches


# =========================
# FCL SERIES START
# Neon PostgreSQL
# =========================

@app.post("/api/fconline/series/start")
def start_fcl_series(
    request: SeriesStartRequest,
):

    # =========================
    # 기본 검증
    # =========================

    if request.team_a == request.team_b:

        raise HTTPException(
            status_code=400,
            detail=(
                "같은 참가자끼리는 "
                "SERIES를 시작할 수 없습니다."
            ),
        )

    # =========================
    # SERIES 종류 검증
    # =========================

    if request.series_type not in (
        "프리시즌",
        "정규리그",
    ):

        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 SERIES 종류입니다.",
        )


    scheduled_date = None
    round_number = None


    # =========================
    # SERIES 경기 날짜
    # =========================

    if not request.scheduled_date:

        raise HTTPException(
            status_code=400,
            detail="경기 날짜를 선택해주세요.",
        )


    try:

        scheduled_date = datetime.strptime(
            request.scheduled_date,
            "%Y-%m-%d",
        ).date()

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "경기 날짜 형식은 "
                "YYYY-MM-DD여야 합니다."
            ),
        )


    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    # =========================
    # 친선전
    # =========================

    if request.series_type == "프리시즌":

        if scheduled_date < today:

            raise HTTPException(
                status_code=400,
                detail=(
                    "지난 날짜로 친선전을 "
                    "생성할 수 없습니다."
                ),
            )


    # =========================
    # 정규리그
    # =========================

    elif request.series_type == "정규리그":

        if request.round_number is None:

            raise HTTPException(
                status_code=400,
                detail=(
                    "정규리그 SERIES에는 "
                    "라운드 정보가 필요합니다."
                ),
            )


        round_number = (
            request.round_number
        )


    # =========================
    # 시작 시간
    # =========================

    if request.test_started_at:

        try:

            started_at = parse_kst_datetime(
                request.test_started_at
            )

        except ValueError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "test_started_at 형식이 "
                    "올바르지 않습니다."
                ),
            )

    else:

        now_kst = datetime.now(
            ZoneInfo("Asia/Seoul")
        )


        if (
            request.series_type
            == "프리시즌"
        ):

            scheduled_start = datetime(
                scheduled_date.year,
                scheduled_date.month,
                scheduled_date.day,
                tzinfo=ZoneInfo(
                    "Asia/Seoul"
                ),
            )


            started_at = max(
                now_kst,
                scheduled_start,
            )

        else:

            started_at = now_kst


    with get_db_connection() as connection:

        with connection.cursor() as cursor:


            # =========================
            # 참가자 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname,
                    ouid

                FROM participants

                WHERE fcl_name IN (
                    %s,
                    %s
                )
                """,
                (
                    request.team_a,
                    request.team_b,
                ),
            )


            participant_rows = (
                cursor.fetchall()
            )


            participant_map = {
                participant["fcl_name"]:
                    participant

                for participant
                in participant_rows
            }


            if (
                request.team_a
                not in participant_map
                or
                request.team_b
                not in participant_map
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "등록되지 않은 "
                        "FCL 참가자입니다."
                    ),
                )


            team_a = participant_map[
                request.team_a
            ]

            team_b = participant_map[
                request.team_b
            ]


            if (
                not team_a["fc_nickname"]
                or
                not team_b["fc_nickname"]
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "FC Online 닉네임이 "
                        "등록되지 않은 참가자가 있습니다."
                    ),
                )

            # =========================
            # 동일 정규리그 SERIES 중복 방지
            # =========================

            if (
                request.series_type
                == "정규리그"
            ):

                cursor.execute(
                    """
                    SELECT
                        id,
                        status

                    FROM series

                    WHERE
                        series_type = '정규리그'

                        AND scheduled_date = %s

                        AND round_number = %s

                        AND status <> 'cancelled'

                        AND (
                            (
                                team_a_id = %s
                                AND
                                team_b_id = %s
                            )

                            OR

                            (
                                team_a_id = %s
                                AND
                                team_b_id = %s
                            )
                        )

                    LIMIT 1
                    """,
                    (
                        scheduled_date,
                        round_number,

                        team_a["id"],
                        team_b["id"],

                        team_b["id"],
                        team_a["id"],
                    ),
                )


                existing_regular_series = (
                    cursor.fetchone()
                )


                if existing_regular_series:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이미 등록된 "
                            "정규리그 SERIES입니다."
                        ),
                    )

            # =========================
            # 동일 친선전 예약 중복 방지
            # 같은 날짜 + 같은 대진
            # =========================

            if (
                request.series_type
                == "프리시즌"
            ):

                cursor.execute(
                    """
                    SELECT
                        id,
                        status

                    FROM series

                    WHERE
                        series_type = '프리시즌'

                        AND
                        scheduled_date = %s

                        AND
                        status <> 'cancelled'

                        AND (
                            (
                                team_a_id = %s
                                AND
                                team_b_id = %s
                            )

                            OR

                            (
                                team_a_id = %s
                                AND
                                team_b_id = %s
                            )
                        )

                    LIMIT 1
                    """,
                    (
                        scheduled_date,

                        team_a["id"],
                        team_b["id"],

                        team_b["id"],
                        team_a["id"],
                    ),
                )


                existing_preseason_series = (
                    cursor.fetchone()
                )


                if existing_preseason_series:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "해당 날짜에 동일한 "
                            "친선전이 이미 예약되어 있습니다."
                        ),
                    )


            # =========================
            # 이미 ACTIVE인 같은 대진 확인
            # =========================

            cursor.execute(
                """
                SELECT id

                FROM series

                WHERE status = 'active'

                AND (
                    (
                        team_a_id = %s
                        AND
                        team_b_id = %s
                    )

                    OR

                    (
                        team_a_id = %s
                        AND
                        team_b_id = %s
                    )
                )

                LIMIT 1
                """,
                (
                    team_a["id"],
                    team_b["id"],

                    team_b["id"],
                    team_a["id"],
                ),
            )


            active_series = (
                cursor.fetchone()
            )


            if active_series:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "두 참가자 사이에 "
                        "이미 진행 중인 SERIES가 있습니다."
                    ),
                )


            # =========================
            # SERIES 생성
            # =========================

            if (
                request.series_type
                == "프리시즌"
            ):

                initial_status = (
                    "scheduled"
                )

            else:

                initial_status = (
                    "active"
                )

            cursor.execute(
                """
                INSERT INTO series (
                    series_type,

                    team_a_id,
                    team_b_id,

                    match_type,

                    scheduled_date,
                    round_number,

                    started_at,

                    status
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

                RETURNING id
                """,
                (
                    request.series_type,

                    team_a["id"],
                    team_b["id"],

                    40,

                    scheduled_date,
                    round_number,

                    started_at,

                    initial_status,
                ),
            )


            series_row = (
                cursor.fetchone()
            )


            series_id = (
                series_row["id"]
            )


        connection.commit()


    return {
        "series_id": series_id,

        "series_type":
            request.series_type,

        "team_a":
            request.team_a,

        "team_b":
            request.team_b,

        "nickname_a":
            team_a["fc_nickname"],

        "nickname_b":
            team_b["fc_nickname"],

        "match_type": 40,

        "started_at":
            started_at.isoformat(),

        "status": initial_status,

        "set_count": 0,

        "scheduled_date":
            request.scheduled_date,

        "round_number":
            round_number,
    }

# =========================
# FCL HISTORY SERIES IMPORT
# 과거 친선전 실제 경기 등록
# =========================

@app.post(
    "/api/fconline/history/import"
)
def import_history_series(
    request: HistorySeriesImportRequest,
):

    # =========================
    # 기본 검증
    # =========================

    if request.team_a == request.team_b:

        raise HTTPException(
            status_code=400,
            detail=(
                "서로 다른 참가자를 "
                "선택해주세요."
            ),
        )


    try:

        target_date = datetime.strptime(
            request.match_date,
            "%Y-%m-%d",
        ).date()

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "경기 날짜 형식은 "
                "YYYY-MM-DD여야 합니다."
            ),
        )


    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    if target_date >= today:

        raise HTTPException(
            status_code=400,
            detail=(
                "과거 경기 등록은 "
                "지난 날짜만 가능합니다."
            ),
        )


    # =========================
    # 참가자 조회
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname,
                    ouid

                FROM participants

                WHERE
                    fcl_name = %s
                    OR
                    fcl_name = %s
                """,
                (
                    request.team_a,
                    request.team_b,
                ),
            )


            participant_rows = (
                cursor.fetchall()
            )


    participant_map = {
        participant["fcl_name"]:
            participant

        for participant
        in participant_rows
    }


    team_a = participant_map.get(
        request.team_a
    )

    team_b = participant_map.get(
        request.team_b
    )


    if not team_a or not team_b:

        raise HTTPException(
            status_code=404,
            detail=(
                "참가자 정보를 "
                "찾을 수 없습니다."
            ),
        )


    nickname_a = (
        team_a["fc_nickname"]
    )

    nickname_b = (
        team_b["fc_nickname"]
    )


    if not nickname_a or not nickname_b:

        raise HTTPException(
            status_code=400,
            detail=(
                "FC Online 닉네임 "
                "정보가 없습니다."
            ),
        )


    # =========================
    # 동일 과거 SERIES 중복 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id

                FROM series

                WHERE
                    series_type = '프리시즌'

                    AND
                    scheduled_date = %s

                    AND
                    status <> 'cancelled'

                    AND (
                        (
                            team_a_id = %s
                            AND
                            team_b_id = %s
                        )

                        OR

                        (
                            team_a_id = %s
                            AND
                            team_b_id = %s
                        )
                    )

                LIMIT 1
                """,
                (
                    target_date,

                    team_a["id"],
                    team_b["id"],

                    team_b["id"],
                    team_a["id"],
                ),
            )


            existing_series = (
                cursor.fetchone()
            )


    if existing_series:

        raise HTTPException(
            status_code=400,
            detail=(
                "해당 날짜의 친선전이 "
                "이미 등록되어 있습니다."
            ),
        )


    # =========================
    # OUID 준비
    # =========================

    ouid_a = get_participant_ouid(
        team_a["id"],
        nickname_a,
        team_a["ouid"],
    )


    ouid_b = get_participant_ouid(
        team_b["id"],
        nickname_b,
        team_b["ouid"],
    )


    # =========================
    # 두 참가자의 최근 경기
    # =========================

    matches_a = get_user_match_ids(
        ouid_a,
        40,
        limit=50,
    )


    matches_b = get_user_match_ids(
        ouid_b,
        40,
        limit=50,
    )


    matches_b_set = set(
        matches_b
    )


    common_match_ids = [
        match_id

        for match_id
        in matches_a

        if match_id in matches_b_set
    ]


    detected_matches = []


    # =========================
    # 날짜 + 정확한 맞대결 필터
    # =========================

    for match_id in common_match_ids:

        match_data = get_match_detail(
            match_id
        )


        if (
            match_data["matchType"]
            != 40
        ):
            continue


        played_at = (
            parse_kst_datetime(
                match_data["matchDate"]
            )
        )


        if (
            played_at.date()
            != target_date
        ):
            continue


        match_nicknames = {
            match_info["nickname"]

            for match_info
            in match_data["matchInfo"]
        }


        if match_nicknames != {
            nickname_a,
            nickname_b,
        }:
            continue


        detected_matches.append(
            {
                "data":
                    match_data,

                "played_at":
                    played_at,
            }
        )


    # =========================
    # 시간순
    # =========================

    detected_matches.sort(
        key=lambda match:
            match["played_at"]
    )


    # =========================
    # 반드시 정확히 3경기
    # =========================

    if len(detected_matches) < 3:

        raise HTTPException(
            status_code=400,
            detail=(
                f"{request.match_date} "
                "맞대결을 "
                f"{len(detected_matches)}경기만 "
                "찾았습니다. "
                "3경기가 필요합니다."
            ),
        )


    if len(detected_matches) > 3:

        raise HTTPException(
            status_code=400,
            detail=(
                f"{request.match_date} "
                "맞대결이 "
                f"{len(detected_matches)}경기입니다. "
                "3경기를 자동으로 "
                "선택할 수 없습니다."
            ),
        )


    match_ids = [
        detected_match[
            "data"
        ][
            "matchId"
        ]

        for detected_match
        in detected_matches
    ]


    # =========================
    # 이미 사용된 실제 경기 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    nexon_match_id

                FROM series_sets

                WHERE nexon_match_id
                    IN (%s, %s, %s)

                LIMIT 1
                """,
                (
                    match_ids[0],
                    match_ids[1],
                    match_ids[2],
                ),
            )


            used_match = (
                cursor.fetchone()
            )


    if used_match:

        raise HTTPException(
            status_code=400,
            detail=(
                "해당 FC Online 경기가 "
                "이미 다른 SERIES에 "
                "등록되어 있습니다."
            ),
        )


    # =========================
    # MVP + 전체 선수 기록 계산
    # DB 저장 전에 먼저 계산
    # =========================

    match_data_list = [
        detected_match["data"]

        for detected_match
        in detected_matches
    ]


    (
        mvp,
        _,
        player_stats,
    ) = calculate_series_mvp_from_matches(
        match_data_list
    )


    started_at = (
        detected_matches[0][
            "played_at"
        ]
    )

    completed_at = (
        detected_matches[-1][
            "played_at"
        ]
    )


    # =========================
    # SERIES + 3 SET 저장
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO series (
                    series_type,

                    team_a_id,
                    team_b_id,

                    match_type,

                    scheduled_date,
                    round_number,

                    started_at,
                    completed_at,

                    status
                )

                VALUES (
                    '프리시즌',

                    %s,
                    %s,

                    40,

                    %s,
                    NULL,

                    %s,
                    %s,

                    'completed'
                )

                RETURNING id
                """,
                (
                    team_a["id"],
                    team_b["id"],

                    target_date,

                    started_at,
                    completed_at,
                ),
            )


            series_row = (
                cursor.fetchone()
            )

            series_id = (
                series_row["id"]
            )


            for (
                set_number,
                detected_match,
            ) in enumerate(
                detected_matches,
                start=1,
            ):

                match_data = (
                    detected_match["data"]
                )

                played_at = (
                    detected_match[
                        "played_at"
                    ]
                )


                participant_info_map = {
                    match_info["nickname"]:
                        match_info

                    for match_info
                    in match_data["matchInfo"]
                }


                team_a_info = (
                    participant_info_map[
                        nickname_a
                    ]
                )

                team_b_info = (
                    participant_info_map[
                        nickname_b
                    ]
                )


                team_a_score = (
                    team_a_info[
                        "shoot"
                    ][
                        "goalTotalDisplay"
                    ]
                )

                team_b_score = (
                    team_b_info[
                        "shoot"
                    ][
                        "goalTotalDisplay"
                    ]
                )


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,

                        set_number,

                        nexon_match_id,
                        played_at,

                        team_a_score,
                        team_b_score
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        series_id,
                        set_number,

                        match_data[
                            "matchId"
                        ],

                        played_at,

                        team_a_score,
                        team_b_score,
                    ),
                )


        connection.commit()


    # =========================
    # 전체 선수 기록 저장
    # =========================

    save_series_player_stats(
        series_id,

        team_a["id"],
        nickname_a,

        team_b["id"],
        nickname_b,

        player_stats,
    )


    # =========================
    # MVP 저장
    # =========================

    if mvp:

        if (
            mvp["nickname"]
            == nickname_a
        ):

            mvp_participant_id = (
                team_a["id"]
            )

        elif (
            mvp["nickname"]
            == nickname_b
        ):

            mvp_participant_id = (
                team_b["id"]
            )

        else:

            mvp_participant_id = None


        if mvp_participant_id:

            save_series_mvp(
                series_id,
                mvp_participant_id,
                mvp,
            )


    # =========================
    # 결과 응답
    # =========================

    return {
        "series_id":
            series_id,

        "series_type":
            "프리시즌",

        "status":
            "completed",

        "match_date":
            target_date.isoformat(),

        "team_a":
            request.team_a,

        "team_b":
            request.team_b,

        "sets_found":
            3,

        "match_ids":
            match_ids,

        "mvp":
            mvp,
    }

# =========================
# FCL SERIES ACTIVATE
# 예약 친선전 경기 시작
# =========================

@app.post(
    "/api/fconline/series/{series_id}/activate"
)
def activate_fcl_series(
    series_id: int,
):

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.scheduled_date,
                    s.status,

                    s.team_a_id,
                    s.team_b_id,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE s.id = %s
                """,
                (
                    series_id,
                ),
            )


            series = cursor.fetchone()


            if not series:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "SERIES를 찾을 수 없습니다."
                    ),
                )


            if (
                series["series_type"]
                != "프리시즌"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "친선전 SERIES만 "
                        "시작할 수 있습니다."
                    ),
                )


            if (
                series["status"]
                != "scheduled"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "예약된 친선전만 "
                        "시작할 수 있습니다."
                    ),
                )


            if (
                series["scheduled_date"]
                != today
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "친선전은 예약된 "
                        "경기 당일에만 "
                        "시작할 수 있습니다."
                    ),
                )


            # =========================
            # 이미 진행 중인 동일 대진 확인
            # =========================

            cursor.execute(
                """
                SELECT id

                FROM series

                WHERE
                    status = 'active'

                    AND id <> %s

                    AND (
                        (
                            team_a_id = %s
                            AND
                            team_b_id = %s
                        )

                        OR

                        (
                            team_a_id = %s
                            AND
                            team_b_id = %s
                        )
                    )

                LIMIT 1
                """,
                (
                    series_id,

                    series["team_a_id"],
                    series["team_b_id"],

                    series["team_b_id"],
                    series["team_a_id"],
                ),
            )


            active_series = (
                cursor.fetchone()
            )


            if active_series:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "두 참가자 사이에 "
                        "이미 진행 중인 "
                        "SERIES가 있습니다."
                    ),
                )


            started_at = datetime.now(
                ZoneInfo("Asia/Seoul")
            )


            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'active',
                    started_at = %s,
                    completed_at = NULL

                WHERE id = %s
                """,
                (
                    started_at,
                    series_id,
                ),
            )


        connection.commit()


    return {
        "series_id":
            series_id,

        "series_type":
            "프리시즌",

        "team_a":
            series["team_a"],

        "team_b":
            series["team_b"],

        "scheduled_date":
            series[
                "scheduled_date"
            ].isoformat(),

        "started_at":
            started_at.isoformat(),

        "status":
            "active",
    }

# =========================
# FCL SERIES CANCEL
# 친선전 취소
# =========================

@app.post(
    "/api/fconline/series/{series_id}/cancel"
)
def cancel_fcl_series(
    series_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    status

                FROM series

                WHERE id = %s
                """,
                (
                    series_id,
                ),
            )


            series = cursor.fetchone()


            if not series:

                raise HTTPException(
                    status_code=404,
                    detail="SERIES를 찾을 수 없습니다.",
                )


            if (
                series["series_type"]
                != "프리시즌"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "친선전 SERIES만 "
                        "취소할 수 있습니다."
                    ),
                )


            if (
                series["status"]
                not in (
                    "scheduled",
                    "active",
                )
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "예약 또는 진행 중인 "
                        "친선전만 취소할 수 있습니다."
                    ),
                )


            # 이미 감지된 세트가 있다면
            # 함께 제거
            cursor.execute(
                """
                DELETE FROM series_sets
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            cursor.execute(
                """
                DELETE FROM series_mvp
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            cursor.execute(
                """
                DELETE FROM series_player_stats
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'cancelled',
                    completed_at = NULL

                WHERE id = %s
                """,
                (
                    series_id,
                ),
            )


        connection.commit()


    return {
        "series_id": series_id,
        "status": "cancelled",
        "message": "친선전 SERIES가 취소되었습니다.",
    }

# =========================
# FCL SERIES MANUAL COMPLETE
# 친선전 수동 결과 입력
# =========================

@app.post(
    "/api/fconline/series/{series_id}/manual-complete"
)
def manual_complete_fcl_series(
    series_id: int,
    request: ManualSeriesCompleteRequest,
):

    scores = [
        request.set1_team_a,
        request.set1_team_b,

        request.set2_team_a,
        request.set2_team_b,

        request.set3_team_a,
        request.set3_team_b,
    ]


    # =========================
    # 점수 검증
    # =========================

    if any(
        score < 0
        for score in scores
    ):

        raise HTTPException(
            status_code=400,
            detail="점수는 0 이상이어야 합니다.",
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.status,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE s.id = %s
                """,
                (
                    series_id,
                ),
            )


            series = cursor.fetchone()


            if not series:

                raise HTTPException(
                    status_code=404,
                    detail="SERIES를 찾을 수 없습니다.",
                )


            # =========================
            # 친선전만 수동 완료 허용
            # =========================

            if (
                series["status"]
                != "active"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "진행 중인 친선전만 "
                        "수동 완료할 수 있습니다."
                    ),
                )


            if (
                series["status"]
                not in (
                    "scheduled",
                    "active",
                )
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "예약 또는 진행 중인 "
                        "친선전만 취소할 수 있습니다."
                    ),
                )


            # =========================
            # 기존 자동 감지 세트 제거
            #
            # 수동 입력 결과로 완전히 덮어씀
            # =========================

            cursor.execute(
                """
                DELETE FROM series_sets
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            cursor.execute(
                """
                DELETE FROM series_mvp
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            cursor.execute(
                """
                DELETE FROM series_player_stats
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            # =========================
            # 수동 세트
            # =========================

            manual_sets = [
                (
                    1,
                    request.set1_team_a,
                    request.set1_team_b,
                ),
                (
                    2,
                    request.set2_team_a,
                    request.set2_team_b,
                ),
                (
                    3,
                    request.set3_team_a,
                    request.set3_team_b,
                ),
            ]


            completed_at = datetime.now(
                ZoneInfo("Asia/Seoul")
            )


            for (
                set_number,
                team_a_score,
                team_b_score,
            ) in manual_sets:

                manual_match_id = (
                    f"manual-{series_id}-"
                    f"{set_number}"
                )


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,
                        set_number,
                        nexon_match_id,
                        played_at,
                        team_a_score,
                        team_b_score
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    """,
                    (
                        series_id,
                        set_number,
                        manual_match_id,
                        completed_at,
                        team_a_score,
                        team_b_score,
                    ),
                )


            # =========================
            # SERIES 완료
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'completed',
                    completed_at = %s

                WHERE id = %s
                """,
                (
                    completed_at,
                    series_id,
                ),
            )


        connection.commit()


    team_a_total_score = (
        request.set1_team_a
        + request.set2_team_a
        + request.set3_team_a
    )


    team_b_total_score = (
        request.set1_team_b
        + request.set2_team_b
        + request.set3_team_b
    )


    return {
        "series_id": series_id,

        "status": "completed",

        "series_type":
            "프리시즌",

        "team_a":
            series["team_a"],

        "team_b":
            series["team_b"],

        "team_a_score":
            team_a_total_score,

        "team_b_score":
            team_b_total_score,

        "sets": [
            {
                "set": 1,
                "team_a_score":
                    request.set1_team_a,
                "team_b_score":
                    request.set1_team_b,
            },
            {
                "set": 2,
                "team_a_score":
                    request.set2_team_a,
                "team_b_score":
                    request.set2_team_b,
            },
            {
                "set": 3,
                "team_a_score":
                    request.set3_team_a,
                "team_b_score":
                    request.set3_team_b,
            },
        ],
    }


# =========================
# FCL SERIES STATUS
# =========================

# =========================
# FCL SERIES STATUS
# NEXON 탐색 + DB 저장
# =========================

@app.get(
    "/api/fconline/series/{series_id}/status"
)
def get_fcl_series_status(
    series_id: int,
):

    # =========================
    # SERIES + 참가자 조회
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.match_type,
                    s.scheduled_date,
                    s.started_at,
                    s.completed_at,
                    s.status,

                    team_a.id
                        AS team_a_id,

                    team_a.fcl_name
                        AS team_a_name,

                    team_a.fc_nickname
                        AS nickname_a,

                    team_a.ouid
                        AS ouid_a,

                    team_b.id
                        AS team_b_id,

                    team_b.fcl_name
                        AS team_b_name,

                    team_b.fc_nickname
                        AS nickname_b,

                    team_b.ouid
                        AS ouid_b

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE s.id = %s
                """,
                (
                    series_id,
                ),
            )


            series = cursor.fetchone()


    if not series:

        raise HTTPException(
            status_code=404,
            detail="SERIES를 찾을 수 없습니다.",
        )
    
    if (
        series["status"]
        != "active"
    ):

        return {
            "series": {
                "series_id":
                    series_id,

                "series_type":
                    series["series_type"],

                "team_a":
                    series[
                        "team_a_name"
                    ],

                "team_b":
                    series[
                        "team_b_name"
                    ],

                "nickname_a":
                    series[
                        "nickname_a"
                    ],

                "nickname_b":
                    series[
                        "nickname_b"
                    ],

                "match_type":
                    series[
                        "match_type"
                    ],

                "scheduled_date":
                    (
                        series[
                            "scheduled_date"
                        ].isoformat()

                        if series[
                            "scheduled_date"
                        ]

                        else None
                    ),

                "started_at":
                    (
                        series[
                            "started_at"
                        ].isoformat()

                        if series[
                            "started_at"
                        ]

                        else None
                    ),

                "status":
                    series[
                        "status"
                    ],

                "set_count":
                    0,
            },

            "sets": [],

            "mvp": None,
        }


    nickname_a = series[
        "nickname_a"
    ]

    nickname_b = series[
        "nickname_b"
    ]


    if (
        not nickname_a
        or
        not nickname_b
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "FC Online 닉네임 정보가 "
                "없습니다."
            ),
        )


    # =========================
    # OUID 준비
    # =========================

    ouid_a = get_participant_ouid(
        series["team_a_id"],
        nickname_a,
        series["ouid_a"],
    )


    ouid_b = get_participant_ouid(
        series["team_b_id"],
        nickname_b,
        series["ouid_b"],
    )


    # =========================
    # NEXON 최근 경기 조회
    # =========================

    matches_a = get_user_match_ids(
        ouid_a,
        series["match_type"],
        limit=50,
    )

    matches_b = get_user_match_ids(
        ouid_b,
        series["match_type"],
        limit=50,
    )


    matches_b_set = set(
        matches_b
    )


    common_match_ids = [
        match_id

        for match_id in matches_a

        if match_id in matches_b_set
    ]


    started_at = parse_kst_datetime(
        series["started_at"]
    )


    detected_matches = []


    # =========================
    # SERIES START 이후
    # 실제 맞대결만 탐색
    # =========================

    for match_id in common_match_ids:

        match_data = get_match_detail(
            match_id
        )


        match_date = parse_kst_datetime(
            match_data["matchDate"]
        )


        # START 이전 경기
        if match_date < started_at:
            continue


        # 다른 경기 타입
        if (
            match_data["matchType"]
            != series["match_type"]
        ):
            continue


        match_nicknames = {
            match_info["nickname"]

            for match_info
            in match_data["matchInfo"]
        }


        # 정확히 두 참가자 경기인지 확인
        if match_nicknames != {
            nickname_a,
            nickname_b,
        }:
            continue


        detected_matches.append(
            {
                "data": match_data,
                "played_at": match_date,
            }
        )


    # =========================
    # 시간순
    # =========================

    detected_matches.sort(
        key=lambda match:
            match["played_at"]
    )


    # SERIES는 3세트
    detected_matches = (
        detected_matches[:3]
    )


    # =========================
    # DB에 세트 저장
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:


            for (
                index,
                detected_match,
            ) in enumerate(
                detected_matches,
                start=1,
            ):

                match_data = (
                    detected_match["data"]
                )

                played_at = (
                    detected_match[
                        "played_at"
                    ]
                )


                participant_map = {
                    match_info["nickname"]:
                        match_info

                    for match_info
                    in match_data["matchInfo"]
                }


                team_a_info = (
                    participant_map[
                        nickname_a
                    ]
                )

                team_b_info = (
                    participant_map[
                        nickname_b
                    ]
                )


                team_a_score = (
                    team_a_info[
                        "shoot"
                    ][
                        "goalTotalDisplay"
                    ]
                )

                team_b_score = (
                    team_b_info[
                        "shoot"
                    ][
                        "goalTotalDisplay"
                    ]
                )


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,

                        set_number,

                        nexon_match_id,

                        played_at,

                        team_a_score,
                        team_b_score
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        series_id,
                        set_number
                    )

                    DO UPDATE SET

                        nexon_match_id =
                            EXCLUDED.nexon_match_id,

                        played_at =
                            EXCLUDED.played_at,

                        team_a_score =
                            EXCLUDED.team_a_score,

                        team_b_score =
                            EXCLUDED.team_b_score
                    """,
                    (
                        series_id,

                        index,

                        match_data[
                            "matchId"
                        ],

                        played_at,

                        team_a_score,
                        team_b_score,
                    ),
                )


            # =========================
            # 실제 저장된 세트 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    nexon_match_id,
                    played_at,
                    team_a_score,
                    team_b_score

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )


            saved_sets = (
                cursor.fetchall()
            )


            set_count = len(
                saved_sets
            )


            # =========================
            # 3세트 완료 처리
            # =========================

            if set_count >= 3:

                completed_at = (
                    saved_sets[-1][
                        "played_at"
                    ]
                )


                cursor.execute(
                    """
                    UPDATE series

                    SET
                        status = 'completed',
                        completed_at = %s

                    WHERE id = %s
                    """,
                    (
                        completed_at,
                        series_id,
                    ),
                )


                status = "completed"

            else:

                status = "active"


        connection.commit()

    # =========================
    # 3세트 완료 시 MVP 계산
    # =========================

    mvp = None


    is_manual_result = any(
        str(
            saved_set[
                "nexon_match_id"
            ]
        ).startswith(
            "manual-"
        )

        for saved_set
        in saved_sets[:3]
    )


    if (
        len(saved_sets) >= 3
        and
        not is_manual_result
    ):

        mvp_matches = []


        for saved_set in saved_sets[:3]:

            match_data = get_match_detail(
                saved_set[
                    "nexon_match_id"
                ]
            )

            mvp_matches.append(
                match_data
            )


        mvp_matches.sort(
            key=lambda match:
                match["matchDate"]
        )


        (
            mvp,
            _,
            player_stats,
        ) = calculate_series_mvp_from_matches(
            mvp_matches
        )

        # =========================
        # 전체 선수 기록 DB 저장
        # =========================

        save_series_player_stats(
            series_id,

            series["team_a_id"],
            nickname_a,

            series["team_b_id"],
            nickname_b,

            player_stats,
        )


        if mvp:

            if (
                mvp["nickname"]
                == nickname_a
            ):

                mvp_participant_id = (
                    series["team_a_id"]
                )


            elif (
                mvp["nickname"]
                == nickname_b
            ):

                mvp_participant_id = (
                    series["team_b_id"]
                )


            else:

                mvp_participant_id = None


            if mvp_participant_id:

                save_series_mvp(
                    series_id,
                    mvp_participant_id,
                    mvp,
                )


    # =========================
    # API 응답용 세트
    # =========================

    sets = []


    for saved_set in saved_sets:

        sets.append(
            {
                "set":
                    saved_set[
                        "set_number"
                    ],

                "match_id":
                    saved_set[
                        "nexon_match_id"
                    ],

                "match_date":
                    saved_set[
                        "played_at"
                    ].isoformat(),

                "team_a_score":
                    saved_set[
                        "team_a_score"
                    ],

                "team_b_score":
                    saved_set[
                        "team_b_score"
                    ],
            }
        )


    return {
        "series": {
            "series_id":
                series_id,

            "series_type":
                series["series_type"],

            "team_a":
                series["team_a_name"],

            "team_b":
                series["team_b_name"],

            "nickname_a":
                nickname_a,

            "nickname_b":
                nickname_b,

            "match_type":
                series["match_type"],

            "started_at":
                started_at.isoformat(),

            "status":
                status,

            "set_count":
                len(sets),
        },

        "sets": sets,

        "mvp": mvp,
    }

# =========================
# SERIES MVP DB 조회
# =========================

@app.get(
    "/api/fconline/series/{series_id}/mvp"
)
def get_saved_series_mvp(
    series_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sm.series_id,

                    p.fcl_name,
                    p.fc_nickname
                        AS nickname,

                    sm.sp_id,
                    sm.player_name,

                    sm.sets_played,

                    sm.rating_total,
                    sm.average_rating,

                    sm.goals,
                    sm.assists,

                    sm.image_url

                FROM series_mvp AS sm

                JOIN participants AS p
                    ON p.id =
                        sm.participant_id

                WHERE sm.series_id = %s
                """,
                (
                    series_id,
                ),
            )


            mvp = cursor.fetchone()


    if not mvp:

        raise HTTPException(
            status_code=404,
            detail=(
                "저장된 MVP가 없습니다."
            ),
        )


    # PostgreSQL NUMERIC -> JSON 숫자
    mvp["rating_total"] = float(
        mvp["rating_total"]
    )

    mvp["average_rating"] = float(
        mvp["average_rating"]
    )


    return mvp

# =========================
# 완료된 SERIES 결과 조회
# =========================

@app.get(
    "/api/fconline/series/completed-results"
)
def get_completed_series_results():

    results = []


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 완료 SERIES 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id AS series_id,
                    s.series_type,
                    s.scheduled_date,
                    s.started_at,
                    s.completed_at,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b,

                    mvp_owner.fcl_name
                        AS mvp_fcl_name,

                    mvp_owner.fc_nickname
                        AS mvp_nickname,

                    sm.sp_id
                        AS mvp_sp_id,

                    sm.player_name
                        AS mvp_player_name,

                    sm.sets_played
                        AS mvp_sets_played,

                    sm.rating_total
                        AS mvp_rating_total,

                    sm.average_rating
                        AS mvp_average_rating,

                    sm.goals
                        AS mvp_goals,

                    sm.assists
                        AS mvp_assists,

                    sm.image_url
                        AS mvp_image_url

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                LEFT JOIN series_mvp AS sm
                    ON sm.series_id =
                        s.id

                LEFT JOIN participants AS mvp_owner
                    ON mvp_owner.id =
                        sm.participant_id

                WHERE s.status = 'completed'

                ORDER BY s.completed_at DESC
                """
            )


            series_rows = (
                cursor.fetchall()
            )


            # =========================
            # SERIES별 세트 조회
            # =========================

            for series_row in series_rows:

                cursor.execute(
                    """
                    SELECT
                        set_number,
                        team_a_score,
                        team_b_score

                    FROM series_sets

                    WHERE series_id = %s

                    ORDER BY set_number
                    """,
                    (
                        series_row[
                            "series_id"
                        ],
                    ),
                )


                set_rows = (
                    cursor.fetchall()
                )


                # 3세트 미완성 데이터 보호
                if len(set_rows) < 3:
                    continue


                sets = []

                team_a_total_score = 0
                team_b_total_score = 0


                for set_row in set_rows:

                    team_a_score = (
                        set_row[
                            "team_a_score"
                        ]
                    )

                    team_b_score = (
                        set_row[
                            "team_b_score"
                        ]
                    )


                    team_a_total_score += (
                        team_a_score
                    )

                    team_b_total_score += (
                        team_b_score
                    )


                    sets.append(
                        {
                            "set":
                                set_row[
                                    "set_number"
                                ],

                            "team_a_score":
                                team_a_score,

                            "team_b_score":
                                team_b_score,
                        }
                    )


                # =========================
                # MVP
                # =========================

                mvp = None


                if (
                    series_row[
                        "mvp_player_name"
                    ]
                    is not None
                ):

                    mvp = {
                        "fcl_name":
                            series_row[
                                "mvp_fcl_name"
                            ],

                        "nickname":
                            series_row[
                                "mvp_nickname"
                            ],

                        "sp_id":
                            series_row[
                                "mvp_sp_id"
                            ],

                        "player_name":
                            series_row[
                                "mvp_player_name"
                            ],

                        "sets_played":
                            series_row[
                                "mvp_sets_played"
                            ],

                        "rating_total":
                            float(
                                series_row[
                                    "mvp_rating_total"
                                ]
                            ),

                        "average_rating":
                            float(
                                series_row[
                                    "mvp_average_rating"
                                ]
                            ),

                        "goals":
                            series_row[
                                "mvp_goals"
                            ],

                        "assists":
                            series_row[
                                "mvp_assists"
                            ],

                        "image_url":
                            series_row[
                                "mvp_image_url"
                            ],
                    }


                started_at = parse_kst_datetime(
                    series_row[
                        "started_at"
                    ]
                )

                result_date = (
                    series_row[
                        "scheduled_date"
                    ]
                )


                if result_date is None:

                    result_date = (
                        started_at.date()
                    )


                results.append(
                    {
                        "series_id":
                            series_row[
                                "series_id"
                            ],

                        "source":
                            "database",

                        "date":
                            result_date.strftime(
                                "%Y-%m-%d"
                            ),

                        "completed_at":
                        (
                            series_row[
                                "completed_at"
                            ].isoformat()

                            if series_row[
                                "completed_at"
                            ]

                            else None
                        ),

                        "round":
                            None,

                        "match_type":
                            series_row[
                                "series_type"
                            ],

                        "team_a":
                            series_row[
                                "team_a"
                            ],

                        "team_b":
                            series_row[
                                "team_b"
                            ],

                        "team_a_score":
                            team_a_total_score,

                        "team_b_score":
                            team_b_total_score,

                        "sets":
                            sets,

                        "mvp":
                            mvp,
                    }
                )


    return results

# =========================
# SERIES 전체 선수 기록 조회
# =========================

@app.get(
    "/api/fconline/series/{series_id}/player-stats"
)
def get_series_player_stats(
    series_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sps.series_id,

                    p.fcl_name,
                    p.fc_nickname
                        AS nickname,

                    sps.sp_id,
                    sps.player_name,

                    sps.sets_played,

                    sps.rating_total,
                    sps.average_rating,

                    sps.goals,
                    sps.assists,

                    sps.image_url

                FROM series_player_stats
                    AS sps

                JOIN participants AS p
                    ON p.id =
                        sps.participant_id

                WHERE sps.series_id = %s

                ORDER BY
                    sps.goals DESC,
                    sps.assists DESC,
                    sps.rating_total DESC
                """,
                (
                    series_id,
                ),
            )


            players = cursor.fetchall()


    for player in players:

        player["rating_total"] = float(
            player["rating_total"]
        )

        player["average_rating"] = float(
            player["average_rating"]
        )


    return players

# =========================
# DB 초기화
# =========================

@app.post("/api/database/init")
def init_database():

    initialize_database()

    return {
        "status": "success",
        "message": "FCL 데이터베이스가 초기화되었습니다.",
    }

# =========================
# 참가자 DB 확인
# =========================

@app.get("/api/database/participants")
def get_database_participants():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname,
                    ouid

                FROM participants

                ORDER BY id
                """
            )

            participants = (
                cursor.fetchall()
            )


    return participants

# =========================
# 프론트엔드
#
# 반드시 API 선언보다 아래에 위치
# =========================

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True,
    ),
    name="frontend",
)