# backend/player_supply_restriction.py

from functools import lru_cache

import httpx


FC_ONLINE_SEASON_METADATA_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/seasonid.json"
)

OFFICIAL_SUPPLY_RESTRICTION_NOTICE_SN = 6213

OFFICIAL_SUPPLY_RESTRICTION_EFFECTIVE_DATE = (
    "2026-08-27"
)


CURRENT_SUPPLY_RESTRICTED_CLASSES = {
    "2017",
    "2018",
    "2019",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",

    "18PLA",
    "18PLS",
    "18TOTY",

    "19NG",
    "19PLA",
    "19PLS",
    "19TOTS",
    "19TOTY",
    "19UCL",

    "20KB",
    "20KL",
    "20NG",
    "20PLA",
    "20TOTS",
    "20TOTY",
    "20TOTY-N",
    "20UCL",

    "21KB",
    "21KL",
    "21NG",
    "21PL",
    "21TOTS",
    "21TOTY",
    "21TOTY-N",
    "21UCL",

    "22KB",
    "22KL",
    "22NG",
    "22PL",
    "22TOTS",
    "22TOTY",
    "22TOTY-N",
    "22UCL",

    "23KB",
    "23KL",
    "23PL",
    "23TOTS",
    "23TOTY",
    "23TOTY-N",
    "23UCL",

    "24KB",
    "24KL",
    "24PL",
    "24TOTS",
    "24TOTY",
    "24TOTY-N",
    "24UCL",

    "25IM-FB",
    "25IM-S&P",
    "25KL",
    "25TOTS",
    "25TOTY",
    "25TOTY-N",

    "26TOTY",
    "26TOTY-N",

    "BWC",
    "EU24",
    "WC22",
}

# =========================================
# 과거 공급 제한 이력
# =========================================

HISTORICAL_SUPPLY_RESTRICTED_CLASSES = {
    "MCFC",
    "LKI",
    "ICONTM",
}


# 기존 참조 호환용 통합 목록.
OFFICIAL_SUPPLY_RESTRICTED_CLASSES = (
    CURRENT_SUPPLY_RESTRICTED_CLASSES
    |
    HISTORICAL_SUPPLY_RESTRICTED_CLASSES
)


def normalize_supply_class_name(
    value,
):
    class_name = (
        str(
            value
            or ""
        )
        .split(
            "(",
            1,
        )[0]
        .strip()
        .upper()
        .replace(
            " ",
            "",
        )
    )

    return class_name


def get_supply_restriction_status(
    class_name,
):
    class_code = (
        normalize_supply_class_name(
            class_name
        )
    )


    current_restricted = (
        class_code
        in
        CURRENT_SUPPLY_RESTRICTED_CLASSES
    )


    historical_restricted = (
        class_code
        in
        HISTORICAL_SUPPLY_RESTRICTED_CLASSES
    )


    restricted = (
        current_restricted
        or
        historical_restricted
    )


    if current_restricted:

        source = (
            "official_notice"
        )

        notice_sn = (
            OFFICIAL_SUPPLY_RESTRICTION_NOTICE_SN
        )

        effective_date = (
            OFFICIAL_SUPPLY_RESTRICTION_EFFECTIVE_DATE
        )

        note = (
            "FC Online 공식 공지 "
            f"#{OFFICIAL_SUPPLY_RESTRICTION_NOTICE_SN}"
            " 공급 제한 클래스"
        )


    elif historical_restricted:

        source = (
            "historical_official_notice"
        )

        notice_sn = None

        effective_date = None

        note = (
            "FC Online 과거 공급 제한 이력 클래스"
        )


    else:

        source = None
        notice_sn = None
        effective_date = None
        note = None


    return {
        "supply_restricted":
            restricted,

        "supply_restriction_class":
            (
                class_code
                if class_code
                else None
            ),

        "supply_restriction_source":
            source,

        "supply_restriction_notice_sn":
            notice_sn,

        "supply_restriction_effective_date":
            effective_date,

        "supply_restriction_note":
            note,
    }

@lru_cache(
    maxsize=1
)
def get_supply_season_class_map():

    response = httpx.get(
        FC_ONLINE_SEASON_METADATA_URL,
        timeout=10.0,
        follow_redirects=True,
    )

    response.raise_for_status()

    payload = response.json()


    return {
        int(
            item[
                "seasonId"
            ]
        ):
            item.get(
                "className"
            )

        for item
        in payload

        if item.get(
            "seasonId"
        )
        is not None
    }


def get_supply_restriction_status_by_season_id(
    season_id,
):

    try:

        normalized_season_id = int(
            season_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return (
            get_supply_restriction_status(
                None
            )
        )


    try:

        class_name = (
            get_supply_season_class_map()
            .get(
                normalized_season_id
            )
        )

    except Exception:

        class_name = None


    return (
        get_supply_restriction_status(
            class_name
        )
    )