import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import secrets
import hashlib
import hmac
import secrets
import heapq


from pathlib import Path
from datetime import (
    datetime,
    timedelta,
)
from zoneinfo import ZoneInfo
from backend.player_catalog import (
    PLAYER_DATABASE_STAT_FILTER_MAP,
    PLAYER_STAT_COLUMN_MAP,
    get_player_catalog_filter_options,
    get_player_catalog_nations_by_continent,
    get_player_catalog_teams_by_league,
    get_player_ability,
    search_player_catalog,
    recommend_player_catalog,
)

from backend import (
    player_catalog as
    player_catalog_service,
)

from backend.update_new_season import (
    build_metadata_card_map,
    get_database_season_counts,
)

from backend.quick_squad_locked import (
    LockedPlayerInput,
    LockedPreviewRequest,
    LockedSquadService,
)

from backend.player_popularity import (
    get_latest_player_popularity_map,
    sync_player_popularity,
)

from backend.player_supply_restriction import (
    get_supply_restriction_status,
    get_supply_restriction_status_by_season_id,
)

from backend.team_color_engine import (
    get_active_team_colors_for_squad,
    get_active_enhancement_team_colors_for_squad,
)

import re

import httpx
import psycopg

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from fastapi import (
    FastAPI,
    HTTPException,
    Response,
    File,
    UploadFile,
    Header,
    Depends,
    Request,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from openpyxl import load_workbook
from pydantic import BaseModel, Field
from typing import Literal

from backend.player_generation_notice import (
    sync_generation_notices,
    get_generation_notice_status,
    get_generation_notice_preview,
    get_generation_action_preview,
    get_generation_resolution_preview,
    sync_generation_status_from_notices,
)



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

ADMIN_PASSWORD = os.getenv(
    "ADMIN_PASSWORD"
)


ADMIN_SESSION_SECONDS = (
    8 * 60 * 60
)


ADMIN_SESSIONS = {}

FC_ONLINE_SYNC_LOCK = (
    threading.Lock()
)

PLAYER_POPULARITY_SYNC_LOCK = (
    threading.Lock()
)

NEXON_API_BASE_URL = (
    "https://open.api.nexon.com/fconline/v1"
)

def get_community_post_attachments(
    cursor,
    post_id: int,
):

    cursor.execute(
        """
        SELECT
            id,
            original_file_name,
            content_type,
            sort_order

        FROM community_attachments

        WHERE post_id = %s

        ORDER BY
            sort_order ASC,
            id ASC
        """,
        (
            post_id,
        ),
    )

    rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "original_file_name": row["original_file_name"],
            "content_type": row["content_type"],
            "sort_order": row["sort_order"],
            "image_url": (
                "/api/community/"
                f"attachments/{row['id']}"
            ),
        }
        for row in rows
    ]

# =========================
# FC Online 선수 메타데이터
# =========================

SPID_METADATA_CACHE = None
SEASON_METADATA_CACHE = None


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

def get_season_metadata():

    global SEASON_METADATA_CACHE


    if SEASON_METADATA_CACHE is not None:
        return SEASON_METADATA_CACHE


    url = (
        "https://open.api.nexon.com/"
        "static/fconline/meta/seasonid.json"
    )


    response = httpx.get(
        url,
        timeout=20.0,
    )


    if response.status_code != 200:

        raise HTTPException(
            status_code=response.status_code,
            detail="시즌 메타데이터 조회 실패",
        )


    SEASON_METADATA_CACHE = {
        int(season["seasonId"]): {
            "season_id":
                int(season["seasonId"]),

            "class_name":
                season["className"],

            "season_image_url":
                season["seasonImg"],
        }

        for season
        in response.json()
    }


    return SEASON_METADATA_CACHE


def get_player_season_info(
    sp_id,
    season_metadata,
):

    try:
        season_id = (
            int(sp_id)
            // 1_000_000
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


    return season_metadata.get(
        season_id
    )

def ensure_fconline_season_snapshot(
    sp_id,
):

    season_id = (
        int(sp_id)
        // 1_000_000
    )


    # =========================
    # 이미 저장됐으면 종료
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    season_id,
                    class_name
                FROM fconline_season_snapshots
                WHERE season_id = %s
                """,
                (
                    season_id,
                ),
            )


            existing_snapshot = cursor.fetchone()


    if existing_snapshot:

        return {
            "season_id":
                existing_snapshot[
                    "season_id"
                ],

            "class_name":
                existing_snapshot[
                    "class_name"
                ],

            "season_image_url":
                (
                    "/api/fconline/"
                    "metadata/seasons/"
                    f"{season_id}/image"
                ),
        }


    # =========================
    # Nexon 시즌 메타데이터
    # =========================

    season_metadata = get_season_metadata()


    season = season_metadata.get(
            season_id
        )


    if not season:

        raise HTTPException(
            status_code=404,
            detail=(
                f"시즌 메타데이터 없음: "
                f"{season_id}"
            ),
        )


    source_image_url = season[
            "season_image_url"
        ]


    # =========================
    # 시즌 이미지 실제 다운로드
    # =========================

    image_response = httpx.get(
            source_image_url,
            timeout=20.0,
            follow_redirects=True,
        )


    if image_response.status_code != 200:

        raise HTTPException(
            status_code=
                image_response.status_code,

            detail=(
                "시즌 이미지 다운로드 실패"
            ),
        )


    image_content_type = (
        image_response.headers.get(
            "content-type",
            "image/png",
        )
        .split(";")[0]
        .strip()
    )


    image_data = image_response.content


    if not image_data:

        raise HTTPException(
            status_code=502,
            detail="시즌 이미지 데이터 없음",
        )


    # =========================
    # Neon 영구 Snapshot
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_season_snapshots (
                        season_id,
                        class_name,
                        source_image_url,
                        image_data,
                        image_content_type
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

                ON CONFLICT (
                    season_id
                )
                DO NOTHING
                """,
                (
                    season_id,

                    season[
                        "class_name"
                    ],

                    source_image_url,
                    image_data,
                    image_content_type,
                ),
            )


        connection.commit()


    return {
        "season_id":
            season_id,

        "class_name":
            season[
                "class_name"
            ],

        "season_image_url":
            (
                "/api/fconline/"
                "metadata/seasons/"
                f"{season_id}/image"
            ),
    }

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

def parse_nexon_datetime(value):

    if isinstance(value, datetime):
        parsed = value

    else:
        parsed = datetime.fromisoformat(
            value
        )


    if parsed.tzinfo is None:

        parsed = parsed.replace(
            tzinfo=ZoneInfo("UTC")
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


# =========================================
# QUICK SQUAD
# BASE PLAYER STATS
# =========================================

QUICK_SQUAD_BASE_STAT_KEYS = (
    "sprint_speed",
    "acceleration",
    "finishing",
    "shot_power",
    "long_shots",
    "positioning",
    "volleys",
    "penalties",

    "short_pass",
    "vision",
    "crossing",
    "long_pass",
    "free_kick",
    "curve",

    "dribbling",
    "ball_control",
    "agility",
    "balance",
    "reactions",

    "marking",
    "tackle",
    "interceptions",
    "heading",
    "sliding_tackle",

    "strength",
    "stamina",
    "aggression",
    "jumping",
    "composure",

    "gk_diving",
    "gk_handling",
    "gk_kick",
    "gk_reflexes",
    "gk_positioning",
)


def attach_quick_squad_player_base_stats(
    connection,
    players,
):

    sp_ids = [
        int(
            player.get(
                "sp_id"
            )
        )

        for player
        in (
            players
            or []
        )

        if (
            player.get(
                "sp_id"
            )
            is not None
        )
    ]


    if not sp_ids:
        return


    stat_select_sql = (
        ",\n".join(
            f"p.{stat_key}"

            for stat_key
            in QUICK_SQUAD_BASE_STAT_KEYS
        )
    )


    with connection.cursor() as cursor:

        cursor.execute(
            f"""
            SELECT
                p.sp_id,
                p.position,
                p.ovr,
                {stat_select_sql}

            FROM
                fconline_players
                AS p

            WHERE
                p.sp_id
                =
                ANY(%s)
            """,
            (
                sp_ids,
            ),
        )


        rows = (
            cursor.fetchall()
        )


    row_map = {
        int(
            row[
                "sp_id"
            ]
        ):
            row

        for row
        in rows
    }


    for player in players:

        try:

            sp_id = int(
                player.get(
                    "sp_id"
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        row = (
            row_map.get(
                sp_id
            )
        )


        if not row:
            continue


        player[
            "base_stats"
        ] = {
            stat_key:
                (
                    None

                    if (
                        row.get(
                            stat_key
                        )
                        is None
                    )

                    else int(
                        row[
                            stat_key
                        ]
                    )
                )

            for stat_key
            in QUICK_SQUAD_BASE_STAT_KEYS
        }


        if not (
            player.get(
                "position"
            )
        ):

            player[
                "position"
            ] = (
                row.get(
                    "position"
                )
                or ""
            )


        if not (
            player.get(
                "base_ovr"
            )
        ):

            player[
                "base_ovr"
            ] = int(
                row.get(
                    "ovr"
                )
                or 0
            )

# =========================================
# QUICK SQUAD
# ACTIVE TEAM COLOR ATTACH
# =========================================

def attach_quick_squad_active_team_colors(
    result,
):

    if not isinstance(
        result,
        dict,
    ):

        return result


    players = (
        result.get(
            "players"
        )
        or []
    )


    # =====================================
    # 최종 XI가 아니면 판정하지 않음
    # =====================================

    if (
        len(
            players
        )
        != 11
    ):

        result[
            "active_team_color_count"
        ] = 0

        result[
            "active_team_colors"
        ] = []

        result[
            "active_non_enhancement_team_color_count"
        ] = 0

        result[
            "active_enhancement_team_color_count"
        ] = 0

        result[
            "active_enhancement_team_colors"
        ] = []

        return result


    # =====================================
    # 일반 / 특성 + 강화 팀컬러
    # =====================================

    with get_db_connection() as connection:

        # =====================================
        # 11명 원본 세부 능력치
        # =====================================

        attach_quick_squad_player_base_stats(
            connection,
            players,
        )


        # =====================================
        # 일반 / 특성 팀컬러
        # =====================================

        normal_team_colors = (
            get_active_team_colors_for_squad(
                connection,
                players,
            )
        )


        # =====================================
        # 강화 팀컬러
        # =====================================

        enhancement_team_colors = (
            get_active_enhancement_team_colors_for_squad(
                connection,
                players,
            )
        )


    selected_team_color_id = int(
        result.get(
            "team_color_id"
        )
        or 0
    )


    # =====================================
    # Quick Squad에서 직접 선택한
    # 기준 팀컬러 표시
    # =====================================

    for team_color in (
        normal_team_colors
    ):

        team_color[
            "is_selected_team_color"
        ] = (
            int(
                team_color[
                    "team_color_id"
                ]
            )
            ==
            selected_team_color_id
        )


    # 강화 팀컬러는 사용자가
    # 팀 선택창에서 선택한 팀컬러가 아니다.
    for team_color in (
        enhancement_team_colors
    ):

        team_color[
            "is_selected_team_color"
        ] = False


    all_active_team_colors = (
        normal_team_colors
        +
        enhancement_team_colors
    )


    result[
        "active_non_enhancement_team_color_count"
    ] = len(
        normal_team_colors
    )


    result[
        "active_enhancement_team_color_count"
    ] = len(
        enhancement_team_colors
    )


    result[
        "active_enhancement_team_colors"
    ] = (
        enhancement_team_colors
    )


    result[
        "active_team_color_count"
    ] = len(
        all_active_team_colors
    )


    result[
        "active_team_colors"
    ] = (
        all_active_team_colors
    )


    return result

def attach_quick_squad_popularity(candidate_rows):
    candidates = [
        dict(row)
        for row in candidate_rows
    ]

    if not candidates:
        return candidates


    sp_ids = list({
        int(candidate["sp_id"])
        for candidate in candidates
    })

    season_ids = list({
        int(
            candidate.get(
                "season_id"
            )
            or
            (
                int(
                    candidate[
                        "sp_id"
                    ]
                )
                //
                1_000_000
            )
        )

        for candidate
        in candidates
    })


    # =====================================
    # 시즌 ID → 클래스명
    #
    # DB snapshot을 우선 사용하고,
    # 없는 시즌만 Nexon 메타데이터로 보완한다.
    # =====================================

    season_class_by_id = {}


    with get_db_connection() as connection:

        # =====================================
        # 저장된 시즌 클래스명
        # =====================================

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    season_id,
                    class_name

                FROM
                    fconline_season_snapshots

                WHERE
                    season_id = ANY(%s)
                """,
                (
                    season_ids,
                ),
            )


            season_snapshot_rows = (
                cursor.fetchall()
            )


        season_class_by_id.update({
            int(
                row[
                    "season_id"
                ]
            ):
                row.get(
                    "class_name"
                )

            for row
            in season_snapshot_rows
        })

        # =====================================
        # 포지션별 공식 인기 데이터
        # =====================================

        popularity_map = (
            get_latest_player_popularity_map(
                connection
            )
        )


        # =====================================
        # 생성 제한 상태
        # =====================================

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id,
                    generation_restricted,
                    source_type,
                    source_note,
                    effective_date
                FROM
                    fconline_player_generation_status
                WHERE
                    sp_id = ANY(%s)
                """,
                (
                    sp_ids,
                ),
            )

            generation_rows = (
                cursor.fetchall()
            )

    missing_season_ids = [
        season_id

        for season_id
        in season_ids

        if season_id
        not in season_class_by_id
    ]


    if missing_season_ids:

        try:

            live_season_metadata = (
                get_season_metadata()
            )


            for season_id in missing_season_ids:

                season = (
                    live_season_metadata.get(
                        season_id
                    )
                )


                if season:

                    season_class_by_id[
                        season_id
                    ] = (
                        season.get(
                            "class_name"
                        )
                    )


        except Exception as error:

            print(
                "[QUICK SQUAD SUPPLY] "
                "시즌 메타데이터 보완 실패:",
                error,
                flush=True,
            )


    popularity_by_spid = {}

    for (
        (sp_id, position),
        popularity,
    ) in popularity_map.items():

        popularity_by_spid.setdefault(
            sp_id,
            {},
        )[position] = popularity


    generation_by_spid = {
        int(row["sp_id"]): {
            "generation_restricted":
                bool(
                    row[
                        "generation_restricted"
                    ]
                ),

            "generation_status_source":
                row.get(
                    "source_type"
                ),

            "generation_status_note":
                row.get(
                    "source_note"
                ),

            "generation_status_effective_date":
                (
                    row["effective_date"].isoformat()
                    if row.get(
                        "effective_date"
                    )
                    else None
                ),
        }

        for row
        in generation_rows
    }


    for candidate in candidates:

        sp_id = int(
            candidate["sp_id"]
        )


        candidate[
            "popularity_by_position"
        ] = dict(
            popularity_by_spid.get(
                sp_id,
                {},
            )
        )

        season_id = int(
            candidate.get(
                "season_id"
            )
            or
            (
                sp_id
                //
                1_000_000
            )
        )


        class_name = (
            season_class_by_id.get(
                season_id
            )
        )


        candidate.update(
            get_supply_restriction_status(
                class_name
            )
        )


        generation = (
            generation_by_spid.get(
                sp_id
            )
        )


        if generation is None:

            candidate[
                "generation_restricted"
            ] = False

            candidate[
                "generation_status_source"
            ] = None

            candidate[
                "generation_status_note"
            ] = None

            candidate[
                "generation_status_effective_date"
            ] = None

        else:

            candidate.update(
                generation
            )


    return candidates




# =========================
# SERIES 목표 세트 수
# =========================

def get_series_target_set_count(
    series,
):

    # =========================
    # 플레이오프
    #
    # 기존 BO5 / BO7 규칙 유지
    # =========================

    if (
        series["series_type"]
        == "플레이오프"
    ):

        best_of = (
            series.get(
                "best_of"
            )
        )


        if best_of is None:

            raise RuntimeError(
                "플레이오프 세트 정보가 없습니다."
            )


        return int(
            best_of
        )


    # =========================
    # 프리시즌 / 정규리그
    # =========================

    target_set_count = int(
        series.get(
            "target_set_count"
        )
        or 3
    )


    if target_set_count not in (
        1,
        2,
        3,
    ):

        raise RuntimeError(
            (
                "올바르지 않은 SERIES "
                f"세트 수입니다: "
                f"{target_set_count}"
            )
        )


    return target_set_count

# =========================
# POINTS
# =========================

def change_user_points(
    cursor,
    user_id: int,
    amount: int,
    transaction_type: str,
    reference_type: str | None = None,
    reference_id: int | None = None,
    description: str | None = None,
):

    if amount == 0:

        raise ValueError(
            "포인트 변동 금액은 "
            "0일 수 없습니다."
        )


    # =========================
    # 사용자 행 잠금
    # =========================

    cursor.execute(
        """
        SELECT
            id,
            points

        FROM users

        WHERE id = %s

        FOR UPDATE
        """,
        (
            user_id,
        ),
    )


    user = (
        cursor.fetchone()
    )


    if not user:

        raise HTTPException(
            status_code=404,
            detail=(
                "사용자를 찾을 수 없습니다."
            ),
        )


    current_balance = int(
        user["points"]
    )


    new_balance = (
        current_balance
        + amount
    )


    # =========================
    # 잔액 부족 방지
    # =========================

    if new_balance < 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "보유 포인트가 부족합니다."
            ),
        )


    # =========================
    # 현재 잔액 수정
    # =========================

    cursor.execute(
        """
        UPDATE users

        SET
            points = %s,
            updated_at = NOW()

        WHERE id = %s
        """,
        (
            new_balance,
            user_id,
        ),
    )


    # =========================
    # 거래 원장 기록
    # =========================

    cursor.execute(
        """
        INSERT INTO point_transactions (
            user_id,
            amount,
            balance_after,
            transaction_type,
            reference_type,
            reference_id,
            description
        )

        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )

        RETURNING
            id,
            created_at
        """,
        (
            user_id,
            amount,
            new_balance,
            transaction_type,
            reference_type,
            reference_id,
            description,
        ),
    )


    transaction = (
        cursor.fetchone()
    )


    return {
        "transaction_id":
            transaction["id"],

        "amount":
            amount,

        "balance_before":
            current_balance,

        "balance_after":
            new_balance,

        "transaction_type":
            transaction_type,

        "reference_type":
            reference_type,

        "reference_id":
            reference_id,

        "description":
            description,

        "created_at":
            transaction["created_at"],
    }

PENALTY_SHOOTOUT_GOAL_TIME_MIN = (
    (2 ** 24) * 4
)


def get_match_special_goal_stats(
    match_info,
):

    shoot = (
        match_info.get(
            "shoot"
        )
        or {}
    )


    # =========================
    # 자책골
    #
    # FC Online API에서는
    # 선수별이 아니라 참가자 단위
    # =========================

    own_goals = int(
        shoot.get(
            "ownGoal",
            0,
        )
        or 0
    )


    # =========================
    # PK 득점 선수
    #
    # shootDetail
    # type = 9   → PK
    # result = 3 → 득점
    #
    # 승부차기는 제외
    # =========================

    penalty_goals_by_sp_id = {}


    for shot in (
        match_info.get(
            "shootDetail"
        )
        or []
    ):

        try:

            shot_type = int(
                shot.get(
                    "type",
                    0,
                )
                or 0
            )

            shot_result = int(
                shot.get(
                    "result",
                    0,
                )
                or 0
            )

            goal_time = int(
                shot.get(
                    "goalTime",
                    0,
                )
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if shot_type != 9:
            continue


        if shot_result != 3:
            continue


        # =========================
        # 승부차기 제외
        # =========================

        if (
            goal_time
            >=
            PENALTY_SHOOTOUT_GOAL_TIME_MIN
        ):

            continue


        sp_id = (
            shot.get(
                "spId"
            )
        )


        if sp_id is None:
            continue


        try:

            sp_id = int(
                sp_id
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        penalty_goals_by_sp_id[
            sp_id
        ] = (
            penalty_goals_by_sp_id.get(
                sp_id,
                0,
            )
            + 1
        )


    return {
        "own_goals":
            own_goals,

        "penalty_goals_by_sp_id":
            penalty_goals_by_sp_id,
    }


def save_series_set_squad_players(
    series_id,
    team_a_id,
    nickname_a,
    team_b_id,
    nickname_b,
    detected_matches,
):

    spid_metadata = (
        get_spid_metadata()
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES SET ID
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    set_number

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )


            series_sets = (
                cursor.fetchall()
            )


            set_id_map = {
                int(
                    series_set[
                        "set_number"
                    ]
                ):
                    series_set[
                        "id"
                    ]

                for series_set
                in series_sets
            }


            # =========================
            # 기존 Snapshot 초기화
            # =========================

            cursor.execute(
                """
                DELETE FROM
                    series_set_squad_players

                WHERE series_set_id IN (
                    SELECT id

                    FROM series_sets

                    WHERE series_id = %s
                )
                """,
                (
                    series_id,
                ),
            )


            inserted_count = 0
            ensured_season_ids = set()


            # =========================
            # SET별 저장
            # =========================

            for (
                set_number,
                detected_match,
            ) in enumerate(
                detected_matches,
                start=1,
            ):

                series_set_id = (
                    set_id_map.get(
                        set_number
                    )
                )


                if series_set_id is None:

                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"{set_number}세트의 "
                            "DB 정보를 찾을 수 없습니다."
                        ),
                    )


                match_data = (
                    detected_match[
                        "data"
                    ]
                )


                participant_map = {
                    match_info[
                        "nickname"
                    ]:
                        match_info

                    for match_info
                    in match_data[
                        "matchInfo"
                    ]
                }


                team_a_match_info = (
                    participant_map.get(
                        nickname_a
                    )
                )

                team_b_match_info = (
                    participant_map.get(
                        nickname_b
                    )
                )


                if (
                    team_a_match_info
                    is None
                    or
                    team_b_match_info
                    is None
                ):

                    raise HTTPException(
                        status_code=500,
                        detail=(
                            f"{set_number}세트의 "
                            "참가자 경기 정보를 "
                            "찾을 수 없습니다."
                        ),
                    )


                # =========================
                # 자책골 / PK 분석
                # =========================

                team_a_special = (
                    get_match_special_goal_stats(
                        team_a_match_info
                    )
                )

                team_b_special = (
                    get_match_special_goal_stats(
                        team_b_match_info
                    )
                )


                # =========================
                # 팀 단위 자책골 저장
                # =========================

                cursor.execute(
                    """
                    UPDATE series_sets

                    SET
                        team_a_own_goals = %s,
                        team_b_own_goals = %s

                    WHERE id = %s
                    """,
                    (
                        team_a_special[
                            "own_goals"
                        ],

                        team_b_special[
                            "own_goals"
                        ],

                        series_set_id,
                    ),
                )


                squad_sides = [
                    (
                        "team_a",
                        team_a_id,
                        nickname_a,
                        team_a_match_info,
                        team_a_special,
                    ),
                    (
                        "team_b",
                        team_b_id,
                        nickname_b,
                        team_b_match_info,
                        team_b_special,
                    ),
                ]


                for (
                    side,
                    participant_id,
                    nickname,
                    match_info,
                    special_stats,
                ) in squad_sides:

                    penalty_goals_by_sp_id = (
                        special_stats[
                            "penalty_goals_by_sp_id"
                        ]
                    )


                    for (
                        source_order,
                        player,
                    ) in enumerate(
                        match_info[
                            "player"
                        ]
                    ):

                        status = (
                            player[
                                "status"
                            ]
                        )


                        sp_id = int(
                            player[
                                "spId"
                            ]
                        )


                        season_id = (
                            sp_id
                            // 1_000_000
                        )


                        if (
                            season_id
                            not in
                            ensured_season_ids
                        ):

                            ensure_fconline_season_snapshot(
                                sp_id
                            )

                            ensured_season_ids.add(
                                season_id
                            )


                        player_name = (
                            get_player_name(
                                sp_id,
                                spid_metadata,
                            )
                        )


                        penalty_goals = int(
                            penalty_goals_by_sp_id.get(
                                sp_id,
                                0,
                            )
                        )


                        cursor.execute(
                            """
                            INSERT INTO
                                series_set_squad_players (
                                    series_set_id,
                                    participant_id,
                                    side,
                                    source_order,

                                    sp_id,
                                    player_name,

                                    sp_position,
                                    sp_grade,

                                    rating,
                                    goals,
                                    penalty_goals,
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
                                %s,
                                %s,
                                %s,

                                %s
                            )
                            """,
                            (
                                series_set_id,
                                participant_id,
                                side,
                                source_order,

                                sp_id,
                                player_name,

                                player[
                                    "spPosition"
                                ],

                                player[
                                    "spGrade"
                                ],

                                float(
                                    status[
                                        "spRating"
                                    ]
                                ),

                                int(
                                    status.get(
                                        "goal",
                                        0,
                                    )
                                    or 0
                                ),

                                penalty_goals,

                                int(
                                    status.get(
                                        "assist",
                                        0,
                                    )
                                    or 0
                                ),

                                get_player_image_url(
                                    sp_id
                                ),
                            ),
                        )


                        inserted_count += 1


        connection.commit()


    return inserted_count


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
            # USERS
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,

                    email VARCHAR(255)
                        NOT NULL
                        UNIQUE,

                    password_hash TEXT
                        NOT NULL,

                    nickname VARCHAR(50)
                        NOT NULL
                        UNIQUE,

                    points INTEGER
                        NOT NULL
                        DEFAULT 0,

                    is_admin BOOLEAN
                        NOT NULL
                        DEFAULT FALSE,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT users_points_check
                    CHECK (
                        points >= 0
                    )
                )
                """
            )

            # =========================
            # ATTENDANCE RECORDS
            # 출석체크 기록
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    attendance_records (
                        id BIGSERIAL PRIMARY KEY,

                        user_id BIGINT
                            NOT NULL
                            REFERENCES users(id)
                            ON DELETE CASCADE,

                        attendance_date DATE
                            NOT NULL,

                        streak_count INTEGER
                            NOT NULL
                            DEFAULT 1,

                        base_reward_points INTEGER
                            NOT NULL
                            DEFAULT 0,

                        streak_bonus_points INTEGER
                            NOT NULL
                            DEFAULT 0,

                        reward_points INTEGER
                            NOT NULL
                            DEFAULT 0,

                        created_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW(),

                        CONSTRAINT
                            attendance_streak_count_check
                        CHECK (
                            streak_count >= 1
                        ),

                        CONSTRAINT
                            attendance_reward_points_check
                        CHECK (
                            base_reward_points >= 0
                            AND
                            streak_bonus_points >= 0
                            AND
                            reward_points >= 0
                        )
                    )
                """
            )


            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_attendance_user_date

                ON attendance_records (
                    user_id,
                    attendance_date
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_attendance_user_date

                ON attendance_records (
                    user_id,
                    attendance_date DESC
                )
                """
            )

            # =========================
            # POINT TRANSACTIONS
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS point_transactions (
                    id BIGSERIAL PRIMARY KEY,

                    user_id BIGINT
                        NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    amount INTEGER
                        NOT NULL,

                    balance_after INTEGER
                        NOT NULL,

                    transaction_type VARCHAR(50)
                        NOT NULL,

                    reference_type VARCHAR(50),

                    reference_id BIGINT,

                    description TEXT,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT
                        point_transactions_balance_check
                    CHECK (
                        balance_after >= 0
                    ),

                    CONSTRAINT
                        point_transactions_amount_check
                    CHECK (
                        amount <> 0
                    )
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_point_transactions_user_id

                ON point_transactions (
                    user_id
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_point_transactions_created_at

                ON point_transactions (
                    created_at
                )
                """
            )

            # =========================
            # POINT SHOP PRODUCTS
            # 교환소 상품
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    point_shop_products (
                        id BIGSERIAL PRIMARY KEY,

                        name VARCHAR(100)
                            NOT NULL,

                        category VARCHAR(50),

                        description TEXT,

                        price_points INTEGER
                            NOT NULL,

                        image_url TEXT,

                        is_active BOOLEAN
                            NOT NULL
                            DEFAULT TRUE,

                        sort_order INTEGER
                            NOT NULL
                            DEFAULT 0,

                        created_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW(),

                        updated_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW(),

                        CONSTRAINT
                            point_shop_products_price_check
                        CHECK (
                            price_points > 0
                        )
                    )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_point_shop_products_active

                ON point_shop_products (
                    is_active,
                    sort_order,
                    id
                )
                """
            )


            # =========================
            # POINT SHOP EXCHANGES
            # 상품 교환 내역
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    point_shop_exchanges (
                        id BIGSERIAL PRIMARY KEY,

                        user_id BIGINT
                            NOT NULL
                            REFERENCES users(id)
                            ON DELETE CASCADE,

                        product_id BIGINT
                            NOT NULL
                            REFERENCES point_shop_products(id),

                        product_name VARCHAR(100)
                            NOT NULL,

                        price_points INTEGER
                            NOT NULL,

                        status VARCHAR(20)
                            NOT NULL
                            DEFAULT 'requested',

                        created_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW(),

                        completed_at TIMESTAMPTZ,

                        CONSTRAINT
                            point_shop_exchanges_price_check
                        CHECK (
                            price_points > 0
                        ),

                        CONSTRAINT
                            point_shop_exchanges_status_check
                        CHECK (
                            status IN (
                                'requested',
                                'completed',
                                'cancelled'
                            )
                        )
                    )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_point_shop_exchanges_user

                ON point_shop_exchanges (
                    user_id,
                    created_at DESC,
                    id DESC
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_point_shop_exchanges_status

                ON point_shop_exchanges (
                    status,
                    created_at ASC
                )
                """
            )

            # =========================
            # USER SESSIONS
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id BIGSERIAL PRIMARY KEY,

                    user_id BIGINT
                        NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    token_hash VARCHAR(64)
                        NOT NULL
                        UNIQUE,

                    expires_at TIMESTAMPTZ
                        NOT NULL,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_user_sessions_user_id

                ON user_sessions (
                    user_id
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_user_sessions_expires_at

                ON user_sessions (
                    expires_at
                )
                """
            )

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

                    include_extra_time_result BOOLEAN
                        NOT NULL
                        DEFAULT FALSE,

                    scheduled_date DATE,

                    round_number INTEGER,

                    fixture_number INTEGER,

                    playoff_stage VARCHAR(20),

                    best_of INTEGER,

                    wins_required INTEGER,

                    started_at TIMESTAMPTZ,

                    completed_at TIMESTAMPTZ,

                    cancelled_at TIMESTAMPTZ,

                    finished_at TIMESTAMPTZ,

                    stats_sync_status VARCHAR(20)
                        NOT NULL
                        DEFAULT 'pending',

                    status VARCHAR(20)
                        NOT NULL
                        DEFAULT 'scheduled',

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT series_check
                    CHECK (
                        team_a_id <> team_b_id
                    ),

                    CONSTRAINT series_series_type_check
                    CHECK (
                        series_type IN (
                            '프리시즌',
                            '정규리그',
                            '플레이오프'
                        )
                    ),

                    CONSTRAINT series_status_check
                    CHECK (
                        status IN (
                            'scheduled',
                            'active',
                            'completed',
                            'cancelled'
                        )
                    ),

                    CONSTRAINT chk_series_stats_sync_status
                    CHECK (
                        stats_sync_status IN (
                            'pending',
                            'synced',
                            'conflict'
                        )
                    ),

                    CONSTRAINT chk_series_playoff_config
                    CHECK (
                        (
                            series_type IN (
                                '프리시즌',
                                '정규리그'
                            )

                            AND playoff_stage IS NULL
                            AND best_of IS NULL
                            AND wins_required IS NULL
                        )

                        OR

                        (
                            series_type = '플레이오프'

                            AND playoff_stage IS NOT NULL
                            AND best_of IS NOT NULL
                            AND wins_required IS NOT NULL

                            AND (
                                (
                                    playoff_stage IN (
                                        '준플레이오프',
                                        '플레이오프'
                                    )

                                    AND best_of = 5
                                    AND wins_required = 3
                                )

                                OR

                                (
                                    playoff_stage = '결승시리즈'

                                    AND best_of = 7
                                    AND wins_required = 4
                                )
                            )
                        )
                    )
                )
                """
            )

            # =========================
            # PLAYOFF 경기 방식 확장
            #
            # 3판 2선승
            # 5판 3선승
            # 7판 4선승
            # =========================

            cursor.execute(
                """
                ALTER TABLE series

                DROP CONSTRAINT IF EXISTS
                    chk_series_playoff_config
                """
            )


            cursor.execute(
                """
                ALTER TABLE series

                ADD CONSTRAINT
                    chk_series_playoff_config

                CHECK (
                    (
                        series_type IN (
                            '프리시즌',
                            '정규리그'
                        )

                        AND playoff_stage IS NULL
                        AND best_of IS NULL
                        AND wins_required IS NULL
                    )

                    OR

                    (
                        series_type = '플레이오프'

                        AND playoff_stage IN (
                            '준플레이오프',
                            '플레이오프',
                            '결승시리즈'
                        )

                        AND (
                            (
                                best_of = 3
                                AND wins_required = 2
                            )

                            OR

                            (
                                best_of = 5
                                AND wins_required = 3
                            )

                            OR

                            (
                                best_of = 7
                                AND wins_required = 4
                            )
                        )
                    )
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE series

                ADD COLUMN IF NOT EXISTS
                    include_extra_time_result BOOLEAN
                    NOT NULL
                    DEFAULT FALSE
                """
            )

            # =========================
            # SERIES 목표 세트 수
            #
            # 프리시즌 / 정규리그
            # 1 ~ 3세트 운영용
            #
            # 기존 데이터는 3세트로 보존
            # =========================

            cursor.execute(
                """
                ALTER TABLE series

                ADD COLUMN IF NOT EXISTS
                    target_set_count SMALLINT
                """
            )


            cursor.execute(
                """
                UPDATE series

                SET target_set_count = 3

                WHERE target_set_count
                    IS NULL
                """
            )


            cursor.execute(
                """
                ALTER TABLE series

                ALTER COLUMN
                    target_set_count

                SET DEFAULT 3
                """
            )


            cursor.execute(
                """
                ALTER TABLE series

                ALTER COLUMN
                    target_set_count

                SET NOT NULL
                """
            )


            # =========================
            # AI 경기 예측 Snapshot
            #
            # 경기 시작 순간의 예측값을
            # 이후에도 역사 데이터로 보존
            # =========================

            cursor.execute(
                """
                ALTER TABLE series

                ADD COLUMN IF NOT EXISTS
                    ai_prediction_snapshot JSONB,

                ADD COLUMN IF NOT EXISTS
                    ai_prediction_snapshot_at
                    TIMESTAMPTZ
                """
            )


            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_series_regular_fixture_number

                ON series (
                    fixture_number
                )

                WHERE
                    series_type = '정규리그'
                """
            )

            # =========================
            # PLAYOFF SETTINGS
            #
            # SERIES 생성 전에도
            # 플레이오프 날짜 / 경기 방식
            # 관리 가능
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    playoff_settings (
                        playoff_stage VARCHAR(20)
                            PRIMARY KEY,

                        scheduled_date DATE
                            NOT NULL,

                        best_of INTEGER
                            NOT NULL,

                        wins_required INTEGER
                            NOT NULL,

                        updated_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW(),

                        CONSTRAINT
                            chk_playoff_settings_stage

                        CHECK (
                            playoff_stage IN (
                                '준플레이오프',
                                '플레이오프',
                                '결승시리즈'
                            )
                        ),

                        CONSTRAINT
                            chk_playoff_settings_format

                        CHECK (
                            (
                                best_of = 3
                                AND
                                wins_required = 2
                            )

                            OR

                            (
                                best_of = 5
                                AND
                                wins_required = 3
                            )

                            OR

                            (
                                best_of = 7
                                AND
                                wins_required = 4
                            )
                        )
                    )
                """
            )

            cursor.execute(
                """
                INSERT INTO playoff_settings (
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required
                )

                VALUES
                    (
                        '준플레이오프',
                        DATE '2026-10-03',
                        5,
                        3
                    ),

                    (
                        '플레이오프',
                        DATE '2026-10-06',
                        5,
                        3
                    ),

                    (
                        '결승시리즈',
                        DATE '2026-10-10',
                        7,
                        4
                    )

                ON CONFLICT (
                    playoff_stage
                )

                DO NOTHING
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
                        UNIQUE,

                    played_at TIMESTAMPTZ
                        NOT NULL,

                    team_a_score INTEGER
                        NOT NULL,

                    team_b_score INTEGER
                        NOT NULL,

                    score_source VARCHAR(20)
                        NOT NULL
                        DEFAULT 'nexon',

                    winner_side VARCHAR(10),

                    result_method VARCHAR(20),

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    UNIQUE (
                        series_id,
                        set_number
                    ),

                    CONSTRAINT series_sets_set_number_check
                    CHECK (
                        set_number
                        BETWEEN 1 AND 7
                    ),

                    CONSTRAINT series_sets_team_a_score_check
                    CHECK (
                        team_a_score >= 0
                    ),

                    CONSTRAINT series_sets_team_b_score_check
                    CHECK (
                        team_b_score >= 0
                    ),

                    CONSTRAINT chk_series_sets_score_source
                    CHECK (
                        score_source IN (
                            'nexon',
                            'manual'
                        )
                    ),

                    CONSTRAINT chk_series_sets_winner_side
                    CHECK (
                        winner_side IS NULL

                        OR winner_side IN (
                            'team_a',
                            'team_b',
                            'draw'
                        )
                    )
                )
                """
            )

            # =========================
            # SERIES 세트별 스쿼드 Snapshot
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS series_set_squad_players (
                    id BIGSERIAL PRIMARY KEY,

                    series_set_id BIGINT
                        NOT NULL
                        REFERENCES series_sets(id)
                        ON DELETE CASCADE,

                    participant_id BIGINT
                        NOT NULL
                        REFERENCES participants(id),

                    side VARCHAR(10)
                        NOT NULL,

                    source_order INTEGER
                        NOT NULL,

                    sp_id BIGINT
                        NOT NULL,

                    player_name VARCHAR(100)
                        NOT NULL,

                    sp_position INTEGER
                        NOT NULL,

                    sp_grade INTEGER
                        NOT NULL,

                    rating NUMERIC(5, 2)
                        NOT NULL,

                    goals INTEGER
                        NOT NULL
                        DEFAULT 0,

                    assists INTEGER
                        NOT NULL
                        DEFAULT 0,

                    image_url TEXT,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT chk_series_set_squad_side
                    CHECK (
                        side IN (
                            'team_a',
                            'team_b'
                        )
                    ),

                    CONSTRAINT chk_series_set_squad_source_order
                    CHECK (
                        source_order >= 0
                    ),

                    CONSTRAINT chk_series_set_squad_rating
                    CHECK (
                        rating >= 0
                    ),

                    CONSTRAINT chk_series_set_squad_goals
                    CHECK (
                        goals >= 0
                    ),

                    CONSTRAINT chk_series_set_squad_assists
                    CHECK (
                        assists >= 0
                    ),

                    UNIQUE (
                        series_set_id,
                        side,
                        source_order
                    )
                )
                """
            )

            # =========================
            # SERIES 특수 득점
            # 자책골
            # =========================

            cursor.execute(
                """
                ALTER TABLE series_sets

                ADD COLUMN IF NOT EXISTS
                    team_a_own_goals INTEGER
                    NOT NULL
                    DEFAULT 0,

                ADD COLUMN IF NOT EXISTS
                    team_b_own_goals INTEGER
                    NOT NULL
                    DEFAULT 0
                """
            )

            # =========================
            # 선수별 PK 득점
            # =========================

            cursor.execute(
                """
                ALTER TABLE
                    series_set_squad_players

                ADD COLUMN IF NOT EXISTS
                    penalty_goals INTEGER
                    NOT NULL
                    DEFAULT 0
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

            # =========================
            # COMMUNITY NOTICE
            # =========================

            cursor.execute(
                """
                ALTER TABLE community_posts

                ADD COLUMN IF NOT EXISTS
                    is_notice BOOLEAN
                    NOT NULL
                    DEFAULT FALSE
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_community_posts_notice

                ON community_posts (
                    is_notice,
                    created_at DESC
                )
                """
            )

            # =========================
            # FC ONLINE 선수도감
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS fconline_players (
                    sp_id BIGINT
                        PRIMARY KEY,

                    player_name VARCHAR(100)
                        NOT NULL,

                    season_id INTEGER
                        NOT NULL,

                    position VARCHAR(10),

                    salary SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    ovr SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    height SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    weight SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    left_foot SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    right_foot SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    nation_id INTEGER,

                    nation_name VARCHAR(100),

                    sprint_speed SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    acceleration SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    finishing SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    shot_power SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    long_shots SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    positioning SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    volleys SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    penalties SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    short_pass SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    vision SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    crossing SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    long_pass SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    free_kick SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    curve SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    dribbling SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    ball_control SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    agility SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    balance SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    reactions SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    marking SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    tackle SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    interceptions SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    heading SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    sliding_tackle SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    strength SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    stamina SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    aggression SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    jumping SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    composure SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    gk_diving SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    gk_handling SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    gk_kick SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    gk_reflexes SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    gk_positioning SMALLINT
                        NOT NULL
                        DEFAULT 0,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE fconline_players

                ADD COLUMN IF NOT EXISTS
                    skill_moves SMALLINT
                    NOT NULL
                    DEFAULT 0
                """
            )


            cursor.execute(
                """
                ALTER TABLE fconline_players

                ADD COLUMN IF NOT EXISTS
                    traits TEXT[]
                    NOT NULL
                    DEFAULT '{}'::TEXT[]
                """
            )

            # =========================
            # FC ONLINE 선수 이미지 URL
            # =========================

            cursor.execute(
                """
                ALTER TABLE
                    fconline_players

                ADD COLUMN IF NOT EXISTS
                    image_url TEXT
                """
            )


            # =========================
            # FC ONLINE 선수 수집 상태
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    fconline_player_sync_state (
                        sp_id BIGINT PRIMARY KEY,

                        player_name VARCHAR(100)
                            NOT NULL
                            DEFAULT '',

                        status VARCHAR(20)
                            NOT NULL
                            DEFAULT 'pending',

                        attempt_count INTEGER
                            NOT NULL
                            DEFAULT 0,

                        last_error TEXT,

                        started_at TIMESTAMPTZ,

                        last_attempt_at TIMESTAMPTZ,

                        completed_at TIMESTAMPTZ,

                        updated_at TIMESTAMPTZ
                            NOT NULL
                            DEFAULT NOW()
                    )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_player_sync_state_status

                ON fconline_player_sync_state (
                    status
                )
                """
            )


            # 기존에 이미 저장된 테스트 선수는
            # completed 상태로 등록
            cursor.execute(
                """
                INSERT INTO
                    fconline_player_sync_state (
                        sp_id,
                        player_name,
                        status,
                        attempt_count,
                        started_at,
                        last_attempt_at,
                        completed_at,
                        updated_at
                    )

                SELECT
                    sp_id,
                    player_name,
                    'completed',
                    1,
                    created_at,
                    updated_at,
                    updated_at,
                    updated_at

                FROM
                    fconline_players

                ON CONFLICT (
                    sp_id
                )

                DO NOTHING
                """
            )


            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    fconline_player_nations (
                        sp_id BIGINT PRIMARY KEY,
                        nation_id INTEGER NOT NULL,
                        nation_name VARCHAR(100) NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                            DEFAULT NOW()
                    )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_player_nations_nation_id

                ON fconline_player_nations (
                    nation_id
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    fconline_nation_sync_state (
                        nation_id INTEGER PRIMARY KEY,
                        nation_name VARCHAR(100) NOT NULL,

                        status VARCHAR(20) NOT NULL
                            DEFAULT 'pending',

                        card_count INTEGER NOT NULL
                            DEFAULT 0,

                        last_error TEXT,

                        started_at TIMESTAMPTZ,
                        completed_at TIMESTAMPTZ,

                        updated_at TIMESTAMPTZ NOT NULL
                            DEFAULT NOW()
                    )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_nation_sync_state_status

                ON fconline_nation_sync_state (
                    status
                )
                """
            )

            # =========================
            # FC ONLINE 선수 소속팀
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    fconline_player_teams (

                    id BIGSERIAL
                        PRIMARY KEY,

                    sp_id BIGINT
                        NOT NULL
                        REFERENCES fconline_players(
                            sp_id
                        )
                        ON DELETE CASCADE,

                    team_name VARCHAR(150)
                        NOT NULL,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    UNIQUE (
                        sp_id,
                        team_name
                    )
                )
                """
            )

            # =========================
            # FC ONLINE 팀컬러 ID
            # =========================

            cursor.execute(
                """
                ALTER TABLE
                    fconline_player_teams

                ADD COLUMN IF NOT EXISTS
                    team_color_id INTEGER
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_player_teams_color_id

                ON fconline_player_teams (
                    team_color_id
                )
                """
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_players_name

                ON fconline_players (
                    player_name
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_players_season

                ON fconline_players (
                    season_id
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_players_position

                ON fconline_players (
                    position
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_players_nation

                ON fconline_players (
                    nation_name
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_fconline_player_teams_name

                ON fconline_player_teams (
                    team_name
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
            "끠끼의팬텀드리블",
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

# =========================
# FC Online 경기 상세 조회
# =========================

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
# FC ONLINE SCORE MODE
#
# goalTime 구간
#
# 0 = 전반
# 1 = 후반
# 2 = 연장 전반
# 3 = 연장 후반
# 4 = 승부차기
# =========================

NEXON_GOAL_TIME_BLOCK = (
    2 ** 24
)

def get_match_score_pair(
    match_data,
    nickname_a,
    nickname_b,
    include_extra_time_result=False,
):

    match_info_list = (
        match_data.get(
            "matchInfo",
            [],
        )
        or []
    )


    participant_map = {}


    for match_info in match_info_list:

        nickname = (
            str(
                match_info.get(
                    "nickname",
                    ""
                )
                or ""
            )
            .strip()
        )


        if not nickname:
            continue


        participant_map[
            nickname
        ] = match_info


    normalized_nickname_a = (
        str(
            nickname_a
            or ""
        )
        .strip()
    )


    normalized_nickname_b = (
        str(
            nickname_b
            or ""
        )
        .strip()
    )


    team_a_info = (
        participant_map.get(
            normalized_nickname_a
        )
    )


    team_b_info = (
        participant_map.get(
            normalized_nickname_b
        )
    )


    if (
        team_a_info is None
        or
        team_b_info is None
    ):

        print(
            "[FCL SCORE LOOKUP ERROR]",
            {
                "requested_a":
                    normalized_nickname_a,

                "requested_b":
                    normalized_nickname_b,

                "match_nicknames":
                    list(
                        participant_map.keys()
                    ),

                "match_id":
                    match_data.get(
                        "matchId"
                    ),
            },
            flush=True,
        )


        return None


    def get_total_score(
        match_info
    ):

        shoot = (
            match_info.get(
                "shoot",
                {},
            )
            or {}
        )


        goal_total_display = (
            shoot.get(
                "goalTotalDisplay"
            )
        )


        if (
            goal_total_display
            is not None
        ):

            try:

                return int(
                    goal_total_display
                )

            except (
                TypeError,
                ValueError,
            ):

                pass


        return int(
            shoot.get(
                "goalTotal",
                0,
            )
            or 0
        )


    team_a_total_score = (
        get_total_score(
            team_a_info
        )
    )


    team_b_total_score = (
        get_total_score(
            team_b_info
        )
    )


    # =========================
    # 연장 포함
    # =========================

    if include_extra_time_result:

        return (
            team_a_total_score,
            team_b_total_score,
        )


    # =========================
    # 정규시간만
    #
    # 최종 표시 점수에서
    # 연장 득점만 제거
    # =========================

    def count_extra_time_goals(
        match_info
    ):

        extra_time_goals = 0


        for shot in (
            match_info.get(
                "shootDetail",
                [],
            )
            or []
        ):

            try:

                shot_result = int(
                    shot.get(
                        "result",
                        0,
                    )
                    or 0
                )


                goal_time = int(
                    shot.get(
                        "goalTime",
                        0,
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):

                continue


            if shot_result != 3:
                continue


            period_index = (
                goal_time
                //
                NEXON_GOAL_TIME_BLOCK
            )


            if period_index in (
                2,
                3,
            ):

                extra_time_goals += 1


        return extra_time_goals


    team_a_extra_goals = (
        count_extra_time_goals(
            team_a_info
        )
    )


    team_b_extra_goals = (
        count_extra_time_goals(
            team_b_info
        )
    )


    team_a_regulation_score = max(
        0,
        (
            team_a_total_score
            -
            team_a_extra_goals
        ),
    )


    team_b_regulation_score = max(
        0,
        (
            team_b_total_score
            -
            team_b_extra_goals
        ),
    )


    return (
        team_a_regulation_score,
        team_b_regulation_score,
    )


def get_total_score(
    match_info
):

    shoot = (
        match_info.get(
            "shoot",
            {},
        )
        or {}
    )


    # =========================
    # 실제 경기 종료 화면 점수
    #
    # goalTotal:
    #   선수들의 직접 득점 합계
    #
    # goalTotalDisplay:
    #   자책골까지 포함된
    #   실제 경기 표시 점수
    #
    # FCL 경기 결과 비교에는
    # goalTotalDisplay를 사용한다.
    # =========================

    goal_total_display = (
        shoot.get(
            "goalTotalDisplay"
        )
    )


    if (
        goal_total_display
        is not None
    ):

        return int(
            goal_total_display
            or 0
        )


    # =========================
    # 구형 / 비정상 API 데이터
    # fallback
    # =========================

    return int(
        shoot.get(
            "goalTotal",
            0,
        )
        or 0
    )


    team_a_total_score = (
        get_total_score(
            team_a_info
        )
    )


    team_b_total_score = (
        get_total_score(
            team_b_info
        )
    )


    # =========================
    # 연장 포함
    #
    # 실제 경기 표시 점수 사용
    # goalTotalDisplay 우선
    # =========================

    if include_extra_time_result:

        return (
            team_a_total_score,
            team_b_total_score,
        )


    # =========================
    # 정규시간만
    #
    # goalTotal에서
    # 연장전 득점만 제거
    #
    # 승부차기 득점은 goalTotal과
    # 별도로 관리되므로 제거 대상 아님
    # =========================

    def count_extra_time_goals(
        match_info
    ):

        extra_time_goals = 0


        for shot in (
            match_info.get(
                "shootDetail",
                [],
            )
            or []
        ):

            try:

                shot_result = int(
                    shot.get(
                        "result",
                        0,
                    )
                    or 0
                )


                goal_time = int(
                    shot.get(
                        "goalTime",
                        0,
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError,
            ):

                continue


            # result 3 = GOAL

            if shot_result != 3:
                continue


            period_index = (
                goal_time
                //
                NEXON_GOAL_TIME_BLOCK
            )


            # 2 = 연장 전반
            # 3 = 연장 후반

            if period_index in (
                2,
                3,
            ):

                extra_time_goals += 1


        return extra_time_goals


    team_a_extra_goals = (
        count_extra_time_goals(
            team_a_info
        )
    )


    team_b_extra_goals = (
        count_extra_time_goals(
            team_b_info
        )
    )


    team_a_regulation_score = max(
        0,
        (
            team_a_total_score
            -
            team_a_extra_goals
        ),
    )


    team_b_regulation_score = max(
        0,
        (
            team_b_total_score
            -
            team_b_extra_goals
        ),
    )


    return (
        team_a_regulation_score,
        team_b_regulation_score,
    )

def get_match_winner_side(
    match_data,
    nickname_a,
    nickname_b,
    series_type=None,
    include_extra_time_result=False,
):

    participant_map = {
        match_info["nickname"]:
            match_info

        for match_info
        in match_data.get(
            "matchInfo",
            [],
        )
    }


    team_a_info = participant_map.get(
        nickname_a
    )


    team_b_info = participant_map.get(
        nickname_b
    )


    if (
        team_a_info is None
        or
        team_b_info is None
    ):

        return None


    # =========================
    # 플레이오프는 기존처럼
    # 항상 최종 승패 사용
    #
    # 프리시즌은 옵션에 따름
    # =========================

    use_final_result = (
        series_type
        == "플레이오프"
        or
        bool(
            include_extra_time_result
        )
    )


    score_pair = (
        get_match_score_pair(
            match_data,
            nickname_a,
            nickname_b,
            include_extra_time_result=
                use_final_result,
        )
    )


    if score_pair is None:
        return None


    (
        team_a_score,
        team_b_score,
    ) = score_pair


    # =========================
    # 점수로 승자 결정
    # =========================

    if (
        team_a_score
        >
        team_b_score
    ):

        return "team_a"


    if (
        team_b_score
        >
        team_a_score
    ):

        return "team_b"


    # =========================
    # 정규시간만 사용하는 경우
    #
    # 동점이면 그대로 DRAW
    # =========================

    if not use_final_result:

        return "draw"


    # =========================
    # 연장 포함인데 점수도 동점
    #
    # 승부차기 승패 등은
    # NEXON matchResult 사용
    # =========================

    team_a_result = (
        team_a_info
        .get(
            "matchDetail",
            {},
        )
        .get(
            "matchResult"
        )
    )


    team_b_result = (
        team_b_info
        .get(
            "matchDetail",
            {},
        )
        .get(
            "matchResult"
        )
    )


    if (
        team_a_result == "승"
        and
        team_b_result == "패"
    ):

        return "team_a"


    if (
        team_a_result == "패"
        and
        team_b_result == "승"
    ):

        return "team_b"


    if (
        team_a_result == "무"
        and
        team_b_result == "무"
    ):

        return "draw"


    return None

# =========================
# FC ONLINE 경기 종료 방식
#
# regulation = 정규시간
# extra_time = 연장전
# penalties  = 승부차기
# draw       = 무승부
# =========================

def get_match_result_method(
    match_data,
    nickname_a,
    nickname_b,
    series_type=None,
    include_extra_time_result=False,
):

    use_final_result = (
        series_type == "플레이오프"
        or
        bool(
            include_extra_time_result
        )
    )


    regulation_score_pair = (
        get_match_score_pair(
            match_data,
            nickname_a,
            nickname_b,
            include_extra_time_result=False,
        )
    )


    if regulation_score_pair is None:
        return None


    (
        regulation_team_a_score,
        regulation_team_b_score,
    ) = regulation_score_pair


    # =========================
    # 정규시간 결과만 사용하는 경기
    # =========================

    if not use_final_result:

        if (
            regulation_team_a_score
            ==
            regulation_team_b_score
        ):

            return "draw"


        return "regulation"


    # =========================
    # 최종 스코어
    # =========================

    final_score_pair = (
        get_match_score_pair(
            match_data,
            nickname_a,
            nickname_b,
            include_extra_time_result=True,
        )
    )


    if final_score_pair is None:
        return None


    (
        final_team_a_score,
        final_team_b_score,
    ) = final_score_pair


    winner_side = (
        get_match_winner_side(
            match_data,
            nickname_a,
            nickname_b,
            series_type,
            include_extra_time_result,
        )
    )


    if winner_side is None:
        return None


    # =========================
    # 90분 안에 승부 결정
    # =========================

    if (
        regulation_team_a_score
        !=
        regulation_team_b_score
    ):

        return "regulation"


    # =========================
    # 90분 동점
    # 최종 스코어가 달라짐
    #
    # → 연장전 득점으로 결정
    # =========================

    if (
        final_team_a_score
        !=
        final_team_b_score
    ):

        return "extra_time"


    # =========================
    # 최종 스코어도 동점인데
    # 승자가 존재
    #
    # → 승부차기
    # =========================

    if winner_side in (
        "team_a",
        "team_b",
    ):

        return "penalties"


    return "draw"


# =========================
# FC Online 경기 데이터 정합성 검증
# =========================

def get_match_integrity_conflict(
    match_data,
    nickname_a,
    nickname_b,
    series_type=None,
):

    participant_map = {
        match_info["nickname"]:
            match_info

        for match_info
        in match_data.get(
            "matchInfo",
            [],
        )
    }


    team_a_info = (
        participant_map.get(
            nickname_a
        )
    )


    team_b_info = (
        participant_map.get(
            nickname_b
        )
    )


    # =========================
    # 참가자 정합성
    # =========================

    if (
        team_a_info is None
        or
        team_b_info is None
    ):

        return (
            "NEXON 경기 데이터에서 "
            "SERIES 참가자를 찾을 수 없습니다."
        )


    # =========================
    # 팀 점수 / 선수 득점 정합성
    # =========================

    for (
        nickname,
        match_info,
    ) in (
        (
            nickname_a,
            team_a_info,
        ),

        (
            nickname_b,
            team_b_info,
        ),
    ):

        shoot = (
            match_info.get(
                "shoot",
                {},
            )
        )


        goal_total = int(
            shoot.get(
                "goalTotal",
                0,
            )
            or 0
        )


        own_goal = int(
            shoot.get(
                "ownGoal",
                0,
            )
            or 0
        )


        player_goal_sum = sum(
            int(
                player
                .get(
                    "status",
                    {},
                )
                .get(
                    "goal",
                    0,
                )
                or 0
            )

            for player
            in match_info.get(
                "player",
                [],
            )
        )


        # =========================
        # 자책골이 없는 경우
        #
        # 선수 득점 합계와
        # 실제 팀 득점이 같아야 함
        # =========================

        if (
            own_goal == 0
            and
            player_goal_sum
            !=
            goal_total
        ):

            return (
                "NEXON 선수 득점 합계와 "
                "팀 득점이 일치하지 않습니다. "
                f"({nickname}: "
                f"playerGoals="
                f"{player_goal_sum}, "
                f"goalTotal={goal_total})"
            )


    # =========================
    # 플레이오프 동점 경기 검증
    # =========================

    team_a_score = int(
        team_a_info
        .get(
            "shoot",
            {},
        )
        .get(
            "goalTotal",
            0,
        )
        or 0
    )


    team_b_score = int(
        team_b_info
        .get(
            "shoot",
            {},
        )
        .get(
            "goalTotal",
            0,
        )
        or 0
    )


    if (
        series_type == "플레이오프"
        and
        team_a_score == team_b_score
    ):

        winner_side = (
            get_match_winner_side(
                match_data,
                nickname_a,
                nickname_b,
                series_type,
            )
        )


        if (
            winner_side
            not in (
                "team_a",
                "team_b",
            )
        ):

            team_a_result = (
                team_a_info
                .get(
                    "matchDetail",
                    {},
                )
                .get(
                    "matchResult"
                )
            )


            team_b_result = (
                team_b_info
                .get(
                    "matchDetail",
                    {},
                )
                .get(
                    "matchResult"
                )
            )


            return (
                "플레이오프 동점 경기의 "
                "승자를 확인할 수 없습니다. "
                f"({nickname_a}: {team_a_result}, "
                f"{nickname_b}: {team_b_result})"
            )


    return None

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
    #
    # 1 ~ 2세트 경기:
    # 최소 1세트 출전
    #
    # 3세트 이상:
    # 기존처럼 최소 2세트 출전
    # =========================

    minimum_mvp_sets = (
        1
        if len(matches) <= 2
        else 2
    )


    mvp_rankings = [
        player

        for player
        in all_player_stats

        if (
            player["sets_played"]
            >= minimum_mvp_sets
        )
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
    "서종원": "끠끼의팬텀드리블",
}

# =========================
# PREDICTIONS
# 승부예측 운영 설정
# =========================

PREDICTION_FIXED_ODDS = 2.50
PREDICTION_MAX_STAKE_POINTS = 1000

# =========================
# ATTENDANCE EVENT
# 출석체크 운영 설정
# =========================

ATTENDANCE_DAILY_REWARD = 50
ATTENDANCE_STREAK_DAYS = 7
ATTENDANCE_STREAK_BONUS = 150

# =========================
# PREDICTIONS
# 세트별 승부예측 자동 정산
# =========================

def settle_predictions_for_series(
    cursor,
    series_id: int,
):

    # =========================
    # SERIES 확인
    # =========================

    cursor.execute(
        """
        SELECT
            id,
            series_type,
            team_a_id,
            team_b_id,
            status,
            target_set_count

        FROM series

        WHERE id = %s

        FOR UPDATE
        """,
        (
            series_id,
        ),
    )


    series = cursor.fetchone()


    if not series:

        raise RuntimeError(
            "승부예측 정산 대상 SERIES를 "
            "찾을 수 없습니다."
        )


    # 정규리그만 승부예측 정산
    if (
        series["series_type"]
        != "정규리그"
    ):

        return {
            "settled": 0,
            "wins": 0,
            "losses": 0,
            "payout_points": 0,
        }


    # 완료된 경기만 정산
    if (
        series["status"]
        != "completed"
    ):

        return {
            "settled": 0,
            "wins": 0,
            "losses": 0,
            "payout_points": 0,
        }


    # =========================
    # 실제 SERIES 세트 결과
    # =========================

    target_set_count = int(
        series[
            "target_set_count"
        ]
        or 3
    )


    cursor.execute(
        """
        SELECT
            set_number,
            team_a_score,
            team_b_score

        FROM series_sets

        WHERE
            series_id = %s

            AND set_number
                BETWEEN 1 AND %s

        ORDER BY
            set_number

        FOR UPDATE
        """,
        (
            series_id,
            target_set_count,
        ),
    )


    set_rows = cursor.fetchall()


    set_map = {
        int(
            row["set_number"]
        ):
            row

        for row
        in set_rows
    }


    expected_set_numbers = set(
        range(
            1,
            target_set_count + 1,
        )
    )


    if (
        set(
            set_map.keys()
        )
        !=
        expected_set_numbers
    ):

        raise RuntimeError(
            "승부예측 정산에 필요한 "
            f"1~{target_set_count}세트 "
            "결과가 모두 존재하지 않습니다."
        )


    # =========================
    # 아직 정산되지 않은 예측
    #
    # pending만 가져오므로
    # 같은 경기 sync를 다시 눌러도
    # 중복 지급되지 않음
    # =========================

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            set_number,
            prediction_type,
            predicted_participant_id,
            stake_points,
            odds

        FROM predictions

        WHERE
            series_id = %s

            AND status =
                'pending'

        ORDER BY
            id

        FOR UPDATE
        """,
        (
            series_id,
        ),
    )


    predictions = (
        cursor.fetchall()
    )


    settled_count = 0
    win_count = 0
    loss_count = 0
    total_payout_points = 0


    for prediction in predictions:

        set_number = int(
            prediction[
                "set_number"
            ]
        )


        set_result = (
            set_map.get(
                set_number
            )
        )


        # =========================
        # 운영 방식 변경 등으로
        # 존재하지 않게 된 세트 예측
        # → 포인트 환불
        # =========================

        if set_result is None:

            refund_points = int(
                prediction[
                    "stake_points"
                ]
            )


            change_user_points(
                cursor,

                prediction[
                    "user_id"
                ],

                refund_points,

                "prediction_refund",

                reference_type=
                    "prediction",

                reference_id=
                    prediction[
                        "id"
                    ],

                description=(
                    "FCL 승부예측 "
                    f"{set_number}세트 "
                    "운영 변경 환불"
                ),
            )


            cursor.execute(
                """
                UPDATE predictions

                SET
                    status = 'refunded',
                    payout_points = %s,
                    settled_at = NOW(),
                    updated_at = NOW()

                WHERE
                    id = %s
                    AND status = 'pending'
                """,
                (
                    refund_points,
                    prediction[
                        "id"
                    ],
                ),
            )


            settled_count += 1

            continue


        team_a_score = int(
            set_result[
                "team_a_score"
            ]
        )

        team_b_score = int(
            set_result[
                "team_b_score"
            ]
        )


        # =========================
        # 실제 결과 판단
        # =========================

        if (
            team_a_score
            ==
            team_b_score
        ):

            winning_type = (
                "draw"
            )

            winning_participant_id = (
                None
            )


        elif (
            team_a_score
            >
            team_b_score
        ):

            winning_type = (
                "participant"
            )

            winning_participant_id = int(
                series[
                    "team_a_id"
                ]
            )


        else:

            winning_type = (
                "participant"
            )

            winning_participant_id = int(
                series[
                    "team_b_id"
                ]
            )


        # =========================
        # 예측 적중 여부
        # =========================

        is_win = False


        if (
            prediction[
                "prediction_type"
            ]
            ==
            "draw"

            and

            winning_type
            ==
            "draw"
        ):

            is_win = True


        elif (
            prediction[
                "prediction_type"
            ]
            ==
            "participant"

            and

            winning_type
            ==
            "participant"

            and

            int(
                prediction[
                    "predicted_participant_id"
                ]
            )
            ==
            winning_participant_id
        ):

            is_win = True


        # =========================
        # 적중
        # =========================

        if is_win:

            payout_points = int(
                prediction[
                    "stake_points"
                ]
                *
                prediction[
                    "odds"
                ]
            )


            change_user_points(
                cursor,

                prediction[
                    "user_id"
                ],

                payout_points,

                "prediction_win",

                reference_type=
                    "prediction",

                reference_id=
                    prediction[
                        "id"
                    ],

                description=(
                    "FCL 승부예측 "
                    f"{set_number}세트 적중"
                ),
            )


            prediction_status = (
                "win"
            )

            win_count += 1

            total_payout_points += (
                payout_points
            )


        # =========================
        # 실패
        # =========================

        else:

            payout_points = 0

            prediction_status = (
                "loss"
            )

            loss_count += 1


        # =========================
        # 예측 정산 완료
        # =========================

        cursor.execute(
            """
            UPDATE predictions

            SET
                status = %s,
                payout_points = %s,
                settled_at = NOW(),
                updated_at = NOW()

            WHERE
                id = %s
                AND status = 'pending'
            """,
            (
                prediction_status,
                payout_points,
                prediction[
                    "id"
                ],
            ),
        )


        settled_count += 1


    return {
        "settled":
            settled_count,

        "wins":
            win_count,

        "losses":
            loss_count,

        "payout_points":
            total_payout_points,
    }

class PointShopExchangeRequest(
    BaseModel
):
    product_id: int

class PredictionCreateRequest(
    BaseModel
): 
    series_id: int
    set_number: int
    prediction_type: str
    participant_id: int | None = None
    stake_points: int

class PredictionSettlementTestRequest(
    BaseModel
):
    series_id: int

    set1_team_a: int
    set1_team_b: int

    set2_team_a: int
    set2_team_b: int

    set3_team_a: int
    set3_team_b: int

class UserSignupRequest(
    BaseModel
):
    email: str
    password: str
    nickname: str

class UserLoginRequest(
    BaseModel
):
    email: str
    password: str

class AdminUserPointRequest(
    BaseModel
):
    amount: int
    description: str | None = None


class AdminUserRoleRequest(
    BaseModel
):
    is_admin: bool

class AdminPointShopProductCreateRequest(
    BaseModel
):
    name: str
    category: str | None = None
    description: str | None = None
    price_points: int
    image_url: str | None = None
    is_active: bool = True
    sort_order: int = 0


class AdminPointShopProductUpdateRequest(
    BaseModel
):
    name: str
    category: str | None = None
    description: str | None = None
    price_points: int
    image_url: str | None = None
    is_active: bool
    sort_order: int

class AdminCommunityPostUpdateRequest(
    BaseModel
):
    title: str
    content: str

class AdminCommunityNoticeRequest(
    BaseModel
):
    title: str
    content: str

class CommunityCommentCreateRequest(
    BaseModel
):
    content: str

class CommunityCommentUpdateRequest(
    BaseModel
):
    content: str

class AdminLoginRequest(BaseModel):
    password: str

class AdminParticipantTeamUpdateRequest(
    BaseModel
):
    current_team_name: str
    current_team_logo_path: str

class SeriesStartRequest(BaseModel):
    team_a: str
    team_b: str

    series_type: str = "프리시즌"

    scheduled_date: str | None = None

    target_set_count: int = Field(
        default=3,
        ge=1,
        le=3,
    )

    include_extra_time_result: bool = False

class ManualSeriesCompleteRequest(BaseModel):

    # 1세트는 항상 존재
    set1_team_a: int
    set1_team_b: int
    set1_winner_side: str | None = None

    # 2 / 3세트는
    # SERIES의 target_set_count에 따라 선택
    set2_team_a: int | None = None
    set2_team_b: int | None = None
    set2_winner_side: str | None = None

    set3_team_a: int | None = None
    set3_team_b: int | None = None
    set3_winner_side: str | None = None

    # 플레이오프용
    set4_team_a: int | None = None
    set4_team_b: int | None = None
    set4_winner_side: str | None = None

    set5_team_a: int | None = None
    set5_team_b: int | None = None
    set5_winner_side: str | None = None

    set6_team_a: int | None = None
    set6_team_b: int | None = None
    set6_winner_side: str | None = None

    set7_team_a: int | None = None
    set7_team_b: int | None = None
    set7_winner_side: str | None = None


class AdminSeriesResultUpdateRequest(
    BaseModel
):
    set1_team_a: int
    set1_team_b: int
    set1_winner_side: str | None = None

    set2_team_a: int | None = None
    set2_team_b: int | None = None
    set2_winner_side: str | None = None

    set3_team_a: int | None = None
    set3_team_b: int | None = None
    set3_winner_side: str | None = None

    set4_team_a: int | None = None
    set4_team_b: int | None = None
    set4_winner_side: str | None = None

    set5_team_a: int | None = None
    set5_team_b: int | None = None
    set5_winner_side: str | None = None

    set6_team_a: int | None = None
    set6_team_b: int | None = None
    set6_winner_side: str | None = None

    set7_team_a: int | None = None
    set7_team_b: int | None = None
    set7_winner_side: str | None = None


class HistorySeriesImportRequest(BaseModel):
    team_a: str
    team_b: str
    match_date: str

    include_extra_time_result: bool = False

class PlayoffInitializeRequest(
    BaseModel
):
    scheduled_date: str

class PlayoffAdvanceRequest(
    BaseModel
):
    scheduled_date: str

class AdminPlayoffUpdateRequest(
    BaseModel
):
    scheduled_date: str

    best_of: Literal[
        3,
        5,
        7,
    ]

class AdminRegularScheduleUpdateRequest(
    BaseModel
):
    scheduled_date: str

# =========================
# USER AUTH
# =========================

PASSWORD_HASH_ITERATIONS = (
    600_000
)

USER_SESSION_SECONDS = (
    30 * 24 * 60 * 60
)

SIGNUP_BONUS_POINTS = 1000

user_bearer_scheme = HTTPBearer(
    auto_error=False
)


def hash_user_password(
    password: str,
):

    salt = secrets.token_bytes(
        16
    )


    password_hash = (
        hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(
                "utf-8"
            ),
            salt,
            PASSWORD_HASH_ITERATIONS,
        )
    )


    return (
        "pbkdf2_sha256"
        f"${PASSWORD_HASH_ITERATIONS}"
        f"${salt.hex()}"
        f"${password_hash.hex()}"
    )


def verify_user_password(
    password: str,
    stored_password_hash: str,
):

    try:

        (
            algorithm,
            iterations_text,
            salt_hex,
            password_hash_hex,
        ) = stored_password_hash.split(
            "$",
            3,
        )


        if (
            algorithm
            != "pbkdf2_sha256"
        ):

            return False


        iterations = int(
            iterations_text
        )


        salt = bytes.fromhex(
            salt_hex
        )


        expected_hash = (
            bytes.fromhex(
                password_hash_hex
            )
        )


        calculated_hash = (
            hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(
                    "utf-8"
                ),
                salt,
                iterations,
            )
        )


        return hmac.compare_digest(
            calculated_hash,
            expected_hash,
        )


    except (
        ValueError,
        TypeError,
    ):

        return False

def hash_user_session_token(
    token: str,
):

    return hashlib.sha256(
        token.encode(
            "utf-8"
        )
    ).hexdigest()


def create_user_session(
    user_id: int,
):

    token = secrets.token_urlsafe(
        48
    )


    token_hash = (
        hash_user_session_token(
            token
        )
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # 만료된 세션 정리
            cursor.execute(
                """
                DELETE FROM user_sessions

                WHERE expires_at <= NOW()
                """
            )


            cursor.execute(
                """
                INSERT INTO user_sessions (
                    user_id,
                    token_hash,
                    expires_at
                )

                VALUES (
                    %s,
                    %s,
                    NOW()
                    + (
                        %s
                        * INTERVAL '1 second'
                    )
                )

                RETURNING
                    expires_at
                """,
                (
                    user_id,
                    token_hash,
                    USER_SESSION_SECONDS,
                ),
            )


            session = (
                cursor.fetchone()
            )


        connection.commit()


    return (
        token,
        session["expires_at"],
    )


def get_user_bearer_token(
    authorization: str | None,
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail=(
                "로그인이 필요합니다."
            ),
        )


    parts = authorization.split(
        " ",
        1,
    )


    if (
        len(parts) != 2
        or
        parts[0].lower()
        != "bearer"
        or
        not parts[1].strip()
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "로그인 정보가 "
                "올바르지 않습니다."
            ),
        )


    return parts[1].strip()

def require_user(
    credentials:
        HTTPAuthorizationCredentials
        | None
        = Depends(
            user_bearer_scheme
        )
):

    if not credentials:

        raise HTTPException(
            status_code=401,
            detail="로그인이 필요합니다.",
        )


    token = (
        credentials.credentials
    )


    token_hash = (
        hash_user_session_token(
            token
        )
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    users.id,
                    users.email,
                    users.nickname,
                    users.points,
                    users.is_admin,
                    users.created_at

                FROM user_sessions

                JOIN users
                    ON users.id
                    = user_sessions.user_id

                WHERE
                    user_sessions.token_hash
                    = %s

                    AND
                    user_sessions.expires_at
                    > NOW()
                """,
                (
                    token_hash,
                ),
            )


            user = (
                cursor.fetchone()
            )


    if not user:

        raise HTTPException(
            status_code=401,
            detail=(
                "로그인이 만료되었거나 "
                "유효하지 않습니다."
            ),
        )


    return user

def require_user_admin(
    user = Depends(
        require_user
    )
):

    if not user["is_admin"]:

        raise HTTPException(
            status_code=403,
            detail=(
                "관리자 권한이 필요합니다."
            ),
        )

    return user


@app.post(
    "/api/auth/signup"
)
def signup_user(
    request: UserSignupRequest
):

    email = (
        request.email
        .strip()
        .lower()
    )


    nickname = (
        request.nickname
        .strip()
    )


    password = (
        request.password
    )


    # =========================
    # 이메일 검증
    # =========================

    if (
        not email
        or
        "@" not in email
        or
        len(email) > 255
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "올바른 이메일을 "
                "입력해주세요."
            ),
        )


    # =========================
    # 닉네임 검증
    # =========================

    if (
        len(nickname) < 2
        or
        len(nickname) > 20
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "닉네임은 2자 이상 "
                "20자 이하로 입력해주세요."
            ),
        )


    # =========================
    # 비밀번호 검증
    # =========================

    if (
        len(password) < 8
        or
        len(password) > 128
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "비밀번호는 8자 이상 "
                "128자 이하로 입력해주세요."
            ),
        )


    # =========================
    # 중복 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id

                FROM users

                WHERE email = %s
                """,
                (
                    email,
                ),
            )


            if cursor.fetchone():

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "이미 사용 중인 "
                        "이메일입니다."
                    ),
                )


            cursor.execute(
                """
                SELECT id

                FROM users

                WHERE nickname = %s
                """,
                (
                    nickname,
                ),
            )


            if cursor.fetchone():

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "이미 사용 중인 "
                        "닉네임입니다."
                    ),
                )


            # =========================
            # 비밀번호 해시
            # =========================

            password_hash = (
                hash_user_password(
                    password
                )
            )


            # =========================
            # 회원 생성
            # =========================

            cursor.execute(
                """
                INSERT INTO users (
                    email,
                    password_hash,
                    nickname
                )

                VALUES (
                    %s,
                    %s,
                    %s
                )

                RETURNING
                    id,
                    email,
                    nickname,
                    points,
                    is_admin,
                    created_at
                """,
                (
                    email,
                    password_hash,
                    nickname,
                ),
            )


            user = (
                cursor.fetchone()
            )

            point_transaction = (
                change_user_points(
                    cursor,
                    user["id"],
                    SIGNUP_BONUS_POINTS,
                    "signup_bonus",
                    description=(
                        "FCL 신규 회원 가입 보너스"
                    ),
                )
            )


            user["points"] = (
                point_transaction[
                    "balance_after"
                ]
            )


        connection.commit()


    return {
        "message":
            "회원가입이 완료되었습니다.",

        "user":
            user,
    }

@app.post(
    "/api/auth/login"
)
def login_user(
    request: UserLoginRequest
):

    email = (
        request.email
        .strip()
        .lower()
    )


    password = (
        request.password
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    password_hash,
                    nickname,
                    points,
                    is_admin,
                    created_at

                FROM users

                WHERE email = %s
                """,
                (
                    email,
                ),
            )


            user = (
                cursor.fetchone()
            )


    if (
        not user
        or
        not verify_user_password(
            password,
            user["password_hash"],
        )
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "이메일 또는 비밀번호가 "
                "올바르지 않습니다."
            ),
        )


    (
        token,
        expires_at,
    ) = create_user_session(
        user["id"]
    )


    return {
        "message":
            "로그인되었습니다.",

        "token_type":
            "Bearer",

        "token":
            token,

        "expires_in":
            USER_SESSION_SECONDS,

        "expires_at":
            expires_at,

        "user": {
            "id":
                user["id"],

            "email":
                user["email"],

            "nickname":
                user["nickname"],

            "points":
                user["points"],

            "is_admin":
                user["is_admin"],

            "created_at":
                user["created_at"],
        },
    }

@app.get(
    "/api/auth/me"
)
def get_current_user(
    user = Depends(
        require_user
    )
):

    return {
        "user":
            user,
    }


@app.post(
    "/api/auth/logout"
)
def logout_user(
    credentials:
        HTTPAuthorizationCredentials
        = Depends(
            user_bearer_scheme
        ),

    user = Depends(
        require_user
    ),
):

    if not credentials:

        raise HTTPException(
            status_code=401,
            detail="로그인이 필요합니다.",
        )


    token = (
        credentials.credentials
    )


    token_hash = (
        hash_user_session_token(
            token
        )
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                DELETE FROM user_sessions

                WHERE token_hash = %s
                """,
                (
                    token_hash,
                ),
            )


        connection.commit()


    return {
        "message":
            "로그아웃되었습니다."
    }

# =========================
# MYPAGE
# =========================

@app.get(
    "/api/mypage"
)
def get_mypage(
    user = Depends(
        require_user
    )
):

    return {
        "user": {
            "id":
                user["id"],

            "email":
                user["email"],

            "nickname":
                user["nickname"],

            "points":
                user["points"],

            "is_admin":
                user["is_admin"],

            "created_at":
                user["created_at"],
        }
    }


@app.get(
    "/api/mypage/point-transactions"
)
def get_mypage_point_transactions(
    limit: int = 50,

    user = Depends(
        require_user
    ),
):

    # =========================
    # 조회 개수 제한
    # =========================

    limit = max(
        1,
        min(
            limit,
            100,
        ),
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    amount,
                    balance_after,
                    transaction_type,
                    reference_type,
                    reference_id,
                    description,
                    created_at

                FROM point_transactions

                WHERE user_id = %s

                ORDER BY
                    created_at DESC,
                    id DESC

                LIMIT %s
                """,
                (
                    user["id"],
                    limit,
                ),
            )


            transactions = (
                cursor.fetchall()
            )


    return {
        "current_points":
            user["points"],

        "transactions":
            transactions,
    }


# =========================
# ADMIN AUTH
# =========================

def create_admin_session():

    token = secrets.token_urlsafe(
        32
    )


    ADMIN_SESSIONS[token] = (
        time.time()
        + ADMIN_SESSION_SECONDS
    )


    return token


def require_admin(
    x_admin_token: str | None =
        Header(default=None)
):

    if not x_admin_token:

        raise HTTPException(
            status_code=401,
            detail="관리자 로그인이 필요합니다.",
        )


    expires_at = (
        ADMIN_SESSIONS.get(
            x_admin_token
        )
    )


    if (
        expires_at is None
        or
        expires_at < time.time()
    ):

        ADMIN_SESSIONS.pop(
            x_admin_token,
            None,
        )


        raise HTTPException(
            status_code=401,
            detail="관리자 로그인이 만료되었습니다.",
        )


    return x_admin_token


@app.post(
    "/api/admin/login"
)
def admin_login(
    request: AdminLoginRequest
):

    if not ADMIN_PASSWORD:

        raise HTTPException(
            status_code=500,
            detail=(
                "ADMIN_PASSWORD가 "
                "설정되지 않았습니다."
            ),
        )


    if not secrets.compare_digest(
        request.password,
        ADMIN_PASSWORD,
    ):

        raise HTTPException(
            status_code=401,
            detail="비밀번호가 올바르지 않습니다.",
        )


    token = create_admin_session()


    return {
        "admin": True,
        "token": token,
        "expires_in":
            ADMIN_SESSION_SECONDS,
    }

# =========================
# ADMIN FC ONLINE DB CHECK
# 신규 시즌 감지
# =========================

@app.get(
    "/api/admin/fconline-sync/check"
)
def admin_check_fconline_sync(
    admin_token: str = Depends(
        require_admin
    ),
):

    if not DATABASE_URL:

        raise HTTPException(
            status_code=500,
            detail=(
                "DATABASE_URL이 "
                "설정되지 않았습니다."
            ),
        )


    try:

        # =================================
        # 관리자 버튼을 누를 때마다
        # 시즌 메타데이터는 새로 조회
        # =================================

        player_catalog_service.SEASON_METADATA_CACHE = (
            None
        )


        season_metadata = (
            player_catalog_service
            .get_season_metadata()
        )


        cards_by_season = (
            build_metadata_card_map()
        )


        db_counts = (
            get_database_season_counts(
                DATABASE_URL
            )
        )


        seasons = []


        for (
            season_id,
            cards,
        ) in cards_by_season.items():

            metadata_count = len(
                cards
            )

            database_count = int(
                db_counts.get(
                    season_id,
                    0,
                )
            )

            missing_count = (
                metadata_count
                -
                database_count
            )


            if missing_count <= 0:
                continue


            metadata = (
                season_metadata.get(
                    season_id,
                    {}
                )
            )


            seasons.append(
                {
                    "season_id":
                        int(
                            season_id
                        ),

                    "class_name":
                        metadata.get(
                            "class_name",
                            "알 수 없는 클래스",
                        ),

                    "metadata_count":
                        metadata_count,

                    "database_count":
                        database_count,

                    "missing_count":
                        missing_count,
                }
            )


        seasons.sort(
            key=lambda season:
                season[
                    "season_id"
                ],
            reverse=True,
        )


        # =================================
        # 현재 Nexon 메타데이터상
        # 가장 최신 시즌
        # =================================

        available_season_ids = [
            int(
                season_id
            )

            for season_id
            in cards_by_season.keys()

            if season_id
            in season_metadata
        ]


        latest_metadata_season = None


        if available_season_ids:

            latest_season_id = max(
                available_season_ids
            )

            latest_metadata = (
                season_metadata.get(
                    latest_season_id,
                    {}
                )
            )


            latest_metadata_season = {
                "season_id":
                    latest_season_id,

                "class_name":
                    latest_metadata.get(
                        "class_name",
                        "알 수 없는 클래스",
                    ),

                "player_count":
                    len(
                        cards_by_season[
                            latest_season_id
                        ]
                    ),

                "database_count":
                    int(
                        db_counts.get(
                            latest_season_id,
                            0,
                        )
                    ),
            }


        return {
            "has_updates":
                bool(
                    seasons
                ),

            "update_count":
                len(
                    seasons
                ),

            "latest_metadata_season":
                latest_metadata_season,

            "seasons":
                seasons,
        }


    except HTTPException:

        raise


    except Exception as error:

        print(
            "FC ONLINE SYNC CHECK ERROR:",
            repr(
                error
            ),
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "신규 시즌 확인 중 "
                "오류가 발생했습니다."
            ),
        )

# =========================
# ADMIN FC ONLINE DB SYNC
# 신규 시즌 10명 단위 동기화
# =========================

@app.post(
    "/api/admin/fconline-sync/batch"
)
def admin_sync_fconline_batch(
    season_id: int,
    batch_size: int = 10,

    admin_token: str = Depends(
        require_admin
    ),
):

    # =========================
    # 기본 검증
    # =========================

    if not DATABASE_URL:

        raise HTTPException(
            status_code=500,
            detail=(
                "DATABASE_URL이 "
                "설정되지 않았습니다."
            ),
        )


    batch_size = max(
        1,
        min(
            int(batch_size),
            10,
        ),
    )


    # =========================
    # 동시에 두 동기화 방지
    # =========================

    lock_acquired = (
        FC_ONLINE_SYNC_LOCK.acquire(
            blocking=False
        )
    )


    if not lock_acquired:

        raise HTTPException(
            status_code=409,
            detail=(
                "다른 FC Online DB "
                "동기화 작업이 진행 중입니다."
            ),
        )


    try:

        # =========================
        # player_catalog.py도
        # 현재 DB 환경변수를 사용하도록 설정
        # =========================

        player_catalog_service.DATABASE_URL = (
            DATABASE_URL
        )


        # =========================
        # Nexon 최신 메타데이터
        # =========================

        season_metadata = (
            player_catalog_service
            .get_season_metadata()
        )


        cards_by_season = (
            build_metadata_card_map()
        )


        season_cards = (
            cards_by_season.get(
                season_id
            )
        )


        if season_cards is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    f"Nexon 메타데이터에서 "
                    f"시즌 {season_id}을 "
                    "찾을 수 없습니다."
                ),
            )


        season_info = (
            season_metadata.get(
                season_id,
                {}
            )
        )


        class_name = (
            season_info.get(
                "class_name",
                f"시즌 {season_id}",
            )
        )


        total_count = len(
            season_cards
        )


        # =========================
        # 현재 DB 저장 SPID
        # =========================

        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        sp_id

                    FROM fconline_players

                    WHERE season_id = %s
                    """,
                    (
                        season_id,
                    ),
                )


                existing_rows = (
                    cursor.fetchall()
                )


        existing_ids = {
            int(
                row["sp_id"]
            )

            for row
            in existing_rows
        }


        # =========================
        # 아직 저장되지 않은 선수
        # =========================

        missing_cards = [
            card

            for card
            in season_cards

            if int(
                card["sp_id"]
            )
            not in existing_ids
        ]


        missing_cards.sort(
            key=lambda card:
                int(
                    card["sp_id"]
                )
        )


        # =========================
        # 이미 완료된 시즌
        # =========================

        if not missing_cards:

            return {
                "season_id":
                    season_id,

                "class_name":
                    class_name,

                "total_count":
                    total_count,

                "database_count":
                    len(
                        existing_ids
                    ),

                "requested_count":
                    0,

                "success_count":
                    0,

                "failed_count":
                    0,

                "remaining_count":
                    0,

                "complete":
                    True,

                "failures":
                    [],
            }


        # =========================
        # 이번 요청에서 최대 10명
        # =========================

        batch_cards = (
            missing_cards[
                :batch_size
            ]
        )


        # =========================
        # 시즌 아이콘 Snapshot 저장
        #
        # 첫 신규 선수 동기화 때만
        # 실제 다운로드됨
        # 이미 있으면 즉시 종료
        # =========================

        global SEASON_METADATA_CACHE

        SEASON_METADATA_CACHE = None


        try:

            ensure_fconline_season_snapshot(
                int(
                    batch_cards[0][
                        "sp_id"
                    ]
                )
            )

        except Exception as error:

            print(
                "FC ONLINE SEASON SNAPSHOT ERROR:",
                repr(
                    error
                ),
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "신규 시즌 이미지 "
                    "저장에 실패했습니다."
                ),
            )


        success_count = 0

        failures = []


        # =========================
        # 선수 단위 저장
        # =========================

        for card in batch_cards:

            sp_id = int(
                card[
                    "sp_id"
                ]
            )

            player_name = str(
                card.get(
                    "player_name",
                    ""
                )
            ).strip()


            try:

                player_catalog_service.set_player_sync_running(
                    sp_id,
                    player_name,
                )


                player = (
                    player_catalog_service
                    .get_player_ability(
                        sp_id,
                        grade=1,
                    )
                )


                player_catalog_service.validate_collected_player(
                    player
                )


                player["image_url"] = (
                    player_catalog_service
                    .PLAYER_IMAGE_URL_TEMPLATE
                    .format(
                        sp_id=sp_id
                    )
                )


                player_catalog_service.save_player_to_database(
                    player
                )


                player_catalog_service.set_player_sync_completed(
                    sp_id
                )


                success_count += 1


            except Exception as error:

                print(
                    "FC ONLINE PLAYER SYNC ERROR:",
                    sp_id,
                    player_name,
                    repr(
                        error
                    ),
                )


                try:

                    player_catalog_service.set_player_sync_failed(
                        sp_id,
                        str(
                            error
                        ),
                    )

                except Exception as state_error:

                    print(
                        "FC ONLINE SYNC STATE ERROR:",
                        repr(
                            state_error
                        ),
                    )


                failures.append(
                    {
                        "sp_id":
                            sp_id,

                        "player_name":
                            player_name,

                        "error":
                            str(
                                error
                            ),
                    }
                )


            time.sleep(
                player_catalog_service
                .PLAYER_REQUEST_DELAY_SECONDS
            )


        # =========================
        # 저장 후 실제 DB 개수 재확인
        # =========================

        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        COUNT(*) AS count

                    FROM fconline_players

                    WHERE season_id = %s
                    """,
                    (
                        season_id,
                    ),
                )


                count_row = (
                    cursor.fetchone()
                )


        database_count = int(
            count_row["count"]
        )


        remaining_count = max(
            0,
            total_count
            -
            database_count,
        )


        return {
            "season_id":
                season_id,

            "class_name":
                class_name,

            "total_count":
                total_count,

            "database_count":
                database_count,

            "requested_count":
                len(
                    batch_cards
                ),

            "success_count":
                success_count,

            "failed_count":
                len(
                    failures
                ),

            "remaining_count":
                remaining_count,

            "complete":
                (
                    remaining_count
                    == 0
                ),

            "failures":
                failures,
        }


    except HTTPException:

        raise


    except Exception as error:

        print(
            "FC ONLINE BATCH SYNC ERROR:",
            repr(
                error
            ),
        )


        raise HTTPException(
            status_code=500,
            detail=(
                "FC Online 선수 "
                "동기화 중 오류가 발생했습니다."
            ),
        )


    finally:

        FC_ONLINE_SYNC_LOCK.release()

# =========================
# ADMIN PLAYER POPULARITY
# FC Online 데이터센터
# 인기 선수 동기화
# =========================

@app.post(
    "/api/admin/player-popularity/sync"
)
def admin_sync_player_popularity(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 동시에 두 번 실행 방지
    # =========================

    acquired = (
        PLAYER_POPULARITY_SYNC_LOCK
        .acquire(
            blocking=False
        )
    )


    if not acquired:

        raise HTTPException(
            status_code=409,
            detail=(
                "인기 선수 데이터 동기화가 "
                "이미 진행 중입니다."
            ),
        )


    try:

        with get_db_connection() as connection:

            result = (
                sync_player_popularity(
                    connection
                )
            )


        return {
            "success":
                True,

            "message":
                (
                    "FC Online 인기 선수 "
                    "데이터 동기화가 "
                    "완료되었습니다."
                ),

            **result,
        }


    except httpx.HTTPError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "FC Online 데이터센터 "
                "조회에 실패했습니다. "
                f"{error}"
            ),
        )


    except RuntimeError as error:

        raise HTTPException(
            status_code=502,
            detail=str(
                error
            ),
        )


    finally:

        PLAYER_POPULARITY_SYNC_LOCK.release()

# =========================
# ADMIN USERS
# =========================

@app.get(
    "/api/admin/users"
)

@app.get(
    "/api/admin/player-popularity/status"
)
def admin_get_player_popularity_status(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 테이블 존재 여부
            # =========================

            cursor.execute(
                """
                SELECT
                    to_regclass(
                        'public.'
                        'fconline_player_popularity'
                    )
                    AS table_name
                """
            )


            table_row = (
                cursor.fetchone()
            )


            table_exists = (
                table_row[
                    "table_name"
                ]
                is not None
            )


            if not table_exists:

                return {
                    "exists":
                        False,

                    "snapshot_date":
                        None,

                    "player_count":
                        0,

                    "position_count":
                        0,

                    "updated_at":
                        None,
                }


            # =========================
            # 최신 Snapshot 조회
            # =========================

            cursor.execute(
                """
                WITH latest AS (
                    SELECT
                        MAX(snapshot_date)
                            AS snapshot_date

                    FROM
                        fconline_player_popularity
                )

                SELECT
                    latest.snapshot_date,

                    COUNT(p.id)
                        AS player_count,

                    COUNT(
                        DISTINCT p.position
                    )
                        AS position_count,

                    MAX(
                        p.updated_at
                    )
                        AS updated_at

                FROM latest

                LEFT JOIN
                    fconline_player_popularity AS p

                    ON
                        p.snapshot_date =
                        latest.snapshot_date

                GROUP BY
                    latest.snapshot_date
                """
            )


            row = (
                cursor.fetchone()
            )


    return {
        "exists":
            True,

        "snapshot_date":
            (
                row[
                    "snapshot_date"
                ].isoformat()

                if row[
                    "snapshot_date"
                ]

                else None
            ),

        "player_count":
            int(
                row[
                    "player_count"
                ]
                or 0
            ),

        "position_count":
            int(
                row[
                    "position_count"
                ]
                or 0
            ),

        "updated_at":
            (
                row[
                    "updated_at"
                ].isoformat()

                if row[
                    "updated_at"
                ]

                else None
            ),
    }


@app.post(
    "/api/admin/"
    "player-generation-notices/sync"
)
def admin_sync_player_generation_notices(
    admin_token: str =
        Depends(
            require_admin
        ),
):
    with get_db_connection() as connection:

        result = (
            sync_generation_notices(
                connection
            )
        )

    return {
        "success":
            True,

        "message":
            (
                "FC Online 생성 제한/해제 "
                "공식 공지 동기화가 "
                "완료되었습니다."
            ),

        **result,
    }


@app.get(
    "/api/admin/"
    "player-generation-notices/status"
)
def admin_player_generation_notice_status(
    admin_token: str =
        Depends(
            require_admin
        ),
):
    with get_db_connection() as connection:

        status = (
            get_generation_notice_status(
                connection
            )
        )

    return {
        "success":
            True,

        **status,
    }


@app.get(
    "/api/admin/"
    "player-generation-notices/preview"
)
def admin_player_generation_notice_preview(
    limit: int = 30,

    admin_token: str =
        Depends(
            require_admin
        ),
):
    safe_limit = max(
        1,
        min(
            int(limit),
            100,
        ),
    )

    with get_db_connection() as connection:

        notices = (
            get_generation_notice_preview(
                connection,
                limit=safe_limit,
            )
        )

    return {
        "success":
            True,

        "count":
            len(notices),

        "notices":
            notices,
    }


@app.get(
    "/api/admin/"
    "player-generation-notices/"
    "preview-actions"
)
def admin_player_generation_action_preview(
    limit: int = 100,

    admin_token: str =
        Depends(
            require_admin
        ),
):
    safe_limit = max(
        1,
        min(
            int(limit),
            300,
        ),
    )

    with get_db_connection() as connection:

        notices = (
            get_generation_action_preview(
                connection,
                limit=safe_limit,
            )
        )

    return {
        "success":
            True,

        "notice_count":
            len(notices),

        "action_count":
            sum(
                int(
                    notice[
                        "action_count"
                    ]
                )
                for notice
                in notices
            ),

        "notices":
            notices,
    }

@app.get(
    "/api/admin/"
    "player-generation-notices/"
    "preview-resolutions"
)
def admin_player_generation_resolution_preview(
    limit: int = 100,

    admin_token: str =
        Depends(
            require_admin
        ),
):
    safe_limit = max(
        1,
        min(
            int(limit),
            300,
        ),
    )

    with get_db_connection() as connection:

        result = (
            get_generation_resolution_preview(
                connection,
                limit=safe_limit,
            )
        )

    return {
        "success":
            True,

        **result,
    }

@app.post(
    "/api/admin/"
    "player-generation-status/sync"
)
def admin_sync_player_generation_status(
    admin_token: str =
        Depends(
            require_admin
        ),
):
    with get_db_connection() as connection:

        result = (
            sync_generation_status_from_notices(
                connection
            )
        )

    return {
        "success":
            True,

        "message":
            (
                "FC Online 공식 공지를 기준으로 "
                "선수 생성 제한 상태 동기화가 "
                "완료되었습니다."
            ),

        **result,
    }


def get_admin_users(
    admin_token = Depends(
        require_admin
    )
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    email,
                    nickname,
                    points,
                    is_admin,
                    created_at,
                    updated_at

                FROM users

                ORDER BY
                    created_at DESC,
                    id DESC
                """
            )


            users = (
                cursor.fetchall()
            )


    return {
        "users":
            users
    }

@app.post(
    "/api/admin/users/{user_id}/points"
)
def change_admin_user_points(
    user_id: int,

    request:
        AdminUserPointRequest,

    admin_token = Depends(
        require_admin
    ),
):

    amount = (
        request.amount
    )


    if amount == 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "포인트 변동 금액은 "
                "0일 수 없습니다."
            ),
        )


    description = (
        request.description.strip()
        if request.description
        else None
    )


    if (
        description
        and
        len(description) > 200
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "포인트 사유는 "
                "200자 이하로 입력해주세요."
            ),
        )


    transaction_type = (
        "admin_grant"
        if amount > 0
        else "admin_deduct"
    )


    if not description:

        description = (
            "관리자 포인트 지급"
            if amount > 0
            else "관리자 포인트 차감"
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            transaction = (
                change_user_points(
                    cursor,
                    user_id,
                    amount,
                    transaction_type,
                    description=
                        description,
                )
            )


        connection.commit()


    return {
        "message":
            "포인트가 변경되었습니다.",

        "transaction":
            transaction,
    }

@app.patch(
    "/api/admin/users/{user_id}/role"
)
def change_admin_user_role(
    user_id: int,

    request:
        AdminUserRoleRequest,

    admin_token = Depends(
        require_admin
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE users

                SET
                    is_admin = %s,
                    updated_at = NOW()

                WHERE id = %s

                RETURNING
                    id,
                    email,
                    nickname,
                    points,
                    is_admin,
                    created_at
                """,
                (
                    request.is_admin,
                    user_id,
                ),
            )


            user = (
                cursor.fetchone()
            )


            if not user:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "사용자를 찾을 수 없습니다."
                    ),
                )


        connection.commit()


    return {
        "message":
            (
                "관리자 권한이 부여되었습니다."
                if request.is_admin
                else
                "관리자 권한이 해제되었습니다."
            ),

        "user":
            user,
    }


# =========================
# ADMIN PARTICIPANTS
# 참가자 / 현재 팀 조회
# =========================

@app.get(
    "/api/admin/participants"
)
def admin_get_participants(
    admin_token: str =
        Depends(
            require_admin
        )
):
    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname,

                    current_team_name,
                    current_team_logo_path

                FROM participants

                ORDER BY id
                """
            )

            participants = (
                cursor.fetchall()
            )

    return participants

# =========================
# ADMIN PARTICIPANT TEAM UPDATE
# 현재 팀 변경
# =========================

@app.put(
    "/api/admin/participants/"
    "{participant_id}/team"
)
def admin_update_participant_team(
    participant_id: int,
    request:
        AdminParticipantTeamUpdateRequest,
    admin_token: str =
        Depends(
            require_admin
        ),
):
    current_team_name = (
        request.current_team_name.strip()
    )

    current_team_logo_path = (
        request
            .current_team_logo_path
            .strip()
    )


    # =========================
    # 기본 검증
    # =========================

    if not current_team_name:

        raise HTTPException(
            status_code=400,
            detail=(
                "현재 팀 이름을 "
                "입력해주세요."
            ),
        )


    if not current_team_logo_path:

        raise HTTPException(
            status_code=400,
            detail=(
                "현재 팀 로고 경로를 "
                "입력해주세요."
            ),
        )


    # =========================
    # 역사 보존용 로고만 허용
    # =========================

    history_directory = (
        FRONTEND_DIR
        / "assets"
        / "images"
        / "teams"
        / "history"
    ).resolve()


    logo_relative_path = Path(
        current_team_logo_path.removeprefix(
            "./"
        )
    )


    logo_file_path = (
        FRONTEND_DIR
        / logo_relative_path
    ).resolve()


    if (
        history_directory
        not in logo_file_path.parents
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "현재 팀 로고는 "
                "history 폴더의 파일만 "
                "사용할 수 있습니다."
            ),
        )


    if not logo_file_path.is_file():

        raise HTTPException(
            status_code=400,
            detail=(
                "지정한 팀 로고 파일을 "
                "찾을 수 없습니다."
            ),
        )


    # =========================
    # 참가자 현재 팀 변경
    #
    # series Snapshot은
    # 절대 수정하지 않음
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 참가자 존재 확인 + 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name

                FROM participants

                WHERE id = %s

                FOR UPDATE
                """,
                (
                    participant_id,
                ),
            )


            existing_participant = (
                cursor.fetchone()
            )


            if not existing_participant:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "참가자를 "
                        "찾을 수 없습니다."
                    ),
                )


            # =========================
            # 진행 중 SERIES 보호
            #
            # 경기 진행 중에는
            # 현재 팀 변경 금지
            #
            # 시작 순간 저장된 Snapshot과
            # participants 현재 팀 정보가
            # 서로 달라지는 상황 방지
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    playoff_stage

                FROM series

                WHERE
                    status = 'active'

                    AND (
                        team_a_id = %s
                        OR
                        team_b_id = %s
                    )

                LIMIT 1

                FOR UPDATE
                """,
                (
                    participant_id,
                    participant_id,
                ),
            )


            active_series = (
                cursor.fetchone()
            )


            if active_series:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "진행 중인 경기가 있는 "
                        "참가자의 팀은 "
                        "변경할 수 없습니다. "
                        "경기 종료 후 다시 시도해주세요."
                    ),
                )


            # =========================
            # 참가자 현재 팀 변경
            #
            # 과거 SERIES Snapshot은
            # 절대 수정하지 않음
            # =========================

            cursor.execute(
                """
                UPDATE participants

                SET
                    current_team_name = %s,
                    current_team_logo_path = %s,
                    updated_at = NOW()

                WHERE id = %s

                RETURNING
                    id,
                    fcl_name,
                    fc_nickname,
                    current_team_name,
                    current_team_logo_path
                """,
                (
                    current_team_name,
                    current_team_logo_path,
                    participant_id,
                ),
            )


            participant = (
                cursor.fetchone()
            )


        connection.commit()


    return participant

# =========================
# ADMIN TEAM LOGO INTEGRITY
# 현재 / 과거 팀 로고 파일 무결성 검사
# =========================

@app.get(
    "/api/admin/team-logo-integrity"
)
def admin_check_team_logo_integrity(
    admin_token: str =
        Depends(
            require_admin
        )
):
    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 현재 참가자 팀 로고
            # =========================

            cursor.execute(
                """
                SELECT DISTINCT
                    current_team_logo_path
                        AS logo_path

                FROM participants

                WHERE
                    current_team_logo_path
                    IS NOT NULL
                """
            )

            current_logo_rows = (
                cursor.fetchall()
            )


            # =========================
            # 과거 SERIES Snapshot 로고
            # =========================

            cursor.execute(
                """
                SELECT DISTINCT
                    logo_path

                FROM (
                    SELECT
                        team_a_snapshot_logo_path
                            AS logo_path

                    FROM series

                    UNION

                    SELECT
                        team_b_snapshot_logo_path
                            AS logo_path

                    FROM series
                ) AS snapshot_logos

                WHERE
                    logo_path IS NOT NULL
                """
            )

            snapshot_logo_rows = (
                cursor.fetchall()
            )


    referenced_logo_paths = set()


    for row in current_logo_rows:

        referenced_logo_paths.add(
            row["logo_path"]
        )


    for row in snapshot_logo_rows:

        referenced_logo_paths.add(
            row["logo_path"]
        )


    history_directory = (
        FRONTEND_DIR
        / "assets"
        / "images"
        / "teams"
        / "history"
    ).resolve()


    missing_logo_paths = []
    invalid_logo_paths = []


    for logo_path in sorted(
        referenced_logo_paths
    ):

        logo_relative_path = Path(
            logo_path.removeprefix("./")
        )


        logo_file_path = (
            FRONTEND_DIR
            / logo_relative_path
        ).resolve()


        # =========================
        # history 밖의 잘못된 경로
        # =========================

        if (
            history_directory
            not in logo_file_path.parents
        ):

            invalid_logo_paths.append(
                logo_path
            )

            continue


        # =========================
        # 실제 파일 존재 여부
        # =========================

        if not logo_file_path.is_file():

            missing_logo_paths.append(
                logo_path
            )


    return {
        "ok":
            (
                len(missing_logo_paths) == 0
                and
                len(invalid_logo_paths) == 0
            ),

        "referenced_count":
            len(
                referenced_logo_paths
            ),

        "missing_count":
            len(
                missing_logo_paths
            ),

        "invalid_count":
            len(
                invalid_logo_paths
            ),

        "missing_logo_paths":
            missing_logo_paths,

        "invalid_logo_paths":
            invalid_logo_paths,
    }


@app.get(
    "/api/admin/check"
)
def admin_check(
    admin_token: str =
        Depends(
            require_admin
        )
):

    return {
        "admin": True
    }

def get_round_number(match_index):
    return (match_index // 5) + 1


# =========================
# ADMIN SERIES SQUAD BACKFILL
# 기존 완료 경기 세트별 스쿼드 Snapshot 생성
# =========================

@app.post(
    "/api/admin/series/{series_id}/squad-backfill"
)
def admin_backfill_series_squad(
    series_id: int,
    admin_token: str =
        Depends(
            require_admin
        ),
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
                    s.status,

                    s.team_a_id,
                    team_a.fc_nickname
                        AS nickname_a,

                    s.team_b_id,
                    team_b.fc_nickname
                        AS nickname_b

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


            if series["status"] != "completed":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "완료된 경기만 "
                        "스쿼드 Snapshot을 "
                        "생성할 수 있습니다."
                    ),
                )


            cursor.execute(
                """
                SELECT
                    id,
                    set_number,
                    nexon_match_id,
                    played_at

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )

            saved_sets = cursor.fetchall()


    # =========================
    # 세트 확인
    # =========================

    if not saved_sets:

        raise HTTPException(
            status_code=400,
            detail=(
                "저장된 세트가 없습니다."
            ),
        )


    nickname_a = series[
        "nickname_a"
    ]

    nickname_b = series[
        "nickname_b"
    ]


    if not nickname_a or not nickname_b:

        raise HTTPException(
            status_code=400,
            detail=(
                "FC Online 닉네임 정보가 "
                "없습니다."
            ),
        )


    # =========================
    # 저장된 matchId 기준
    # Nexon 원본 다시 조회
    # =========================

    detected_matches = []


    for saved_set in saved_sets:

        match_id = saved_set[
            "nexon_match_id"
        ]


        if not match_id:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"{saved_set['set_number']}세트에 "
                    "Nexon matchId가 없습니다."
                ),
            )


        match_data = get_match_detail(
            match_id
        )


        match_nicknames = {
            match_info["nickname"]

            for match_info
            in match_data["matchInfo"]
        }


        if match_nicknames != {
            nickname_a,
            nickname_b,
        }:

            raise HTTPException(
                status_code=400,
                detail=(
                    f"{saved_set['set_number']}세트의 "
                    "Nexon 참가자 정보가 "
                    "SERIES와 일치하지 않습니다."
                ),
            )


        detected_matches.append(
            {
                "data":
                    match_data,

                "played_at":
                    parse_nexon_datetime(
                        match_data[
                            "matchDate"
                        ]
                    ),
            }
        )


    # =========================
    # Snapshot 저장
    # =========================

    inserted_count = (
        save_series_set_squad_players(
            series_id,

            series[
                "team_a_id"
            ],
            nickname_a,

            series[
                "team_b_id"
            ],
            nickname_b,

            detected_matches,
        )
    )


    return {
        "series_id":
            series_id,

        "set_count":
            len(saved_sets),

        "player_snapshot_count":
            inserted_count,

        "message":
            (
                "세트별 스쿼드 Snapshot "
                "생성이 완료되었습니다."
            ),
    }

# =========================
# ADMIN REGULAR SCHEDULE
# 정규리그 일정 조회
# =========================

@app.get(
    "/api/admin/regular-schedule"
)
def admin_get_regular_schedule(
    admin_token: str =
        Depends(
            require_admin
        )
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id AS series_id,
                    s.fixture_number,
                    s.round_number,
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
                        '정규리그'

                ORDER BY
                    s.fixture_number,
                    s.id
                """
            )


            schedule_rows = cursor.fetchall()


    schedules = []


    for schedule_row in schedule_rows:

        scheduled_date = schedule_row [
                "scheduled_date"
            ]


        schedules.append(
            {
                "series_id":
                    schedule_row[
                        "series_id"
                    ],

                "fixture_number":
                    schedule_row[
                        "fixture_number"
                    ],

                "round":
                    schedule_row[
                        "round_number"
                    ],

                "date":
                    (
                        scheduled_date.isoformat()
                        if scheduled_date
                        else None
                    ),

                "team_a":
                    schedule_row[
                        "team_a"
                    ],

                "team_b":
                    schedule_row[
                        "team_b"
                    ],

                "status":
                    schedule_row[
                        "status"
                    ],
            }
        )


    return schedules

# =========================
# ADMIN REGULAR SCHEDULE UPDATE
# 정규리그 일정 변경
# =========================

@app.put(
    "/api/admin/series/{series_id}/schedule"
)
def admin_update_regular_schedule(
    series_id: int,
    request:
        AdminRegularScheduleUpdateRequest,
    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 날짜 형식 확인
    # =========================

    try:

        new_scheduled_date = (
            datetime.strptime(
                request.scheduled_date,
                "%Y-%m-%d",
            ).date()
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail=(
                "경기 날짜 형식이 "
                "올바르지 않습니다."
            ),
        )


    # =========================
    # 과거 날짜 금지
    # =========================

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    if new_scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로는 "
                "일정을 변경할 수 없습니다."
            ),
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    scheduled_date,
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
                    detail=(
                        "경기를 찾을 수 없습니다."
                    ),
                )


            # =========================
            # 정규리그만 허용
            # =========================

            if (
                series["series_type"]
                != "정규리그"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "정규리그 경기만 "
                        "일정을 변경할 수 있습니다."
                    ),
                )


            # =========================
            # 예정 경기만 허용
            # =========================

            if (
                series["status"]
                != "scheduled"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "예정 상태의 경기만 "
                        "일정을 변경할 수 있습니다."
                    ),
                )


            previous_date = (
                series["scheduled_date"]
            )


            # =========================
            # 날짜 변경
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    scheduled_date = %s

                WHERE id = %s

                RETURNING
                    id,
                    fixture_number,
                    round_number,
                    scheduled_date,
                    status
                """,
                (
                    new_scheduled_date,
                    series_id,
                ),
            )


            updated_series = cursor.fetchone()


        connection.commit()


    return {
        "series_id":
            updated_series["id"],

        "fixture_number":
            updated_series[
                "fixture_number"
            ],

        "round":
            updated_series[
                "round_number"
            ],

        "previous_date":
            (
                previous_date.isoformat()
                if previous_date
                else None
            ),

        "scheduled_date":
            updated_series[
                "scheduled_date"
            ].isoformat(),

        "status":
            updated_series[
                "status"
            ],

        "message":
            "정규리그 일정이 변경되었습니다.",
    }


# =========================
# ADMIN REGULAR SCHEDULE REFORM
#
# 2026-09-15 이후
#
# 화 / 목 / 토
# 하루 2 SERIES
#
# ROUND 1:
# Fixture 1 ~ 5
# 기존 일정 / 기존 3 SET 유지
#
# ROUND 2 ~ 4:
# Fixture 6 ~ 20
# 2 SET
# =========================

@app.post(
    "/api/admin/regular-schedule/"
    "apply-two-set-format"
)
def admin_apply_regular_two_set_format(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    from itertools import permutations


    # =========================
    # 새 운영 시작일
    #
    # 월 / 수 / 토
    # =========================

    first_schedule_date = (
        datetime.strptime(
            "2026-09-14",
            "%Y-%m-%d",
        ).date()
    )


    # =========================
    # 변경 대상
    #
    # ROUND 2 ~ ROUND 4
    # Fixture 6 ~ 20
    # =========================

    first_fixture = 6
    last_fixture = 20


    expected_fixture_numbers = list(
        range(
            first_fixture,
            last_fixture + 1,
        )
    )


    # =========================
    # 두 SERIES 참가자 중복 확인
    # =========================

    def series_are_disjoint(
        left_series,
        right_series,
    ):

        left_participants = {
            int(
                left_series[
                    "team_a_id"
                ]
            ),
            int(
                left_series[
                    "team_b_id"
                ]
            ),
        }


        right_participants = {
            int(
                right_series[
                    "team_a_id"
                ]
            ),
            int(
                right_series[
                    "team_b_id"
                ]
            ),
        }


        return (
            left_participants
            .isdisjoint(
                right_participants
            )
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 대상 SERIES 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.fixture_number,
                    s.round_number,
                    s.scheduled_date,
                    s.status,
                    s.target_set_count,

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

                WHERE
                    s.series_type =
                        '정규리그'

                    AND
                    s.fixture_number
                        BETWEEN %s AND %s

                    AND
                    s.status <>
                        'cancelled'

                ORDER BY
                    s.fixture_number ASC

                FOR UPDATE
                """,
                (
                    first_fixture,
                    last_fixture,
                ),
            )


            series_rows = (
                cursor.fetchall()
            )


            # =========================
            # Fixture 구성 검증
            # =========================

            actual_fixture_numbers = [
                int(
                    row[
                        "fixture_number"
                    ]
                )

                for row
                in series_rows
            ]


            if (
                actual_fixture_numbers
                != expected_fixture_numbers
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "정규리그 Fixture 6~20을 "
                        "정확히 찾을 수 없습니다. "
                        f"현재: "
                        f"{actual_fixture_numbers}"
                    ),
                )


            # =========================
            # 이미 진행된 경기 보호
            #
            # scheduled만 일정 변경 가능
            # =========================

            non_scheduled_rows = [
                row

                for row
                in series_rows

                if (
                    row["status"]
                    != "scheduled"
                )
            ]


            if non_scheduled_rows:

                blocked_fixtures = [
                    int(
                        row[
                            "fixture_number"
                        ]
                    )

                    for row
                    in non_scheduled_rows
                ]


                raise HTTPException(
                    status_code=400,
                    detail=(
                        "이미 시작 또는 완료된 "
                        "정규리그 경기가 있어 "
                        "일괄 변경할 수 없습니다. "
                        f"Fixture: "
                        f"{blocked_fixtures}"
                    ),
                )


            # =========================
            # 기존 라운드별 SERIES 분리
            #
            # 기존 대진 구성 자체는 보존
            # 라운드 안에서 경기 순서만 변경
            # =========================

            round_rows = {
                2: [],
                3: [],
                4: [],
            }


            for series_row in series_rows:

                fixture_number = int(
                    series_row[
                        "fixture_number"
                    ]
                )


                round_number = (
                    (
                        fixture_number - 1
                    )
                    // 5
                ) + 1


                if (
                    round_number
                    not in round_rows
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "정규리그 라운드 계산 중 "
                            "올바르지 않은 Fixture가 "
                            "발견되었습니다."
                        ),
                    )


                round_rows[
                    round_number
                ].append(
                    series_row
                )


            # =========================
            # 라운드 구성 검증
            #
            # 각 라운드:
            # - 5 SERIES
            # - 참가자 5명
            # - 각 참가자 2회 출전
            # =========================

            for (
                round_number,
                rows,
            ) in round_rows.items():

                if len(rows) != 5:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"ROUND {round_number}의 "
                            "경기 수가 5경기가 아닙니다."
                        ),
                    )


                participant_counts = {}


                for row in rows:

                    for participant_id in (
                        int(
                            row[
                                "team_a_id"
                            ]
                        ),
                        int(
                            row[
                                "team_b_id"
                            ]
                        ),
                    ):

                        participant_counts[
                            participant_id
                        ] = (
                            participant_counts.get(
                                participant_id,
                                0,
                            )
                            + 1
                        )


                if (
                    len(participant_counts)
                    != 5
                    or
                    any(
                        count != 2
                        for count
                        in participant_counts.values()
                    )
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"ROUND {round_number}의 "
                            "참가자 출전 구성이 "
                            "2회씩 균등하지 않습니다. "
                            f"현재: "
                            f"{participant_counts}"
                        ),
                    )


            # =========================
            # 경기 순서 재배치
            #
            # 하루 2 SERIES인 경우
            # 두 경기 참가자가 완전히 달라야 함
            #
            # 전체 위치:
            #
            # R2
            # 0 / 1
            # 2 / 3
            # 4
            #
            # R3
            # 5
            # 6 / 7
            # 8 / 9
            #
            # R4
            # 10 / 11
            # 12 / 13
            # 14
            #
            # 위치 4 / 5는 같은 9/19 경기일
            # =========================

            round_2_candidates = [
                candidate

                for candidate
                in permutations(
                    round_rows[2]
                )

                if (
                    series_are_disjoint(
                        candidate[0],
                        candidate[1],
                    )
                    and
                    series_are_disjoint(
                        candidate[2],
                        candidate[3],
                    )
                )
            ]


            round_3_candidates = [
                candidate

                for candidate
                in permutations(
                    round_rows[3]
                )

                if (
                    series_are_disjoint(
                        candidate[1],
                        candidate[2],
                    )
                    and
                    series_are_disjoint(
                        candidate[3],
                        candidate[4],
                    )
                )
            ]


            round_4_candidates = [
                candidate

                for candidate
                in permutations(
                    round_rows[4]
                )

                if (
                    series_are_disjoint(
                        candidate[0],
                        candidate[1],
                    )
                    and
                    series_are_disjoint(
                        candidate[2],
                        candidate[3],
                    )
                )
            ]


            ordered_series = None


            for round_2 in (
                round_2_candidates
            ):

                for round_3 in (
                    round_3_candidates
                ):

                    # =================
                    # 9/19
                    #
                    # R2 마지막 경기 +
                    # R3 첫 경기
                    # =================

                    if not (
                        series_are_disjoint(
                            round_2[4],
                            round_3[0],
                        )
                    ):

                        continue


                    for round_4 in (
                        round_4_candidates
                    ):

                        ordered_series = list(
                            round_2
                            + round_3
                            + round_4
                        )

                        break


                    if (
                        ordered_series
                        is not None
                    ):

                        break


                if (
                    ordered_series
                    is not None
                ):

                    break


            if (
                ordered_series
                is None
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "하루 2경기에 "
                        "4명의 서로 다른 참가자가 "
                        "배치되는 일정 조합을 "
                        "찾을 수 없습니다."
                    ),
                )


            # =========================
            # 월 / 수 / 토 경기일 생성
            #
            # Python weekday:
            #
            # 월 0
            # 화 1
            # 수 2
            # 목 3
            # 금 4
            # 토 5
            # 일 6
            # =========================

            allowed_weekdays = {
                0,
                2,
                5,
            }


            required_match_days = (
                (
                    len(
                        ordered_series
                    )
                    + 1
                )
                // 2
            )


            match_dates = []


            current_date = (
                first_schedule_date
            )


            while (
                len(match_dates)
                <
                required_match_days
            ):

                if (
                    current_date.weekday()
                    in allowed_weekdays
                ):

                    match_dates.append(
                        current_date
                    )


                current_date += timedelta(
                    days=1
                )


            # =========================
            # 최종 하루 참가자 중복 검증
            # =========================

            for index in range(
                0,
                len(ordered_series),
                2,
            ):

                if (
                    index + 1
                    >= len(
                        ordered_series
                    )
                ):

                    break


                first_series = (
                    ordered_series[
                        index
                    ]
                )

                second_series = (
                    ordered_series[
                        index + 1
                    ]
                )


                if not (
                    series_are_disjoint(
                        first_series,
                        second_series,
                    )
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "동일 경기일에 같은 "
                            "참가자가 두 번 배정되는 "
                            "일정이 발견되었습니다."
                        ),
                    )


            # =========================
            # Fixture 번호 임시 해제
            #
            # 순서를 재배치하므로
            # UNIQUE 충돌 방지
            # =========================

            for series_row in (
                series_rows
            ):

                cursor.execute(
                    """
                    UPDATE series

                    SET fixture_number = NULL

                    WHERE id = %s
                    """,
                    (
                        series_row["id"],
                    ),
                )


            # =========================
            # 새 일정 / Fixture 적용
            # =========================

            updated_schedules = []


            for (
                index,
                series_row,
            ) in enumerate(
                ordered_series
            ):

                fixture_number = (
                    first_fixture
                    + index
                )


                round_number = (
                    (
                        fixture_number - 1
                    )
                    // 5
                ) + 1


                match_day_index = (
                    index
                    // 2
                )


                scheduled_date = (
                    match_dates[
                        match_day_index
                    ]
                )


                cursor.execute(
                    """
                    UPDATE series

                    SET
                        fixture_number = %s,
                        scheduled_date = %s,
                        round_number = %s,
                        target_set_count = 2

                    WHERE id = %s
                    """,
                    (
                        fixture_number,
                        scheduled_date,
                        round_number,
                        series_row["id"],
                    ),
                )


                updated_schedules.append(
                    {
                        "series_id":
                            series_row[
                                "id"
                            ],

                        "fixture_number":
                            fixture_number,

                        "round":
                            round_number,

                        "scheduled_date":
                            scheduled_date
                                .isoformat(),

                        "target_set_count":
                            2,

                        "team_a":
                            series_row[
                                "team_a"
                            ],

                        "team_b":
                            series_row[
                                "team_b"
                            ],
                    }
                )


        connection.commit()


    return {
        "message": (
            "정규리그 일정 개편이 "
            "완료되었습니다."
        ),

        "rule": {
            "start_date":
                first_schedule_date
                    .isoformat(),

            "weekdays": [
                "월",
                "수",
                "토",
            ],

            "series_per_day":
                2,

            "unique_players_per_full_day":
                4,

            "sets_per_series":
                2,

            "first_fixture":
                first_fixture,

            "last_fixture":
                last_fixture,
        },

        "updated_count":
            len(
                updated_schedules
            ),

        "schedule":
            updated_schedules,
    }


# =========================
# ADMIN SERIES DELETE
# =========================

@app.delete(
    "/api/admin/series/{series_id}"
)
def admin_delete_series(
    series_id: int,
    admin_token: str =
        Depends(
            require_admin
        )
):

    removed_downstream_series = []

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    status,
                    scheduled_date
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
                    detail=(
                        "SERIES를 찾을 수 없습니다."
                    ),
                )


            if (
                series["status"]
                != "completed"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "완료된 경기만 "
                        "삭제할 수 있습니다."
                    ),
                )


            # =========================
            # 프리시즌
            #
            # SERIES 자체 삭제
            # 자식 데이터는 CASCADE 삭제
            # =========================

            if (
                series["series_type"]
                == "프리시즌"
            ):

                cursor.execute(
                    """
                    DELETE FROM series
                    WHERE id = %s
                    """,
                    (
                        series_id,
                    ),
                )


                result_action = (
                    "deleted"
                )


            # =========================
            # 정규리그
            #
            # 일정은 유지하고
            # 경기 결과만 초기화
            # =========================

            elif (
                series["series_type"]
                == "정규리그"
            ):

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
                        status = 'scheduled',
                        started_at = NULL,
                        completed_at = NULL,
                        finished_at = NULL,

                        stats_sync_status = 'pending',

                        team_a_snapshot_name = NULL,
                        team_a_snapshot_logo_path = NULL,

                        team_b_snapshot_name = NULL,
                        team_b_snapshot_logo_path = NULL

                    WHERE id = %s
                    """,
                    (
                        series_id,
                    ),
                )


                result_action = (
                    "reset"
                )

            # =========================
            # 플레이오프
            #
            # 현재 결과는 scheduled로 복구
            # 이후 자동 생성된 단계는 제거
            #
            # 단, 이후 단계가 이미
            # active/completed면 삭제 금지
            # =========================

            elif (
                series["series_type"]
                == "플레이오프"
            ):

                # =========================
                # 현재 단계 확인
                # =========================

                cursor.execute(
                    """
                    SELECT
                        playoff_stage

                    FROM series

                    WHERE id = %s

                    FOR UPDATE
                    """,
                    (
                        series_id,
                    ),
                )


                playoff_series = (
                    cursor.fetchone()
                )


                playoff_stage = (
                    playoff_series[
                        "playoff_stage"
                    ]
                )


                if playoff_stage not in (
                    "준플레이오프",
                    "플레이오프",
                    "결승시리즈",
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "플레이오프 단계를 "
                            "확인할 수 없습니다."
                        ),
                    )


                # =========================
                # 이후 단계 목록
                # =========================

                if (
                    playoff_stage
                    == "준플레이오프"
                ):

                    downstream_stages = [
                        "플레이오프",
                        "결승시리즈",
                    ]

                elif (
                    playoff_stage
                    == "플레이오프"
                ):

                    downstream_stages = [
                        "결승시리즈",
                    ]

                else:

                    downstream_stages = []


                downstream_series = []


                # =========================
                # 이후 단계 상태 확인
                # =========================

                if downstream_stages:

                    cursor.execute(
                        """
                        SELECT
                            id,
                            playoff_stage,
                            status

                        FROM series

                        WHERE
                            series_type =
                                '플레이오프'

                            AND
                            playoff_stage =
                                ANY(%s)

                            AND
                            status <>
                                'cancelled'

                        ORDER BY id

                        FOR UPDATE
                        """,
                        (
                            downstream_stages,
                        ),
                    )


                    downstream_series = (
                        cursor.fetchall()
                    )


                    for downstream in (
                        downstream_series
                    ):

                        if (
                            downstream["status"]
                            != "scheduled"
                        ):

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"{downstream['playoff_stage']}가 "
                                    "이미 시작되었거나 완료되어 "
                                    "이전 단계 결과를 "
                                    "삭제할 수 없습니다."
                                ),
                            )


                # =========================
                # 이후 자동 생성 SERIES 제거
                #
                # scheduled 상태만 여기까지
                # 통과했으므로 제거 가능
                # =========================

                removed_downstream_series = []


                for downstream in reversed(
                    downstream_series
                ):

                    cursor.execute(
                        """
                        DELETE FROM series

                        WHERE id = %s
                        """,
                        (
                            downstream["id"],
                        ),
                    )


                    removed_downstream_series.append(
                        {
                            "series_id":
                                downstream["id"],

                            "playoff_stage":
                                downstream[
                                    "playoff_stage"
                                ],
                        }
                    )


                # =========================
                # 현재 플레이오프 결과 제거
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
                # 현재 SERIES는 일정 유지
                # scheduled 상태로 복구
                # =========================

                cursor.execute(
                    """
                    UPDATE series

                    SET
                        status = 'scheduled',

                        started_at = NULL,
                        completed_at = NULL,
                        finished_at = NULL,

                        stats_sync_status =
                            'pending',

                        team_a_snapshot_name =
                            NULL,

                        team_a_snapshot_logo_path =
                            NULL,

                        team_b_snapshot_name =
                            NULL,

                        team_b_snapshot_logo_path =
                            NULL

                    WHERE id = %s
                    """,
                    (
                        series_id,
                    ),
                )


                result_action = (
                    "playoff_reset"
                )


            else:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "삭제할 수 없는 "
                        "경기 종류입니다."
                    ),
                )


        connection.commit()


    return {
        "series_id":
            series_id,

        "series_type":
            series["series_type"],

        "action":
            result_action,

        "removed_downstream_series":
            removed_downstream_series,

        "message":
            (
                "경기 결과가 "
                "삭제되었습니다."
            ),
    }

# =========================
# ADMIN SERIES RESULT UPDATE
# =========================

@app.put(
    "/api/admin/series/{series_id}/result"
)
def admin_update_series_result(
    series_id: int,
    request:
        AdminSeriesResultUpdateRequest,
    admin_token: str =
        Depends(
            require_admin
        ),
):

    edited_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    )


    requested_sets = [
        (
            1,
            request.set1_team_a,
            request.set1_team_b,
            request.set1_winner_side,
        ),
        (
            2,
            request.set2_team_a,
            request.set2_team_b,
            request.set2_winner_side,
        ),
        (
            3,
            request.set3_team_a,
            request.set3_team_b,
            request.set3_winner_side,
        ),
        (
            4,
            request.set4_team_a,
            request.set4_team_b,
            request.set4_winner_side,
        ),
        (
            5,
            request.set5_team_a,
            request.set5_team_b,
            request.set5_winner_side,
        ),
        (
            6,
            request.set6_team_a,
            request.set6_team_b,
            request.set6_winner_side,
        ),
        (
            7,
            request.set7_team_a,
            request.set7_team_b,
            request.set7_winner_side,
        ),
    ]


    bracket_updated = False
    next_stage = None
    next_series_missing = False


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    playoff_stage,
                    target_set_count,
                    best_of,
                    wins_required,
                    status,

                    team_a_id,
                    team_b_id,

                    completed_at,
                    finished_at

                FROM series

                WHERE id = %s

                FOR UPDATE
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
                series["status"]
                != "completed"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "완료된 경기 결과만 "
                        "수정할 수 있습니다."
                    ),
                )


            # =========================
            # 경기 종류별 세트 수
            # =========================

            is_playoff = (
                series["series_type"]
                == "플레이오프"
            )


            if is_playoff:

                if (
                    series["best_of"] is None
                    or
                    series["wins_required"] is None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "플레이오프 진행 정보가 "
                            "올바르지 않습니다."
                        ),
                    )


                max_sets = int(
                    series["best_of"]
                )

                wins_required = int(
                    series["wins_required"]
                )

            else:

                max_sets = (
                    get_series_target_set_count(
                        series
                    )
                )

                wins_required = None


            # =========================
            # 허용 세트 초과 방어
            # =========================

            for (
                set_number,
                team_a_score,
                team_b_score,
                explicit_winner_side,
            ) in requested_sets[max_sets:]:

                if (
                    team_a_score is not None
                    or team_b_score is not None
                    or explicit_winner_side is not None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{max_sets}세트를 초과하여 "
                            "결과를 입력할 수 없습니다."
                        ),
                    )


            # =========================
            # 기존 세트
            #
            # 기존 played_at 보존
            # 기존 플레이오프 승자 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    played_at,
                    winner_side

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )


            saved_sets = cursor.fetchall()


            if not saved_sets:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "저장된 경기 결과가 없습니다."
                    ),
                )


            saved_played_at = {
                saved_set["set_number"]:
                    saved_set["played_at"]

                for saved_set in saved_sets
            }


            current_winner_side = None


            if is_playoff:

                current_team_a_wins = 0
                current_team_b_wins = 0


                for saved_set in saved_sets:

                    if current_winner_side is not None:

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "기존 플레이오프 결과에 "
                                "선승 도달 이후 세트가 "
                                "존재합니다."
                            ),
                        )


                    winner_side = (
                        saved_set[
                            "winner_side"
                        ]
                    )


                    if winner_side == "team_a":

                        current_team_a_wins += 1

                    elif winner_side == "team_b":

                        current_team_b_wins += 1

                    else:

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "기존 플레이오프의 "
                                "세트 승패 정보가 "
                                "올바르지 않습니다."
                            ),
                        )


                    if (
                        current_team_a_wins
                        >= wins_required
                    ):

                        current_winner_side = (
                            "team_a"
                        )

                    elif (
                        current_team_b_wins
                        >= wins_required
                    ):

                        current_winner_side = (
                            "team_b"
                        )


                if current_winner_side is None:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "기존 플레이오프의 "
                            "SERIES 승자를 "
                            "확인할 수 없습니다."
                        ),
                    )


            # =========================
            # 수정 결과 검증
            # =========================

            updated_sets = []

            gap_found = False

            team_a_wins = 0
            team_b_wins = 0

            series_winner_side = None
            winning_set_number = None


            for (
                set_number,
                team_a_score,
                team_b_score,
                explicit_winner_side,
            ) in requested_sets[:max_sets]:

                # =========================
                # 둘 다 비어 있음
                # =========================

                if (
                    team_a_score is None
                    and team_b_score is None
                ):

                    if (
                        explicit_winner_side
                        is not None
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 점수 없이 "
                                "승자만 지정할 수 없습니다."
                            ),
                        )


                    gap_found = True
                    continue


                # =========================
                # 한쪽 점수만 입력
                # =========================

                if (
                    team_a_score is None
                    or team_b_score is None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{set_number}세트의 "
                            "양쪽 점수를 모두 입력해주세요."
                        ),
                    )


                # =========================
                # 중간 세트 공백
                # =========================

                if gap_found:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "중간 세트를 비워둔 채 "
                            "다음 세트를 입력할 수 없습니다."
                        ),
                    )


                # =========================
                # 음수 방어
                # =========================

                if (
                    team_a_score < 0
                    or team_b_score < 0
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "점수는 0 이상의 "
                            "정수여야 합니다."
                        ),
                    )


                # =========================
                # 세트 승자
                # =========================

                if team_a_score > team_b_score:

                    winner_side = "team_a"


                    if (
                        explicit_winner_side
                        is not None
                        and
                        explicit_winner_side
                        != winner_side
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 승자와 "
                                "입력 점수가 일치하지 않습니다."
                            ),
                        )


                elif team_b_score > team_a_score:

                    winner_side = "team_b"


                    if (
                        explicit_winner_side
                        is not None
                        and
                        explicit_winner_side
                        != winner_side
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 승자와 "
                                "입력 점수가 일치하지 않습니다."
                            ),
                        )


                else:

                    if not is_playoff:

                        winner_side = "draw"

                    else:

                        if (
                            explicit_winner_side
                            not in (
                                "team_a",
                                "team_b",
                            )
                        ):

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"{set_number}세트가 동점입니다. "
                                    "플레이오프에서는 실제 승자를 "
                                    "지정해야 합니다."
                                ),
                            )


                        winner_side = (
                            explicit_winner_side
                        )


                # =========================
                # 선승 이후 추가 세트 방어
                # =========================

                if (
                    is_playoff
                    and
                    series_winner_side
                    is not None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "선승 도달 이후의 "
                            "추가 세트가 입력되었습니다."
                        ),
                    )


                updated_sets.append(
                    (
                        set_number,
                        team_a_score,
                        team_b_score,
                        winner_side,
                    )
                )


                # =========================
                # 플레이오프 승수
                # =========================

                if is_playoff:

                    if winner_side == "team_a":

                        team_a_wins += 1

                    elif winner_side == "team_b":

                        team_b_wins += 1


                    if (
                        team_a_wins
                        >= wins_required
                    ):

                        series_winner_side = (
                            "team_a"
                        )

                        winning_set_number = (
                            set_number
                        )

                    elif (
                        team_b_wins
                        >= wins_required
                    ):

                        series_winner_side = (
                            "team_b"
                        )

                        winning_set_number = (
                            set_number
                        )


            # =========================
            # 일반 경기
            # =========================

            if not is_playoff:

                if (
                    len(updated_sets)
                    != max_sets
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{series['series_type']}는 "
                            f"{max_sets}세트를 모두 "
                            "입력해야 합니다."
                        ),
                    )


            # =========================
            # 플레이오프
            # 선승 도달 필수
            # =========================

            else:

                if series_winner_side is None:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{wins_required}승에 도달한 "
                            "참가자가 없습니다."
                        ),
                    )


            # =========================
            # 플레이오프 승자 변경 시
            # 다음 단계 대진 보호
            # =========================

            if (
                is_playoff
                and
                series[
                    "playoff_stage"
                ]
                in (
                    "준플레이오프",
                    "플레이오프",
                )
            ):

                if (
                    series["playoff_stage"]
                    == "준플레이오프"
                ):

                    next_stage = "플레이오프"

                else:

                    next_stage = "결승시리즈"


                cursor.execute(
                    """
                    SELECT
                        id,
                        status,
                        team_a_id,
                        team_b_id

                    FROM series

                    WHERE
                        series_type =
                            '플레이오프'

                        AND
                        playoff_stage = %s

                        AND
                        status <>
                            'cancelled'

                    ORDER BY id DESC

                    LIMIT 1

                    FOR UPDATE
                    """,
                    (
                        next_stage,
                    ),
                )


                next_series = (
                    cursor.fetchone()
                )


                if next_series:

                    current_winner_id = (
                        series["team_a_id"]
                        if
                        current_winner_side
                        == "team_a"
                        else
                        series["team_b_id"]
                    )


                    new_winner_id = (
                        series["team_a_id"]
                        if
                        series_winner_side
                        == "team_a"
                        else
                        series["team_b_id"]
                    )


                    # =========================
                    # 승자가 바뀌는 경우만
                    # 다음 단계 영향
                    # =========================

                    if (
                        new_winner_id
                        != current_winner_id
                    ):

                        if (
                            next_series["status"]
                            != "scheduled"
                        ):

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"{next_stage}가 이미 "
                                    "시작되었거나 완료되어 "
                                    "이전 단계 승자를 "
                                    "변경할 수 없습니다."
                                ),
                            )


                        if (
                            next_series["team_a_id"]
                            == new_winner_id
                        ):

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    "수정된 승자와 "
                                    "다음 단계 시드 참가자가 "
                                    "같습니다."
                                ),
                            )


                        cursor.execute(
                            """
                            SELECT COUNT(*) AS count

                            FROM series_sets

                            WHERE series_id = %s
                            """,
                            (
                                next_series["id"],
                            ),
                        )


                        next_set_count = int(
                            cursor.fetchone()[
                                "count"
                            ]
                        )


                        if next_set_count > 0:

                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    "다음 단계에 이미 "
                                    "세트 결과가 존재하여 "
                                    "승자를 변경할 수 없습니다."
                                ),
                            )


                        # 다음 단계의 team_b는
                        # 이전 단계 승자
                        cursor.execute(
                            """
                            UPDATE series

                            SET
                                team_b_id = %s,

                                team_b_snapshot_name =
                                    NULL,

                                team_b_snapshot_logo_path =
                                    NULL

                            WHERE id = %s
                            """,
                            (
                                new_winner_id,
                                next_series["id"],
                            ),
                        )


                        bracket_updated = True

                else:

                    next_series_missing = True


            # =========================
            # 기존 결과 제거
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
            # 수정 세트 저장
            # =========================

            for (
                set_number,
                team_a_score,
                team_b_score,
                winner_side,
            ) in updated_sets:

                played_at = (
                    saved_played_at.get(
                        set_number
                    )
                    or
                    series["finished_at"]
                    or
                    series["completed_at"]
                    or
                    edited_at
                )


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,
                        set_number,
                        nexon_match_id,
                        played_at,
                        team_a_score,
                        team_b_score,
                        score_source,
                        winner_side
                    )

                    VALUES (
                        %s,
                        %s,
                        NULL,
                        %s,
                        %s,
                        %s,
                        'manual',
                        %s
                    )
                    """,
                    (
                        series_id,
                        set_number,
                        played_at,
                        team_a_score,
                        team_b_score,
                        winner_side,
                    ),
                )


            # =========================
            # 관리자 수정 후
            # NEXON 통계 재동기화 대기
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    stats_sync_status =
                        'pending'

                WHERE id = %s
                """,
                (
                    series_id,
                ),
            )


        connection.commit()


    # =========================
    # 다음 단계가 없는 경우
    # 자동 진행 복구 시도
    # =========================

    progression_warning = None


    if (
        is_playoff
        and
        next_series_missing
    ):

        try:

            create_next_playoff_if_ready(
                series_id
            )

        except Exception as error:

            print(
                "[PLAYOFF ADMIN EDIT "
                "ADVANCE ERROR]",
                repr(error),
            )

            progression_warning = (
                "결과 수정은 완료됐지만 "
                "다음 플레이오프 생성에 "
                "실패했습니다."
            )


    return {
        "series_id":
            series_id,

        "status":
            "completed",

        "stats_sync_status":
            "pending",

        "series_type":
            series["series_type"],

        "playoff_stage":
            series["playoff_stage"],

        "best_of":
            series["best_of"],

        "wins_required":
            series["wins_required"],

        "team_a_wins":
            (
                team_a_wins
                if is_playoff
                else None
            ),

        "team_b_wins":
            (
                team_b_wins
                if is_playoff
                else None
            ),

        "winner_side":
            (
                series_winner_side
                if is_playoff
                else None
            ),

        "winning_set":
            (
                winning_set_number
                if is_playoff
                else None
            ),

        "bracket_updated":
            bracket_updated,

        "progression_warning":
            progression_warning,

        "sets": [
            {
                "set":
                    set_number,

                "team_a_score":
                    team_a_score,

                "team_b_score":
                    team_b_score,

                "winner_side":
                    winner_side,
            }

            for (
                set_number,
                team_a_score,
                team_b_score,
                winner_side,
            ) in updated_sets
        ],

        "message":
            "경기 결과가 수정되었습니다.",
    }

# =========================
# PREDICTIONS
# 승부예측 가능 경기 조회
# =========================

# =========================
# PREDICTIONS
# 승부예측 대상 경기 조회
# =========================

@app.get(
    "/api/predictions/matches"
)
def get_prediction_matches():

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 표시할 경기 날짜 결정
            #
            # 1. 오늘 경기 있으면 오늘
            # 2. 없으면 가장 가까운 다음 경기일
            # =========================

            cursor.execute(
                """
                SELECT
                    MIN(scheduled_date)
                        AS target_date

                FROM series

                WHERE
                    series_type = '정규리그'

                    AND scheduled_date
                        IS NOT NULL

                    AND scheduled_date >= %s

                    AND status <> 'cancelled'
                """,
                (
                    today,
                ),
            )


            target_row = (
                cursor.fetchone()
            )


            target_date = (
                target_row["target_date"]
                if target_row
                else None
            )


            # 앞으로 남은 정규리그가 없음
            if target_date is None:

                return []


            # =========================
            # 해당 날짜의 경기 전부 조회
            #
            # 같은 날 2경기면
            # 둘 다 반환
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id AS series_id,
                    s.fixture_number,
                    s.round_number,
                    s.scheduled_date,
                    s.status,
                    s.started_at,
                    s.target_set_count,

                    team_a.id
                        AS team_a_id,

                    team_a.fcl_name
                        AS team_a_fcl_name,

                    team_a.current_team_name
                        AS team_a_team_name,

                    team_a.current_team_logo_path
                        AS team_a_logo_path,

                    team_b.id
                        AS team_b_id,

                    team_b.fcl_name
                        AS team_b_fcl_name,

                    team_b.current_team_name
                        AS team_b_team_name,

                    team_b.current_team_logo_path
                        AS team_b_logo_path

                FROM series AS s

                INNER JOIN participants
                    AS team_a

                    ON team_a.id =
                        s.team_a_id

                INNER JOIN participants
                    AS team_b

                    ON team_b.id =
                        s.team_b_id

                WHERE
                    s.series_type =
                        '정규리그'

                    AND s.scheduled_date =
                        %s

                    AND s.status <>
                        'cancelled'

                ORDER BY
                    s.fixture_number ASC,
                    s.id ASC
                """,
                (
                    target_date,
                ),
            )


            rows = cursor.fetchall()


    matches = []


    for row in rows:

        # =========================
        # 예측 가능 여부
        #
        # 경기 당일부터는 마감
        # =========================

        is_open = (
            row["scheduled_date"] > today
            and row["status"] == "scheduled"
        )


        matches.append(
            {
                "series_id":
                    row["series_id"],

                "fixture_number":
                    row[
                        "fixture_number"
                    ],

                "round":
                    row[
                        "round_number"
                    ],

                "date":
                    (
                        row[
                            "scheduled_date"
                        ].isoformat()

                        if row[
                            "scheduled_date"
                        ]

                        else None
                    ),

                "status":
                    row["status"],

                "is_open":
                    is_open,

                "target_set_count":
                    int(
                        row[
                            "target_set_count"
                        ]
                        or 3
                    ),

                "odds": {
                    "team_a":
                        PREDICTION_FIXED_ODDS,

                    "draw":
                        PREDICTION_FIXED_ODDS,

                    "team_b":
                        PREDICTION_FIXED_ODDS,
                },

                "max_stake_points":
                    PREDICTION_MAX_STAKE_POINTS,

                "team_a": {
                    "participant_id":
                        row[
                            "team_a_id"
                        ],

                    "fcl_name":
                        row[
                            "team_a_fcl_name"
                        ],

                    "team_name":
                        row[
                            "team_a_team_name"
                        ],

                    "logo_path":
                        row[
                            "team_a_logo_path"
                        ],
                },

                "team_b": {
                    "participant_id":
                        row[
                            "team_b_id"
                        ],

                    "fcl_name":
                        row[
                            "team_b_fcl_name"
                        ],

                    "team_name":
                        row[
                            "team_b_team_name"
                        ],

                    "logo_path":
                        row[
                            "team_b_logo_path"
                        ],
                },
            }
        )


    return matches

# =========================
# ATTENDANCE EVENT
# 출석체크 상태 조회
# =========================

@app.get(
    "/api/events/attendance"
)
def get_attendance_status(
    user = Depends(require_user)
):

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 전체 출석 횟수
            # =========================

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_count

                FROM attendance_records

                WHERE user_id = %s
                """,
                (
                    user["id"],
                ),
            )


            total_row = cursor.fetchone()


            total_count = int(
                total_row[
                    "total_count"
                ]
                or 0
            )


            # =========================
            # 오늘 출석 여부
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    attendance_date,
                    streak_count,
                    base_reward_points,
                    streak_bonus_points,
                    reward_points

                FROM attendance_records

                WHERE
                    user_id = %s
                    AND
                    attendance_date = %s

                LIMIT 1
                """,
                (
                    user["id"],
                    today,
                ),
            )


            today_record = cursor.fetchone()


            # =========================
            # 가장 최근 출석
            # =========================

            cursor.execute(
                """
                SELECT
                    attendance_date,
                    streak_count,

                    (
                        attendance_date
                        =
                        (%s::date - 1)
                    ) AS is_yesterday

                FROM attendance_records

                WHERE user_id = %s

                ORDER BY
                    attendance_date DESC

                LIMIT 1
                """,
                (
                    today,
                    user["id"],
                ),
            )


            latest_record = cursor.fetchone()

            # =========================
            # 이번 달 출석 기록
            # =========================

            month_start = (
                today.replace(
                    day=1
                )
            )


            if today.month == 12:

                next_month_start = (
                    today.replace(
                        year=today.year + 1,
                        month=1,
                        day=1,
                    )
                )

            else:

                next_month_start = (
                    today.replace(
                        month=today.month + 1,
                        day=1,
                    )
                )


            cursor.execute(
                """
                SELECT
                    attendance_date

                FROM attendance_records

                WHERE
                    user_id = %s
                    AND
                    attendance_date >= %s
                    AND
                    attendance_date < %s

                ORDER BY
                    attendance_date ASC
                """,
                (
                    user["id"],
                    month_start,
                    next_month_start,
                ),
            )


            month_records = (
                cursor.fetchall()
            )

    month_attendance_dates = [
        record[
            "attendance_date"
        ].isoformat()

        for record
        in month_records
    ]


    current_month = (
        today.strftime(
            "%Y-%m"
        )
    )


    # =========================
    # 이미 오늘 출석함
    # =========================

    if today_record:

        current_streak = int(
            today_record[
                "streak_count"
            ]
        )


        today_reward_points = int(
            today_record[
                "reward_points"
            ]
        )


        streak_bonus_points = int(
            today_record[
                "streak_bonus_points"
            ]
        )

        month_attendance_dates = [
            record[
                "attendance_date"
            ].isoformat()

            for record
            in month_records
        ]


        current_month = (
            today.strftime(
                "%Y-%m"
            )
        )


        return {
            "today_attended":
                True,

            "attendance_date":
                today.isoformat(),

            "current_month":
                current_month,

            "month_attendance_dates":
                month_attendance_dates,

            "total_count":
                total_count,

            "current_streak":
                current_streak,

            "daily_reward_points":
                ATTENDANCE_DAILY_REWARD,

            "streak_days":
                ATTENDANCE_STREAK_DAYS,

            "streak_bonus_points":
                ATTENDANCE_STREAK_BONUS,

            "today_streak_bonus":
                streak_bonus_points,

            "today_reward_points":
                today_reward_points,
        }


    # =========================
    # 아직 오늘 출석하지 않음
    # 오늘 출석 시 연속 일수 계산
    # =========================

    if (
        latest_record
        and
        latest_record[
            "is_yesterday"
        ]
    ):

        current_streak = int(
            latest_record[
                "streak_count"
            ]
        )


        next_streak = (
            current_streak
            + 1
        )

    else:

        current_streak = 0

        next_streak = 1


    will_get_streak_bonus = (
        next_streak
        % ATTENDANCE_STREAK_DAYS
        == 0
    )


    today_streak_bonus = (
        ATTENDANCE_STREAK_BONUS
        if will_get_streak_bonus
        else 0
    )


    today_reward_points = (
        ATTENDANCE_DAILY_REWARD
        +
        today_streak_bonus
    )

    month_attendance_dates = [
        record[
            "attendance_date"
        ].isoformat()

        for record
        in month_records
    ]


    current_month = (
        today.strftime(
            "%Y-%m"
        )
    )


    return {
        "today_attended":
            False,

        "attendance_date":
            today.isoformat(),

        "current_month":
            current_month,

        "month_attendance_dates":
            month_attendance_dates,

        "total_count":
            total_count,

        "current_streak":
            current_streak,

        "next_streak":
            next_streak,

        "daily_reward_points":
            ATTENDANCE_DAILY_REWARD,

        "streak_days":
            ATTENDANCE_STREAK_DAYS,

        "streak_bonus_points":
            ATTENDANCE_STREAK_BONUS,

        "today_streak_bonus":
            today_streak_bonus,

        "today_reward_points":
            today_reward_points,
    }


# =========================
# ATTENDANCE EVENT
# 출석체크 실행
# =========================

@app.post(
    "/api/events/attendance"
)
def check_attendance(
    user = Depends(require_user)
):

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 회원 잠금
            # 동시에 여러 번 요청되어도
            # 중복 지급 방지
            # =========================

            cursor.execute(
                """
                SELECT
                    id

                FROM users

                WHERE id = %s

                FOR UPDATE
                """,
                (
                    user["id"],
                ),
            )


            locked_user = cursor.fetchone()


            if not locked_user:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "회원 정보를 "
                        "찾을 수 없습니다."
                    ),
                )


            # =========================
            # 오늘 이미 출석했는지 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id

                FROM attendance_records

                WHERE
                    user_id = %s
                    AND
                    attendance_date = %s

                LIMIT 1
                """,
                (
                    user["id"],
                    today,
                ),
            )


            existing_record = cursor.fetchone()


            if existing_record:

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "오늘은 이미 "
                        "출석체크를 완료했습니다."
                    ),
                )


            # =========================
            # 가장 최근 출석 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    attendance_date,
                    streak_count,

                    (
                        attendance_date
                        =
                        (%s::date - 1)
                    ) AS is_yesterday

                FROM attendance_records

                WHERE user_id = %s

                ORDER BY
                    attendance_date DESC

                LIMIT 1
                """,
                (
                    today,
                    user["id"],
                ),
            )


            latest_record = cursor.fetchone()


            # =========================
            # 연속 출석 계산
            # =========================

            if (
                latest_record
                and
                latest_record[
                    "is_yesterday"
                ]
            ):

                streak_count = (
                    int(
                        latest_record[
                            "streak_count"
                        ]
                    )
                    + 1
                )

            else:

                streak_count = 1


            # =========================
            # 7일 단위 보너스
            # 7 / 14 / 21 / 28 ...
            # =========================

            if (
                streak_count
                % ATTENDANCE_STREAK_DAYS
                == 0
            ):

                streak_bonus_points = (
                    ATTENDANCE_STREAK_BONUS
                )

            else:

                streak_bonus_points = 0


            reward_points = (
                ATTENDANCE_DAILY_REWARD
                +
                streak_bonus_points
            )


            # =========================
            # 출석 기록 저장
            # =========================

            cursor.execute(
                """
                INSERT INTO attendance_records (
                    user_id,
                    attendance_date,
                    streak_count,
                    base_reward_points,
                    streak_bonus_points,
                    reward_points
                )

                VALUES (
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
                    user["id"],
                    today,
                    streak_count,
                    ATTENDANCE_DAILY_REWARD,
                    streak_bonus_points,
                    reward_points,
                ),
            )


            attendance_row = cursor.fetchone()


            attendance_id = (
                attendance_row[
                    "id"
                ]
            )


            # =========================
            # 포인트 지급
            # =========================

            description = (
                f"FCL 출석체크 "
                f"{streak_count}일차"
            )


            if streak_bonus_points > 0:

                description += (
                    " + 연속 출석 보너스"
                )


            change_user_points(
                cursor,
                user["id"],
                reward_points,
                "attendance_reward",
                reference_type=
                    "attendance",
                reference_id=
                    attendance_id,
                description=
                    description,
            )


            # =========================
            # 지급 후 포인트 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    points

                FROM users

                WHERE id = %s
                """,
                (
                    user["id"],
                ),
            )


            user_row = cursor.fetchone()


            current_points = int(
                user_row[
                    "points"
                ]
            )


        connection.commit()


    return {
        "status":
            "success",

        "attendance_id":
            attendance_id,

        "attendance_date":
            today.isoformat(),

        "streak_count":
            streak_count,

        "base_reward_points":
            ATTENDANCE_DAILY_REWARD,

        "streak_bonus_points":
            streak_bonus_points,

        "reward_points":
            reward_points,

        "current_points":
            current_points,

        "message":
            (
                f"출석체크 완료! "
                f"{reward_points}P가 지급되었습니다."
            ),
    }

# =========================
# ADMIN POINT SHOP
# 교환 신청 목록 조회
# =========================

@app.get(
    "/api/admin/point-shop/exchanges"
)
def get_admin_point_shop_exchanges(
    admin_token = Depends(
        require_admin
    )
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    e.id,
                    e.user_id,
                    u.nickname,
                    u.email,

                    e.product_id,
                    e.product_name,
                    e.price_points,

                    e.status,
                    e.created_at,
                    e.completed_at

                FROM point_shop_exchanges e

                JOIN users u
                    ON u.id = e.user_id

                ORDER BY
                    CASE
                        WHEN e.status = 'requested'
                            THEN 0
                        WHEN e.status = 'completed'
                            THEN 1
                        ELSE 2
                    END,

                    e.created_at DESC,
                    e.id DESC
                """
            )


            exchanges = cursor.fetchall()


    return [
        {
            "id":
                exchange["id"],

            "user_id":
                exchange["user_id"],

            "nickname":
                exchange["nickname"],

            "email":
                exchange["email"],

            "product_id":
                exchange["product_id"],

            "product_name":
                exchange["product_name"],

            "price_points":
                int(
                    exchange[
                        "price_points"
                    ]
                ),

            "status":
                exchange["status"],

            "created_at":
                exchange[
                    "created_at"
                ].isoformat(),

            "completed_at":
                (
                    exchange[
                        "completed_at"
                    ].isoformat()

                    if exchange[
                        "completed_at"
                    ]

                    else None
                ),
        }

        for exchange
        in exchanges
    ]

# =========================
# ADMIN POINT SHOP
# 교환 처리 완료
# =========================

@app.patch(
    "/api/admin/point-shop/exchanges/{exchange_id}/complete"
)
def complete_admin_point_shop_exchange(
    exchange_id: int,

    admin_token = Depends(
        require_admin
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 교환 신청 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    user_id,
                    product_name,
                    price_points,
                    status,
                    created_at,
                    completed_at

                FROM point_shop_exchanges

                WHERE
                    id = %s

                FOR UPDATE
                """,
                (
                    exchange_id,
                ),
            )


            exchange = (
                cursor.fetchone()
            )


            if not exchange:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "교환 신청을 찾을 수 없습니다."
                    ),
                )


            if (
                exchange["status"]
                == "completed"
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "이미 처리 완료된 교환 신청입니다."
                    ),
                )


            if (
                exchange["status"]
                != "requested"
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "처리할 수 없는 교환 상태입니다."
                    ),
                )


            # =========================
            # 완료 처리
            # =========================

            cursor.execute(
                """
                UPDATE point_shop_exchanges

                SET
                    status = 'completed',
                    completed_at = NOW()

                WHERE
                    id = %s

                RETURNING
                    id,
                    user_id,
                    product_name,
                    price_points,
                    status,
                    created_at,
                    completed_at
                """,
                (
                    exchange_id,
                ),
            )


            completed_exchange = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "status":
            "success",

        "message":
            "교환 신청이 처리 완료되었습니다.",

        "exchange": {
            "id":
                completed_exchange["id"],

            "user_id":
                completed_exchange["user_id"],

            "product_name":
                completed_exchange["product_name"],

            "price_points":
                int(
                    completed_exchange[
                        "price_points"
                    ]
                ),

            "status":
                completed_exchange["status"],

            "created_at":
                completed_exchange[
                    "created_at"
                ].isoformat(),

            "completed_at":
                completed_exchange[
                    "completed_at"
                ].isoformat(),
        },
    }

# =========================
# ADMIN POINT SHOP
# 상품 전체 조회
# =========================

@app.get(
    "/api/admin/point-shop/products"
)
def get_admin_point_shop_products(
    admin_token = Depends(
        require_admin
    )
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    description,
                    price_points,
                    image_url,
                    is_active,
                    sort_order,
                    created_at,
                    updated_at

                FROM point_shop_products

                ORDER BY
                    sort_order ASC,
                    id ASC
                """
            )


            products = (
                cursor.fetchall()
            )


    return [
        {
            "id":
                product["id"],

            "name":
                product["name"],

            "category":
                product["category"],

            "description":
                product["description"],

            "price_points":
                int(
                    product[
                        "price_points"
                    ]
                ),

            "image_url":
                product["image_url"],

            "is_active":
                product["is_active"],

            "sort_order":
                product["sort_order"],

            "created_at":
                product[
                    "created_at"
                ].isoformat(),

            "updated_at":
                product[
                    "updated_at"
                ].isoformat(),
        }

        for product
        in products
    ]


# =========================
# ADMIN POINT SHOP
# 상품 등록
# =========================

@app.post(
    "/api/admin/point-shop/products"
)
def create_admin_point_shop_product(
    request:
        AdminPointShopProductCreateRequest,

    admin_token = Depends(
        require_admin
    ),
):

    name = (
        request.name.strip()
    )


    if not name:

        raise HTTPException(
            status_code=400,
            detail=(
                "상품명을 입력해주세요."
            ),
        )


    if (
        request.price_points
        <= 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "상품 가격은 1P 이상이어야 합니다."
            ),
        )


    if (
        request.sort_order
        < 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "정렬 순서는 0 이상이어야 합니다."
            ),
        )


    category = (
        request.category.strip()
        if request.category
        else None
    )


    description = (
        request.description.strip()
        if request.description
        else None
    )


    image_url = (
        request.image_url.strip()
        if request.image_url
        else None
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    point_shop_products (
                        name,
                        category,
                        description,
                        price_points,
                        image_url,
                        is_active,
                        sort_order
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

                RETURNING
                    id,
                    name,
                    category,
                    description,
                    price_points,
                    image_url,
                    is_active,
                    sort_order,
                    created_at,
                    updated_at
                """,
                (
                    name,
                    category,
                    description,
                    request.price_points,
                    image_url,
                    request.is_active,
                    request.sort_order,
                ),
            )


            product = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "status":
            "success",

        "message":
            "교환 상품이 등록되었습니다.",

        "product": {
            "id":
                product["id"],

            "name":
                product["name"],

            "category":
                product["category"],

            "description":
                product["description"],

            "price_points":
                int(
                    product[
                        "price_points"
                    ]
                ),

            "image_url":
                product["image_url"],

            "is_active":
                product["is_active"],

            "sort_order":
                product["sort_order"],
        },
    }


# =========================
# ADMIN POINT SHOP
# 상품 수정 / 판매 상태 변경
# =========================

@app.patch(
    "/api/admin/point-shop/products/{product_id}"
)
def update_admin_point_shop_product(
    product_id: int,

    request:
        AdminPointShopProductUpdateRequest,

    admin_token = Depends(
        require_admin
    ),
):

    name = (
        request.name.strip()
    )


    if not name:

        raise HTTPException(
            status_code=400,
            detail=(
                "상품명을 입력해주세요."
            ),
        )


    if (
        request.price_points
        <= 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "상품 가격은 1P 이상이어야 합니다."
            ),
        )


    if (
        request.sort_order
        < 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "정렬 순서는 0 이상이어야 합니다."
            ),
        )


    category = (
        request.category.strip()
        if request.category
        else None
    )


    description = (
        request.description.strip()
        if request.description
        else None
    )


    image_url = (
        request.image_url.strip()
        if request.image_url
        else None
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE point_shop_products

                SET
                    name = %s,
                    category = %s,
                    description = %s,
                    price_points = %s,
                    image_url = %s,
                    is_active = %s,
                    sort_order = %s,
                    updated_at = NOW()

                WHERE
                    id = %s

                RETURNING
                    id,
                    name,
                    category,
                    description,
                    price_points,
                    image_url,
                    is_active,
                    sort_order,
                    created_at,
                    updated_at
                """,
                (
                    name,
                    category,
                    description,
                    request.price_points,
                    image_url,
                    request.is_active,
                    request.sort_order,
                    product_id,
                ),
            )


            product = (
                cursor.fetchone()
            )


            if not product:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "교환 상품을 "
                        "찾을 수 없습니다."
                    ),
                )


        connection.commit()


    return {
        "status":
            "success",

        "message":
            "교환 상품이 수정되었습니다.",

        "product": {
            "id":
                product["id"],

            "name":
                product["name"],

            "category":
                product["category"],

            "description":
                product["description"],

            "price_points":
                int(
                    product[
                        "price_points"
                    ]
                ),

            "image_url":
                product["image_url"],

            "is_active":
                product["is_active"],

            "sort_order":
                product["sort_order"],
        },
    }

# =========================
# POINT SHOP
# 상품 목록
# =========================

@app.get(
    "/api/point-shop/products"
)
def get_point_shop_products():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    description,
                    price_points,
                    image_url,
                    sort_order

                FROM point_shop_products

                WHERE
                    is_active = TRUE

                ORDER BY
                    sort_order ASC,
                    id ASC
                """
            )


            products = (
                cursor.fetchall()
            )


    return [
        {
            "id":
                product["id"],

            "name":
                product["name"],

            "category":
                product["category"],

            "description":
                product["description"],

            "price_points":
                int(
                    product[
                        "price_points"
                    ]
                ),

            "image_url":
                product["image_url"],
        }

        for product
        in products
    ]


# =========================
# POINT SHOP
# 상품 교환
# =========================

@app.post(
    "/api/point-shop/exchanges"
)
def create_point_shop_exchange(
    request:
        PointShopExchangeRequest,

    user = Depends(
        require_user
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 상품 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    price_points,
                    is_active

                FROM point_shop_products

                WHERE
                    id = %s

                FOR SHARE
                """,
                (
                    request.product_id,
                ),
            )


            product = (
                cursor.fetchone()
            )


            if (
                not product
                or
                not product[
                    "is_active"
                ]
            ):

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "교환 가능한 상품을 "
                        "찾을 수 없습니다."
                    ),
                )


            price_points = int(
                product[
                    "price_points"
                ]
            )


            # =========================
            # 교환 내역 먼저 생성
            #
            # 뒤 포인트 차감 실패 시
            # 같은 트랜잭션이므로
            # 이 INSERT도 자동 롤백
            # =========================

            cursor.execute(
                """
                INSERT INTO
                    point_shop_exchanges (
                        user_id,
                        product_id,
                        product_name,
                        price_points,
                        status
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'requested'
                )

                RETURNING
                    id,
                    created_at
                """,
                (
                    user["id"],
                    product["id"],
                    product["name"],
                    price_points,
                ),
            )


            exchange = (
                cursor.fetchone()
            )


            # =========================
            # 포인트 차감
            # =========================

            point_transaction = (
                change_user_points(
                    cursor,

                    user["id"],

                    -price_points,

                    "point_shop_exchange",

                    reference_type=
                        "point_shop_exchange",

                    reference_id=
                        exchange["id"],

                    description=(
                        "포인트 교환소 - "
                        f"{product['name']}"
                    ),
                )
            )


        connection.commit()


    return {
        "status":
            "success",

        "message":
            (
                f"{product['name']} "
                "교환 신청이 완료되었습니다."
            ),

        "exchange": {
            "id":
                exchange["id"],

            "product_id":
                product["id"],

            "product_name":
                product["name"],

            "price_points":
                price_points,

            "status":
                "requested",

            "created_at":
                exchange[
                    "created_at"
                ].isoformat(),
        },

        "points": {
            "spent":
                price_points,

            "balance":
                point_transaction[
                    "balance_after"
                ],
        },
    }


# =========================
# POINT SHOP
# 내 교환 내역
# =========================

@app.get(
    "/api/point-shop/exchanges/me"
)
def get_my_point_shop_exchanges(
    user = Depends(
        require_user
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    product_id,
                    product_name,
                    price_points,
                    status,
                    created_at,
                    completed_at

                FROM point_shop_exchanges

                WHERE
                    user_id = %s

                ORDER BY
                    created_at DESC,
                    id DESC
                """,
                (
                    user["id"],
                ),
            )


            exchanges = (
                cursor.fetchall()
            )


    return [
        {
            "id":
                exchange["id"],

            "product_id":
                exchange["product_id"],

            "product_name":
                exchange["product_name"],

            "price_points":
                int(
                    exchange[
                        "price_points"
                    ]
                ),

            "status":
                exchange["status"],

            "created_at":
                exchange[
                    "created_at"
                ].isoformat(),

            "completed_at":
                (
                    exchange[
                        "completed_at"
                    ].isoformat()

                    if exchange[
                        "completed_at"
                    ]

                    else None
                ),
        }

        for exchange
        in exchanges
    ]

# =========================
# PREDICTIONS
# 세트별 승부예측 참여
# =========================

@app.post(
    "/api/predictions"
)
def create_prediction(
    request:
        PredictionCreateRequest,

    user = Depends(
        require_user
    ),
):

    # =========================
    # 기본 검증
    # =========================

    if request.set_number not in (
        1,
        2,
        3,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "세트 번호는 "
                "1, 2, 3 중 하나여야 합니다."
            ),
        )


    if request.stake_points <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "예측 포인트는 "
                "1P 이상이어야 합니다."
            ),
        )

    if (
        request.stake_points
        >
        PREDICTION_MAX_STAKE_POINTS
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "한 세트에는 최대 "
                f"{PREDICTION_MAX_STAKE_POINTS:,}P까지 "
                "예측할 수 있습니다."
            ),
        )


    prediction_type = (
        request.prediction_type
        .strip()
        .lower()
    )


    if prediction_type not in (
        "participant",
        "draw",
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "올바르지 않은 "
                "승부예측 유형입니다."
            ),
        )


    # 현재 배당은 기존과 동일
    prediction_odds = (
        PREDICTION_FIXED_ODDS
    )


    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()


    with get_db_connection() as connection:

        try:

            with connection.cursor() as cursor:

                # =========================
                # SERIES 확인
                # =========================

                cursor.execute(
                    """
                    SELECT
                        id,
                        series_type,
                        team_a_id,
                        team_b_id,
                        status,
                        scheduled_date,
                        started_at,
                        target_set_count

                    FROM series

                    WHERE id = %s

                    FOR UPDATE
                    """,
                    (
                        request.series_id,
                    ),
                )


                series = cursor.fetchone()


                if not series:

                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "경기를 찾을 수 없습니다."
                        ),
                    )


                # =========================
                # 정규리그만 가능
                # =========================

                if (
                    series[
                        "series_type"
                    ]
                    != "정규리그"
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "정규리그 경기만 "
                            "승부예측할 수 있습니다."
                        ),
                    )

                # =========================
                # 실제 SERIES 세트 수 확인
                # =========================

                target_set_count = int(
                    series[
                        "target_set_count"
                    ]
                    or 3
                )


                if (
                    request.set_number
                    >
                    target_set_count
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이 경기는 "
                            f"{target_set_count}세트 "
                            "경기입니다."
                        ),
                    )


                # =========================
                # 경기 날짜 확인
                # =========================

                if (
                    series[
                        "scheduled_date"
                    ]
                    is None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "경기 날짜가 "
                            "등록되지 않았습니다."
                        ),
                    )


                # =========================
                # 예측 마감
                #
                # 경기 전날까지만 가능
                # 경기 당일 00:00부터 마감
                # =========================

                if (
                    series[
                        "scheduled_date"
                    ]
                    <= today
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "승부예측은 "
                            "경기 전날까지만 "
                            "참여할 수 있습니다."
                        ),
                    )


                # =========================
                # SERIES 상태 확인
                # =========================

                if (
                    series["status"]
                    != "scheduled"
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이미 시작되었거나 "
                            "마감된 경기입니다."
                        ),
                    )


                # =========================
                # 예측 대상
                # =========================

                predicted_participant_id = (
                    None
                )


                if (
                    prediction_type
                    == "participant"
                ):

                    if (
                        request.participant_id
                        is None
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "예측할 참가자를 "
                                "선택해주세요."
                            ),
                        )


                    valid_participant_ids = {
                        int(
                            series[
                                "team_a_id"
                            ]
                        ),

                        int(
                            series[
                                "team_b_id"
                            ]
                        ),
                    }


                    if (
                        request.participant_id
                        not in
                        valid_participant_ids
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "해당 경기에 "
                                "참가하는 선수만 "
                                "선택할 수 있습니다."
                            ),
                        )


                    predicted_participant_id = (
                        request.participant_id
                    )


                elif (
                    prediction_type
                    == "draw"
                ):

                    if (
                        request.participant_id
                        is not None
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "무승부 예측에는 "
                                "참가자 ID가 "
                                "필요하지 않습니다."
                            ),
                        )


                # =========================
                # 같은 세트 중복 확인
                # =========================

                cursor.execute(
                    """
                    SELECT
                        id

                    FROM predictions

                    WHERE
                        user_id = %s

                        AND series_id = %s

                        AND set_number = %s
                    """,
                    (
                        user["id"],

                        request.series_id,

                        request.set_number,
                    ),
                )


                existing_prediction = (
                    cursor.fetchone()
                )


                if existing_prediction:

                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"이미 {request.set_number}세트 "
                            "승부예측에 참여했습니다."
                        ),
                    )


                # =========================
                # 예측 저장
                # =========================

                cursor.execute(
                    """
                    INSERT INTO predictions (
                        user_id,
                        series_id,
                        set_number,
                        predicted_participant_id,
                        prediction_type,
                        stake_points,
                        odds,
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
                        'pending'
                    )

                    RETURNING
                        id,
                        user_id,
                        series_id,
                        set_number,
                        predicted_participant_id,
                        prediction_type,
                        stake_points,
                        odds,
                        status,
                        created_at
                    """,
                    (
                        user["id"],

                        request.series_id,

                        request.set_number,

                        predicted_participant_id,

                        prediction_type,

                        request.stake_points,

                        prediction_odds,
                    ),
                )


                prediction = (
                    cursor.fetchone()
                )


                # =========================
                # 포인트 차감
                # =========================

                point_transaction = (
                    change_user_points(
                        cursor,

                        user["id"],

                        -request.stake_points,

                        "prediction_bet",

                        reference_type=
                            "prediction",

                        reference_id=
                            prediction["id"],

                        description=(
                            "FCL 승부예측 "
                            f"{request.set_number}세트 참여"
                        ),
                    )
                )


            connection.commit()


        except psycopg.errors.UniqueViolation:

            connection.rollback()

            raise HTTPException(
                status_code=409,
                detail=(
                    f"이미 {request.set_number}세트 "
                    "승부예측에 참여했습니다."
                ),
            )


    return {
        "status":
            "success",

        "message":
            (
                f"{request.set_number}세트 "
                "승부예측 참여가 완료되었습니다."
            ),

        "prediction": {

            "id":
                prediction["id"],

            "series_id":
                prediction[
                    "series_id"
                ],

            "set_number":
                prediction[
                    "set_number"
                ],

            "prediction_type":
                prediction[
                    "prediction_type"
                ],

            "participant_id":
                prediction[
                    "predicted_participant_id"
                ],

            "stake_points":
                prediction[
                    "stake_points"
                ],

            "odds":
                float(
                    prediction["odds"]
                ),

            "status":
                prediction[
                    "status"
                ],

            "created_at":
                prediction[
                    "created_at"
                ].isoformat(),
        },

        "points": {

            "spent":
                request.stake_points,

            "balance":
                point_transaction[
                    "balance_after"
                ],
        },
    }


# =========================
# PREDICTIONS
# 내 세트별 승부예측 조회
# =========================

@app.get(
    "/api/predictions/me"
)
def get_my_predictions(
    user = Depends(
        require_user
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    p.id,
                    p.series_id,
                    p.set_number,
                    p.prediction_type,
                    p.predicted_participant_id,
                    p.stake_points,
                    p.odds,
                    p.status,
                    p.payout_points,
                    p.settled_at,
                    p.created_at,

                    s.fixture_number,
                    s.round_number,
                    s.scheduled_date,
                    s.status
                        AS series_status,

                    s.team_a_id,
                    s.team_b_id,

                    team_a.fcl_name
                        AS team_a_fcl_name,

                    team_a.current_team_name
                        AS team_a_team_name,

                    team_a.current_team_logo_path
                        AS team_a_logo_path,

                    team_b.fcl_name
                        AS team_b_fcl_name,

                    team_b.current_team_name
                        AS team_b_team_name,

                    team_b.current_team_logo_path
                        AS team_b_logo_path

                FROM predictions AS p

                INNER JOIN series AS s
                    ON s.id =
                        p.series_id

                INNER JOIN participants
                    AS team_a

                    ON team_a.id =
                        s.team_a_id

                INNER JOIN participants
                    AS team_b

                    ON team_b.id =
                        s.team_b_id

                WHERE
                    p.user_id = %s

                ORDER BY
                    s.scheduled_date DESC,
                    s.fixture_number DESC,
                    p.set_number ASC,
                    p.id ASC
                """,
                (
                    user["id"],
                ),
            )


            rows = cursor.fetchall()


    predictions = []


    for row in rows:

        if (
            row["prediction_type"]
            == "draw"
        ):

            selection_side = "draw"
            selection_name = "무승부"


        elif (
            row[
                "predicted_participant_id"
            ]
            ==
            row["team_a_id"]
        ):

            selection_side = "team_a"

            selection_name = (
                row[
                    "team_a_fcl_name"
                ]
            )


        elif (
            row[
                "predicted_participant_id"
            ]
            ==
            row["team_b_id"]
        ):

            selection_side = "team_b"

            selection_name = (
                row[
                    "team_b_fcl_name"
                ]
            )


        else:

            selection_side = "unknown"
            selection_name = "알 수 없음"


        predictions.append(
            {
                "id":
                    row["id"],

                "series_id":
                    row[
                        "series_id"
                    ],

                "set_number":
                    row[
                        "set_number"
                    ],

                "fixture_number":
                    row[
                        "fixture_number"
                    ],

                "round":
                    row[
                        "round_number"
                    ],

                "date":
                    (
                        row[
                            "scheduled_date"
                        ].isoformat()

                        if row[
                            "scheduled_date"
                        ]

                        else None
                    ),

                "series_status":
                    row[
                        "series_status"
                    ],

                "prediction_type":
                    row[
                        "prediction_type"
                    ],

                "selection_side":
                    selection_side,

                "selection_name":
                    selection_name,

                "stake_points":
                    row[
                        "stake_points"
                    ],

                "odds":
                    float(
                        row["odds"]
                    ),

                "expected_payout":
                    int(
                        row[
                            "stake_points"
                        ]
                        *
                        float(
                            row["odds"]
                        )
                    ),

                "status":
                    row["status"],

                "payout_points":
                    row[
                        "payout_points"
                    ],

                "team_a": {

                    "participant_id":
                        row[
                            "team_a_id"
                        ],

                    "fcl_name":
                        row[
                            "team_a_fcl_name"
                        ],

                    "team_name":
                        row[
                            "team_a_team_name"
                        ],

                    "logo_path":
                        row[
                            "team_a_logo_path"
                        ],
                },

                "team_b": {

                    "participant_id":
                        row[
                            "team_b_id"
                        ],

                    "fcl_name":
                        row[
                            "team_b_fcl_name"
                        ],

                    "team_name":
                        row[
                            "team_b_team_name"
                        ],

                    "logo_path":
                        row[
                            "team_b_logo_path"
                        ],
                },

                "created_at":
                    row[
                        "created_at"
                    ].isoformat(),

                "settled_at":
                    (
                        row[
                            "settled_at"
                        ].isoformat()

                        if row[
                            "settled_at"
                        ]

                        else None
                    ),
            }
        )


    return predictions

# =========================
# PREDICTIONS
# 자동 정산 테스트
#
# 실제 DB 변경 없음
# 마지막에 무조건 ROLLBACK
# =========================

@app.post(
    "/api/admin/predictions/settlement-test"
)
def test_prediction_settlement(
    request:
        PredictionSettlementTestRequest,

    admin_user = Depends(
        require_user_admin
    ),
):

    with get_db_connection() as connection:

        try:

            with connection.cursor() as cursor:

                # =========================
                # SERIES 확인
                # =========================

                cursor.execute(
                    """
                    SELECT
                        id,
                        series_type,
                        status,
                        team_a_id,
                        team_b_id

                    FROM series

                    WHERE id = %s

                    FOR UPDATE
                    """,
                    (
                        request.series_id,
                    ),
                )


                series = cursor.fetchone()


                if not series:

                    raise HTTPException(
                        status_code=404,
                        detail=(
                            "경기를 찾을 수 없습니다."
                        ),
                    )


                if (
                    series["series_type"]
                    != "정규리그"
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "정규리그 경기만 "
                            "정산 테스트할 수 있습니다."
                        ),
                    )


                # =========================
                # 현재 pending 예측 조회
                # =========================

                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.user_id,
                        p.set_number,
                        p.prediction_type,
                        p.predicted_participant_id,
                        p.stake_points,
                        p.odds,
                        p.status,

                        u.nickname,
                        u.points

                    FROM predictions AS p

                    INNER JOIN users AS u
                        ON u.id =
                            p.user_id

                    WHERE
                        p.series_id = %s

                        AND p.status =
                            'pending'

                    ORDER BY
                        p.set_number,
                        p.id
                    """,
                    (
                        request.series_id,
                    ),
                )


                before_predictions = (
                    cursor.fetchall()
                )


                if (
                    len(
                        before_predictions
                    )
                    == 0
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이 경기에 정산 테스트할 "
                            "pending 예측이 없습니다."
                        ),
                    )


                before_points = {
                    int(
                        row["user_id"]
                    ):
                        int(
                            row["points"]
                        )

                    for row
                    in before_predictions
                }


                # =========================
                # 테스트용 경기 완료 처리
                #
                # ROLLBACK되므로
                # 실제 상태는 바뀌지 않음
                # =========================

                cursor.execute(
                    """
                    UPDATE series

                    SET
                        status =
                            'completed'

                    WHERE id = %s
                    """,
                    (
                        request.series_id,
                    ),
                )


                # =========================
                # 테스트 세트 결과
                # =========================

                test_sets = [
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


                for (
                    set_number,
                    team_a_score,
                    team_b_score,
                ) in test_sets:

                    if (
                        team_a_score < 0
                        or
                        team_b_score < 0
                    ):

                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "세트 점수는 "
                                "0 이상이어야 합니다."
                            ),
                        )


                    if (
                        team_a_score
                        >
                        team_b_score
                    ):

                        winner_side = (
                            "team_a"
                        )


                    elif (
                        team_a_score
                        <
                        team_b_score
                    ):

                        winner_side = (
                            "team_b"
                        )


                    else:

                        winner_side = (
                            "draw"
                        )


                    cursor.execute(
                        """
                        INSERT INTO series_sets (
                            series_id,
                            set_number,
                            nexon_match_id,
                            played_at,
                            team_a_score,
                            team_b_score,
                            score_source,
                            winner_side
                        )

                        VALUES (
                            %s,
                            %s,
                            NULL,
                            NOW(),
                            %s,
                            %s,
                            'manual',
                            %s
                        )

                        ON CONFLICT (
                            series_id,
                            set_number
                        )

                        DO UPDATE SET
                            team_a_score =
                                EXCLUDED.team_a_score,

                            team_b_score =
                                EXCLUDED.team_b_score,

                            score_source =
                                'manual',

                            winner_side =
                                EXCLUDED.winner_side
                        """,
                        (
                            request.series_id,
                            set_number,
                            team_a_score,
                            team_b_score,
                            winner_side,
                        ),
                    )


                # =========================
                # 실제 정산 함수 실행
                # =========================

                settlement_result = (
                    settle_predictions_for_series(
                        cursor,
                        request.series_id,
                    )
                )


                # =========================
                # 정산 후 예측 상태
                # =========================

                cursor.execute(
                    """
                    SELECT
                        p.id,
                        p.user_id,
                        p.set_number,
                        p.prediction_type,
                        p.predicted_participant_id,
                        p.stake_points,
                        p.odds,
                        p.status,
                        p.payout_points,

                        u.nickname,
                        u.points

                    FROM predictions AS p

                    INNER JOIN users AS u
                        ON u.id =
                            p.user_id

                    WHERE
                        p.series_id = %s

                    ORDER BY
                        p.set_number,
                        p.id
                    """,
                    (
                        request.series_id,
                    ),
                )


                after_predictions = (
                    cursor.fetchall()
                )


                prediction_results = []


                for row in after_predictions:

                    user_id = int(
                        row["user_id"]
                    )


                    points_before = (
                        before_points.get(
                            user_id,
                            int(
                                row["points"]
                            ),
                        )
                    )


                    points_after = int(
                        row["points"]
                    )


                    prediction_results.append(
                        {
                            "prediction_id":
                                row["id"],

                            "nickname":
                                row[
                                    "nickname"
                                ],

                            "set_number":
                                row[
                                    "set_number"
                                ],

                            "prediction_type":
                                row[
                                    "prediction_type"
                                ],

                            "participant_id":
                                row[
                                    "predicted_participant_id"
                                ],

                            "stake_points":
                                row[
                                    "stake_points"
                                ],

                            "odds":
                                float(
                                    row[
                                        "odds"
                                    ]
                                ),

                            "result_status":
                                row[
                                    "status"
                                ],

                            "payout_points":
                                row[
                                    "payout_points"
                                ],

                            "points_before":
                                points_before,

                            "points_after":
                                points_after,

                            "point_change":
                                int(
                                    row[
                                        "payout_points"
                                    ]
                                    or 0
                                ),
                            "user_total_point_change":
                                (
                                    points_after
                                    -
                                    points_before
                                ),
                        }
                    )


            # =========================
            # 핵심
            #
            # 모든 테스트 변경 취소
            # =========================

            connection.rollback()


        except Exception:

            connection.rollback()

            raise


    return {
        "status":
            "success",

        "database_change":
            "rolled_back",

        "message":
            (
                "정산 테스트가 완료되었습니다. "
                "실제 DB 변경은 모두 취소되었습니다."
            ),

        "settlement":
            settlement_result,

        "predictions":
            prediction_results,
    }

# =========================
# AI MATCH PREDICTION V1
#
# 기준
# 전체 전적      20%
# 최근 폼        20%
# 상대 전적      15%
# 득실           15%
# Elo            20%
# Home / Away    10%
#
# team_a = Home
# team_b = Away
# =========================

AI_PREDICTION_MODEL = (
    "fcl-stat-v1.1"
)

AI_PREDICTION_WEIGHTS = {
    "overall": 0.23,
    "recent_form": 0.12,
    "head_to_head": 0.05,
    "goals": 0.23,
    "elo": 0.24,
    "home_away": 0.13,
}


AI_RECENT_FORM_WEIGHTS = [
    1.00,
    0.92,
    0.85,
    0.78,
    0.71,
    0.64,
    0.58,
    0.52,
    0.46,
    0.40,
]


def clamp_ai_value(
    value,
    minimum,
    maximum,
):

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def create_ai_record_bucket():

    return {
        "sets": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "goals_for": 0,
        "goals_against": 0,
    }


def update_ai_record_bucket(
    bucket,
    result,
    goals_for,
    goals_against,
):

    bucket["sets"] += 1

    bucket["goals_for"] += int(
        goals_for
    )

    bucket["goals_against"] += int(
        goals_against
    )


    if result == 1.0:

        bucket["wins"] += 1

    elif result == 0.5:

        bucket["draws"] += 1

    else:

        bucket["losses"] += 1


def get_ai_record_rate(
    bucket,
):

    set_count = int(
        bucket["sets"]
    )


    if set_count <= 0:

        return 0.5


    return (
        (
            bucket["wins"]
            +
            (
                bucket["draws"]
                * 0.5
            )
        )
        /
        set_count
    )


def get_ai_draw_rate(
    bucket,
    default=0.22,
):

    set_count = int(
        bucket["sets"]
    )


    if set_count <= 0:

        return default


    return (
        bucket["draws"]
        /
        set_count
    )


def get_ai_average_goals_for(
    bucket,
):

    set_count = int(
        bucket["sets"]
    )


    if set_count <= 0:

        return 0.0


    return (
        bucket["goals_for"]
        /
        set_count
    )


def get_ai_average_goals_against(
    bucket,
):

    set_count = int(
        bucket["sets"]
    )


    if set_count <= 0:

        return 0.0


    return (
        bucket["goals_against"]
        /
        set_count
    )

def build_ai_prediction_context_from_history(
    source_history,
):

    history = list(
        source_history
    )


    history.sort(
        key=lambda record:
            record["order_key"]
    )


    # =========================
    # 참가자별 통계
    # =========================

    stats = {}

    recent_results = {}

    elo_ratings = {}


    def ensure_participant(
        name,
    ):

        if name in stats:
            return


        stats[name] = {
            "overall":
                create_ai_record_bucket(),

            "home":
                create_ai_record_bucket(),

            "away":
                create_ai_record_bucket(),
        }


        recent_results[name] = []

        elo_ratings[name] = 1500.0


    for participant in PARTICIPANTS:

        ensure_participant(
            participant
        )


    global_record = (
        create_ai_record_bucket()
    )


    # =========================
    # 시간순 통계 + Elo
    # =========================

    for record in history:

        team_a = (
            record[
                "team_a"
            ]
        )

        team_b = (
            record[
                "team_b"
            ]
        )


        ensure_participant(
            team_a
        )

        ensure_participant(
            team_b
        )


        team_a_score = int(
            record[
                "team_a_score"
            ]
        )

        team_b_score = int(
            record[
                "team_b_score"
            ]
        )


        winner_side = (
            record[
                "winner_side"
            ]
        )


        if (
            winner_side
            == "team_a"
        ):

            result_a = 1.0
            result_b = 0.0


        elif (
            winner_side
            == "team_b"
        ):

            result_a = 0.0
            result_b = 1.0


        else:

            result_a = 0.5
            result_b = 0.5


        # =====================
        # 전체 기록
        # =====================

        update_ai_record_bucket(
            stats[
                team_a
            ][
                "overall"
            ],
            result_a,
            team_a_score,
            team_b_score,
        )

        update_ai_record_bucket(
            stats[
                team_b
            ][
                "overall"
            ],
            result_b,
            team_b_score,
            team_a_score,
        )


        # =====================
        # Home / Away
        # =====================

        update_ai_record_bucket(
            stats[
                team_a
            ][
                "home"
            ],
            result_a,
            team_a_score,
            team_b_score,
        )

        update_ai_record_bucket(
            stats[
                team_b
            ][
                "away"
            ],
            result_b,
            team_b_score,
            team_a_score,
        )


        # =====================
        # 최근 폼
        # =====================

        recent_results[
            team_a
        ].append(
            result_a
        )

        recent_results[
            team_b
        ].append(
            result_b
        )


        # =====================
        # 전체 무승부율
        # =====================

        update_ai_record_bucket(
            global_record,

            (
                0.5
                if
                winner_side
                == "draw"

                else
                (
                    1.0
                    if
                    winner_side
                    == "team_a"

                    else
                    0.0
                )
            ),

            team_a_score,
            team_b_score,
        )


        # =====================
        # Elo
        # =====================

        elo_a = float(
            elo_ratings[
                team_a
            ]
        )

        elo_b = float(
            elo_ratings[
                team_b
            ]
        )


        expected_a = (
            1.0
            /
            (
                1.0
                +
                (
                    10
                    **
                    (
                        (
                            elo_b
                            -
                            elo_a
                        )
                        /
                        400.0
                    )
                )
            )
        )


        expected_b = (
            1.0
            -
            expected_a
        )


        elo_k = 24.0


        elo_ratings[
            team_a
        ] = (
            elo_a
            +
            elo_k
            *
            (
                result_a
                -
                expected_a
            )
        )


        elo_ratings[
            team_b
        ] = (
            elo_b
            +
            elo_k
            *
            (
                result_b
                -
                expected_b
            )
        )


    return {
        "history":
            history,

        "stats":
            stats,

        "recent_results":
            recent_results,

        "elo_ratings":
            elo_ratings,

        "global_record":
            global_record,
    }


def build_ai_prediction_context():

    history = []

    regular_database_match_keys = set()


    # =========================
    # 1. DB 완료 경기
    #
    # 정규리그
    # +
    # 정규시간 결과를 사용한 프리시즌
    #
    # 플레이오프는 제외
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id AS series_id,
                    s.series_type,
                    s.scheduled_date,
                    s.include_extra_time_result,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b,

                    ss.set_number,
                    ss.played_at,
                    ss.team_a_score,
                    ss.team_b_score,
                    ss.winner_side

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
                    s.status =
                        'completed'

                    AND (
                        s.series_type =
                            '정규리그'

                        OR

                        (
                            s.series_type =
                                '프리시즌'

                            AND
                            s.include_extra_time_result
                                = FALSE
                        )
                    )

                ORDER BY
                    s.scheduled_date,
                    ss.played_at,
                    s.id,
                    ss.set_number
                """
            )


            rows = cursor.fetchall()


    for row in rows:

        team_a_score = int(
            row["team_a_score"]
        )

        team_b_score = int(
            row["team_b_score"]
        )


        winner_side = (
            row["winner_side"]
        )


        if winner_side not in (
            "team_a",
            "team_b",
            "draw",
        ):

            if (
                team_a_score
                >
                team_b_score
            ):

                winner_side = "team_a"

            elif (
                team_b_score
                >
                team_a_score
            ):

                winner_side = "team_b"

            else:

                winner_side = "draw"


        scheduled_date = (
            row["scheduled_date"]
        )


        date_text = (
            scheduled_date.isoformat()
            if scheduled_date
            else ""
        )


        played_at_text = (
            row["played_at"].isoformat()
            if row["played_at"]
            else ""
        )


        history.append(
            {
                "series_id":
                    row["series_id"],

                "series_type":
                    row["series_type"],

                "date":
                    date_text,

                "order_key": (
                    date_text,
                    played_at_text,
                    int(
                        row["series_id"]
                    ),
                    int(
                        row["set_number"]
                    ),
                ),

                "team_a":
                    row["team_a"],

                "team_b":
                    row["team_b"],

                "team_a_score":
                    team_a_score,

                "team_b_score":
                    team_b_score,

                "winner_side":
                    winner_side,
            }
        )


        if (
            row["series_type"]
            == "정규리그"
            and
            scheduled_date
        ):

            teams = sorted(
                [
                    row["team_a"],
                    row["team_b"],
                ]
            )


            regular_database_match_keys.add(
                (
                    scheduled_date
                        .isoformat(),

                    teams[0],
                    teams[1],
                )
            )


    # =========================
    # 2. 기존 Excel 정규리그
    #
    # DB에 같은 경기가 없을 때만
    # 과거 데이터 보완
    # =========================

    workbook = load_workbook(
        RESULTS_PATH,
        data_only=True,
    )

    worksheet = workbook[
        "경기결과"
    ]


    excel_order = 0


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

            match_type = (
                "정규리그"
            )


        if (
            match_type
            != "정규리그"
        ):

            continue


        if hasattr(
            match_date,
            "date",
        ):

            match_date = (
                match_date.date()
            )


        elif isinstance(
            match_date,
            str,
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


        teams = sorted(
            [
                team_a,
                team_b,
            ]
        )


        match_key = (
            match_date.isoformat(),
            teams[0],
            teams[1],
        )


        if (
            match_key
            in regular_database_match_keys
        ):

            continue


        excel_sets = [
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


        for (
            set_index,
            (
                team_a_score,
                team_b_score,
            ),
        ) in enumerate(
            excel_sets,
            start=1,
        ):

            team_a_score = int(
                team_a_score
            )

            team_b_score = int(
                team_b_score
            )


            if (
                team_a_score
                >
                team_b_score
            ):

                winner_side = (
                    "team_a"
                )

            elif (
                team_b_score
                >
                team_a_score
            ):

                winner_side = (
                    "team_b"
                )

            else:

                winner_side = (
                    "draw"
                )


            history.append(
                {
                    "series_id":
                        None,

                    "series_type":
                        "정규리그",

                    "date":
                        match_date
                            .isoformat(),

                    "order_key": (
                        match_date
                            .isoformat(),

                        "",

                        excel_order,

                        set_index,
                    ),

                    "team_a":
                        team_a,

                    "team_b":
                        team_b,

                    "team_a_score":
                        team_a_score,

                    "team_b_score":
                        team_b_score,

                    "winner_side":
                        winner_side,
                }
            )


        excel_order += 1


    workbook.close()

    history.sort(
        key=lambda record:
            record["order_key"]
    )

    return (
        build_ai_prediction_context_from_history(
            history
        )
    )


def calculate_ai_match_prediction(
    context,
    team_a,
    team_b,
    weights=None,
):

    stats = context[
        "stats"
    ]

    recent_results = context[
        "recent_results"
    ]

    elo_ratings = context[
        "elo_ratings"
    ]

    history = context[
        "history"
    ]


    if (
        team_a not in stats
        or
        team_b not in stats
    ):

        return {
            "team_a_win": 39,
            "draw": 22,
            "team_b_win": 39,
            "sample_size": 0,
            "confidence": "low",
            "model":
                AI_PREDICTION_MODEL,
        }


    stats_a = stats[
        team_a
    ]

    stats_b = stats[
        team_b
    ]


    overall_a = (
        get_ai_record_rate(
            stats_a[
                "overall"
            ]
        )
    )

    overall_b = (
        get_ai_record_rate(
            stats_b[
                "overall"
            ]
        )
    )


    # =========================
    # 1. 전체 전적
    # =========================

    overall_factor = (
        0.5
        +
        (
            overall_a
            -
            overall_b
        )
        *
        0.5
    )


    overall_factor = (
        clamp_ai_value(
            overall_factor,
            0.10,
            0.90,
        )
    )


    # =========================
    # 2. 최근 폼
    # 최근 10세트
    # =========================

    def recent_form_rate(
        name,
    ):

        values = (
            recent_results.get(
                name,
                [],
            )
        )


        values = list(
            reversed(
                values[-10:]
            )
        )


        if not values:

            return 0.5


        weighted_total = 0.0
        weight_total = 0.0


        for (
            index,
            result,
        ) in enumerate(
            values
        ):

            weight = (
                AI_RECENT_FORM_WEIGHTS[
                    index
                ]
            )


            weighted_total += (
                float(result)
                *
                weight
            )

            weight_total += (
                weight
            )


        if weight_total <= 0:

            return 0.5


        return (
            weighted_total
            /
            weight_total
        )


    recent_a = (
        recent_form_rate(
            team_a
        )
    )

    recent_b = (
        recent_form_rate(
            team_b
        )
    )


    recent_factor = (
        0.5
        +
        (
            recent_a
            -
            recent_b
        )
        *
        0.5
    )


    recent_factor = (
        clamp_ai_value(
            recent_factor,
            0.10,
            0.90,
        )
    )


    # =========================
    # 3. 상대전적
    # =========================

    head_to_head_results = []

    head_to_head_draws = 0


    for record in history:

        is_same_matchup = (
            {
                record[
                    "team_a"
                ],
                record[
                    "team_b"
                ],
            }
            ==
            {
                team_a,
                team_b,
            }
        )


        if not is_same_matchup:

            continue


        if (
            record[
                "winner_side"
            ]
            == "draw"
        ):

            result = 0.5

            head_to_head_draws += 1


        elif (
            (
                record[
                    "team_a"
                ]
                ==
                team_a
                and
                record[
                    "winner_side"
                ]
                ==
                "team_a"
            )
            or
            (
                record[
                    "team_b"
                ]
                ==
                team_a
                and
                record[
                    "winner_side"
                ]
                ==
                "team_b"
            )
        ):

            result = 1.0


        else:

            result = 0.0


        head_to_head_results.append(
            result
        )


    head_to_head_count = len(
        head_to_head_results
    )


    if head_to_head_count:

        raw_head_to_head = (
            sum(
                head_to_head_results
            )
            /
            head_to_head_count
        )


        head_to_head_reliability = min(
            1.0,
            (
                head_to_head_count
                /
                6.0
            ),
        )


        head_to_head_factor = (
            0.5
            +
            (
                raw_head_to_head
                -
                0.5
            )
            *
            head_to_head_reliability
        )


    else:

        head_to_head_factor = 0.5

        head_to_head_reliability = 0.0


    # =========================
    # 4. 득실
    #
    # 공격력 차이
    # +
    # 수비력 차이
    # =========================

    average_for_a = (
        get_ai_average_goals_for(
            stats_a[
                "overall"
            ]
        )
    )

    average_against_a = (
        get_ai_average_goals_against(
            stats_a[
                "overall"
            ]
        )
    )


    average_for_b = (
        get_ai_average_goals_for(
            stats_b[
                "overall"
            ]
        )
    )

    average_against_b = (
        get_ai_average_goals_against(
            stats_b[
                "overall"
            ]
        )
    )


    attack_edge = (
        average_for_a
        -
        average_for_b
    )


    defense_edge = (
        average_against_b
        -
        average_against_a
    )


    goal_edge = (
        (
            attack_edge
            +
            defense_edge
        )
        /
        2.0
    )


    goals_factor = (
        0.5
        +
        clamp_ai_value(
            (
                goal_edge
                /
                6.0
            ),
            -0.35,
            0.35,
        )
    )


    # =========================
    # 5. Elo
    # =========================

    elo_a = float(
        elo_ratings.get(
            team_a,
            1500.0,
        )
    )

    elo_b = float(
        elo_ratings.get(
            team_b,
            1500.0,
        )
    )


    elo_factor = (
        1.0
        /
        (
            1.0
            +
            (
                10
                **
                (
                    (
                        elo_b
                        -
                        elo_a
                    )
                    /
                    400.0
                )
            )
        )
    )


    # =========================
    # 6. Home / Away
    #
    # A의 Home 기록
    # B의 Away 기록
    # =========================

    home_a = (
        stats_a[
            "home"
        ]
    )

    away_b = (
        stats_b[
            "away"
        ]
    )


    home_a_rate = (
        get_ai_record_rate(
            home_a
        )
    )

    away_b_rate = (
        get_ai_record_rate(
            away_b
        )
    )


    # 표본이 적으면
    # 전체 기록 쪽으로 보정
    home_reliability = min(
        1.0,
        home_a["sets"]
        /
        6.0,
    )

    away_reliability = min(
        1.0,
        away_b["sets"]
        /
        6.0,
    )


    adjusted_home_a = (
        overall_a
        +
        (
            home_a_rate
            -
            overall_a
        )
        *
        home_reliability
    )


    adjusted_away_b = (
        overall_b
        +
        (
            away_b_rate
            -
            overall_b
        )
        *
        away_reliability
    )


    home_away_factor = (
        0.5
        +
        (
            adjusted_home_a
            -
            adjusted_away_b
        )
        *
        0.5
    )


    home_away_factor = (
        clamp_ai_value(
            home_away_factor,
            0.10,
            0.90,
        )
    )


    # =========================
    # 종합 A 우세도
    # =========================

    factors = {
        "overall":
            overall_factor,

        "recent_form":
            recent_factor,

        "head_to_head":
            head_to_head_factor,

        "goals":
            goals_factor,

        "elo":
            elo_factor,

        "home_away":
            home_away_factor,
    }


    active_weights = (
        weights
        if weights is not None
        else AI_PREDICTION_WEIGHTS
    )


    total_weight = sum(
        active_weights.values()
    )


    if total_weight <= 0:

        active_weights = (
            AI_PREDICTION_WEIGHTS
        )

        total_weight = sum(
            active_weights.values()
        )


    team_a_strength = 0.0


    for (
        factor_name,
        weight,
    ) in active_weights.items():

        if (
            factor_name
            not in factors
        ):

            continue


        normalized_weight = (
            weight
            /
            total_weight
        )


        team_a_strength += (
            factors[
                factor_name
            ]
            *
            normalized_weight
        )
    #
    # 두 참가자 중
    # 기록이 적은 참가자를 기준
    # =========================

    sample_size = min(
        int(
            stats_a[
                "overall"
            ][
                "sets"
            ]
        ),
        int(
            stats_b[
                "overall"
            ][
                "sets"
            ]
        ),
    )


    sample_reliability = min(
        1.0,
        sample_size
        /
        16.0,
    )


    team_a_strength = (
        0.5
        +
        (
            team_a_strength
            -
            0.5
        )
        *
        (
            0.25
            +
            (
                0.75
                *
                sample_reliability
            )
        )
    )


    team_a_strength = (
        clamp_ai_value(
            team_a_strength,
            0.12,
            0.88,
        )
    )


    # =========================
    # 무승부 확률
    # =========================

    global_draw_rate = (
        get_ai_draw_rate(
            context[
                "global_record"
            ]
        )
    )


    draw_rate_a = (
        get_ai_draw_rate(
            stats_a[
                "overall"
            ]
        )
    )

    draw_rate_b = (
        get_ai_draw_rate(
            stats_b[
                "overall"
            ]
        )
    )


    if head_to_head_count:

        raw_h2h_draw_rate = (
            head_to_head_draws
            /
            head_to_head_count
        )


        h2h_draw_rate = (
            global_draw_rate
            +
            (
                raw_h2h_draw_rate
                -
                global_draw_rate
            )
            *
            head_to_head_reliability
        )

    else:

        h2h_draw_rate = (
            global_draw_rate
        )


    base_draw_probability = (
        global_draw_rate
        *
        0.40

        +
        draw_rate_a
        *
        0.20

        +
        draw_rate_b
        *
        0.20

        +
        h2h_draw_rate
        *
        0.20
    )


    # 실력이 비슷할수록
    # 무승부 확률 상승
    closeness = (
        1.0
        -
        min(
            1.0,
            abs(
                team_a_strength
                -
                0.5
            )
            *
            2.0,
        )
    )


    draw_probability = (
        base_draw_probability
        *
        (
            0.75
            +
            (
                0.35
                *
                closeness
            )
        )
    )


    # 시즌 초반에는
    # 22% Prior 쪽으로 보정
    draw_probability = (
        0.22
        *
        (
            1.0
            -
            sample_reliability
        )

        +

        draw_probability
        *
        sample_reliability
    )


    draw_probability = (
        clamp_ai_value(
            draw_probability,
            0.12,
            0.38,
        )
    )


    # =========================
    # 최종 A승 / 무 / B승
    # =========================

    decisive_probability = (
        1.0
        -
        draw_probability
    )


    team_a_probability = (
        decisive_probability
        *
        team_a_strength
    )


    team_b_probability = (
        decisive_probability
        *
        (
            1.0
            -
            team_a_strength
        )
    )


    team_a_percent = int(
        round(
            team_a_probability
            *
            100
        )
    )

    draw_percent = int(
        round(
            draw_probability
            *
            100
        )
    )


    # 합계 무조건 100
    team_b_percent = (
        100
        -
        team_a_percent
        -
        draw_percent
    )


    team_b_percent = max(
        0,
        team_b_percent,
    )


    # =========================
    # 신뢰도
    # =========================

    if sample_size >= 20:

        confidence = "high"

    elif sample_size >= 8:

        confidence = "medium"

    else:

        confidence = "low"


    return {
        "team_a_win":
            team_a_percent,

        "draw":
            draw_percent,

        "team_b_win":
            team_b_percent,

        "sample_size":
            sample_size,

        "head_to_head_sample":
            head_to_head_count,

        "confidence":
            confidence,

        "model":
            AI_PREDICTION_MODEL,

        "elo": {
            "team_a":
                round(
                    elo_a,
                    1,
                ),

            "team_b":
                round(
                    elo_b,
                    1,
                ),
        },

        "factors": {
            factor_name:
                round(
                    value,
                    3,
                )

            for (
                factor_name,
                value,
            )
            in factors.items()
        },
    }


def calculate_ai_series_prediction(
    prediction,
    target_set_count,
):

    if not isinstance(
        prediction,
        dict,
    ):
        return None


    try:

        team_a_win = float(
            prediction.get(
                "team_a_win",
                0,
            )
        )

        draw = float(
            prediction.get(
                "draw",
                0,
            )
        )

        team_b_win = float(
            prediction.get(
                "team_b_win",
                0,
            )
        )

        set_count = int(
            target_set_count
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


    total = (
        team_a_win
        +
        draw
        +
        team_b_win
    )


    if (
        total <= 0
        or
        set_count <= 0
    ):

        return None


    # =====================================
    # 1SET 확률 정규화
    # =====================================

    probability_a = (
        team_a_win
        /
        total
    )

    probability_draw = (
        draw
        /
        total
    )

    probability_b = (
        team_b_win
        /
        total
    )


    # =====================================
    # SERIES 확률 계산
    #
    # key:
    # A 승 세트 수 - B 승 세트 수
    #
    # A 승 = +1
    # 무승부 = 0
    # B 승 = -1
    #
    # 현재 2SET뿐 아니라
    # 향후 1~3SET에도 그대로 사용 가능
    # =====================================

    distribution = {
        0: 1.0,
    }


    for _ in range(
        set_count
    ):

        next_distribution = {}


        for (
            score_difference,
            probability,
        ) in distribution.items():

            # A 승
            next_distribution[
                score_difference + 1
            ] = (
                next_distribution.get(
                    score_difference + 1,
                    0.0,
                )
                +
                probability
                *
                probability_a
            )


            # 무승부
            next_distribution[
                score_difference
            ] = (
                next_distribution.get(
                    score_difference,
                    0.0,
                )
                +
                probability
                *
                probability_draw
            )


            # B 승
            next_distribution[
                score_difference - 1
            ] = (
                next_distribution.get(
                    score_difference - 1,
                    0.0,
                )
                +
                probability
                *
                probability_b
            )


        distribution = (
            next_distribution
        )


    series_a = sum(
        probability

        for (
            score_difference,
            probability,
        ) in distribution.items()

        if score_difference > 0
    )


    series_draw = (
        distribution.get(
            0,
            0.0,
        )
    )


    series_b = sum(
        probability

        for (
            score_difference,
            probability,
        ) in distribution.items()

        if score_difference < 0
    )


    team_a_percent = round(
        series_a * 100,
        1,
    )

    draw_percent = round(
        series_draw * 100,
        1,
    )

    # 반올림해도 합계 100 유지
    team_b_percent = round(
        100.0
        -
        team_a_percent
        -
        draw_percent,
        1,
    )


    return {
        "team_a_win":
            team_a_percent,

        "draw":
            draw_percent,

        "team_b_win":
            team_b_percent,

        "target_set_count":
            set_count,
    }

def get_ai_prediction_top_result(
    prediction,
):

    if not isinstance(
        prediction,
        dict,
    ):

        return None


    probabilities = {
        "team_a":
            float(
                prediction.get(
                    "team_a_win",
                    0,
                )
            ),

        "draw":
            float(
                prediction.get(
                    "draw",
                    0,
                )
            ),

        "team_b":
            float(
                prediction.get(
                    "team_b_win",
                    0,
                )
            ),
    }


    highest_probability = max(
        probabilities.values()
    )


    leaders = [
        result

        for (
            result,
            probability,
        ) in probabilities.items()

        if abs(
            probability
            -
            highest_probability
        ) < 0.000001
    ]


    # 정확히 같은 최고 확률이 2개 이상이면
    # 억지로 A/B 한쪽을 적중 후보로 잡지 않음
    if len(leaders) != 1:

        return None


    return leaders[0]

def calculate_ai_brier_score(
    prediction,
    actual_result,
):

    if (
        not isinstance(
            prediction,
            dict,
        )
        or
        actual_result
        not in (
            "team_a",
            "draw",
            "team_b",
        )
    ):

        return None


    try:

        team_a = float(
            prediction.get(
                "team_a_win",
                0,
            )
        )

        draw = float(
            prediction.get(
                "draw",
                0,
            )
        )

        team_b = float(
            prediction.get(
                "team_b_win",
                0,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None


    total = (
        team_a
        +
        draw
        +
        team_b
    )


    if total <= 0:

        return None


    probabilities = {
        "team_a":
            team_a / total,

        "draw":
            draw / total,

        "team_b":
            team_b / total,
    }


    brier_score = 0.0


    for (
        result,
        probability,
    ) in probabilities.items():

        actual_value = (
            1.0

            if result
            ==
            actual_result

            else 0.0
        )


        brier_score += (
            probability
            -
            actual_value
        ) ** 2


    return brier_score

@app.get(
    "/api/ai-predictions/history"
)
def get_ai_prediction_history():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id
                        AS series_id,

                    s.fixture_number,

                    s.scheduled_date,

                    s.round_number,

                    s.target_set_count,

                    s.status,

                    s.ai_prediction_snapshot,

                    s.ai_prediction_snapshot_at,

                    team_a.fcl_name
                        AS team_a,

                    team_b.fcl_name
                        AS team_b,

                    ss.set_number,

                    ss.team_a_score,

                    ss.team_b_score,

                    ss.winner_side

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                LEFT JOIN series_sets AS ss
                    ON ss.series_id =
                        s.id

                WHERE
                    s.series_type =
                        '정규리그'

                    AND
                    s.status =
                        'completed'

                    AND
                    s.ai_prediction_snapshot
                        IS NOT NULL

                ORDER BY
                    s.scheduled_date DESC,
                    s.fixture_number DESC,
                    s.id DESC,
                    ss.set_number ASC
                """
            )


            rows = cursor.fetchall()


    # =====================================
    # SERIES 단위 묶기
    # =====================================

    series_map = {}


    for row in rows:

        series_id = (
            row[
                "series_id"
            ]
        )


        if (
            series_id
            not in series_map
        ):

            snapshot = (
                row[
                    "ai_prediction_snapshot"
                ]
            )


            series_map[
                series_id
            ] = {
                "series_id":
                    series_id,

                "fixture_number":
                    row[
                        "fixture_number"
                    ],

                "date":
                    (
                        row[
                            "scheduled_date"
                        ].isoformat()

                        if row[
                            "scheduled_date"
                        ]

                        else None
                    ),

                "round":
                    row[
                        "round_number"
                    ],

                "team_a":
                    row[
                        "team_a"
                    ],

                "team_b":
                    row[
                        "team_b"
                    ],

                "target_set_count":
                    int(
                        row[
                            "target_set_count"
                        ]
                        or 0
                    ),

                "model":
                    (
                        snapshot.get(
                            "model"
                        )

                        if isinstance(
                            snapshot,
                            dict,
                        )

                        else None
                    ),

                "snapshot_at":
                    (
                        row[
                            "ai_prediction_snapshot_at"
                        ].isoformat()

                        if row[
                            "ai_prediction_snapshot_at"
                        ]

                        else None
                    ),

                "set_prediction":
                    snapshot,

                "sets": [],
            }


        if (
            row[
                "set_number"
            ]
            is not None
        ):

            series_map[
                series_id
            ][
                "sets"
            ].append(
                {
                    "set_number":
                        row[
                            "set_number"
                        ],

                    "team_a_score":
                        row[
                            "team_a_score"
                        ],

                    "team_b_score":
                        row[
                            "team_b_score"
                        ],

                    "actual_result":
                        row[
                            "winner_side"
                        ],
                }
            )


    # =====================================
    # 실전 성적 집계
    # =====================================

    predictions = []


    series_prediction_count = 0
    series_decisive_count = 0
    series_correct_count = 0

    series_brier_total = 0.0
    series_brier_count = 0


    set_prediction_count = 0
    set_decisive_count = 0
    set_correct_count = 0

    set_brier_total = 0.0
    set_brier_count = 0


    for series in series_map.values():

        set_prediction = (
            series[
                "set_prediction"
            ]
        )


        if not isinstance(
            set_prediction,
            dict,
        ):

            continue


        # =================================
        # 1SET 예측 1순위
        # =================================

        set_top_result = (
            get_ai_prediction_top_result(
                set_prediction
            )
        )


        # =================================
        # 실제 SET 성적
        # =================================

        team_a_points = 0
        team_b_points = 0

        valid_set_count = 0


        for set_result in series[
            "sets"
        ]:

            actual_result = (
                set_result[
                    "actual_result"
                ]
            )


            if actual_result not in (
                "team_a",
                "draw",
                "team_b",
            ):

                set_result[
                    "is_correct"
                ] = None

                continue


            valid_set_count += 1
            set_prediction_count += 1


            if (
                actual_result
                ==
                "team_a"
            ):

                team_a_points += 3


            elif (
                actual_result
                ==
                "team_b"
            ):

                team_b_points += 3


            else:

                team_a_points += 1
                team_b_points += 1


            # SET 적중 여부
            if (
                set_top_result
                is not None
            ):

                set_decisive_count += 1

                set_is_correct = (
                    set_top_result
                    ==
                    actual_result
                )

                set_result[
                    "is_correct"
                ] = (
                    set_is_correct
                )


                if set_is_correct:

                    set_correct_count += 1


            else:

                set_result[
                    "is_correct"
                ] = None


            # SET Brier
            set_brier = (
                calculate_ai_brier_score(
                    set_prediction,
                    actual_result,
                )
            )


            if (
                set_brier
                is not None
            ):

                set_brier_total += (
                    set_brier
                )

                set_brier_count += 1


        # =================================
        # 실제 SERIES 결과
        #
        # 승 3 / 무 1 / 패 0
        # =================================

        actual_series_result = None


        if (
            valid_set_count
            >=
            series[
                "target_set_count"
            ]
            and
            valid_set_count > 0
        ):

            if (
                team_a_points
                >
                team_b_points
            ):

                actual_series_result = (
                    "team_a"
                )


            elif (
                team_a_points
                <
                team_b_points
            ):

                actual_series_result = (
                    "team_b"
                )


            else:

                actual_series_result = (
                    "draw"
                )


        # =================================
        # SET → SERIES AI 확률 변환
        # =================================

        series_prediction = (
            calculate_ai_series_prediction(
                set_prediction,
                series[
                    "target_set_count"
                ],
            )
        )


        series_top_result = (
            get_ai_prediction_top_result(
                series_prediction
            )

            if series_prediction

            else None
        )


        series_is_correct = None
        series_brier = None


        if (
            actual_series_result
            is not None
            and
            series_prediction
            is not None
        ):

            series_prediction_count += 1


            if (
                series_top_result
                is not None
            ):

                series_decisive_count += 1

                series_is_correct = (
                    series_top_result
                    ==
                    actual_series_result
                )


                if series_is_correct:

                    series_correct_count += 1


            series_brier = (
                calculate_ai_brier_score(
                    series_prediction,
                    actual_series_result,
                )
            )


            if (
                series_brier
                is not None
            ):

                series_brier_total += (
                    series_brier
                )

                series_brier_count += 1


        series[
            "series_prediction"
        ] = (
            series_prediction
        )

        series[
            "predicted_result"
        ] = (
            series_top_result
        )

        series[
            "actual_result"
        ] = (
            actual_series_result
        )

        series[
            "team_a_points"
        ] = (
            team_a_points
        )

        series[
            "team_b_points"
        ] = (
            team_b_points
        )

        series[
            "is_correct"
        ] = (
            series_is_correct
        )

        series[
            "brier_score"
        ] = (
            round(
                series_brier,
                4,
            )

            if series_brier
            is not None

            else None
        )


        predictions.append(
            series
        )


    # =====================================
    # Summary
    # =====================================

    series_accuracy = (
        round(
            (
                series_correct_count
                /
                series_decisive_count
            )
            * 100,
            1,
        )

        if series_decisive_count

        else None
    )


    set_accuracy = (
        round(
            (
                set_correct_count
                /
                set_decisive_count
            )
            * 100,
            1,
        )

        if set_decisive_count

        else None
    )


    average_series_brier = (
        round(
            series_brier_total
            /
            series_brier_count,
            4,
        )

        if series_brier_count

        else None
    )


    average_set_brier = (
        round(
            set_brier_total
            /
            set_brier_count,
            4,
        )

        if set_brier_count

        else None
    )


    return {
        "series_summary": {
            "prediction_count":
                series_prediction_count,

            "decisive_prediction_count":
                series_decisive_count,

            "correct_count":
                series_correct_count,

            "accuracy":
                series_accuracy,

            "brier_score":
                average_series_brier,

            "normalized_brier_score":
                (
                    round(
                        average_series_brier
                        /
                        2.0,
                        4,
                    )

                    if average_series_brier
                    is not None

                    else None
                ),
        },

        "set_summary": {
            "prediction_count":
                set_prediction_count,

            "decisive_prediction_count":
                set_decisive_count,

            "correct_count":
                set_correct_count,

            "accuracy":
                set_accuracy,

            "brier_score":
                average_set_brier,

            "normalized_brier_score":
                (
                    round(
                        average_set_brier
                        /
                        2.0,
                        4,
                    )

                    if average_set_brier
                    is not None

                    else None
                ),
        },

        "predictions":
            predictions,
    }

# =========================
# AI PREDICTION BACKTEST
#
# 각 SERIES 시작 이전 데이터만
# 사용해서 예측한다.
#
# 동일 SERIES 안의 다른 SET 결과는
# 학습 데이터에 포함하지 않는다.
# =========================

def run_ai_prediction_backtest(
    weights=None,
    include_evaluations=True,
):

    full_context = (
        build_ai_prediction_context()
    )


    history = list(
        full_context[
            "history"
        ]
    )


    # =========================
    # 정규리그만 검증
    # =========================

    regular_history = [
        record

        for record
        in history

        if (
            record[
                "series_type"
            ]
            ==
            "정규리그"
        )
    ]


    # =========================
    # SERIES 단위로 묶기
    #
    # DB SERIES:
    # series_id 기준
    #
    # Excel 과거경기:
    # 날짜 + 참가자 기준
    # =========================

    series_groups = {}


    for record in regular_history:

        if (
            record[
                "series_id"
            ]
            is not None
        ):

            group_key = (
                "database",
                int(
                    record[
                        "series_id"
                    ]
                ),
            )


        else:

            group_key = (
                "excel",
                record[
                    "date"
                ],
                record[
                    "team_a"
                ],
                record[
                    "team_b"
                ],
            )


        series_groups.setdefault(
            group_key,
            []
        ).append(
            record
        )


    # =========================
    # SERIES 시간순
    # =========================

    grouped_series = list(
        series_groups.values()
    )


    for group in grouped_series:

        group.sort(
            key=lambda record:
                record[
                    "order_key"
                ]
        )


    grouped_series.sort(
        key=lambda group:
            group[0][
                "order_key"
            ]
    )


    evaluations = []


    # =========================
    # SERIES 하나씩 과거로 이동
    # =========================

    for group in grouped_series:

        if not group:
            continue


        first_record = (
            group[0]
        )


        team_a = (
            first_record[
                "team_a"
            ]
        )

        team_b = (
            first_record[
                "team_b"
            ]
        )


        cutoff_key = (
            first_record[
                "order_key"
            ]
        )


        # =====================
        # 현재 SERIES보다
        # 과거 데이터만 사용
        # =====================

        training_history = [
            record

            for record
            in history

            if (
                record[
                    "order_key"
                ]
                <
                cutoff_key
            )
        ]


        training_context = (
            build_ai_prediction_context_from_history(
                training_history
            )
        )


        prediction = (
            calculate_ai_match_prediction(
                training_context,
                team_a,
                team_b,
                weights=weights,
            )
        )


        probability_map = {
            "team_a":
                (
                    prediction[
                        "team_a_win"
                    ]
                    /
                    100.0
                ),

            "draw":
                (
                    prediction[
                        "draw"
                    ]
                    /
                    100.0
                ),

            "team_b":
                (
                    prediction[
                        "team_b_win"
                    ]
                    /
                    100.0
                ),
        }


        # =====================
        # 1순위 예측
        # =====================

        predicted_side = max(
            probability_map,
            key=
                probability_map.get,
        )


        # =====================
        # 동일 SERIES의 모든 SET을
        # 같은 사전 예측값으로 평가
        # =====================

        for record in group:

            actual_side = (
                record[
                    "winner_side"
                ]
            )


            if actual_side not in (
                "team_a",
                "draw",
                "team_b",
            ):

                continue


            actual_probability = (
                probability_map[
                    actual_side
                ]
            )


            # =================
            # Multi-class
            # Brier Score
            #
            # 0이 완벽
            # 최대 2
            # =================

            brier_score = 0.0


            for side in (
                "team_a",
                "draw",
                "team_b",
            ):

                expected_value = (
                    1.0
                    if
                    side == actual_side

                    else
                    0.0
                )


                brier_score += (
                    (
                        probability_map[
                            side
                        ]
                        -
                        expected_value
                    )
                    **
                    2
                )


            evaluations.append(
                {
                    "date":
                        record[
                            "date"
                        ],

                    "series_id":
                        record[
                            "series_id"
                        ],

                    "team_a":
                        team_a,

                    "team_b":
                        team_b,

                    "actual":
                        actual_side,

                    "predicted":
                        predicted_side,

                    "correct":
                        (
                            predicted_side
                            ==
                            actual_side
                        ),

                    "actual_probability":
                        actual_probability,

                    "brier_score":
                        brier_score,

                    "prediction":
                        prediction,
                }
            )


    sample_count = len(
        evaluations
    )


    if sample_count == 0:

        return {
            "model":
                AI_PREDICTION_MODEL,

            "sample_count":
                0,

            "message":
                (
                    "백테스트 가능한 "
                    "정규리그 기록이 없습니다."
                ),
        }


    # =========================
    # 적중률
    # =========================

    correct_count = sum(
        1

        for evaluation
        in evaluations

        if evaluation[
            "correct"
        ]
    )


    accuracy = (
        correct_count
        /
        sample_count
    )


    # =========================
    # 실제 결과에 부여한
    # 평균 확률
    # =========================

    average_actual_probability = (
        sum(
            evaluation[
                "actual_probability"
            ]

            for evaluation
            in evaluations
        )
        /
        sample_count
    )


    # =========================
    # Brier Score
    # =========================

    average_brier_score = (
        sum(
            evaluation[
                "brier_score"
            ]

            for evaluation
            in evaluations
        )
        /
        sample_count
    )


    normalized_brier_score = (
        average_brier_score
        /
        2.0
    )


    # =========================
    # 실제 결과 분포
    # =========================

    actual_counts = {
        "team_a": 0,
        "draw": 0,
        "team_b": 0,
    }


    predicted_probability_sum = {
        "team_a": 0.0,
        "draw": 0.0,
        "team_b": 0.0,
    }


    for evaluation in evaluations:

        actual_counts[
            evaluation[
                "actual"
            ]
        ] += 1


        prediction = (
            evaluation[
                "prediction"
            ]
        )


        predicted_probability_sum[
            "team_a"
        ] += (
            prediction[
                "team_a_win"
            ]
            /
            100.0
        )


        predicted_probability_sum[
            "draw"
        ] += (
            prediction[
                "draw"
            ]
            /
            100.0
        )


        predicted_probability_sum[
            "team_b"
        ] += (
            prediction[
                "team_b_win"
            ]
            /
            100.0
        )


    actual_distribution = {
        side:
            round(
                (
                    actual_counts[
                        side
                    ]
                    /
                    sample_count
                )
                *
                100,
                1,
            )

        for side in (
            "team_a",
            "draw",
            "team_b",
        )
    }


    average_prediction = {
        side:
            round(
                (
                    predicted_probability_sum[
                        side
                    ]
                    /
                    sample_count
                )
                *
                100,
                1,
            )

        for side in (
            "team_a",
            "draw",
            "team_b",
        )
    }


    # =========================
    # 신뢰도별 성능
    # =========================

    confidence_summary = {}


    for confidence in (
        "low",
        "medium",
        "high",
    ):

        confidence_rows = [
            evaluation

            for evaluation
            in evaluations

            if (
                evaluation[
                    "prediction"
                ][
                    "confidence"
                ]
                ==
                confidence
            )
        ]


        confidence_count = len(
            confidence_rows
        )


        if confidence_count == 0:

            confidence_summary[
                confidence
            ] = {
                "count": 0,
                "accuracy": None,
            }

            continue


        confidence_correct = sum(
            1

            for evaluation
            in confidence_rows

            if evaluation[
                "correct"
            ]
        )


        confidence_summary[
            confidence
        ] = {
            "count":
                confidence_count,

            "accuracy":
                round(
                    (
                        confidence_correct
                        /
                        confidence_count
                    )
                    *
                    100,
                    1,
                ),
        }

    result = {
        "model":
            AI_PREDICTION_MODEL,

        "method":
            (
                "series-pre-match-"
                "walk-forward"
            ),

        "sample_count":
            sample_count,

        "correct_count":
            correct_count,

        "accuracy":
            round(
                accuracy
                *
                100,
                1,
            ),

        "average_actual_probability":
            round(
                average_actual_probability
                *
                100,
                1,
            ),

        "brier_score":
            round(
                average_brier_score,
                4,
            ),

        "normalized_brier_score":
            round(
                normalized_brier_score,
                4,
            ),

        "actual_distribution":
            actual_distribution,

        "average_prediction":
            average_prediction,

        "confidence":
            confidence_summary,
    }


    if include_evaluations:

        result[
            "evaluations"
        ] = evaluations


    return result

# =========================
# AI PREDICTION
# ABLATION BACKTEST
#
# 각 요소를 하나씩 제거해서
# FULL 모델과 성능 비교
# =========================

def run_ai_prediction_ablation_backtest():

    variants = {
        "full":
            dict(
                AI_PREDICTION_WEIGHTS
            )
    }


    for factor_name in (
        AI_PREDICTION_WEIGHTS
        .keys()
    ):

        variant_name = (
            f"without_{factor_name}"
        )


        variants[
            variant_name
        ] = {
            name:
                weight

            for (
                name,
                weight,
            )
            in (
                AI_PREDICTION_WEIGHTS
                .items()
            )

            if (
                name
                !=
                factor_name
            )
        }


    results = {}


    for (
        variant_name,
        weights,
    ) in variants.items():

        backtest = (
            run_ai_prediction_backtest(
                weights=weights,
                include_evaluations=False,
            )
        )


        results[
            variant_name
        ] = {
            "weights":
                weights,

            "sample_count":
                backtest.get(
                    "sample_count",
                    0,
                ),

            "accuracy":
                backtest.get(
                    "accuracy"
                ),

            "average_actual_probability":
                backtest.get(
                    "average_actual_probability"
                ),

            "brier_score":
                backtest.get(
                    "brier_score"
                ),

            "normalized_brier_score":
                backtest.get(
                    "normalized_brier_score"
                ),

            "average_prediction":
                backtest.get(
                    "average_prediction"
                ),
        }


    full_result = (
        results[
            "full"
        ]
    )


    full_accuracy = (
        full_result[
            "accuracy"
        ]
    )

    full_brier = (
        full_result[
            "brier_score"
        ]
    )


    for (
        variant_name,
        result,
    ) in results.items():

        if (
            variant_name
            ==
            "full"
        ):

            result[
                "accuracy_change"
            ] = 0.0

            result[
                "brier_change"
            ] = 0.0

            continue


        result[
            "accuracy_change"
        ] = round(
            (
                result[
                    "accuracy"
                ]
                -
                full_accuracy
            ),
            1,
        )


        result[
            "brier_change"
        ] = round(
            (
                result[
                    "brier_score"
                ]
                -
                full_brier
            ),
            4,
        )


    return results

def run_ai_prediction_candidate_backtest():

    candidates = {
        "v1":
            {
                "overall": 0.20,
                "recent_form": 0.20,
                "head_to_head": 0.15,
                "goals": 0.15,
                "elo": 0.20,
                "home_away": 0.10,
            },

        "v1_1_a":
            {
                "overall": 0.22,
                "recent_form": 0.15,
                "head_to_head": 0.08,
                "goals": 0.20,
                "elo": 0.23,
                "home_away": 0.12,
            },

        "v1_1_b":
            {
                "overall": 0.23,
                "recent_form": 0.12,
                "head_to_head": 0.05,
                "goals": 0.23,
                "elo": 0.24,
                "home_away": 0.13,
            },

        "v1_1_c":
            {
                "overall": 0.24,
                "recent_form": 0.12,
                "head_to_head": 0.00,
                "goals": 0.25,
                "elo": 0.26,
                "home_away": 0.13,
            },

        "v1_1_d":
            {
                "overall": 0.25,
                "recent_form": 0.08,
                "head_to_head": 0.04,
                "goals": 0.25,
                "elo": 0.27,
                "home_away": 0.11,
            },
    }


    results = {}


    for (
        candidate_name,
        weights,
    ) in candidates.items():

        backtest = (
            run_ai_prediction_backtest(
                weights=weights,
                include_evaluations=False,
            )
        )


        results[
            candidate_name
        ] = {
            "weights":
                weights,

            "accuracy":
                backtest[
                    "accuracy"
                ],

            "average_actual_probability":
                backtest[
                    "average_actual_probability"
                ],

            "brier_score":
                backtest[
                    "brier_score"
                ],

            "normalized_brier_score":
                backtest[
                    "normalized_brier_score"
                ],

            "average_prediction":
                backtest[
                    "average_prediction"
                ],
        }


    return results


# =========================
# ADMIN
# AI 승률 백테스트
# =========================

@app.get(
    "/api/admin/ai-predictions/backtest"
)
def get_ai_prediction_backtest(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    result = (
        run_ai_prediction_backtest()
    )


    result[
        "ablation"
    ] = (
        run_ai_prediction_ablation_backtest()
    )

    result[
        "candidates"
    ] = (
        run_ai_prediction_candidate_backtest()
    )


    return result

# =========================
# 전체 경기 일정
# =========================

@app.get("/api/matches")
def get_matches():

    matches = []

    database_match_keys = set()


    # =========================================
    # 1. Neon DB 일정
    #
    # 정규리그 + 프리시즌
    # =========================================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id AS series_id,
                    s.fixture_number,
                    s.series_type,
                    s.scheduled_date,
                    s.round_number,
                    s.status,
                    s.target_set_count,

                    s.team_a_snapshot_name,
                    s.team_a_snapshot_logo_path,

                    s.team_b_snapshot_name,
                    s.team_b_snapshot_logo_path,

                    s.ai_prediction_snapshot,
                    s.ai_prediction_snapshot_at,

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
                    s.scheduled_date
                        IS NOT NULL

                    AND
                    s.status <>
                        'cancelled'

                ORDER BY
                    s.scheduled_date,
                    s.fixture_number,
                    s.id
                """
            )


            series_rows = cursor.fetchall()


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


        series_type = (
            series_row[
                "series_type"
            ]
        )


        teams = sorted(
            [
                team_a,
                team_b,
            ]
        )


        database_match_keys.add(
            (
                match_date,
                series_type,
                teams[0],
                teams[1],
            )
        )


        matches.append(
            {
                "series_id":
                    series_row[
                        "series_id"
                    ],

                "fixture_number":
                    series_row[
                        "fixture_number"
                    ],

                "source":
                    "database",

                "date":
                    match_date,

                "round":
                    series_row[
                        "round_number"
                    ],

                "match_type":
                    series_type,

                "team_a":
                    team_a,

                "team_b":
                    team_b,

                "status":
                    series_row[
                        "status"
                    ],

                "team_a_snapshot_name":
                    series_row[
                        "team_a_snapshot_name"
                    ],

                "team_a_snapshot_logo_path":
                    series_row[
                        "team_a_snapshot_logo_path"
                    ],

                "team_b_snapshot_name":
                    series_row[
                        "team_b_snapshot_name"
                    ],

                "team_b_snapshot_logo_path":
                    series_row[
                        "team_b_snapshot_logo_path"
                    ],

                "ai_prediction_snapshot":
                    series_row[
                        "ai_prediction_snapshot"
                    ],

                "ai_prediction_snapshot_at":
                    (
                        series_row[
                            "ai_prediction_snapshot_at"
                        ].isoformat()

                        if series_row[
                            "ai_prediction_snapshot_at"
                        ]

                        else None
                    ),

                "target_set_count":
                    int(
                        series_row[
                            "target_set_count"
                        ]
                        or 3
                    ),
            }
        )


    # =========================================
    # 2. 기존 Excel
    #
    # 프리시즌만 임시 유지
    # 정규리그는 이제 DB 사용
    # =========================================

    workbook = load_workbook(
        EXCEL_PATH
    )


    worksheet = workbook[
        "경기일정"
    ]


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


        # 경기구분이 비어 있으면
        # 기존 정규리그 데이터이므로 제외
        if match_type is None:
            continue


        # 정규리그는 DB에서만 조회
        if (
            match_type
            != "프리시즌"
        ):
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


        # 같은 프리시즌이 DB에 있으면
        # DB 데이터 우선
        if (
            match_key
            in database_match_keys
        ):
            continue


        matches.append(
            {
                "series_id":
                    None,

                "fixture_number":
                    None,

                "source":
                    "excel",

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
                    None,
            }
        )


    workbook.close()

    # =========================================
    # 일정 표시용 팀 정보
    #
    # 예정 / 진행 중:
    # participants의 현재 팀 정보 사용
    #
    # 완료 경기:
    # 경기 완료 당시 Snapshot 사용
    # =========================================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    fcl_name,
                    current_team_name,
                    current_team_logo_path

                FROM participants
                """
            )

            participant_team_rows = (
                cursor.fetchall()
            )


    participant_team_map = {
        row["fcl_name"]: row
        for row in participant_team_rows
    }

    # =========================================
    # AI 예측용 과거 경기 데이터
    #
    # API 요청 1회당 한 번만 계산
    # =========================================

    ai_prediction_context = (
        build_ai_prediction_context()
    )


    for match in matches:

        use_snapshot = (
            match.get(
                "source"
            )
            ==
            "database"
            and
            match.get(
                "status"
            )
            ==
            "completed"
        )

        # =====================================
        # AI 추천 승률
        #
        # 예정 경기:
        # 현재까지의 기록으로 실시간 계산
        #
        # 시작 / 완료 경기:
        # 경기 시작 순간 Snapshot 사용
        # =====================================

        if (
            match.get(
                "match_type"
            )
            ==
            "정규리그"

            and

            match.get(
                "status"
            )
            ==
            "scheduled"

            and

            match.get(
                "source"
            )
            ==
            "database"
        ):

            match[
                "ai_prediction"
            ] = (
                calculate_ai_match_prediction(
                    ai_prediction_context,

                    match[
                        "team_a"
                    ],

                    match[
                        "team_b"
                    ],
                )
            )


        elif (
            match.get(
                "match_type"
            )
            ==
            "정규리그"

            and

            match.get(
                "source"
            )
            ==
            "database"

            and

            match.get(
                "ai_prediction_snapshot"
            )
        ):

            match[
                "ai_prediction"
            ] = (
                match[
                    "ai_prediction_snapshot"
                ]
            )


        else:

            match[
                "ai_prediction"
            ] = None

        team_a_current = (
            participant_team_map.get(
                match["team_a"]
            )
        )

        team_b_current = (
            participant_team_map.get(
                match["team_b"]
            )
        )


        if team_a_current:

            match[
                "team_a_current_team_name"
            ] = (
                match.get(
                    "team_a_snapshot_name"
                )
                if (
                    use_snapshot
                    and
                    match.get(
                        "team_a_snapshot_name"
                    )
                )
                else
                team_a_current[
                    "current_team_name"
                ]
            )

            match[
                "team_a_current_team_logo_path"
            ] = (
                match.get(
                    "team_a_snapshot_logo_path"
                )
                if (
                    use_snapshot
                    and
                    match.get(
                        "team_a_snapshot_logo_path"
                    )
                )
                else
                team_a_current[
                    "current_team_logo_path"
                ]
            )

        else:

            match[
                "team_a_current_team_name"
            ] = None

            match[
                "team_a_current_team_logo_path"
            ] = None


        if team_b_current:

            match[
                "team_b_current_team_name"
            ] = (
                match.get(
                    "team_b_snapshot_name"
                )
                if (
                    use_snapshot
                    and
                    match.get(
                        "team_b_snapshot_name"
                    )
                )
                else
                team_b_current[
                    "current_team_name"
                ]
            )

            match[
                "team_b_current_team_logo_path"
            ] = (
                match.get(
                    "team_b_snapshot_logo_path"
                )
                if (
                    use_snapshot
                    and
                    match.get(
                        "team_b_snapshot_logo_path"
                    )
                )
                else
                team_b_current[
                    "current_team_logo_path"
                ]
            )

        else:

            match[
                "team_b_current_team_name"
            ] = None

            match[
                "team_b_current_team_logo_path"
            ] = None


    # =========================================
    # 날짜순
    # =========================================

    matches.sort(
        key=lambda match: (
            match["date"],
            (
                match[
                    "fixture_number"
                ]
                or 9999
            ),
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
    ).date()


    today_string = (
        today.isoformat()
    )


    # 기존 Excel 일정 사용
    all_matches = get_matches()


    matches = [
        match
        for match in all_matches
        if match["date"] == today_string
    ]


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            for match in matches:

                cursor.execute(
                    """
                    SELECT
                        s.id AS series_id,
                        s.status AS series_status

                    FROM series AS s

                    JOIN participants AS team_a
                        ON team_a.id =
                            s.team_a_id

                    JOIN participants AS team_b
                        ON team_b.id =
                            s.team_b_id

                    WHERE
                        s.scheduled_date = %s

                        AND
                        s.series_type = %s

                        AND
                        s.status <> 'cancelled'

                        AND (
                            (
                                team_a.fcl_name = %s
                                AND
                                team_b.fcl_name = %s
                            )

                            OR

                            (
                                team_a.fcl_name = %s
                                AND
                                team_b.fcl_name = %s
                            )
                        )

                    ORDER BY
                        CASE s.status

                            WHEN 'active'
                                THEN 1

                            WHEN 'scheduled'
                                THEN 2

                            WHEN 'completed'
                                THEN 3

                            ELSE 4

                        END,

                        s.id DESC

                    LIMIT 1
                    """,
                    (
                        today,

                        match["match_type"],

                        match["team_a"],
                        match["team_b"],

                        match["team_b"],
                        match["team_a"],
                    ),
                )


                series = cursor.fetchone()


                if series:

                    match["series_id"] = (
                        series["series_id"]
                    )

                    match["series_status"] = (
                        series["series_status"]
                    )

                else:

                    match["series_id"] = None

                    match["series_status"] = (
                        "not_started"
                    )


    return matches

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
        expected_set_count=3,
    ):

        if (
            team_a not in standings
            or
            team_b not in standings
        ):
            return


        # SERIES에 설정된
        # 세트 수가 모두 있어야 반영
        if (
            len(sets)
            != expected_set_count
        ):
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
                    s.target_set_count,

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

                "target_set_count":
                    int(
                        row[
                            "target_set_count"
                        ]
                        or 3
                    ),

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


        expected_set_count = int(
            series_data[
                "target_set_count"
            ]
            or 3
        )


        if (
            len(sets)
            != expected_set_count
        ):
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

            expected_set_count,
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


    # =========================
    # 참가자 현재 팀 정보
    #
    # 현재 화면에서 사용하는 팀 정보는
    # participants 테이블을 기준으로 함
    #
    # 과거 SERIES Snapshot은
    # 절대 수정하지 않음
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    fcl_name,
                    current_team_name,
                    current_team_logo_path

                FROM participants
                """
            )

            participant_team_rows = (
                cursor.fetchall()
            )


    participant_team_map = {
        row["fcl_name"]: row
        for row in participant_team_rows
    }


    for record in sorted_standings:

        participant_team = (
            participant_team_map.get(
                record["name"]
            )
        )

        if participant_team:

            record["current_team_name"] = (
                participant_team[
                    "current_team_name"
                ]
            )

            record[
                "current_team_logo_path"
            ] = (
                participant_team[
                    "current_team_logo_path"
                ]
            )

        else:

            record["current_team_name"] = None

            record[
                "current_team_logo_path"
            ] = None


    return sorted_standings

# =========================
# ADMIN PLAYOFF UPDATE
# 날짜 / 경기 방식 변경
# =========================

@app.put(
    "/api/admin/playoffs/{series_id}"
)
def admin_update_playoff(
    series_id: int,

    request:
        AdminPlayoffUpdateRequest,

    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 날짜 검증
    # =========================

    try:

        scheduled_date = (
            datetime.strptime(
                request.scheduled_date,
                "%Y-%m-%d",
            ).date()
        )

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


    if scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로는 "
                "일정을 변경할 수 없습니다."
            ),
        )


    # =========================
    # 경기 방식
    # =========================

    wins_required_map = {
        3: 2,
        5: 3,
        7: 4,
    }


    best_of = int(
        request.best_of
    )


    wins_required = (
        wins_required_map[
            best_of
        ]
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 조회 + 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.playoff_stage,
                    s.scheduled_date,
                    s.best_of,
                    s.wins_required,
                    s.status,

                    (
                        SELECT COUNT(*)

                        FROM series_sets AS ss

                        WHERE
                            ss.series_id = s.id
                    ) AS set_count

                FROM series AS s

                WHERE s.id = %s

                FOR UPDATE
                """,
                (
                    series_id,
                ),
            )


            series = (
                cursor.fetchone()
            )


            if not series:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "플레이오프 경기를 "
                        "찾을 수 없습니다."
                    ),
                )


            # =========================
            # 플레이오프만 허용
            # =========================

            if (
                series["series_type"]
                != "플레이오프"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 경기만 "
                        "변경할 수 있습니다."
                    ),
                )


            # =========================
            # 예정 경기만 수정
            # =========================

            if (
                series["status"]
                != "scheduled"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "아직 시작하지 않은 "
                        "플레이오프 경기만 "
                        "변경할 수 있습니다."
                    ),
                )


            # =========================
            # 세트 결과 존재 여부
            # =========================

            if (
                int(
                    series["set_count"]
                    or 0
                )
                > 0
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "이미 세트 결과가 있는 "
                        "경기는 변경할 수 없습니다."
                    ),
                )


            previous_date = (
                series[
                    "scheduled_date"
                ]
            )

            previous_best_of = int(
                series[
                    "best_of"
                ]
            )

            previous_wins_required = int(
                series[
                    "wins_required"
                ]
            )


            # =========================
            # 실제 변경
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    scheduled_date = %s,
                    best_of = %s,
                    wins_required = %s

                WHERE id = %s

                RETURNING
                    id,
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required,
                    status
                """,
                (
                    scheduled_date,
                    best_of,
                    wins_required,
                    series_id,
                ),
            )


            updated_series = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "series_id":
            updated_series["id"],

        "playoff_stage":
            updated_series[
                "playoff_stage"
            ],

        "previous_date":
            (
                previous_date.isoformat()
                if previous_date
                else None
            ),

        "scheduled_date":
            updated_series[
                "scheduled_date"
            ].isoformat(),

        "previous_best_of":
            previous_best_of,

        "previous_wins_required":
            previous_wins_required,

        "best_of":
            updated_series[
                "best_of"
            ],

        "wins_required":
            updated_series[
                "wins_required"
            ],

        "status":
            updated_series[
                "status"
            ],

        "message":
            (
                "플레이오프 설정이 "
                "변경되었습니다."
            ),
    }

# =========================
# ADMIN PLAYOFF SETTING UPDATE
#
# SERIES 생성 전:
# playoff_settings만 변경
#
# SERIES 생성 후 scheduled:
# settings + SERIES 같이 변경
# =========================

@app.put(
    "/api/admin/playoffs/settings/{playoff_stage}"
)
def admin_update_playoff_setting(
    playoff_stage: str,

    request:
        AdminPlayoffUpdateRequest,

    admin_token: str =
        Depends(
            require_admin
        ),
):

    allowed_stages = (
        "준플레이오프",
        "플레이오프",
        "결승시리즈",
    )


    if (
        playoff_stage
        not in allowed_stages
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "올바르지 않은 "
                "플레이오프 단계입니다."
            ),
        )


    # =========================
    # 날짜 검증
    # =========================

    try:

        scheduled_date = (
            datetime.strptime(
                request.scheduled_date,
                "%Y-%m-%d",
            ).date()
        )

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


    if scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로는 "
                "일정을 변경할 수 없습니다."
            ),
        )


    wins_required_map = {
        3: 2,
        5: 3,
        7: 4,
    }


    best_of = int(
        request.best_of
    )


    wins_required = (
        wins_required_map[
            best_of
        ]
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 이미 실제 SERIES가
            # 생성되어 있는지 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.status,

                    (
                        SELECT COUNT(*)

                        FROM series_sets AS ss

                        WHERE
                            ss.series_id = s.id
                    ) AS set_count

                FROM series AS s

                WHERE
                    s.series_type =
                        '플레이오프'

                    AND
                    s.playoff_stage = %s

                    AND
                    s.status <>
                        'cancelled'

                ORDER BY
                    s.id DESC

                LIMIT 1

                FOR UPDATE
                """,
                (
                    playoff_stage,
                ),
            )


            series = (
                cursor.fetchone()
            )


            # =========================
            # 생성된 SERIES가 있다면
            # 예정 상태에서만 변경
            # =========================

            if series:

                if (
                    series["status"]
                    != "scheduled"
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이미 시작되었거나 완료된 "
                            "플레이오프 경기는 "
                            "설정을 변경할 수 없습니다."
                        ),
                    )


                if (
                    int(
                        series["set_count"]
                        or 0
                    )
                    > 0
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "이미 세트 결과가 있는 "
                            "경기는 변경할 수 없습니다."
                        ),
                    )


            # =========================
            # 기본 설정 저장
            # =========================

            cursor.execute(
                """
                INSERT INTO playoff_settings (
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required,
                    updated_at
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )

                ON CONFLICT (
                    playoff_stage
                )

                DO UPDATE SET
                    scheduled_date =
                        EXCLUDED.scheduled_date,

                    best_of =
                        EXCLUDED.best_of,

                    wins_required =
                        EXCLUDED.wins_required,

                    updated_at =
                        NOW()

                RETURNING
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required
                """,
                (
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required,
                ),
            )


            setting = (
                cursor.fetchone()
            )


            # =========================
            # 실제 SERIES가 이미 있으면
            # 같이 변경
            # =========================

            if series:

                cursor.execute(
                    """
                    UPDATE series

                    SET
                        scheduled_date = %s,
                        best_of = %s,
                        wins_required = %s

                    WHERE id = %s
                    """,
                    (
                        scheduled_date,
                        best_of,
                        wins_required,
                        series["id"],
                    ),
                )


        connection.commit()


    return {
        "playoff_stage":
            setting[
                "playoff_stage"
            ],

        "scheduled_date":
            setting[
                "scheduled_date"
            ].isoformat(),

        "best_of":
            setting[
                "best_of"
            ],

        "wins_required":
            setting[
                "wins_required"
            ],

        "series_id":
            (
                series["id"]
                if series
                else None
            ),

        "series_updated":
            bool(series),

        "message":
            (
                "플레이오프 설정이 "
                "변경되었습니다."
            ),
    }

# =========================
# PLAYOFF PREVIEW
# 현재 정규리그 순위 기준
# =========================

@app.get(
    "/api/admin/playoffs/preview"
)
def preview_playoffs(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 정규리그 진행 상태
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_count,

                    COUNT(*) FILTER (
                        WHERE status = 'completed'
                    ) AS completed_count

                FROM series

                WHERE
                    series_type = '정규리그'
                    AND status <> 'cancelled'
                """
            )

            regular_status = (
                cursor.fetchone()
            )


    total_count = int(
        regular_status["total_count"]
    )

    completed_count = int(
        regular_status["completed_count"]
    )


    # =========================
    # 현재 정규리그 순위
    # =========================

    standings = get_standings()


    if len(standings) < 5:

        raise HTTPException(
            status_code=400,
            detail=(
                "정규리그 순위를 "
                "확인할 수 없습니다."
            ),
        )


    first_place = standings[0]
    second_place = standings[1]
    third_place = standings[2]
    fourth_place = standings[3]
    fifth_place = standings[4]


    # =========================
    # 미리보기 반환
    # =========================

    return {
        "regular_league": {
            "total": total_count,
            "completed": completed_count,
            "is_completed": (
                total_count == 20
                and
                completed_count == 20
            ),
        },

        "standings": [
            {
                "rank": participant["rank"],
                "name": participant["name"],
                "points": participant["points"],
                "goal_difference":
                    participant[
                        "goal_difference"
                    ],
                "goals_for":
                    participant["goals_for"],
            }

            for participant
            in standings[:5]
        ],

        "playoff_bracket": {
            "준플레이오프": {
                "best_of": 5,
                "wins_required": 3,

                "team_a": {
                    "rank": 3,
                    "name":
                        third_place["name"],
                },

                "team_b": {
                    "rank": 4,
                    "name":
                        fourth_place["name"],
                },
            },

            "플레이오프": {
                "best_of": 5,
                "wins_required": 3,

                "team_a": {
                    "rank": 2,
                    "name":
                        second_place["name"],
                },

                "team_b": {
                    "source":
                        "준플레이오프 승자",
                },
            },

            "결승시리즈": {
                "best_of": 7,
                "wins_required": 4,

                "team_a": {
                    "rank": 1,
                    "name":
                        first_place["name"],
                },

                "team_b": {
                    "source":
                        "플레이오프 승자",
                },
            },
        },

        "eliminated": {
            "rank": 5,
            "name":
                fifth_place["name"],
        },
    }


# =========================
# PLAYOFF INITIALIZE
# 정규리그 3위 VS 4위
# =========================

@app.post(
    "/api/admin/playoffs/initialize"
)
def initialize_playoffs(
    request: PlayoffInitializeRequest,

    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 경기 날짜 검증
    # =========================

    try:

        scheduled_date = (
            datetime.strptime(
                request.scheduled_date,
                "%Y-%m-%d",
            ).date()
        )

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


    if scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로 플레이오프를 "
                "생성할 수 없습니다."
            ),
        )


    # =========================
    # 정규리그 완료 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_count,

                    COUNT(*) FILTER (
                        WHERE status = 'completed'
                    ) AS completed_count

                FROM series

                WHERE
                    series_type = '정규리그'
                    AND status <> 'cancelled'
                """
            )


            regular_status = (
                cursor.fetchone()
            )


    total_count = int(
        regular_status[
            "total_count"
        ]
    )

    completed_count = int(
        regular_status[
            "completed_count"
        ]
    )


    if (
        total_count != 20
        or
        completed_count != 20
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "정규리그 20경기가 "
                "모두 완료된 후 "
                "플레이오프를 생성할 수 있습니다."
            ),
        )


    # =========================
    # 기존 플레이오프 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    playoff_stage,
                    status

                FROM series

                WHERE
                    series_type = '플레이오프'

                    AND
                    playoff_stage = '준플레이오프'

                    AND
                    status <> 'cancelled'

                LIMIT 1
                """
            )


            existing_series = (
                cursor.fetchone()
            )


    if existing_series:

        raise HTTPException(
            status_code=400,
            detail=(
                "이미 준플레이오프 "
                "SERIES가 생성되어 있습니다."
            ),
        )


    # =========================
    # 정규리그 최종 순위
    # =========================

    standings = get_standings()


    if len(standings) < 4:

        raise HTTPException(
            status_code=400,
            detail=(
                "플레이오프 진출자를 "
                "확정할 수 없습니다."
            ),
        )


    third_place = standings[2]

    fourth_place = standings[3]


    team_a_name = (
        third_place["name"]
    )

    team_b_name = (
        fourth_place["name"]
    )


    # =========================
    # 참가자 ID 조회
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname

                FROM participants

                WHERE fcl_name IN (
                    %s,
                    %s
                )
                """,
                (
                    team_a_name,
                    team_b_name,
                ),
            )


            participant_rows = (
                cursor.fetchall()
            )


            participant_map = {
                participant[
                    "fcl_name"
                ]:
                    participant

                for participant
                in participant_rows
            }


            if (
                team_a_name
                not in participant_map

                or

                team_b_name
                not in participant_map
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 참가자 정보를 "
                        "찾을 수 없습니다."
                    ),
                )


            team_a = participant_map[
                team_a_name
            ]

            team_b = participant_map[
                team_b_name
            ]


            # =========================
            # 준플레이오프 SERIES 생성
            # =========================

            cursor.execute(
                """
                INSERT INTO series (
                    series_type,

                    team_a_id,
                    team_b_id,

                    match_type,

                    scheduled_date,

                    playoff_stage,
                    best_of,
                    wins_required,

                    stats_sync_status,
                    status
                )

                VALUES (
                    '플레이오프',

                    %s,
                    %s,

                    40,

                    %s,

                    '준플레이오프',
                    5,
                    3,

                    'pending',
                    'scheduled'
                )

                RETURNING
                    id,
                    scheduled_date,
                    playoff_stage,
                    best_of,
                    wins_required,
                    status
                """,
                (
                    team_a["id"],
                    team_b["id"],
                    scheduled_date,
                ),
            )


            series_row = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "series_id":
            series_row["id"],

        "series_type":
            "플레이오프",

        "playoff_stage":
            series_row[
                "playoff_stage"
            ],

        "scheduled_date":
            series_row[
                "scheduled_date"
            ].isoformat(),

        "team_a": {
            "rank": 3,
            "fcl_name":
                team_a["fcl_name"],
            "nickname":
                team_a[
                    "fc_nickname"
                ],
        },

        "team_b": {
            "rank": 4,
            "fcl_name":
                team_b["fcl_name"],
            "nickname":
                team_b[
                    "fc_nickname"
                ],
        },

        "best_of":
            series_row[
                "best_of"
            ],

        "wins_required":
            series_row[
                "wins_required"
            ],

        "status":
            series_row["status"],
    }


# =========================
# PLAYOFF ADVANCE
# 다음 플레이오프 단계 생성
# =========================

@app.post(
    "/api/admin/playoffs/{series_id}/advance"
)
def advance_playoff_series(
    series_id: int,
    request: PlayoffAdvanceRequest,

    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 다음 경기 날짜 검증
    # =========================

    try:

        scheduled_date = (
            datetime.strptime(
                request.scheduled_date,
                "%Y-%m-%d",
            ).date()
        )

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


    if scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로 다음 "
                "플레이오프 경기를 "
                "생성할 수 없습니다."
            ),
        )


    # =========================
    # 정규리그 최종 순위
    #
    # 다음 단계의
    # 1위 / 2위 참가자 확인
    # =========================

    standings = get_standings()


    if len(standings) < 4:

        raise HTTPException(
            status_code=400,
            detail=(
                "정규리그 최종 순위를 "
                "확인할 수 없습니다."
            ),
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 현재 플레이오프 SERIES
            #
            # 동시에 advance 되는 것을
            # 방지하기 위해 행 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,
                    s.status,
                    s.completed_at,

                    s.team_a_id,
                    s.team_b_id,

                    team_a.fcl_name
                        AS team_a_name,

                    team_a.fc_nickname
                        AS team_a_nickname,

                    team_b.fcl_name
                        AS team_b_name,

                    team_b.fc_nickname
                        AS team_b_nickname

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE s.id = %s

                FOR UPDATE OF s
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


            # =========================
            # 플레이오프 확인
            # =========================

            if (
                series["series_type"]
                != "플레이오프"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 SERIES만 "
                        "다음 단계로 "
                        "진출시킬 수 있습니다."
                    ),
                )


            # =========================
            # 완료 상태 확인
            # =========================

            if (
                series["status"]
                != "completed"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "완료된 플레이오프만 "
                        "다음 단계로 "
                        "진출시킬 수 있습니다."
                    ),
                )


            # =========================
            # 결승은 다음 단계 없음
            # =========================

            if (
                series["playoff_stage"]
                == "결승시리즈"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "결승시리즈는 "
                        "다음 단계가 없습니다."
                    ),
                )


            # =========================
            # 현재 SERIES 세트 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    winner_side

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )


            saved_sets = cursor.fetchall()


            if not saved_sets:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 세트 결과가 "
                        "없습니다."
                    ),
                )


            # =========================
            # SERIES 승자 계산
            #
            # 선승 도달 이후 세트가
            # 존재하는지도 검증
            # =========================

            team_a_wins = 0
            team_b_wins = 0

            series_winner_side = None
            winning_set_number = None


            for saved_set in saved_sets:

                winner_side = (
                    saved_set[
                        "winner_side"
                    ]
                )


                if winner_side not in (
                    "team_a",
                    "team_b",
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "플레이오프 세트의 "
                            "승패 정보가 "
                            "올바르지 않습니다."
                        ),
                    )


                # 이미 선승 도달 후인데
                # 추가 세트가 존재하면 비정상
                if (
                    series_winner_side
                    is not None
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "선승 도달 이후의 "
                            "추가 세트가 존재합니다."
                        ),
                    )


                if (
                    winner_side
                    == "team_a"
                ):

                    team_a_wins += 1

                else:

                    team_b_wins += 1


                if (
                    team_a_wins
                    >=
                    int(
                        series[
                            "wins_required"
                        ]
                    )
                ):

                    series_winner_side = (
                        "team_a"
                    )

                    winning_set_number = (
                        saved_set[
                            "set_number"
                        ]
                    )


                elif (
                    team_b_wins
                    >=
                    int(
                        series[
                            "wins_required"
                        ]
                    )
                ):

                    series_winner_side = (
                        "team_b"
                    )

                    winning_set_number = (
                        saved_set[
                            "set_number"
                        ]
                    )


            # =========================
            # 선승 미도달 방어
            # =========================

            if series_winner_side is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "SERIES 승자가 "
                        "확정되지 않았습니다."
                    ),
                )


            # =========================
            # 최대 세트 수 방어
            # =========================

            if (
                len(saved_sets)
                >
                int(
                    series["best_of"]
                )
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "허용된 경기 수보다 "
                        "많은 세트가 "
                        "저장되어 있습니다."
                    ),
                )


            # =========================
            # 현재 SERIES 승자
            # =========================

            if (
                series_winner_side
                == "team_a"
            ):

                winner_id = (
                    series[
                        "team_a_id"
                    ]
                )

                winner_name = (
                    series[
                        "team_a_name"
                    ]
                )

                winner_nickname = (
                    series[
                        "team_a_nickname"
                    ]
                )

            else:

                winner_id = (
                    series[
                        "team_b_id"
                    ]
                )

                winner_name = (
                    series[
                        "team_b_name"
                    ]
                )

                winner_nickname = (
                    series[
                        "team_b_nickname"
                    ]
                )


            # =========================
            # 다음 단계 설정
            # =========================

            if (
                series["playoff_stage"]
                == "준플레이오프"
            ):

                next_stage = (
                    "플레이오프"
                )

                seeded_rank = 2


            elif (
                series["playoff_stage"]
                == "플레이오프"
            ):

                next_stage = (
                    "결승시리즈"
                )

                seeded_rank = 1


            else:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "알 수 없는 "
                        "플레이오프 단계입니다."
                    ),
                )

            next_playoff_setting = (
                get_playoff_setting(
                    next_stage
                )
            )


            if not next_playoff_setting:

                raise HTTPException(
                    status_code=500,
                    detail=(
                        f"{next_stage} 설정을 "
                        "찾을 수 없습니다."
                    ),
                )


            next_best_of = int(
                next_playoff_setting[
                    "best_of"
                ]
            )


            next_wins_required = int(
                next_playoff_setting[
                    "wins_required"
                ]
            )


            # =========================
            # 이미 다음 단계가
            # 생성되어 있는지 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    status

                FROM series

                WHERE
                    series_type =
                        '플레이오프'

                    AND
                    playoff_stage = %s

                    AND
                    status <> 'cancelled'

                LIMIT 1
                """,
                (
                    next_stage,
                ),
            )


            existing_next_series = (
                cursor.fetchone()
            )


            if existing_next_series:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"이미 {next_stage} "
                        "SERIES가 "
                        "생성되어 있습니다."
                    ),
                )


            # =========================
            # 1위 또는 2위 확인
            # =========================

            seeded_name = (
                standings[
                    seeded_rank - 1
                ][
                    "name"
                ]
            )


            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname

                FROM participants

                WHERE fcl_name = %s
                """,
                (
                    seeded_name,
                ),
            )


            seeded_participant = (
                cursor.fetchone()
            )


            if not seeded_participant:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "시드 참가자 정보를 "
                        "찾을 수 없습니다."
                    ),
                )


            if (
                seeded_participant["id"]
                == winner_id
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "다음 플레이오프의 "
                        "두 참가자가 같습니다."
                    ),
                )


            # =========================
            # 다음 SERIES 생성
            #
            # team_a = 상위 시드
            # team_b = 이전 단계 승자
            # =========================

            cursor.execute(
                """
                INSERT INTO series (
                    series_type,

                    team_a_id,
                    team_b_id,

                    match_type,
                    scheduled_date,

                    playoff_stage,
                    best_of,
                    wins_required,

                    stats_sync_status,
                    status
                )

                VALUES (
                    '플레이오프',

                    %s,
                    %s,

                    40,
                    %s,

                    %s,
                    %s,
                    %s,

                    'pending',
                    'scheduled'
                )

                RETURNING
                    id,
                    scheduled_date,
                    playoff_stage,
                    best_of,
                    wins_required,
                    status
                """,
                (
                    seeded_participant[
                        "id"
                    ],

                    winner_id,

                    scheduled_date,

                    next_stage,
                    next_best_of,
                    next_wins_required,
                ),
            )


            next_series = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "source_series": {
            "series_id":
                series_id,

            "playoff_stage":
                series[
                    "playoff_stage"
                ],

            "winner": {
                "side":
                    series_winner_side,

                "fcl_name":
                    winner_name,

                "nickname":
                    winner_nickname,

                "wins":
                    (
                        team_a_wins
                        if
                        series_winner_side
                        == "team_a"
                        else
                        team_b_wins
                    ),

                "winning_set":
                    winning_set_number,
            },
        },

        "next_series": {
            "series_id":
                next_series[
                    "id"
                ],

            "playoff_stage":
                next_series[
                    "playoff_stage"
                ],

            "scheduled_date":
                next_series[
                    "scheduled_date"
                ].isoformat(),

            "team_a": {
                "rank":
                    seeded_rank,

                "fcl_name":
                    seeded_participant[
                        "fcl_name"
                    ],

                "nickname":
                    seeded_participant[
                        "fc_nickname"
                    ],
            },

            "team_b": {
                "source":
                    (
                        series[
                            "playoff_stage"
                        ]
                        + " 승자"
                    ),

                "fcl_name":
                    winner_name,

                "nickname":
                    winner_nickname,
            },

            "best_of":
                next_series[
                    "best_of"
                ],

            "wins_required":
                next_series[
                    "wins_required"
                ],

            "status":
                next_series[
                    "status"
                ],
        },

        "message":
            (
                f"{next_stage} SERIES가 "
                "생성되었습니다."
            ),
    }


# =========================
# 선수 기록 동기화 상태
# 정규리그만 확인
# =========================

@app.get("/api/player-rankings/sync-status")
def get_player_rankings_sync_status():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE
                            stats_sync_status =
                                'pending'
                    )
                        AS pending_count,

                    COUNT(*) FILTER (
                        WHERE
                            stats_sync_status =
                                'conflict'
                    )
                        AS conflict_count

                FROM series

                WHERE
                    status = 'completed'
                    AND
                    series_type = '정규리그'
                """
            )

            row = cursor.fetchone()


    pending_count = int(
        row["pending_count"]
        or 0
    )

    conflict_count = int(
        row["conflict_count"]
        or 0
    )


    return {
        "is_syncing":
            pending_count > 0,

        "pending_count":
            pending_count,

        "conflict_count":
            conflict_count,
    }

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
                WITH regular_squad_series AS (

                    SELECT DISTINCT
                        sssp.participant_id,
                        s.id AS series_id,
                        s.completed_at

                    FROM series_set_squad_players
                        AS sssp

                    JOIN series_sets AS ss
                        ON ss.id =
                            sssp.series_set_id

                    JOIN series AS s
                        ON s.id =
                            ss.series_id

                    WHERE
                        s.series_type =
                            '정규리그'

                        AND
                        s.status =
                            'completed'

                        AND
                        sssp.sp_position
                            BETWEEN 0 AND 27
                ),


                ranked_regular_series AS (

                    SELECT
                        participant_id,
                        series_id,

                        ROW_NUMBER() OVER (
                            PARTITION BY
                                participant_id

                            ORDER BY
                                completed_at DESC
                                    NULLS LAST,
                                series_id DESC
                        )
                            AS row_number

                    FROM regular_squad_series
                ),


                latest_regular_series AS (

                    SELECT
                        participant_id,
                        series_id

                    FROM ranked_regular_series

                    WHERE
                        row_number = 1
                ),


                preseason_squad_series AS (

                    SELECT DISTINCT
                        sssp.participant_id,
                        s.id AS series_id,
                        s.completed_at

                    FROM series_set_squad_players
                        AS sssp

                    JOIN series_sets AS ss
                        ON ss.id =
                            sssp.series_set_id

                    JOIN series AS s
                        ON s.id =
                            ss.series_id

                    WHERE
                        s.series_type =
                            '프리시즌'

                        AND
                        s.status =
                            'completed'

                        AND
                        sssp.sp_position
                            BETWEEN 0 AND 27
                ),


                ranked_preseason_series AS (

                    SELECT
                        participant_id,
                        series_id,

                        ROW_NUMBER() OVER (
                            PARTITION BY
                                participant_id

                            ORDER BY
                                completed_at DESC
                                    NULLS LAST,
                                series_id DESC
                        )
                            AS row_number

                    FROM preseason_squad_series
                ),


                latest_preseason_series AS (

                    SELECT
                        participant_id,
                        series_id

                    FROM ranked_preseason_series

                    WHERE
                        row_number = 1
                ),


                current_squad_source AS (

                    SELECT
                        participant_id,
                        series_id

                    FROM latest_regular_series


                    UNION ALL


                    SELECT
                        preseason.participant_id,
                        preseason.series_id

                    FROM latest_preseason_series
                        AS preseason

                    WHERE NOT EXISTS (
                        SELECT 1

                        FROM latest_regular_series
                            AS regular

                        WHERE
                            regular.participant_id =
                                preseason.participant_id
                    )
                ),

                latest_squad_set AS (

                    SELECT
                        source.participant_id,
                        source.series_id,

                        MAX(
                            ss.set_number
                        )
                            AS set_number

                    FROM current_squad_source
                        AS source

                    JOIN series_sets AS ss
                        ON ss.series_id =
                            source.series_id

                    GROUP BY
                        source.participant_id,
                        source.series_id
                ),


                current_squad_rows AS (

                    SELECT
                        sssp.participant_id,

                        TRIM(
                            sssp.player_name
                        )
                            AS player_name,

                        sssp.sp_id,
                        sssp.image_url,

                        ROW_NUMBER() OVER (
                            PARTITION BY
                                sssp.participant_id,
                                TRIM(
                                    sssp.player_name
                                )

                            ORDER BY
                                sssp.created_at DESC,
                                sssp.id DESC
                        )
                            AS row_number

                    FROM latest_squad_set
                        AS latest_set

                    JOIN series_sets AS ss
                        ON ss.series_id =
                            latest_set.series_id

                        AND
                        ss.set_number =
                            latest_set.set_number

                    JOIN series_set_squad_players
                        AS sssp
                        ON sssp.series_set_id =
                            ss.id

                        AND
                        sssp.participant_id =
                            latest_set.participant_id

                    WHERE
                        sssp.sp_position
                            BETWEEN 0 AND 27
                ),


                current_squad_players AS (

                    SELECT
                        participant_id,
                        player_name,
                        sp_id,
                        image_url

                    FROM current_squad_rows

                    WHERE
                        row_number = 1
                ),


                regular_stats AS (

                    SELECT
                        sps.participant_id,

                        TRIM(
                            sps.player_name
                        )
                            AS player_name,

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

                    WHERE
                        s.status =
                            'completed'

                        AND
                        s.series_type =
                            '정규리그'

                    GROUP BY
                        sps.participant_id,
                        TRIM(
                            sps.player_name
                        )
                ),


                regular_mvp AS (

                    SELECT
                        sm.participant_id,

                        TRIM(
                            sm.player_name
                        )
                            AS player_name,

                        COUNT(*)
                            AS mvp_count

                    FROM series_mvp AS sm

                    JOIN series AS s
                        ON s.id =
                            sm.series_id

                    WHERE
                        s.status =
                            'completed'

                        AND
                        s.series_type =
                            '정규리그'

                    GROUP BY
                        sm.participant_id,
                        TRIM(
                            sm.player_name
                        )
                )


                SELECT
                    p.id
                        AS participant_id,

                    p.fcl_name,

                    p.fc_nickname
                        AS nickname,

                    csp.player_name,

                    csp.sp_id,

                    csp.image_url,

                    COALESCE(
                        rs.sets_played,
                        0
                    )
                        AS sets_played,

                    COALESCE(
                        rs.rating_total,
                        0
                    )
                        AS rating_total,

                    COALESCE(
                        rs.goals,
                        0
                    )
                        AS goals,

                    COALESCE(
                        rs.assists,
                        0
                    )
                        AS assists,

                    COALESCE(
                        rm.mvp_count,
                        0
                    )
                        AS mvp_count

                FROM current_squad_players
                    AS csp

                JOIN participants AS p
                    ON p.id =
                        csp.participant_id

                LEFT JOIN regular_stats AS rs
                    ON rs.participant_id =
                        csp.participant_id

                    AND
                    rs.player_name =
                        csp.player_name

                LEFT JOIN regular_mvp AS rm
                    ON rm.participant_id =
                        csp.participant_id

                    AND
                    rm.player_name =
                        csp.player_name

                ORDER BY
                    COALESCE(
                        rs.goals,
                        0
                    ) DESC,

                    COALESCE(
                        rs.assists,
                        0
                    ) DESC,

                    COALESCE(
                        rs.rating_total,
                        0
                    ) DESC,

                    csp.player_name ASC,

                    p.id ASC
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


        goals = int(
            row["goals"]
        )


        assists = int(
            row["assists"]
        )

        mvp_count = int(
            row["mvp_count"]
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
                "fcl_name":
                    row["fcl_name"],

                "nickname":
                    row["nickname"],

                "player_name":
                    row["player_name"],

                "sp_id":
                    row["sp_id"],

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
                    goals,

                "assists":
                    assists,

                "mvp_count":
                    mvp_count,
            }
        )


    # =========================
    # 득점 공동 순위
    # =========================

    previous_goals = None
    previous_rank = 0


    for index, player in enumerate(
        players,
        start=1,
    ):

        if (
            previous_goals is None
            or
            player["goals"]
            != previous_goals
        ):

            previous_rank = index


        player["rank"] = (
            previous_rank
        )


        previous_goals = (
            player["goals"]
        )


    return players

# =========================
# 정규리그 확정 순위
#
# 남은 경기 최대 승점을 계산해서
# 승점만으로도 순위가 뒤집힐 수 없는
# 참가자만 확정 처리
#
# 동률 가능성이 있으면
# 득실차 / 득점과 관계없이
# 아직 확정하지 않음
# =========================

def get_locked_regular_seeds():

    standings = (
        get_standings()
    )


    if not standings:

        return {}


    current_points = {
        standing["name"]:
            int(
                standing["points"]
            )

        for standing
        in standings
    }


    remaining_max_points = {
        standing["name"]: 0

        for standing
        in standings
    }


    # =========================
    # 남은 정규리그 경기
    #
    # 세트 승 = 3점
    # 따라서 경기당 최대:
    # target_set_count * 3
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.target_set_count,

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
                        '정규리그'

                    AND
                    s.status IN (
                        'scheduled',
                        'active'
                    )
                """
            )


            remaining_series = (
                cursor.fetchall()
            )


    for series in remaining_series:

        max_series_points = (
            int(
                series[
                    "target_set_count"
                ]
                or 3
            )
            *
            3
        )


        team_a = (
            series[
                "team_a"
            ]
        )

        team_b = (
            series[
                "team_b"
            ]
        )


        if (
            team_a
            in remaining_max_points
        ):

            remaining_max_points[
                team_a
            ] += max_series_points


        if (
            team_b
            in remaining_max_points
        ):

            remaining_max_points[
                team_b
            ] += max_series_points


    # =========================
    # 최종 최대 가능 승점
    # =========================

    maximum_final_points = {
        name:
            (
                current_points[name]
                +
                remaining_max_points[name]
            )

        for name
        in current_points
    }


    locked_seeds = {}


    # =========================
    # 참가자별 정확한 최종 순위가
    # 승점만으로 확정됐는지 확인
    # =========================

    for participant in standings:

        name = (
            participant[
                "name"
            ]
        )

        participant_min = (
            current_points[
                name
            ]
        )

        participant_max = (
            maximum_final_points[
                name
            ]
        )


        guaranteed_above_count = 0

        rank_is_locked = True


        for other in standings:

            other_name = (
                other[
                    "name"
                ]
            )


            if (
                other_name
                == name
            ):
                continue


            other_min = (
                current_points[
                    other_name
                ]
            )

            other_max = (
                maximum_final_points[
                    other_name
                ]
            )


            # 상대가 어떤 경우에도
            # 이 참가자보다 위
            if (
                other_min
                >
                participant_max
            ):

                guaranteed_above_count += 1

                continue


            # 이 참가자가 어떤 경우에도
            # 상대보다 위
            if (
                participant_min
                >
                other_max
            ):

                continue


            # 승점 동률 또는 역전 가능
            # → 아직 정확한 순위 미확정
            rank_is_locked = False

            break


        if not rank_is_locked:
            continue


        locked_rank = (
            guaranteed_above_count
            + 1
        )


        if locked_rank in (
            1,
            2,
            3,
            4,
            5,
        ):

            locked_seeds[
                locked_rank
            ] = name


    return locked_seeds

def get_playoff_setting(
    playoff_stage: str,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required

                FROM playoff_settings

                WHERE playoff_stage = %s

                LIMIT 1
                """,
                (
                    playoff_stage,
                ),
            )


            setting = (
                cursor.fetchone()
            )


    return setting


def get_playoff_schedule_date(
    playoff_stage: str,
):

    setting = (
        get_playoff_setting(
            playoff_stage
        )
    )


    if not setting:
        return None


    return setting[
        "scheduled_date"
    ]


def create_initial_playoff_if_ready():

    # =========================
    # 정규리그 완료 여부
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_count,

                    COUNT(*) FILTER (
                        WHERE status = 'completed'
                    ) AS completed_count

                FROM series

                WHERE
                    series_type =
                        '정규리그'

                    AND
                    status <>
                        'cancelled'
                """
            )


            regular_status = (
                cursor.fetchone()
            )


    total_count = int(
        regular_status[
            "total_count"
        ]
    )

    completed_count = int(
        regular_status[
            "completed_count"
        ]
    )


    # 아직 정규리그가 안 끝남
    if (
        total_count != 20
        or
        completed_count != 20
    ):

        return None


    # =========================
    # 이미 준PO가 있는지 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id

                FROM series

                WHERE
                    series_type =
                        '플레이오프'

                    AND
                    playoff_stage =
                        '준플레이오프'

                    AND
                    status <>
                        'cancelled'

                LIMIT 1
                """
            )


            existing_series = (
                cursor.fetchone()
            )


    if existing_series:

        return {
            "created": False,
            "series_id":
                existing_series["id"],
        }


    # =========================
    # 최종 순위
    # =========================

    standings = get_standings()


    if len(standings) < 4:

        return None


    third_place = standings[2]
    fourth_place = standings[3]


    # =========================
    # 기존 플레이오프 일정에서
    # 준PO 날짜 가져오기
    # =========================

    playoff_setting = (
        get_playoff_setting(
            "준플레이오프"
        )
    )


    if not playoff_setting:

        raise RuntimeError(
            "준플레이오프 설정을 "
            "찾을 수 없습니다."
        )


    best_of = int(
        playoff_setting[
            "best_of"
        ]
    )

    wins_required = int(
        playoff_setting[
            "wins_required"
        ]
    )

    scheduled_date = (
        get_playoff_schedule_date(
            "준플레이오프"
        )
    )


    if scheduled_date is None:

        raise RuntimeError(
            "준플레이오프 일정 날짜를 "
            "찾을 수 없습니다."
        )


    # =========================
    # 참가자 조회 + SERIES 생성
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # 중복 생성 방지
            cursor.execute(
                """
                SELECT
                    pg_advisory_xact_lock(
                        20261010
                    )
                """
            )


            # lock을 기다리는 동안
            # 다른 요청이 먼저 만들었을 수 있으므로
            # 다시 확인
            cursor.execute(
                """
                SELECT
                    id

                FROM series

                WHERE
                    series_type =
                        '플레이오프'

                    AND
                    playoff_stage =
                        '준플레이오프'

                    AND
                    status <>
                        'cancelled'

                LIMIT 1
                """
            )


            existing_series = (
                cursor.fetchone()
            )


            if existing_series:

                return {
                    "created": False,
                    "series_id":
                        existing_series[
                            "id"
                        ],
                }


            cursor.execute(
                """
                SELECT
                    id,
                    fcl_name,
                    fc_nickname

                FROM participants

                WHERE fcl_name IN (
                    %s,
                    %s
                )
                """,
                (
                    third_place["name"],
                    fourth_place["name"],
                ),
            )


            participant_rows = (
                cursor.fetchall()
            )


            participant_map = {
                participant[
                    "fcl_name"
                ]:
                    participant

                for participant
                in participant_rows
            }


            if (
                third_place["name"]
                not in participant_map

                or

                fourth_place["name"]
                not in participant_map
            ):

                raise RuntimeError(
                    "플레이오프 참가자 정보를 "
                    "찾을 수 없습니다."
                )


            team_a = participant_map[
                third_place["name"]
            ]

            team_b = participant_map[
                fourth_place["name"]
            ]


            cursor.execute(
                """
                INSERT INTO series (
                    series_type,
                    team_a_id,
                    team_b_id,
                    match_type,
                    scheduled_date,
                    playoff_stage,
                    best_of,
                    wins_required,
                    stats_sync_status,
                    status
                )

                VALUES (
                    '플레이오프',
                    %s,
                    %s,
                    40,
                    %s,
                    '준플레이오프',
                    5,
                    3,
                    'pending',
                    'scheduled'
                )

                RETURNING
                    id,
                    scheduled_date
                """,
                (
                    team_a["id"],
                    team_b["id"],
                    scheduled_date,
                    best_of,
                    wins_required,
                ),
            )


            playoff_series = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "created": True,

        "series_id":
            playoff_series["id"],

        "scheduled_date":
            playoff_series[
                "scheduled_date"
            ].isoformat(),

        "team_a":
            team_a["fcl_name"],

        "team_b":
            team_b["fcl_name"],
    }

def create_next_playoff_if_ready(
    series_id: int,
):

    # =========================
    # 현재 플레이오프 확인
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    playoff_stage,
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
        return None


    if (
        series["series_type"]
        != "플레이오프"
    ):
        return None


    if (
        series["status"]
        != "completed"
    ):
        return None


    # =========================
    # 다음 단계
    # =========================

    if (
        series["playoff_stage"]
        == "준플레이오프"
    ):

        next_stage = "플레이오프"

    elif (
        series["playoff_stage"]
        == "플레이오프"
    ):

        next_stage = "결승시리즈"

    elif (
        series["playoff_stage"]
        == "결승시리즈"
    ):

        return {
            "created": False,
            "reason": "final_completed",
        }

    else:

        return None


    # =========================
    # 이미 다음 SERIES가 있는지
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id

                FROM series

                WHERE
                    series_type =
                        '플레이오프'

                    AND
                    playoff_stage = %s

                    AND
                    status <>
                        'cancelled'

                LIMIT 1
                """,
                (
                    next_stage,
                ),
            )


            existing_series = (
                cursor.fetchone()
            )


    if existing_series:

        return {
            "created": False,
            "series_id":
                existing_series["id"],
        }


    # =========================
    # 기존 플레이오프 일정 날짜
    # =========================

    scheduled_date = (
        get_playoff_schedule_date(
            next_stage
        )
    )


    if scheduled_date is None:

        raise RuntimeError(
            f"{next_stage} 일정 날짜를 "
            "찾을 수 없습니다."
        )


    # =========================
    # 기존 검증된 ADVANCE 로직 재사용
    # =========================

    request = PlayoffAdvanceRequest(
        scheduled_date=
            scheduled_date.isoformat()
    )


    try:

        result = advance_playoff_series(
            series_id,
            request,
            admin_token="internal",
        )

    except HTTPException:

        # 동시에 두 요청이 들어온 경우
        # 먼저 생성된 다음 SERIES 확인
        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        id

                    FROM series

                    WHERE
                        series_type =
                            '플레이오프'

                        AND
                        playoff_stage = %s

                        AND
                        status <>
                            'cancelled'

                    LIMIT 1
                    """,
                    (
                        next_stage,
                    ),
                )


                existing_series = (
                    cursor.fetchone()
                )


        if existing_series:

            return {
                "created": False,
                "series_id":
                    existing_series["id"],
            }


        raise


    return {
        "created": True,

        "series_id":
            result[
                "next_series"
            ][
                "series_id"
            ],

        "playoff_stage":
            next_stage,

        "scheduled_date":
            scheduled_date.isoformat(),
    }

# =========================
# 플레이오프 일정
#
# 날짜/단계:
# playoffs.xlsx
#
# 실제 대진/진행 상태:
# Neon SERIES
# =========================

@app.get("/api/playoffs")
def get_playoffs():

    # =========================
    # 1. 기존 플레이오프 일정
    # =========================

    workbook = load_workbook(
        PLAYOFFS_PATH,
        data_only=True,
    )

    worksheet = workbook[
        "플레이오프"
    ]

    schedule_rows = []


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


        if hasattr(
            match_date,
            "strftime",
        ):

            match_date = (
                match_date.strftime(
                    "%Y-%m-%d"
                )
            )


        stage_text = (
            str(stage).strip()
            if stage is not None
            else ""
        )


        # DB에서는
        # "결승시리즈"로 저장
        if stage_text == "결승 시리즈":

            database_stage = (
                "결승시리즈"
            )

        else:

            database_stage = (
                stage_text
            )


        schedule_rows.append(
            {
                "date":
                    str(match_date),

                "stage":
                    stage_text,

                "database_stage":
                    database_stage,

                "default_team_a":
                    team_a,

                "default_team_b":
                    team_b,
            }
        )


    workbook.close()

    # =========================
    # PLAYOFF 관리자 설정
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    playoff_stage,
                    scheduled_date,
                    best_of,
                    wins_required

                FROM playoff_settings
                """
            )


            setting_rows = (
                cursor.fetchall()
            )


    playoff_setting_map = {
        row[
            "playoff_stage"
        ]:
            row

        for row
        in setting_rows
    }

    # =========================
    # 정규리그 조기 확정 시드
    # =========================

    locked_seeds = (
        get_locked_regular_seeds()
    )


    # =========================
    # 2. 실제 플레이오프 SERIES
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,
                    s.status,
                    s.scheduled_date,

                    team_a.fcl_name
                        AS team_a_name,

                    team_b.fcl_name
                        AS team_b_name,

                    CASE
                        WHEN
                            s.status = 'completed'
                        THEN
                            COALESCE(
                                s.team_a_snapshot_logo_path,
                                team_a.current_team_logo_path
                            )
                        ELSE
                            team_a.current_team_logo_path
                    END
                        AS team_a_logo_path,

                    CASE
                        WHEN
                            s.status = 'completed'
                        THEN
                            COALESCE(
                                s.team_b_snapshot_logo_path,
                                team_b.current_team_logo_path
                            )
                        ELSE
                            team_b.current_team_logo_path
                    END
                        AS team_b_logo_path,

                    (
                        SELECT COUNT(*)
                        FROM series_sets AS ss
                        WHERE
                            ss.series_id = s.id
                    )
                        AS set_count,

                    (
                        SELECT COUNT(*)
                        FROM series_sets AS ss
                        WHERE
                            ss.series_id = s.id
                            AND
                            ss.winner_side = 'team_a'
                    )
                        AS team_a_wins,

                    (
                        SELECT COUNT(*)
                        FROM series_sets AS ss
                        WHERE
                            ss.series_id = s.id
                            AND
                            ss.winner_side = 'team_b'
                    )
                        AS team_b_wins

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE
                    s.series_type =
                        '플레이오프'

                    AND
                    s.status <>
                        'cancelled'

                ORDER BY
                    s.id DESC
                """
            )


            series_rows = (
                cursor.fetchall()
            )


    # =========================
    # 단계별 최신 SERIES
    # =========================

    series_by_stage = {}


    for series_row in series_rows:

        playoff_stage = (
            series_row[
                "playoff_stage"
            ]
        )


        if (
            playoff_stage
            not in series_by_stage
        ):

            series_by_stage[
                playoff_stage
            ] = series_row


    # =========================
    # 3. 일정 + SERIES 결합
    # =========================

    playoffs = []


    for schedule_row in schedule_rows:

        database_stage = (
            schedule_row[
                "database_stage"
            ]
        )


        series_row = (
            series_by_stage.get(
                database_stage
            )
        )


        playoff_setting = (
            playoff_setting_map.get(
                database_stage
            )
        )


        if playoff_setting:

            setting_date = (
                playoff_setting[
                    "scheduled_date"
                ].isoformat()
            )

            default_best_of = int(
                playoff_setting[
                    "best_of"
                ]
            )

            default_wins_required = int(
                playoff_setting[
                    "wins_required"
                ]
            )

        else:

            setting_date = (
                schedule_row[
                    "date"
                ]
            )

            default_best_of = None
            default_wins_required = None

        # =========================
        # SERIES 생성 전
        # 조기 확정 참가자 표시
        # =========================

        waiting_team_a = (
            schedule_row[
                "default_team_a"
            ]
            or
            "TBD"
        )

        waiting_team_b = (
            schedule_row[
                "default_team_b"
            ]
            or
            "TBD"
        )


        if (
            database_stage
            == "준플레이오프"
        ):

            waiting_team_a = (
                locked_seeds.get(
                    3
                )
                or
                "TBD"
            )

            waiting_team_b = (
                locked_seeds.get(
                    4
                )
                or
                "TBD"
            )


        elif (
            database_stage
            == "플레이오프"
        ):

            waiting_team_a = (
                locked_seeds.get(
                    2
                )
                or
                "TBD"
            )

            waiting_team_b = (
                "준플레이오프 승자"
            )


        elif (
            database_stage
            == "결승시리즈"
        ):

            waiting_team_a = (
                locked_seeds.get(
                    1
                )
                or
                "TBD"
            )

            waiting_team_b = (
                "플레이오프 승자"
            )


        # =====================
        # 아직 SERIES 없음
        # =====================

        if series_row is None:

            playoffs.append(
                {
                    "date":
                        setting_date,

                    "stage":
                        schedule_row[
                            "stage"
                        ],

                    "playoff_stage":
                        database_stage,

                    "series_id":
                        None,

                    "status":
                        "waiting",

                    "best_of":
                        default_best_of,

                    "wins_required":
                        default_wins_required,

                    "team_a":
                        waiting_team_a,

                    "team_b":
                        waiting_team_b,

                    "team_a_logo_path":
                        None,

                    "team_b_logo_path":
                        None,

                    "set_count":
                        0,

                    "team_a_wins":
                        0,

                    "team_b_wins":
                        0,
                }
            )

            continue


        # =====================
        # 실제 SERIES 존재
        # =====================

        team_a_wins = int(
            series_row[
                "team_a_wins"
            ]
        )

        team_b_wins = int(
            series_row[
                "team_b_wins"
            ]
        )


        winner = None


        if (
            series_row["status"]
            == "completed"
        ):

            if (
                team_a_wins
                >=
                int(
                    series_row[
                        "wins_required"
                    ]
                )
            ):

                winner = (
                    series_row[
                        "team_a_name"
                    ]
                )

            elif (
                team_b_wins
                >=
                int(
                    series_row[
                        "wins_required"
                    ]
                )
            ):

                winner = (
                    series_row[
                        "team_b_name"
                    ]
                )


        playoffs.append(
            {
                # 실제 SERIES가 생성된 뒤에는
                # DB의 변경된 일정을 우선 사용
                "date":
                    (
                        series_row[
                            "scheduled_date"
                        ].isoformat()

                        if series_row[
                            "scheduled_date"
                        ]

                        else schedule_row[
                            "date"
                        ]
                    ),

                "stage":
                    schedule_row[
                        "stage"
                    ],

                "playoff_stage":
                    database_stage,

                "series_id":
                    series_row["id"],

                "status":
                    series_row[
                        "status"
                    ],

                "best_of":
                    series_row[
                        "best_of"
                    ],

                "wins_required":
                    series_row[
                        "wins_required"
                    ],

                "team_a":
                    series_row[
                        "team_a_name"
                    ],

                "team_b":
                    series_row[
                        "team_b_name"
                    ],

                "team_a_logo_path":
                    series_row[
                        "team_a_logo_path"
                    ],

                "team_b_logo_path":
                    series_row[
                        "team_b_logo_path"
                    ],

                "set_count":
                    int(
                        series_row[
                            "set_count"
                        ]
                    ),

                "team_a_wins":
                    team_a_wins,

                "team_b_wins":
                    team_b_wins,

                "winner":
                    winner,
            }
        )


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
                            "goalTotal"
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
    # 친선전 생성 전용
    # =========================

    if (
        request.series_type
        != "프리시즌"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "정규리그 SERIES는 "
                "미리 등록된 일정만 "
                "사용할 수 있습니다."
            ),
        )


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
    # 경기 날짜
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


    if scheduled_date < today:

        raise HTTPException(
            status_code=400,
            detail=(
                "지난 날짜로 친선전을 "
                "생성할 수 없습니다."
            ),
        )


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
            # 동일 친선전 예약 중복 방지
            # 같은 날짜 + 같은 대진
            # =========================

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
                    status IN (
                        'scheduled',
                        'active'
                    )

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
            # 친선전 예약 생성
            # =========================
            cursor.execute(
                """
                INSERT INTO series (
                    series_type,

                    team_a_id,
                    team_b_id,

                    match_type,

                    include_extra_time_result,

                    target_set_count,

                    scheduled_date,
                    round_number,

                    status
                )

                VALUES (
                    '프리시즌',
                    %s,
                    %s,

                    40,

                    %s,

                    %s,

                    %s,
                    NULL,

                    'scheduled'
                )

                RETURNING id
                """,
                (
                    team_a["id"],
                    team_b["id"],

                    bool(
                        request
                            .include_extra_time_result
                    ),

                    int(
                        request
                            .target_set_count
                    ),

                    scheduled_date,
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
        "series_id":
            series_id,

        "series_type":
            "프리시즌",

        "team_a":
            request.team_a,

        "team_b":
            request.team_b,

        "nickname_a":
            team_a["fc_nickname"],

        "nickname_b":
            team_b["fc_nickname"],

        "match_type":
            40,

        "include_extra_time_result":
            bool(
                request
                    .include_extra_time_result
            ),

        "target_set_count":
            int(
                request
                    .target_set_count
            ),

        "started_at":
            None,

        "status":
            "scheduled",

        "set_count":
            0,

        "scheduled_date":
            request.scheduled_date,

        "round_number":
            None,
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


    if target_date > today:

        raise HTTPException(
            status_code=400,
            detail=(
                "경기 불러오기는 "
                "오늘 또는 지난 날짜만 가능합니다."
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
            parse_nexon_datetime(
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
    # 과거 친선전 세트 수
    # 자동 감지
    #
    # 1경기 -> 1세트
    # 2경기 -> 2세트
    # 3경기 -> 3세트
    # =========================

    detected_set_count = len(
        detected_matches
    )


    if detected_set_count == 0:

        raise HTTPException(
            status_code=400,
            detail=(
                f"{request.match_date} "
                "두 참가자의 맞대결을 "
                "찾지 못했습니다."
            ),
        )


    if detected_set_count > 3:

        raise HTTPException(
            status_code=400,
            detail=(
                f"{request.match_date} "
                "맞대결을 "
                f"{detected_set_count}경기 "
                "찾았습니다. "
                "같은 날짜에 4경기 이상이면 "
                "하나의 친선전 SERIES를 "
                "자동으로 구분할 수 없습니다."
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
                    = ANY(%s)

                LIMIT 1
                """,
                (
                    match_ids,
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
    # 최종 저장 세트 수
    #
    # DB INSERT 바로 직전에
    # 실제 detected_matches 기준으로
    # 다시 계산
    # =========================

    detected_set_count = len(
        detected_matches
    )


    if detected_set_count not in (
        1,
        2,
        3,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "과거 친선전은 "
                "1~3경기만 자동 등록할 수 있습니다. "
                f"현재 감지: {detected_set_count}경기"
            ),
        )


    # =========================
    # SERIES + 감지된 SET 저장
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

                    include_extra_time_result,
                    target_set_count,

                    scheduled_date,
                    round_number,

                    started_at,
                    completed_at,
                    finished_at,

                    status,
                    stats_sync_status
                )

                VALUES (
                    '프리시즌',

                    %s,
                    %s,

                    40,

                    %s,
                    %s,

                    %s,
                    NULL,

                    %s,
                    %s,
                    %s,

                    'completed',
                    'synced'
                )

                RETURNING id
                """,
                (
                    team_a["id"],
                    team_b["id"],

                    bool(
                        request
                            .include_extra_time_result
                    ),

                    detected_set_count,

                    target_date,

                    started_at,
                    completed_at,
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


                score_pair = (
                    get_match_score_pair(
                        match_data,
                        nickname_a,
                        nickname_b,
                        include_extra_time_result=
                            bool(
                                request
                                    .include_extra_time_result
                            ),
                    )
                )


                if score_pair is None:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{set_number}세트의 "
                            "점수를 확인할 수 없습니다."
                        ),
                    )


                (
                    team_a_score,
                    team_b_score,
                ) = score_pair


                winner_side = (
                    get_match_winner_side(
                        match_data,
                        nickname_a,
                        nickname_b,
                        "프리시즌",
                        bool(
                            request
                                .include_extra_time_result
                        ),
                    )
                )

                result_method = (
                    get_match_result_method(
                        match_data,
                        nickname_a,
                        nickname_b,
                        "프리시즌",
                        bool(
                            request
                                .include_extra_time_result
                        ),
                    )
                )


                if winner_side is None:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{set_number}세트의 "
                            "승패를 확인할 수 없습니다."
                        ),
                    )


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,

                        set_number,
                        nexon_match_id,
                        played_at,

                        team_a_score,
                        team_b_score,

                        score_source,
                        winner_side,
                        result_method
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,

                        %s,
                        %s,

                        'nexon',
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

                        winner_side,
                        result_method,
                    ),
                )

        connection.commit()

    # =========================
    # 세트별 스쿼드 Snapshot 저장
    # =========================

    save_series_set_squad_players(
        series_id,

        team_a["id"],
        nickname_a,

        team_b["id"],
        nickname_b,

        detected_matches,
    )


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

        "stats_sync_status":
            "synced",

        "match_date":
            target_date.isoformat(),

        "team_a":
            request.team_a,

        "team_b":
            request.team_b,

        "sets_found":
            detected_set_count,

        "match_ids":
            match_ids,

        "mvp":
            mvp,
    }

# =========================
# FCL SERIES ACTIVATE
# 예약된 경기 실제 시작
# 프리시즌 + 정규리그
# =========================

@app.post(
    "/api/fconline/series/{series_id}/activate"
)
def activate_fcl_series(
    series_id: int,
):

    now = datetime.now(
        ZoneInfo("Asia/Seoul")
    )

    today = now.date()


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.scheduled_date,

                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,

                    s.status,

                    s.team_a_id,
                    s.team_b_id,

                    team_a.fcl_name
                        AS team_a,

                    team_a.current_team_name
                        AS team_a_current_team_name,

                    team_a.current_team_logo_path
                        AS team_a_current_team_logo_path,

                    team_b.fcl_name
                        AS team_b,

                    team_b.current_team_name
                        AS team_b_current_team_name,

                    team_b.current_team_logo_path
                        AS team_b_current_team_logo_path

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


            # =========================
            # SERIES 종류 확인
            # =========================

            if (
                series["series_type"]
                not in (
                    "프리시즌",
                    "정규리그",
                    "플레이오프",
                )
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "시작할 수 없는 "
                        "SERIES 종류입니다."
                    ),
                )


            # =========================
            # 예약 상태 확인
            # =========================

            if (
                series["status"]
                != "scheduled"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "예약된 경기만 "
                        "시작할 수 있습니다."
                    ),
                )


            # =========================
            # 경기 당일 확인
            # =========================

            if (
                series["scheduled_date"]
                != today
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "경기는 예정된 "
                        "경기 당일에만 "
                        "시작할 수 있습니다."
                    ),
                )


            # =========================
            # 동일 대진 ACTIVE 확인
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

            # =========================
            # AI 경기 예측 Snapshot
            #
            # 정규리그만 저장
            #
            # 아직 status가 scheduled이므로
            # 현재 SERIES 결과가 학습 데이터에
            # 들어갈 일도 없음
            # =========================

            ai_prediction_snapshot = None


            if (
                series[
                    "series_type"
                ]
                ==
                "정규리그"
            ):

                ai_prediction_context = (
                    build_ai_prediction_context()
                )


                ai_prediction_snapshot = (
                    calculate_ai_match_prediction(
                        ai_prediction_context,

                        series[
                            "team_a"
                        ],

                        series[
                            "team_b"
                        ],
                    )
                )


            # =========================
            # SERIES 시작
            #
            # 경기 시작 순간의 현재 팀을
            # 역사 보존용 Snapshot으로 고정
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'active',
                    started_at = %s,
                    completed_at = NULL,
                    finished_at = NULL,
                    stats_sync_status =
                        'pending',

                    team_a_snapshot_name = %s,
                    team_a_snapshot_logo_path = %s,

                    team_b_snapshot_name = %s,
                    team_b_snapshot_logo_path = %s,

                    ai_prediction_snapshot = %s,
                    ai_prediction_snapshot_at = %s

                WHERE id = %s
                """,
                (
                    now,

                    series[
                        "team_a_current_team_name"
                    ],

                    series[
                        "team_a_current_team_logo_path"
                    ],

                    series[
                        "team_b_current_team_name"
                    ],

                    series[
                        "team_b_current_team_logo_path"
                    ],

                    (
                        Jsonb(
                            ai_prediction_snapshot
                        )

                        if
                        ai_prediction_snapshot
                        is not None

                        else
                        None
                    ),

                    (
                        now

                        if
                        ai_prediction_snapshot
                        is not None

                        else
                        None
                    ),

                    series_id,
                ),
            )


        connection.commit()


    return {
        "series_id":
            series_id,

        "series_type":
            series["series_type"],

        "playoff_stage":
            series["playoff_stage"],

        "best_of":
            series["best_of"],

        "wins_required":
            series["wins_required"],

        "team_a":
            series["team_a"],

        "team_b":
            series["team_b"],

        "scheduled_date":
            series[
                "scheduled_date"
            ].isoformat(),

        "started_at":
            now.isoformat(),

        "status":
            "active",

        "ai_prediction_snapshot":
            ai_prediction_snapshot,
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

    cancelled_at = datetime.now(
        ZoneInfo("Asia/Seoul")
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 확인
            #
            # 취소와 완료 처리가 동시에
            # 발생하지 않도록 행 잠금
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    series_type,
                    status,
                    started_at

                FROM series

                WHERE id = %s

                FOR UPDATE
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


            # =========================
            # 프리시즌만 취소 가능
            # =========================

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


            # =========================
            # 예약 / 진행 중만 취소 가능
            # =========================

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


            previous_status = series["status"]


            # =========================
            # 세트 삭제
            #
            # nexon_match_id UNIQUE 연결도
            # 같이 제거됨
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


            deleted_set_count = cursor.rowcount


            # =========================
            # MVP 삭제
            # =========================

            cursor.execute(
                """
                DELETE FROM series_mvp
                WHERE series_id = %s
                """,
                (
                    series_id,
                ),
            )


            # =========================
            # 선수 기록 삭제
            # =========================

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
            # SERIES 취소
            #
            # started_at은 유지
            # → 시작 후 취소 여부 확인 가능
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'cancelled',

                    cancelled_at = %s,

                    completed_at = NULL,
                    finished_at = NULL,

                    stats_sync_status = 'pending',

                    team_a_snapshot_name = NULL,
                    team_a_snapshot_logo_path = NULL,

                    team_b_snapshot_name = NULL,
                    team_b_snapshot_logo_path = NULL

                WHERE id = %s

                RETURNING
                    id,
                    status,
                    started_at,
                    cancelled_at
                """,
                (
                    cancelled_at,
                    series_id,
                ),
            )


            cancelled_series = cursor.fetchone()


        connection.commit()


    return {
        "series_id":
            cancelled_series["id"],

        "previous_status":
            previous_status,

        "status":
            cancelled_series["status"],

        "started_at":
            (
                cancelled_series[
                    "started_at"
                ].isoformat()
                if cancelled_series[
                    "started_at"
                ]
                else None
            ),

        "cancelled_at":
            cancelled_series[
                "cancelled_at"
            ].isoformat(),

        "deleted_set_count":
            deleted_set_count,

        "message":
            "친선전이 취소되었습니다.",
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

    finished_at = datetime.now(
        ZoneInfo("Asia/Seoul")
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
                    s.target_set_count,

                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,

                    team_a.fcl_name
                        AS team_a,

                    team_a.current_team_name
                        AS team_a_current_team_name,

                    team_a.current_team_logo_path
                        AS team_a_current_team_logo_path,

                    team_b.fcl_name
                        AS team_b,

                    team_b.current_team_name
                        AS team_b_current_team_name,

                    team_b.current_team_logo_path
                        AS team_b_current_team_logo_path

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE s.id = %s

                FOR UPDATE OF s
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
            # 지원 SERIES
            # =========================

            if series["series_type"] not in (
                "프리시즌",
                "정규리그",
                "플레이오프",
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "수동 결과를 입력할 수 없는 "
                        "SERIES입니다."
                    ),
                )


            # =========================
            # 진행 중 경기만 가능
            # =========================

            if series["status"] != "active":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "진행 중인 SERIES만 "
                        "수동 완료할 수 있습니다."
                    ),
                )


            # =========================
            # 완료 Snapshot 검증
            # =========================

            if (
                not series[
                    "team_a_current_team_name"
                ]
                or
                not series[
                    "team_a_current_team_logo_path"
                ]
                or
                not series[
                    "team_b_current_team_name"
                ]
                or
                not series[
                    "team_b_current_team_logo_path"
                ]
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "현재 팀 또는 로고 정보가 "
                        "등록되지 않았습니다."
                    ),
                )


            # =========================
            # 입력된 모든 세트
            # =========================

            requested_sets = [
                (
                    1,
                    request.set1_team_a,
                    request.set1_team_b,
                    request.set1_winner_side,
                ),
                (
                    2,
                    request.set2_team_a,
                    request.set2_team_b,
                    request.set2_winner_side,
                ),
                (
                    3,
                    request.set3_team_a,
                    request.set3_team_b,
                    request.set3_winner_side,
                ),
                (
                    4,
                    request.set4_team_a,
                    request.set4_team_b,
                    request.set4_winner_side,
                ),
                (
                    5,
                    request.set5_team_a,
                    request.set5_team_b,
                    request.set5_winner_side,
                ),
                (
                    6,
                    request.set6_team_a,
                    request.set6_team_b,
                    request.set6_winner_side,
                ),
                (
                    7,
                    request.set7_team_a,
                    request.set7_team_b,
                    request.set7_winner_side,
                ),
            ]


            is_playoff = (
                series["series_type"]
                == "플레이오프"
            )


            if is_playoff:

                if (
                    series["best_of"] is None
                    or
                    series["wins_required"] is None
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "플레이오프 진행 정보가 "
                            "올바르지 않습니다."
                        ),
                    )


                max_sets = int(
                    series["best_of"]
                )

                wins_required = int(
                    series["wins_required"]
                )

            else:

                max_sets = (
                    get_series_target_set_count(
                        series
                    )
                )

                wins_required = None


            # =========================
            # 허용 세트 초과 방어
            # =========================

            for (
                set_number,
                team_a_score,
                team_b_score,
                explicit_winner_side,
            ) in requested_sets[max_sets:]:

                if (
                    team_a_score is not None
                    or team_b_score is not None
                    or explicit_winner_side is not None
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{max_sets}세트를 초과하여 "
                            "결과를 입력할 수 없습니다."
                        ),
                    )


            # =========================
            # 실제 저장할 세트 검증
            # =========================

            manual_sets = []

            gap_found = False

            team_a_wins = 0
            team_b_wins = 0

            series_winner_side = None
            winning_set_number = None


            for (
                set_number,
                team_a_score,
                team_b_score,
                explicit_winner_side,
            ) in requested_sets[:max_sets]:

                # 둘 다 비어 있으면
                # 여기서 실제 경기 종료
                if (
                    team_a_score is None
                    and team_b_score is None
                ):

                    if explicit_winner_side is not None:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 점수 없이 "
                                "승자만 지정할 수 없습니다."
                            ),
                        )

                    gap_found = True
                    continue


                # 한쪽만 입력됨
                if (
                    team_a_score is None
                    or team_b_score is None
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{set_number}세트의 "
                            "양쪽 점수를 모두 입력해주세요."
                        ),
                    )


                # 중간 빈 세트 이후 입력
                if gap_found:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "중간 세트를 비워둔 채 "
                            "다음 세트를 입력할 수 없습니다."
                        ),
                    )


                if (
                    team_a_score < 0
                    or team_b_score < 0
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "점수는 0 이상의 "
                            "정수여야 합니다."
                        ),
                    )


                # =========================
                # 세트 승자
                # =========================

                if team_a_score > team_b_score:

                    winner_side = "team_a"

                    if (
                        explicit_winner_side
                        is not None
                        and
                        explicit_winner_side
                        != winner_side
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 승자와 "
                                "입력 점수가 일치하지 않습니다."
                            ),
                        )


                elif team_b_score > team_a_score:

                    winner_side = "team_b"

                    if (
                        explicit_winner_side
                        is not None
                        and
                        explicit_winner_side
                        != winner_side
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"{set_number}세트 승자와 "
                                "입력 점수가 일치하지 않습니다."
                            ),
                        )


                else:

                    # 일반 경기에서는 무승부 허용
                    if not is_playoff:
                        winner_side = "draw"

                    # 플레이오프는
                    # 승부차기 등 실제 승자 필요
                    else:

                        if explicit_winner_side not in (
                            "team_a",
                            "team_b",
                        ):
                            raise HTTPException(
                                status_code=400,
                                detail=(
                                    f"{set_number}세트가 동점입니다. "
                                    "플레이오프에서는 실제 승자를 "
                                    "지정해야 합니다."
                                ),
                            )

                        winner_side = (
                            explicit_winner_side
                        )


                # =========================
                # 선승 이후 추가 세트 방어
                # =========================

                if (
                    is_playoff
                    and
                    series_winner_side is not None
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "선승 도달 이후의 "
                            "추가 세트가 입력되었습니다."
                        ),
                    )


                manual_sets.append(
                    (
                        set_number,
                        team_a_score,
                        team_b_score,
                        winner_side,
                    )
                )


                # =========================
                # 플레이오프 승수 계산
                # =========================

                if is_playoff:

                    if winner_side == "team_a":
                        team_a_wins += 1

                    elif winner_side == "team_b":
                        team_b_wins += 1


                    if (
                        team_a_wins
                        >= wins_required
                    ):
                        series_winner_side = (
                            "team_a"
                        )

                        winning_set_number = (
                            set_number
                        )


                    elif (
                        team_b_wins
                        >= wins_required
                    ):
                        series_winner_side = (
                            "team_b"
                        )

                        winning_set_number = (
                            set_number
                        )


            # =========================
            # 일반 SERIES
            # 예약된 세트 수만큼 입력
            # =========================

            if not is_playoff:

                if (
                    len(manual_sets)
                    != max_sets
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{series['series_type']}는 "
                            f"{max_sets}세트를 모두 "
                            "입력해야 합니다."
                        ),
                    )


            # =========================
            # 플레이오프는 선승 필수
            # =========================

            else:

                if series_winner_side is None:
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{wins_required}승에 도달한 "
                            "참가자가 없습니다."
                        ),
                    )


            # =========================
            # 검증 완료 후 기존 기록 제거
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
            # 세트 저장
            # =========================

            for (
                set_number,
                team_a_score,
                team_b_score,
                winner_side,
            ) in manual_sets:

                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,
                        set_number,
                        nexon_match_id,
                        played_at,
                        team_a_score,
                        team_b_score,
                        score_source,
                        winner_side
                    )

                    VALUES (
                        %s,
                        %s,
                        NULL,
                        %s,
                        %s,
                        %s,
                        'manual',
                        %s
                    )
                    """,
                    (
                        series_id,
                        set_number,
                        finished_at,
                        team_a_score,
                        team_b_score,
                        winner_side,
                    ),
                )


            # =========================
            # SERIES 완료 + Snapshot
            # =========================

            cursor.execute(
                """
                UPDATE series

                SET
                    status = 'completed',
                    completed_at = %s,
                    finished_at = %s,
                    stats_sync_status = 'pending',

                    team_a_snapshot_name =
                        COALESCE(
                            team_a_snapshot_name,
                            %s
                        ),

                    team_a_snapshot_logo_path =
                        COALESCE(
                            team_a_snapshot_logo_path,
                            %s
                        ),

                    team_b_snapshot_name =
                        COALESCE(
                            team_b_snapshot_name,
                            %s
                        ),

                    team_b_snapshot_logo_path =
                        COALESCE(
                            team_b_snapshot_logo_path,
                            %s
                        )

                WHERE id = %s
                """,
                (
                    finished_at,
                    finished_at,

                    series[
                        "team_a_current_team_name"
                    ],
                    series[
                        "team_a_current_team_logo_path"
                    ],

                    series[
                        "team_b_current_team_name"
                    ],
                    series[
                        "team_b_current_team_logo_path"
                    ],

                    series_id,
                ),
            )


        connection.commit()

    # =========================
    # 정규리그 종료 후
    # 준플레이오프 자동 생성
    # =========================

    if (
        series["series_type"]
        == "정규리그"
    ):
        create_initial_playoff_if_ready()

    if (
        series["series_type"]
        == "플레이오프"
    ):
        create_next_playoff_if_ready(
            series_id
        )


    team_a_total_score = sum(
        manual_set[1]
        for manual_set in manual_sets
    )

    team_b_total_score = sum(
        manual_set[2]
        for manual_set in manual_sets
    )


    return {
        "series_id":
            series_id,

        "status":
            "completed",

        "stats_sync_status":
            "pending",

        "series_type":
            series["series_type"],

        "playoff_stage":
            series["playoff_stage"],

        "best_of":
            series["best_of"],

        "wins_required":
            series["wins_required"],

        "team_a":
            series["team_a"],

        "team_b":
            series["team_b"],

        "team_a_score":
            team_a_total_score,

        "team_b_score":
            team_b_total_score,

        "team_a_wins":
            (
                team_a_wins
                if is_playoff
                else None
            ),

        "team_b_wins":
            (
                team_b_wins
                if is_playoff
                else None
            ),

        "winner_side":
            series_winner_side,

        "winning_set":
            winning_set_number,

        "finished_at":
            finished_at.isoformat(),

        "sets": [
            {
                "set":
                    set_number,

                "team_a_score":
                    team_a_score,

                "team_b_score":
                    team_b_score,

                "winner_side":
                    winner_side,
            }

            for (
                set_number,
                team_a_score,
                team_b_score,
                winner_side,
            ) in manual_sets
        ],
    }

# =========================
# FCL SERIES STATUS
# =========================

# =========================
# FCL SERIES STATUS
# DB 조회 전용
# NEXON API 호출 없음
# =========================

@app.get(
    "/api/fconline/series/{series_id}/status"
)
def get_fcl_series_status(
    series_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.match_type,
                    s.scheduled_date,
                    s.target_set_count,
                    
                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,

                    s.started_at,
                    s.completed_at,
                    s.finished_at,
                    s.stats_sync_status,
                    s.status,

                    team_a.fcl_name
                        AS team_a_name,

                    team_a.fc_nickname
                        AS nickname_a,

                    team_b.fcl_name
                        AS team_b_name,

                    team_b.fc_nickname
                        AS nickname_b

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
            # 저장된 SET
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    nexon_match_id,
                    played_at,
                    team_a_score,
                    team_b_score,
                    score_source
                    winner_side

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    series_id,
                ),
            )

            saved_sets = cursor.fetchall()

            # =========================
            # 저장된 MVP
            # =========================

            cursor.execute(
                """
                SELECT
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
                    (
                        saved_set[
                            "played_at"
                        ].isoformat()

                        if saved_set[
                            "played_at"
                        ]

                        else None
                    ),

                "team_a_score":
                    saved_set[
                        "team_a_score"
                    ],

                "team_b_score":
                    saved_set[
                        "team_b_score"
                    ],

                "score_source":
                    saved_set[
                        "score_source"
                    ],

                "winner_side":
                    saved_set[
                        "winner_side"
                    ],
            }
        )

    if mvp:

        mvp["rating_total"] = float(
            mvp["rating_total"]
        )

        mvp["average_rating"] = float(
            mvp["average_rating"]
        )

    return {
        "series": {
            "series_id":
                series_id,

            "series_type":
                series["series_type"],

            "playoff_stage":
                series[
                    "playoff_stage"
                ],

            "best_of":
                series[
                    "best_of"
                ],

            "wins_required":
                series[
                    "wins_required"
                ],

            "target_set_count":
                get_series_target_set_count(
                    series
                ),

            "team_a":
                series["team_a_name"],

            "team_b":
                series["team_b_name"],

            "nickname_a":
                series["nickname_a"],

            "nickname_b":
                series["nickname_b"],

            "match_type":
                series["match_type"],

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

                "finished_at":
                    (
                        series[
                            "finished_at"
                        ].isoformat()

                        if series[
                            "finished_at"
                        ]

                        else None
                    ),

                "stats_sync_status":
                    series[
                        "stats_sync_status"
                    ],

                "status":
                    series[
                        "status"
                    ],

                "set_count":
                    len(sets),
        },

        "sets": sets,

        "mvp": mvp,
    }


# =========================
# FCL SERIES STATUS
# NEXON 탐색 + DB 저장
# =========================
@app.post(
    "/api/fconline/series/{series_id}/sync"
)
def sync_fcl_series_status(
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
                    s.include_extra_time_result,
                    s.scheduled_date,
                    s.target_set_count,

                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,

                    s.started_at,
                    s.completed_at,
                    s.finished_at,
                    s.stats_sync_status,
                    s.status,

                    team_a.id
                        AS team_a_id,

                    team_a.fcl_name
                        AS team_a_name,

                    team_a.current_team_name
                        AS team_a_current_team_name,

                    team_a.current_team_logo_path
                        AS team_a_current_team_logo_path,

                    team_a.fc_nickname
                        AS nickname_a,

                    team_a.ouid
                        AS ouid_a,

                    team_b.id
                        AS team_b_id,

                    team_b.fcl_name
                        AS team_b_name,

                    team_b.current_team_name
                        AS team_b_current_team_name,

                    team_b.current_team_logo_path
                        AS team_b_current_team_logo_path,

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


    # =========================
    # 현재 SERIES가
    # 사후 동기화 대상인지 확인
    # =========================

    is_pending_result_sync = (
        series["status"] == "completed"
        and
        series["stats_sync_status"]
        in (
            "pending",
            "conflict",
        )
    )

    status = series["status"]

    required_set_count = (
        get_series_target_set_count(
            series
        )
    )


    # active 또는
    # completed + pending/conflict만
    # NEXON 동기화 가능
    if (
        series["status"] != "active"
        and
        not is_pending_result_sync
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "NEXON 기록을 동기화할 수 없는 "
                "SERIES입니다."
            ),
        )


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
        limit=10,
    )


    # 개발/서비스 키 모두
    # 순간 호출 몰림 방지
    time.sleep(0.3)


    matches_b = get_user_match_ids(
        ouid_b,
        series["match_type"],
        limit=10,
    )


    matches_b_set = set(
        matches_b
    )


    common_match_ids = [
        match_id

        for match_id
        in matches_a

        if match_id
        in matches_b_set
    ]


    # =========================
    # SERIES 시간 범위
    # =========================

    started_at = parse_kst_datetime(
        series["started_at"]
    )


    finished_at = None


    if series["finished_at"]:

        finished_at = parse_kst_datetime(
            series["finished_at"]
        )


    detected_matches = []
    debug_matches = []


    # =========================
    # 실제 맞대결 탐색
    # =========================

    for match_id in common_match_ids:

        time.sleep(0.3)

        match_data = get_match_detail(
            match_id
        )


        match_date = parse_nexon_datetime(
            match_data["matchDate"]
        )


        match_nicknames = {
            match_info["nickname"]
            for match_info
            in match_data["matchInfo"]
        }


        reject_reason = None


        # =====================================
        # 시간 범위 확인
        #
        # ACTIVE 상태:
        # START 이후 경기만 인정
        #
        # 수동 결과 입력 후 사후 동기화:
        # 실제 경기를 먼저 진행하고
        # 사이트 START를 나중에 누른 경우도
        # 있으므로 scheduled_date 당일의
        # 경기까지 허용
        # =====================================

        if is_pending_result_sync:

            if (
                match_date.date()
                !=
                series[
                    "scheduled_date"
                ]
            ):

                reject_reason = (
                    "scheduled_date_mismatch"
                )


            elif (
                finished_at is not None
                and
                match_date
                >
                finished_at
            ):

                reject_reason = (
                    "after_finished_at"
                )


        else:

            if (
                match_date
                <
                started_at
            ):

                reject_reason = (
                    "before_started_at"
                )


            elif (
                finished_at is not None
                and
                match_date
                >
                finished_at
            ):

                reject_reason = (
                    "after_finished_at"
                )


        if (
            reject_reason is None
            and
            match_data["matchType"]
            !=
            series["match_type"]
        ):

            reject_reason = (
                "match_type_mismatch"
            )


        elif (
            reject_reason is None
            and
            match_nicknames
            !=
            {
                nickname_a,
                nickname_b,
            }
        ):

            reject_reason = (
                "nickname_mismatch"
            )

            reject_reason = (
                "match_type_mismatch"
            )


        debug_matches.append(
            {
                "match_id":
                    match_id,

                "match_date":
                    match_date.isoformat(),

                "match_type":
                    match_data[
                        "matchType"
                    ],

                "nicknames":
                    sorted(
                        match_nicknames
                    ),

                "reject_reason":
                    reject_reason,
            }
        )


        if reject_reason is not None:
            continue


        detected_matches.append(
            {
                "data":
                    match_data,

                "played_at":
                    match_date,
            }
        )

    # =========================
    # 시간순 정렬
    # =========================

    detected_matches.sort(
        key=lambda match:
            match["played_at"]
    )


    # =========================
    # SERIES 종류별 경기 제한
    # =========================

    if (
        series["series_type"]
        == "플레이오프"
    ):

        best_of = int(
            series["best_of"]
        )

        wins_required = int(
            series["wins_required"]
        )


        playoff_matches = []

        detected_team_a_wins = 0
        detected_team_b_wins = 0


        for detected_match in (
            detected_matches[:best_of]
        ):

            winner_side = (
                get_match_winner_side(
                    detected_match["data"],
                    nickname_a,
                    nickname_b,
                    series["series_type"],
                )
            )


            if winner_side is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 경기의 "
                        "승패 결과를 확인할 수 없습니다."
                    ),
                )


            if winner_side == "draw":

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "플레이오프 경기에서 "
                        "무승부 결과가 감지되었습니다."
                    ),
                )


            detected_match[
                "winner_side"
            ] = winner_side

            detected_match[
                "result_method"
            ],

            detected_match[
                "result_method"
            ] = (
                get_match_result_method(
                    detected_match["data"],
                    nickname_a,
                    nickname_b,
                    series["series_type"],
                    True,
                )
            )


            playoff_matches.append(
                detected_match
            )


            if winner_side == "team_a":

                detected_team_a_wins += 1

            elif winner_side == "team_b":

                detected_team_b_wins += 1


            # 선승 도달 즉시 SERIES 종료 지점
            if (
                detected_team_a_wins
                >= wins_required

                or

                detected_team_b_wins
                >= wins_required
            ):
                break


        detected_matches = playoff_matches


    else:

        # =========================
        # 프리시즌 / 정규리그
        #
        # SERIES에 저장된
        # 목표 세트 수만 감지
        # =========================

        if not is_pending_result_sync:

            detected_matches = (
                detected_matches[
                    :required_set_count
                ]
            )

        # =========================
        # NEXON 경기 데이터 정합성 검증
        # =========================

        integrity_conflict = None

        for (
            set_index,
            detected_match,
        ) in enumerate(
            detected_matches,
            start=1,
        ):
            conflict_reason = (
                get_match_integrity_conflict(
                    detected_match["data"],
                    nickname_a,
                    nickname_b,
                    series["series_type"],
                )
            )

            if conflict_reason:
                integrity_conflict = (
                    f"{set_index}세트: "
                    f"{conflict_reason}"
                )
                break

        if integrity_conflict:
            if is_pending_result_sync:
                with get_db_connection() as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE series
                            SET
                                stats_sync_status =
                                    'conflict'
                            WHERE id = %s
                            """,
                            (
                                series_id,
                            ),
                        )

                    connection.commit()

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

                    "status":
                        series["status"],

                    "set_count":
                        0,

                    "stats_sync_status":
                        (
                            "conflict"
                            if is_pending_result_sync
                            else
                            series[
                                "stats_sync_status"
                            ]
                        ),
                },

                "sets": [],

                "mvp": None,

                "sync_message": (
                    "NEXON 경기 데이터 정합성 "
                    "검증에 실패했습니다. "
                    f"{integrity_conflict}"
                ),
            }


        for detected_match in detected_matches:

            detected_match[
                "winner_side"
            ] = (
                get_match_winner_side(
                    detected_match["data"],
                    nickname_a,
                    nickname_b,
                    series["series_type"],
                    bool(
                        series[
                            "include_extra_time_result"
                        ]
                    ),
                )
            )


            detected_match[
                "result_method"
            ] = (
                get_match_result_method(
                    detected_match["data"],
                    nickname_a,
                    nickname_b,
                    series["series_type"],
                    bool(
                        series[
                            "include_extra_time_result"
                        ]
                    ),
                )
            )

    # =========================
    # NEXON 경기 데이터 정합성 검증
    # =========================

    integrity_conflict = None

    for (
        set_index,
        detected_match,
    ) in enumerate(
        detected_matches,
        start=1,
    ):
        conflict_reason = (
            get_match_integrity_conflict(
                detected_match["data"],
                nickname_a,
                nickname_b,
                series["series_type"],
            )
        )

        if conflict_reason:
            integrity_conflict = (
                f"{set_index}세트: "
                f"{conflict_reason}"
            )
            break

    if integrity_conflict:
        if is_pending_result_sync:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE series
                        SET
                            stats_sync_status =
                                'conflict'
                        WHERE id = %s
                        """,
                        (
                            series_id,
                        ),
                    )

                connection.commit()

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

                "status":
                    series["status"],

                "set_count":
                    0,

                "stats_sync_status":
                    (
                        "conflict"
                        if is_pending_result_sync
                        else
                        series[
                            "stats_sync_status"
                        ]
                    ),
            },

            "sets": [],

            "mvp": None,

            "sync_message": (
                "NEXON 경기 데이터 정합성 "
                "검증에 실패했습니다. "
                f"{integrity_conflict}"
            ),
        }

    # ==================================================
    # A.
    # 수동 결과 입력 완료 후
    # NEXON 기록 사후 연결
    # ==================================================

    if is_pending_result_sync:

        # =========================
        # 기존 수동 결과 조회
        # =========================

        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        set_number,
                        nexon_match_id,
                        played_at,
                        team_a_score,
                        team_b_score,
                        score_source

                    FROM series_sets

                    WHERE series_id = %s

                    ORDER BY set_number
                    """,
                    (
                        series_id,
                    ),
                )

                manual_sets = (
                    cursor.fetchall()
                )


        # =========================
        # 실제 NEXON 동기화에
        # 필요한 경기 수
        # =========================

        if (
            series["series_type"]
            == "플레이오프"
        ):

            required_sync_set_count = (
                len(
                    manual_sets
                )
            )

        else:

            required_sync_set_count = (
                required_set_count
            )


            if (
                len(manual_sets)
                != required_sync_set_count
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "수동 입력된 "
                        f"{required_sync_set_count}세트 "
                        "결과가 완전하지 않습니다."
                    ),
                )

        # =========================
        # 사후 동기화 후보 중
        # 수동 입력 점수와 정확히 일치하는
        # 연속 SERIES 찾기
        #
        # 같은 날 같은 참가자끼리
        # 다른 경기를 추가로 했더라도
        # 잘못 연결되는 것을 방지
        # =========================

        if (
            len(detected_matches)
            >=
            required_sync_set_count
        ):

            manual_score_pairs = [
                (
                    int(
                        manual_set[
                            "team_a_score"
                        ]
                    ),
                    int(
                        manual_set[
                            "team_b_score"
                        ]
                    ),
                )

                for manual_set
                in manual_sets
            ]


            matching_windows = []


            max_start_index = (
                len(
                    detected_matches
                )
                -
                required_sync_set_count
                +
                1
            )


            for start_index in range(
                max_start_index
            ):

                candidate_matches = (
                    detected_matches[
                        start_index:
                        start_index
                        +
                        required_sync_set_count
                    ]
                )


                candidate_score_pairs = []

                candidate_valid = True


                for candidate_match in (
                    candidate_matches
                ):

                    score_pair = (
                        get_match_score_pair(
                            candidate_match[
                                "data"
                            ],
                            nickname_a,
                            nickname_b,
                            include_extra_time_result=
                                (
                                    series[
                                        "series_type"
                                    ]
                                    ==
                                    "플레이오프"

                                    or

                                    bool(
                                        series[
                                            "include_extra_time_result"
                                        ]
                                    )
                                ),
                        )
                    )


                    if score_pair is None:

                        candidate_valid = (
                            False
                        )

                        break


                    candidate_score_pairs.append(
                        (
                            int(
                                score_pair[0]
                            ),
                            int(
                                score_pair[1]
                            ),
                        )
                    )


                if (
                    candidate_valid
                    and
                    candidate_score_pairs
                    ==
                    manual_score_pairs
                ):

                    matching_windows.append(
                        candidate_matches
                    )


            # 같은 점수 조합이 여러 번 있다면
            # 완료 시각에 가장 가까운
            # 마지막 SERIES를 선택
            if matching_windows:

                detected_matches = (
                    matching_windows[-1]
                )


            # 정확한 점수 조합은 없지만
            # 후보가 충분하다면
            # 가장 최근 경기들로 비교
            # 이후 기존 conflict 검사가
            # 점수 불일치를 잡아줌
            elif (
                len(detected_matches)
                >
                required_sync_set_count
            ):

                detected_matches = (
                    detected_matches[
                        -
                        required_sync_set_count:
                    ]
                )


        # =========================
        # Nexon 데이터가 아직
        # 필요한 경기 수만큼 올라오지 않음
        # =========================

        if (
            len(detected_matches)
            <
            required_sync_set_count
        ):

            return {
                "series": {
                    "series_id":
                        series_id,

                    "series_type":
                        series[
                            "series_type"
                        ],

                    "team_a":
                        series[
                            "team_a_name"
                        ],

                    "team_b":
                        series[
                            "team_b_name"
                        ],

                    "nickname_a":
                        nickname_a,

                    "nickname_b":
                        nickname_b,

                    "match_type":
                        series[
                            "match_type"
                        ],

                    "started_at":
                        started_at.isoformat(),

                    "status":
                        "completed",

                    "set_count":
                        required_sync_set_count,

                    "stats_sync_status":
                        "pending",
                },

                "sets": [
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
                            (
                                saved_set[
                                    "played_at"
                                ].isoformat()

                                if saved_set[
                                    "played_at"
                                ]

                                else None
                            ),

                        "team_a_score":
                            saved_set[
                                "team_a_score"
                            ],

                        "team_b_score":
                            saved_set[
                                "team_b_score"
                            ],
                    }

                    for saved_set
                    in manual_sets
                ],

                "detected_set_count":
                    len(detected_matches),

                "common_match_count":
                    len(common_match_ids),

                "debug": {
                    "started_at":
                        started_at.isoformat(),

                    "finished_at":
                        (
                            finished_at.isoformat()
                            if finished_at
                            else None
                        ),

                    "matches":
                        debug_matches,
                },

                "mvp":
                    None,

                "sync_message":
                    (
                        "NEXON 경기 기록 "
                        f"{len(detected_matches)}/"
                        f"{required_sync_set_count}경기 감지. "
                        "아직 필요한 경기 기록이 모두 "
                        "반영되지 않았습니다."
                    ),
            }


        # =========================
        # Nexon 점수 추출
        # =========================

        nexon_scores = []


        for detected_match in (
            detected_matches
        ):

            match_data = (
                detected_match[
                    "data"
                ]
            )


            participant_map = {
                match_info["nickname"]:
                    match_info

                for match_info
                in match_data[
                    "matchInfo"
                ]
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


            score_pair = (
                get_match_score_pair(
                    match_data,
                    nickname_a,
                    nickname_b,
                    include_extra_time_result=
                        (
                            series[
                                "series_type"
                            ]
                            == "플레이오프"
                            or
                            bool(
                                series[
                                    "include_extra_time_result"
                                ]
                            )
                        ),
                )
            )


            if score_pair is None:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "NEXON 경기 점수를 "
                        "확인할 수 없습니다."
                    ),
                )


            (
                team_a_score,
                team_b_score,
            ) = score_pair


            nexon_scores.append(
                (
                    team_a_score,
                    team_b_score,
                )
            )


        # =========================
        # 수동 점수와
        # Nexon 점수 비교
        # =========================

        has_score_conflict = any(
            (
                manual_set[
                    "team_a_score"
                ]
                !=
                nexon_score[0]
            )
            or
            (
                manual_set[
                    "team_b_score"
                ]
                !=
                nexon_score[1]
            )

            for (
                manual_set,
                nexon_score,
            )
            in zip(
                manual_sets,
                nexon_scores,
            )
        )


        # =========================
        # 점수 불일치
        # =========================

        if has_score_conflict:

            with get_db_connection() as connection:

                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        UPDATE series

                        SET
                            stats_sync_status =
                                'conflict'

                        WHERE id = %s
                        """,
                        (
                            series_id,
                        ),
                    )

                connection.commit()


            return {
                "series": {
                    "series_id":
                        series_id,

                    "series_type":
                        series[
                            "series_type"
                        ],

                    "team_a":
                        series[
                            "team_a_name"
                        ],

                    "team_b":
                        series[
                            "team_b_name"
                        ],

                    "status":
                        "completed",

                    "set_count":
                        required_sync_set_count,

                    "stats_sync_status":
                        "conflict",
                },

                "sets": [
                    {
                        "set":
                            saved_set[
                                "set_number"
                            ],

                        "team_a_score":
                            saved_set[
                                "team_a_score"
                            ],

                        "team_b_score":
                            saved_set[
                                "team_b_score"
                            ],
                    }

                    for saved_set
                    in manual_sets
                ],

                "detected_sets": [
                    {
                        "set":
                            index,

                        "team_a_score":
                            score[0],

                        "team_b_score":
                            score[1],
                    }

                    for (
                        index,
                        score,
                    )
                    in enumerate(
                        nexon_scores,
                        start=1,
                    )
                ],

                "mvp":
                    None,

                "sync_message":
                    (
                        "수동 입력 점수와 "
                        "NEXON 기록이 "
                        "일치하지 않습니다."
                    ),
            }


        # =========================
        # 점수 일치
        # 실제 matchId 연결
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

                    cursor.execute(
                        """
                        UPDATE series_sets

                        SET
                            nexon_match_id = %s,

                            played_at = %s,

                            score_source =
                                'nexon',

                            winner_side = %s,

                            result_method = %s

                        WHERE
                            series_id = %s

                            AND
                            set_number = %s
                        """,
                        (
                            detected_match[
                                "data"
                            ][
                                "matchId"
                            ],

                            detected_match[
                                "played_at"
                            ],

                            detected_match[
                                "winner_side"
                            ],

                            detected_match[
                                "result_method"
                            ],

                            series_id,
                            index,
                        ),
                    )


                # 혹시 이전 통계가 있었다면
                # 깨끗하게 다시 계산
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
                    DELETE FROM
                        series_player_stats

                    WHERE series_id = %s
                    """,
                    (
                        series_id,
                    ),
                )


            connection.commit()

        # =========================
        # 세트별 스쿼드 Snapshot 저장
        # =========================

        save_series_set_squad_players(
            series_id,

            series[
                "team_a_id"
            ],
            nickname_a,

            series[
                "team_b_id"
            ],
            nickname_b,

            detected_matches,
        )


        # =========================
        # 이미 받은 match detail로
        # MVP / 선수 기록 계산
        #
        # 추가 Nexon 호출 없음
        # =========================

        mvp_matches = [
            detected_match[
                "data"
            ]

            for detected_match
            in detected_matches
        ]


        (
            mvp,
            _,
            player_stats,
        ) = calculate_series_mvp_from_matches(
            mvp_matches
        )


        save_series_player_stats(
            series_id,

            series[
                "team_a_id"
            ],
            nickname_a,

            series[
                "team_b_id"
            ],
            nickname_b,

            player_stats,
        )


        if mvp:

            if (
                mvp["nickname"]
                == nickname_a
            ):

                mvp_participant_id = (
                    series[
                        "team_a_id"
                    ]
                )


            elif (
                mvp["nickname"]
                == nickname_b
            ):

                mvp_participant_id = (
                    series[
                        "team_b_id"
                    ]
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
        # 사후 동기화 완료
        # =========================

        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE series

                    SET
                        stats_sync_status =
                            'synced'

                    WHERE id = %s
                    """,
                    (
                        series_id,
                    ),
                )

                settlement_result = (
                    settle_predictions_for_series(
                        cursor,
                        series_id,
                    )
                )

            connection.commit()


        sets = []


        for (
            index,
            detected_match,
        ) in enumerate(
            detected_matches,
            start=1,
        ):

            manual_set = (
                manual_sets[
                    index - 1
                ]
            )


            sets.append(
                {
                    "set":
                        index,

                    "match_id":
                        detected_match[
                            "data"
                        ][
                            "matchId"
                        ],

                    "match_date":
                        detected_match[
                            "played_at"
                        ].isoformat(),

                    "team_a_score":
                        manual_set[
                            "team_a_score"
                        ],

                    "team_b_score":
                        manual_set[
                            "team_b_score"
                        ],
                }
            )

    # =========================
    # 정규리그 종료 후
    # 준플레이오프 자동 생성
    # =========================

        if (
            series["series_type"]
            == "정규리그"
            and
            status == "completed"
        ):
            create_initial_playoff_if_ready()


        if (
            series["series_type"]
            == "플레이오프"
            and
            status == "completed"
        ):
            create_next_playoff_if_ready(
                series_id
            )


        return {
            "series": {
                "series_id":
                    series_id,

                "series_type":
                    series[
                        "series_type"
                    ],

                "team_a":
                    series[
                        "team_a_name"
                    ],

                "team_b":
                    series[
                        "team_b_name"
                    ],

                "nickname_a":
                    nickname_a,

                "nickname_b":
                    nickname_b,

                "match_type":
                    series[
                        "match_type"
                    ],

                "started_at":
                    started_at.isoformat(),

                "status":
                    "completed",

                "set_count":
                    3,

                "stats_sync_status":
                    "synced",
            },

            "sets":
                sets,

            "mvp":
                mvp,

            "sync_message":
                (
                    "NEXON 기록 동기화가 "
                    "완료되었습니다."
                ),
        }

    # =========================
    # 완료 Snapshot 기준 정보 확인
    #
    # 이미 completed 상태에서 하는
    # 사후 sync에는 적용하지 않음
    # =========================

    if (
        not series[
            "team_a_current_team_name"
        ]
        or
        not series[
            "team_a_current_team_logo_path"
        ]
        or
        not series[
            "team_b_current_team_name"
        ]
        or
        not series[
            "team_b_current_team_logo_path"
        ]
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "현재 팀 또는 로고 정보가 "
                "등록되지 않았습니다."
            ),
        )




    # ==================================================
    # B.
    # 아직 active 상태에서
    # 직접 NEXON 기록 확인
    # ==================================================

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
                    detected_match[
                        "data"
                    ]
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
                    in match_data[
                        "matchInfo"
                    ]
                }


                score_pair = (
                    get_match_score_pair(
                        match_data,
                        nickname_a,
                        nickname_b,
                        include_extra_time_result=
                            (
                                series[
                                    "series_type"
                                ]
                                == "플레이오프"
                                or
                                bool(
                                    series[
                                        "include_extra_time_result"
                                    ]
                                )
                            ),
                    )
                )


                if score_pair is None:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"{index}세트의 "
                            "NEXON 점수를 "
                            "확인할 수 없습니다."
                        ),
                    )


                (
                    team_a_score,
                    team_b_score,
                ) = score_pair


                cursor.execute(
                    """
                    INSERT INTO series_sets (
                        series_id,
                        set_number,
                        nexon_match_id,
                        played_at,
                        team_a_score,
                        team_b_score,
                        score_source,
                        winner_side,
                        result_method
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        'nexon',
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
                            EXCLUDED.team_b_score,

                        score_source =
                            'nexon',

                        winner_side =
                            EXCLUDED.winner_side,

                        result_method =
                            EXCLUDED.result_method
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

                        detected_match[
                            "winner_side"
                        ],

                        detected_match[
                            "result_method"
                        ],
                    ),
                )


            # =========================
            # 저장된 세트 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    nexon_match_id,
                    played_at,
                    team_a_score,
                    team_b_score,
                    score_source,
                    winner_side

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
            # SERIES 완료 여부
            # =========================

            team_a_wins = 0
            team_b_wins = 0


            if (
                series["series_type"]
                == "플레이오프"
            ):

                for saved_set in saved_sets:

                    if (
                        saved_set[
                            "winner_side"
                        ]
                        == "team_a"
                    ):

                        team_a_wins += 1


                    elif (
                        saved_set[
                            "winner_side"
                        ]
                        == "team_b"
                    ):

                        team_b_wins += 1


                series_completed = (
                    team_a_wins
                    >= int(
                        series[
                            "wins_required"
                        ]
                    )

                    or

                    team_b_wins
                    >= int(
                        series[
                            "wins_required"
                        ]
                    )
                )


            else:

                # =========================
                # 프리시즌 / 정규리그
                #
                # 목표 세트 수 도달 시 완료
                # =========================

                series_completed = (
                    set_count
                    >= required_set_count
                )


            # =========================
            # SERIES 종료
            # =========================

            if series_completed:

                completed_at = (
                    saved_sets[-1][
                        "played_at"
                    ]
                )


                cursor.execute(
            """
            UPDATE series

            SET
                status =
                    'completed',

                completed_at = %s,

                finished_at =
                    COALESCE(
                        finished_at,
                        %s
                    ),

                stats_sync_status =
                    'pending',

                team_a_snapshot_name =
                    COALESCE(
                        team_a_snapshot_name,
                        %s
                    ),

                team_a_snapshot_logo_path =
                    COALESCE(
                        team_a_snapshot_logo_path,
                        %s
                    ),

                team_b_snapshot_name =
                    COALESCE(
                        team_b_snapshot_name,
                        %s
                    ),

                team_b_snapshot_logo_path =
                    COALESCE(
                        team_b_snapshot_logo_path,
                        %s
                    )

            WHERE id = %s
            """,
            (
                completed_at,
                completed_at,

                series[
                    "team_a_current_team_name"
                ],

                series[
                    "team_a_current_team_logo_path"
                ],

                series[
                    "team_b_current_team_name"
                ],

                series[
                    "team_b_current_team_logo_path"
                ],

                series_id,
            ),
        )


                status = "completed"


            else:

                status = "active"


        connection.commit()


    # =========================
    # 세트별 스쿼드 Snapshot 저장
    # =========================

    save_series_set_squad_players(
        series_id,

        series[
            "team_a_id"
        ],
        nickname_a,

        series[
            "team_b_id"
        ],
        nickname_b,

        detected_matches,
    )




    # =========================
    # MVP
    # =========================

    mvp = None


    final_stats_sync_status = (
        series[
            "stats_sync_status"
        ]
    )


    if (
        status == "completed"
        and
        len(saved_sets) > 0
        and
        len(detected_matches)
            >= len(saved_sets)
    ):

        mvp_matches = [
            detected_match[
                "data"
            ]

            for detected_match
            in detected_matches[
                :len(saved_sets)
            ]
        ]


        (
            mvp,
            _,
            player_stats,
        ) = calculate_series_mvp_from_matches(
            mvp_matches
        )


        save_series_player_stats(
            series_id,

            series[
                "team_a_id"
            ],
            nickname_a,

            series[
                "team_b_id"
            ],
            nickname_b,

            player_stats,
        )


        if mvp:

            if (
                mvp["nickname"]
                == nickname_a
            ):

                mvp_participant_id = (
                    series[
                        "team_a_id"
                    ]
                )


            elif (
                mvp["nickname"]
                == nickname_b
            ):

                mvp_participant_id = (
                    series[
                        "team_b_id"
                    ]
                )


            else:

                mvp_participant_id = None


            if mvp_participant_id:

                save_series_mvp(
                    series_id,
                    mvp_participant_id,
                    mvp,
                )


        with get_db_connection() as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    UPDATE series

                    SET
                        stats_sync_status =
                            'synced'

                    WHERE id = %s
                    """,
                    (
                        series_id,
                    ),
                )

                settlement_result = (
                    settle_predictions_for_series(
                        cursor,
                        series_id,
                    )
                )

            connection.commit()


        final_stats_sync_status = (
            "synced"
        )


    # =========================
    # 응답용 세트
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
                    (
                        saved_set[
                            "played_at"
                        ].isoformat()

                        if saved_set[
                            "played_at"
                        ]

                        else None
                    ),

                "team_a_score":
                    saved_set[
                        "team_a_score"
                    ],

                "team_b_score":
                    saved_set[
                        "team_b_score"
                    ],

                "winner_side":
                    saved_set[
                        "winner_side"
                    ],
            }
        )
    if (
        series["series_type"]
        == "정규리그"
        and
        status == "completed"
    ):
        create_initial_playoff_if_ready()

    if (
        series["series_type"]
        == "플레이오프"
        and
        status == "completed"
    ):
        create_next_playoff_if_ready(
            series_id
        )

    return {
        "series": {
            "series_id":
                series_id,

            "series_type":
                series[
                    "series_type"
                ],

            "team_a":
                series[
                    "team_a_name"
                ],

            "team_b":
                series[
                    "team_b_name"
                ],

            "nickname_a":
                nickname_a,

            "nickname_b":
                nickname_b,

            "match_type":
                series[
                    "match_type"
                ],

            "started_at":
                started_at.isoformat(),

            "status":
                status,

            "set_count":
                len(sets),

            "stats_sync_status":
                final_stats_sync_status,
        },

        "sets":
            sets,

        "mvp":
            mvp,
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
# SEASON CHAMPION
# 시즌 우승자 + FINAL MVP
# =========================

@app.get("/api/season/champion")
def get_season_champion():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 현재 시즌 결승 SERIES
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.status,
                    s.stats_sync_status,
                    s.best_of,
                    s.wins_required,

                    s.team_a_id,
                    s.team_b_id,

                    s.team_a_snapshot_name,
                    s.team_a_snapshot_logo_path,

                    s.team_b_snapshot_name,
                    s.team_b_snapshot_logo_path,

                    team_a.fcl_name
                        AS team_a_name,

                    team_a.fc_nickname
                        AS team_a_nickname,

                    team_b.fcl_name
                        AS team_b_name,

                    team_b.fc_nickname
                        AS team_b_nickname

                FROM series AS s

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE
                    s.series_type = '플레이오프'

                    AND
                    s.playoff_stage = '결승시리즈'

                    AND
                    s.status <> 'cancelled'

                ORDER BY s.id DESC

                LIMIT 1
                """
            )


            final_series = cursor.fetchone()


            # 결승 자체가 아직 없음
            if not final_series:
                return {
                    "season": 1,
                    "completed": False,
                    "champion": None,
                    "final": None,
                    "final_mvp": None,
                }


            # 결승이 아직 진행 중
            if (
                final_series["status"]
                != "completed"
            ):
                return {
                    "season": 1,
                    "completed": False,
                    "champion": None,
                    "final": {
                        "series_id":
                            final_series["id"],

                        "status":
                            final_series["status"],
                    },
                    "final_mvp": None,
                }


            # =========================
            # 결승 세트 결과
            # =========================

            cursor.execute(
                """
                SELECT
                    set_number,
                    winner_side

                FROM series_sets

                WHERE series_id = %s

                ORDER BY set_number
                """,
                (
                    final_series["id"],
                ),
            )


            final_sets = cursor.fetchall()


            team_a_wins = 0
            team_b_wins = 0

            champion_side = None
            winning_set = None

            invalid_final = False


            for final_set in final_sets:

                winner_side = final_set[
                    "winner_side"
                ]


                if winner_side not in (
                    "team_a",
                    "team_b",
                ):
                    invalid_final = True
                    break


                # 이미 우승 확정 뒤
                # 추가 세트가 존재하면 비정상
                if champion_side is not None:
                    invalid_final = True
                    break


                if winner_side == "team_a":
                    team_a_wins += 1

                else:
                    team_b_wins += 1


                if (
                    team_a_wins
                    >= int(
                        final_series[
                            "wins_required"
                        ]
                    )
                ):
                    champion_side = "team_a"

                    winning_set = final_set[
                        "set_number"
                    ]


                elif (
                    team_b_wins
                    >= int(
                        final_series[
                            "wins_required"
                        ]
                    )
                ):
                    champion_side = "team_b"

                    winning_set = final_set[
                        "set_number"
                    ]


            # =========================
            # 실제 4승 미도달
            # 또는 비정상 데이터
            # =========================

            if (
                invalid_final
                or
                champion_side is None
            ):
                return {
                    "season": 1,
                    "completed": False,
                    "champion": None,

                    "final": {
                        "series_id":
                            final_series["id"],

                        "status":
                            final_series["status"],

                        "team_a_wins":
                            team_a_wins,

                        "team_b_wins":
                            team_b_wins,
                    },

                    "final_mvp": None,
                }


            # =========================
            # 우승자
            # =========================

            if champion_side == "team_a":

                champion = {
                    "participant_id":
                        final_series[
                            "team_a_id"
                        ],

                    "fcl_name":
                        final_series[
                            "team_a_name"
                        ],

                    "nickname":
                        final_series[
                            "team_a_nickname"
                        ],

                    "team_name":
                        final_series[
                            "team_a_snapshot_name"
                        ],

                    "team_logo_path":
                        final_series[
                            "team_a_snapshot_logo_path"
                        ],
                }

            else:

                champion = {
                    "participant_id":
                        final_series[
                            "team_b_id"
                        ],

                    "fcl_name":
                        final_series[
                            "team_b_name"
                        ],

                    "nickname":
                        final_series[
                            "team_b_nickname"
                        ],

                    "team_name":
                        final_series[
                            "team_b_snapshot_name"
                        ],

                    "team_logo_path":
                        final_series[
                            "team_b_snapshot_logo_path"
                        ],
                }


            # =========================
            # FINAL MVP
            # =========================

            cursor.execute(
                """
                SELECT
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
                    final_series["id"],
                ),
            )


            final_mvp_row = cursor.fetchone()


    final_mvp = None


    if final_mvp_row:

        final_mvp = {
            "fcl_name":
                final_mvp_row[
                    "fcl_name"
                ],

            "nickname":
                final_mvp_row[
                    "nickname"
                ],

            "sp_id":
                final_mvp_row[
                    "sp_id"
                ],

            "player_name":
                final_mvp_row[
                    "player_name"
                ],

            "sets_played":
                final_mvp_row[
                    "sets_played"
                ],

            "rating_total":
                float(
                    final_mvp_row[
                        "rating_total"
                    ]
                ),

            "average_rating":
                float(
                    final_mvp_row[
                        "average_rating"
                    ]
                ),

            "goals":
                final_mvp_row[
                    "goals"
                ],

            "assists":
                final_mvp_row[
                    "assists"
                ],

            "image_url":
                final_mvp_row[
                    "image_url"
                ],
        }


    return {
        "season": 1,

        "completed": True,

        "champion":
            champion,

        "final": {
            "series_id":
                final_series["id"],

            "best_of":
                final_series["best_of"],

            "wins_required":
                final_series[
                    "wins_required"
                ],

            "team_a_wins":
                team_a_wins,

            "team_b_wins":
                team_b_wins,

            "winning_set":
                winning_set,

            "stats_sync_status":
                final_series[
                    "stats_sync_status"
                ],
        },

        "final_mvp":
            final_mvp,
    }


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
                    s.target_set_count,
                    s.round_number,

                    s.playoff_stage,
                    s.best_of,
                    s.wins_required,

                    s.scheduled_date,
                    s.started_at,
                    s.completed_at,
                    s.stats_sync_status,

                    s.team_a_snapshot_name,
                    s.team_a_snapshot_logo_path,

                    s.team_b_snapshot_name,
                    s.team_b_snapshot_logo_path,

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
                        team_b_score,
                        winner_side,
                        result_method
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


                # =========================
                # SERIES별 결과 완성 여부
                #
                # 프리시즌 / 정규리그:
                # target_set_count 기준
                #
                # 플레이오프:
                # 선승 구조이므로 실제 저장된
                # 세트를 그대로 사용
                # =========================

                if (
                    series_row[
                        "series_type"
                    ]
                    != "플레이오프"
                ):

                    target_set_count = int(
                        series_row[
                            "target_set_count"
                        ]
                        or 3
                    )


                    if (
                        len(set_rows)
                        != target_set_count
                    ):
                        continue


                else:

                    wins_required = int(
                        series_row[
                            "wins_required"
                        ]
                        or 1
                    )


                    if (
                        len(set_rows)
                        < wins_required
                    ):
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

                            "winner_side":
                                set_row[
                                    "winner_side"
                                ],

                            "result_method":
                                set_row[
                                    "result_method"
                                ],
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

                        "stats_sync_status":
                            series_row[
                                "stats_sync_status"
                            ],

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
                            series_row[
                                "round_number"
                            ],
                        "match_type":
                            series_row[
                                "series_type"
                            ],

                        "target_set_count":
                            int(
                                series_row[
                                    "target_set_count"
                                ]
                                or 3
                            ),

                        "playoff_stage":
                            series_row[
                                "playoff_stage"
                            ],

                        "best_of":
                            series_row[
                                "best_of"
                            ],

                        "wins_required":
                            series_row[
                                "wins_required"
                            ],

                        "team_a":
                            series_row[
                                "team_a"
                            ],

                        "team_b":
                            series_row[
                                "team_b"
                            ],

                        "team_a_snapshot_name":
                            series_row[
                                "team_a_snapshot_name"
                            ],

                        "team_a_snapshot_logo_path":
                            series_row[
                                "team_a_snapshot_logo_path"
                            ],

                        "team_b_snapshot_name":
                            series_row[
                                "team_b_snapshot_name"
                            ],

                        "team_b_snapshot_logo_path":
                            series_row[
                                "team_b_snapshot_logo_path"
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
# SERIES 세트별 스쿼드 조회
# =========================

@app.get(
    "/api/fconline/series/{series_id}/squads"
)
def get_series_squads(
    series_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # SERIES 정보
            # =========================

            cursor.execute(
                """
                SELECT
                    s.id,
                    s.series_type,
                    s.playoff_stage,
                    s.status,

                    team_a.id
                        AS team_a_id,

                    team_a.fcl_name
                        AS team_a_fcl_name,

                    COALESCE(
                        s.team_a_snapshot_name,
                        team_a.current_team_name
                    ) AS team_a_name,

                    COALESCE(
                        s.team_a_snapshot_logo_path,
                        team_a.current_team_logo_path
                    ) AS team_a_logo_path,

                    team_b.id
                        AS team_b_id,

                    team_b.fcl_name
                        AS team_b_fcl_name,

                    COALESCE(
                        s.team_b_snapshot_name,
                        team_b.current_team_name
                    ) AS team_b_name,

                    COALESCE(
                        s.team_b_snapshot_logo_path,
                        team_b.current_team_logo_path
                    ) AS team_b_logo_path

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


            # =========================
            # SET + Snapshot 선수
            # =========================

            cursor.execute(
                """
                SELECT
                    ss.set_number,
                    ss.played_at,

                    ss.team_a_score,
                    ss.team_b_score,

                    ss.team_a_own_goals,
                    ss.team_b_own_goals,

                    ss.winner_side,
                    ss.result_method,

                    sssp.side,
                    sssp.source_order,

                    sssp.sp_id,
                    sssp.player_name,

                    sssp.sp_position,
                    sssp.sp_grade,

                    sssp.rating,
                    sssp.goals,
                    sssp.penalty_goals,
                    sssp.assists,

                    sssp.image_url

                FROM series_sets AS ss

                LEFT JOIN
                    series_set_squad_players
                        AS sssp
                    ON sssp.series_set_id =
                        ss.id

                WHERE ss.series_id = %s

                ORDER BY
                    ss.set_number,
                    sssp.side,
                    sssp.source_order
                """,
                (
                    series_id,
                ),
            )

            rows = cursor.fetchall()


    # =========================
    # SET별 응답 구성
    # =========================

    set_map = {}


    for row in rows:

        set_number = row[
            "set_number"
        ]


        if set_number not in set_map:

            set_map[set_number] = {
                "set":
                    set_number,

                "played_at":
                    (
                        row[
                            "played_at"
                        ].isoformat()

                        if row[
                            "played_at"
                        ]

                        else None
                    ),

                "team_a_score":
                    row[
                        "team_a_score"
                    ],

                "team_b_score":
                    row[
                        "team_b_score"
                    ],

                "team_a_own_goals":
                    int(
                        row[
                            "team_a_own_goals"
                        ]
                        or 0
                    ),

                "team_b_own_goals":
                    int(
                        row[
                            "team_b_own_goals"
                        ]
                        or 0
                    ),

                "winner_side":
                    row[
                        "winner_side"
                    ],

                "result_method":
                    row[
                        "result_method"
                    ],

                "team_a_squad": [],
                "team_b_squad": [],
            }


        # Snapshot이 없는 SET도
        # LEFT JOIN으로 반환 가능
        if row["side"] is None:
            continue


        player = {
            "source_order":
                row[
                    "source_order"
                ],

            "sp_id":
                row[
                    "sp_id"
                ],

            "player_name":
                row[
                    "player_name"
                ],

            "sp_position":
                row[
                    "sp_position"
                ],

            "sp_grade":
                row[
                    "sp_grade"
                ],

            "rating":
                float(
                    row[
                        "rating"
                    ]
                ),

            "goals":
                row[
                    "goals"
                ],

            "penalty_goals":
                int(
                    row[
                        "penalty_goals"
                    ]
                    or 0
                ),

            "assists":
                row[
                    "assists"
                ],

            "image_url":
                row[
                    "image_url"
                ],
        }


        if row["side"] == "team_a":

            set_map[
                set_number
            ][
                "team_a_squad"
            ].append(
                player
            )


        elif row["side"] == "team_b":

            set_map[
                set_number
            ][
                "team_b_squad"
            ].append(
                player
            )


    return {
        "series_id":
            series["id"],

        "series_type":
            series[
                "series_type"
            ],

        "playoff_stage":
            series[
                "playoff_stage"
            ],

        "status":
            series[
                "status"
            ],

        "team_a": {
            "participant_id":
                series[
                    "team_a_id"
                ],

            "fcl_name":
                series[
                    "team_a_fcl_name"
                ],

            "team_name":
                series[
                    "team_a_name"
                ],

            "logo_path":
                series[
                    "team_a_logo_path"
                ],
        },

        "team_b": {
            "participant_id":
                series[
                    "team_b_id"
                ],

            "fcl_name":
                series[
                    "team_b_fcl_name"
                ],

            "team_name":
                series[
                    "team_b_name"
                ],

            "logo_path":
                series[
                    "team_b_logo_path"
                ],
        },

        "sets":
            list(
                set_map.values()
            ),
    }

# =========================
# DB 초기화
# =========================

@app.post("/api/database/init")
def init_database():

    initialize_database()


    # =========================
    # COMMUNITY NOTICE MIGRATION
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # PREDICTIONS
            # 승부예측
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    predictions (

                    id BIGSERIAL PRIMARY KEY,

                    user_id BIGINT
                        NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    series_id BIGINT
                        NOT NULL
                        REFERENCES series(id)
                        ON DELETE CASCADE,

                    predicted_participant_id BIGINT
                        REFERENCES participants(id),

                    prediction_type VARCHAR(20)
                        NOT NULL
                        DEFAULT 'participant',

                    stake_points INTEGER
                        NOT NULL,

                    odds NUMERIC(8, 2)
                        NOT NULL
                        DEFAULT 2.00,

                    status VARCHAR(20)
                        NOT NULL
                        DEFAULT 'pending',

                    payout_points INTEGER
                        NOT NULL
                        DEFAULT 0,

                    settled_at TIMESTAMPTZ,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT
                        predictions_stake_check

                    CHECK (
                        prediction_type IN (
                            'participant',
                            'draw'
                        )
                    ),

                    CHECK (
                        stake_points > 0
                    ),

                    CONSTRAINT
                        predictions_odds_check

                    CHECK (
                        odds >= 1.00
                    ),

                    CONSTRAINT
                        predictions_payout_check

                    CHECK (
                        payout_points >= 0
                    ),

                    CONSTRAINT
                        predictions_status_check

                    CHECK (
                        status IN (
                            'pending',
                            'win',
                            'loss',
                            'refunded'
                        )
                    ),

                    CONSTRAINT
                        predictions_user_series_unique

                    UNIQUE (
                        user_id,
                        series_id
                    )
                )
                """
            )

            # =========================
            # PREDICTIONS
            # 무승부 예측 지원
            # =========================

            cursor.execute(
                """
                ALTER TABLE predictions

                ADD COLUMN IF NOT EXISTS
                    prediction_type VARCHAR(20)
                """
            )


            cursor.execute(
                """
                UPDATE predictions

                SET prediction_type =
                    'participant'

                WHERE prediction_type
                    IS NULL
                """
            )


            cursor.execute(
                """
                ALTER TABLE predictions

                ALTER COLUMN
                    predicted_participant_id

                DROP NOT NULL
                """
            )

            # =========================
            # PREDICTIONS
            # 세트별 승부예측 지원
            # =========================

            cursor.execute(
                """
                ALTER TABLE predictions

                ADD COLUMN IF NOT EXISTS
                    set_number INTEGER
                """
            )


            # 기존 테스트 예측 데이터는
            # 우선 1세트 예측으로 변환
            cursor.execute(
                """
                UPDATE predictions

                SET set_number = 1

                WHERE set_number IS NULL
                """
            )


            cursor.execute(
                """
                ALTER TABLE predictions

                ALTER COLUMN set_number
                SET NOT NULL
                """
            )


            # 기존 경기당 1회 UNIQUE 제거
            cursor.execute(
                """
                ALTER TABLE predictions

                DROP CONSTRAINT IF EXISTS
                    predictions_user_series_unique
                """
            )


            # 세트 번호 검증
            cursor.execute(
                """
                DO $$
                BEGIN

                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname =
                            'predictions_set_number_check'
                    ) THEN

                        ALTER TABLE predictions

                        ADD CONSTRAINT
                            predictions_set_number_check

                        CHECK (
                            set_number
                            BETWEEN 1 AND 3
                        );

                    END IF;

                END
                $$;
                """
            )


            # 회원 + 경기 + 세트별 1회
            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    ux_predictions_user_series_set

                ON predictions (
                    user_id,
                    series_id,
                    set_number
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_predictions_series_set

                ON predictions (
                    series_id,
                    set_number,
                    status
                )
                """
            )



            # =========================
            # POINT TRANSACTION
            # IDEMPOTENCY
            # 중복 지급 / 환불 방지
            # =========================

            cursor.execute(
                """
                ALTER TABLE point_transactions

                ADD COLUMN IF NOT EXISTS
                    idempotency_key VARCHAR(150)
                """
            )


            cursor.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_point_transactions_idempotency_key

                ON point_transactions (
                    idempotency_key
                )

                WHERE
                    idempotency_key
                    IS NOT NULL
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_predictions_series_id

                ON predictions (
                    series_id
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_predictions_user_id

                ON predictions (
                    user_id,
                    created_at DESC
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_predictions_pending

                ON predictions (
                    series_id,
                    status
                )
                """
            )

            cursor.execute(
                """
                ALTER TABLE community_posts

                ADD COLUMN IF NOT EXISTS
                    is_notice BOOLEAN
                    NOT NULL
                    DEFAULT FALSE
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_community_posts_notice

                ON community_posts (
                    is_notice,
                    created_at DESC
                )
                """
            )

            # =========================
            # COMMUNITY COMMENTS
            # =========================

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    community_comments (

                    id BIGSERIAL PRIMARY KEY,

                    post_id BIGINT NOT NULL
                        REFERENCES community_posts(id)
                        ON DELETE CASCADE,

                    user_id BIGINT NOT NULL
                        REFERENCES users(id)
                        ON DELETE CASCADE,

                    content TEXT NOT NULL,

                    created_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    CONSTRAINT
                        community_comments_content_check

                    CHECK (
                        LENGTH(
                            BTRIM(content)
                        ) > 0
                    )
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_community_comments_post_id

                ON community_comments (
                    post_id,
                    created_at ASC,
                    id ASC
                )
                """
            )


            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_community_comments_user_id

                ON community_comments (
                    user_id
                )
                """
            )


        connection.commit()


    return {
        "status":
            "success",

        "message":
            "FCL 데이터베이스가 초기화되었습니다.",
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

# 메타데이터 API
@app.get(
    "/api/fconline/metadata/seasons"
)
def get_fconline_season_metadata():

    seasons = {}


    # =========================
    # Nexon 메타데이터
    # 아직 서비스 중일 때 사용
    # =========================

    try:

        live_metadata = get_season_metadata()


        seasons.update(
            live_metadata
        )

    except Exception as error:

        print(
            "Nexon 시즌 메타데이터 "
            "조회 실패:",
            error,
        )


    # =========================
    # 우리 Snapshot
    # 항상 Snapshot 우선
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    season_id,
                    class_name

                FROM
                    fconline_season_snapshots

                ORDER BY
                    season_id
                """
            )


            snapshots = cursor.fetchall()


    for snapshot in snapshots:

        season_id = snapshot[
                "season_id"
            ]


        seasons[
            season_id
        ] = {
            "season_id":
                season_id,

            "class_name":
                snapshot[
                    "class_name"
                ],

            "season_image_url":
                (
                    "/api/fconline/"
                    "metadata/seasons/"
                    f"{season_id}/image"
                ),
        }


    return {
        "seasons":
            list(
                seasons.values()
            )
    }

@app.get(
    "/api/fconline/"
    "metadata/seasons/"
    "{season_id}/image"
)
def get_fconline_season_snapshot_image(
    season_id: int,
):

    # =========================================
    # 1. 기존 snapshot 확인
    # =========================================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    image_data,
                    image_content_type

                FROM
                    fconline_season_snapshots

                WHERE
                    season_id = %s
                """,
                (
                    season_id,
                ),
            )

            snapshot = cursor.fetchone()


    # =========================================
    # 2. 이미 저장되어 있으면 바로 반환
    # =========================================

    if (
        snapshot
        and
        snapshot["image_data"]
    ):

        return Response(
            content=
                bytes(
                    snapshot[
                        "image_data"
                    ]
                ),

            media_type=
                snapshot[
                    "image_content_type"
                ],
        )


    # =========================================
    # 3. snapshot이 없으면 Nexon metadata 조회
    # =========================================

    season_metadata = get_season_metadata()


    season = season_metadata.get(
            season_id
        )


    if not season:

        raise HTTPException(
            status_code=404,
            detail=(
                f"시즌 메타데이터를 찾을 수 없습니다: "
                f"{season_id}"
            ),
        )


    source_image_url = season[
            "season_image_url"
        ]


    # =========================================
    # 4. Nexon 시즌 아이콘 다운로드
    # =========================================

    image_response = httpx.get(
            source_image_url,
            timeout=20.0,
            follow_redirects=True,
        )


    if (
        image_response.status_code
        != 200
    ):

        raise HTTPException(
            status_code=
                image_response.status_code,

            detail=
                "시즌 이미지 다운로드 실패",
        )


    image_data = image_response.content


    if not image_data:

        raise HTTPException(
            status_code=502,
            detail=
                "시즌 이미지 데이터가 없습니다.",
        )


    image_content_type = (
            image_response
            .headers
            .get(
                "content-type",
                "image/png",
            )
            .split(";")[0]
            .strip()
        )


    # =========================================
    # 5. DB snapshot 저장
    # =========================================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_season_snapshots (
                        season_id,
                        class_name,
                        source_image_url,
                        image_data,
                        image_content_type
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

                ON CONFLICT (
                    season_id
                )

                DO UPDATE SET
                    class_name =
                        EXCLUDED.class_name,

                    source_image_url =
                        EXCLUDED.source_image_url,

                    image_data =
                        EXCLUDED.image_data,

                    image_content_type =
                        EXCLUDED.image_content_type
                """,
                (
                    season_id,

                    season[
                        "class_name"
                    ],

                    source_image_url,

                    image_data,

                    image_content_type,
                ),
            )


        connection.commit()


    # =========================================
    # 6. 방금 받은 이미지 반환
    # =========================================

    return Response(
        content=
            image_data,

        media_type=
            image_content_type,
    )


@app.post(
    "/api/admin/fconline/season-snapshots/backfill"
)
def admin_backfill_fconline_season_snapshots(
    admin_token: str =
        Depends(
            require_admin
        ),
):

    # =========================
    # 과거 기록에 등장한 모든 sp_id
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT sp_id
                FROM series_set_squad_players

                UNION

                SELECT sp_id
                FROM series_mvp

                UNION

                SELECT sp_id
                FROM series_player_stats
                """
            )


            rows = cursor.fetchall()


    # =========================
    # 시즌별 대표 sp_id 하나만 사용
    # =========================

    season_sp_ids = {}


    for row in rows:

        sp_id = row["sp_id"]


        if sp_id is None:
            continue


        season_id = (
            int(sp_id)
            // 1_000_000
        )


        if season_id not in season_sp_ids:

            season_sp_ids[
                season_id
            ] = int(sp_id)


    # =========================
    # Snapshot 저장
    # =========================

    saved = []
    failed = []


    for (
        season_id,
        sp_id,
    ) in sorted(
        season_sp_ids.items()
    ):

        try:

            snapshot = ensure_fconline_season_snapshot(
                    sp_id
                )


            saved.append(
                {
                    "season_id":
                        snapshot[
                            "season_id"
                        ],

                    "class_name":
                        snapshot[
                            "class_name"
                        ],
                }
            )


        except Exception as error:

            failed.append(
                {
                    "season_id":
                        season_id,

                    "error":
                        (
                            error.detail
                            if isinstance(
                                error,
                                HTTPException,
                            )
                            else str(error)
                        ),
                }
            )


    return {
        "target_season_count":
            len(
                season_sp_ids
            ),

        "snapshot_count":
            len(saved),

        "failed_count":
            len(failed),

        "snapshots":
            saved,

        "failed":
            failed,
    }

# =========================
# COMMUNITY
# 자유게시판
# =========================

def hash_community_password(
    password: str,
):

    iterations = 200_000

    salt = secrets.token_bytes(
        16
    )

    password_hash = (
        hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(
                "utf-8"
            ),
            salt,
            iterations,
        )
    )

    return (
        f"pbkdf2_sha256$"
        f"{iterations}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


def verify_community_password(
    password: str,
    stored_hash: str,
):

    if not stored_hash:
        return False


    try:

        (
            algorithm,
            iterations_text,
            salt_hex,
            expected_hash_hex,
        ) = stored_hash.split(
            "$"
        )


        if (
            algorithm
            != "pbkdf2_sha256"
        ):
            return False


        iterations = int(
            iterations_text
        )

        salt = bytes.fromhex(
            salt_hex
        )

        expected_hash = (
            bytes.fromhex(
                expected_hash_hex
            )
        )


        actual_hash = (
            hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(
                    "utf-8"
                ),
                salt,
                iterations,
            )
        )


        return hmac.compare_digest(
            actual_hash,
            expected_hash,
        )

    except (
        ValueError,
        TypeError,
    ):

        return False

def get_community_post_attachments(
    cursor,
    post_id: int,
):

    cursor.execute(
        """
        SELECT
            id,
            original_file_name,
            content_type,
            sort_order

        FROM community_attachments

        WHERE post_id = %s

        ORDER BY
            sort_order ASC,
            id ASC
        """,
        (
            post_id,
        ),
    )

    rows = cursor.fetchall()

    return [
        {
            "id": row["id"],
            "original_file_name": row["original_file_name"],
            "content_type": row["content_type"],
            "sort_order": row["sort_order"],
            "image_url": (
                "/api/community/"
                f"attachments/{row['id']}"
            ),
        }
        for row in rows
    ]

@app.get("/api/community/posts")
def get_community_posts(
    board_type: str = "free",
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    cp.id,
                    cp.board_type,
                    cp.title,
                    cp.content,
                    cp.author_name,
                    cp.is_notice,
                    cp.created_at,
                    cp.updated_at,
                    COUNT(ca.id) AS attachment_count

                FROM community_posts AS cp

                LEFT JOIN community_attachments AS ca
                    ON ca.post_id = cp.id

                WHERE cp.board_type = %s

                GROUP BY
                    cp.id

                ORDER BY
                    cp.is_notice DESC,
                    cp.created_at DESC,
                    cp.id DESC
                """,
                (
                    board_type,
                ),
            )


            rows = cursor.fetchall()


    posts = []


    for row in rows:

        posts.append(
            {
                "id":
                    row["id"],

                "board_type":
                    row["board_type"],

                "is_notice":
                    bool(
                        row["is_notice"]
                    ),

                "title":
                    row["title"],

                "content":
                    row["content"],

                "author_name":
                    row["author_name"],

                "created_at":
                    row["created_at"].isoformat(),

                "updated_at":
                    row["updated_at"].isoformat(),

                "attachment_count":
                    int(row["attachment_count"]),
            }
        )


    return posts

@app.post("/api/community/posts")
def create_community_post(
    payload: dict,
):

    board_type = str(
            payload.get(
                "board_type",
                ""
            )
        ).strip()


    title = str(
            payload.get(
                "title",
                ""
            )
        ).strip()


    content = str(
            payload.get(
                "content",
                ""
            )
        ).strip()


    author_name = str(
            payload.get(
                "author_name",
                ""
            )
        ).strip()

    password = str(
            payload.get(
                "password",
                ""
            )
        ).strip()


    if board_type not in (
        "free",
        "player_photo_request",
    ):

        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 게시판 유형입니다.",
        )


    if not title:

        raise HTTPException(
            status_code=400,
            detail="제목을 입력해주세요.",
        )


    if not content:

        raise HTTPException(
            status_code=400,
            detail="내용을 입력해주세요.",
        )


    if not author_name:

        raise HTTPException(
            status_code=400,
            detail="작성자를 입력해주세요.",
        )

    if len(password) < 4:

        raise HTTPException(
            status_code=400,
            detail="비밀번호는 4자 이상 입력해주세요.",
        )


    if len(password) > 50:

        raise HTTPException(
            status_code=400,
            detail="비밀번호는 50자 이하로 입력해주세요.",
        )


    password_hash = (
        hash_community_password(
            password
        )
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO community_posts (
                    board_type,
                    title,
                    content,
                    author_name,
                    password_hash
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

                RETURNING
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    created_at,
                    updated_at
                """,
                (
                    board_type,
                    title,
                    content,
                    author_name,
                    password_hash,
                ),
            )


            row = cursor.fetchone()


        connection.commit()


    return {
        "id":
            row["id"],

        "board_type":
            row["board_type"],

        "title":
            row["title"],

        "content":
            row["content"],

        "author_name":
            row["author_name"],

        "created_at":
            row["created_at"].isoformat(),

        "updated_at":
            row["updated_at"].isoformat(),
    }



@app.get("/api/community/posts/{post_id}")
def get_community_post(
    post_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    is_notice,
                    created_at,
                    updated_at

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )

            row = cursor.fetchone()

            if not row:

                raise HTTPException(
                    status_code=404,
                    detail="게시글을 찾을 수 없습니다.",
                )

            attachments = (
                get_community_post_attachments(
                    cursor,
                    post_id,
                )
            )


    return {
        "id":
            row["id"],

        "board_type":
            row["board_type"],

        "is_notice":
            bool(
                row["is_notice"]
            ),

        "title":
            row["title"],

        "content":
            row["content"],

        "author_name":
            row["author_name"],

        "created_at":
            row["created_at"].isoformat(),

        "updated_at":
            row["updated_at"].isoformat(),

        "attachments":
            attachments,
    }

# =========================
# COMMUNITY COMMENTS
# 댓글 조회
# =========================

@app.get(
    "/api/community/posts/{post_id}/comments"
)
def get_community_comments(
    post_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 게시글 존재 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    board_type
                FROM community_posts
                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


            post = cursor.fetchone()


            if not post:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "게시글을 찾을 수 없습니다."
                    ),
                )


            # 자유게시판에만 댓글 사용
            if (
                post["board_type"]
                != "free"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "자유게시판 게시글의 "
                        "댓글만 조회할 수 있습니다."
                    ),
                )


            # =========================
            # 댓글 조회
            # =========================

            cursor.execute(
                """
                SELECT
                    cc.id,
                    cc.post_id,
                    cc.user_id,
                    cc.content,
                    cc.created_at,
                    cc.updated_at,

                    u.nickname
                        AS author_nickname,

                    u.is_admin
                        AS author_is_admin

                FROM community_comments
                    AS cc

                INNER JOIN users AS u
                    ON u.id = cc.user_id

                WHERE
                    cc.post_id = %s

                ORDER BY
                    cc.created_at ASC,
                    cc.id ASC
                """,
                (
                    post_id,
                ),
            )


            rows = cursor.fetchall()


    return [
        {
            "id":
                row["id"],

            "post_id":
                row["post_id"],

            "user_id":
                row["user_id"],

            "author_nickname":
                row[
                    "author_nickname"
                ],

            "author_is_admin":
                bool(
                    row[
                        "author_is_admin"
                    ]
                ),

            "content":
                row["content"],

            "created_at":
                row[
                    "created_at"
                ].isoformat(),

            "updated_at":
                row[
                    "updated_at"
                ].isoformat(),
        }

        for row in rows
    ]


# =========================
# COMMUNITY COMMENTS
# 댓글 작성
# =========================

@app.post(
    "/api/community/posts/{post_id}/comments"
)
def create_community_comment(
    post_id: int,

    request:
        CommunityCommentCreateRequest,

    user = Depends(
        require_user
    ),
):

    content = (
        request.content
        .strip()
    )


    # =========================
    # 내용 검증
    # =========================

    if not content:

        raise HTTPException(
            status_code=400,
            detail=(
                "댓글 내용을 입력해주세요."
            ),
        )


    if len(content) > 1000:

        raise HTTPException(
            status_code=400,
            detail=(
                "댓글은 1000자 이하로 "
                "입력해주세요."
            ),
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            # =========================
            # 게시글 존재 확인
            # =========================

            cursor.execute(
                """
                SELECT
                    id,
                    board_type
                FROM community_posts
                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


            post = cursor.fetchone()


            if not post:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "게시글을 찾을 수 없습니다."
                    ),
                )


            if (
                post["board_type"]
                != "free"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "자유게시판 게시글에만 "
                        "댓글을 작성할 수 있습니다."
                    ),
                )


            # =========================
            # 댓글 저장
            # =========================

            cursor.execute(
                """
                INSERT INTO
                    community_comments (
                        post_id,
                        user_id,
                        content
                    )

                VALUES (
                    %s,
                    %s,
                    %s
                )

                RETURNING
                    id,
                    post_id,
                    user_id,
                    content,
                    created_at,
                    updated_at
                """,
                (
                    post_id,
                    user["id"],
                    content,
                ),
            )


            comment = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "message":
            "댓글이 등록되었습니다.",

        "comment": {
            "id":
                comment["id"],

            "post_id":
                comment["post_id"],

            "user_id":
                comment["user_id"],

            "author_nickname":
                user["nickname"],

            "author_is_admin":
                bool(
                    user["is_admin"]
                ),

            "content":
                comment["content"],

            "created_at":
                comment[
                    "created_at"
                ].isoformat(),

            "updated_at":
                comment[
                    "updated_at"
                ].isoformat(),
        },
    }


@app.patch(
    "/api/community/posts/{post_id}"
)
def update_community_post(
    post_id: int,
    payload: dict,
):

    password = str(
        payload.get(
            "password",
            ""
        )
    ).strip()

    title = str(
        payload.get(
            "title",
            ""
        )
    ).strip()

    author_name = str(
        payload.get(
            "author_name",
            ""
        )
    ).strip()

    content = str(
        payload.get(
            "content",
            ""
        )
    ).strip()


    if not password:

        raise HTTPException(
            status_code=400,
            detail="비밀번호를 입력해주세요.",
        )


    if not title:

        raise HTTPException(
            status_code=400,
            detail="제목을 입력해주세요.",
        )


    if not author_name:

        raise HTTPException(
            status_code=400,
            detail="작성자를 입력해주세요.",
        )


    if not content:

        raise HTTPException(
            status_code=400,
            detail="내용을 입력해주세요.",
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    password_hash,
                    is_notice

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )

            post_row = cursor.fetchone()


            if not post_row:

                raise HTTPException(
                    status_code=404,
                    detail="게시글을 찾을 수 없습니다.",
                )

            if post_row["is_notice"]:

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "공지사항은 관리자만 "
                        "수정할 수 있습니다."
                    ),
                )


            if not verify_community_password(
                password,
                post_row[
                    "password_hash"
                ],
            ):

                raise HTTPException(
                    status_code=403,
                    detail="비밀번호가 일치하지 않습니다.",
                )


            cursor.execute(
                """
                UPDATE community_posts

                SET
                    title = %s,
                    author_name = %s,
                    content = %s,
                    updated_at = NOW()

                WHERE id = %s

                RETURNING
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    created_at,
                    updated_at
                """,
                (
                    title,
                    author_name,
                    content,
                    post_id,
                ),
            )

            row = cursor.fetchone()


        connection.commit()


    return {
        "id": row["id"],
        "board_type": row["board_type"],
        "title": row["title"],
        "content": row["content"],
        "author_name": row["author_name"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }

@app.delete(
    "/api/community/posts/{post_id}"
)
def delete_community_post(
    post_id: int,
    payload: dict,
):

    password = str(
        payload.get(
            "password",
            ""
        )
    ).strip()


    if not password:

        raise HTTPException(
            status_code=400,
            detail="비밀번호를 입력해주세요.",
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    password_hash,
                    is_notice

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )

            post_row = cursor.fetchone()


            if not post_row:

                raise HTTPException(
                    status_code=404,
                    detail="게시글을 찾을 수 없습니다.",
                )

            if post_row["is_notice"]:

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "공지사항은 관리자만 "
                        "삭제할 수 있습니다."
                    ),
                )


            if not verify_community_password(
                password,
                post_row[
                    "password_hash"
                ],
            ):

                raise HTTPException(
                    status_code=403,
                    detail="비밀번호가 일치하지 않습니다.",
                )


            cursor.execute(
                """
                DELETE FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


        connection.commit()


    return {
        "deleted": True,
        "post_id": post_id,
    }

# =========================
# COMMUNITY COMMENTS
# 댓글 수정
# =========================

@app.patch(
    "/api/community/comments/{comment_id}"
)
def update_community_comment(
    comment_id: int,

    request:
        CommunityCommentUpdateRequest,

    user = Depends(
        require_user
    ),
):

    content = (
        request.content
        .strip()
    )


    if not content:

        raise HTTPException(
            status_code=400,
            detail="댓글 내용을 입력해주세요.",
        )


    if len(content) > 1000:

        raise HTTPException(
            status_code=400,
            detail=(
                "댓글은 1000자 이하로 "
                "입력해주세요."
            ),
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    post_id,
                    user_id
                FROM community_comments
                WHERE id = %s
                """,
                (
                    comment_id,
                ),
            )


            comment = cursor.fetchone()


            if not comment:

                raise HTTPException(
                    status_code=404,
                    detail="댓글을 찾을 수 없습니다.",
                )


            # 작성자 본인만 수정 가능
            if (
                comment["user_id"]
                != user["id"]
            ):

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "본인이 작성한 댓글만 "
                        "수정할 수 있습니다."
                    ),
                )


            cursor.execute(
                """
                UPDATE community_comments

                SET
                    content = %s,
                    updated_at = NOW()

                WHERE id = %s

                RETURNING
                    id,
                    post_id,
                    user_id,
                    content,
                    created_at,
                    updated_at
                """,
                (
                    content,
                    comment_id,
                ),
            )


            updated_comment = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "message":
            "댓글이 수정되었습니다.",

        "comment": {
            "id":
                updated_comment["id"],

            "post_id":
                updated_comment["post_id"],

            "user_id":
                updated_comment["user_id"],

            "author_nickname":
                user["nickname"],

            "author_is_admin":
                bool(
                    user["is_admin"]
                ),

            "content":
                updated_comment["content"],

            "created_at":
                updated_comment[
                    "created_at"
                ].isoformat(),

            "updated_at":
                updated_comment[
                    "updated_at"
                ].isoformat(),
        },
    }

# =========================
# COMMUNITY COMMENTS
# 댓글 삭제
# =========================

@app.delete(
    "/api/community/comments/{comment_id}"
)
def delete_community_comment(
    comment_id: int,

    user = Depends(
        require_user
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    post_id,
                    user_id

                FROM community_comments

                WHERE id = %s
                """,
                (
                    comment_id,
                ),
            )


            comment = cursor.fetchone()


            if not comment:

                raise HTTPException(
                    status_code=404,
                    detail="댓글을 찾을 수 없습니다.",
                )


            is_owner = (
                comment["user_id"]
                == user["id"]
            )


            is_admin = bool(
                user["is_admin"]
            )


            # 작성자 또는 관리자만 삭제 가능
            if (
                not is_owner
                and
                not is_admin
            ):

                raise HTTPException(
                    status_code=403,
                    detail=(
                        "댓글을 삭제할 "
                        "권한이 없습니다."
                    ),
                )


            cursor.execute(
                """
                DELETE FROM
                    community_comments

                WHERE id = %s
                """,
                (
                    comment_id,
                ),
            )


        connection.commit()


    return {
        "deleted":
            True,

        "comment_id":
            comment_id,

        "post_id":
            comment["post_id"],
    }

@app.post(
    "/api/community/admin/notices"
)
def create_community_notice(
    request:
        AdminCommunityNoticeRequest,

    admin_user = Depends(
        require_user_admin
    ),
):

    title = (
        request.title
        .strip()
    )


    content = (
        request.content
        .strip()
    )


    if not title:

        raise HTTPException(
            status_code=400,
            detail=(
                "제목을 입력해주세요."
            ),
        )


    if not content:

        raise HTTPException(
            status_code=400,
            detail=(
                "내용을 입력해주세요."
            ),
        )


    if len(title) > 200:

        raise HTTPException(
            status_code=400,
            detail=(
                "제목은 200자 이하로 "
                "입력해주세요."
            ),
        )


    # 일반 게시글 비밀번호 수정 기능으로
    # 공지를 수정할 수 없도록
    # 아무도 알 수 없는 임의 비밀번호 생성
    random_password = (
        secrets.token_urlsafe(
            32
        )
    )


    password_hash = (
        hash_community_password(
            random_password
        )
    )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO community_posts (
                    board_type,
                    title,
                    content,
                    author_name,
                    password_hash,
                    is_notice
                )

                VALUES (
                    'free',
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE
                )

                RETURNING
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    is_notice,
                    created_at,
                    updated_at
                """,
                (
                    title,
                    content,
                    admin_user[
                        "nickname"
                    ],
                    password_hash,
                ),
            )


            notice = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "message":
            "공지사항이 등록되었습니다.",

        "notice": {
            "id":
                notice["id"],

            "board_type":
                notice[
                    "board_type"
                ],

            "title":
                notice["title"],

            "content":
                notice["content"],

            "author_name":
                notice[
                    "author_name"
                ],

            "is_notice":
                notice[
                    "is_notice"
                ],

            "created_at":
                notice[
                    "created_at"
                ].isoformat(),

            "updated_at":
                notice[
                    "updated_at"
                ].isoformat(),
        },
    }

# =========================
# COMMUNITY ADMIN
# =========================

@app.patch(
    "/api/community/admin/posts/{post_id}"
)
def admin_update_community_post(
    post_id: int,

    request:
        AdminCommunityPostUpdateRequest,

    admin_user = Depends(
        require_user_admin
    ),
):

    title = (
        request.title
        .strip()
    )

    content = (
        request.content
        .strip()
    )


    if not title:

        raise HTTPException(
            status_code=400,
            detail=(
                "제목을 입력해주세요."
            ),
        )


    if not content:

        raise HTTPException(
            status_code=400,
            detail=(
                "내용을 입력해주세요."
            ),
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    board_type

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


            post = (
                cursor.fetchone()
            )


            if not post:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "게시글을 찾을 수 없습니다."
                    ),
                )


            if (
                post["board_type"]
                != "free"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "자유게시판 게시글만 "
                        "관리할 수 있습니다."
                    ),
                )


            cursor.execute(
                """
                UPDATE community_posts

                SET
                    title = %s,
                    content = %s,
                    updated_at = NOW()

                WHERE id = %s

                RETURNING
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    created_at,
                    updated_at
                """,
                (
                    title,
                    content,
                    post_id,
                ),
            )


            updated_post = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "message":
            "게시글이 관리자에 의해 수정되었습니다.",

        "post": {
            "id":
                updated_post["id"],

            "board_type":
                updated_post["board_type"],

            "title":
                updated_post["title"],

            "content":
                updated_post["content"],

            "author_name":
                updated_post["author_name"],

            "created_at":
                updated_post[
                    "created_at"
                ].isoformat(),

            "updated_at":
                updated_post[
                    "updated_at"
                ].isoformat(),
        },
    }


@app.delete(
    "/api/community/admin/posts/{post_id}"
)
def admin_delete_community_post(
    post_id: int,

    admin_user = Depends(
        require_user_admin
    ),
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    id,
                    board_type,
                    title

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


            post = (
                cursor.fetchone()
            )


            if not post:

                raise HTTPException(
                    status_code=404,
                    detail=(
                        "게시글을 찾을 수 없습니다."
                    ),
                )


            if (
                post["board_type"]
                != "free"
            ):

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "자유게시판 게시글만 "
                        "관리할 수 있습니다."
                    ),
                )


            # 첨부파일 레코드 먼저 제거
            cursor.execute(
                """
                DELETE FROM community_attachments

                WHERE post_id = %s
                """,
                (
                    post_id,
                ),
            )


            cursor.execute(
                """
                DELETE FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


        connection.commit()


    return {
        "deleted":
            True,

        "post_id":
            post_id,

        "message":
            "게시글이 관리자에 의해 삭제되었습니다.",
    }

# =========================
# PLAYER PHOTO REQUEST
# =========================

@app.post(
    "/api/community/player-photo-requests"
)
def create_player_photo_request(
    payload: dict,
):

    player_name = str(
        payload.get(
            "player_name",
            ""
        )
    ).strip()

    season_name = str(
        payload.get(
            "season_name",
            ""
        )
    ).strip()

    sp_id_value = payload.get(
        "sp_id"
    )

    content = str(
        payload.get(
            "content",
            ""
        )
    ).strip()

    author_name = str(
        payload.get(
            "author_name",
            ""
        )
    ).strip()

    password = str(
        payload.get(
            "password",
            ""
        )
    ).strip()


    if not player_name:

        raise HTTPException(
            status_code=400,
            detail="선수명을 입력해주세요.",
        )


    if not content:

        raise HTTPException(
            status_code=400,
            detail="요청 내용을 입력해주세요.",
        )


    if not author_name:

        raise HTTPException(
            status_code=400,
            detail="작성자 닉네임을 입력해주세요.",
        )


    if len(password) < 4:

        raise HTTPException(
            status_code=400,
            detail="비밀번호는 4자 이상 입력해주세요.",
        )


    if len(password) > 50:

        raise HTTPException(
            status_code=400,
            detail="비밀번호는 50자 이하로 입력해주세요.",
        )


    sp_id = None


    if (
        sp_id_value is not None
        and
        str(sp_id_value).strip()
    ):

        try:

            sp_id = int(
                sp_id_value
            )

        except (
            TypeError,
            ValueError,
        ):

            raise HTTPException(
                status_code=400,
                detail="sp_id가 올바르지 않습니다.",
            )


    password_hash = (
        hash_community_password(
            password
        )
    )


    if season_name:

        title = (
            f"{player_name} "
            f"({season_name}) "
            "선수 사진 요청"
        )

    else:

        title = (
            f"{player_name} "
            "선수 사진 요청"
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO community_posts (
                    board_type,
                    title,
                    content,
                    author_name,
                    password_hash
                )

                VALUES (
                    'player_photo_request',
                    %s,
                    %s,
                    %s,
                    %s
                )

                RETURNING
                    id,
                    board_type,
                    title,
                    content,
                    author_name,
                    created_at,
                    updated_at
                """,
                (
                    title,
                    content,
                    author_name,
                    password_hash,
                ),
            )

            post_row = cursor.fetchone()


            cursor.execute(
                """
                INSERT INTO player_photo_requests (
                    post_id,
                    player_name,
                    season_name,
                    sp_id,
                    request_status
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    'pending'
                )

                RETURNING
                    player_name,
                    season_name,
                    sp_id,
                    request_status,
                    admin_note,
                    completed_at
                """,
                (
                    post_row["id"],
                    player_name,
                    (
                        season_name
                        if season_name
                        else None
                    ),
                    sp_id,
                ),
            )

            request_row = (
                cursor.fetchone()
            )


        connection.commit()


    return {
        "id":
            post_row["id"],

        "board_type":
            post_row["board_type"],

        "title":
            post_row["title"],

        "content":
            post_row["content"],

        "author_name":
            post_row["author_name"],

        "created_at":
            post_row[
                "created_at"
            ].isoformat(),

        "updated_at":
            post_row[
                "updated_at"
            ].isoformat(),

        "player_name":
            request_row[
                "player_name"
            ],

        "season_name":
            request_row[
                "season_name"
            ],

        "sp_id":
            request_row[
                "sp_id"
            ],

        "request_status":
            request_row[
                "request_status"
            ],

        "admin_note":
            request_row[
                "admin_note"
            ],

        "completed_at":
            (
                request_row[
                    "completed_at"
                ].isoformat()

                if request_row[
                    "completed_at"
                ]

                else None
            ),
    }

@app.get(
    "/api/community/player-photo-requests"
)
def get_player_photo_requests():

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    cp.id,
                    cp.title,
                    cp.content,
                    cp.author_name,
                    cp.created_at,
                    cp.updated_at,

                    ppr.player_name,
                    ppr.season_name,
                    ppr.sp_id,
                    ppr.request_status,
                    ppr.admin_note,
                    ppr.completed_at,

                    COUNT(ca.id) AS attachment_count

                FROM community_posts cp

                INNER JOIN player_photo_requests ppr
                    ON ppr.post_id = cp.id

                LEFT JOIN community_attachments ca
                    ON ca.post_id = cp.id

                WHERE
                    cp.board_type = 'player_photo_request'

                GROUP BY
                    cp.id,
                    ppr.post_id

                ORDER BY
                    cp.id DESC
                """
            )

            rows = cursor.fetchall()


    return [
        {
            "id":
                row["id"],

            "title":
                row["title"],

            "content":
                row["content"],

            "author_name":
                row["author_name"],

            "created_at":
                row[
                    "created_at"
                ].isoformat(),

            "updated_at":
                row[
                    "updated_at"
                ].isoformat(),

            "player_name":
                row["player_name"],

            "season_name":
                row["season_name"],

            "sp_id":
                row["sp_id"],

            "request_status":
                row[
                    "request_status"
                ],

            "admin_note":
                row["admin_note"],

            "completed_at":
                (
                    row[
                        "completed_at"
                    ].isoformat()

                    if row[
                        "completed_at"
                    ]

                    else None
                ),

            "attachment_count":
                row[
                    "attachment_count"
                ],
        }

        for row in rows
    ]

@app.get(
    "/api/community/player-photo-requests/{post_id}"
)
def get_player_photo_request(
    post_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    cp.id,
                    cp.board_type,
                    cp.title,
                    cp.content,
                    cp.author_name,
                    cp.created_at,
                    cp.updated_at,

                    ppr.player_name,
                    ppr.season_name,
                    ppr.sp_id,
                    ppr.request_status,
                    ppr.admin_note,
                    ppr.completed_at

                FROM community_posts cp

                INNER JOIN player_photo_requests ppr
                    ON ppr.post_id = cp.id

                WHERE
                    cp.id = %s
                    AND
                    cp.board_type = 'player_photo_request'
                """,
                (
                    post_id,
                ),
            )

            row = cursor.fetchone()


            if not row:

                raise HTTPException(
                    status_code=404,
                    detail="선수 사진 요청을 찾을 수 없습니다.",
                )


            attachments = (
                get_community_post_attachments(
                    cursor,
                    post_id,
                )
            )


    return {
        "id":
            row["id"],

        "board_type":
            row["board_type"],

        "title":
            row["title"],

        "content":
            row["content"],

        "author_name":
            row["author_name"],

        "created_at":
            row[
                "created_at"
            ].isoformat(),

        "updated_at":
            row[
                "updated_at"
            ].isoformat(),

        "player_name":
            row["player_name"],

        "season_name":
            row["season_name"],

        "sp_id":
            row["sp_id"],

        "request_status":
            row[
                "request_status"
            ],

        "admin_note":
            row["admin_note"],

        "completed_at":
            (
                row[
                    "completed_at"
                ].isoformat()

                if row[
                    "completed_at"
                ]

                else None
            ),

        "attachments":
            attachments,
    }

@app.patch(
    "/api/admin/community/player-photo-requests/{post_id}"
)
def update_admin_player_photo_request(
    post_id: int,
    payload: dict,
    _admin=Depends(require_admin),
):

    request_status = str(
        payload.get(
            "request_status",
            ""
        )
    ).strip()

    admin_note = str(
        payload.get(
            "admin_note",
            ""
        )
    ).strip()


    allowed_statuses = {
        "pending",
        "in_progress",
        "completed",
        "rejected",
    }


    if (
        request_status
        not in allowed_statuses
    ):

        raise HTTPException(
            status_code=400,
            detail="올바르지 않은 처리 상태입니다.",
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE player_photo_requests

                SET
                    request_status = %s,
                    admin_note = %s,
                    completed_at =
                        CASE
                            WHEN %s = 'completed'
                            THEN COALESCE(
                                completed_at,
                                NOW()
                            )
                            ELSE NULL
                        END

                WHERE post_id = %s

                RETURNING
                    post_id,
                    player_name,
                    season_name,
                    sp_id,
                    request_status,
                    admin_note,
                    completed_at
                """,
                (
                    request_status,
                    (
                        admin_note
                        if admin_note
                        else None
                    ),
                    request_status,
                    post_id,
                ),
            )

            row = cursor.fetchone()


            if not row:

                raise HTTPException(
                    status_code=404,
                    detail="선수 사진 요청을 찾을 수 없습니다.",
                )


        connection.commit()


    return {
        "post_id":
            row["post_id"],

        "player_name":
            row["player_name"],

        "season_name":
            row["season_name"],

        "sp_id":
            row["sp_id"],

        "request_status":
            row[
                "request_status"
            ],

        "admin_note":
            row["admin_note"],

        "completed_at":
            (
                row[
                    "completed_at"
                ].isoformat()

                if row[
                    "completed_at"
                ]

                else None
            ),
    }

# =========================
# COMMUNITY ATTACHMENTS
# =========================

@app.post(
    "/api/community/posts/{post_id}/attachments"
)
async def upload_community_attachments(
    post_id: int,
    files: list[UploadFile] = File(...),
):

    if len(files) > 5:

        raise HTTPException(
            status_code=400,
            detail="이미지는 최대 5장까지 첨부할 수 있습니다.",
        )


    allowed_content_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    }


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT id

                FROM community_posts

                WHERE id = %s
                """,
                (
                    post_id,
                ),
            )


            post_row = cursor.fetchone()


            if not post_row:

                raise HTTPException(
                    status_code=404,
                    detail="게시글을 찾을 수 없습니다.",
                )


            cursor.execute(
                """
                SELECT COUNT(*) AS count

                FROM community_attachments

                WHERE post_id = %s
                """,
                (
                    post_id,
                ),
            )


            attachment_count = int(
                    cursor.fetchone()["count"]
                )


            if (
                attachment_count
                + len(files)
                > 5
            ):

                raise HTTPException(
                    status_code=400,
                    detail="게시글당 이미지는 최대 5장까지 첨부할 수 있습니다.",
                )


            uploaded_attachments = []


            for index, upload_file in enumerate(
                files,
                start=attachment_count,
            ):

                if (
                    upload_file.content_type
                    not in allowed_content_types
                ):

                    raise HTTPException(
                        status_code=400,
                        detail="지원하지 않는 이미지 형식입니다.",
                    )


                image_data = await upload_file.read()


                if len(image_data) > 5 * 1024 * 1024:

                    raise HTTPException(
                        status_code=400,
                        detail="이미지 한 장의 최대 크기는 5MB입니다.",
                    )


                cursor.execute(
                    """
                    INSERT INTO community_attachments (
                        post_id,
                        original_file_name,
                        content_type,
                        image_data,
                        sort_order
                    )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )

                    RETURNING
                        id,
                        original_file_name,
                        content_type,
                        sort_order
                    """,
                    (
                        post_id,
                        upload_file.filename
                        or "image",
                        upload_file.content_type,
                        image_data,
                        index,
                    ),
                )


                attachment_row = cursor.fetchone()


                uploaded_attachments.append(
                    {
                        "id":
                            attachment_row["id"],

                        "original_file_name":
                            attachment_row[
                                "original_file_name"
                            ],

                        "content_type":
                            attachment_row[
                                "content_type"
                            ],

                        "sort_order":
                            attachment_row[
                                "sort_order"
                            ],

                        "image_url":
                            (
                                "/api/community/"
                                "attachments/"
                                f"{attachment_row['id']}"
                            ),
                    }
                )


        connection.commit()


    return {
        "post_id":
            post_id,

        "attachments":
            uploaded_attachments,
    }

@app.get(
    "/api/community/attachments/{attachment_id}"
)
def get_community_attachment(
    attachment_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    content_type,
                    image_data

                FROM community_attachments

                WHERE id = %s
                """,
                (
                    attachment_id,
                ),
            )


            row = cursor.fetchone()


    if not row:

        raise HTTPException(
            status_code=404,
            detail="첨부 이미지를 찾을 수 없습니다.",
        )


    return Response(
        content=bytes(
            row["image_data"]
        ),
        media_type=row["content_type"],
    )


@app.get(
    "/api/player-database/filters"
)
def get_player_database_filters():

    return (
        get_player_catalog_filter_options()
    )

# =========================================
# QUICK SQUAD - OFFICIAL FORMATIONS
# =========================================

FCONLINE_FORMATION_SOURCE_URL = (
    "https://fconline.nexon.com/"
    "datacenter/rank?rt=1vs1"
)


FCONLINE_FORMATION_CACHE_SECONDS = (
    6
    *
    60
    *
    60
)


fconline_formation_cache = {
    "expires_at":
        0.0,

    "formations":
        [],
}


FCONLINE_FORMATION_FALLBACK = [
    # =============================
    # 3 BACK
    # =============================

    "3-4-3",
    "3-4-3(2)",
    "3-4-1-2",
    "3-2-3-2",
    "3-2-2-1-2",
    "3-1-2-1-3",
    "3-1-4-2",

    # =============================
    # 4 BACK
    # =============================

    "4-5-1",
    "4-4-2",
    "4-4-2(2)",
    "4-4-1-1",
    "4-3-3",
    "4-3-3(2)",
    "4-3-2-1",
    "4-3-1-2",
    "4-2-4",
    "4-2-3-1",
    "4-2-2-2",
    "4-2-2-2(2)",
    "4-2-2-1-1",
    "4-2-1-3",
    "4-2-1-3(2)",
    "4-1-4-1",
    "4-1-3-2",
    "4-1-2-3",
    "4-1-2-3(2)",
    "4-1-2-1-2",
    "4-1-2-1-2(2)",

    # =============================
    # 5 BACK
    # =============================

    "5-4-1",
    "5-3-2",
    "5-2-3",
    "5-2-1-2",
    "5-1-2-1-1",
]


FCONLINE_FORMATION_PATTERN = (
    re.compile(
        (
            r"^[345]"
            r"(?:-[1-5]){2,4}"
            r"(?:\(2\))?$"
        )
    )
)


def get_fconline_official_formations():

    current_time = (
        time.time()
    )


    cached_formations = (
        fconline_formation_cache[
            "formations"
        ]
    )


    if (
        cached_formations
        and
        current_time
        <
        fconline_formation_cache[
            "expires_at"
        ]
    ):

        return {
            "formations":
                cached_formations,

            "live":
                True,
        }


    try:

        response = httpx.get(
            FCONLINE_FORMATION_SOURCE_URL,

            headers={
                "User-Agent":
                    (
                        "Mozilla/5.0 "
                        "(Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 "
                        "(KHTML, like Gecko) "
                        "Chrome/150.0.0.0 Safari/537.36"
                    ),

                "Referer":
                    "https://fconline.nexon.com/",
            },

            timeout=20.0,

            follow_redirects=True,
        )


        response.raise_for_status()


        html = (
            response.text
        )


        # =================================
        # FC Online 페이지 원본에서
        # 포메이션 문자열 직접 추출
        #
        # 화면 텍스트뿐 아니라
        # HTML / script 데이터 안에 있어도 찾음
        # =================================

        formation_matches = (
            re.findall(
                (
                    r"(?<![\d-])"
                    r"[345]"
                    r"(?:-[1-5]){2,4}"
                    r"(?:\(2\))?"
                    r"(?![\d-])"
                ),
                html,
            )
        )


        found_formations = []

        seen_formations = set()


        for raw_formation in (
            formation_matches
        ):

            formation = (
                str(
                    raw_formation
                )
                .strip()
            )


            if not (
                FCONLINE_FORMATION_PATTERN
                .fullmatch(
                    formation
                )
            ):

                continue


            base_formation = (
                formation
                .replace(
                    "(2)",
                    "",
                )
            )


            formation_numbers = [
                int(
                    value
                )

                for value
                in base_formation
                    .split(
                        "-"
                    )
            ]


            # GK를 제외한 필드 플레이어 10명
            if (
                sum(
                    formation_numbers
                )
                != 10
            ):

                continue


            if (
                formation
                in seen_formations
            ):

                continue


            seen_formations.add(
                formation
            )


            found_formations.append(
                formation
            )


        # =================================
        # 데이터센터 구조가 바뀐 경우
        # 잘못된 일부 목록을 사용하지 않음
        # =================================

        if (
            len(
                found_formations
            )
            < 20
        ):

            raise RuntimeError(
                (
                    "FC Online 포메이션 목록을 "
                    "정상적으로 확인하지 못했습니다."
                )
            )


        # =================================
        # 3 / 4 / 5 BACK 순서
        # =================================

        formations = []


        for back_count in (
            3,
            4,
            5,
        ):

            formations.extend(
                [
                    formation

                    for formation
                    in found_formations

                    if formation.startswith(
                        f"{back_count}-"
                    )
                ]
            )


        fconline_formation_cache[
            "formations"
        ] = formations


        fconline_formation_cache[
            "expires_at"
        ] = (
            current_time
            +
            FCONLINE_FORMATION_CACHE_SECONDS
        )


        return {
            "formations":
                formations,

            "live":
                True,
        }


    except Exception as error:

        print(
            (
                "[QUICK SQUAD] "
                "formation fetch failed:"
            ),
            error,
        )


        return {
            "formations":
                FCONLINE_FORMATION_FALLBACK,

            "live":
                False,
        }


@app.get(
    "/api/quick-squad/formations"
)
def get_quick_squad_formations():

    formation_data = (
        get_fconline_official_formations()
    )


    formations = (
        formation_data[
            "formations"
        ]
    )


    return {
        "count":
            len(
                formations
            ),

        "formations":
            [
                {
                    "name":
                        formation,

                    "back_count":
                        int(
                            formation[
                                0
                            ]
                        ),
                }

                for formation
                in formations
            ],

        "source":
            "FC Online DataCenter",

        "live":
            formation_data[
                "live"
            ],
    }

# =========================================
# QUICK SQUAD - RECOMMEND
# =========================================

# =========================================
# FC ONLINE 대표팀 급여
# 공식 스쿼드 메이커 기준
# =========================================

QUICK_SQUAD_SALARY_CAP = 310

QUICK_SQUAD_ENHANCEMENT_BONUS = {
    1: 0,
    2: 1,
    3: 2,
    4: 4,
    5: 6,
    6: 8,
    7: 11,
    8: 15,
    9: 17,
    10: 19,
    11: 21,
    12: 24,
    13: 27,
}

# =========================================
# QUICK SQUAD 강화 추천 정책
# =========================================

# 일반 추천에서는 1강 ~ 8강까지만 사용
QUICK_SQUAD_PRIMARY_MAX_GRADE = 8


# 9강 이상은 최종 잔여 예산 처리 때만 허용
QUICK_SQUAD_HIGH_GRADE_MIN = 9


# 한 스쿼드에서 9강 이상 선수 최대 인원
QUICK_SQUAD_MAX_HIGH_GRADE_PLAYERS = 2


QUICK_SQUAD_POSITION_CANDIDATES = {

    # =====================================
    # GK
    # =====================================

    "GK": [
        "GK",
    ],


    # =====================================
    # DEFENDER
    # =====================================

    "LB": [
        "LB",
        "LWB",
    ],

    "LWB": [
        "LWB",
        "LB",
    ],

    "RB": [
        "RB",
        "RWB",
    ],

    "RWB": [
        "RWB",
        "RB",
    ],

    "CB": [
        "CB",
    ],

    "LCB": [
        "CB",
    ],

    "RCB": [
        "CB",
    ],


    # =====================================
    # MIDFIELDER
    # =====================================

    "CDM": [
        "CDM",
        "CM",
    ],

    "LDM": [
        "CDM",
        "CM",
    ],

    "RDM": [
        "CDM",
        "CM",
    ],


    "CM": [
        "CM",
        "CDM",
        "CAM",
    ],

    "LCM": [
        "CM",
        "CDM",
        "CAM",
    ],

    "RCM": [
        "CM",
        "CDM",
        "CAM",
    ],


    "CAM": [
        "CAM",
        "CF",
        "CM",
    ],

    "LAM": [
        "CAM",
        "LW",
        "LM",
    ],

    "RAM": [
        "CAM",
        "RW",
        "RM",
    ],


    "LM": [
        "LM",
        "LW",
        "CM",
    ],

    "RM": [
        "RM",
        "RW",
        "CM",
    ],


    # =====================================
    # ATTACKER
    # =====================================

    "LW": [
        "LW",
        "LM",
        "CF",
    ],

    "RW": [
        "RW",
        "RM",
        "CF",
    ],


    "CF": [
        "CF",
        "ST",
        "CAM",
    ],


    "ST": [
        "ST",
        "CF",
    ],

    "LS": [
        "ST",
        "CF",
    ],

    "RS": [
        "ST",
        "CF",
    ],
}

QUICK_SQUAD_POPULARITY_POSITION_MAP = {
    "LS": "ST",
    "RS": "ST",

    "LF": "CF",
    "RF": "CF",

    "LAM": "CAM",
    "RAM": "CAM",

    "LCM": "CM",
    "RCM": "CM",

    "LDM": "CDM",
    "RDM": "CDM",

    "LCB": "CB",
    "RCB": "CB",
    "SW": "CB",
}


def get_quick_squad_popularity_position(
    slot,
):

    normalized = (
        str(
            slot
        )
        .strip()
        .upper()
    )

    return (
        QUICK_SQUAD_POPULARITY_POSITION_MAP
        .get(
            normalized,
            normalized,
        )
    )

QUICK_SQUAD_PRICE_CACHE_SECONDS = (
    20
    *
    60
)


quick_squad_price_cache = {}



class QuickSquadRecommendRequest(BaseModel):
    team_color_id: int
    budget_bp: int
    formation: str
    slots: list[str]

    enhancement_grade: int | None = Field(
        default=None,
        ge=1,
        le=13,
        strict=True,
    )

    locked_players: list[LockedPlayerInput] = Field(
        default_factory=list,
        max_length=11,
    )

    # 기존 API 요청은 이전 추천 방식을 유지한다.
    budget_mode: Literal[
        "legacy",
        "balanced",
        "core",
    ] = "legacy"

    core_strength: int = Field(
        default=200,
        ge=100,
        le=300,
        strict=True,
    )

    recommendation_mode: Literal[
        "meta",
        "performance",
        "value",
    ] = "meta"

# =========================================
# QUICK SQUAD
# TEAM COLOR RECALCULATION
# =========================================

class QuickSquadTeamColorRecalculatePlayer(
    BaseModel
):

    sp_id: int = Field(
        gt=0,
        strict=True,
    )

    grade: int = Field(
        ge=1,
        le=13,
        strict=True,
    )


class QuickSquadTeamColorRecalculateRequest(
    BaseModel
):

    team_color_id: int = Field(
        gt=0,
        strict=True,
    )

    players: list[
        QuickSquadTeamColorRecalculatePlayer
    ] = Field(
        default_factory=list,
        max_length=11,
    )

def get_quick_squad_cached_prices(
    sp_id: int,
):
    numeric_sp_id = int(sp_id)
    current_time = time.time()

    cached_item = quick_squad_price_cache.get(
        numeric_sp_id
    )

    if (
        cached_item
        and current_time < cached_item["expires_at"]
    ):
        return cached_item["prices"]

    prices = get_fconline_player_market_prices(
        numeric_sp_id
    )

    # 만료된 캐시부터 정리
    expired_keys = [
        key
        for key, item in quick_squad_price_cache.items()
        if current_time >= item["expires_at"]
    ]

    for key in expired_keys:
        quick_squad_price_cache.pop(key, None)

    # 메모리 캐시는 최대 512명분만 유지
    if len(quick_squad_price_cache) >= 512:
        oldest_key = min(
            quick_squad_price_cache,
            key=lambda key: (
                quick_squad_price_cache[key]["expires_at"]
            ),
        )

        quick_squad_price_cache.pop(
            oldest_key,
            None,
        )

    quick_squad_price_cache[numeric_sp_id] = {
        "expires_at": (
            current_time
            + QUICK_SQUAD_PRICE_CACHE_SECONDS
        ),
        "prices": prices,
    }

    return prices


def is_valid_quick_squad_market_prices(
    prices,
):

    valid_prices = [
        int(
            item[
                "price"
            ]
        )

        for item
        in (
            prices
            or []
        )

        if (
            item.get(
                "price"
            )
            is not None

            and

            int(
                item[
                    "price"
                ]
            )
            > 0
        )
    ]


    # =====================================
    # 시세 자체가 없음
    # =====================================

    if not valid_prices:

        return False


    # =====================================
    # 강화별 가격이 전부 똑같은 경우
    #
    # 예:
    # 1강 ~ 13강 전부 43,300 BP
    #
    # 퀵 스쿼드 강화 선택에는 사용할 수 없음
    # =====================================

    unique_prices = set(
        valid_prices
    )


    if (
        len(
            unique_prices
        )
        <= 1
    ):

        return False


    # =====================================
    # 최소한 낮은 강화와 높은 강화 사이에
    # 실제 가격 변화가 있어야 함
    # =====================================

    first_price = (
        valid_prices[
            0
        ]
    )


    last_price = (
        valid_prices[
            -1
        ]
    )


    if (
        last_price
        <=
        first_price
    ):

        return False


    return True

def get_quick_squad_candidate_rows(
    team_color_id: int,
    slot_position: str,
    used_player_names: list[str],
    max_salary: int | None = None,
):

    normalized_slot_position = (
        str(
            slot_position
            or ""
        )
        .strip()
        .upper()
    )


    candidate_positions = (
        QUICK_SQUAD_POSITION_CANDIDATES
        .get(
            normalized_slot_position,
            [
                normalized_slot_position,
            ],
        )
    )


    salary_sql = ""


    query_parameters = [
        candidate_positions,
        int(
            team_color_id
        ),
    ]


    if (
        max_salary
        is not None
    ):

        salary_sql = (
            """
            AND
                COALESCE(
                    p.salary,
                    0
                )
                <=
                %s
            """
        )


        query_parameters.append(
            int(
                max_salary
            )
        )


    used_player_sql = ""


    if used_player_names:

        used_player_sql = (
            """
            AND
                NOT (
                    p.player_name
                    =
                    ANY(%s)
                )
            """
        )


        query_parameters.append(
            used_player_names
        )


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                WITH top_candidates AS (

                    SELECT
                        p.sp_id,
                        p.player_name,
                        p.season_id,
                        p.image_url,
                        p.position,
                        p.salary,
                        p.ovr

                    FROM
                        fconline_players AS p

                    WHERE
                        p.position
                        =
                        ANY(%s)

                    AND
                        EXISTS (

                            SELECT
                                1

                            FROM
                                fconline_player_teams
                                AS team_filter

                            WHERE
                                team_filter.sp_id
                                =
                                p.sp_id

                            AND
                                team_filter.team_color_id
                                =
                                %s

                        )

                    {salary_sql}

                    {used_player_sql}

                    ORDER BY
                        p.ovr DESC,
                        p.salary DESC,
                        p.sp_id DESC

                    LIMIT 100

                )

                SELECT
                    *

                FROM
                    top_candidates

                ORDER BY
                    ovr DESC,
                    RANDOM()

                LIMIT 8
                """,
                query_parameters,
            )


            return (
                cursor.fetchall()
            )

def get_quick_squad_team_name(
    team_color_id: int,
):

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    team_name

                FROM
                    fconline_player_teams

                WHERE
                    team_color_id = %s

                AND
                    team_name IS NOT NULL

                AND
                    team_name <> ''

                LIMIT 1
                """,
                (
                    int(
                        team_color_id
                    ),
                ),
            )


            row = (
                cursor.fetchone()
            )


    if not row:

        return ""


    return (
        row[
            "team_name"
        ]
        or ""
    )

def choose_quick_squad_candidate(
    team_color_id: int,
    slot_position: str,
    target_budget: int,
    remaining_budget: int,
    max_salary: int,
    used_player_names: list[str],
):

    candidate_rows = (
        get_quick_squad_candidate_rows(
            team_color_id=
                team_color_id,

            slot_position=
                slot_position,

            used_player_names=
                used_player_names,

            max_salary=
                max_salary,
        )
    )


    all_options = []


    for candidate_row in (
        candidate_rows
    ):

        sp_id = int(
            candidate_row[
                "sp_id"
            ]
        )


        try:

            prices = (
                get_quick_squad_cached_prices(
                    sp_id
                )
            )

        except Exception as error:

            print(
                (
                    "[QUICK SQUAD] "
                    "price fetch failed:"
                ),
                sp_id,
                error,
            )

            continue


        if not (
            is_valid_quick_squad_market_prices(
                prices
            )
        ):

            continue


        base_ovr = int(
            candidate_row[
                "ovr"
            ]
            or 0
        )


        for price_data in (
            prices
        ):

            raw_price = (
                price_data.get(
                    "price"
                )
            )


            if (
                raw_price
                is None
            ):

                continue


            price = int(
                raw_price
            )


            if (
                price <= 0
                or
                price > remaining_budget
            ):

                continue


            grade = int(
                price_data[
                    "grade"
                ]
            )


            # =================================
            # 일반 추천은 최대 +8까지만
            # =================================

            if (
                grade
                >
                QUICK_SQUAD_PRIMARY_MAX_GRADE
            ):

                continue


            adjusted_ovr = (
                base_ovr
                +
                QUICK_SQUAD_ENHANCEMENT_BONUS
                .get(
                    grade,
                    0,
                )
            )


            all_options.append(
                {
                    "slot_position":
                        slot_position,

                    "sp_id":
                        sp_id,

                    "player_name":
                        candidate_row[
                            "player_name"
                        ],

                    "season_id":
                        int(
                            candidate_row[
                                "season_id"
                            ]
                        ),

                    "image_url":
                        (
                            candidate_row[
                                "image_url"
                            ]
                            or ""
                        ),

                    "position":
                        (
                            candidate_row[
                                "position"
                            ]
                            or ""
                        ),

                    "salary":
                        int(
                            candidate_row[
                                "salary"
                            ]
                            or 0
                        ),

                    "base_ovr":
                        base_ovr,

                    "grade":
                        grade,

                    "ovr":
                        adjusted_ovr,

                    "price":
                        price,
                }
            )


    if not all_options:

        return None


    # =====================================
    # 1. 자리별 목표 예산 안에 들어오는 후보
    # =====================================

    target_options = [
        option

        for option
        in all_options

        if (
            option[
                "price"
            ]
            <=
            target_budget
        )
    ]


    if target_options:

        # =================================
        # 강화 OVR이 아니라
        # 기본 카드 OVR을 기준으로
        # 좋은 시즌부터 추림
        # =================================

        best_base_ovr = max(
            option[
                "base_ovr"
            ]

            for option
            in target_options
        )


        # =================================
        # 최고 기본 OVR과 2 이내면
        # 충분히 경쟁력 있는 카드로 인정
        # =================================

        quality_floor = (
            best_base_ovr
            -
            1
        )


        quality_options = [
            option

            for option
            in target_options

            if (
                option[
                    "base_ovr"
                ]
                >=
                quality_floor
            )
        ]


        # =================================
        # 좋은 시즌들 중
        # 목표 예산에 가장 가깝게 사용
        #
        # 여기서 자연스럽게
        # +1 / +5 / +8 / +12 / +13 등이 섞임
        # =================================

        return max(
            quality_options,

            key=lambda option: (
                option[
                    "price"
                ],

                option[
                    "base_ovr"
                ],

                option[
                    "ovr"
                ],
            ),
        )


    # =====================================
    # 목표 예산보다 싼 카드가 하나도 없다면
    # 전체 남은 예산 내에서 가장 싼 카드로
    # 일단 11명을 완성
    # =====================================

    return min(
        all_options,

        key=lambda option: (
            option[
                "price"
            ],

            -
            option[
                "base_ovr"
            ],
        ),
    )

def choose_quick_squad_upgrade(
    team_color_id: int,
    current_player: dict,
    upgrade_budget: int,
    max_salary: int,
    excluded_player_names: list[str],
):

    slot_position = (
        current_player[
            "slot_position"
        ]
    )


    current_price = int(
        current_player[
            "price"
        ]
    )


    current_ovr = int(
        current_player[
            "ovr"
        ]
    )


    current_base_ovr = int(
        current_player[
            "base_ovr"
        ]
    )


    max_total_price = (
        current_price
        +
        upgrade_budget
    )


    candidate_rows = (
        get_quick_squad_candidate_rows(
            team_color_id=
                team_color_id,

            slot_position=
                slot_position,

            used_player_names=
                excluded_player_names,

            max_salary=
                max_salary,
        )
    )


    upgrade_options = []


    for candidate_row in (
        candidate_rows
    ):

        sp_id = int(
            candidate_row[
                "sp_id"
            ]
        )


        try:

            prices = (
                get_quick_squad_cached_prices(
                    sp_id
                )
            )

        except Exception as error:

            print(
                (
                    "[QUICK SQUAD] "
                    "upgrade price fetch failed:"
                ),
                sp_id,
                error,
            )

            continue


        if not (
            is_valid_quick_squad_market_prices(
                prices
            )
        ):

            continue


        base_ovr = int(
            candidate_row[
                "ovr"
            ]
            or 0
        )


        for price_data in (
            prices
        ):

            raw_price = (
                price_data.get(
                    "price"
                )
            )


            if (
                raw_price
                is None
            ):

                continue


            price = int(
                raw_price
            )


            # =================================
            # 실제로 돈을 더 쓰는 교체만
            # =================================

            if (
                price <= current_price
                or
                price > max_total_price
            ):

                continue


            grade = int(
                price_data[
                    "grade"
                ]
            )

            if (
                grade
                >
                QUICK_SQUAD_PRIMARY_MAX_GRADE
            ):

                continue

            adjusted_ovr = (
                base_ovr
                +
                QUICK_SQUAD_ENHANCEMENT_BONUS
                .get(
                    grade,
                    0,
                )
            )


            # =================================
            # 교체 후 OVR이 내려가는 건 제외
            # =================================

            if (
                adjusted_ovr
                <
                current_ovr
            ):

                continue


            upgrade_options.append(
                {
                    "slot_position":
                        slot_position,

                    "sp_id":
                        sp_id,

                    "player_name":
                        candidate_row[
                            "player_name"
                        ],

                    "season_id":
                        int(
                            candidate_row[
                                "season_id"
                            ]
                        ),

                    "image_url":
                        (
                            candidate_row[
                                "image_url"
                            ]
                            or ""
                        ),

                    "position":
                        (
                            candidate_row[
                                "position"
                            ]
                            or ""
                        ),

                    "salary":
                        int(
                            candidate_row[
                                "salary"
                            ]
                            or 0
                        ),

                    "base_ovr":
                        base_ovr,

                    "grade":
                        grade,

                    "ovr":
                        adjusted_ovr,

                    "price":
                        price,

                    "extra_cost":
                        (
                            price
                            -
                            current_price
                        ),
                }
            )


    if not upgrade_options:

        return None


    # =====================================
    # 현재 카드보다 기본 OVR이 떨어지는
    # 구시즌 +고강 카드 남발 방지
    # =====================================

    better_base_options = [
        option

        for option
        in upgrade_options

        if (
            option[
                "base_ovr"
            ]
            >=
            current_base_ovr
        )
    ]


    if better_base_options:

        upgrade_options = (
            better_base_options
        )


    best_base_ovr = max(
        option[
            "base_ovr"
        ]

        for option
        in upgrade_options
    )


    quality_floor = (
        best_base_ovr
        -
        1
    )


    quality_options = [
        option

        for option
        in upgrade_options

        if (
            option[
                "base_ovr"
            ]
            >=
            quality_floor
        )
    ]


    # =====================================
    # 품질이 비슷한 카드들 중
    # 이번에 사용할 수 있는 돈을 최대한 사용
    # =====================================

    return max(
        quality_options,

        key=lambda option: (
            option[
                "price"
            ],

            option[
                "base_ovr"
            ],

            option[
                "ovr"
            ],
        ),
    )

def maximize_quick_squad_grade_budget(
    selected_players: list[dict],
    remaining_budget: int,
):

    # =====================================
    # +1 ~ +8 범위에서
    # 남은 예산 최대한 사용
    # =====================================

    max_upgrade_steps = 100


    for _ in range(
        max_upgrade_steps
    ):

        if (
            remaining_budget
            <= 0
        ):

            break


        best_upgrade = None


        # =================================
        # 현재 11명 모두 검사
        # =================================

        for (
            player_index,
            player
        ) in enumerate(
            selected_players
        ):

            sp_id = int(
                player[
                    "sp_id"
                ]
            )


            current_grade = int(
                player[
                    "grade"
                ]
            )


            current_price = int(
                player[
                    "price"
                ]
            )


            base_ovr = int(
                player[
                    "base_ovr"
                ]
            )


            try:

                prices = (
                    get_quick_squad_cached_prices(
                        sp_id
                    )
                )

            except Exception as error:

                print(
                    (
                        "[QUICK SQUAD] "
                        "grade upgrade price fetch failed:"
                    ),
                    sp_id,
                    error,
                )

                continue


            if not (
                is_valid_quick_squad_market_prices(
                    prices
                )
            ):

                continue


            for price_data in (
                prices
            ):

                grade = int(
                    price_data[
                        "grade"
                    ]
                )


                # =================================
                # 일반 강화 최적화는
                # 최대 +8까지만
                # =================================

                if (
                    grade
                    >
                    QUICK_SQUAD_PRIMARY_MAX_GRADE
                ):

                    continue


                # =================================
                # 현재 강화보다 높은 단계만
                # =================================

                if (
                    grade
                    <=
                    current_grade
                ):

                    continue


                raw_price = (
                    price_data.get(
                        "price"
                    )
                )


                if (
                    raw_price
                    is None
                ):

                    continue


                price = int(
                    raw_price
                )


                if (
                    price
                    <=
                    current_price
                ):

                    continue


                extra_cost = (
                    price
                    -
                    current_price
                )


                if (
                    extra_cost
                    >
                    remaining_budget
                ):

                    continue


                adjusted_ovr = (
                    base_ovr
                    +
                    QUICK_SQUAD_ENHANCEMENT_BONUS
                    .get(
                        grade,
                        0,
                    )
                )


                candidate = {
                    "player_index":
                        player_index,

                    "grade":
                        grade,

                    "price":
                        price,

                    "ovr":
                        adjusted_ovr,

                    "extra_cost":
                        extra_cost,
                }


                # =================================
                # 남은 BP를 가장 많이 사용하는
                # 업그레이드 우선
                # =================================

                if (
                    best_upgrade
                    is None

                    or

                    candidate[
                        "extra_cost"
                    ]
                    >
                    best_upgrade[
                        "extra_cost"
                    ]
                ):

                    best_upgrade = (
                        candidate
                    )


        if (
            best_upgrade
            is None
        ):

            break


        player_index = int(
            best_upgrade[
                "player_index"
            ]
        )


        selected_players[
            player_index
        ][
            "grade"
        ] = int(
            best_upgrade[
                "grade"
            ]
        )


        selected_players[
            player_index
        ][
            "price"
        ] = int(
            best_upgrade[
                "price"
            ]
        )


        selected_players[
            player_index
        ][
            "ovr"
        ] = int(
            best_upgrade[
                "ovr"
            ]
        )


        remaining_budget -= int(
            best_upgrade[
                "extra_cost"
            ]
        )


    return (
        remaining_budget
    )

def maximize_quick_squad_high_grade_budget(
    selected_players: list[dict],
    remaining_budget: int,
):

    high_grade_player_indexes = set()


    # =====================================
    # 혹시 이미 9강 이상이 있다면 카운트
    # =====================================

    for (
        player_index,
        player
    ) in enumerate(
        selected_players
    ):

        if (
            int(
                player[
                    "grade"
                ]
            )
            >=
            QUICK_SQUAD_HIGH_GRADE_MIN
        ):

            high_grade_player_indexes.add(
                player_index
            )


    while (
        remaining_budget
        >
        0
        and
        len(
            high_grade_player_indexes
        )
        <
        QUICK_SQUAD_MAX_HIGH_GRADE_PLAYERS
    ):

        best_upgrade = None


        for (
            player_index,
            player
        ) in enumerate(
            selected_players
        ):

            # =================================
            # 이미 고강화 담당이 된 선수는
            # 다시 선택하지 않음
            # =================================

            if (
                player_index
                in
                high_grade_player_indexes
            ):

                continue


            sp_id = int(
                player[
                    "sp_id"
                ]
            )


            current_grade = int(
                player[
                    "grade"
                ]
            )


            current_price = int(
                player[
                    "price"
                ]
            )


            base_ovr = int(
                player[
                    "base_ovr"
                ]
            )


            try:

                prices = (
                    get_quick_squad_cached_prices(
                        sp_id
                    )
                )

            except Exception:

                continue


            if not (
                is_valid_quick_squad_market_prices(
                    prices
                )
            ):

                continue


            for price_data in (
                prices
            ):

                grade = int(
                    price_data[
                        "grade"
                    ]
                )


                # =================================
                # 여기서만 +9 ~ +13 허용
                # =================================

                if (
                    grade
                    <
                    QUICK_SQUAD_HIGH_GRADE_MIN
                ):

                    continue


                if (
                    grade
                    <=
                    current_grade
                ):

                    continue


                raw_price = (
                    price_data.get(
                        "price"
                    )
                )


                if (
                    raw_price
                    is None
                ):

                    continue


                price = int(
                    raw_price
                )


                if (
                    price
                    <=
                    current_price
                ):

                    continue


                extra_cost = (
                    price
                    -
                    current_price
                )


                if (
                    extra_cost
                    >
                    remaining_budget
                ):

                    continue


                adjusted_ovr = (
                    base_ovr
                    +
                    QUICK_SQUAD_ENHANCEMENT_BONUS
                    .get(
                        grade,
                        0,
                    )
                )


                candidate = {
                    "player_index":
                        player_index,

                    "grade":
                        grade,

                    "price":
                        price,

                    "ovr":
                        adjusted_ovr,

                    "extra_cost":
                        extra_cost,
                }


                # =================================
                # 남은 BP를 가장 많이 사용하는
                # 강화 선택
                # =================================

                if (
                    best_upgrade
                    is None

                    or

                    candidate[
                        "extra_cost"
                    ]
                    >
                    best_upgrade[
                        "extra_cost"
                    ]
                ):

                    best_upgrade = (
                        candidate
                    )


        if (
            best_upgrade
            is None
        ):

            break


        player_index = int(
            best_upgrade[
                "player_index"
            ]
        )


        selected_players[
            player_index
        ][
            "grade"
        ] = int(
            best_upgrade[
                "grade"
            ]
        )


        selected_players[
            player_index
        ][
            "price"
        ] = int(
            best_upgrade[
                "price"
            ]
        )


        selected_players[
            player_index
        ][
            "ovr"
        ] = int(
            best_upgrade[
                "ovr"
            ]
        )


        remaining_budget -= int(
            best_upgrade[
                "extra_cost"
            ]
        )


        high_grade_player_indexes.add(
            player_index
        )


    return (
        remaining_budget
    )

# =========================================
# QUICK SQUAD - FIXED ENHANCEMENT
# =========================================

def get_fixed_quick_squad_candidate_rows(
    team_color_id: int,
    slots: list[str],
    per_salary_limit: int = 5,
    total_limit: int = 600,
):
    """
    팀컬러와 포지션에 맞는 여러 시즌을 수집한다.
    기존 자동 추천의 LIMIT 8 대신
    급여 구간별로 후보를 확보한다.
    """

    positions = sorted({
        position
        for slot in slots
        for position in (
            QUICK_SQUAD_POSITION_CANDIDATES.get(
                slot,
                [slot],
            )
        )
    })

    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH ranked AS (
                    SELECT
                        p.sp_id,
                        p.player_name,
                        p.season_id,
                        p.image_url,
                        p.position,
                        p.salary,
                        p.ovr,
                        ROW_NUMBER() OVER (
                            PARTITION BY
                                p.position,
                                p.salary
                            ORDER BY
                                p.ovr DESC,
                                p.sp_id DESC
                        ) AS salary_rank
                    FROM fconline_players AS p
                    WHERE p.position = ANY(%s)
                    AND COALESCE(p.salary, 0)
                        BETWEEN 1 AND %s
                    AND COALESCE(p.ovr, 0) > 0
                    AND EXISTS (
                        SELECT 1
                        FROM fconline_player_teams AS t
                        WHERE t.sp_id = p.sp_id
                        AND t.team_color_id = %s
                    )
                )
                SELECT
                    sp_id,
                    player_name,
                    season_id,
                    image_url,
                    position,
                    salary,
                    ovr
                FROM ranked
                WHERE salary_rank <= %s
                ORDER BY
                    ovr DESC,
                    sp_id DESC
                LIMIT %s
                """,
                (
                    positions,
                    QUICK_SQUAD_SALARY_CAP - 10,
                    team_color_id,
                    per_salary_limit,
                    total_limit,
                ),
            )

            return cursor.fetchall()

def get_budget_quick_squad_candidate_rows(
    team_color_id: int,
    slots: list[str],
    per_salary_limit: int = 2,
    total_limit: int = 48,
):
    """
    예산 배분용 후보 수집.

    기존:
    - 급여 구간별 고 OVR
    - 급여 구간별 저 OVR

    추가:
    - 실제 FC Online 포지션별 인기 선수

    인기 선수가 OVR 사전 필터에서
    탈락하지 않도록 별도 후보 통로를 유지한다.
    """

    unique_slots = list(
        dict.fromkeys(
            str(
                slot
            )
            .strip()
            .upper()

            for slot
            in slots
        )
    )


    if not unique_slots:
        return []


    per_slot = max(
        6,

        total_limit
        //
        len(
            unique_slots
        ),
    )


    rank_limit = max(
        4,
        min(
            12,
            per_salary_limit,
        ),
    )


    # =====================================
    # 인기 후보는 자리당 최대 몇 명을
    # SQL에서 확보할지
    # =====================================

    popularity_rank_limit = max(
        2,
        min(
            8,
            per_salary_limit
            * 2,
        ),
    )


    specifications = [
        (
            index,

            QUICK_SQUAD_POSITION_CANDIDATES
            .get(
                slot,
                [
                    slot
                ],
            ),

            get_quick_squad_popularity_position(
                slot
            ),
        )

        for (
            index,
            slot,
        )
        in enumerate(
            unique_slots
        )
    ]


    placeholders = ", ".join(
        [
            (
                "("
                "%s::integer, "
                "%s::text[], "
                "%s::text"
                ")"
            )
        ]
        *
        len(
            specifications
        )
    )


    parameters = [
        value

        for specification
        in specifications

        for value
        in specification
    ]


    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                WITH requested(
                    slot_index,
                    positions,
                    popularity_position
                ) AS (

                    VALUES
                        {placeholders}
                ),

                latest_snapshot AS (

                    SELECT
                        MAX(
                            snapshot_date
                        )
                            AS snapshot_date

                    FROM
                        fconline_player_popularity
                ),

                latest_popularity AS (

                    SELECT
                        pp.sp_id,
                        pp.position,
                        pp.usage_count,
                        pp.usage_rate,
                        pp.popularity_score

                    FROM
                        fconline_player_popularity
                        AS pp

                    JOIN latest_snapshot
                        AS latest

                        ON
                            pp.snapshot_date
                            =
                            latest.snapshot_date
                ),

                eligible AS (

                    SELECT
                        r.slot_index,
                        r.popularity_position,

                        p.sp_id,
                        p.player_name,
                        p.season_id,
                        p.image_url,
                        p.position,
                        p.salary,
                        p.ovr,

                        COALESCE(
                            popularity.usage_count,
                            0
                        )
                            AS slot_usage_count,

                        COALESCE(
                            popularity.usage_rate,
                            0
                        )
                            AS slot_usage_rate,

                        COALESCE(
                            popularity.popularity_score,
                            0
                        )
                            AS slot_popularity_score,

                        CASE
                            WHEN p.salary <= 15
                                THEN 0

                            WHEN p.salary <= 22
                                THEN 1

                            WHEN p.salary <= 28
                                THEN 2

                            ELSE 3
                        END
                            AS salary_band

                    FROM
                        requested
                        AS r

                    JOIN
                        fconline_players
                        AS p

                        ON
                            p.position
                            =
                            ANY(
                                r.positions
                            )

                    LEFT JOIN
                        latest_popularity
                        AS popularity

                        ON
                            popularity.sp_id
                            =
                            p.sp_id

                            AND

                            popularity.position
                            =
                            r.popularity_position

                    WHERE
                        COALESCE(
                            p.salary,
                            0
                        )
                        BETWEEN 1 AND %s

                        AND

                        COALESCE(
                            p.ovr,
                            0
                        )
                        > 0

                        AND EXISTS (

                            SELECT
                                1

                            FROM
                                fconline_player_teams
                                AS t

                            WHERE
                                t.sp_id
                                =
                                p.sp_id

                                AND

                                t.team_color_id
                                =
                                %s
                        )
                ),

                ranked AS (

                    SELECT
                        *,

                        ROW_NUMBER() OVER (
                            PARTITION BY
                                slot_index,
                                salary_band

                            ORDER BY
                                ovr DESC,
                                sp_id DESC
                        )
                            AS best_rank,

                        ROW_NUMBER() OVER (
                            PARTITION BY
                                slot_index

                            ORDER BY
                                slot_popularity_score
                                    DESC,

                                slot_usage_count
                                    DESC,

                                ovr
                                    DESC,

                                sp_id
                                    DESC
                        )
                            AS popularity_rank

                    FROM
                        eligible
                )

                SELECT
                    slot_index,
                    popularity_position,

                    salary_band,

                    best_rank,
                    popularity_rank,

                    slot_usage_count,
                    slot_usage_rate,
                    slot_popularity_score,

                    sp_id,
                    player_name,
                    season_id,
                    image_url,
                    position,
                    salary,
                    ovr

                FROM
                    ranked

                WHERE
                    best_rank <= %s

                    OR (

                        popularity_rank <= %s

                        AND

                        slot_popularity_score > 0
                    )

                ORDER BY
                    slot_index,
                    popularity_rank,
                    salary_band,
                    best_rank
                """,
                (
                    *parameters,

                    QUICK_SQUAD_SALARY_CAP
                    - 10,

                    team_color_id,

                    rank_limit,
                    popularity_rank_limit,
                ),
            )


            rows = (
                cursor.fetchall()
            )


    # =====================================
    # 제한 상태를 슬롯 후보 선별 전에 적용
    #
    # 공급제한 / 생성제한 / ICONTMB가
    # best_rank 자리를 차지한 뒤 제거되면
    # 정상 카드가 후보군에 들어오지 못한다.
    # =====================================

    rows = attach_quick_squad_popularity(
        rows
    )


    allowed_rows = []


    for row in rows:

        candidate = dict(
            row
        )


        supply_status = (
            get_supply_restriction_status_by_season_id(
                candidate.get(
                    "season_id"
                )
            )
        )


        candidate.update(
            supply_status
        )


        generation_restricted = bool(
            candidate.get(
                "generation_restricted",
                False,
            )
        )


        supply_restricted = bool(
            candidate.get(
                "supply_restricted",
                False,
            )
        )


        class_code = (
            str(
                candidate.get(
                    "supply_restriction_class",
                    "",
                )
                or ""
            )
            .strip()
            .upper()
        )


        if (
            generation_restricted
            or
            supply_restricted
            or class_code == "ICONTMB"
        ):
            continue


        allowed_rows.append(
            candidate
        )


    rows = allowed_rows


    # =====================================
    # 슬롯별 후보 저장
    # =====================================

    groups = {
        index: {
            "popular": {},

            "best": {
                band: {}
                for band
                in range(4)
            },
        }

        for index
        in range(
            len(
                unique_slots
            )
        )
    }


    for row in rows:

        index = int(
            row[
                "slot_index"
            ]
        )

        band = int(
            row[
                "salary_band"
            ]
        )


        popularity_score = float(
            row[
                "slot_popularity_score"
            ]
            or 0
        )


        if popularity_score > 0:

            popularity_rank = int(
                row[
                    "popularity_rank"
                ]
            )

            if (
                popularity_rank
                <=
                popularity_rank_limit
            ):

                groups[
                    index
                ][
                    "popular"
                ][
                    popularity_rank
                ] = row


        if (
            int(
                row[
                    "best_rank"
                ]
            )
            <=
            rank_limit
        ):

            groups[
                index
            ][
                "best"
            ][
                band
            ][
                int(
                    row[
                        "best_rank"
                    ]
                )
            ] = row


    # =====================================
    # 슬롯별 최종 후보
    #
    # 절반 정도는 인기 후보를 우선 확보하고,
    # 나머지는 기존 OVR/저비용 다양성으로 채움
    # =====================================

    selected = {}


    for index in range(
        len(
            unique_slots
        )
    ):

        slot_selected = {}


        # 인기 후보 2자리는 보장하되,
        # 기존 4개 급여 구간의
        # 최고 OVR 후보도 모두 살려둔다.
        popularity_keep = min(
            2,

            max(
                1,
                per_slot - 4,
            ),
        )


        # =================================
        # 1. 인기 후보
        # =================================

        popular_rows = sorted(
            groups[
                index
            ][
                "popular"
            ].values(),

            key=lambda row: (
                -float(
                    row[
                        "slot_popularity_score"
                    ]
                    or 0
                ),

                -int(
                    row[
                        "ovr"
                    ]
                    or 0
                ),
            ),
        )


        for row in popular_rows[
            :popularity_keep
        ]:

            slot_selected.setdefault(
                int(
                    row[
                        "sp_id"
                    ]
                ),
                row,
            )


        # =================================
        # 2. 기존 성능 / 저비용 후보
        # =================================

        for rank in range(
            1,
            rank_limit + 1,
        ):

            for rank in range(
                1,
                rank_limit + 1,
            ):

                for band in range(4):

                    row = (
                        groups[
                            index
                        ][
                            "best"
                        ][
                            band
                        ]
                        .get(
                            rank
                        )
                    )


                    if row is None:
                        continue


                    slot_selected.setdefault(
                        int(
                            row[
                                "sp_id"
                            ]
                        ),
                        row,
                    )


                    if (
                        len(
                            slot_selected
                        )
                        >=
                        per_slot
                    ):
                        break


                if (
                    len(
                        slot_selected
                    )
                    >=
                    per_slot
                ):
                    break

                for band in range(4):

                    row = (
                        groups[
                            index
                        ][
                            "best"
                        ][
                            band
                        ]
                        .get(
                            rank
                        )
                    )


                    if row is None:
                        continue


                    slot_selected.setdefault(
                        int(
                            row[
                                "sp_id"
                            ]
                        ),
                        row,
                    )


                    if (
                        len(
                            slot_selected
                        )
                        >=
                        per_slot
                    ):
                        break


                if (
                    len(
                        slot_selected
                    )
                    >=
                    per_slot
                ):
                    break


            if (
                len(
                    slot_selected
                )
                >=
                per_slot
            ):
                break


        for row in list(
            slot_selected.values()
        )[
            :per_slot
        ]:

            selected.setdefault(
                int(
                    row[
                        "sp_id"
                    ]
                ),
                row,
            )


    # =====================================
    # 최종적으로 전체 포지션별 인기도를
    # 붙여 quick_squad_locked로 전달
    # =====================================


    return list(
        selected.values()
    )



def get_fixed_quick_squad_options(
    candidate_rows: list[dict],
    grade: int,
    budget_bp: int,
    price_cache: dict,
):
    """
    선택한 강화등급의 실제 가격만 사용한다.
    가격이 없으면 다른 강화로 대체하지 않는다.
    """

    rows_to_fetch = [
        row
        for row in candidate_rows
        if int(row["sp_id"]) not in price_cache
    ]

    def fetch_prices(row):
        sp_id = int(row["sp_id"])

        try:
            return (
                sp_id,
                get_quick_squad_cached_prices(sp_id),
            )
        except Exception as error:
            print(
                "[QUICK SQUAD FIXED] price failed:",
                sp_id,
                error,
            )
            return sp_id, None

    # 동일 SPID는 한 번만 조회한다.
    unique_rows = {
        int(row["sp_id"]): row
        for row in rows_to_fetch
    }

    if unique_rows:
        with ThreadPoolExecutor(max_workers=4) as executor:
            for sp_id, prices in executor.map(
                fetch_prices,
                unique_rows.values(),
            ):
                price_cache[sp_id] = prices

    options = []

    for row in candidate_rows:
        sp_id = int(row["sp_id"])
        prices = price_cache.get(sp_id)

        if not prices:
            continue

        selected_price = None

        for price_data in prices:
            if int(price_data.get("grade", 0)) != grade:
                continue

            raw_price = price_data.get("price")

            if raw_price is not None:
                selected_price = int(raw_price)

            break

        if (
            selected_price is None
            or selected_price <= 0
            or selected_price > budget_bp
        ):
            continue

        base_ovr = int(row["ovr"] or 0)

        options.append({
            "sp_id": sp_id,
            "player_name": row["player_name"],
            "season_id": int(row["season_id"]),
            "image_url": row["image_url"] or "",
            "position": row["position"] or "",
            "salary": int(row["salary"] or 0),
            "base_ovr": base_ovr,
            "grade": grade,
            "ovr": (
                base_ovr
                + QUICK_SQUAD_ENHANCEMENT_BONUS[grade]
            ),
            "price": selected_price,
        })

    return options


def search_fixed_quick_squad(
    options_by_slot: list[list[dict]],
    budget_bp: int,
):
    """
    메모리 제한형 고정 강화 조합 탐색.
    매 단계에서 상위 상태만 유지하고,
    모든 조합을 리스트에 쌓지 않는다.
    """

    if len(options_by_slot) != 11 or budget_bp <= 0:
        return None

    # 자리별 후보를 능력치·가격·급여 기준으로 다양하게 확보
    # 한 자리당 최대 40개까지만 탐색한다.
    prepared = []

    for options in options_by_slot:
        if not options:
            return None

        unique = {
            int(option["sp_id"]): option
            for option in options
        }

        values = list(unique.values())

        groups = [
            sorted(
                values,
                key=lambda p: (
                    -p["ovr"],
                    p["price"],
                    p["salary"],
                ),
            )[:14],
            sorted(
                values,
                key=lambda p: (
                    p["price"],
                    -p["ovr"],
                ),
            )[:12],
            sorted(
                values,
                key=lambda p: (
                    -p["price"],
                    -p["ovr"],
                ),
            )[:10],
            sorted(
                values,
                key=lambda p: (
                    p["salary"],
                    -p["ovr"],
                    p["price"],
                ),
            )[:10],
        ]

        chosen = {}

        for group in groups:
            for option in group:
                if len(chosen) >= 40:
                    break

                chosen.setdefault(
                    int(option["sp_id"]),
                    option,
                )

        prepared.append(list(chosen.values()))

    # 후보가 적은 자리부터 탐색
    order = sorted(
        range(11),
        key=lambda index: len(prepared[index]),
    )

    ordered = [prepared[index] for index in order]

    # 남은 자리의 최소 비용·급여
    # 불가능한 조합은 미리 제거한다.
    remaining_min_price = [0] * 12
    remaining_min_salary = [0] * 12

    for index in range(10, -1, -1):
        remaining_min_price[index] = (
            remaining_min_price[index + 1]
            + min(
                p["price"]
                for p in ordered[index]
            )
        )

        remaining_min_salary[index] = (
            remaining_min_salary[index + 1]
            + min(
                p["salary"]
                for p in ordered[index]
            )
        )

    if (
        remaining_min_price[0] > budget_bp
        or remaining_min_salary[0] > QUICK_SQUAD_SALARY_CAP
    ):
        return None

    # state = (선택 선수, 사용 이름, 비용, 급여, OVR 합계)
    initial = ((), frozenset(), 0, 0, 0)
    beam = [initial]

    # 각 기준별 최대 유지 상태 수
    BEAM_WIDTH = 32
    sequence = 0

    def push_bounded(heap, rank, state):
        nonlocal sequence

        sequence += 1
        entry = (rank, sequence, state)

        if len(heap) < BEAM_WIDTH:
            heapq.heappush(heap, entry)
        elif rank > heap[0][0]:
            heapq.heapreplace(heap, entry)

    for depth, options in enumerate(ordered):
        quality_heap = []
        spend_heap = []
        cheap_heap = []

        for selected, names, cost, salary, quality in beam:
            for option in options:
                name_key = (
                    str(option["player_name"])
                    .strip()
                    .casefold()
                )

                if name_key in names:
                    continue

                next_cost = cost + int(option["price"])
                next_salary = salary + int(option["salary"])

                if (
                    next_cost
                    + remaining_min_price[depth + 1]
                    > budget_bp
                ):
                    continue

                if (
                    next_salary
                    + remaining_min_salary[depth + 1]
                    > QUICK_SQUAD_SALARY_CAP
                ):
                    continue

                next_quality = quality + int(option["ovr"])

                state = (
                    selected + (option,),
                    names | {name_key},
                    next_cost,
                    next_salary,
                    next_quality,
                )

                # 능력치 우선
                push_bounded(
                    quality_heap,
                    (
                        next_quality,
                        -next_cost,
                        -next_salary,
                    ),
                    state,
                )

                # 예산 활용 우선
                push_bounded(
                    spend_heap,
                    (
                        next_cost,
                        next_quality,
                        -next_salary,
                    ),
                    state,
                )

                # 저비용 조합도 유지해
                # 뒤쪽 선수의 예산 부족을 방지
                push_bounded(
                    cheap_heap,
                    (
                        -next_cost,
                        -next_salary,
                        next_quality,
                    ),
                    state,
                )

        if not quality_heap and not spend_heap and not cheap_heap:
            return None

        # 각 기준별 최대 32개, 총 96개 이하만 유지
        merged = {}

        for heap in (
            quality_heap,
            spend_heap,
            cheap_heap,
        ):
            for _, _, state in heap:
                key = (
                    state[1],
                    state[2],
                    state[3],
                )

                previous = merged.get(key)

                if previous is None or state[4] > previous[4]:
                    merged[key] = state

        beam = list(merged.values())

    if not beam:
        return None

    best_quality = max(state[4] for state in beam)

    # 최고 OVR 합계에서 11 이내인 경쟁력 있는 조합 중
    # 예산을 가장 많이 사용하는 조합을 선택
    eligible = [
        state
        for state in beam
        if state[4] >= best_quality - 11
    ]

    best = max(
        eligible,
        key=lambda state: (
            state[2],
            state[4],
            -state[3],
        ),
    )

    selected_players = [None] * 11

    for ordered_index, original_index in enumerate(order):
        selected_players[original_index] = dict(
            best[0][ordered_index]
        )

    return selected_players

def recommend_fixed_quick_squad(
    team_color_id: int,
    budget_bp: int,
    formation: str,
    slots: list[str],
    grade: int,
):
    """
    고정 강화 추천 전용 경로.
    기존 자동 강화 업그레이드 함수를 호출하지 않는다.
    """

    price_cache = {}
    best_players = None
    price_fetch_failed = False

    # 1차 후보로 구성하고, 불가능하면 후보 범위를 넓힌다.
    for per_salary_limit, total_limit in (
        (3, 120),
        (6, 240),
    ):
        candidate_rows = (
            get_fixed_quick_squad_candidate_rows(
                team_color_id=team_color_id,
                slots=slots,
                per_salary_limit=per_salary_limit,
                total_limit=total_limit,
            )
        )

        options = get_fixed_quick_squad_options(
            candidate_rows=candidate_rows,
            grade=grade,
            budget_bp=budget_bp,
            price_cache=price_cache,
        )

        if any(value is None for value in price_cache.values()):
            price_fetch_failed = True

        options_by_slot = []

        for slot in slots:
            accepted_positions = set(
                QUICK_SQUAD_POSITION_CANDIDATES.get(
                    slot,
                    [slot],
                )
            )

            slot_options = [
                {
                    **option,
                    "slot_position": slot,
                }
                for option in options
                if option["position"] in accepted_positions
            ]

            options_by_slot.append(slot_options)

        selected = search_fixed_quick_squad(
            options_by_slot=options_by_slot,
            budget_bp=budget_bp,
        )

        if selected is not None:
            best_players = selected
            break

    if best_players is None:
        if price_fetch_failed:
            raise HTTPException(
                status_code=502,
                detail=(
                    "일부 선수의 이적시장 시세를 조회하지 "
                    "못했습니다. 잠시 후 다시 시도해주세요."
                ),
            )

        raise HTTPException(
            status_code=422,
            detail=(
                f"+{grade}강 고정 조건으로 "
                "예산과 급여를 모두 만족하는 "
                "11명 조합을 찾지 못했습니다. "
                "예산을 늘리거나 다른 강화등급을 "
                "선택해주세요."
            ),
        )

    total_price = sum(
        int(player["price"])
        for player in best_players
    )

    total_salary = sum(
        int(player["salary"])
        for player in best_players
    )

    player_names = [
        str(player["player_name"]).strip().casefold()
        for player in best_players
    ]

    # 최종 방어 검증: 조건이 깨진 결과는 반환하지 않는다.
    if (
        len(best_players) != 11
        or any(player["grade"] != grade for player in best_players)
        or len(set(player_names)) != 11
        or total_price > budget_bp
        or total_salary > QUICK_SQUAD_SALARY_CAP
        or any(player["price"] <= 0 for player in best_players)
    ):
        raise HTTPException(
            status_code=500,
            detail="고정 강화 스쿼드 검증에 실패했습니다.",
        )

    return {
        "team_color_id": team_color_id,
        "team_name": get_quick_squad_team_name(team_color_id),
        "formation": formation,
        "budget_bp": budget_bp,
        "enhancement_grade": grade,
        "total_price": total_price,
        "remaining_budget": budget_bp - total_price,
        "total_salary": total_salary,
        "salary_cap": QUICK_SQUAD_SALARY_CAP,
        "players": best_players,
        "source": {
            "player": "FCL Player Database",
            "price": "FC Online DataCenter",
        },
    }

# =========================================
# QUICK SQUAD - LOCKED PLAYERS
# =========================================

def create_locked_squad_service():
    return LockedSquadService(
        db=get_db_connection,
        prices=get_quick_squad_cached_prices,
        candidates=get_fixed_quick_squad_candidate_rows,
        budget_candidates=get_budget_quick_squad_candidate_rows,
        positions=QUICK_SQUAD_POSITION_CANDIDATES,
        bonus=QUICK_SQUAD_ENHANCEMENT_BONUS,
        team_name=get_quick_squad_team_name,
        valid_prices=is_valid_quick_squad_market_prices,
        cap=QUICK_SQUAD_SALARY_CAP,
    )

# =========================================
# QUICK SQUAD
# TEAM COLOR RECALCULATION API
# =========================================

@app.post(
    "/api/quick-squad/team-colors/recalculate"
)
def recalculate_quick_squad_team_colors(
    request_data:
        QuickSquadTeamColorRecalculateRequest,
):

    if (
        len(
            request_data.players
        )
        != 11
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "팀컬러 재계산에는 "
                "11명의 선수가 필요합니다."
            ),
        )


    players = [
        {
            "sp_id":
                int(
                    player.sp_id
                ),

            "grade":
                int(
                    player.grade
                ),
        }

        for player
        in request_data.players
    ]


    sp_ids = [
        int(
            player[
                "sp_id"
            ]
        )

        for player
        in players
    ]


    if (
        len(
            set(
                sp_ids
            )
        )
        != 11
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "동일한 선수 카드가 "
                "중복되어 있습니다."
            ),
        )


    with get_db_connection() as connection:

        normal_team_colors = (
            get_active_team_colors_for_squad(
                connection,
                players,
            )
        )


        enhancement_team_colors = (
            get_active_enhancement_team_colors_for_squad(
                connection,
                players,
            )
        )


    selected_team_color_id = int(
        request_data.team_color_id
    )


    for team_color in (
        normal_team_colors
    ):

        team_color[
            "is_selected_team_color"
        ] = (
            int(
                team_color[
                    "team_color_id"
                ]
            )
            ==
            selected_team_color_id
        )


    for team_color in (
        enhancement_team_colors
    ):

        team_color[
            "is_selected_team_color"
        ] = False


    active_team_colors = (
        normal_team_colors
        +
        enhancement_team_colors
    )


    return {

        "active_non_enhancement_team_color_count":
            len(
                normal_team_colors
            ),

        "active_enhancement_team_color_count":
            len(
                enhancement_team_colors
            ),

        "active_enhancement_team_colors":
            enhancement_team_colors,

        "active_team_color_count":
            len(
                active_team_colors
            ),

        "active_team_colors":
            active_team_colors,
    }

@app.post("/api/quick-squad/locked/preview")
def preview_quick_squad_locked(
    request_data: LockedPreviewRequest,
):
    players = create_locked_squad_service().resolve(
        request_data.locked_players,
        team_color_id=request_data.team_color_id,
    )

    return {
        "players": players,
    }

@app.post(
    "/api/quick-squad/recommend"
)
def recommend_quick_squad(
    request_data:
        QuickSquadRecommendRequest,
):

    team_color_id = int(
        request_data.team_color_id
    )


    budget_bp = int(
        request_data.budget_bp
    )


    formation = (
        str(
            request_data.formation
            or ""
        )
        .strip()
    )


    slots = [
        str(
            slot
        )
        .strip()
        .upper()

        for slot
        in request_data.slots
    ]


    # =====================================
    # VALIDATION
    # =====================================

    if (
        team_color_id <= 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "팀컬러를 선택해주세요."
            ),
        )


    if (
        budget_bp <= 0
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "구단가치를 입력해주세요."
            ),
        )


    if (
        len(
            slots
        )
        != 11
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "스쿼드 포지션은 "
                "11개여야 합니다."
            ),
        )


    if (
        "GK"
        not in slots
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "포메이션에 GK가 없습니다."
            ),
        )

    # =====================================
    # 선수도감에서 고정한 선수 우선
    # =====================================

    if (
        request_data.locked_players
        or request_data.budget_mode != "legacy"
    ):

        result = (
            create_locked_squad_service()
            .recommend(
                request_data
            )
        )


        return (
            attach_quick_squad_active_team_colors(
                result
            )
        )

    # =====================================
    # 고정 강화 추천
    # =====================================

    if (
        request_data.enhancement_grade
        is not None
    ):

        result = (
            recommend_fixed_quick_squad(
                team_color_id=
                    team_color_id,

                budget_bp=
                    budget_bp,

                formation=
                    formation,

                slots=
                    slots,

                grade=
                    request_data
                    .enhancement_grade,
            )
        )


        return (
            attach_quick_squad_active_team_colors(
                result
            )
        )


    # =====================================
    # 추천
    # =====================================

    remaining_budget = (
        budget_bp
    )

    remaining_salary = (
        QUICK_SQUAD_SALARY_CAP
    )

    selected_players = []


    used_player_names = []


    for (
        slot_index,
        slot_position
    ) in enumerate(
        slots
    ):

        remaining_slot_count = (
            len(
                slots
            )
            -
            slot_index
        )


        # =================================
        # 남은 예산을 남은 자리 수로
        # 나눈 금액을 해당 자리 목표값으로 사용
        # =================================

        target_budget = max(
            1,

            remaining_budget
            //
            remaining_slot_count,
        )


        # =================================
        # 남은 공식 급여를
        # 남은 자리 수로 배분
        # =================================

        salary_budget = max(
            1,

            remaining_salary
            //
            remaining_slot_count,
        )


        selected_player = (
            choose_quick_squad_candidate(
                team_color_id=
                    team_color_id,

                slot_position=
                    slot_position,

                target_budget=
                    target_budget,

                remaining_budget=
                    remaining_budget,

                max_salary=
                    salary_budget,

                used_player_names=
                    used_player_names,
            )
        )


        # =================================
        # 정확한 평균 급여 안에 후보가 없으면
        # 최대 +3까지 완화
        #
        # 그래도 전체 310은 넘지 않음
        # =================================

        if (
            selected_player
            is None
            and
            remaining_slot_count
            >
            1
        ):

            maximum_relaxed_salary = (
                remaining_salary
                -
                (
                    remaining_slot_count
                    -
                    1
                )
            )


            relaxed_salary_budget = min(
                salary_budget
                +
                3,

                maximum_relaxed_salary,
            )


            if (
                relaxed_salary_budget
                >
                salary_budget
            ):

                selected_player = (
                    choose_quick_squad_candidate(
                        team_color_id=
                            team_color_id,

                        slot_position=
                            slot_position,

                        target_budget=
                            target_budget,

                        remaining_budget=
                            remaining_budget,

                        max_salary=
                            relaxed_salary_budget,

                        used_player_names=
                            used_player_names,
                    )
                )


        if (
            selected_player
            is None
        ):

            raise HTTPException(
                status_code=422,
                detail=(
                    f"{slot_position} 포지션에서 "
                    "선택한 팀컬러에 해당하는 "
                    "거래 가능한 선수를 "
                    "찾지 못했습니다."
                ),
            )


        selected_players.append(
            selected_player
        )


        used_player_names.append(
            selected_player[
                "player_name"
            ]
        )


        remaining_budget -= (
            selected_player[
                "price"
            ]
        )

        remaining_salary -= (
            selected_player[
                "salary"
            ]
        )


    # =====================================
    # 2차 업그레이드
    #
    # 1차에서 스쿼드 11명을 확보한 뒤
    # 남은 예산을 다시 선수단에 투자
    # =====================================

    QUICK_SQUAD_UPGRADE_ROUNDS = 0


    for upgrade_round in range(
        QUICK_SQUAD_UPGRADE_ROUNDS
    ):

        if (
            remaining_budget
            <= 0
        ):

            break


        upgraded_in_round = False


        # =================================
        # 현재 OVR이 낮은 자리부터
        # 업그레이드 기회 부여
        #
        # 실제 배열 순서는 변경하지 않음
        # =================================

        upgrade_indices = sorted(
            range(
                len(
                    selected_players
                )
            ),

            key=lambda index:
                int(
                    selected_players[
                        index
                    ][
                        "ovr"
                    ]
                ),
        )


        for (
            order_index,
            player_index
        ) in enumerate(
            upgrade_indices
        ):

            if (
                remaining_budget
                <= 0
            ):

                break


            current_player = (
                selected_players[
                    player_index
                ]
            )


            remaining_upgrade_slots = (
                len(
                    upgrade_indices
                )
                -
                order_index
            )


            # =================================
            # 현재 남은 예산을
            # 아직 업그레이드 기회를
            # 받지 않은 자리끼리 배분
            # =================================

            upgrade_budget = max(
                1,

                remaining_budget
                //
                remaining_upgrade_slots,
            )


            # =================================
            # 다른 10명과 같은 이름의 선수는
            # 중복 선택 금지
            #
            # 현재 자리 선수 이름은 제외하지 않음
            # → 같은 선수의 다른 시즌 교체 가능
            # =================================

            excluded_player_names = [
                player[
                    "player_name"
                ]

                for (
                    other_index,
                    player
                ) in enumerate(
                    selected_players
                )

                if (
                    other_index
                    !=
                    player_index
                )
            ]

            current_total_salary = sum(
                int(
                    player[
                        "salary"
                    ]
                )

                for player
                in selected_players
            )


            max_upgrade_salary = (
                QUICK_SQUAD_SALARY_CAP
                -
                (
                    current_total_salary
                    -
                    int(
                        current_player[
                            "salary"
                        ]
                    )
                )
            )


            upgrade_player = (
                choose_quick_squad_upgrade(
                    team_color_id=
                        team_color_id,

                    current_player=
                        current_player,

                    upgrade_budget=
                        upgrade_budget,

                    max_salary=
                        max_upgrade_salary,

                    excluded_player_names=
                        excluded_player_names,
                )
            )


            if (
                upgrade_player
                is None
            ):

                continue


            extra_cost = int(
                upgrade_player[
                    "extra_cost"
                ]
            )


            if (
                extra_cost
                >
                remaining_budget
            ):

                continue


            # =================================
            # 교체
            # =================================

            selected_players[
                player_index
            ] = {
                key:
                    value

                for (
                    key,
                    value
                ) in (
                    upgrade_player.items()
                )

                if key not in (
                    "extra_cost",
                    "ovr_gain",
                )
            }


            remaining_budget -= (
                extra_cost
            )


            upgraded_in_round = (
                True
            )


        # =================================
        # 한 바퀴 돌았는데 아무도
        # 좋아지지 않았다면 종료
        # =================================

        if not (
            upgraded_in_round
        ):

            break

    # =====================================
    # 최종 예산 소진
    #
    # 현재 선택된 11명의 강화단계를
    # 가능한 범위에서 추가 업그레이드
    # =====================================

    remaining_budget = (
        maximize_quick_squad_grade_budget(
            selected_players=
                selected_players,

            remaining_budget=
                remaining_budget,
        )
    )

    # =====================================
    # +1 ~ +8까지 모두 최적화했는데도
    # 남은 BP가 있을 경우
    #
    # 최대 2명만 +9 ~ +13 허용
    # =====================================

    remaining_budget = (
        maximize_quick_squad_high_grade_budget(
            selected_players=
                selected_players,

            remaining_budget=
                remaining_budget,
        )
    )


    # =====================================
    # SUMMARY
    # =====================================

    total_price = sum(
        int(
            player[
                "price"
            ]
        )

        for player
        in selected_players
    )


    total_salary = sum(
        int(
            player[
                "salary"
            ]
        )

        for player
        in selected_players
    )


    team_name = (
        get_quick_squad_team_name(
            team_color_id
        )
    )


    result = {
        "team_color_id":
            team_color_id,

        "team_name":
            team_name,

        "formation":
            formation,

        "budget_bp":
            budget_bp,

        "total_price":
            total_price,

        "remaining_budget":
            (
                budget_bp
                -
                total_price
            ),

        "total_salary":
            total_salary,

        "salary_cap":
            QUICK_SQUAD_SALARY_CAP,

        "players":
            selected_players,

        "source":
            {
                "player":
                    "FCL Player Database",

                "price":
                    "FC Online DataCenter",
            },
    }


    return (
        attach_quick_squad_active_team_colors(
            result
        )
    )

@app.get(
    "/api/player-database/filters/nations"
)
def get_player_database_nations(
    continent_id: int,
):

    return {
        "nations":
            get_player_catalog_nations_by_continent(
                continent_id
            )
    }


@app.get(
    "/api/player-database/filters/teams"
)
def get_player_database_teams(
    league_id: int,
):

    return {
        "teams":
            get_player_catalog_teams_by_league(
                league_id
            )
    }


# =========================================
# FC ONLINE PLAYER DATABASE
# =========================================

# =========================================
# FC ONLINE PLAYER TRAITS
# =========================================

@app.get(
    "/api/player-database/traits/{sp_id}"
)
def get_player_database_traits_api(
    sp_id: int,
):

    if sp_id <= 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "올바른 선수 ID가 아닙니다."
            ),
        )


    try:

        player_data = (
            get_player_ability(
                sp_id=
                    sp_id,

                grade=
                    1,
            )
        )

    except httpx.HTTPError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "FC Online 데이터센터에서 "
                "선수 특성을 불러오지 못했습니다."
            ),
        ) from error


    trait_items = (
        player_data.get(
            "trait_items",
            [],
        )
        or []
    )


    return {
        "sp_id":
            sp_id,

        "traits":
            trait_items,

        "source":
            "FC Online DataCenter",
    }


# =========================================
# QUICK SQUAD - PLAYER DETAIL
# =========================================

@app.get("/api/quick-squad/player-detail/{sp_id}")
def get_quick_squad_player_detail(sp_id: int):

    if sp_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="올바른 선수 ID가 아닙니다.",
        )

    with get_db_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM fconline_players
                WHERE sp_id = %s
                """,
                (sp_id,),
            )

            row = cursor.fetchone()

            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail="선수 DB에서 해당 선수를 찾지 못했습니다.",
                )

            cursor.execute(
                """
                SELECT
                    team_color_id,
                    team_name
                FROM fconline_player_teams
                WHERE sp_id = %s
                ORDER BY team_name
                """,
                (sp_id,),
            )

            team_colors = [
                {
                    "team_color_id": item["team_color_id"],
                    "team_name": item["team_name"],
                }
                for item in cursor.fetchall()
            ]

    # DB에 저장된 1강 / 적응도 1 / 팀컬러 0 원본값
    stats = {}

    for stat_name, column_name in PLAYER_STAT_COLUMN_MAP.items():
        raw_value = row.get(column_name)

        stats[stat_name] = (
            int(raw_value)
            if raw_value is not None
            else None
        )

    left_foot = int(row.get("left_foot") or 0)
    right_foot = int(row.get("right_foot") or 0)

    return {
        "sp_id": int(row["sp_id"]),
        "player_name": row["player_name"],
        "season_id": int(row["season_id"]),
        "image_url": row.get("image_url") or "",
        "position": row.get("position") or "",
        "salary": int(row.get("salary") or 0),
        "base_ovr": int(row.get("ovr") or 0),
        "height": row.get("height"),
        "weight": row.get("weight"),
        "nation_name": row.get("nation_name") or "",
        "left_foot": left_foot,
        "right_foot": right_foot,
        "skill_moves": row.get("skill_moves"),
        "traits": row.get("traits") or [],
        "stats": stats,
        "team_colors": team_colors,
        "ability_bonus": 0,
    }


# =========================================
# FC ONLINE PLAYER MARKET PRICE
# =========================================

def get_fconline_player_market_prices(
    sp_id: int,
):

    url = (
        "https://m.fconline.nexon.com/"
        "datacenter/playerinfo"
    )


    headers = {
        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),

        "Referer":
            "https://m.fconline.nexon.com/",
    }


    try:

        response = httpx.get(
            url,
            params={
                "spid":
                    sp_id,
            },
            headers=headers,
            timeout=6.0,
            follow_redirects=True,
        )

    except httpx.RequestError as error:

        raise HTTPException(
            status_code=502,
            detail=(
                "FC Online 데이터센터에 "
                "연결할 수 없습니다."
            ),
        ) from error


    if response.status_code != 200:

        raise HTTPException(
            status_code=502,
            detail=(
                "FC Online 데이터센터에서 "
                "선수 시세를 불러오지 못했습니다."
            ),
        )


    price_pattern = re.compile(
        (
            r'<span\b'
            r'[^>]*'
            r'class=["\']'
            r'[^"\']*'
            r'span_bp(\d+)'
            r'[^"\']*'
            r'["\']'
            r'[^>]*>'
            r'\s*'
            r'([\d,]+)'
            r'\s*BP'
            r'\s*'
            r'</span>'
        ),
        flags=re.IGNORECASE,
    )

    parsed_prices = {}


    for match in price_pattern.finditer(
        response.text
    ):

        grade = int(
            match.group(1)
        )


        if (
            grade < 1
            or grade > 13
        ):
            continue


        price = int(
            match.group(2)
                .replace(
                    ",",
                    "",
                )
        )


        parsed_prices[
            grade
        ] = price


    if not parsed_prices:

        raise HTTPException(
            status_code=502,
            detail=(
                "FC Online 데이터센터에서 "
                "시세 정보를 찾을 수 없습니다."
            ),
        )


    prices = []


    for grade in range(
        1,
        14,
    ):

        prices.append(
            {
                "grade":
                    grade,

                "price":
                    parsed_prices.get(
                        grade
                    ),
            }
        )


    return prices


@app.get(
    "/api/player-database/price/{sp_id}"
)
def get_player_database_price_api(
    sp_id: int,
    grade: int = 1,
):

    if (
        grade < 1
        or grade > 13
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "강화 단계는 "
                "1강부터 13강까지 가능합니다."
            ),
        )


    prices = (
        get_fconline_player_market_prices(
            sp_id
        )
    )


    selected_price = None


    for price_data in prices:

        if (
            price_data["grade"]
            == grade
        ):

            selected_price = (
                price_data["price"]
            )

            break


    return {
        "sp_id":
            sp_id,

        "grade":
            grade,

        "current_price":
            selected_price,

        "prices":
            prices,

        "source":
            "FC Online DataCenter",
    }

@app.get(
    "/api/player-database/search"
)
def search_player_database_api(
    request: Request,
    player_name: str = "",
    season_id: int | None = None,
    season_ids: str = "",
    nation_id: int | None = None,
    nation_name: str = "",
    team_color_id: int | None = None,
    official_team_color_id: int | None = None,
    team_name: str = "",
    position: str = "",
    positions: str = "",
    grade: int = 1,
    adaptation: int = 5,
    team_color: int = 0,
    salary_min: int | None = None,
    salary_max: int | None = None,
    ovr_min: int | None = None,
    height_min: int | None = None,
    height_max: int | None = None,
    left_foot: int | None = None,
    right_foot: int | None = None,
    page: int = 1,
    page_size: int = 20,
):

    try:

        # =================================
        # 34개 능력치 최소값
        # =================================

        stat_mins = {}


        for (
            query_name,
            stat_column,
        ) in (
            PLAYER_DATABASE_STAT_FILTER_MAP
            .items()
        ):

            raw_value = (
                request.query_params.get(
                    query_name
                )
            )


            if (
                raw_value is None
                or
                raw_value == ""
            ):
                continue


            try:

                stat_mins[
                    stat_column
                ] = int(
                    raw_value
                )

            except ValueError as error:

                raise HTTPException(
                    status_code=400,
                    detail=(
                        "능력치 검색값이 "
                        "올바르지 않습니다."
                    ),
                ) from error


        return search_player_catalog(
            player_name=
                player_name,

            season_id=
                season_id,

            nation_id=
                nation_id,

            nation_name=
                nation_name,

            team_color_id=
                team_color_id,

            official_team_color_id=
                official_team_color_id,

            team_name=
                team_name,

            position=
                position,

            grade=
                grade,

            adaptation=
                adaptation,

            team_color=
                team_color,

            salary_min=
                salary_min,

            salary_max=
                salary_max,

            ovr_min=
                ovr_min,

            height_min=
                height_min,

            height_max=
                height_max,

            left_foot=
                left_foot,

            right_foot=
                right_foot,

            stat_mins=
                stat_mins,

            page=
                page,

            page_size=
                page_size,

            season_ids=
                season_ids,

            positions=
                positions,

        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

# =========================================
# FC ONLINE PLAYER RECOMMENDATION
# =========================================

@app.get(
    "/api/player-database/recommend"
)
def recommend_player_database_api(
    base_sp_id: int,
    grade: int = 1,
    adaptation: int = 5,
    team_color: int = 0,
    position_mode: str = "same",
    salary_mode: str = "any",
    team_color_id: int | None = None,
    ovr_min: int | None = None,
    ovr_max: int | None = None,
    limit: int = 10,
):

    try:

        return recommend_player_catalog(
            base_sp_id=
                base_sp_id,

            grade=
                grade,

            adaptation=
                adaptation,

            team_color=
                team_color,

            position_mode=
                position_mode,

            salary_mode=
                salary_mode,

            team_color_id=
                team_color_id,

            ovr_min=
                ovr_min,

            ovr_max=
                ovr_max,

            limit=
                limit,
        )


    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(
                error
            ),
        ) from error

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