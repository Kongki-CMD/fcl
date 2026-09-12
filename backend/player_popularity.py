import re

from datetime import (
    date,
    datetime,
    timedelta,
)

from zoneinfo import ZoneInfo

import httpx

from bs4 import BeautifulSoup


DAILY_SQUAD_URL = (
    "https://fconline.nexon.com/"
    "datacenter/dailysquad"
)

POSITION_POPULARITY_URL = (
    "https://fconline.nexon.com/"
    "Datacenter/BestUsePositionPlayer"
)


POSITION_CODE_MAP = {
    "ST": 25,
    "CF": 21,
    "LW": 27,
    "RW": 23,

    "CM": 14,
    "CAM": 18,
    "CDM": 10,
    "LM": 16,
    "RM": 12,

    "CB": 5,
    "LB": 7,
    "RB": 3,
    "LWB": 8,
    "RWB": 2,

    "GK": 0,
}


SPID_HREF_PATTERN = re.compile(
    r"[?&]spid=(\d+)",
    re.IGNORECASE,
)

SEASON_METADATA_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/seasonid.json"
)

KST = ZoneInfo(
    "Asia/Seoul"
)

def get_popularity_snapshot_date():

    return (
        datetime.now(
            KST
        ).date()
        -
        timedelta(
            days=1
        )
    )


PLAYER_POSITIONS = {
    "ST",
    "CF",
    "LW",
    "RW",
    "CM",
    "CAM",
    "CDM",
    "LM",
    "RM",
    "CB",
    "LB",
    "RB",
    "LWB",
    "RWB",
    "GK",
}


USAGE_PATTERN = re.compile(
    r"([\d,]+)명\s*\(([\d.]+)%\)"
)


SPID_PATTERN = re.compile(
    r"(?:playersAction|players)/"
    r"p?(\d+)"
    r"(?:_\d+)?"
    r"\.png",
    re.IGNORECASE,
)

SEASON_IMAGE_PATTERN = re.compile(
    r"/season/"
    r"([^/?]+?)"
    r"(?:_big)?"
    r"\.png",
    re.IGNORECASE,
)

POSITION_PATTERN = re.compile(
    r"(?<![A-Z])"
    r"(ST|CF|LW|RW|CM|CAM|CDM|LM|RM|CB|LB|RB|LWB|RWB|GK)"
    r"(?![A-Z])",
    re.IGNORECASE,
)


def create_player_popularity_table(
    connection,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_player_popularity
            (
                id BIGSERIAL PRIMARY KEY,

                sp_id BIGINT NOT NULL,

                position VARCHAR(10) NOT NULL,

                usage_count INTEGER NOT NULL
                    DEFAULT 0,

                usage_rate DOUBLE PRECISION
                    NOT NULL
                    DEFAULT 0,

                popularity_score DOUBLE PRECISION
                    NOT NULL
                    DEFAULT 0,

                snapshot_date DATE NOT NULL,

                updated_at TIMESTAMPTZ
                    NOT NULL
                    DEFAULT NOW(),

                UNIQUE (
                    sp_id,
                    position,
                    snapshot_date
                )
            )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_fconline_player_popularity_latest

            ON fconline_player_popularity (
                snapshot_date DESC,
                position,
                popularity_score DESC
            )
            """
        )


    connection.commit()

def get_latest_player_popularity_map(
    connection,
):

    with connection.cursor() as cursor:

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


        if (
            not table_row
            or
            table_row[
                "table_name"
            ]
            is None
        ):
            return {}


        cursor.execute(
            """
            WITH latest AS (

                SELECT
                    MAX(
                        snapshot_date
                    )
                        AS snapshot_date

                FROM
                    fconline_player_popularity
            )

            SELECT
                p.sp_id,
                p.position,
                p.usage_count,
                p.usage_rate,
                p.popularity_score,
                p.snapshot_date

            FROM
                fconline_player_popularity
                AS p

            JOIN latest

                ON
                    p.snapshot_date
                    =
                    latest.snapshot_date
            """
        )

        rows = (
            cursor.fetchall()
        )


    popularity_map = {}


    for row in rows:

        key = (
            int(
                row[
                    "sp_id"
                ]
            ),

            str(
                row[
                    "position"
                ]
            )
            .strip()
            .upper(),
        )


        popularity_map[
            key
        ] = {

            "position":
                str(
                    row[
                        "position"
                    ]
                )
                .strip()
                .upper(),

            "usage_count":
                int(
                    row[
                        "usage_count"
                    ]
                    or 0
                ),

            "usage_rate":
                float(
                    row[
                        "usage_rate"
                    ]
                    or 0
                ),

            "popularity_score":
                float(
                    row[
                        "popularity_score"
                    ]
                    or 0
                ),

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
        }


    return popularity_map


def _extract_sp_id(
    element,
    season_code_map,
):

    player_image_id = None


    # =====================================
    # 선수 이미지 번호 추출
    # =====================================

    for image in element.find_all(
        "img"
    ):

        src = str(
            image.get(
                "src",
                "",
            )
        )


        match = (
            SPID_PATTERN.search(
                src
            )
        )


        if not match:

            continue


        player_image_id = int(
            match.group(1)
        )


        break


    if player_image_id is None:

        return None


    # =====================================
    # 이미지 번호 자체가 이미 SPID인 경우
    # =====================================

    if (
        player_image_id
        >= 100_000_000
    ):

        return player_image_id


    # =====================================
    # 짧은 값이면 PID이므로
    # 시즌 아이콘을 이용해 SPID 복원
    # =====================================

    for image in element.find_all(
        "img"
    ):

        src = str(
            image.get(
                "src",
                "",
            )
        )


        match = (
            SEASON_IMAGE_PATTERN.search(
                src
            )
        )


        if not match:

            continue


        season_code = (
            match.group(1)
            .upper()
        )


        season_id = (
            season_code_map.get(
                season_code
            )
        )


        if season_id is None:

            continue


        return (
            season_id
            * 1_000_000
            +
            player_image_id
        )


    return None

def fetch_season_code_map():

    response = httpx.get(
        SEASON_METADATA_URL,
        timeout=20.0,
        follow_redirects=True,
    )


    response.raise_for_status()


    result = {}


    for season in response.json():

        season_id = int(
            season[
                "seasonId"
            ]
        )


        season_image = str(
            season.get(
                "seasonImg",
                "",
            )
        )


        file_name = (
            season_image
            .split("/")[-1]
            .split("?")[0]
        )


        if not file_name:

            continue


        season_code = (
            file_name
            .removesuffix(".png")
            .removesuffix("_big")
            .upper()
        )


        if not season_code:

            continue


        result[
            season_code
        ] = season_id


    return result


def _extract_position(element):

    text = element.get_text(
        " ",
        strip=True,
    )


    positions = {
        match.upper()
        for match
        in POSITION_PATTERN.findall(
            text
        )
    }


    # 선수 1명 카드라면
    # 포지션도 하나만 존재해야 한다.
    if len(positions) != 1:

        return None


    return next(
        iter(
            positions
        )
    )

def _find_player_container(
    usage_node,
    season_code_map,
):

    element = (
        usage_node.parent
    )


    while (
        element
        and
        element.name
        not in {
            "body",
            "html",
        }
    ):

        text = element.get_text(
            " ",
            strip=True,
        )


        usage_matches = (
            USAGE_PATTERN.findall(
                text
            )
        )


        # 부모 영역으로 너무 올라가
        # 여러 선수 데이터가 포함되면 중단한다.
        if len(
            usage_matches
        ) > 1:

            return None


        sp_id = (
            _extract_sp_id(
                element,
                season_code_map,
            )
        )


        position = (
            _extract_position(
                element
            )
        )


        if (
            sp_id
            and
            position
        ):

            return {
                "element":
                    element,

                "sp_id":
                    sp_id,

                "position":
                    position,
            }


        element = (
            element.parent
        )


    return None


def _extract_usage(text):

    match = (
        USAGE_PATTERN.search(
            text
        )
    )


    if not match:

        return None


    usage_count = int(
        match.group(1)
        .replace(
            ",",
            "",
        )
    )


    usage_rate = float(
        match.group(2)
    )


    return (
        usage_count,
        usage_rate,
    )


def parse_position_popularity(
    html,
    position,
):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )


    players = []


    for card in soup.select(
        ".item_list.swiper-slide"
    ):

        link = card.select_one(
            'a.outlink[href*="spid="]'
        )


        usage_element = (
            card.select_one(
                "p.txt"
            )
        )


        if (
            link is None
            or
            usage_element is None
        ):

            continue


        href = str(
            link.get(
                "href",
                "",
            )
        )


        spid_match = (
            SPID_HREF_PATTERN.search(
                href
            )
        )


        if not spid_match:

            continue


        usage = (
            _extract_usage(
                usage_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        if not usage:

            continue


        sp_id = int(
            spid_match.group(1)
        )


        usage_count, usage_rate = (
            usage
        )


        players.append(
            {
                "sp_id":
                    sp_id,

                "position":
                    position,

                "usage_count":
                    usage_count,

                "usage_rate":
                    usage_rate,
            }
        )


    # =====================================
    # 같은 카드 중복 제거
    # =====================================

    deduplicated = {}


    for player in players:

        key = (
            player["sp_id"],
            player["position"],
        )


        previous = (
            deduplicated.get(
                key
            )
        )


        if (
            previous is None
            or
            player["usage_count"]
            >
            previous["usage_count"]
        ):

            deduplicated[
                key
            ] = player


    return list(
        deduplicated.values()
    )

def fetch_position_popularity(
    position,
    position_code,
    snapshot_date,
):

    response = httpx.get(
        POSITION_POPULARITY_URL,

        params={
            "strDate":
                snapshot_date.strftime(
                    "%Y.%m.%d"
                ),

            "n4Position":
                position_code,

            "n1Type":
                50,

            "n4StartRanking":
                1,

            "n4EndRanking":
                10000,

            "isGroup":
                "true",
        },

        headers={
            "Accept":
                "*/*",

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; "
                    "Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/150 Safari/537.36"
                ),

            "Referer":
                (
                    "https://fconline.nexon.com/"
                    "datacenter/dailysquad"
                ),

            "X-Requested-With":
                "XMLHttpRequest",
        },

        timeout=30.0,
        follow_redirects=True,
    )


    response.raise_for_status()


    players = (
        parse_position_popularity(
            response.text,
            position,
        )
    )


    return players


def fetch_daily_popularity(
    snapshot_date=None,
):

    if snapshot_date is None:

        snapshot_date = (
            get_popularity_snapshot_date()
        )


    result = []


    for (
        position,
        position_code,
    ) in POSITION_CODE_MAP.items():

        players = (
            fetch_position_popularity(
                position,
                position_code,
                snapshot_date,
            )
        )


        print(
            (
                f"{position:>4} "
                f"수집: "
                f"{len(players)}명"
            )
        )


        result.extend(
            players
        )


    return result


def calculate_popularity_scores(
    players,
):

    groups = {}


    for player in players:

        position = (
            player[
                "position"
            ]
        )


        groups.setdefault(
            position,
            [],
        ).append(
            player
        )


    normalized = []


    for (
        position,
        position_players,
    ) in groups.items():

        max_usage_count = max(
            int(
                player[
                    "usage_count"
                ]
            )
            for player
            in position_players
        )


        for player in position_players:

            usage_count = int(
                player[
                    "usage_count"
                ]
            )


            if (
                max_usage_count
                <= 0
            ):

                score = 0.0

            else:

                score = (
                    usage_count
                    /
                    max_usage_count
                )


            normalized.append(
                {
                    **player,

                    "popularity_score":
                        round(
                            score,
                            6,
                        ),
                }
            )


    return normalized


def save_player_popularity(
    connection,
    players,
    snapshot_date=None,
):

    if snapshot_date is None:

        snapshot_date = (
            get_popularity_snapshot_date()
        )


    with connection.cursor() as cursor:

        for player in players:

            cursor.execute(
                """
                INSERT INTO
                    fconline_player_popularity
                (
                    sp_id,
                    position,
                    usage_count,
                    usage_rate,
                    popularity_score,
                    snapshot_date,
                    updated_at
                )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )

                ON CONFLICT (
                    sp_id,
                    position,
                    snapshot_date
                )

                DO UPDATE SET
                    usage_count =
                        EXCLUDED.usage_count,

                    usage_rate =
                        EXCLUDED.usage_rate,

                    popularity_score =
                        EXCLUDED.popularity_score,

                    updated_at =
                        NOW()
                """,
                (
                    player[
                        "sp_id"
                    ],

                    player[
                        "position"
                    ],

                    player[
                        "usage_count"
                    ],

                    player[
                        "usage_rate"
                    ],

                    player[
                        "popularity_score"
                    ],

                    snapshot_date,
                ),
            )


    connection.commit()


def sync_player_popularity(
    connection,
):

    # =====================================
    # 테이블 준비
    # =====================================

    create_player_popularity_table(
        connection
    )


    # =====================================
    # FC Online 공식 데이터는
    # 전날 기록 기준
    # =====================================

    snapshot_date = (
        get_popularity_snapshot_date()
    )


    # =====================================
    # 공식 데이터 수집
    # =====================================

    players = (
        fetch_daily_popularity(
            snapshot_date=
                snapshot_date
        )
    )


    players = (
        calculate_popularity_scores(
            players
        )
    )


    if not players:

        raise RuntimeError(
            "FC Online 인기 선수 데이터를 "
            "수집하지 못했습니다."
        )


    positions = sorted(
        {
            player[
                "position"
            ]
            for player
            in players
        }
    )


    # =====================================
    # 비정상 수집 방어
    #
    # 잘못 수집된 데이터를 저장하기 전에
    # 반드시 여기서 중단한다.
    # =====================================

    if (
        len(players)
        < 100
        or
        len(positions)
        < 10
    ):

        raise RuntimeError(
            (
                "FC Online 인기 선수 데이터가 "
                "비정상적으로 적습니다. "
                f"선수 {len(players)}명 / "
                f"포지션 {len(positions)}개"
            )
        )


    # =====================================
    # 현재 Snapshot부터 미래 날짜까지 삭제
    #
    # 이전 테스트에서 잘못 저장된
    # 오늘 날짜 Snapshot도 여기서 제거된다.
    # =====================================

    with connection.cursor() as cursor:

        cursor.execute(
            """
            DELETE FROM
                fconline_player_popularity

            WHERE
                snapshot_date >= %s
            """,
            (
                snapshot_date,
            ),
        )


    connection.commit()


    # =====================================
    # 새 Snapshot 저장
    # =====================================

    save_player_popularity(
        connection,
        players,
        snapshot_date=
            snapshot_date,
    )


    return {
        "count":
            len(players),

        "positions":
            positions,

        "snapshot_date":
            snapshot_date.isoformat(),

        "synced_at":
            datetime.now(
                KST
            ).isoformat(),
    }


if __name__ == "__main__":

    print(
        "FC Online 인기 선수 데이터 수집 테스트 시작"
    )


    players = (
        fetch_daily_popularity()
    )


    print(
        f"원본 수집 선수 수: {len(players)}"
    )


    players = (
        calculate_popularity_scores(
            players
        )
    )


    print(
        f"점수 계산 완료: {len(players)}"
    )


    positions = sorted(
        {
            player["position"]
            for player in players
        }
    )


    print(
        "수집 포지션:",
        positions,
    )


    print(
        "\n상위 데이터 샘플\n"
        "============================"
    )


    top_players = sorted(
        players,
        key=lambda player: (
            -player[
                "usage_count"
            ]
        ),
    )[:30]


    for player in top_players:

        print(
            (
                f'{player["position"]:>4} | '
                f'SPID {player["sp_id"]} | '
                f'{player["usage_count"]}명 | '
                f'{player["usage_rate"]}% | '
                f'인기도 '
                f'{player["popularity_score"]:.3f}'
            )
        )