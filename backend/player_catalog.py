import os
import re
import time

import httpx
import psycopg

from bs4 import BeautifulSoup
from psycopg.rows import dict_row


# =========================================
# FC ONLINE PLAYER CATALOG
# =========================================

PLAYER_ABILITY_URL = (
    "https://fconline.nexon.com"
    "/datacenter/PlayerAbility"
)

SEASON_METADATA_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/seasonid.json"
)

SPID_METADATA_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/spid.json"
)

PLAYER_STAT_URL = (
    "https://fconline.nexon.com/"
    "DataCenter/PlayerStat"
)

PLAYER_LIST_URL = (
    "https://fconline.nexon.com/"
    "datacenter/PlayerList"
)

PLAYER_IMAGE_URL_TEMPLATE = (
    "https://fco.dn.nexoncdn.co.kr/"
    "live/externalAssets/common/"
    "playersAction/p{sp_id}.png"
)

PLAYER_REQUEST_DELAY_SECONDS = 0.4

PLAYER_HTTP_RETRY_DELAYS = (
    1.5,
    3.0,
    6.0,
)

PLAYER_MAX_SYNC_ATTEMPTS = 3


SEASON_METADATA_CACHE = None
PLAYER_FILTER_GROUP_CACHE = None

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

ENHANCEMENT_BONUS = {
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

ADAPTATION_BONUS = {
    1: 0,
    5: 4,
}


TEAM_COLOR_BONUS = {
    0: 0,
    1: 1,
    2: 2,
    3: 3,
    4: 4,
    5: 5,
    6: 6,
    7: 7,
    8: 8,
    9: 9,
}

PLAYER_LIST_RESULT_LIMIT = 200


POSITION_FILTERS = {
    "FW": [
        24,
        25,
        26,
        20,
        21,
        22,
        27,
        23,
    ],

    "MF": [
        13,
        14,
        15,
        17,
        18,
        19,
        9,
        10,
        11,
        16,
        12,
    ],

    "DF": [
        1,
        4,
        5,
        6,
        3,
        7,
        2,
        8,
    ],

    "GK": [
        0,
    ],
}

EXTRA_NATIONS = [
    {
        "nation_id": 205,
        "nation_name": "지브롤터",
    },
]

def make_position_filter(
    position_indices,
):

    if position_indices is None:

        return ""


    return (
        ","
        +
        ",".join(
            str(
                position_index
            )

            for position_index
            in position_indices
        )
        +
        ","
    )


def collect_nation_spids(
    nation_id,
    salary_min=0,
    salary_max=50,
    ovr_min=0,
    ovr_max=200,
    position_indices=None,
    position_label="ALL",
    depth=0,
):

    spids = (
        get_player_list_spids(
            nation_id=
                nation_id,

            salary_min=
                salary_min,

            salary_max=
                salary_max,

            ovr_min=
                ovr_min,

            ovr_max=
                ovr_max,

            position_indices=
                position_indices,
        )
    )


    indent = (
        "  "
        *
        depth
    )


    print(
        (
            f"{indent}"
            f"nation={nation_id}"
            f" | salary="
            f"{salary_min}-{salary_max}"
            f" | ovr="
            f"{ovr_min}-{ovr_max}"
            f" | pos="
            f"{position_label}"
            f" | count="
            f"{len(spids)}"
        )
    )


    # =====================================
    # 200개 미만이면 안전하게 완료
    # =====================================

    if (
        len(spids)
        <
        PLAYER_LIST_RESULT_LIMIT
    ):

        return set(
            spids
        )


    # =====================================
    # 1차: 급여 분할
    # =====================================

    if (
        salary_min
        <
        salary_max
    ):

        salary_middle = (
            salary_min
            +
            salary_max
        ) // 2


        left = (
            collect_nation_spids(
                nation_id=
                    nation_id,

                salary_min=
                    salary_min,

                salary_max=
                    salary_middle,

                ovr_min=
                    ovr_min,

                ovr_max=
                    ovr_max,

                position_indices=
                    position_indices,

                position_label=
                    position_label,

                depth=
                    depth + 1,
            )
        )


        right = (
            collect_nation_spids(
                nation_id=
                    nation_id,

                salary_min=
                    salary_middle + 1,

                salary_max=
                    salary_max,

                ovr_min=
                    ovr_min,

                ovr_max=
                    ovr_max,

                position_indices=
                    position_indices,

                position_label=
                    position_label,

                depth=
                    depth + 1,
            )
        )


        return (
            left
            |
            right
        )


    # =====================================
    # 2차: OVR 분할
    # =====================================

    if (
        ovr_min
        <
        ovr_max
    ):

        ovr_middle = (
            ovr_min
            +
            ovr_max
        ) // 2


        left = (
            collect_nation_spids(
                nation_id=
                    nation_id,

                salary_min=
                    salary_min,

                salary_max=
                    salary_max,

                ovr_min=
                    ovr_min,

                ovr_max=
                    ovr_middle,

                position_indices=
                    position_indices,

                position_label=
                    position_label,

                depth=
                    depth + 1,
            )
        )


        right = (
            collect_nation_spids(
                nation_id=
                    nation_id,

                salary_min=
                    salary_min,

                salary_max=
                    salary_max,

                ovr_min=
                    ovr_middle + 1,

                ovr_max=
                    ovr_max,

                position_indices=
                    position_indices,

                position_label=
                    position_label,

                depth=
                    depth + 1,
            )
        )


        return (
            left
            |
            right
        )


    # =====================================
    # 3차: FW / MF / DF / GK
    # =====================================

    if position_indices is None:

        result = set()


        for (
            group_name,
            group_positions,
        ) in POSITION_FILTERS.items():

            result |= (
                collect_nation_spids(
                    nation_id=
                        nation_id,

                    salary_min=
                        salary_min,

                    salary_max=
                        salary_max,

                    ovr_min=
                        ovr_min,

                    ovr_max=
                        ovr_max,

                    position_indices=
                        group_positions,

                    position_label=
                        group_name,

                    depth=
                        depth + 1,
                )
            )


        return result


    # =====================================
    # 4차: 상세 포지션 하나씩
    # =====================================

    if (
        len(
            position_indices
        )
        >
        1
    ):

        result = set()


        for position_index in (
            position_indices
        ):

            result |= (
                collect_nation_spids(
                    nation_id=
                        nation_id,

                    salary_min=
                        salary_min,

                    salary_max=
                        salary_max,

                    ovr_min=
                        ovr_min,

                    ovr_max=
                        ovr_max,

                    position_indices=[
                        position_index,
                    ],

                    position_label=
                        str(
                            position_index
                        ),

                    depth=
                        depth + 1,
                )
            )


        return result


    # =====================================
    # 여기까지 200이면 정말 위험
    # 조용히 누락시키지 않고 중단
    # =====================================

    raise RuntimeError(
        (
            "PlayerList 결과가 "
            "상세 포지션까지 분할했는데도 "
            "200개입니다. "

            f"nation={nation_id}, "
            f"salary={salary_min}, "
            f"ovr={ovr_min}, "
            f"position={position_indices}"
        )
    )


def save_nation_spids(
    nation_id,
    nation_name,
    spids,
):

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    rows = [
        (
            int(
                sp_id
            ),
            int(
                nation_id
            ),
            str(
                nation_name
            ),
        )

        for sp_id
        in spids
    ]


    if not rows:

        return 0


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.executemany(
                """
                INSERT INTO
                    fconline_player_nations (
                        sp_id,
                        nation_id,
                        nation_name
                    )

                VALUES (
                    %s,
                    %s,
                    %s
                )

                ON CONFLICT (
                    sp_id
                )

                DO UPDATE SET
                    nation_id =
                        EXCLUDED.nation_id,

                    nation_name =
                        EXCLUDED.nation_name,

                    updated_at =
                        NOW()
                """,
                rows,
            )


        connection.commit()


    return len(
        rows
    )


def get_completed_nation_ids():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    nation_id

                FROM
                    fconline_nation_sync_state

                WHERE
                    status = 'completed'
                """
            )


            return {
                int(
                    row[0]
                )

                for row
                in cursor.fetchall()
            }


def set_nation_sync_running(
    nation_id,
    nation_name,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_nation_sync_state (
                        nation_id,
                        nation_name,
                        status,
                        started_at,
                        completed_at,
                        last_error,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    'running',
                    NOW(),
                    NULL,
                    NULL,
                    NOW()
                )

                ON CONFLICT (
                    nation_id
                )

                DO UPDATE SET
                    nation_name =
                        EXCLUDED.nation_name,

                    status =
                        'running',

                    started_at =
                        NOW(),

                    completed_at =
                        NULL,

                    last_error =
                        NULL,

                    updated_at =
                        NOW()
                """,
                (
                    nation_id,
                    nation_name,
                ),
            )


        connection.commit()


def set_nation_sync_completed(
    nation_id,
    nation_name,
    card_count,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_nation_sync_state (
                        nation_id,
                        nation_name,
                        status,
                        card_count,
                        completed_at,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    'completed',
                    %s,
                    NOW(),
                    NOW()
                )

                ON CONFLICT (
                    nation_id
                )

                DO UPDATE SET
                    nation_name =
                        EXCLUDED.nation_name,

                    status =
                        'completed',

                    card_count =
                        EXCLUDED.card_count,

                    completed_at =
                        NOW(),

                    last_error =
                        NULL,

                    updated_at =
                        NOW()
                """,
                (
                    nation_id,
                    nation_name,
                    card_count,
                ),
            )


        connection.commit()

def set_nation_sync_failed(
    nation_id,
    nation_name,
    error,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_nation_sync_state (
                        nation_id,
                        nation_name,
                        status,
                        last_error,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    'failed',
                    %s,
                    NOW()
                )

                ON CONFLICT (
                    nation_id
                )

                DO UPDATE SET
                    nation_name =
                        EXCLUDED.nation_name,

                    status =
                        'failed',

                    last_error =
                        EXCLUDED.last_error,

                    updated_at =
                        NOW()
                """,
                (
                    nation_id,
                    nation_name,
                    str(
                        error
                    )[:2000],
                ),
            )


        connection.commit()


def mark_existing_nation_completed(
    nation_id,
):

    nations = {
        nation[
            "nation_id"
        ]:
            nation[
                "nation_name"
            ]

        for nation
        in get_nation_metadata()
    }


    nation_name = (
        nations.get(
            nation_id
        )
    )


    if not nation_name:

        raise RuntimeError(
            (
                "국적 메타데이터를 "
                "찾을 수 없습니다: "
                f"{nation_id}"
            )
        )


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_player_nations

                WHERE
                    nation_id = %s
                """,
                (
                    nation_id,
                ),
            )


            card_count = int(
                cursor.fetchone()[0]
            )


    if card_count <= 0:

        raise RuntimeError(
            (
                "저장된 국적 카드가 없습니다: "
                f"{nation_id}"
            )
        )


    set_nation_sync_completed(
        nation_id=
            nation_id,

        nation_name=
            nation_name,

        card_count=
            card_count,
    )


    return {
        "nation_id":
            nation_id,

        "nation_name":
            nation_name,

        "card_count":
            card_count,
    }


def sync_nation_maps(
    max_nations=3,
):

    nations = (
        get_nation_metadata()
    )


    completed_ids = (
        get_completed_nation_ids()
    )


    pending_nations = [
        nation

        for nation
        in nations

        if (
            nation[
                "nation_id"
            ]
            not in completed_ids
        )
    ]


    if (
        max_nations
        is not None
    ):

        pending_nations = (
            pending_nations[
                :max_nations
            ]
        )


    print()
    print(
        "전체 국적:",
        len(
            nations
        ),
    )

    print(
        "완료 국적:",
        len(
            completed_ids
        ),
    )

    print(
        "이번 실행:",
        len(
            pending_nations
        ),
    )


    success_count = 0
    failure_count = 0


    for (
        index,
        nation
    ) in enumerate(
        pending_nations,
        start=1,
    ):

        nation_id = (
            nation[
                "nation_id"
            ]
        )

        nation_name = (
            nation[
                "nation_name"
            ]
        )


        print()
        print(
            "======================================"
        )

        print(
            (
                f"[{index}/"
                f"{len(pending_nations)}] "
                f"{nation_name} "
                f"({nation_id})"
            )
        )

        print(
            "======================================"
        )


        set_nation_sync_running(
            nation_id,
            nation_name,
        )


        try:

            spids = (
                collect_nation_spids(
                    nation_id=
                        nation_id,
                )
            )


            saved_count = (
                save_nation_spids(
                    nation_id=
                        nation_id,

                    nation_name=
                        nation_name,

                    spids=
                        spids,
                )
            )


            set_nation_sync_completed(
                nation_id=
                    nation_id,

                nation_name=
                    nation_name,

                card_count=
                    len(
                        spids
                    ),
            )


            success_count += 1


            print()
            print(
                "국적:",
                nation_name,
            )

            print(
                "카드:",
                len(
                    spids
                ),
            )

            print(
                "저장:",
                saved_count,
            )

            print(
                "상태: SUCCESS"
            )


        except Exception as error:

            failure_count += 1


            set_nation_sync_failed(
                nation_id=
                    nation_id,

                nation_name=
                    nation_name,

                error=
                    error,
            )


            print()
            print(
                "상태: FAILED"
            )

            print(
                "오류:",
                repr(
                    error
                ),
            )


    updated_players = (
        apply_nation_map_to_players()
    )


    print()
    print(
        "======================================"
    )

    print(
        "NATION SYNC COMPLETE"
    )

    print(
        "국가 성공:",
        success_count,
    )

    print(
        "국가 실패:",
        failure_count,
    )

    print(
        "기존 선수 국적 교정:",
        updated_players,
    )

    print(
        "======================================"
    )


def apply_nation_map_to_players():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE
                    fconline_players
                AS player

                SET
                    nation_id =
                        nation.nation_id,

                    nation_name =
                        nation.nation_name,

                    updated_at =
                        NOW()

                FROM
                    fconline_player_nations
                AS nation

                WHERE
                    nation.sp_id =
                        player.sp_id

                    AND (
                        player.nation_id
                            IS DISTINCT FROM
                            nation.nation_id

                        OR

                        player.nation_name
                            IS DISTINCT FROM
                            nation.nation_name
                    )
                """
            )


            updated_count = (
                cursor.rowcount
            )


        connection.commit()


    return updated_count


def get_saved_nation_test(
    sp_id,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor(
            row_factory=dict_row,
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id,
                    player_name,
                    nation_id,
                    nation_name

                FROM
                    fconline_players

                WHERE
                    sp_id = %s
                """,
                (
                    sp_id,
                ),
            )


            return (
                cursor.fetchone()
            )

# =========================================
# FC ONLINE 공식 선수검색 필터
# 대륙 / 리그 구조
# =========================================

def _get_player_stat_filter_soup(
    params=None,
):

    response = httpx.get(
        PLAYER_STAT_URL,

        headers={
            "User-Agent":
                "Mozilla/5.0",
        },

        params=
            params
            or {},

        timeout=20.0,

        follow_redirects=True,
    )


    response.raise_for_status()


    return BeautifulSoup(
        response.text,
        "html.parser",
    )


def _extract_ability_filter_items(
    soup,
    field_keyword,
):

    items = []


    for element in soup.select(
        "a[onclick]"
    ):

        onclick = (
            element.get(
                "onclick",
                "",
            )
        )


        match = re.search(
            (
                r"SetAbilitySearch\("
                r"\s*['\"](\d+)['\"]"
                r"\s*,\s*"
                r"['\"]([^'\"]+)['\"]"
            ),
            onclick,
            re.IGNORECASE,
        )


        if not match:
            continue


        value = int(
            match.group(
                1
            )
        )


        field_name = (
            match.group(
                2
            )
        )


        normalized_field_name = (
            field_name
            .strip()
            .lower()
        )


        if (
            field_keyword.lower()
            not in normalized_field_name
        ):
            continue


        name = (
            element.get_text(
                " ",
                strip=True,
            )
        )


        if not name:
            continue


        items.append(
            {
                "id":
                    value,

                "name":
                    name,

                "field_name":
                    field_name,
            }
        )


    # 중복 제거
    unique_items = {}


    for item in items:

        unique_items[
            item["id"]
        ] = item


    return list(
        unique_items.values()
    )

def normalize_player_filter_name(
    value,
):

    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ).strip(),
    ).casefold()

def get_player_filter_groups():

    global PLAYER_FILTER_GROUP_CACHE


    if (
        PLAYER_FILTER_GROUP_CACHE
        is not None
    ):
        return PLAYER_FILTER_GROUP_CACHE


    soup = (
        _get_player_stat_filter_soup()
    )


    # =====================================
    # 대륙
    # =====================================

    continent_map = {}


    for element in soup.select(
        "a.continent_item.selector_item[data-no]"
    ):

        try:
            continent_id = int(
                element.get(
                    "data-no"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue


        if continent_id == 0:
            continue


        continent_map[
            continent_id
        ] = {
            "id":
                continent_id,

            "name":
                element.get_text(
                    " ",
                    strip=True,
                ),

            "nations":
                [],
        }


    # =====================================
    # 국적
    #
    # data-no = 대륙 ID
    # onclick  = 실제 nation ID
    # =====================================

    for element in soup.select(
        "a.nationality_item.selector_item[data-no]"
    ):

        try:
            continent_id = int(
                element.get(
                    "data-no"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue


        onclick = (
            element.get(
                "onclick",
                "",
            )
        )


        match = re.search(
            (
                r"SetAbilitySearch\("
                r"\s*['\"](\d+)['\"]"
                r"\s*,\s*"
                r"['\"]n4NationId['\"]"
            ),
            onclick,
        )


        if not match:
            continue


        nation_id = int(
            match.group(
                1
            )
        )


        if (
            continent_id
            not in continent_map
        ):
            continue


        continent_map[
            continent_id
        ][
            "nations"
        ].append(
            {
                "nation_id":
                    nation_id,

                "nation_name":
                    element.get_text(
                        " ",
                        strip=True,
                    ),
            }
        )


    # =====================================
    # 리그
    # =====================================

    league_map = {}


    for element in soup.select(
        "a.league_item.selector_item[data-no]"
    ):

        try:
            league_id = int(
                element.get(
                    "data-no"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue


        if league_id == 0:
            continue


        league_name = (
            element.get_text(
                " ",
                strip=True,
            )
        )


        # 공식 "기타 리그"는
        # 우리 화면에서는 그냥 "기타"
        if league_id == 76:
            league_name = "기타"


        league_map[
            league_id
        ] = {
            "id":
                league_id,

            "name":
                league_name,

            "clubs":
                [],
        }


    # =====================================
    # 클럽
    #
    # data-no = 리그 ID
    # onclick  = FC 공식 team ID
    # =====================================

    for element in soup.select(
        "a.club_item.selector_item[data-no]"
    ):

        try:
            league_id = int(
                element.get(
                    "data-no"
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue


        onclick = (
            element.get(
                "onclick",
                "",
            )
        )


        match = re.search(
            (
                r"SetAbilitySearch\("
                r"\s*['\"](\d+)['\"]"
                r"\s*,\s*"
                r"['\"]n4TeamId['\"]"
            ),
            onclick,
        )


        if not match:
            continue


        if (
            league_id
            not in league_map
        ):
            continue


        official_team_id = int(
            match.group(
                1
            )
        )


        league_map[
            league_id
        ][
            "clubs"
        ].append(
            {
                "official_team_id":
                    official_team_id,

                "team_name":
                    element.get_text(
                        " ",
                        strip=True,
                    ),
            }
        )


    PLAYER_FILTER_GROUP_CACHE = {
        "continents":
            list(
                continent_map.values()
            ),

        "leagues":
            list(
                league_map.values()
            ),
    }


    return (
        PLAYER_FILTER_GROUP_CACHE
    )

# =========================================
# TEMP DEBUG
# FC ONLINE 대륙 / 리그 HTML 구조 확인
# =========================================

def get_player_catalog_nations_by_continent(
    continent_id,
):

    groups = (
        get_player_filter_groups()
    )


    continent = next(
        (
            item

            for item in (
                groups[
                    "continents"
                ]
            )

            if (
                int(
                    item["id"]
                )
                ==
                int(
                    continent_id
                )
            )
        ),
        None,
    )


    if not continent:

        return []


    soup = (
        _get_player_stat_filter_soup(
            {
                continent[
                    "field_name"
                ]:
                    continent[
                        "id"
                    ],
            }
        )
    )


    nations = (
        _extract_ability_filter_items(
            soup,
            "nation",
        )
    )


    # =====================================
    # 우리 DB에 실제 존재하는 국적만
    # =====================================

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT DISTINCT
                    nation_id,
                    nation_name

                FROM
                    fconline_players

                WHERE
                    nation_id IS NOT NULL

                AND
                    nation_name IS NOT NULL

                AND
                    nation_name <> ''
                """
            )


            db_rows = (
                cursor.fetchall()
            )


    db_nations = {
        int(
            row[
                "nation_id"
            ]
        ):
            row

        for row in db_rows
    }


    result = []


    for nation in nations:

        db_nation = (
            db_nations.get(
                int(
                    nation[
                        "id"
                    ]
                )
            )
        )


        if not db_nation:
            continue


        result.append(
            {
                "nation_id":
                    int(
                        db_nation[
                            "nation_id"
                        ]
                    ),

                "nation_name":
                    db_nation[
                        "nation_name"
                    ],
            }
        )


    return result

def get_player_catalog_teams_by_league(
    league_id,
):

    groups = (
        get_player_filter_groups()
    )


    league = next(
        (
            item

            for item in (
                groups[
                    "leagues"
                ]
            )

            if (
                int(
                    item["id"]
                )
                ==
                int(
                    league_id
                )
            )
        ),
        None,
    )


    if not league:

        return []


    soup = (
        _get_player_stat_filter_soup(
            {
                league[
                    "field_name"
                ]:
                    league[
                        "id"
                    ],
            }
        )
    )


    official_teams = (
        _extract_ability_filter_items(
            soup,
            "teamid",
        )
    )


    official_team_names = {
        item[
            "name"
        ]
        .strip()
        .casefold()

        for item in official_teams
    }


    # =====================================
    # 우리 선수도감에 실제 존재하는 팀만
    # =====================================

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    team_color_id,
                    team_name,
                    COUNT(
                        DISTINCT sp_id
                    ) AS player_count

                FROM
                    fconline_player_teams

                GROUP BY
                    team_color_id,
                    team_name

                ORDER BY
                    team_name ASC
                """
            )


            rows = (
                cursor.fetchall()
            )


    result = []


    for row in rows:

        normalized_team_name = (
            str(
                row[
                    "team_name"
                ]
            )
            .strip()
            .casefold()
        )


        if (
            normalized_team_name
            not in official_team_names
        ):
            continue


        result.append(
            {
                "team_color_id":
                    int(
                        row[
                            "team_color_id"
                        ]
                    ),

                "team_name":
                    row[
                        "team_name"
                    ],

                "player_count":
                    int(
                        row[
                            "player_count"
                        ]
                    ),
            }
        )


    return result

def get_nation_metadata():

    response = httpx.get(
        PLAYER_STAT_URL,
        headers={
            "User-Agent":
                "Mozilla/5.0",
        },
        timeout=20.0,
        follow_redirects=True,
    )

    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )


    nations = []


    for element in soup.select(
        "a.nationality_item.selector_item"
    ):

        nation_name = (
            element.get_text(
                strip=True
            )
        )


        onclick = (
            element.get(
                "onclick",
                "",
            )
        )


        match = re.search(
            r"SetAbilitySearch\("
            r"'(\d+)'"
            r",\s*'n4NationId'",
            onclick,
        )


        if not match:

            continue


        nation_id = int(
            match.group(1)
        )


        nations.append(
            {
                "nation_id":
                    nation_id,

                "nation_name":
                    nation_name,
            }
        )


    unique_nations = {
        nation[
            "nation_id"
        ]:
            nation

        for nation in nations
    }

    existing_nation_ids = {
        nation[
            "nation_id"
        ]
        for nation
        in nations
    }


    for extra_nation in (
        EXTRA_NATIONS
    ):

        if (
            extra_nation[
                "nation_id"
            ]
            in existing_nation_ids
        ):

            continue


        nations.append(
            extra_nation.copy()
        )


    return sorted(
        unique_nations.values(),
        key=lambda item:
            item[
                "nation_id"
            ],
    )

def get_player_list_spids(
    nation_id,
    salary_min=0,
    salary_max=50,
    ovr_min=0,
    ovr_max=200,
    position_indices=None,
):

    position_filter = (
        make_position_filter(
            position_indices
        )
    )


    payload = {
        "strPlayerName":
            "",

        "strSeason":
            "",

        "strPosition":
            position_filter,

        "n4NationId":
            nation_id,

        "n1Strong":
            1,

        "n4SalaryMin":
            salary_min,

        "n4SalaryMax":
            salary_max,

        "n4OvrMin":
            ovr_min,

        "n4OvrMax":
            ovr_max,
    }


    response = httpx.post(
        PLAYER_LIST_URL,
        headers={
            "User-Agent":
                "Mozilla/5.0",

            "Referer":
                PLAYER_STAT_URL,
        },
        data=payload,
        timeout=20.0,
    )

    response.raise_for_status()


    spids = re.findall(
        r"\$\('#PlayerVs1'\)"
        r"\.val\('(\d+)'\)",
        response.text,
    )


    return list(
        dict.fromkeys(
            int(
                spid
            )

            for spid
            in spids
        )
    )

def get_enhancement_bonus(
    grade: int,
):
    return (
        ENHANCEMENT_BONUS.get(
            grade,
            0,
        )
    )


PLAYER_STAT_NAMES = [
    "속력",
    "가속력",
    "골 결정력",
    "슛 파워",
    "중거리 슛",
    "위치 선정",
    "발리슛",
    "페널티 킥",

    "짧은 패스",
    "시야",
    "크로스",
    "긴 패스",
    "프리킥",
    "커브",

    "드리블",
    "볼 컨트롤",
    "민첩성",
    "밸런스",
    "반응 속도",

    "대인 수비",
    "태클",
    "가로채기",
    "헤더",
    "슬라이딩 태클",

    "몸싸움",
    "스태미너",
    "적극성",
    "점프",
    "침착성",

    "GK 다이빙",
    "GK 핸들링",
    "GK 킥",
    "GK 반응속도",
    "GK 위치 선정",
]

PLAYER_STAT_COLUMN_MAP = {
    "속력":
        "sprint_speed",

    "가속력":
        "acceleration",

    "골 결정력":
        "finishing",

    "슛 파워":
        "shot_power",

    "중거리 슛":
        "long_shots",

    "위치 선정":
        "positioning",

    "발리슛":
        "volleys",

    "페널티 킥":
        "penalties",

    "짧은 패스":
        "short_pass",

    "시야":
        "vision",

    "크로스":
        "crossing",

    "긴 패스":
        "long_pass",

    "프리킥":
        "free_kick",

    "커브":
        "curve",

    "드리블":
        "dribbling",

    "볼 컨트롤":
        "ball_control",

    "민첩성":
        "agility",

    "밸런스":
        "balance",

    "반응 속도":
        "reactions",

    "대인 수비":
        "marking",

    "태클":
        "tackle",

    "가로채기":
        "interceptions",

    "헤더":
        "heading",

    "슬라이딩 태클":
        "sliding_tackle",

    "몸싸움":
        "strength",

    "스태미너":
        "stamina",

    "적극성":
        "aggression",

    "점프":
        "jumping",

    "침착성":
        "composure",

    "GK 다이빙":
        "gk_diving",

    "GK 핸들링":
        "gk_handling",

    "GK 킥":
        "gk_kick",

    "GK 반응속도":
        "gk_reflexes",

    "GK 위치 선정":
        "gk_positioning",
}

PLAYER_DATABASE_STAT_FILTER_MAP = {
    "sprint_speed_min":
        "sprint_speed",

    "acceleration_min":
        "acceleration",

    "finishing_min":
        "finishing",

    "shot_power_min":
        "shot_power",

    "long_shots_min":
        "long_shots",

    "positioning_min":
        "positioning",

    "volleys_min":
        "volleys",

    "penalties_min":
        "penalties",

    "short_pass_min":
        "short_pass",

    "vision_min":
        "vision",

    "crossing_min":
        "crossing",

    "long_pass_min":
        "long_pass",

    "free_kick_min":
        "free_kick",

    "curve_min":
        "curve",

    "dribbling_min":
        "dribbling",

    "ball_control_min":
        "ball_control",

    "agility_min":
        "agility",

    "balance_min":
        "balance",

    "reactions_min":
        "reactions",

    "marking_min":
        "marking",

    "tackle_min":
        "tackle",

    "interceptions_min":
        "interceptions",

    "heading_min":
        "heading",

    "sliding_tackle_min":
        "sliding_tackle",

    "strength_min":
        "strength",

    "stamina_min":
        "stamina",

    "aggression_min":
        "aggression",

    "jumping_min":
        "jumping",

    "composure_min":
        "composure",

    "gk_diving_min":
        "gk_diving",

    "gk_handling_min":
        "gk_handling",

    "gk_kick_min":
        "gk_kick",

    "gk_reflexes_min":
        "gk_reflexes",

    "gk_positioning_min":
        "gk_positioning",
}

# =========================================
# PLAYER DATABASE SEARCH
# =========================================

def get_player_catalog_ability_bonus(
    grade=1,
    adaptation=1,
    team_color=0,
):

    if grade not in ENHANCEMENT_BONUS:
        raise ValueError(
            "강화등급은 1~13 사이여야 합니다."
        )

    if adaptation not in ADAPTATION_BONUS:
        raise ValueError(
            "적응도는 1~5 사이여야 합니다."
        )

    if team_color not in TEAM_COLOR_BONUS:
        raise ValueError(
            "팀컬러는 0~9 사이여야 합니다."
        )

    return (
        ENHANCEMENT_BONUS[
            grade
        ]
        +
        ADAPTATION_BONUS[
            adaptation
        ]
        +
        TEAM_COLOR_BONUS[
            team_color
        ]
    )


def get_player_preferred_foot(
    left_foot,
    right_foot,
):

    left_foot = int(
        left_foot or 0
    )

    right_foot = int(
        right_foot or 0
    )

    if (
        left_foot
        ==
        right_foot
    ):
        return "both"

    if (
        left_foot
        >
        right_foot
    ):
        return "left"

    return "right"

def get_player_catalog_filter_options():

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다."
        )

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            # =============================
            # 실제 DB에 존재하는 시즌
            # =============================

            cursor.execute(
                """
                SELECT
                    season_id,
                    COUNT(*) AS player_count
                FROM
                    fconline_players
                GROUP BY
                    season_id
                ORDER BY
                    season_id DESC
                """
            )

            season_rows = cursor.fetchall()

            # =============================
            # 국적
            # =============================

            cursor.execute(
                """
                SELECT
                    nation_id,
                    nation_name,
                    COUNT(*) AS player_count
                FROM
                    fconline_players
                WHERE
                    nation_id IS NOT NULL
                AND
                    nation_name IS NOT NULL
                AND
                    nation_name <> ''
                GROUP BY
                    nation_id,
                    nation_name
                ORDER BY
                    nation_name ASC
                """
            )

            nation_rows = cursor.fetchall()

            # =============================
            # 소속 팀컬러
            # =============================

            cursor.execute(
                """
                SELECT
                    team_color_id,
                    team_name,
                    COUNT(
                        DISTINCT sp_id
                    ) AS player_count
                FROM
                    fconline_player_teams
                GROUP BY
                    team_color_id,
                    team_name
                ORDER BY
                    team_name ASC
                """
            )

            team_rows = cursor.fetchall()

    # =============================
    # 시즌 이름
    # =============================

    try:
        season_metadata = (
            get_season_metadata()
        )

    except Exception:
        season_metadata = {}

    seasons = []

    for row in season_rows:

        season_id = int(
            row["season_id"]
        )

        season = (
            season_metadata.get(
                season_id,
                {}
            )
        )

        seasons.append(
    {
        "season_id":
            season_id,

        "class_name":
            (
                season.get(
                    "class_name"
                )
                or
                str(
                    season_id
                )
            ),

        "season_image_url":
            season.get(
                "season_image",
                "",
            ),

        "player_count":
            int(
                row[
                    "player_count"
                ]
            ),
    }
)

        filter_groups = (
            get_player_filter_groups()
        )

    # =====================================
    # 국적 DB MAP
    # =====================================

    db_nation_map = {
        int(
            row[
                "nation_id"
            ]
        ):
            row

        for row in nation_rows
    }


    # =====================================
    # 대륙 → 국적
    # =====================================

    nation_groups = []

    mapped_nation_ids = set()


    for continent in (
        filter_groups[
            "continents"
        ]
    ):

        nations = []


        for nation in (
            continent[
                "nations"
            ]
        ):

            nation_id = int(
                nation[
                    "nation_id"
                ]
            )


            db_nation = (
                db_nation_map.get(
                    nation_id
                )
            )


            if not db_nation:
                continue


            mapped_nation_ids.add(
                nation_id
            )


            nations.append(
                {
                    "nation_id":
                        nation_id,

                    "nation_name":
                        db_nation[
                            "nation_name"
                        ],

                    "player_count":
                        int(
                            db_nation[
                                "player_count"
                            ]
                        ),
                }
            )


        if nations:

            nation_groups.append(
                {
                    "continent_id":
                        int(
                            continent[
                                "id"
                            ]
                        ),

                    "continent_name":
                        continent[
                            "name"
                        ],

                    "nations":
                        nations,
                }
            )


    # =====================================
    # 공식 분류에 없는 국적
    # =====================================

    other_nations = []


    for row in nation_rows:

        nation_id = int(
            row[
                "nation_id"
            ]
        )


        if (
            nation_id
            in mapped_nation_ids
        ):
            continue


        other_nations.append(
            {
                "nation_id":
                    nation_id,

                "nation_name":
                    row[
                        "nation_name"
                    ],

                "player_count":
                    int(
                        row[
                            "player_count"
                        ]
                    ),
            }
        )


    if other_nations:

        nation_groups.append(
            {
                "continent_id":
                    -1,

                "continent_name":
                    "기타",

                "nations":
                    other_nations,
            }
        )

    # =====================================
    # DB 팀 이름 MAP
    # =====================================

    db_team_map = {}


    for row in team_rows:

        normalized_name = (
            normalize_player_filter_name(
                row[
                    "team_name"
                ]
            )
        )


        db_team_map[
            normalized_name
        ] = row


    # =====================================
    # 리그 → 팀
    # =====================================

    team_groups = []

    mapped_team_color_ids = set()

    other_league = None


    for league in (
        filter_groups[
            "leagues"
        ]
    ):

        if (
            int(
                league[
                    "id"
                ]
            )
            ==
            76
        ):
            other_league = league
            continue


        teams = []


        for club in (
            league[
                "clubs"
            ]
        ):

            normalized_name = (
                normalize_player_filter_name(
                    club[
                        "team_name"
                    ]
                )
            )


            db_team = (
                db_team_map.get(
                    normalized_name
                )
            )


            if not db_team:
                continue


            team_color_id = int(
                db_team[
                    "team_color_id"
                ]
            )


            mapped_team_color_ids.add(
                team_color_id
            )


            teams.append(
                {
                    "team_color_id":
                        team_color_id,

                    "team_name":
                        db_team[
                            "team_name"
                        ],

                    "player_count":
                        int(
                            db_team[
                                "player_count"
                            ]
                        ),
                }
            )


        if teams:

            team_groups.append(
                {
                    "league_id":
                        int(
                            league[
                                "id"
                            ]
                        ),

                    "league_name":
                        league[
                            "name"
                        ],

                    "teams":
                        teams,
                }
            )


    # =====================================
    # 기타
    #
    # 공식 기타리그 +
    # 어디에도 매칭되지 않은 팀컬러
    # =====================================

    other_teams = []


    # 공식 기타 리그
    if other_league:

        for club in (
            other_league[
                "clubs"
            ]
        ):

            normalized_name = (
                normalize_player_filter_name(
                    club[
                        "team_name"
                    ]
                )
            )


            db_team = (
                db_team_map.get(
                    normalized_name
                )
            )


            if not db_team:
                continue


            team_color_id = int(
                db_team[
                    "team_color_id"
                ]
            )


            if (
                team_color_id
                in mapped_team_color_ids
            ):
                continue


            mapped_team_color_ids.add(
                team_color_id
            )


            other_teams.append(
                {
                    "team_color_id":
                        team_color_id,

                    "team_name":
                        db_team[
                            "team_name"
                        ],

                    "player_count":
                        int(
                            db_team[
                                "player_count"
                            ]
                        ),
                }
            )


    # 어떤 리그에도 속하지 않는 팀컬러
    for row in team_rows:

        team_color_id = int(
            row[
                "team_color_id"
            ]
        )


        if (
            team_color_id
            in mapped_team_color_ids
        ):
            continue


        other_teams.append(
            {
                "team_color_id":
                    team_color_id,

                "team_name":
                    row[
                        "team_name"
                    ],

                "player_count":
                    int(
                        row[
                            "player_count"
                        ]
                    ),
            }
        )


    if other_teams:

        other_teams.sort(
            key=lambda item:
                item[
                    "team_name"
                ]
        )


        team_groups.append(
            {
                "league_id":
                    76,

                "league_name":
                    "기타",

                "teams":
                    other_teams,
            }
        )

    return {
        "seasons":
            seasons,

        "nation_groups":
            nation_groups,

        "team_groups":
            team_groups,

        "continents":
            [
                {
                    "continent_id":
                        int(
                            item[
                                "id"
                            ]
                        ),

                    "continent_name":
                        item[
                            "name"
                        ],
                }

                for item in (
                    filter_groups[
                        "continents"
                    ]
                )
            ],

        "leagues":
            [
                {
                    "league_id":
                        int(
                            item[
                                "id"
                            ]
                        ),

                    "league_name":
                        item[
                            "name"
                        ],
                }

                for item in (
                    filter_groups[
                        "leagues"
                    ]
                )
            ],

        "nations": [
            {
                "nation_id":
                    int(
                        row[
                            "nation_id"
                        ]
                    ),

                "nation_name":
                    row[
                        "nation_name"
                    ],

                "player_count":
                    int(
                        row[
                            "player_count"
                        ]
                    ),
            }

            for row in nation_rows
        ],

        "teams": [
            {
                "team_color_id":
                    int(
                        row[
                            "team_color_id"
                        ]
                    ),

                "team_name":
                    row[
                        "team_name"
                    ],

                "player_count":
                    int(
                        row[
                            "player_count"
                        ]
                    ),
            }


            for row in team_rows
        ],
    }

def search_player_catalog(
    player_name="",
    season_id=None,
    season_ids="",
    nation_id=None,
    nation_name="",
    team_color_id=None,
    team_name="",
    position="",
    positions="",
    grade=1,
    adaptation=1,
    team_color=0,
    salary_min=None,
    salary_max=None,
    ovr_min=None,
    height_min=None,
    height_max=None,
    preferred_foot="",
    stat_mins=None,
    page=1,
    page_size=20,
):

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다."
        )

    # =====================================
    # 검색 옵션 정리
    # =====================================

    player_name = (
        str(
            player_name or ""
        )
        .strip()
    )

    nation_name = (
        str(
            nation_name or ""
        )
        .strip()
    )

    team_name = (
        str(
            team_name or ""
        )
        .strip()
    )

    position = (
        str(
            position or ""
        )
        .strip()
        .upper()
    )

    grade = int(
        grade
    )

    adaptation = int(
        adaptation
    )

    team_color = int(
        team_color
    )

    page = max(
        1,
        int(
            page
        ),
    )

    page_size = max(
        1,
        min(
            int(
                page_size
            ),
            100,
        ),
    )

    ability_bonus = (
        get_player_catalog_ability_bonus(
            grade=
                grade,

            adaptation=
                adaptation,

            team_color=
                team_color,
        )
    )

    preferred_foot = (
        str(
            preferred_foot or ""
        )
        .strip()
        .lower()
    )

    if (
        preferred_foot
        not in {
            "",
            "left",
            "right",
            "both",
        }
    ):
        raise ValueError(
            "주발 조건이 올바르지 않습니다."
        )

    stat_mins = (
        stat_mins
        or {}
    )

    # =====================================
    # WHERE
    # =====================================

    where_clauses = [
        "TRUE",
    ]

    query_params = []

    # =====================================
    # 선수명 다중 검색
    # 메시, 호날두 → 둘 다 검색
    # =====================================

    player_names = [
        name.strip()

        for name in re.split(
            r"[,，]",
            player_name,
        )

        if name.strip()
    ]


    if player_names:

        name_clauses = []

        for name in player_names:

            name_clauses.append(
                """
                p.player_name ILIKE %s
                """
            )

            query_params.append(
                f"%{name}%"
            )


        where_clauses.append(
            "("
            +
            " OR ".join(
                name_clauses
            )
            +
            ")"
        )

    if season_id is not None:

        where_clauses.append(
            """
            p.season_id = %s
            """
        )

        query_params.append(
            int(
                season_id
            )
        )

    # =====================================
    # 다중 시즌
    # =====================================

    season_id_list = [
        int(value)

        for value in str(
            season_ids or ""
        ).split(",")

        if value.strip()
    ]


    if season_id_list:

        where_clauses.append(
            """
            p.season_id = ANY(%s)
            """
        )

        query_params.append(
            season_id_list
        )


    if nation_id is not None:

        where_clauses.append(
            """
            p.nation_id = %s
            """
        )

        query_params.append(
            int(
                nation_id
            )
        )

    if nation_name:

        where_clauses.append(
            """
            p.nation_name
            ILIKE %s
            """
        )

        query_params.append(
            f"%{nation_name}%"
        )

    if position:

        where_clauses.append(
            """
            p.position = %s
            """
        )

        query_params.append(
            position
        )

    if (
        team_color_id
        is not None
    ):

        where_clauses.append(
            """
            EXISTS (
                SELECT 1

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
            """
        )

        query_params.append(
            int(
                team_color_id
            )
        )

    # =====================================
    # 다중 포지션
    # =====================================

    position_list = [
        value
            .strip()
            .upper()

        for value in str(
            positions or ""
        ).split(",")

        if value.strip()
    ]


    if position_list:

        where_clauses.append(
            """
            p.position = ANY(%s)
            """
        )

        query_params.append(
            position_list
        )


    if team_name:

        where_clauses.append(
            """
            EXISTS (
                SELECT 1

                FROM
                    fconline_player_teams
                    AS team_filter

                WHERE
                    team_filter.sp_id
                    =
                    p.sp_id

                AND
                    team_filter.team_name
                    ILIKE
                    %s
            )
            """
        )

        query_params.append(
            f"%{team_name}%"
        )

    # =====================================
    # 상세 조건
    # =====================================

    if salary_min is not None:

        where_clauses.append(
            """
            p.salary >= %s
            """
        )

        query_params.append(
            int(
                salary_min
            )
        )


    if salary_max is not None:

        where_clauses.append(
            """
            p.salary <= %s
            """
        )

        query_params.append(
            int(
                salary_max
            )
        )


    # OVR은 현재 선택한
    # 강화 + 적응도 + 팀컬러 보정 적용 후 기준
    if ovr_min is not None:

        where_clauses.append(
            """
            (
                p.ovr
                +
                %s
            )
            >=
            %s
            """
        )

        query_params.extend(
            [
                ability_bonus,
                int(
                    ovr_min
                ),
            ]
        )


    if height_min is not None:

        where_clauses.append(
            """
            p.height >= %s
            """
        )

        query_params.append(
            int(
                height_min
            )
        )


    if height_max is not None:

        where_clauses.append(
            """
            p.height <= %s
            """
        )

        query_params.append(
            int(
                height_max
            )
        )


    # =====================================
    # 주발
    # =====================================

    if preferred_foot == "left":

        where_clauses.append(
            """
            p.left_foot
            >
            p.right_foot
            """
        )


    elif preferred_foot == "right":

        where_clauses.append(
            """
            p.right_foot
            >
            p.left_foot
            """
        )


    elif preferred_foot == "both":

        where_clauses.append(
            """
            p.left_foot
            =
            p.right_foot
            """
        )


    # =====================================
    # 34개 세부 능력치
    #
    # DB는 1강/적응도1/팀컬러0 기준이므로
    # 현재 ability_bonus를 더한 값으로 검색
    # =====================================

    allowed_stat_columns = set(
        PLAYER_DATABASE_STAT_FILTER_MAP
        .values()
    )


    for (
        stat_column,
        minimum_value,
    ) in stat_mins.items():

        if (
            stat_column
            not in allowed_stat_columns
        ):
            continue

        if minimum_value is None:
            continue


        where_clauses.append(
            f"""
            (
                COALESCE(
                    p.{stat_column},
                    0
                )
                +
                %s
            )
            >=
            %s
            """
        )

        query_params.extend(
            [
                ability_bonus,
                int(
                    minimum_value
                ),
            ]
        )



    where_sql = (
        "\nAND\n".join(
            where_clauses
        )
    )

    # =====================================
    # PAGINATION
    # =====================================

    offset = (
        page - 1
    ) * page_size

    # =====================================
    # DB SEARCH
    # =====================================

    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            # =============================
            # 전체 검색 결과 수
            # =============================

            cursor.execute(
                f"""
                SELECT
                    COUNT(*) AS count

                FROM
                    fconline_players AS p

                WHERE
                    {where_sql}
                """,
                query_params,
            )

            count_row = (
                cursor.fetchone()
            )

            total_count = int(
                count_row[
                    "count"
                ]
                or 0
            )

            # =============================
            # 현재 페이지 선수
            # =============================

            cursor.execute(
                f"""
                SELECT
                    p.*

                FROM
                    fconline_players AS p

                WHERE
                    {where_sql}

                ORDER BY
                    p.ovr DESC,
                    p.salary DESC,
                    p.player_name ASC,
                    p.sp_id DESC

                LIMIT %s
                OFFSET %s
                """,
                [
                    *query_params,
                    page_size,
                    offset,
                ],
            )

            player_rows = (
                cursor.fetchall()
            )

            # =============================
            # 현재 페이지 팀컬러
            # =============================

            team_color_map = {}

            sp_ids = [
                int(
                    player[
                        "sp_id"
                    ]
                )

                for player
                in player_rows
            ]

            if sp_ids:

                cursor.execute(
                    """
                    SELECT
                        sp_id,
                        team_color_id,
                        team_name

                    FROM
                        fconline_player_teams

                    WHERE
                        sp_id
                        =
                        ANY(%s)

                    ORDER BY
                        sp_id,
                        team_name
                    """,
                    (
                        sp_ids,
                    ),
                )

                for team_row in (
                    cursor.fetchall()
                ):

                    sp_id = int(
                        team_row[
                            "sp_id"
                        ]
                    )

                    team_color_map.setdefault(
                        sp_id,
                        [],
                    ).append(
                        {
                            "team_color_id":
                                team_row[
                                    "team_color_id"
                                ],

                            "team_name":
                                team_row[
                                    "team_name"
                                ],
                        }
                    )

    # =====================================
    # RESPONSE
    # =====================================

    players = []

    for player_row in player_rows:

        sp_id = int(
            player_row[
                "sp_id"
            ]
        )

        base_ovr = int(
            player_row[
                "ovr"
            ]
            or 0
        )

        left_foot = int(
            player_row[
                "left_foot"
            ]
            or 0
        )

        right_foot = int(
            player_row[
                "right_foot"
            ]
            or 0
        )

        stats = {}

        for (
            stat_name,
            stat_column,
        ) in (
            PLAYER_STAT_COLUMN_MAP
            .items()
        ):

            base_stat = int(
                player_row.get(
                    stat_column
                )
                or 0
            )

            stats[
                stat_name
            ] = (
                base_stat
                +
                ability_bonus
            )

        players.append(
            {
                "sp_id":
                    sp_id,

                "player_name":
                    player_row[
                        "player_name"
                    ],

                "season_id":
                    int(
                        player_row[
                            "season_id"
                        ]
                    ),

                "image_url":
                    player_row[
                        "image_url"
                    ],

                "position":
                    player_row[
                        "position"
                    ],

                "salary":
                    int(
                        player_row[
                            "salary"
                        ]
                        or 0
                    ),

                # DB 원본 OVR
                "base_ovr":
                    base_ovr,

                # 강화/적응도/팀컬러 적용
                "ovr":
                    (
                        base_ovr
                        +
                        ability_bonus
                    ),

                "height":
                    int(
                        player_row[
                            "height"
                        ]
                        or 0
                    ),

                "weight":
                    int(
                        player_row[
                            "weight"
                        ]
                        or 0
                    ),

                "left_foot":
                    left_foot,

                "right_foot":
                    right_foot,

                "preferred_foot":
                    get_player_preferred_foot(
                        left_foot,
                        right_foot,
                    ),

                "nation_id":
                    player_row[
                        "nation_id"
                    ],

                "nation_name":
                    player_row[
                        "nation_name"
                    ],

                "skill_moves":
                    int(
                        player_row[
                            "skill_moves"
                        ]
                        or 0
                    ),

                "traits":
                    (
                        player_row[
                            "traits"
                        ]
                        or []
                    ),

                "grade":
                    grade,

                "adaptation":
                    adaptation,

                "team_color_bonus":
                    team_color,

                "ability_bonus":
                    ability_bonus,

                "stats":
                    stats,

                "team_colors":
                    team_color_map.get(
                        sp_id,
                        [],
                    ),
            }
        )

    page_count = (
        (
            total_count
            +
            page_size
            -
            1
        )
        //
        page_size
    )

    return {
        "total_count":
            total_count,

        "page":
            page,

        "page_size":
            page_size,

        "page_count":
            page_count,

        "grade":
            grade,

        "adaptation":
            adaptation,

        "team_color_bonus":
            team_color,

        "ability_bonus":
            ability_bonus,

        "players":
            players,
    }


def text_or_empty(
    soup,
    selector,
):
    element = soup.select_one(
        selector
    )

    if not element:
        return ""

    return element.get_text(
        strip=True
    )


def to_int(
    value,
):
    if not value:
        return 0

    number_text = re.sub(
        r"[^0-9-]",
        "",
        str(value),
    )

    if not number_text:
        return 0

    return int(
        number_text
    )

def get_season_metadata():

    global SEASON_METADATA_CACHE


    if (
        SEASON_METADATA_CACHE
        is not None
    ):
        return (
            SEASON_METADATA_CACHE
        )


    response = httpx.get(
        SEASON_METADATA_URL,
        timeout=20.0,
    )


    response.raise_for_status()


    SEASON_METADATA_CACHE = {
        int(
            item[
                "seasonId"
            ]
        ):
            {
                "class_name":
                    item.get(
                        "className",
                        "",
                    ),

                "season_image":
                    item.get(
                        "seasonImg",
                        "",
                    ),
            }

        for item
        in response.json()
    }


    return (
        SEASON_METADATA_CACHE
    )


# =========================================
# FC ONLINE 전체 SPID 목록
# =========================================

def get_all_player_cards():

    response = httpx.get(
        SPID_METADATA_URL,
        timeout=30.0,
    )

    response.raise_for_status()


    player_cards = []


    for item in response.json():

        sp_id = item.get(
            "id"
        )

        player_name = (
            item.get(
                "name",
                "",
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


        player_cards.append(
            {
                "sp_id":
                    sp_id,

                "player_name":
                    str(
                        player_name
                    ).strip(),
            }
        )


    player_cards.sort(
        key=lambda item:
            item[
                "sp_id"
            ],
    )


    return player_cards


# =========================================
# 이미 수집된 선수 SPID
# =========================================

def get_saved_player_ids():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id

                FROM fconline_players
                """
            )


            return {
                int(
                    row[
                        0
                    ]
                )

                for row
                in cursor.fetchall()
            }

def get_pending_player_cards(
    limit=10,
):

    all_cards = (
        get_all_player_cards()
    )


    saved_ids = (
        get_saved_player_ids()
    )


    pending_cards = [
        card

        for card
        in all_cards

        if (
            card[
                "sp_id"
            ]
            not in saved_ids
        )
    ]


    return (
        pending_cards[
            :limit
        ],
        len(
            all_cards
        ),
        len(
            saved_ids
        ),
        len(
            pending_cards
        ),
    )

def sync_player_catalog(
    batch_size=100,
):

    all_cards = (
        get_all_player_cards()
    )


    saved_ids = (
        get_saved_player_ids()
    )


    sync_states = (
        get_player_sync_states()
    )


    nation_map = (
        get_saved_nation_map()
    )


    mapped_count = sum(
        1

        for card
        in all_cards

        if (
            card[
                "sp_id"
            ]
            in nation_map
        )
    )


    missing_nation_count = (
        len(
            all_cards
        )
        -
        mapped_count
    )


    pending_cards = []

    blocked_failed_count = 0


    for card in (
        all_cards
    ):

        sp_id = (
            card[
                "sp_id"
            ]
        )


        # 이미 실제 선수 DB에 있으면 완료
        if sp_id in saved_ids:

            continue


        state = (
            sync_states.get(
                sp_id
            )
        )


        if state:

            attempt_count = int(
                state[
                    "attempt_count"
                ]
                or 0
            )


            if (
                attempt_count
                >=
                PLAYER_MAX_SYNC_ATTEMPTS

                and

                state[
                    "status"
                ]
                != "completed"
            ):

                blocked_failed_count += 1

                continue


        pending_cards.append(
            card
        )


        if (
            len(
                pending_cards
            )
            >=
            batch_size
        ):

            break


    print()
    print(
        "전체 카드:",
        len(
            all_cards
        ),
    )

    print(
        "기존 저장:",
        len(
            saved_ids
        ),
    )

    print(
        "국적 매핑:",
        mapped_count,
    )

    print(
        "국적 미매핑:",
        missing_nation_count,
    )

    print(
        "재시도 한도 초과:",
        blocked_failed_count,
    )

    print(
        "이번 수집:",
        len(
            pending_cards
        ),
    )


    success_count = 0
    failure_count = 0


    for (
        index,
        card
    ) in enumerate(
        pending_cards,
        start=1,
    ):

        sp_id = (
            card[
                "sp_id"
            ]
        )

        metadata_name = (
            card[
                "player_name"
            ]
        )


        print()
        print(
            "--------------------------------------"
        )

        print(
            (
                f"[{index}/"
                f"{len(pending_cards)}] "
                f"{sp_id} / "
                f"{metadata_name}"
            )
        )


        set_player_sync_running(
            sp_id=
                sp_id,

            player_name=
                metadata_name,
        )


        try:

            player = (
                get_player_ability(
                    sp_id,
                    grade=1,
                )
            )


            validate_collected_player(
                player
            )


            # =========================
            # 공식 국적 매핑으로 교체
            # =========================

            nation = (
                nation_map.get(
                    sp_id
                )
            )


            if nation:

                player[
                    "nation_id"
                ] = (
                    nation[
                        "nation_id"
                    ]
                )

                player[
                    "nation_name"
                ] = (
                    nation[
                        "nation_name"
                    ]
                )


            else:

                player[
                    "nation_id"
                ] = None


            # =========================
            # 선수 이미지
            # =========================

            player[
                "image_url"
            ] = (
                PLAYER_IMAGE_URL_TEMPLATE.format(
                    sp_id=sp_id
                )
            )


            save_player_to_database(
                player
            )


            set_player_sync_completed(
                sp_id
            )


            success_count += 1


            print(
                (
                    "SUCCESS"
                    f" | {player['season_name']}"
                    f" | {player['position']}"
                    f" | OVR {player['ovr']}"
                    f" | {player.get('nation_name')}"
                )
            )


        except Exception as error:

            failure_count += 1


            set_player_sync_failed(
                sp_id=
                    sp_id,

                error=
                    error,
            )


            print(
                "FAILED"
            )

            print(
                "오류:",
                repr(
                    error
                ),
            )


        finally:

            time.sleep(
                PLAYER_REQUEST_DELAY_SECONDS
            )


    print()
    print(
        "======================================"
    )

    print(
        "PLAYER SYNC COMPLETE"
    )

    print(
        "성공:",
        success_count,
    )

    print(
        "실패:",
        failure_count,
    )

    print(
        "======================================"
    )


def post_with_retry(
    url,
    *,
    data,
    headers,
    timeout=20.0,
):

    last_error = None


    for attempt in range(
        1,
        len(
            PLAYER_HTTP_RETRY_DELAYS
        ) + 1,
    ):

        try:

            response = httpx.post(
                url,
                data=data,
                headers=headers,
                timeout=timeout,
            )


            if (
                response.status_code
                == 429
                or
                response.status_code
                >= 500
            ):

                response.raise_for_status()


            response.raise_for_status()


            return response


        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
        ) as error:

            last_error = error


            if (
                attempt
                >=
                len(
                    PLAYER_HTTP_RETRY_DELAYS
                )
            ):

                raise


            delay = (
                PLAYER_HTTP_RETRY_DELAYS[
                    attempt - 1
                ]
            )


            print(
                (
                    "HTTP 재시도 "
                    f"{attempt}/"
                    f"{len(PLAYER_HTTP_RETRY_DELAYS)}"
                    f" | {delay}초 대기"
                )
            )


            time.sleep(
                delay
            )


    raise last_error

# =========================================
# 선수 능력치 조회
# =========================================

def get_player_ability(
    sp_id: int,
    grade: int = 1,
):

    headers = {
        "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/150.0.0.0 "
                "Safari/537.36"
            ),

        "Referer":
            (
                "https://fconline.nexon.com/"
                f"datacenter/PlayerInfo?spid={sp_id}"
            ),
    }


    payload = {
        "spid":
            str(
                sp_id
            ),

        "n1Strong":
            str(
                grade
            ),

        "n1Grow":
            "0",

        "n4TeamColorId":
            "0",

        "n4TeamColorLv":
            "0",

        "n1Change":
            "0",

        "strPlayerImg":
            (
                "https://fo4.dn.nexoncdn.co.kr/"
                "live/externalAssets/common/"
                f"playersAction/p{sp_id}.png"
            ),

        "rd":
            "0",
    }


    response = post_with_retry(
        PLAYER_ABILITY_URL,
        data=payload,
        headers=headers,
        timeout=20.0,
    )


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # =====================================
    # 시즌
    # 공식 NEXON 메타데이터 사용
    # =====================================

    season_id = (
        sp_id
        //
        1_000_000
    )


    season_metadata = (
        get_season_metadata()
    )


    season_info = (
        season_metadata.get(
            season_id,
            {},
        )
    )


    season_name = (
        season_info.get(
            "class_name",
            "",
        )
    )


    season_image_url = (
        season_info.get(
            "season_image",
            "",
        )
    )


    # =====================================
    # 소속 팀컬러
    # =====================================

    team_colors = []


    team_color_container = (
        soup.select_one(
            "div.tdefault"
        )
    )

    team_color_debug = []


    if team_color_container:

        team_color_elements = (
            team_color_container.select(
                (
                    "div.selector_list "
                    "ul li "
                    "a.selector_item"
                )
            )
        )

    # =====================================
    # 국적
    # 팀컬러 ID 2000 ~ 2999
    # =====================================

    nation_id = None
    nation_name = None


    for element in (
        team_color_elements
    ):

        data_no = (
            element.get(
                "data-no"
            )
        )


        if not data_no:

            continue


        try:

            team_color_id = int(
                data_no
            )

        except ValueError:

            continue


        if (
            2000
            <= team_color_id
            < 3000
        ):

            nation_id = (
                team_color_id
            )

            nation_name = (
                element.get_text(
                    strip=True
                )
            )

            break


        team_colors = [
            element.get_text(
                strip=True
            )

            for element
            in team_color_elements
        ]


        for element in (
            team_color_elements
        ):

            team_color_debug.append(
                {
                    "name":
                        element.get_text(
                            strip=True
                        ),

                    "attrs":
                        dict(
                            element.attrs
                        ),

                    "parent_attrs":
                        dict(
                            element.parent.attrs
                        )
                        if element.parent
                        else {},
                }
            )


    team_colors = [
        team_name

        for team_name
        in team_colors

        if team_name not in (
            "소속 팀컬러",
            "단일팀",
            "단일국가",
        )
    ]

    # =====================================
    # 최종 팀컬러 ID + 이름
    # 시즌 팀컬러 제거 이후 생성
    # =====================================

    final_team_name_set = {
        team_name
        .strip()
        .casefold()

        for team_name
        in team_colors
    }


    team_color_items = []


    for element in (
        team_color_elements
    ):

        team_name = (
            element.get_text(
                strip=True
            )
        )


        normalized_team_name = (
            team_name
            .strip()
            .casefold()
        )


        if (
            normalized_team_name
            not in final_team_name_set
        ):

            continue


        data_no = (
            element.get(
                "data-no"
            )
        )


        if not data_no:

            continue


        try:

            team_color_id = int(
                data_no
            )

        except ValueError:

            continue


        team_color_items.append(
            {
                "team_color_id":
                    team_color_id,

                "team_name":
                    team_name,
            }
        )


    # =====================================
    # 팀컬러 목록에서 시즌명 제거
    # =====================================

    season_names = set()


    for season_data in (
        season_metadata.values()
    ):

        class_name = (
            season_data.get(
                "class_name",
                "",
            ).strip()
        )


        if not class_name:

            continue


        # 예:
        # PTG (Path to Glory)
        # 전체 이름도 등록
        season_names.add(
            class_name.casefold()
        )


        # 괄호 앞 약칭
        # PTG
        if " (" in class_name:

            short_name = (
                class_name
                .split(
                    " (",
                    1,
                )[0]
                .strip()
            )


            if short_name:

                season_names.add(
                    short_name.casefold()
                )


        # 괄호 안 전체 시즌명
        # Path to Glory
        season_match = re.search(
            r"\(([^()]*)\)\s*$",
            class_name,
        )


        if season_match:

            full_name = (
                season_match
                .group(1)
                .strip()
            )


            if full_name:

                season_names.add(
                    full_name.casefold()
                )


    team_colors = [
        team_name

        for team_name
        in team_colors

        if (
            team_name
            .strip()
            .casefold()
            not in season_names
        )
    ]


    # =====================================
    # 개인기
    # =====================================

    skill_text = text_or_empty(
        soup,
        "span.etc.skill span",
    )


    skill_moves = (
        skill_text.count(
            "★"
        )
    )


    # =====================================
    # 특성
    # =====================================

    traits = [
        element.get_text(
            strip=True
        )

        for element
        in soup.select(
            "div.skill_wrap span.desc"
        )

        if element.get_text(
            strip=True
        )
    ]


    # =====================================
    # 선수명
    # =====================================

    player_name = text_or_empty(
        soup,
        (
            "div.nameWrap div.name, "
            ".info_line.info_name div.name"
        ),
    )

    # =====================================
    # 포지션 / OVR
    # =====================================

    position = text_or_empty(
        soup,
        (
            "div.content_header div.position, "
            ".info_line.info_ab "
            "span.position .txt"
        ),
    )


    ovr_text = text_or_empty(
        soup,
        (
            "div.content_header "
            ".ovr.value, "
            ".info_line.info_ab "
            "span.value"
        ),
    )


    ovr = to_int(
        ovr_text
    )


    # =====================================
    # 급여
    # =====================================

    salary_element = (
        soup.select_one(
            (
                "div.playerCardInfoSide "
                "div.pay span"
            )
        )
        or
        soup.select_one(
            "div.side_utils div.pay_side"
        )
    )


    salary = (
        to_int(
            salary_element.get_text(
                strip=True
            )
        )
        if salary_element
        else 0
    )


    # =====================================
    # 신체 정보
    # =====================================

    height = to_int(
        text_or_empty(
            soup,
            "span.etc.height",
        )
    )


    weight = to_int(
        text_or_empty(
            soup,
            "span.etc.weight",
        )
    )


    foot_text = text_or_empty(
        soup,
        "span.etc.foot",
    )


    left_foot = 0
    right_foot = 0


    foot_match = re.search(
        r"L(\d+)\s*[-–]\s*R(\d+)",
        foot_text,
    )


    if foot_match:

        left_foot = int(
            foot_match.group(
                1
            )
        )

        right_foot = int(
            foot_match.group(
                2
            )
        )


    # =====================================
    # 능력치
    # =====================================

    stats = {
        stat_name:
            0

        for stat_name
        in PLAYER_STAT_NAMES
    }


    ability_elements = (
        soup.select(
            "ul.data_wrap_playerinfo li.ab"
        )
    )


    for ability_element in (
        ability_elements
    ):

        name_element = (
            ability_element.select_one(
                "div.txt"
            )
        )


        value_element = (
            ability_element.select_one(
                "div.value"
            )
        )


        if (
            not name_element
            or
            not value_element
        ):
            continue


        stat_name = (
            name_element.get_text(
                strip=True
            )
        )


        if stat_name not in stats:
            continue


        stat_value_text = (
            value_element.get_text(
                " ",
                strip=True,
            )
        )


        stat_value = to_int(
            stat_value_text
                .split(
                    " "
                )[0]
        )


        stats[
            stat_name
        ] = stat_value


    # =====================================
    # 팀컬러 최종 정합성 보정
    #
    # team_colors에 최종적으로 남은 팀만
    # team_color_items에도 유지
    # =====================================

    final_team_names = {
        team_name
        .strip()
        .casefold()

        for team_name
        in team_colors
    }


    team_color_items = [
        team_color

        for team_color
        in team_color_items

        if (
            str(
                team_color.get(
                    "team_name",
                    "",
                )
            )
            .strip()
            .casefold()
            in final_team_names
        )
    ]

    # =====================================
    # 결과
    # =====================================

    return {
        "sp_id":
            sp_id,

        "grade":
            grade,

        "player_name":
            player_name,

        "season_name":
            season_name,

        "season_image_url":
            season_image_url,

        "nation_id":
            nation_id,

        "nation_name":
            nation_name,

        "position":
            position,

        "ovr":
            ovr,

        "salary":
            salary,

        "height":
            height,

        "weight":
            weight,

        "left_foot":
            left_foot,

        "right_foot":
            right_foot,

        "skill_moves":
            skill_moves,

        "traits":
            traits,

        "team_colors":
            team_colors,

        "team_color_items":
            team_color_items,

        "ability_count":
            len(
                ability_elements
            ),

        "stats":
            stats,

        "team_color_debug":
            team_color_debug,

        "image_url":
            PLAYER_IMAGE_URL_TEMPLATE.format(
                sp_id=sp_id
            ),

    }

# =========================================
# 선수도감
# Neon UPSERT
# =========================================

def save_player_to_database(
    player,
):

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    sp_id = int(
        player[
            "sp_id"
        ]
    )


    season_id = (
        sp_id
        //
        1_000_000
    )


    stats = (
        player[
            "stats"
        ]
    )


    values = {
        "sp_id":
            sp_id,

        "player_name":
            player[
                "player_name"
            ],

        "season_id":
            season_id,

        "nation_id":
            player.get(
                "nation_id"
            ),

        "nation_name":
            player.get(
                "nation_name"
            ),

        "position":
            player[
                "position"
            ],

        "salary":
            player[
                "salary"
            ],

        "ovr":
            player[
                "ovr"
            ],

        "height":
            player[
                "height"
            ],

        "weight":
            player[
                "weight"
            ],

        "left_foot":
            player[
                "left_foot"
            ],

        "right_foot":
            player[
                "right_foot"
            ],

        "skill_moves":
            player.get(
                "skill_moves",
                0,
            ),

        "traits":
            player.get(
                "traits",
                [],
            ),

        "image_url":
            player.get(
                "image_url"
            ),
    }


    for (
        stat_name,
        column_name
    ) in (
        PLAYER_STAT_COLUMN_MAP.items()
    ):

        values[
            column_name
        ] = (
            stats.get(
                stat_name,
                0,
            )
        )


    columns = [
        "sp_id",
        "player_name",
        "season_id",
        "nation_id",
        "nation_name",
        "image_url",
        "position",
        "salary",
        "ovr",
        "height",
        "weight",
        "left_foot",
        "right_foot",
        "skill_moves",
        "traits",

        *PLAYER_STAT_COLUMN_MAP.values(),
    ]


    column_sql = (
        ", ".join(
            columns
        )
    )


    placeholder_sql = (
        ", ".join(
            [
                "%s"
                for _
                in columns
            ]
        )
    )


    update_columns = [
        column
        for column
        in columns
        if column != "sp_id"
    ]


    update_sql = (
        ", ".join(
            (
                f"{column} = "
                f"EXCLUDED.{column}"
            )
            for column
            in update_columns
        )
    )


    sql = f"""
        INSERT INTO fconline_players (
            {column_sql}
        )

        VALUES (
            {placeholder_sql}
        )

        ON CONFLICT (
            sp_id
        )

        DO UPDATE SET
            {update_sql},
            updated_at = NOW()

        RETURNING
            sp_id,
            player_name,
            season_id,
            position,
            salary,
            ovr,
            height,
            weight,
            left_foot,
            right_foot,
            sprint_speed,
            acceleration,
            finishing,
            updated_at
    """


    parameters = [
        values[
            column
        ]

        for column
        in columns
    ]


    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                sql,
                parameters,
            )


            saved_player = (
                cursor.fetchone()
            )

            # =============================
            # 기존 팀컬러 초기화
            # =============================

            cursor.execute(
                """
                DELETE FROM
                    fconline_player_teams

                WHERE sp_id = %s
                """,
                (
                    sp_id,
                ),
            )


            valid_team_names = {
                team_name
                .strip()
                .casefold()

                for team_name
                in player.get(
                    "team_colors",
                    [],
                )
            }


            # =============================
            # 현재 팀컬러 저장
            # =============================

            for team_color in (
                player.get(
                    "team_color_items",
                    [],
                )
            ):


                team_name = (
                    team_color.get(
                        "team_name",
                        "",
                    )
                )


                if (
                    team_name
                    .strip()
                    .casefold()
                    not in valid_team_names
                ):

                    continue

                cursor.execute(
                    """
                    INSERT INTO
                        fconline_player_teams (
                            sp_id,
                            team_color_id,
                            team_name
                        )

                    VALUES (
                        %s,
                        %s,
                        %s
                    )

                    ON CONFLICT (
                        sp_id,
                        team_name
                    )

                    DO UPDATE SET
                        team_color_id =
                            EXCLUDED.team_color_id
                    """,
                    (
                        sp_id,

                        team_color[
                            "team_color_id"
                        ],

                        team_color[
                            "team_name"
                        ],
                    ),
                )


        connection.commit()


    return saved_player

# =========================================
# 선수도감
# Neon 단일 선수 확인
# =========================================

def get_saved_player(
    sp_id: int,
):

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id,
                    player_name,
                    season_id,
                    nation_id,
                    nation_name,
                    position,
                    salary,
                    ovr,
                    height,
                    weight,
                    left_foot,
                    right_foot,
                    skill_moves,
                    traits,

                    sprint_speed,
                    acceleration,
                    finishing,
                    shot_power,
                    long_shots,
                    short_pass,
                    dribbling,
                    marking,
                    strength,
                    stamina,

                    created_at,
                    updated_at

                FROM fconline_players

                WHERE sp_id = %s
                """,
                (
                    sp_id,
                ),
            )


            player = (
                cursor.fetchone()
            )


            if not player:
                return None


            cursor.execute(
                """
                SELECT
                    team_color_id,
                    team_name

                FROM fconline_player_teams

                WHERE sp_id = %s

                ORDER BY
                    team_name
                """,
                (
                    sp_id,
                ),
            )


            team_rows = (
                cursor.fetchall()
            )


            player[
                "team_colors"
            ] = [
                row[
                    "team_name"
                ]

                for row
                in team_rows
            ]


            player[
                "team_color_items"
            ] = [
                {
                    "team_color_id":
                        row[
                            "team_color_id"
                        ],

                    "team_name":
                        row[
                            "team_name"
                        ],
                }

                for row
                in team_rows
            ]


            return player


def get_saved_nation_map():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor(
            row_factory=dict_row,
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id,
                    nation_id,
                    nation_name

                FROM
                    fconline_player_nations
                """
            )


            rows = (
                cursor.fetchall()
            )


    return {
        int(
            row[
                "sp_id"
            ]
        ): {
            "nation_id":
                int(
                    row[
                        "nation_id"
                    ]
                ),

            "nation_name":
                row[
                    "nation_name"
                ],
        }

        for row
        in rows
    }

def get_player_sync_states():

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor(
            row_factory=dict_row,
        ) as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id,
                    status,
                    attempt_count

                FROM
                    fconline_player_sync_state
                """
            )


            rows = (
                cursor.fetchall()
            )


    return {
        int(
            row[
                "sp_id"
            ]
        ): row

        for row
        in rows
    }

def set_player_sync_running(
    sp_id,
    player_name,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

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
                        last_error,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    'running',
                    1,
                    NOW(),
                    NOW(),
                    NULL,
                    NOW()
                )

                ON CONFLICT (
                    sp_id
                )

                DO UPDATE SET
                    player_name =
                        EXCLUDED.player_name,

                    status =
                        'running',

                    attempt_count =
                        fconline_player_sync_state.attempt_count
                        + 1,

                    last_attempt_at =
                        NOW(),

                    last_error =
                        NULL,

                    updated_at =
                        NOW()
                """,
                (
                    sp_id,
                    player_name,
                ),
            )


        connection.commit()

def set_player_sync_completed(
    sp_id,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE
                    fconline_player_sync_state

                SET
                    status =
                        'completed',

                    completed_at =
                        NOW(),

                    last_error =
                        NULL,

                    updated_at =
                        NOW()

                WHERE
                    sp_id = %s
                """,
                (
                    sp_id,
                ),
            )


        connection.commit()

def set_player_sync_failed(
    sp_id,
    error,
):

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                UPDATE
                    fconline_player_sync_state

                SET
                    status =
                        'failed',

                    last_error =
                        %s,

                    updated_at =
                        NOW()

                WHERE
                    sp_id = %s
                """,
                (
                    str(
                        error
                    )[:2000],

                    sp_id,
                ),
            )


        connection.commit()

def validate_collected_player(
    player,
):

    if not player.get(
        "player_name"
    ):

        raise ValueError(
            "선수명이 비어 있습니다."
        )


    if not player.get(
        "position"
    ):

        raise ValueError(
            "포지션이 비어 있습니다."
        )


    if int(
        player.get(
            "ovr",
            0,
        )
    ) <= 0:

        raise ValueError(
            "OVR이 정상적이지 않습니다."
        )


    stats = (
        player.get(
            "stats",
            {}
        )
    )


    if len(
        stats
    ) < 34:

        raise ValueError(
            (
                "능력치 파싱 개수가 "
                f"부족합니다: {len(stats)}"
            )
        )

# =========================================
#  실행
# =========================================

if __name__ == "__main__":

    print()
    print(
        "======================================"
    )

    print(
        "FC ONLINE PLAYER SYNC"
    )

    print(
        "======================================"
    )


    sync_player_catalog(
        batch_size=80000,
    )