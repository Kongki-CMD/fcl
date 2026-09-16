from collections import OrderedDict


# =========================================
# FC ONLINE TEAM COLOR ACTIVATION ENGINE
# =========================================

NON_ENHANCE_CATEGORIES = (
    "affiliation",
    "feature",
)


# =========================================
# OFFICIAL ENHANCEMENT TEAM COLORS
#
# FC Online 공식 기준
#
# 동빛      +3 ~ +4
# 은빛      +5 ~ +7
# 금빛      +8 ~ +10
# 백금빛    +11 ~ +13
#
# 각 선수는 가장 높은 해당 구간의
# 강화 팀컬러 하나에만 속한다.
# =========================================

ENHANCEMENT_TEAM_COLOR_RULES = (
    {
        "team_name":
            "동빛 물결",

        "minimum_grade":
            3,

        "maximum_grade":
            4,
    },

    {
        "team_name":
            "은빛 물결",

        "minimum_grade":
            5,

        "maximum_grade":
            7,
    },

    {
        "team_name":
            "금빛 물결",

        "minimum_grade":
            8,

        "maximum_grade":
            10,
    },

    {
        "team_name":
            "백금빛 물결",

        "minimum_grade":
            11,

        "maximum_grade":
            13,
    },
)


def normalize_squad_sp_ids(
    players,
):

    sp_ids = []

    seen_sp_ids = set()


    for player in (
        players
        or []
    ):

        if isinstance(
            player,
            dict,
        ):

            raw_sp_id = (
                player.get(
                    "sp_id"
                )
            )

        else:

            raw_sp_id = (
                player
            )


        try:

            sp_id = int(
                raw_sp_id
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if sp_id <= 0:
            continue


        if (
            sp_id
            in
            seen_sp_ids
        ):

            continue


        seen_sp_ids.add(
            sp_id
        )


        sp_ids.append(
            sp_id
        )


    return sp_ids


def normalize_squad_players(
    players,
):

    normalized_players = []

    seen_sp_ids = set()


    for player in (
        players
        or []
    ):

        if not isinstance(
            player,
            dict,
        ):
            continue


        try:

            sp_id = int(
                player.get(
                    "sp_id"
                )
            )


            grade = int(
                player.get(
                    "grade"
                )
                or 1
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


        if (
            sp_id <= 0
            or
            grade < 1
            or
            grade > 13
        ):
            continue


        if (
            sp_id
            in
            seen_sp_ids
        ):
            continue


        seen_sp_ids.add(
            sp_id
        )


        normalized_players.append(
            {
                "sp_id":
                    sp_id,

                "grade":
                    grade,

                "player_name":
                    (
                        player.get(
                            "player_name"
                        )
                        or ""
                    ),
            }
        )


    return normalized_players


# =========================================
# NORMAL / AFFILIATION / FEATURE TEAM COLORS
# =========================================

def get_active_team_colors_for_squad(
    connection,
    players,
):

    sp_ids = (
        normalize_squad_sp_ids(
            players
        )
    )


    if not sp_ids:

        return []


    with connection.cursor() as cursor:

        cursor.execute(
            """
            WITH matched_colors AS (

                SELECT
                    player_map.team_color_id,

                    COUNT(
                        DISTINCT
                        player_map.sp_id
                    )::INTEGER
                        AS matched_players,

                    ARRAY_AGG(
                        DISTINCT
                        player_map.sp_id
                        ORDER BY
                            player_map.sp_id
                    )
                        AS matched_sp_ids

                FROM
                    fconline_team_color_players
                    AS player_map

                INNER JOIN
                    fconline_team_colors
                    AS team_color

                ON
                    team_color.team_color_id
                    =
                    player_map.team_color_id

                WHERE
                    player_map.sp_id
                    =
                    ANY(%s)

                AND
                    team_color.is_active
                    =
                    TRUE

                AND
                    team_color.category
                    =
                    ANY(%s)

                GROUP BY
                    player_map.team_color_id
            ),

            active_stages AS (

                SELECT
                    matched.team_color_id,

                    matched.matched_players,

                    matched.matched_sp_ids,

                    MAX(
                        team_level.stage
                    )::INTEGER
                        AS active_stage

                FROM
                    matched_colors
                    AS matched

                INNER JOIN
                    fconline_team_color_levels
                    AS team_level

                ON
                    team_level.team_color_id
                    =
                    matched.team_color_id

                AND
                    team_level.required_players
                    <=
                    matched.matched_players

                GROUP BY
                    matched.team_color_id,
                    matched.matched_players,
                    matched.matched_sp_ids
            )

            SELECT
                team_color.team_color_id,

                team_color.team_name,

                team_color.category,

                team_color.team_color_type,

                team_color.icon_url,

                team_color.max_stage,

                active.active_stage,

                active.matched_players,

                active.matched_sp_ids,

                team_level.required_players,

                effect.stat_key,

                effect.stat_name,

                effect.bonus,

                effect.effect_order

            FROM
                active_stages
                AS active

            INNER JOIN
                fconline_team_colors
                AS team_color

            ON
                team_color.team_color_id
                =
                active.team_color_id

            INNER JOIN
                fconline_team_color_levels
                AS team_level

            ON
                team_level.team_color_id
                =
                active.team_color_id

            AND
                team_level.stage
                =
                active.active_stage

            LEFT JOIN
                fconline_team_color_effects
                AS effect

            ON
                effect.team_color_id
                =
                active.team_color_id

            AND
                effect.stage
                =
                active.active_stage

            ORDER BY

                CASE
                    WHEN
                        team_color.category
                        =
                        'affiliation'
                    THEN 1

                    WHEN
                        team_color.category
                        =
                        'feature'
                    THEN 2

                    ELSE 9
                END,

                team_color.team_name ASC,

                effect.effect_order ASC
            """,
            (
                sp_ids,

                list(
                    NON_ENHANCE_CATEGORIES
                ),
            ),
        )


        rows = (
            cursor.fetchall()
        )


    active_colors = (
        OrderedDict()
    )


    for row in rows:

        team_color_id = int(
            row[
                "team_color_id"
            ]
        )


        if (
            team_color_id
            not in
            active_colors
        ):

            matched_sp_ids = [
                int(
                    sp_id
                )

                for sp_id
                in (
                    row.get(
                        "matched_sp_ids"
                    )
                    or []
                )
            ]


            active_colors[
                team_color_id
            ] = {

                "team_color_id":
                    team_color_id,

                "team_name":
                    row[
                        "team_name"
                    ],

                "category":
                    row[
                        "category"
                    ],

                "team_color_type":
                    row[
                        "team_color_type"
                    ],

                "icon_url":
                    (
                        row.get(
                            "icon_url"
                        )
                        or ""
                    ),

                "stage":
                    int(
                        row[
                            "active_stage"
                        ]
                    ),

                "max_stage":
                    int(
                        row.get(
                            "max_stage"
                        )
                        or
                        row[
                            "active_stage"
                        ]
                    ),

                "required_players":
                    int(
                        row[
                            "required_players"
                        ]
                        or 0
                    ),

                "matched_players":
                    int(
                        row[
                            "matched_players"
                        ]
                    ),

                "matched_sp_ids":
                    matched_sp_ids,

                "effects":
                    [],
            }


        if (
            row.get(
                "stat_key"
            )
            is None
        ):
            continue


        active_colors[
            team_color_id
        ][
            "effects"
        ].append(
            {
                "stat_key":
                    row[
                        "stat_key"
                    ],

                "stat_name":
                    row[
                        "stat_name"
                    ],

                "bonus":
                    int(
                        row[
                            "bonus"
                        ]
                    ),

                "effect_order":
                    int(
                        row[
                            "effect_order"
                        ]
                        or 0
                    ),
            }
        )


    return list(
        active_colors.values()
    )


# =========================================
# ENHANCEMENT TEAM COLOR DEFINITIONS
# =========================================

def get_enhancement_team_color_definitions(
    connection,
):

    official_names = [
        rule[
            "team_name"
        ]

        for rule
        in ENHANCEMENT_TEAM_COLOR_RULES
    ]


    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                team_color.team_color_id,

                team_color.team_name,

                team_color.category,

                team_color.team_color_type,

                team_color.icon_url,

                team_color.max_stage,

                team_level.stage,

                team_level.required_players,

                effect.stat_key,

                effect.stat_name,

                effect.bonus,

                effect.effect_order

            FROM
                fconline_team_colors
                AS team_color

            INNER JOIN
                fconline_team_color_levels
                AS team_level

            ON
                team_level.team_color_id
                =
                team_color.team_color_id

            LEFT JOIN
                fconline_team_color_effects
                AS effect

            ON
                effect.team_color_id
                =
                team_color.team_color_id

            AND
                effect.stage
                =
                team_level.stage

            WHERE
                team_color.is_active
                =
                TRUE

            AND
                team_color.category
                =
                'enhance'

            AND
                team_color.team_name
                =
                ANY(%s)

            ORDER BY
                team_color.team_name,
                team_level.stage,
                effect.effect_order
            """,
            (
                official_names,
            ),
        )


        rows = (
            cursor.fetchall()
        )


    definitions = {}


    for row in rows:

        team_name = str(
            row[
                "team_name"
            ]
        )


        if (
            team_name
            not in
            definitions
        ):

            definitions[
                team_name
            ] = {

                "team_color_id":
                    int(
                        row[
                            "team_color_id"
                        ]
                    ),

                "team_name":
                    team_name,

                "category":
                    "enhance",

                "team_color_type":
                    row[
                        "team_color_type"
                    ],

                "icon_url":
                    (
                        row.get(
                            "icon_url"
                        )
                        or ""
                    ),

                "max_stage":
                    int(
                        row.get(
                            "max_stage"
                        )
                        or 1
                    ),

                "levels":
                    {},
            }


        stage = int(
            row[
                "stage"
            ]
        )


        if (
            stage
            not in
            definitions[
                team_name
            ][
                "levels"
            ]
        ):

            definitions[
                team_name
            ][
                "levels"
            ][
                stage
            ] = {

                "stage":
                    stage,

                "required_players":
                    int(
                        row[
                            "required_players"
                        ]
                        or 0
                    ),

                "effects":
                    [],
            }


        if (
            row.get(
                "stat_key"
            )
            is None
        ):
            continue


        definitions[
            team_name
        ][
            "levels"
        ][
            stage
        ][
            "effects"
        ].append(
            {
                "stat_key":
                    row[
                        "stat_key"
                    ],

                "stat_name":
                    row[
                        "stat_name"
                    ],

                "bonus":
                    int(
                        row[
                            "bonus"
                        ]
                    ),

                "effect_order":
                    int(
                        row[
                            "effect_order"
                        ]
                        or 0
                    ),
            }
        )


    return definitions


# =========================================
# ENHANCEMENT TEAM COLOR ACTIVATION
# =========================================

def get_active_enhancement_team_colors_for_squad(
    connection,
    players,
):

    squad_players = (
        normalize_squad_players(
            players
        )
    )


    if not squad_players:

        return []


    definitions = (
        get_enhancement_team_color_definitions(
            connection
        )
    )


    active_colors = []


    for rule in (
        ENHANCEMENT_TEAM_COLOR_RULES
    ):

        team_name = (
            rule[
                "team_name"
            ]
        )


        minimum_grade = int(
            rule[
                "minimum_grade"
            ]
        )


        maximum_grade = int(
            rule[
                "maximum_grade"
            ]
        )


        # =====================================
        # 누적 조건이 아니다.
        #
        # 예:
        # +8 선수는 금빛 물결
        # 은빛 / 동빛 인원으로 다시 세지 않는다.
        # =====================================

        matched_players = [
            player

            for player
            in squad_players

            if (
                minimum_grade
                <=
                int(
                    player[
                        "grade"
                    ]
                )
                <=
                maximum_grade
            )
        ]


        matched_count = len(
            matched_players
        )


        if matched_count <= 0:
            continue


        definition = (
            definitions.get(
                team_name
            )
        )


        # 공식 단계 DB 자체가 없으면
        # 임의 효과를 만들지 않는다.
        if definition is None:
            continue


        eligible_levels = [
            level

            for level
            in (
                definition[
                    "levels"
                ]
                .values()
            )

            if (
                int(
                    level[
                        "required_players"
                    ]
                )
                <=
                matched_count
            )
        ]


        # 5명 미만 등
        # 어느 단계도 활성화되지 않음
        if not eligible_levels:
            continue


        active_level = max(
            eligible_levels,

            key=lambda level:
                int(
                    level[
                        "stage"
                    ]
                ),
        )


        active_colors.append(
            {
                "team_color_id":
                    int(
                        definition[
                            "team_color_id"
                        ]
                    ),

                "team_name":
                    team_name,

                "category":
                    "enhance",

                "team_color_type":
                    definition[
                        "team_color_type"
                    ],

                "icon_url":
                    definition[
                        "icon_url"
                    ],

                "stage":
                    int(
                        active_level[
                            "stage"
                        ]
                    ),

                "max_stage":
                    int(
                        definition[
                            "max_stage"
                        ]
                    ),

                "required_players":
                    int(
                        active_level[
                            "required_players"
                        ]
                    ),

                "matched_players":
                    matched_count,

                "matched_sp_ids": [
                    int(
                        player[
                            "sp_id"
                        ]
                    )

                    for player
                    in matched_players
                ],

                "minimum_grade":
                    minimum_grade,

                "maximum_grade":
                    maximum_grade,

                "effects":
                    list(
                        active_level[
                            "effects"
                        ]
                    ),
            }
        )


    # 높은 강화 팀컬러부터 표시
    active_colors.sort(
        key=lambda item:
            int(
                item[
                    "minimum_grade"
                ]
            ),
        reverse=True,
    )


    return active_colors