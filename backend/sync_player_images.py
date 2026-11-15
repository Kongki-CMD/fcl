import argparse
import os
import re
import time

from urllib.parse import (
    urljoin,
)

import httpx
import psycopg

from bs4 import BeautifulSoup
from psycopg.rows import dict_row


# =========================================
# CONFIG
# =========================================

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


PLAYER_INFO_URL = (
    "https://fconline.nexon.com/"
    "DataCenter/PlayerInfo"
)


DEFAULT_PLAYER_IMAGE_URL = (
    "https://fco.dn.nexoncdn.co.kr/"
    "live/externalAssets/common/"
    "playersAction/p{sp_id}.png"
)


HTTP_HEADERS = {
    "User-Agent":
        (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/150.0.0.0 "
            "Safari/537.36"
        ),

    "Accept":
        (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "image/avif,"
            "image/webp,"
            "image/apng,"
            "*/*;q=0.8"
        ),

    "Accept-Language":
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


REQUEST_DELAY_SECONDS = 0.05

OFFICIAL_PAGE_DELAY_SECONDS = 0.15


# =========================================
# DB
# =========================================

def get_connection():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def ensure_image_sync_table(
    connection,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_player_image_sync (
                    sp_id BIGINT
                        PRIMARY KEY,

                    player_name TEXT
                        NOT NULL,

                    original_image_url TEXT,

                    resolved_image_url TEXT,

                    status TEXT
                        NOT NULL
                        DEFAULT 'pending',

                    source TEXT,

                    http_status INTEGER,

                    attempt_count INTEGER
                        NOT NULL
                        DEFAULT 0,

                    last_error TEXT,

                    checked_at TIMESTAMPTZ,

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_fconline_player_image_sync_status

            ON
                fconline_player_image_sync (
                    status
                )
            """
        )


    connection.commit()


# =========================================
# IMAGE VALIDATION
# =========================================

def is_image_content_type(
    content_type,
):

    return str(
        content_type
        or
        ""
    ).lower().startswith(
        "image/"
    )


def probe_image_url(
    client,
    image_url,
):

    image_url = str(
        image_url
        or
        ""
    ).strip()


    if not image_url:

        return {
            "valid":
                False,

            "status_code":
                None,

            "content_type":
                "",
        }


    # =====================================
    # HEAD 우선
    # =====================================

    try:

        response = client.head(
            image_url,
            headers={
                "Referer":
                    "https://fconline.nexon.com/",
            },
            timeout=10.0,
            follow_redirects=True,
        )


        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
        )


        if (
            response.status_code
            in {
                200,
                206,
            }
            and
            is_image_content_type(
                content_type
            )
        ):

            return {
                "valid":
                    True,

                "status_code":
                    response.status_code,

                "content_type":
                    content_type,
            }


        # HEAD를 지원하지 않는 CDN이면
        # 아래 GET 검사로 넘어간다.

    except Exception:
        pass


    # =====================================
    # GET 스트리밍 검사
    #
    # 전체 이미지를 내려받지 않고
    # 첫 데이터만 확인하고 연결 종료
    # =====================================

    try:

        with client.stream(
            "GET",
            image_url,
            headers={
                "Referer":
                    "https://fconline.nexon.com/",

                "Range":
                    "bytes=0-1023",
            },
            timeout=15.0,
            follow_redirects=True,
        ) as response:

            content_type = (
                response.headers.get(
                    "content-type",
                    "",
                )
            )


            valid = (
                response.status_code
                in {
                    200,
                    206,
                }
                and
                is_image_content_type(
                    content_type
                )
            )


            if valid:

                for _ in response.iter_bytes():
                    break


            return {
                "valid":
                    valid,

                "status_code":
                    response.status_code,

                "content_type":
                    content_type,
            }


    except Exception as error:

        return {
            "valid":
                False,

            "status_code":
                None,

            "content_type":
                "",

            "error":
                str(
                    error
                ),
        }


# =========================================
# OFFICIAL PAGE IMAGE DISCOVERY
# =========================================

def normalize_candidate_url(
    value,
):

    value = str(
        value
        or
        ""
    ).strip()


    if not value:

        return ""


    value = (
        value
        .replace(
            "&amp;",
            "&",
        )
    )


    if value.startswith(
        "//"
    ):

        return (
            "https:"
            +
            value
        )


    return urljoin(
        PLAYER_INFO_URL,
        value,
    )


def extract_css_urls(
    value,
):

    return re.findall(
        r"""url\(
            \s*
            ['"]?
            ([^'")]+)
            ['"]?
            \s*
        \)""",
        str(
            value
            or
            ""
        ),
        flags=re.IGNORECASE
        |
        re.VERBOSE,
    )


def get_candidate_score(
    image_url,
    sp_id,
):

    url = str(
        image_url
        or
        ""
    ).lower()


    score = 0


    # =====================================
    # 선수 이미지 가능성이 높은 경로
    # =====================================

    if (
        "playersaction"
        in url
    ):
        score += 100


    if (
        "/players/"
        in url
    ):
        score += 70


    if (
        "playerface"
        in url
    ):
        score += 65


    if (
        "player"
        in url
    ):
        score += 20


    if (
        str(
            sp_id
        )
        in url
    ):
        score += 80


    # =====================================
    # 선수 이미지가 아닐 가능성이 높은 것
    # =====================================

    negative_words = (
        "season",
        "nation",
        "national",
        "teamlogo",
        "clublogo",
        "position",
        "grade",
        "strong",
        "trait",
        "skill",
        "icon",
        "logo",
        "flag",
        "common/ui",
    )


    for word in negative_words:

        if word in url:

            score -= 50


    return score


def extract_official_image_candidates(
    html,
    sp_id,
):

    soup = BeautifulSoup(
        html,
        "html.parser",
    )


    candidates = []


    def add_candidate(
        raw_url,
    ):

        image_url = (
            normalize_candidate_url(
                raw_url
            )
        )


        if not image_url:
            return


        lowered = (
            image_url.lower()
        )


        if not (
            lowered.endswith(
                ".png"
            )
            or
            lowered.endswith(
                ".jpg"
            )
            or
            lowered.endswith(
                ".jpeg"
            )
            or
            lowered.endswith(
                ".webp"
            )
            or
            ".png?"
            in lowered
            or
            ".jpg?"
            in lowered
            or
            ".jpeg?"
            in lowered
            or
            ".webp?"
            in lowered
        ):
            return


        candidates.append(
            image_url
        )


    # =====================================
    # IMG / SOURCE 속성
    # =====================================

    for element in soup.select(
        "img, source"
    ):

        for attribute_name in (
            "src",
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-url",
        ):

            add_candidate(
                element.get(
                    attribute_name
                )
            )


        srcset = (
            element.get(
                "srcset",
                ""
            )
        )


        if srcset:

            for srcset_item in (
                srcset.split(
                    ","
                )
            ):

                srcset_url = (
                    srcset_item
                    .strip()
                    .split(
                        " "
                    )[0]
                )


                add_candidate(
                    srcset_url
                )


    # =====================================
    # inline style
    # =====================================

    for element in soup.select(
        "[style]"
    ):

        for style_url in (
            extract_css_urls(
                element.get(
                    "style"
                )
            )
        ):

            add_candidate(
                style_url
            )


    # =====================================
    # HTML / SCRIPT 안에 직접 박힌 URL
    # =====================================

    raw_urls = re.findall(
        (
            r"""(?:"|')"""
            r"""((?:https?:)?//"""
            r"""[^"'\\\s<>]+"""
            r"""\.(?:png|jpg|jpeg|webp)"""
            r"""(?:\?[^"'\\\s<>]*)?)"""
            r"""(?:"|')"""
        ),
        html,
        flags=re.IGNORECASE,
    )


    for raw_url in raw_urls:

        add_candidate(
            raw_url
        )


    # =====================================
    # 중복 제거
    # =====================================

    unique_candidates = list(
        dict.fromkeys(
            candidates
        )
    )


    # =====================================
    # 선수 이미지 가능성 순 정렬
    # =====================================

    unique_candidates.sort(
        key=lambda image_url:
            get_candidate_score(
                image_url,
                sp_id,
            ),
        reverse=True,
    )


    return unique_candidates


def find_official_player_image(
    client,
    sp_id,
):

    response = client.get(
        PLAYER_INFO_URL,
        params={
            "spid":
                int(
                    sp_id
                ),

            "n1Strong":
                1,
        },
        headers={
            "Referer":
                (
                    "https://fconline.nexon.com/"
                    "DataCenter/PlayerStat"
                ),
        },
        timeout=20.0,
        follow_redirects=True,
    )


    response.raise_for_status()


    candidates = (
        extract_official_image_candidates(
            response.text,
            sp_id,
        )
    )


    # 너무 많은 아이콘까지 검사하지 않도록
    # 후보 상위 20개까지만 확인
    candidates = (
        candidates[
            :20
        ]
    )


    for image_url in candidates:

        score = (
            get_candidate_score(
                image_url,
                sp_id,
            )
        )


        # 선수 이미지 가능성이 지나치게 낮은
        # 아이콘은 검사하지 않는다.
        if score < 20:
            continue


        result = (
            probe_image_url(
                client,
                image_url,
            )
        )


        if result[
            "valid"
        ]:

            return {
                "image_url":
                    image_url,

                "http_status":
                    result[
                        "status_code"
                    ],

                "candidate_count":
                    len(
                        candidates
                    ),
            }


    return {
        "image_url":
            None,

        "http_status":
            response.status_code,

        "candidate_count":
            len(
                candidates
            ),
    }


# =========================================
# DB STATUS
# =========================================

def save_image_status(
    connection,
    *,
    sp_id,
    player_name,
    original_image_url,
    resolved_image_url,
    status,
    source,
    http_status=None,
    error=None,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            INSERT INTO
                fconline_player_image_sync (
                    sp_id,
                    player_name,
                    original_image_url,
                    resolved_image_url,
                    status,
                    source,
                    http_status,
                    attempt_count,
                    last_error,
                    checked_at,
                    updated_at
                )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                1,
                %s,
                NOW(),
                NOW()
            )

            ON CONFLICT (
                sp_id
            )

            DO UPDATE SET
                player_name =
                    EXCLUDED.player_name,

                original_image_url =
                    COALESCE(
                        fconline_player_image_sync
                            .original_image_url,
                        EXCLUDED.original_image_url
                    ),

                resolved_image_url =
                    EXCLUDED.resolved_image_url,

                status =
                    EXCLUDED.status,

                source =
                    EXCLUDED.source,

                http_status =
                    EXCLUDED.http_status,

                attempt_count =
                    fconline_player_image_sync
                        .attempt_count
                    + 1,

                last_error =
                    EXCLUDED.last_error,

                checked_at =
                    NOW(),

                updated_at =
                    NOW()
            """,
            (
                int(
                    sp_id
                ),

                str(
                    player_name
                    or
                    ""
                ),

                original_image_url,
                resolved_image_url,
                status,
                source,
                http_status,

                (
                    str(
                        error
                    )[:2000]
                    if error
                    else None
                ),
            ),
        )


    connection.commit()


def update_player_image_url(
    connection,
    sp_id,
    image_url,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            UPDATE
                fconline_players

            SET
                image_url = %s,
                updated_at = NOW()

            WHERE
                sp_id = %s
            """,
            (
                image_url,
                int(
                    sp_id
                ),
            ),
        )


    connection.commit()


# =========================================
# PLAYER LOAD
# =========================================

def load_scan_players(
    connection,
    *,
    limit=None,
    sp_id=None,
    force=False,
):

    clauses = [
        "TRUE",
    ]

    params = []


    if sp_id is not None:

        clauses.append(
            "p.sp_id = %s"
        )

        params.append(
            int(
                sp_id
            )
        )


    if not force:

        clauses.append(
            """
            NOT EXISTS (
                SELECT
                    1

                FROM
                    fconline_player_image_sync
                    AS image_sync

                WHERE
                    image_sync.sp_id
                    =
                    p.sp_id

                AND
                    image_sync.status
                    IN (
                        'valid',
                        'repaired',
                        'missing'
                    )
            )
            """
        )


    where_sql = (
        "\nAND\n".join(
            clauses
        )
    )


    sql = f"""
        SELECT
            p.sp_id,
            p.player_name,
            p.image_url

        FROM
            fconline_players AS p

        WHERE
            {where_sql}

        ORDER BY
            p.sp_id ASC
    """


    if (
        limit is not None
        and
        limit > 0
    ):

        sql += "\nLIMIT %s"

        params.append(
            int(
                limit
            )
        )


    with connection.cursor() as cursor:

        cursor.execute(
            sql,
            params,
        )


        return (
            cursor.fetchall()
        )


def load_repair_players(
    connection,
    *,
    limit=None,
    sp_id=None,
    force=False,
):

    clauses = [
        "TRUE",
    ]

    params = []


    if sp_id is not None:

        clauses.append(
            "p.sp_id = %s"
        )

        params.append(
            int(
                sp_id
            )
        )


    if not force:

        clauses.append(
            """
            image_sync.status
            IN (
                'broken',
                'error'
            )
            """
        )


    sql = f"""
        SELECT
            p.sp_id,
            p.player_name,
            p.image_url,

            image_sync.original_image_url,
            image_sync.status

        FROM
            fconline_players AS p

        INNER JOIN
            fconline_player_image_sync
            AS image_sync

        ON
            image_sync.sp_id
            =
            p.sp_id

        WHERE
            {
                "\nAND\n".join(
                    clauses
                )
            }

        ORDER BY
            p.sp_id ASC
    """


    if (
        limit is not None
        and
        limit > 0
    ):

        sql += "\nLIMIT %s"

        params.append(
            int(
                limit
            )
        )


    with connection.cursor() as cursor:

        cursor.execute(
            sql,
            params,
        )


        return (
            cursor.fetchall()
        )


# =========================================
# SCAN
# =========================================

def scan_player_images(
    connection,
    client,
    *,
    limit=None,
    sp_id=None,
    force=False,
):

    players = (
        load_scan_players(
            connection,
            limit=
                limit,
            sp_id=
                sp_id,
            force=
                force,
        )
    )


    print()
    print(
        "[PLAYER IMAGE SCAN] "
        f"target={len(players)}"
    )


    valid_count = 0
    broken_count = 0
    error_count = 0


    for (
        index,
        player,
    ) in enumerate(
        players,
        start=1,
    ):

        current_image_url = (
            str(
                player.get(
                    "image_url"
                )
                or
                ""
            )
            .strip()
        )


        if not current_image_url:

            current_image_url = (
                DEFAULT_PLAYER_IMAGE_URL.format(
                    sp_id=
                        player[
                            "sp_id"
                        ]
                )
            )


        try:

            result = (
                probe_image_url(
                    client,
                    current_image_url,
                )
            )


            if result[
                "valid"
            ]:

                valid_count += 1

                status = (
                    "valid"
                )


                save_image_status(
                    connection,

                    sp_id=
                        player[
                            "sp_id"
                        ],

                    player_name=
                        player[
                            "player_name"
                        ],

                    original_image_url=
                        current_image_url,

                    resolved_image_url=
                        current_image_url,

                    status=
                        status,

                    source=
                        "current",

                    http_status=
                        result[
                            "status_code"
                        ],
                )


                print(
                    (
                        "[PLAYER IMAGE] "
                        f"{index}/{len(players)} "
                        f"{player['sp_id']} "
                        f"{player['player_name']} "
                        "OK"
                    ),
                    flush=True,
                )


            else:

                broken_count += 1


                save_image_status(
                    connection,

                    sp_id=
                        player[
                            "sp_id"
                        ],

                    player_name=
                        player[
                            "player_name"
                        ],

                    original_image_url=
                        current_image_url,

                    resolved_image_url=
                        None,

                    status=
                        "broken",

                    source=
                        "current",

                    http_status=
                        result.get(
                            "status_code"
                        ),

                    error=
                        result.get(
                            "error"
                        ),
                )


                print(
                    (
                        "[PLAYER IMAGE] "
                        f"{index}/{len(players)} "
                        f"{player['sp_id']} "
                        f"{player['player_name']} "
                        "BROKEN "
                        f"http="
                        f"{result.get('status_code')}"
                    ),
                    flush=True,
                )


        except Exception as error:

            error_count += 1


            save_image_status(
                connection,

                sp_id=
                    player[
                        "sp_id"
                    ],

                player_name=
                    player[
                        "player_name"
                    ],

                original_image_url=
                    current_image_url,

                resolved_image_url=
                    None,

                status=
                    "error",

                source=
                    "current",

                error=
                    error,
            )


            print(
                (
                    "[PLAYER IMAGE] "
                    f"{index}/{len(players)} "
                    f"{player['sp_id']} "
                    f"{player['player_name']} "
                    f"ERROR {error}"
                ),
                flush=True,
            )


        time.sleep(
            REQUEST_DELAY_SECONDS
        )


    return {
        "target":
            len(
                players
            ),

        "valid":
            valid_count,

        "broken":
            broken_count,

        "error":
            error_count,
    }


# =========================================
# REPAIR
# =========================================

def repair_player_images(
    connection,
    client,
    *,
    limit=None,
    sp_id=None,
    force=False,
):

    players = (
        load_repair_players(
            connection,
            limit=
                limit,
            sp_id=
                sp_id,
            force=
                force,
        )
    )


    print()
    print(
        "[PLAYER IMAGE REPAIR] "
        f"target={len(players)}"
    )


    repaired_count = 0
    missing_count = 0
    error_count = 0


    for (
        index,
        player,
    ) in enumerate(
        players,
        start=1,
    ):

        try:

            result = (
                find_official_player_image(
                    client,
                    player[
                        "sp_id"
                    ],
                )
            )


            repaired_image_url = (
                result.get(
                    "image_url"
                )
            )


            if repaired_image_url:

                update_player_image_url(
                    connection,
                    player[
                        "sp_id"
                    ],
                    repaired_image_url,
                )


                save_image_status(
                    connection,

                    sp_id=
                        player[
                            "sp_id"
                        ],

                    player_name=
                        player[
                            "player_name"
                        ],

                    original_image_url=
                        (
                            player.get(
                                "original_image_url"
                            )
                            or
                            player.get(
                                "image_url"
                            )
                        ),

                    resolved_image_url=
                        repaired_image_url,

                    status=
                        "repaired",

                    source=
                        "official_player_info",

                    http_status=
                        result.get(
                            "http_status"
                        ),
                )


                repaired_count += 1


                print(
                    (
                        "[PLAYER IMAGE REPAIR] "
                        f"{index}/{len(players)} "
                        f"{player['sp_id']} "
                        f"{player['player_name']} "
                        "REPAIRED"
                    ),
                    flush=True,
                )


                print(
                    (
                        "    -> "
                        f"{repaired_image_url}"
                    ),
                    flush=True,
                )


            else:

                missing_count += 1


                save_image_status(
                    connection,

                    sp_id=
                        player[
                            "sp_id"
                        ],

                    player_name=
                        player[
                            "player_name"
                        ],

                    original_image_url=
                        (
                            player.get(
                                "original_image_url"
                            )
                            or
                            player.get(
                                "image_url"
                            )
                        ),

                    resolved_image_url=
                        None,

                    status=
                        "missing",

                    source=
                        "official_player_info",

                    http_status=
                        result.get(
                            "http_status"
                        ),
                )


                print(
                    (
                        "[PLAYER IMAGE REPAIR] "
                        f"{index}/{len(players)} "
                        f"{player['sp_id']} "
                        f"{player['player_name']} "
                        "NO OFFICIAL IMAGE "
                        f"candidates="
                        f"{result.get('candidate_count', 0)}"
                    ),
                    flush=True,
                )


        except Exception as error:

            error_count += 1


            save_image_status(
                connection,

                sp_id=
                    player[
                        "sp_id"
                    ],

                player_name=
                    player[
                        "player_name"
                    ],

                original_image_url=
                    (
                        player.get(
                            "original_image_url"
                        )
                        or
                        player.get(
                            "image_url"
                        )
                    ),

                resolved_image_url=
                    None,

                status=
                    "error",

                source=
                    "official_player_info",

                error=
                    error,
            )


            print(
                (
                    "[PLAYER IMAGE REPAIR] "
                    f"{index}/{len(players)} "
                    f"{player['sp_id']} "
                    f"{player['player_name']} "
                    f"ERROR {error}"
                ),
                flush=True,
            )


        time.sleep(
            OFFICIAL_PAGE_DELAY_SECONDS
        )


    return {
        "target":
            len(
                players
            ),

        "repaired":
            repaired_count,

        "missing":
            missing_count,

        "error":
            error_count,
    }


# =========================================
# SUMMARY
# =========================================

def print_summary(
    connection,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                status,
                COUNT(*) AS count

            FROM
                fconline_player_image_sync

            GROUP BY
                status

            ORDER BY
                status
            """
        )


        rows = (
            cursor.fetchall()
        )


    print()
    print(
        "========================================="
    )

    print(
        "PLAYER IMAGE SYNC SUMMARY"
    )


    for row in rows:

        print(
            (
                f"{row['status']}: "
                f"{row['count']}"
            )
        )


    print(
        "========================================="
    )


# =========================================
# MAIN
# =========================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "FC Online 선수 이미지 검사 / 복구"
        )
    )


    parser.add_argument(
        "--mode",
        choices=[
            "scan",
            "repair",
            "all",
            "summary",
        ],
        default=
            "scan",
    )


    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "이번 실행에서 처리할 최대 선수 수"
        ),
    )


    parser.add_argument(
        "--sp-id",
        type=int,
        default=None,
        help=(
            "특정 SPID 한 명만 검사"
        ),
    )


    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "이미 검사 완료한 선수도 다시 검사"
        ),
    )


    args = (
        parser.parse_args()
    )


    with get_connection() as connection:

        ensure_image_sync_table(
            connection
        )


        if (
            args.mode
            ==
            "summary"
        ):

            print_summary(
                connection
            )

            return


        with httpx.Client(
            headers=
                HTTP_HEADERS,

            timeout=
                20.0,

            follow_redirects=
                True,
        ) as client:


            if (
                args.mode
                in {
                    "scan",
                    "all",
                }
            ):

                result = (
                    scan_player_images(
                        connection,
                        client,

                        limit=
                            args.limit,

                        sp_id=
                            args.sp_id,

                        force=
                            args.force,
                    )
                )


                print(
                    "[PLAYER IMAGE SCAN RESULT]",
                    result,
                    flush=True,
                )


            if (
                args.mode
                in {
                    "repair",
                    "all",
                }
            ):

                result = (
                    repair_player_images(
                        connection,
                        client,

                        limit=
                            args.limit,

                        sp_id=
                            args.sp_id,

                        force=
                            args.force,
                    )
                )


                print(
                    "[PLAYER IMAGE REPAIR RESULT]",
                    result,
                    flush=True,
                )


        print_summary(
            connection
        )


if __name__ == "__main__":

    main()