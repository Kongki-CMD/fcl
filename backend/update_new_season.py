from __future__ import annotations

import argparse
import os
import re
import sys
import time

from collections import defaultdict
from pathlib import Path

import psycopg


# =========================================
# PROJECT / LOCAL ENV
# =========================================

PROJECT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


def load_local_env():
    """
    python-dotenv 없이 .env.local을 읽는다.

    이미 PowerShell / 시스템 환경변수에 값이 있으면
    기존 값을 우선한다.
    """

    env_path = (
        PROJECT_DIR
        / ".env.local"
    )

    if not env_path.exists():
        return

    for raw_line in env_path.read_text(
        encoding="utf-8"
    ).splitlines():

        line = raw_line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split(
            "=",
            1,
        )

        key = key.strip()
        value = value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {
                '"',
                "'",
            }
        ):
            value = value[1:-1]

        if key:
            os.environ.setdefault(
                key,
                value,
            )


load_local_env()


# backend 패키지 import 가능하게
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_DIR),
    )


from backend import player_catalog as catalog


# =========================================
# HELPERS
# =========================================

def require_database_url():

    database_url = (
        os.getenv("DATABASE_URL")
        or catalog.DATABASE_URL
    )

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL이 설정되지 않았습니다.\n"
            "PowerShell 환경변수 또는 "
            "프로젝트 루트의 .env.local을 확인해주세요."
        )

    # player_catalog는 import 시점에 환경변수를 읽기 때문에
    # 현재 값을 명시적으로 맞춘다.
    catalog.DATABASE_URL = database_url

    return database_url


def normalize_name(value):

    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip(),
    ).casefold()


def class_acronym(value):

    words = re.findall(
        r"[A-Za-z0-9]+",
        str(value or ""),
    )

    return "".join(
        word[0]
        for word in words
        if word
    ).casefold()


def season_id_from_spid(
    sp_id: int,
):

    return (
        int(sp_id)
        // 1_000_000
    )


# =========================================
# DB READ
# =========================================

def get_database_season_counts(
    database_url,
):

    with psycopg.connect(
        database_url,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    season_id,
                    COUNT(*)

                FROM
                    fconline_players

                GROUP BY
                    season_id
                """
            )

            return {
                int(season_id):
                    int(count)

                for (
                    season_id,
                    count,
                )
                in cursor.fetchall()
            }


def get_existing_ids_for_season(
    database_url,
    season_id,
):

    with psycopg.connect(
        database_url,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    sp_id

                FROM
                    fconline_players

                WHERE
                    season_id = %s
                """,
                (
                    season_id,
                ),
            )

            return {
                int(row[0])
                for row
                in cursor.fetchall()
            }


# =========================================
# METADATA
# =========================================

def build_metadata_card_map():

    cards = (
        catalog
        .get_all_player_cards()
    )

    result = defaultdict(
        list
    )

    for card in cards:

        sp_id = int(
            card["sp_id"]
        )

        season_id = (
            season_id_from_spid(
                sp_id
            )
        )

        result[
            season_id
        ].append(
            {
                "sp_id":
                    sp_id,

                "player_name":
                    str(
                        card.get(
                            "player_name",
                            "",
                        )
                    ).strip(),
            }
        )

    for season_cards in result.values():

        season_cards.sort(
            key=lambda item:
                item["sp_id"]
        )

    return dict(result)


def print_missing_season_candidates(
    season_metadata,
    cards_by_season,
    db_counts,
):

    candidates = []

    for (
        season_id,
        cards,
    ) in cards_by_season.items():

        metadata_count = len(cards)

        database_count = (
            db_counts.get(
                season_id,
                0,
            )
        )

        missing = (
            metadata_count
            - database_count
        )

        if missing <= 0:
            continue

        class_name = (
            season_metadata
            .get(
                season_id,
                {},
            )
            .get(
                "class_name",
                "알 수 없는 클래스",
            )
        )

        candidates.append(
            (
                season_id,
                class_name,
                metadata_count,
                database_count,
                missing,
            )
        )

    candidates.sort(
        key=lambda item:
            item[0],
        reverse=True,
    )

    print()
    print(
        "======================================"
    )
    print(
        "DB와 차이가 있는 시즌"
    )
    print(
        "======================================"
    )

    if not candidates:

        print(
            "누락된 시즌/선수가 없습니다."
        )

        return []

    for (
        season_id,
        class_name,
        metadata_count,
        database_count,
        missing,
    ) in candidates[:10]:

        print(
            f"{season_id}"
            f" | {class_name}"
            f" | 메타 {metadata_count}"
            f" | DB {database_count}"
            f" | 누락 {missing}"
        )

    return candidates


def select_target_season(
    *,
    requested_season_id,
    requested_class_name,
    season_metadata,
    cards_by_season,
    db_counts,
):

    if requested_season_id is not None:

        season_id = int(
            requested_season_id
        )

        if (
            season_id
            not in cards_by_season
        ):
            raise RuntimeError(
                "해당 시즌의 선수 카드가 "
                f"SPID 메타데이터에 없습니다: {season_id}"
            )

        return season_id

    if requested_class_name:

        query = normalize_name(
            requested_class_name
        )

        matches = []

        for (
            season_id,
            metadata,
        ) in season_metadata.items():

            if (
                season_id
                not in cards_by_season
            ):
                continue

            class_name = str(
                metadata.get(
                    "class_name",
                    "",
                )
            ).strip()

            normalized = normalize_name(
                class_name
            )

            # 예:
            # "UC (Untouchable Champions)"
            # -> prefix = "UC"
            #
            # "25 UCL (25 UEFA Champions League)"
            # -> prefix = "25 UCL"
            prefix = (
                class_name
                .split(
                    "(",
                    1,
                )[0]
                .strip()
            )

            prefix_tokens = {
                normalize_name(token)

                for token
                in re.findall(
                    r"[A-Za-z0-9]+",
                    prefix,
                )
            }

            # 괄호 안 정식 클래스명
            parenthetical_match = re.search(
                r"\((.*?)\)",
                class_name,
            )

            parenthetical = (
                normalize_name(
                    parenthetical_match.group(1)
                )

                if parenthetical_match
                else ""
            )

            matched = (
                # 정확한 전체 클래스명
                query == normalized

                # UC / UCL / SPT 같은 정확한 코드
                or query in prefix_tokens

                # Untouchable Champions 같은 정식 이름
                or (
                    parenthetical
                    and query == parenthetical
                )
            )

            if matched:

                matches.append(
                    season_id
                )

        if not matches:

            raise RuntimeError(
                (
                    "Nexon 메타데이터에서 "
                    "클래스를 찾지 못했습니다: "
                    f"{requested_class_name}"
                    "\n"
                    "신규 클래스가 오늘 출시된 경우 "
                    "seasonid.json / spid.json 반영이 "
                    "아직 안 되었을 수 있습니다."
                )
            )

        if len(matches) > 1:

            print()
            print(
                "동일 클래스 코드 후보:",
                matches,
            )

        return max(
            matches
        )


# =========================================
# NATION
# =========================================

def build_nation_lookup():

    try:

        nations = (
            catalog
            .get_nation_metadata()
        )

    except Exception as error:

        print()
        print(
            "WARNING:"
            " 국적 ID 메타데이터를 "
            "불러오지 못했습니다."
        )

        print(
            repr(error)
        )

        print(
            "선수 수집은 계속 진행합니다."
        )

        return {}

    return {
        normalize_name(
            nation["nation_name"]
        ):
            int(
                nation["nation_id"]
            )

        for nation in nations

        if (
            nation.get(
                "nation_name"
            )
            and
            nation.get(
                "nation_id"
            )
            is not None
        )
    }


def apply_nation_id(
    player,
    nation_lookup,
):

    current_id = (
        player.get(
            "nation_id"
        )
    )

    if (
        current_id
        is not None
    ):

        try:
            player[
                "nation_id"
            ] = int(
                current_id
            )

            return

        except (
            TypeError,
            ValueError,
        ):
            pass

    nation_name = (
        player.get(
            "nation_name",
            "",
        )
    )

    nation_id = (
        nation_lookup.get(
            normalize_name(
                nation_name
            )
        )
    )

    player[
        "nation_id"
    ] = nation_id


def sync_nation_table_from_players(
    database_url,
    season_id,
):

    with psycopg.connect(
        database_url,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_player_nations (
                        sp_id,
                        nation_id,
                        nation_name,
                        updated_at
                    )

                SELECT
                    sp_id,
                    nation_id,
                    nation_name,
                    NOW()

                FROM
                    fconline_players

                WHERE
                    season_id = %s

                    AND
                    nation_id IS NOT NULL

                    AND
                    COALESCE(
                        nation_name,
                        ''
                    ) <> ''

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
                (
                    season_id,
                ),
            )

        connection.commit()


# =========================================
# VERIFY
# =========================================

def get_verification(
    database_url,
    season_id,
):

    with psycopg.connect(
        database_url,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*),
                    COUNT(*) FILTER (
                        WHERE ovr <= 0
                    ),
                    COUNT(*) FILTER (
                        WHERE salary <= 0
                    ),
                    COUNT(*) FILTER (
                        WHERE image_url IS NULL
                        OR image_url = ''
                    )

                FROM
                    fconline_players

                WHERE
                    season_id = %s
                """,
                (
                    season_id,
                ),
            )

            (
                player_count,
                invalid_ovr,
                invalid_salary,
                missing_image,
            ) = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_player_teams

                WHERE
                    sp_id IN (
                        SELECT
                            sp_id

                        FROM
                            fconline_players

                        WHERE
                            season_id = %s
                    )
                """,
                (
                    season_id,
                ),
            )

            team_rows = int(
                cursor.fetchone()[0]
            )

    return {
        "player_count":
            int(player_count),

        "invalid_ovr":
            int(invalid_ovr),

        "invalid_salary":
            int(invalid_salary),

        "missing_image":
            int(missing_image),

        "team_rows":
            team_rows,
    }


# =========================================
# SYNC
# =========================================

def sync_cards(
    *,
    cards,
    season_id,
    class_name,
    database_url,
    delay,
):

    nation_lookup = (
        build_nation_lookup()
    )

    success = 0
    failed = []

    print()
    print(
        "======================================"
    )
    print(
        "NEW SEASON SYNC START"
    )
    print(
        "======================================"
    )

    print(
        "시즌:",
        season_id,
    )

    print(
        "클래스:",
        class_name,
    )

    print(
        "이번 수집:",
        len(cards),
    )

    for (
        index,
        card,
    ) in enumerate(
        cards,
        start=1,
    ):

        sp_id = int(
            card["sp_id"]
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
            f"[{index}/{len(cards)}]"
            f" {sp_id}"
            f" | {metadata_name}"
        )

        try:

            # 기존 sync 상태 구조와 맞춤
            catalog.set_player_sync_running(
                sp_id=
                    sp_id,

                player_name=
                    metadata_name,
            )

            player = (
                catalog
                .get_player_ability(
                    sp_id,
                    grade=1,
                )
            )

            catalog.validate_collected_player(
                player
            )

            apply_nation_id(
                player,
                nation_lookup,
            )

            player[
                "image_url"
            ] = (
                catalog
                .PLAYER_IMAGE_URL_TEMPLATE
                .format(
                    sp_id=sp_id
                )
            )

            saved = (
                catalog
                .save_player_to_database(
                    player
                )
            )

            catalog.set_player_sync_completed(
                sp_id
            )

            success += 1

            print(
                "SUCCESS"
                f" | {saved['player_name']}"
                f" | {saved['position']}"
                f" | OVR {saved['ovr']}"
            )

        except Exception as error:

            failed.append(
                (
                    sp_id,
                    metadata_name,
                    repr(error),
                )
            )

            try:
                catalog.set_player_sync_failed(
                    sp_id=
                        sp_id,

                    error=
                        error,
                )

            except Exception as state_error:

                print(
                    "SYNC STATE UPDATE FAILED:",
                    repr(
                        state_error
                    ),
                )

            print(
                "FAILED:",
                repr(
                    error
                ),
            )

        finally:

            if delay > 0:

                time.sleep(
                    delay
                )

    # 새 시즌의 국적 매핑을 한 번에 동기화
    sync_nation_table_from_players(
        database_url,
        season_id,
    )

    return (
        success,
        failed,
    )


# =========================================
# CLI
# =========================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description=(
            "FC Online 신규 시즌을 감지하고 "
            "Neon DB에 누락 선수만 추가합니다."
        )
    )

    parser.add_argument(
        "--season-id",
        type=int,
        default=None,
        help=(
            "특정 시즌 ID를 직접 지정합니다."
        ),
    )

    parser.add_argument(
        "--class-name",
        type=str,
        default=None,
        help=(
            "클래스명 또는 약어. "
            "예: UC, Untouchable Champions"
        ),
    )

    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "실제로 DB에 저장합니다. "
            "없으면 확인만 하는 dry-run입니다."
        ),
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help=(
            "DB 저장 전 확인 질문을 생략합니다."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "테스트용 최대 수집 선수 수"
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=(
            catalog
            .PLAYER_REQUEST_DELAY_SECONDS
        ),
        help=(
            "선수 요청 사이 대기 시간(초)"
        ),
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Nexon 메타데이터와 Neon DB만 비교하고 "
            "신규/누락 시즌 여부를 확인합니다."
        ),
    )

    return parser.parse_args()


def main():

    args = (
        parse_arguments()
    )

    database_url = (
        require_database_url()
    )

    print()
    print(
        "FC Online 신규 시즌 검사 시작"
    )

    print(
        "Nexon 시즌 메타데이터 조회..."
    )

    season_metadata = (
        catalog
        .get_season_metadata()
    )

    print(
        "Nexon SPID 메타데이터 조회..."
    )

    cards_by_season = (
        build_metadata_card_map()
    )

    print(
        "Neon 시즌별 저장 현황 조회..."
    )

    db_counts = (
        get_database_season_counts(
            database_url
        )
    )

    candidates = (
        print_missing_season_candidates(
            season_metadata,
            cards_by_season,
            db_counts,
        )
    )

    # =====================================
    # CHECK ONLY
    # =====================================

    if args.check:

        print()
        print(
            "======================================"
        )
        print(
            "CHECK RESULT"
        )
        print(
            "======================================"
        )

        if not candidates:

            print(
                "현재 Nexon 메타데이터 기준 "
                "신규/누락 시즌이 없습니다."
            )

            print(
                "Neon DB는 현재 메타데이터와 "
                "동기화되어 있습니다."
            )

            return 0

        print(
            f"신규/누락 시즌 {len(candidates)}개 발견"
        )

        print()

        for (
            season_id,
            class_name,
            metadata_count,
            database_count,
            missing,
        ) in candidates:

            print(
                f"[{season_id}] "
                f"{class_name}"
            )

            print(
                f"  Nexon: {metadata_count}"
                f" | Neon: {database_count}"
                f" | 추가 필요: {missing}"
            )

        print()

        latest = candidates[0]

        print(
            "가장 최신 후보:"
        )

        print(
            f"{latest[0]}"
            f" | {latest[1]}"
            f" | {latest[4]}명 추가 필요"
        )

        print()

        print(
            "먼저 dry-run:"
        )

        print(
            "python backend/update_new_season.py "
            f"--season-id {latest[0]}"
        )

        return 0

    target_season = (
        select_target_season(
            requested_season_id=
                args.season_id,

            requested_class_name=
                args.class_name,

            season_metadata=
                season_metadata,

            cards_by_season=
                cards_by_season,

            db_counts=
                db_counts,
        )
    )

    if target_season is None:

        print()
        print(
            "DB가 현재 메타데이터와 "
            "동기화되어 있습니다."
        )

        return 0

    metadata = (
        season_metadata.get(
            target_season,
            {},
        )
    )

    class_name = (
        metadata.get(
            "class_name",
            "알 수 없는 클래스",
        )
    )

    season_cards = (
        cards_by_season[
            target_season
        ]
    )

    existing_ids = (
        get_existing_ids_for_season(
            database_url,
            target_season,
        )
    )

    missing_cards = [
        card

        for card
        in season_cards

        if (
            card["sp_id"]
            not in existing_ids
        )
    ]

    print()
    print(
        "======================================"
    )

    print(
        "선택된 시즌"
    )

    print(
        "======================================"
    )

    print(
        "시즌 ID:",
        target_season,
    )

    print(
        "클래스:",
        class_name,
    )

    print(
        "메타데이터 카드:",
        len(
            season_cards
        ),
    )

    print(
        "현재 DB:",
        len(
            existing_ids
        ),
    )

    print(
        "추가 필요:",
        len(
            missing_cards
        ),
    )

    if missing_cards:

        print()
        print(
            "추가 대상 일부:"
        )

        for card in (
            missing_cards[:10]
        ):

            print(
                " -",
                card["sp_id"],
                card["player_name"],
            )

    if not missing_cards:

        print()
        print(
            "이 시즌은 이미 모두 저장되어 있습니다."
        )

        verification = (
            get_verification(
                database_url,
                target_season,
            )
        )

        print(
            verification
        )

        return 0

    if (
        args.limit is not None
    ):

        if args.limit <= 0:

            raise RuntimeError(
                "--limit은 1 이상이어야 합니다."
            )

        work_cards = (
            missing_cards[
                :args.limit
            ]
        )

    else:

        work_cards = (
            missing_cards
        )

    # =====================================
    # DRY RUN
    # =====================================

    if not args.apply:

        print()
        print(
            "DRY RUN 완료."
        )

        print(
            "DB에는 아무 것도 저장하지 않았습니다."
        )

        print()
        print(
            "실제 저장:"
        )

        print(
            "python backend/update_new_season.py "
            f"--season-id {target_season} --apply"
        )

        return 0

    # =====================================
    # CONFIRM
    # =====================================

    if not args.yes:

        print()
        answer = input(
            f"{class_name} "
            f"{len(work_cards)}명을 "
            "Neon에 저장할까요? [y/N]: "
        )

        if (
            answer.strip().lower()
            not in {
                "y",
                "yes",
            }
        ):

            print(
                "취소했습니다."
            )

            return 0

    success, failed = (
        sync_cards(
            cards=
                work_cards,

            season_id=
                target_season,

            class_name=
                class_name,

            database_url=
                database_url,

            delay=
                max(
                    0.0,
                    args.delay,
                ),
        )
    )

    verification = (
        get_verification(
            database_url,
            target_season,
        )
    )

    print()
    print(
        "======================================"
    )
    print(
        "SYNC RESULT"
    )
    print(
        "======================================"
    )

    print(
        "이번 성공:",
        success,
    )

    print(
        "이번 실패:",
        len(
            failed
        ),
    )

    print(
        "현재 시즌 DB 선수:",
        verification[
            "player_count"
        ],
        "/",
        len(
            season_cards
        ),
    )

    print(
        "팀컬러 관계 행:",
        verification[
            "team_rows"
        ],
    )

    print(
        "OVR 오류:",
        verification[
            "invalid_ovr"
        ],
    )

    print(
        "급여 오류:",
        verification[
            "invalid_salary"
        ],
    )

    print(
        "이미지 URL 누락:",
        verification[
            "missing_image"
        ],
    )

    if failed:

        print()
        print(
            "실패 목록"
        )

        for (
            sp_id,
            player_name,
            error,
        ) in failed:

            print(
                f" - {sp_id}"
                f" | {player_name}"
                f" | {error}"
            )

    remaining = (
        len(season_cards)
        -
        verification[
            "player_count"
        ]
    )

    if (
        args.limit is None
        and remaining > 0
    ):

        print()
        print(
            f"아직 {remaining}명이 남았습니다."
        )

        print(
            "같은 명령을 다시 실행하면 "
            "이미 저장된 선수는 건너뜁니다."
        )

        return 2

    print()
    print(
        "완료."
    )

    return 0


if __name__ == "__main__":

    try:

        raise SystemExit(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "사용자가 중단했습니다."
        )

        raise SystemExit(
            130
        )

    except Exception as error:

        print()
        print(
            "ERROR:"
        )

        print(
            repr(
                error
            )
        )

        raise SystemExit(
            1
        )