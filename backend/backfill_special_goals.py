from backend.main import (
    get_db_connection,
    get_match_detail,
    get_match_special_goal_stats,
)


def get_match_info_sp_ids(
    match_info,
):

    sp_ids = set()


    for player in (
        match_info.get(
            "player"
        )
        or []
    ):

        sp_id = (
            player.get(
                "spId"
            )
        )


        if sp_id is None:
            continue


        try:

            sp_ids.add(
                int(
                    sp_id
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            continue


    return sp_ids


def get_identity_score(
    match_info,
    expected_ouid,
    expected_nickname,
    expected_sp_ids,
):

    score = 0


    # =========================
    # OUID 일치
    # 가장 강한 증거
    # =========================

    if (
        expected_ouid
        and
        str(
            match_info.get(
                "ouid"
            )
            or ""
        )
        ==
        str(
            expected_ouid
        )
    ):

        score += 10000


    # =========================
    # 닉네임 일치
    # =========================

    if (
        expected_nickname
        and
        str(
            match_info.get(
                "nickname"
            )
            or ""
        )
        ==
        str(
            expected_nickname
        )
    ):

        score += 5000


    # =========================
    # 당시 저장된 스쿼드와
    # NEXON 스쿼드 SPID 비교
    # =========================

    nexon_sp_ids = (
        get_match_info_sp_ids(
            match_info
        )
    )


    overlap_count = len(
        nexon_sp_ids
        &
        expected_sp_ids
    )


    score += (
        overlap_count
        * 100
    )


    return score


def resolve_match_infos(
    match_data,
    row,
):

    match_infos = list(
        match_data.get(
            "matchInfo"
        )
        or []
    )


    if len(match_infos) < 2:

        return (
            None,
            None,
        )


    expected_a_sp_ids = {
        int(sp_id)

        for sp_id
        in (
            row.get(
                "team_a_sp_ids"
            )
            or []
        )

        if sp_id is not None
    }


    expected_b_sp_ids = {
        int(sp_id)

        for sp_id
        in (
            row.get(
                "team_b_sp_ids"
            )
            or []
        )

        if sp_id is not None
    }


    best_pair = None
    best_score = -1


    # =========================
    # 서로 다른 두 참가자를
    # TEAM A / TEAM B에 배정
    # =========================

    for team_a_info in match_infos:

        for team_b_info in match_infos:

            if (
                team_a_info
                is
                team_b_info
            ):

                continue


            team_a_score = (
                get_identity_score(
                    team_a_info,
                    row.get(
                        "team_a_ouid"
                    ),
                    row.get(
                        "team_a_nickname"
                    ),
                    expected_a_sp_ids,
                )
            )


            team_b_score = (
                get_identity_score(
                    team_b_info,
                    row.get(
                        "team_b_ouid"
                    ),
                    row.get(
                        "team_b_nickname"
                    ),
                    expected_b_sp_ids,
                )
            )


            total_score = (
                team_a_score
                +
                team_b_score
            )


            if (
                total_score
                >
                best_score
            ):

                best_score = (
                    total_score
                )

                best_pair = (
                    team_a_info,
                    team_b_info,
                )


    if (
        best_pair is None
        or
        best_score <= 0
    ):

        return (
            None,
            None,
        )


    return best_pair


def backfill_special_goals():

    # =========================
    # 기존 NEXON SET + 당시 스쿼드
    # =========================

    with get_db_connection() as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    ss.id
                        AS series_set_id,

                    ss.series_id,
                    ss.set_number,
                    ss.nexon_match_id,

                    s.team_a_id,
                    s.team_b_id,

                    team_a.ouid
                        AS team_a_ouid,

                    team_a.fc_nickname
                        AS team_a_nickname,

                    team_b.ouid
                        AS team_b_ouid,

                    team_b.fc_nickname
                        AS team_b_nickname,

                    ARRAY(
                        SELECT
                            sssp.sp_id

                        FROM
                            series_set_squad_players
                            AS sssp

                        WHERE
                            sssp.series_set_id
                            =
                            ss.id

                            AND
                            sssp.side
                            =
                            'team_a'
                    )
                        AS team_a_sp_ids,

                    ARRAY(
                        SELECT
                            sssp.sp_id

                        FROM
                            series_set_squad_players
                            AS sssp

                        WHERE
                            sssp.series_set_id
                            =
                            ss.id

                            AND
                            sssp.side
                            =
                            'team_b'
                    )
                        AS team_b_sp_ids

                FROM series_sets AS ss

                JOIN series AS s
                    ON s.id =
                        ss.series_id

                JOIN participants AS team_a
                    ON team_a.id =
                        s.team_a_id

                JOIN participants AS team_b
                    ON team_b.id =
                        s.team_b_id

                WHERE
                    ss.nexon_match_id
                    IS NOT NULL

                ORDER BY
                    ss.series_id,
                    ss.set_number
                """
            )


            sets = (
                cursor.fetchall()
            )


    total_count = len(
        sets
    )


    print(
        (
            "[SPECIAL GOAL BACKFILL] "
            f"target_sets={total_count}"
        ),
        flush=True,
    )


    success_count = 0
    skipped_count = 0


    for index, row in enumerate(
        sets,
        start=1,
    ):

        match_id = (
            row[
                "nexon_match_id"
            ]
        )


        try:

            match_data = (
                get_match_detail(
                    match_id
                )
            )


            (
                team_a_match_info,
                team_b_match_info,
            ) = (
                resolve_match_infos(
                    match_data,
                    row,
                )
            )


            if (
                team_a_match_info
                is None
                or
                team_b_match_info
                is None
            ):

                print(
                    (
                        "[SPECIAL GOAL BACKFILL] "
                        f"{index}/{total_count} "
                        f"series={row['series_id']} "
                        f"set={row['set_number']} "
                        "SKIP participant_not_found"
                    ),
                    flush=True,
                )


                # 어떤 닉네임으로 기록돼 있는지
                # 바로 확인할 수 있게 출력
                print(
                    (
                        "    NEXON participants="
                        +
                        str([
                            {
                                "nickname":
                                    info.get(
                                        "nickname"
                                    ),

                                "ouid":
                                    info.get(
                                        "ouid"
                                    ),

                                "players":
                                    len(
                                        info.get(
                                            "player"
                                        )
                                        or []
                                    ),
                            }

                            for info
                            in (
                                match_data.get(
                                    "matchInfo"
                                )
                                or []
                            )
                        ])
                    ),
                    flush=True,
                )


                skipped_count += 1
                continue


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


            with get_db_connection() as connection:

                with connection.cursor() as cursor:

                    # =========================
                    # 자책골
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

                            row[
                                "series_set_id"
                            ],
                        ),
                    )


                    # =========================
                    # PK 초기화
                    # =========================

                    cursor.execute(
                        """
                        UPDATE
                            series_set_squad_players

                        SET
                            penalty_goals = 0

                        WHERE
                            series_set_id = %s
                        """,
                        (
                            row[
                                "series_set_id"
                            ],
                        ),
                    )


                    # =========================
                    # TEAM A PK
                    # =========================

                    for (
                        sp_id,
                        penalty_goals,
                    ) in (
                        team_a_special[
                            "penalty_goals_by_sp_id"
                        ].items()
                    ):

                        cursor.execute(
                            """
                            UPDATE
                                series_set_squad_players

                            SET
                                penalty_goals = %s

                            WHERE
                                series_set_id = %s

                                AND
                                side = 'team_a'

                                AND
                                sp_id = %s
                            """,
                            (
                                penalty_goals,

                                row[
                                    "series_set_id"
                                ],

                                sp_id,
                            ),
                        )


                    # =========================
                    # TEAM B PK
                    # =========================

                    for (
                        sp_id,
                        penalty_goals,
                    ) in (
                        team_b_special[
                            "penalty_goals_by_sp_id"
                        ].items()
                    ):

                        cursor.execute(
                            """
                            UPDATE
                                series_set_squad_players

                            SET
                                penalty_goals = %s

                            WHERE
                                series_set_id = %s

                                AND
                                side = 'team_b'

                                AND
                                sp_id = %s
                            """,
                            (
                                penalty_goals,

                                row[
                                    "series_set_id"
                                ],

                                sp_id,
                            ),
                        )


                connection.commit()


            success_count += 1


            print(
                (
                    "[SPECIAL GOAL BACKFILL] "
                    f"{index}/{total_count} "
                    f"series={row['series_id']} "
                    f"set={row['set_number']} "
                    f"own=("
                    f"{team_a_special['own_goals']},"
                    f"{team_b_special['own_goals']}"
                    ") "
                    f"pk=("
                    f"{sum(team_a_special['penalty_goals_by_sp_id'].values())},"
                    f"{sum(team_b_special['penalty_goals_by_sp_id'].values())}"
                    ")"
                ),
                flush=True,
            )


        except Exception as error:

            skipped_count += 1


            print(
                (
                    "[SPECIAL GOAL BACKFILL] "
                    f"{index}/{total_count} "
                    f"series={row['series_id']} "
                    f"set={row['set_number']} "
                    f"ERROR {error}"
                ),
                flush=True,
            )


    print(
        (
            "[SPECIAL GOAL BACKFILL] completed "
            f"success={success_count} "
            f"skipped={skipped_count}"
        ),
        flush=True,
    )


if __name__ == "__main__":

    backfill_special_goals()