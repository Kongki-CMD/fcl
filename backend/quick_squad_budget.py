"""Quick Squad: 예산 배분 및 메모리 제한형 조합 탐색."""

from heapq import heappush, heapreplace
from itertools import count


CORE_POSITIONS = frozenset(
    """
    ST CF LS RS LF RF LW RW
    CAM LAM RAM CM LCM RCM
    CDM LDM RDM LM RM
    CB LCB RCB SW
    """.split()
)

META_POPULARITY_WEIGHT = 6.0
META_BALANCE_GAP_WEIGHT = 0.35
GENERATION_RESTRICTED_PENALTY = 1.5
SUPPLY_RESTRICTED_PENALTY = 1.0
GENERATION_RESTRICTED_OVR_ADVANTAGE = 3
CORE_SLOT_MIN_TARGET_RATIO = 0.20
CORE_SLOT_UNDERINVEST_WEIGHT = 2.5

CORE_SLOT_OVER_TARGET_RATIO = 3.0
CORE_SLOT_OVERINVEST_WEIGHT = 0.75


def is_core(position):
    return (
        str(position).strip().upper()
        in CORE_POSITIONS
    )


def make_budget_plan(
    slots,
    budget,
    locked=(),
    mode="core",
    strength=200,
):
    if mode not in ("core", "balanced"):
        raise ValueError(
            "올바르지 않은 예산 배분 방식입니다."
        )

    if (
        not isinstance(strength, int)
        or not 100 <= strength <= 300
    ):
        raise ValueError(
            "투자 강도는 100~300이어야 합니다."
        )

    locked_cost = sum(
        int(p["price"]) for p in locked
    )

    remaining = int(budget) - locked_cost

    if remaining < 0:
        raise ValueError(
            "고정 선수 가격이 예산을 초과합니다."
        )

    occupied = {
        int(p["slot_index"])
        for p in locked
    }

    indices = [
        i for i in range(len(slots))
        if i not in occupied
    ]

    strength = (
        strength if mode == "core" else 100
    )

    weights = [
        strength if is_core(slots[i]) else 100
        for i in indices
    ]

    targets = [None] * len(slots)

    if weights:
        total_weight = sum(weights)

        parts = [
            divmod(remaining * w, total_weight)
            for w in weights
        ]

        amounts = [q for q, _ in parts]

        # 정수 BP의 나머지를 분배해 합계를 정확히 보존.
        remainder = remaining - sum(amounts)

        order = sorted(
            range(len(weights)),
            key=lambda i: (-parts[i][1], i),
        )

        for i in order[:remainder]:
            amounts[i] += 1

        for i, amount in zip(indices, amounts):
            targets[i] = amount

    core_indices = [
        i for i in indices
        if is_core(slots[i])
    ]

    other_indices = [
        i for i in indices
        if not is_core(slots[i])
    ]

    return {
        "mode": mode,
        "core_strength": strength,
        "budget_bp": int(budget),
        "locked_total_price": locked_cost,
        "remaining_budget": remaining,
        "remaining_indices": indices,
        "core_indices": core_indices,
        "other_indices": other_indices,
        "targets": targets,
        "core_target": sum(
            targets[i] for i in core_indices
        ),
        "other_target": sum(
            targets[i] for i in other_indices
        ),
    }


def summarize_budget_plan(plan, players):
    by_index = {
        int(p["slot_index"]): p
        for p in players
    }

    actuals = [
        (
            int(by_index[i]["price"])
            if i in by_index
            else 0
        )
        for i in range(len(plan["targets"]))
    ]

    # 고정 선수는 이미 차감했으므로,
    # 실제 추천된 자리의 지출만 집계한다.
    core = sum(
        actuals[i]
        for i in plan["core_indices"]
    )

    other = sum(
        actuals[i]
        for i in plan["other_indices"]
    )

    spent = core + other

    return {
        **plan,
        "core_actual": core,
        "other_actual": other,
        "remaining_actual": spent,
        "actuals": actuals,
        "unspent_budget": (
            plan["remaining_budget"] - spent
        ),
    }


def _is_acquisition_restricted(
    player,
):
    return (
        bool(
            player.get(
                "generation_restricted",
                False,
            )
        )
        or
        bool(
            player.get(
                "supply_restricted",
                False,
            )
        )
    )


def _prepare_options(
    options,
    target,
    budget,
    allow_high,
    core_slot,
):
    values = [
        p for p in options
        if (
            0 < int(p["price"]) <= budget
            and int(p["salary"]) > 0
            and (
                allow_high
                or int(p["grade"]) < 9
            )
        )
    ]

    if not values:
        return []

    # 목표 예산을 먼저 정규화한다.
    target = max(
        1,
        int(target),
    )


    # =========================================
    # OVR 하한의 기준 선수를
    # "무조건 최고 OVR"로 잡지 않는다.
    #
    # 해당 자리 목표 예산의 3배 이하에서
    # 구매 가능한 선수들을 기준으로
    # 현실적인 최고 OVR을 계산한다.
    #
    # 저예산에서 비싼 카드 한 장 때문에
    # 싼 실사용 후보가 전부 잘리는 현상 방지.
    # =========================================

    reference_price_cap = min(
        int(budget),
        target * 3,
    )


    reference_values = [
        player
        for player in values
        if (
            int(player["price"])
            <= reference_price_cap
        )
    ]


    # 해당 가격대 후보가 아예 없을 때만
    # 전체 후보 중 싼 카드 몇 장을 기준으로 사용.
    if not reference_values:

        reference_values = sorted(
            values,
            key=lambda player: (
                int(player["price"]),
                -int(player["ovr"]),
            ),
        )[:8]


    best_slot_ovr = max(
        int(player["ovr"])
        for player in reference_values
    )


    ovr_gap = (
        10
        if core_slot
        else 16
    )


    competitive_floor = (
        best_slot_ovr
        -
        ovr_gap
    )


    competitive_values = [
        player
        for player in values
        if (
            int(player["ovr"])
            >= competitive_floor
        )
    ]


    # =========================================
    # 작은 팀컬러 보호
    #
    # OVR 하한을 통과한 후보가 너무 적으면
    # 추천 자체가 불가능해질 수 있다.
    #
    # 따라서:
    # - 코어 자리: 최소 6개의 서로 다른 선수명
    # - 비코어 자리: 최소 4개의 서로 다른 선수명
    #
    # 까지는 원본 후보에서 성능 좋은 순으로 보충한다.
    #
    # 같은 선수의 다른 시즌만 여러 장 들어가는 것도
    # 방지하기 위해 player_name 기준으로 다양성을 확보한다.
    # =========================================

    minimum_unique_names = (
        6
        if core_slot
        else 4
    )


    selected = {}
    selected_names = set()


    # 우선 경쟁력 하한을 통과한 선수부터 유지.
    for player in sorted(
        competitive_values,
        key=lambda player: (
            -int(player["ovr"]),
            int(player["salary"]),
            int(player["price"]),
        ),
    ):

        name_key = (
            str(player["player_name"])
            .strip()
            .casefold()
        )

        card_key = (
            int(player["sp_id"]),
            int(player["grade"]),
        )

        selected.setdefault(
            card_key,
            player,
        )

        selected_names.add(
            name_key
        )


    # 서로 다른 선수명이 너무 적을 때만
    # 원래 후보에서 추가 보충.
    if (
        len(selected_names)
        <
        minimum_unique_names
    ):

        for player in sorted(
            values,
            key=lambda player: (
                -int(player["ovr"]),
                int(player["salary"]),
                int(player["price"]),
            ),
        ):

            name_key = (
                str(player["player_name"])
                .strip()
                .casefold()
            )

            if (
                name_key
                in selected_names
            ):
                continue

            card_key = (
                int(player["sp_id"]),
                int(player["grade"]),
            )

            selected.setdefault(
                card_key,
                player,
            )

            selected_names.add(
                name_key
            )

            if (
                len(selected_names)
                >=
                minimum_unique_names
            ):
                break


    # 경쟁력 후보가 하나도 없었던 극단적인 경우까지 보호.
    if not selected:

        for player in reference_values:

            selected[
                (
                    int(player["sp_id"]),
                    int(player["grade"]),
                )
            ] = player


    values = list(
        selected.values()
    )

    # =========================================
    # 생성 제한 선수 후순위
    #
    # 같은 포지션에 충분히 경쟁력 있는
    # 생성 가능 선수가 존재하면
    # 생성 제한 선수는 후보에서 뒤로 미룬다.
    #
    # 단, 생성 제한 선수가 생성 가능 최고
    # OVR보다 확실히 높으면 후보로 유지한다.
    # =========================================

    generation_available_values = [
        player

        for player
        in values

        if not _is_acquisition_restricted(
            player
        )
    ]

    generation_restricted_values = [
        player

        for player
        in values

        if _is_acquisition_restricted(
            player
        )
    ]

    if generation_restricted_values:

        print(
            "[QUICK SQUAD ACQUISITION RESTRICTED]",
            [
                {
                    "sp_id":
                        int(
                            player[
                                "sp_id"
                            ]
                        ),

                    "name":
                        player.get(
                            "player_name"
                        ),

                    "ovr":
                        int(
                            player[
                                "ovr"
                            ]
                        ),

                    "generation":
                        bool(
                            player.get(
                                "generation_restricted",
                                False,
                            )
                        ),

                    "supply":
                        bool(
                            player.get(
                                "supply_restricted",
                                False,
                            )
                        ),

                    "class":
                        player.get(
                            "supply_restriction_class"
                        ),
                }

                for player
                in generation_restricted_values
            ],
            flush=True,
        )

    if (
        generation_available_values
        and generation_restricted_values
    ):

        best_available_ovr = max(
            int(player["ovr"])
            for player
            in generation_available_values
        )


        preferred_values = list(
            generation_available_values
        )


        preferred_values.extend(
            player
            for player
            in generation_restricted_values
            if (
                int(player["ovr"])
                >=
                best_available_ovr
                +
                GENERATION_RESTRICTED_OVR_ADVANTAGE
            )
        )


        preferred_unique_names = {
            str(player["player_name"])
            .strip()
            .casefold()

            for player
            in preferred_values
        }


        # 작은 팀컬러에서 후보 부족으로
        # 스쿼드 생성 자체가 실패하는 것을 방지.
        generation_minimum_unique_names = (
            3
            if core_slot
            else 2
        )

        if (
            len(preferred_unique_names)
            >= generation_minimum_unique_names
        ):
            values = preferred_values

    if core_slot:
        groups = (
            sorted(
                values,
                key=lambda p: (
                    -float(
                        p.get("popularity_score", 0)
                        or 0
                    ),
                    -p["ovr"],
                    p["price"],
                ),
            )[:10],

            sorted(
                values,
                key=lambda p: (
                    -p["ovr"],
                    p["price"],
                ),
            )[:10],

            sorted(
                values,
                key=lambda p: (
                    abs(p["price"] - target) / target,
                    -p["ovr"],
                ),
            )[:10],

            sorted(
                values,
                key=lambda p: (
                    -p["price"],
                    -p["ovr"],
                ),
            )[:6],
        )

    else:
        groups = (
            sorted(
                values,
                key=lambda p: (
                    -float(
                        p.get("popularity_score", 0)
                        or 0
                    ),
                    -p["ovr"],
                    p["salary"],
                    p["price"],
                ),
            )[:8],

            sorted(
                values,
                key=lambda p: (
                    -p["ovr"],
                    p["salary"],
                    p["price"],
                ),
            )[:8],

            sorted(
                values,
                key=lambda p: (
                    p["salary"],
                    -p["ovr"],
                    p["price"],
                ),
            )[:10],

            sorted(
                values,
                key=lambda p: (
                    p["price"],
                    -p["ovr"],
                    p["salary"],
                ),
            )[:10],

            sorted(
                values,
                key=lambda p: (
                    abs(p["price"] - target) / target,
                    -p["ovr"],
                    p["salary"],
                ),
            )[:8],
        )

    chosen = {}

    for group in groups:
        for p in group:
            chosen[
                (int(p["sp_id"]), int(p["grade"]))
            ] = p

    return list(chosen.values())[:40]


def search_budget_squad(
    options_by_slot,
    slot_indices,
    plan,
    salary_cap,
    excluded_names=(),
    max_high=2,
    recommendation_mode="meta",
):
    """
    목표 예산과 OVR을 함께 평가한다.
    한 단계에서 최대 128개 상태만 유지한다.
    """

    recommendation_mode = (
        str(
            recommendation_mode
            or "meta"
        )
        .strip()
        .lower()
    )


    if recommendation_mode not in (
        "meta",
        "performance",
        "value",
    ):
        raise ValueError(
            "올바르지 않은 추천 모드입니다."
        )

    n = len(options_by_slot)

    if n != len(slot_indices):
        raise ValueError(
            "포지션과 후보 목록 수가 다릅니다."
        )

    if n == 0:
        return []

    budget = plan["remaining_budget"]

    if budget <= 0 or salary_cap <= 0:
        return None

    targets = [
        max(1, plan["targets"][i])
        for i in slot_indices
    ]

    prepared = [
        _prepare_options(
            options,
            target,
            budget,
            max_high > 0,
            (
                slot_indices[i]
                in plan["core_indices"]
            ),
        )
        for i, (
            options,
            target,
        ) in enumerate(
            zip(
                options_by_slot,
                targets,
            )
        )
    ]

    if any(not options for options in prepared):
        return None

    # 후보가 적은 포지션부터 탐색.
    order = sorted(
        range(n),
        key=lambda i: len(prepared[i]),
    )

    ordered = [prepared[i] for i in order]

    ordered_targets = [
        targets[i] for i in order
    ]

    ordered_core = [
        slot_indices[i] in plan["core_indices"]
        for i in order
    ]

    min_price = [0] * (n + 1)
    min_salary = [0] * (n + 1)

    for i in range(n - 1, -1, -1):
        min_price[i] = (
            min_price[i + 1]
            + min(p["price"] for p in ordered[i])
        )

        min_salary[i] = (
            min_salary[i + 1]
            + min(p["salary"] for p in ordered[i])
        )

    if (
        min_price[0] > budget
        or min_salary[0] > salary_cap
    ):
        return None

    names = frozenset(
        str(name).strip().casefold()
        for name in excluded_names
    )

# 선수, 이름, 비용, 급여, OVR,
# 고강화 수, 목표 편차,
# 코어 지출, 인기도 합계,
# 현재 조합 최저 OVR

    beam = [
        (
            (),
            names,
            0,
            0,
            0,
            0,
            0.0,
            0,
            0.0,
            0,
        )
    ]

    serial = count()

    def offer(heap, rank, state):
        item = (rank, next(serial), state)

        if len(heap) < 48:
            heappush(heap, item)
        elif rank > heap[0][0]:
            heapreplace(heap, item)

    for depth, options in enumerate(ordered):
        heaps = (
            [],
            [],
            [],
            [],
            [],
            [],
        )

        assigned_target = sum(
            ordered_targets[:depth + 1]
        )

        group_target = sum(
            ordered_targets[i]
            for i in range(depth + 1)
            if ordered_core[i]
        )

        for (
            selected,
            used,
            cost,
            salary,
            quality,
            high,
            error,
            core_cost,
            popularity,
            weakest_ovr,
        ) in beam:

            for p in options:
                name = (
                    str(p["player_name"])
                    .strip()
                    .casefold()
                )

                if name in used:
                    continue

                next_cost = cost + int(p["price"])
                next_salary = salary + int(p["salary"])
                next_high = (
                    high + int(p["grade"] >= 9)
                )

                if (
                    next_high > max_high
                    or next_cost
                    + min_price[depth + 1] > budget
                    or next_salary
                    + min_salary[depth + 1] > salary_cap
                ):
                    continue

                target = ordered_targets[depth]

                next_error = error + min(
                    3.0,
                    abs(p["price"] - target)
                    / max(
                        target,
                        budget / (n * 4),
                        1,
                    ),
                )

                next_quality = (
                    quality + int(p["ovr"])
                )

                player_ovr = int(
                    p["ovr"]
                )


                next_quality = (
                    quality
                    +
                    player_ovr
                )


                next_weakest_ovr = (
                    player_ovr

                    if depth == 0

                    else min(
                        weakest_ovr,
                        player_ovr,
                    )
                )

                next_popularity = (
                    popularity
                    +
                    float(
                        p.get(
                            "popularity_score",
                            0,
                        )
                        or 0
                    )
                )

                next_restricted_count = (
                    sum(
                        1
                        for selected_player
                        in selected
                        if bool(
                            selected_player.get(
                                "generation_restricted",
                                False,
                            )
                        )
                    )
                    +
                    int(
                        bool(
                            p.get(
                                "generation_restricted",
                                False,
                            )
                        )
                    )
                )

                next_core = core_cost + (
                    int(p["price"])
                    if ordered_core[depth]
                    else 0
                )

                state = (
                    selected + (p,),
                    used | {name},
                    next_cost,
                    next_salary,
                    next_quality,
                    next_high,
                    next_error,
                    next_core,
                    next_popularity,
                    next_weakest_ovr,
                )

                average_ovr = (
                    next_quality
                    /
                    (
                        depth
                        + 1
                    )
                )


                balance_gap = max(
                    0.0,

                    average_ovr
                    -
                    next_weakest_ovr,
                )

                # 품질, 예산 활용, 목표 근접도를
                # 모두 평가하는 점수.
                fit = (
                    average_ovr


                    # 실제 유저 선호도
                    +
                    META_POPULARITY_WEIGHT
                    *
                    (
                        next_popularity
                        /
                        (
                            depth
                            + 1
                        )
                    )

                    -
                    GENERATION_RESTRICTED_PENALTY
                    *
                    (
                        next_restricted_count
                        /
                        (
                            depth
                            + 1
                        )
                    )

                    -
                    META_BALANCE_GAP_WEIGHT
                    *
                    balance_gap

                    # 목표 예산 활용
                    +
                    8
                    *
                    min(
                        1.0,

                        next_cost
                        /
                        max(
                            assigned_target,
                            1,
                        ),
                    )


                    # 포지션별 목표 예산 편차
                    -
                    10
                    *
                    next_error
                    /
                    (
                        depth
                        + 1
                    )


                    # 코어 포지션 투자 비율
                    -
                    5
                    *
                    abs(
                        next_core
                        -
                        group_target
                    )
                    /
                    max(
                        assigned_target,
                        1,
                    )
                )

                offer(
                    heaps[0],
                    (
                        fit,
                        next_popularity,
                        next_quality,
                        next_cost,
                    ),
                    state,
                )

                offer(
                    heaps[1],
                    (
                        next_quality,
                        next_popularity,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

                offer(
                    heaps[2],
                    (
                        next_cost,
                        next_popularity,
                        next_quality,
                        -next_error,
                    ),
                    state,
                )

                offer(
                    heaps[3],
                    (
                        -next_cost,
                        next_popularity,
                        next_quality,
                        -next_error,
                    ),
                    state,
                )

                offer(
                    heaps[4],
                    (
                        next_weakest_ovr,
                        next_quality,
                        next_popularity,
                        -next_salary,
                        next_cost,
                    ),
                    state,
                )

                # 코어 투자 조합을 별도 보존한다.
                # 같은 코어 지출이면 급여가 낮은 조합을 우선해
                # 풀백/GK에 필요한 급여 여유를 남긴다.
                offer(
                    heaps[5],
                    (
                        next_core,
                        -next_salary,
                        next_quality,
                        next_popularity,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

        merged = {}

        for heap in heaps:
            for _, _, state in heap:
                key = tuple(
                    (p["sp_id"], p["grade"])
                    for p in state[0]
                )

                merged.setdefault(key, state)

        beam = list(merged.values())

        if not beam:
            return None

    # =========================================
    # 최종 조합 선택
    # =========================================

    balanced_mode = (
        plan.get("mode")
        == "balanced"
    )

    raw_core_target = (
        0
        if balanced_mode
        else int(
            plan.get("core_target")
            or 0
        )
    )

    raw_other_target = (
        0
        if balanced_mode
        else int(
            plan.get("other_target")
            or 0
        )
    )

    core_target = max(
        1,
        raw_core_target,
    )

    other_target = max(
        1,
        raw_other_target,
    )


    # -----------------------------------------
    # core 모드일 때만 코어 지출 하한 적용
    # -----------------------------------------

    if raw_core_target > 0:

        core_floor = int(
            raw_core_target
            * 0.70
        )

        eligible = [
            state
            for state in beam
            if state[7] >= core_floor
        ]


        if not eligible:

            core_floor = int(
                raw_core_target
                * 0.55
            )

            eligible = [
                state
                for state in beam
                if state[7] >= core_floor
            ]


    # balanced는 코어/비코어 구분 없이
    # 전체 beam을 그대로 최종 후보로 사용
    else:

        core_floor = 0
        eligible = list(beam)


    max_core_in_beam = max(
        state[7]
        for state in beam
    )


    # core 모드에서 목표 하한을 만족하는 조합이
    # 정말 하나도 없을 때만
    # 현재 beam의 최고 코어 지출 기준으로 fallback
    if not eligible:

        core_floor = int(
            max_core_in_beam
            * 0.90
        )

        eligible = [
            state
            for state in beam
            if state[7] >= core_floor
        ]


    print(
        "[QUICK SQUAD META]",

        "mode=",
        plan.get("mode"),

        "core_target=",
        raw_core_target,

        "core_floor=",
        core_floor,

        "max_core_in_beam=",
        max_core_in_beam,

        "other_target=",
        raw_other_target,

        "eligible=",
        len(eligible),

        flush=True,
    )


    def final_score(state):

        average_ovr = (
            state[4]
            / n
        )

        popularity_average = (
            state[8]
            / n
        )

        generation_restricted_count = sum(
            1
            for player
            in state[0]
            if bool(
                player.get(
                    "generation_restricted",
                    False,
                )
            )
        )

        supply_restricted_only_count = sum(
            1

            for player
            in state[0]

            if (
                bool(
                    player.get(
                        "supply_restricted",
                        False,
                    )
                )
                and
                not bool(
                    player.get(
                        "generation_restricted",
                        False,
                    )
                )
            )
        )

        weakest_ovr = state[9]


        balance_gap = max(
            0.0,
            average_ovr
            - weakest_ovr,
        )


        core_cost = state[7]

        other_cost = max(
            0,
            state[2]
            - core_cost,
        )


        core_ratio = (
            min(
                1.0,
                core_cost
                / core_target,
            )
            if raw_core_target > 0
            else 0.0
        )


        other_overspend = (
            max(
                0.0,
                (
                    other_cost
                    - raw_other_target
                )
                / other_target,
            )
            if raw_other_target > 0
            else 0.0
        )


        core_error = (
            abs(
                core_cost
                - raw_core_target
            )
            / core_target
            if raw_core_target > 0
            else 0.0
        )


        total_budget_ratio = min(
            1.0,
            state[2]
            / max(
                budget,
                1,
            ),
        )


        core_slot_underinvestment = 0.0
        core_slot_overinvestment = 0.0


        # balanced에서는 자리별 코어 투자 감점도 사용하지 않음
        if not balanced_mode:

            for i, player in enumerate(
                state[0]
            ):

                if not ordered_core[i]:
                    continue


                slot_target = max(
                    1,
                    ordered_targets[i],
                )


                spend_ratio = (
                    int(
                        player["price"]
                    )
                    / slot_target
                )


                # 목표의 20%보다 적게 쓰는 코어 자리
                if (
                    spend_ratio
                    <
                    CORE_SLOT_MIN_TARGET_RATIO
                ):

                    core_slot_underinvestment += (
                        (
                            CORE_SLOT_MIN_TARGET_RATIO
                            - spend_ratio
                        )
                        /
                        CORE_SLOT_MIN_TARGET_RATIO
                    )


                # 목표의 3배를 넘어가는 코어 몰빵
                if (
                    spend_ratio
                    >
                    CORE_SLOT_OVER_TARGET_RATIO
                ):

                    core_slot_overinvestment += min(
                        2.0,
                        (
                            spend_ratio
                            - CORE_SLOT_OVER_TARGET_RATIO
                        )
                        /
                        CORE_SLOT_OVER_TARGET_RATIO,
                    )

        # =========================================
        # 성능 추천
        #
        # 인기 데이터는 점수에 넣지 않는다.
        # 평균 OVR뿐 아니라 가장 약한 자리의
        # OVR을 강하게 보면서 전체 체급을 높인다.
        # =========================================

        if recommendation_mode == "performance":

            return (
                average_ovr

                +
                0.35
                *
                weakest_ovr

                -
                0.15
                *
                balance_gap

                +
                4.0
                *
                core_ratio

                -
                3.0
                *
                other_overspend

                -
                1.0
                *
                core_error

                -
                1.5
                *
                core_slot_underinvestment

                +
                0.5
                *
                total_budget_ratio

                -
                GENERATION_RESTRICTED_PENALTY
                *
                generation_restricted_count
            )


        # =========================================
        # 가성비 추천
        #
        # 무조건 싼 선수를 고르는 것이 아니다.
        #
        # 해당 슬롯 최고 OVR과 가까우면서
        # 목표 예산보다 저렴한 카드만
        # 높은 가성비 점수를 받는다.
        #
        # 현재 후보 단계의 OVR 품질 하한도
        # 그대로 적용되므로 저성능 카드가
        # 가격만 싸다는 이유로 올라오는 것을 막는다.
        # =========================================

        if recommendation_mode == "value":

            value_efficiency = 0.0


            for i, player in enumerate(
                state[0]
            ):

                slot_target = max(
                    1,
                    ordered_targets[i],
                )


                player_price = int(
                    player[
                        "price"
                    ]
                )


                player_ovr = int(
                    player[
                        "ovr"
                    ]
                )


                saving_ratio = max(
                    0.0,
                    1.0
                    -
                    min(
                        1.0,
                        player_price
                        /
                        slot_target,
                    ),
                )


                slot_best_ovr = max(
                    int(
                        option[
                            "ovr"
                        ]
                    )

                    for option
                    in ordered[i]
                )


                allowed_gap = (
                    10
                    if ordered_core[i]
                    else 16
                )


                quality_gap = max(
                    0,
                    slot_best_ovr
                    -
                    player_ovr,
                )


                quality_factor = max(
                    0.0,
                    1.0
                    -
                    (
                        quality_gap
                        /
                        max(
                            allowed_gap,
                            1,
                        )
                    ),
                )


                value_efficiency += (
                    saving_ratio
                    *
                    quality_factor
                )


            value_efficiency /= max(
                n,
                1,
            )


            return (
                average_ovr

                +
                12.0
                *
                value_efficiency

                -
                0.25
                *
                balance_gap

                +
                3.5
                *
                core_ratio

                -
                3.0
                *
                other_overspend

                -
                1.0
                *
                core_error

                -
                1.0
                *
                core_slot_underinvestment

                -
                GENERATION_RESTRICTED_PENALTY
                *
                generation_restricted_count
            )


        return (
            average_ovr

            + META_POPULARITY_WEIGHT
            * popularity_average

            - GENERATION_RESTRICTED_PENALTY
            * generation_restricted_count

            - META_BALANCE_GAP_WEIGHT
            * balance_gap

            + 7.0
            * core_ratio

            - 5.0
            * other_overspend

            - 2.0
            * core_error

            - CORE_SLOT_UNDERINVEST_WEIGHT
            * core_slot_underinvestment

            - CORE_SLOT_OVERINVEST_WEIGHT
            * core_slot_overinvestment

            + 1.5
            * total_budget_ratio
        )


    def final_rank(
        state,
    ):

        if recommendation_mode == "value":

            return (
                final_score(
                    state
                ),

                # 먼저 성능
                state[4],

                # 가장 약한 포지션
                state[9],

                # 동급이면 더 저렴한 조합
                -state[2],

                # 마지막 동점에서 인기도
                state[8],
            )


        if recommendation_mode == "performance":

            return (
                final_score(
                    state
                ),

                # 총 OVR
                state[4],

                # 가장 약한 자리
                state[9],

                # 동일 성능이면 적게 쓰는 쪽
                -state[2],

                state[8],
            )


        # =====================================
        # META
        # 기존 우선순위 유지
        # =====================================

        return (
            final_score(
                state
            ),

            state[4],
            state[8],
            state[9],
            state[2],
        )


    best = max(
        eligible,
        key=final_rank,
    )


    result = [None] * n

    for ordered_index, original_index in enumerate(order):
        result[original_index] = dict(
            best[0][ordered_index]
        )

    return result