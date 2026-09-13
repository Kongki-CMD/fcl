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

META_POPULARITY_WEIGHT = 10.0
META_BALANCE_GAP_WEIGHT = 0.35
GENERATION_RESTRICTED_PENALTY = 1.5
SUPPLY_RESTRICTED_PENALTY = 1.0
GENERATION_RESTRICTED_OVR_ADVANTAGE = 3
ICONTMB_DEPRIORITIZED_PENALTY = 2.0
MAX_SEASON_VARIANTS_PER_PLAYER = 2
CORE_SLOT_MIN_TARGET_RATIO_BASE = 0.35
CORE_SLOT_MIN_TARGET_RATIO_MAX = 0.55
CORE_SLOT_UNDERINVEST_WEIGHT = 4.0
BALANCED_CORE_SLOT_MIN_TARGET_RATIO = 0.30
CORE_CANDIDATE_MIN_RATIO_FACTOR = 0.0

CORE_SLOT_OVER_TARGET_RATIO = 3.0
CORE_SLOT_OVERINVEST_WEIGHT = 0.75

SIDE_POSITION_PAIRS = (
    ("LS", "RS"),
    ("LF", "RF"),
    ("LW", "RW"),
    ("LAM", "RAM"),
    ("LCM", "RCM"),
    ("LDM", "RDM"),
    ("LM", "RM"),
    ("LCB", "RCB"),
    ("LB", "RB"),
    ("LWB", "RWB"),
)

CORE_SIDE_PAIR_PRICE_WEIGHT = 1.25
CORE_SIDE_PAIR_OVR_WEIGHT = 0.35

OTHER_SIDE_PAIR_PRICE_WEIGHT = 0.50
OTHER_SIDE_PAIR_OVR_WEIGHT = 0.15

SIDE_PAIR_FREE_PRICE_RATIO = 1.60
SIDE_PAIR_FREE_OVR_GAP = 3

# =========================================
# VALUE MODE BALANCE
# =========================================

# 가성비라도 코어 자리는
# 해당 슬롯 최고 후보와 체급 차이를 크게 허용하지 않는다.
VALUE_CORE_MAX_OVR_GAP = 4

# 풀백 / 윙백 / GK는 코어보다 조금 더 절약 가능.
VALUE_OTHER_MAX_OVR_GAP = 7

# 전체 평균 OVR 대비 최저 OVR 차이.
#
# 먼저 8 이내 조합을 사용하고,
# 불가능한 팀컬러에서만 11까지 완화한다.
VALUE_STRICT_BALANCE_GAP = 8
VALUE_RELAXED_BALANCE_GAP = 11


def is_core(position):
    return (
        str(position).strip().upper()
        in CORE_POSITIONS
    )

def get_core_slot_min_target_ratio(
    plan,
):
    strength = int(
        plan.get(
            "core_strength",
            100,
        )
        or 100
    )


    strength = max(
        100,
        min(
            300,
            strength,
        ),
    )


    progress = (
        strength
        - 100
    ) / 200


    return (
        CORE_SLOT_MIN_TARGET_RATIO_BASE
        +
        (
            CORE_SLOT_MIN_TARGET_RATIO_MAX
            -
            CORE_SLOT_MIN_TARGET_RATIO_BASE
        )
        *
        progress
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

        "slots": [
            str(slot)
            .strip()
            .upper()
            for slot in slots
        ],

        "locked_slots": {
            int(player["slot_index"]): {
                "price": int(
                    player["price"]
                ),
                "ovr": int(
                    player.get(
                        "ovr",
                        0,
                    )
                    or 0
                ),
            }
            for player in locked
        },

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

def _is_icontmb(
    player,
):
    class_code = (
        str(
            player.get(
                "supply_restriction_class",
                "",
            )
            or ""
        )
        .strip()
        .upper()
    )

    return (
        class_code
        ==
        "ICONTMB"
    )

def _is_quick_squad_forbidden(
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
        or
        _is_icontmb(
            player
        )
    )


def _quick_squad_priority_rank(
    player,
):
    # 낮을수록 우선
    #
    # 0 일반
    # 1 공급 제한
    # 2 생성 제한
    # 3 ICONTMB
    #
    # ICONTMB는 제한 카드는 아니지만
    # 자동 추천에서는 최후순위로 둔다.

    if bool(
        player.get(
            "generation_restricted",
            False,
        )
    ):
        return 2


    if bool(
        player.get(
            "supply_restricted",
            False,
        )
    ):
        return 1


    if _is_icontmb(
        player
    ):
        return 3


    return 0

def _quick_squad_player_penalty(
    player,
):
    # 생성 제한이 가장 강한 감점
    if bool(
        player.get(
            "generation_restricted",
            False,
        )
    ):
        return (
            GENERATION_RESTRICTED_PENALTY
        )

    # 그다음 공급 제한
    if bool(
        player.get(
            "supply_restricted",
            False,
        )
    ):
        return (
            SUPPLY_RESTRICTED_PENALTY
        )

    # ICONTMB는 제한 카드는 아니지만
    # 에이전트 재료 가치를 고려해 일반 시즌보다 후순위
    if _is_icontmb(
        player
    ):
        return (
            ICONTMB_DEPRIORITIZED_PENALTY
        )

    return 0.0

def _quick_squad_player_name_key(
    player,
):
    return (
        str(
            player.get(
                "player_name",
                "",
            )
            or ""
        )
        .strip()
        .casefold()
    )


def _take_unique_player_names(
    players,
    limit,
):
    result = []
    seen_names = set()

    for player in players:

        name_key = (
            _quick_squad_player_name_key(
                player
            )
        )

        if (
            not name_key
            or name_key in seen_names
        ):
            continue

        result.append(
            player
        )

        seen_names.add(
            name_key
        )

        if (
            len(result)
            >= limit
        ):
            break

    return result


def _quick_squad_squad_priority(
    players,
):
    generation_count = 0
    supply_count = 0
    acquisition_restricted_count = 0
    icontmb_count = 0


    for player in players:

        generation_restricted = bool(
            player.get(
                "generation_restricted",
                False,
            )
        )


        supply_restricted = bool(
            player.get(
                "supply_restricted",
                False,
            )
        )


        acquisition_restricted = (
            generation_restricted
            or
            supply_restricted
        )


        if generation_restricted:
            generation_count += 1


        if supply_restricted:
            supply_count += 1


        if acquisition_restricted:
            acquisition_restricted_count += 1


        # 제한 카드가 아닌 ICONTMB만
        # 별도의 최후순위 카드로 계산.
        if (
            not acquisition_restricted
            and
            _is_icontmb(
                player
            )
        ):
            icontmb_count += 1


    # max()에서 큰 tuple이 우선.
    #
    # 최종 우선순위:
    #
    # 1. ICONTMB가 적은 스쿼드
    # 2. 공급/생성 제한 카드가 적은 스쿼드
    # 3. 생성 제한이 적은 스쿼드
    # 4. 공급 제한이 적은 스쿼드
    #
    # 따라서 일반 선수만으로 가능하면
    # 제한 카드나 ICONTMB는 절대 먼저 선택되지 않는다.
    return (
        -icontmb_count,
        -acquisition_restricted_count,
        -generation_count,
        -supply_count,
    )


def _prepare_options(
    options,
    target,
    budget,
    allow_high,
    core_slot,
    core_min_ratio=0.0,
    recommendation_mode="meta",
):
    values = [
        p
        for p in options
        if (
            0 < int(p["price"]) <= budget

            and int(p["salary"]) > 0

            and (
                allow_high
                or int(p["grade"]) < 9
            )

            and not _is_quick_squad_forbidden(
                p
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
    # 급여 한도 충족용 후보 보존
    #
    # OVR 필터에서 탈락하더라도
    # 정상 획득 가능한 저급여 선수 일부는
    # 반드시 탐색 후보에 남긴다.
    # =========================================

    feasibility_values = (
        _take_unique_player_names(
            sorted(
                values,
                key=lambda player: (
                    int(
                        player["salary"]
                    ),
                    -int(
                        player["ovr"]
                    ),
                    int(
                        player["price"]
                    ),
                ),
            ),
            8 if core_slot else 6,
        )
    )

    # =========================================
    # 코어 슬롯 최소 투자 후보 필터
    #
    # 최종 단계에서 싸구려 코어를 감점하는 게 아니라
    # 충분한 정상 후보가 존재한다면 애초에
    # 지나치게 싼 카드를 후보군에서 제외한다.
    #
    # 작은 팀컬러에서는 자동 완화한다.
    # =========================================

    if (
        core_slot
        and core_min_ratio > 0
    ):

        strict_price_floor = int(
            target
            *
            core_min_ratio
        )


        strict_values = [
            player

            for player
            in values

            if (
                int(player["price"])
                >=
                strict_price_floor
            )
        ]


        strict_unique_names = {
            _quick_squad_player_name_key(
                player
            )

            for player
            in strict_values
        }


        if (
            len(strict_unique_names)
            >= 3
        ):

            values = strict_values


        else:

            relaxed_price_floor = int(
                strict_price_floor
                *
                0.75
            )


            relaxed_values = [
                player

                for player
                in values

                if (
                    int(player["price"])
                    >=
                    relaxed_price_floor
                )
            ]


            relaxed_unique_names = {
                _quick_squad_player_name_key(
                    player
                )

                for player
                in relaxed_values
            }


            if (
                len(relaxed_unique_names)
                >= 2
            ):

                values = relaxed_values


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

    # OVR 경쟁력 후보와 별개로
    # 저급여 정상 선수 후보를 다시 합친다.
    for player in feasibility_values:

        selected.setdefault(
            (
                int(
                    player["sp_id"]
                ),
                int(
                    player["grade"]
                ),
            ),
            player,
        )

    # =========================================
    # 가성비 전용 후보
    #
    # 인기도와 관계없이 현재 슬롯의 좋은 카드보다
    # OVR이 크게 떨어지지 않으면서 저렴한 카드를
    # 별도로 beam까지 보존한다.
    #
    # 코어: 최고 OVR -6
    # 비코어: 최고 OVR -9
    # =========================================

    if recommendation_mode == "value":

        value_allowed_gap = (
            VALUE_CORE_MAX_OVR_GAP
            if core_slot
            else VALUE_OTHER_MAX_OVR_GAP
        )


        value_quality_floor = (
            best_slot_ovr
            -
            value_allowed_gap
        )


        value_candidates = [
            player

            for player
            in values

            if (
                int(player["ovr"])
                >=
                value_quality_floor
            )
        ]


        value_candidates = (
            _take_unique_player_names(
                sorted(
                    value_candidates,
                    key=lambda player: (
                        int(player["price"]),
                        int(player["salary"]),
                        -int(player["ovr"]),
                    ),
                ),
                (
                    14
                    if core_slot
                    else 12
                ),
            )
        )


        for player in value_candidates:

            selected.setdefault(
                (
                    int(player["sp_id"]),
                    int(player["grade"]),
                ),
                player,
            )


    values = list(
        selected.values()
    )


    # =========================================
    # 가성비 전용 저가 후보 그룹
    #
    # 코어 포지션도 성능 후보만 남지 않도록
    # 허용 OVR 범위 안의 저렴한 카드를
    # 별도 그룹으로 보존한다.
    # =========================================

    value_price_group = []


    if recommendation_mode == "value":

        value_price_group = (
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda player: (
                        int(
                            player["price"]
                        ),

                        -int(
                            player["ovr"]
                        ),

                        int(
                            player["salary"]
                        ),
                    ),
                ),
                (
                    14
                    if core_slot
                    else 10
                ),
            )
        )


    if core_slot:

        groups = (

            # ---------------------------------
            # 가성비 모드 전용 저가 후보
            # ---------------------------------
            value_price_group,

            # ---------------------------------
            # 인기 우선
            # 동일 선수는 한 시즌만
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),

                        -float(
                            p.get(
                                "popularity_score",
                                0,
                            )
                            or 0
                        ),

                        -p["ovr"],
                        p["price"],
                    ),
                ),
                10,
            ),

            # ---------------------------------
            # 성능 우선
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),
                        -p["ovr"],
                        p["price"],
                    ),
                ),
                10,
            ),

            # ---------------------------------
            # 저급여 fallback
            #
            # 공격/미드/CB를 코어로 유지하면서도
            # 급여 310 안에서 조합 자체가
            # 성립할 수 있도록 후보를 보존한다.
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        p["salary"],
                        _quick_squad_priority_rank(
                            p
                        ),
                        p["price"],
                        -p["ovr"],
                    ),
                ),
                8,
            ),


            # ---------------------------------
            # 목표 예산 근접
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),

                        abs(
                            p["price"]
                            - target
                        )
                        / target,

                        -p["ovr"],
                    ),
                ),
                10,
            ),

            # ---------------------------------
            # 고가 카드 보존
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),
                        -p["price"],
                        -p["ovr"],
                    ),
                ),
                6,
            ),
        )

    else:

        groups = (

            # ---------------------------------
            # 인기
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),

                        -float(
                            p.get(
                                "popularity_score",
                                0,
                            )
                            or 0
                        ),

                        -p["ovr"],
                        p["salary"],
                        p["price"],
                    ),
                ),
                8,
            ),

            # ---------------------------------
            # OVR
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),
                        -p["ovr"],
                        p["salary"],
                        p["price"],
                    ),
                ),
                8,
            ),

            # ---------------------------------
            # 저급여
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),
                        p["salary"],
                        -p["ovr"],
                        p["price"],
                    ),
                ),
                10,
            ),

            # ---------------------------------
            # 저가
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),
                        p["price"],
                        -p["ovr"],
                        p["salary"],
                    ),
                ),
                10,
            ),

            # ---------------------------------
            # 목표 예산 근접
            # ---------------------------------
            _take_unique_player_names(
                sorted(
                    values,
                    key=lambda p: (
                        _quick_squad_priority_rank(p),

                        abs(
                            p["price"]
                            - target
                        )
                        / target,

                        -p["ovr"],
                        p["salary"],
                    ),
                ),
                8,
            ),
        )

    chosen = {}

    chosen_name_counts = {}


    for group in groups:

        for player in group:

            card_key = (
                int(
                    player["sp_id"]
                ),
                int(
                    player["grade"]
                ),
            )


            if card_key in chosen:
                continue


            name_key = (
                _quick_squad_player_name_key(
                    player
                )
            )


            if (
                chosen_name_counts.get(
                    name_key,
                    0,
                )
                >=
                MAX_SEASON_VARIANTS_PER_PLAYER
            ):
                continue


            chosen[
                card_key
            ] = player


            chosen_name_counts[
                name_key
            ] = (
                chosen_name_counts.get(
                    name_key,
                    0,
                )
                + 1
            )


    return list(
        chosen.values()
    )[:48]


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

    final_core_min_ratio = (
        BALANCED_CORE_SLOT_MIN_TARGET_RATIO

        if (
            plan.get("mode")
            == "balanced"
        )

        else get_core_slot_min_target_ratio(
            plan
        )
    )


    candidate_core_min_ratio = (
        final_core_min_ratio
        *
        CORE_CANDIDATE_MIN_RATIO_FACTOR
    )

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
            candidate_core_min_ratio,
            recommendation_mode,
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

    ordered_slot_indices = [
        slot_indices[i]
        for i in order
    ]


    ordered_positions = [
        str(
            plan["slots"][
                slot_indices[i]
            ]
        )
        .strip()
        .upper()

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

    def side_pair_balance_penalty(
        players,
        positions,
    ):
        by_position = {}


        for position, player in zip(
            positions,
            players,
        ):
            by_position[
                str(position)
                .strip()
                .upper()
            ] = {
                "price": int(
                    player["price"]
                ),
                "ovr": int(
                    player["ovr"]
                ),
            }


        # 고정 선수도 좌우 균형 계산에 포함한다.
        for (
            locked_index,
            locked_player,
        ) in (
            plan.get(
                "locked_slots",
                {},
            )
            or {}
        ).items():

            locked_index = int(
                locked_index
            )


            if (
                locked_index
                < 0
                or locked_index
                >= len(
                    plan["slots"]
                )
            ):
                continue


            position = (
                str(
                    plan["slots"][
                        locked_index
                    ]
                )
                .strip()
                .upper()
            )


            by_position[
                position
            ] = {
                "price": int(
                    locked_player.get(
                        "price",
                        0,
                    )
                    or 0
                ),
                "ovr": int(
                    locked_player.get(
                        "ovr",
                        0,
                    )
                    or 0
                ),
            }


        penalty = 0.0


        for (
            left_position,
            right_position,
        ) in SIDE_POSITION_PAIRS:

            left = by_position.get(
                left_position
            )

            right = by_position.get(
                right_position
            )


            # 두 자리가 모두 존재할 때만 비교.
            if (
                left is None
                or right is None
            ):
                continue


            left_price = max(
                1,
                int(left["price"]),
            )

            right_price = max(
                1,
                int(right["price"]),
            )


            expensive_price = max(
                left_price,
                right_price,
            )

            cheap_price = min(
                left_price,
                right_price,
            )


            price_ratio = (
                expensive_price
                /
                cheap_price
            )


            price_gap = max(
                0.0,
                price_ratio
                -
                SIDE_PAIR_FREE_PRICE_RATIO,
            )


            # 극단적인 가격 차이가 점수를
            # 무한정 지배하지 않도록 상한 설정.
            price_gap = min(
                3.0,
                price_gap,
            )


            left_ovr = int(
                left["ovr"]
            )

            right_ovr = int(
                right["ovr"]
            )


            ovr_gap = max(
                0,
                abs(
                    left_ovr
                    -
                    right_ovr
                )
                -
                SIDE_PAIR_FREE_OVR_GAP,
            )


            ovr_gap = min(
                10,
                ovr_gap,
            )


            core_pair = (
                is_core(
                    left_position
                )
                and
                is_core(
                    right_position
                )
            )


            if core_pair:

                penalty += (
                    CORE_SIDE_PAIR_PRICE_WEIGHT
                    *
                    price_gap
                )

                penalty += (
                    CORE_SIDE_PAIR_OVR_WEIGHT
                    *
                    ovr_gap
                )

            else:

                penalty += (
                    OTHER_SIDE_PAIR_PRICE_WEIGHT
                    *
                    price_gap
                )

                penalty += (
                    OTHER_SIDE_PAIR_OVR_WEIGHT
                    *
                    ovr_gap
                )


        return penalty

    def side_pair_balance_is_valid(
        players,
        positions,
        *,
        price_ratio_limit,
        ovr_gap_limit,
    ):
        by_position = {}


        for position, player in zip(
            positions,
            players,
        ):
            by_position[
                str(position)
                .strip()
                .upper()
            ] = {
                "price": int(
                    player["price"]
                ),
                "ovr": int(
                    player["ovr"]
                ),
            }


        # 고정 선수도 pair 검증에 포함.
        for (
            locked_index,
            locked_player,
        ) in (
            plan.get(
                "locked_slots",
                {},
            )
            or {}
        ).items():

            locked_index = int(
                locked_index
            )


            if (
                locked_index < 0
                or locked_index >= len(
                    plan["slots"]
                )
            ):
                continue


            position = (
                str(
                    plan["slots"][
                        locked_index
                    ]
                )
                .strip()
                .upper()
            )


            by_position[
                position
            ] = {
                "price": max(
                    1,
                    int(
                        locked_player.get(
                            "price",
                            0,
                        )
                        or 0
                    ),
                ),
                "ovr": int(
                    locked_player.get(
                        "ovr",
                        0,
                    )
                    or 0
                ),
            }


        for (
            left_position,
            right_position,
        ) in SIDE_POSITION_PAIRS:

            left = by_position.get(
                left_position
            )

            right = by_position.get(
                right_position
            )


            if (
                left is None
                or right is None
            ):
                continue


            left_price = max(
                1,
                int(left["price"]),
            )

            right_price = max(
                1,
                int(right["price"]),
            )


            price_ratio = (
                max(
                    left_price,
                    right_price,
                )
                /
                min(
                    left_price,
                    right_price,
                )
            )


            ovr_gap = abs(
                int(left["ovr"])
                -
                int(right["ovr"])
            )


            if (
                price_ratio
                >
                price_ratio_limit
            ):
                return False


            if (
                ovr_gap
                >
                ovr_gap_limit
            ):
                return False


        return True

    def calculate_value_efficiency(
        players,
    ):
        if not players:
            return 0.0


        total_value = 0.0


        for i, player in enumerate(
            players
        ):

            slot_target = max(
                1,
                ordered_targets[i],
            )


            slot_best_ovr = max(
                int(option["ovr"])

                for option
                in ordered[i]
            )


            player_ovr = int(
                player["ovr"]
            )


            player_price = int(
                player["price"]
            )


            allowed_gap = (
                VALUE_CORE_MAX_OVR_GAP
                if ordered_core[i]
                else VALUE_OTHER_MAX_OVR_GAP
            )


            quality_gap = max(
                0,
                slot_best_ovr
                -
                player_ovr,
            )


            # 허용 OVR 범위 안에서는
            # 체급 손실을 완전히 0점 처리하지 않는다.
            #
            # 예:
            # 최고 OVR -2인데 가격이 절반이라면
            # 충분히 좋은 가성비 카드로 평가한다.
            quality_factor = max(
                0.35,
                1.0
                -
                (
                    quality_gap
                    /
                    max(
                        allowed_gap
                        + 2,
                        1,
                    )
                ),
            )


            # 목표 예산보다 저렴할수록 좋지만
            # 65% 이상 절약부터는 추가 보너스를 주지 않는다.
            #
            # 초저가 쓰레기 카드가 과도하게 유리해지는 것 방지.
            saving_ratio = max(
                0.0,
                1.0
                -
                (
                    player_price
                    /
                    slot_target
                ),
            )


            saving_score = (
                min(
                    0.65,
                    saving_ratio,
                )
                /
                0.65
            )


            player_value = (
                0.50
                *
                quality_factor

                +

                0.50
                *
                saving_score
            )


        return (
            total_value
            /
            len(players)
        )

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
                if _is_quick_squad_forbidden(
                    p
                ):
                    continue

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

                selected_generation_count = sum(
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


                selected_supply_count = sum(
                    1

                    for selected_player
                    in selected

                    if bool(
                        selected_player.get(
                            "supply_restricted",
                            False,
                        )
                    )
                )


                selected_acquisition_count = sum(
                    1

                    for selected_player
                    in selected

                    if _is_acquisition_restricted(
                        selected_player
                    )
                )


                player_generation_restricted = bool(
                    p.get(
                        "generation_restricted",
                        False,
                    )
                )


                player_supply_restricted = bool(
                    p.get(
                        "supply_restricted",
                        False,
                    )
                )


                player_acquisition_restricted = (
                    player_generation_restricted
                    or
                    player_supply_restricted
                )

                next_core = core_cost + (
                    int(p["price"])
                    if ordered_core[depth]
                    else 0
                )

                next_selected = (
                    selected
                    +
                    (p,)
                )


                next_side_pair_penalty = (
                    side_pair_balance_penalty(
                        next_selected,
                        ordered_positions[
                            :depth + 1
                        ],
                    )
                )

                next_other_salary = sum(
                    int(
                        selected_player[
                            "salary"
                        ]
                    )

                    for i, selected_player
                    in enumerate(
                        next_selected
                    )

                    if not ordered_core[i]
                )

                state = (
                    next_selected,
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
                popularity_average = (
                    next_popularity
                    /
                    (
                        depth
                        + 1
                    )
                )


                error_average = (
                    next_error
                    /
                    (
                        depth
                        + 1
                    )
                )


                budget_usage = min(
                    1.0,
                    next_cost
                    /
                    max(
                        assigned_target,
                        1,
                    ),
                )


                core_target_error = (
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


                # =====================================
                # 성능
                # =====================================

                if recommendation_mode == "performance":

                    fit = (
                        1.25
                        *
                        average_ovr

                        +
                        0.75
                        *
                        next_weakest_ovr

                        -
                        0.10
                        *
                        balance_gap

                        -
                        0.15
                        *
                        error_average

                        -
                        1.25
                        *
                        next_side_pair_penalty
                    )


                # =====================================
                # 가성비
                # =====================================

                elif recommendation_mode == "value":

                    partial_value_efficiency = (
                        calculate_value_efficiency(
                            next_selected
                        )
                    )


                    fit = (
                        0.25
                        *
                        average_ovr

                        +
                        0.20
                        *
                        next_weakest_ovr

                        +
                        34.0
                        *
                        partial_value_efficiency

                        -
                        0.40
                        *
                        balance_gap

                        -
                        0.35
                        *
                        error_average

                        -
                        1.50
                        *
                        next_side_pair_penalty
                    )


                # =====================================
                # 메타
                # =====================================

                else:

                    # =====================================
                    # META
                    #
                    # 1순위: 실제 유저 사용률
                    # 2순위: 선수 체급
                    #
                    # 인기도 데이터가 존재하는 선수라면
                    # OVR이 조금 낮더라도 메타 추천에서
                    # 적극적으로 살아남도록 한다.
                    # =====================================

                    fit = (
                        100.0
                        *
                        popularity_average

                        +
                        0.20
                        *
                        average_ovr

                        +
                        0.05
                        *
                        next_weakest_ovr

                        -
                        0.20
                        *
                        balance_gap

                        -
                        0.50
                        *
                        error_average

                        -
                        1.50
                        *
                        next_side_pair_penalty
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

                # 좌우 pair가 고르게 투자된 조합을
                # 별도 beam으로 보존한다.
                offer(
                    heaps[6],
                    (
                        -next_side_pair_penalty,
                        next_quality,
                        next_popularity,
                        next_core,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

                # 비코어인 풀백/윙백/GK의
                # 급여를 낮춘 조합을 별도로 보존한다.
                #
                # 코어 ST/CM/윙/CB 급여가 부족하면
                # 비코어 쪽에서 급여를 확보하기 위함.
                offer(
                    heaps[7],
                    (
                        -next_other_salary,
                        next_core,
                        next_quality,
                        next_popularity,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

                # 전체 급여가 낮은 경로도 별도로 보존.
                #
                # 후반부에 급여 310 때문에
                # 정상적인 조합 경로가 beam에서
                # 미리 사라지는 것을 막는다.
                offer(
                    heaps[8],
                    (
                        -next_salary,
                        next_quality,
                        next_core,
                        next_popularity,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

                # =====================================
                # 추천 모드 전용 beam
                # =====================================

                if recommendation_mode == "meta":

                    # 실제 사용률이 높은 조합을
                    # 별도 경로로 끝까지 보존한다.
                    offer(
                        heaps[9],
                        (
                            next_popularity,
                            next_quality,
                            next_weakest_ovr,
                            -next_salary,
                            -next_error,
                        ),
                        state,
                    )

                elif recommendation_mode == "performance":

                    # 성능 모드는 인기도와 무관하게
                    # 총 OVR / 최저 OVR이 높은 경로 보존.
                    offer(
                        heaps[9],
                        (
                            next_quality,
                            next_weakest_ovr,
                            -next_salary,
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

    core_slot_min_target_ratio = (
        BALANCED_CORE_SLOT_MIN_TARGET_RATIO

        if balanced_mode

        else get_core_slot_min_target_ratio(
            plan
        )
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

    # =========================================
    # 코어 개별 슬롯 투자 하한
    #
    # 총 코어 지출만 높은 조합이 아니라
    # 모든 코어 자리가 일정 수준 이상
    # 투자된 조합을 우선한다.
    #
    # 조건을 만족하는 조합이 전혀 없으면
    # 하한을 75%까지 완화하고,
    # 그래도 없으면 기존 eligible을 유지한다.
    # =========================================

    def minimum_core_slot_spend_ratio(
        state,
    ):
        ratios = [
            (
                int(
                    player[
                        "price"
                    ]
                )
                /
                max(
                    1,
                    ordered_targets[i],
                )
            )

            for i, player
            in enumerate(
                state[0]
            )

            if ordered_core[i]
        ]


        if not ratios:
            return 1.0


        return min(
            ratios
        )




    strict_core_slot_eligible = [
        state

        for state
        in eligible

        if (
            minimum_core_slot_spend_ratio(
                state
            )
            >=
            core_slot_min_target_ratio
        )
    ]


    if strict_core_slot_eligible:

        eligible = (
            strict_core_slot_eligible
        )


    else:

        relaxed_core_slot_ratio = (
            core_slot_min_target_ratio
            * 0.75
        )


        relaxed_core_slot_eligible = [
            state

            for state
            in eligible

            if (
                minimum_core_slot_spend_ratio(
                    state
                )
                >=
                relaxed_core_slot_ratio
            )
        ]


        if relaxed_core_slot_eligible:

            eligible = (
                relaxed_core_slot_eligible
            )


        else:

            # strict/relaxed 기준을 만족하는 조합이
            # 하나도 없더라도 기존 후보 전체로
            # 되돌아가지는 않는다.
            #
            # 현재 beam에서 가능한 최선의
            # "가장 약한 코어 투자비율"을 구하고,
            # 그 값의 90% 이상인 조합만 남긴다.
            best_core_slot_ratio = max(
                minimum_core_slot_spend_ratio(
                    state
                )
                for state
                in eligible
            )


            fallback_core_slot_ratio = (
                best_core_slot_ratio
                * 0.90
            )


            eligible = [
                state

                for state
                in eligible

                if (
                    minimum_core_slot_spend_ratio(
                        state
                    )
                    >=
                    fallback_core_slot_ratio
                )
            ]

    # =========================================
    # 최종 좌우 pair hard gate
    #
    # soft penalty만으로는 급여 압박 상황에서
    # 한쪽 코어를 완전히 버리는 조합이 살아날 수 있다.
    #
    # 1차:
    #   가격 2.5배 이내
    #   OVR 5 이내
    #
    # 2차 fallback:
    #   가격 4배 이내
    #   OVR 7 이내
    #
    # 이것도 불가능할 때만 기존 후보 중
    # pair penalty가 가장 작은 조합군을 사용한다.
    # =========================================

    strict_pair_eligible = [
        state

        for state
        in eligible

        if side_pair_balance_is_valid(
            state[0],
            ordered_positions,
            price_ratio_limit=2.5,
            ovr_gap_limit=5,
        )
    ]


    if strict_pair_eligible:

        eligible = (
            strict_pair_eligible
        )


    else:

        relaxed_pair_eligible = [
            state

            for state
            in eligible

            if side_pair_balance_is_valid(
                state[0],
                ordered_positions,
                price_ratio_limit=4.0,
                ovr_gap_limit=7,
            )
        ]


        if relaxed_pair_eligible:

            eligible = (
                relaxed_pair_eligible
            )


        else:

            best_pair_penalty = min(
                side_pair_balance_penalty(
                    state[0],
                    ordered_positions,
                )
                for state
                in eligible
            )


            eligible = [
                state

                for state
                in eligible

                if (
                    side_pair_balance_penalty(
                        state[0],
                        ordered_positions,
                    )
                    <=
                    best_pair_penalty
                    + 0.50
                )
            ]

    # =========================================
    # 가성비 전체 체급 균형
    #
    # 싼 선수 한 명을 지나치게 낮춰
    # 전체 가성비 점수를 만드는 조합 방지.
    #
    # 평균 OVR - 최저 OVR
    #
    # 1차: 8 이내
    # 2차: 11 이내
    #
    # 작은 팀컬러에서 두 조건 모두 불가능하면
    # 기존 eligible을 유지해서 추천 실패는 막는다.
    # =========================================

    if recommendation_mode == "value":

        strict_value_balance = [
            state

            for state
            in eligible

            if (
                (
                    state[4]
                    / n
                )
                -
                state[9]
                <=
                VALUE_STRICT_BALANCE_GAP
            )
        ]


        if strict_value_balance:

            eligible = (
                strict_value_balance
            )

        else:

            relaxed_value_balance = [
                state

                for state
                in eligible

                if (
                    (
                        state[4]
                        / n
                    )
                    -
                    state[9]
                    <=
                    VALUE_RELAXED_BALANCE_GAP
                )
            ]


            if relaxed_value_balance:

                eligible = (
                    relaxed_value_balance
                )


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

        deprioritized_penalty = sum(
            _quick_squad_player_penalty(
                player
            )
            for player
            in state[0]
        )

        weakest_ovr = state[9]

        side_pair_penalty = (
            side_pair_balance_penalty(
                state[0],
                ordered_positions,
            )
        )


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


            if (
                spend_ratio
                <
                core_slot_min_target_ratio
            ):

                core_slot_underinvestment += (
                    (
                        core_slot_min_target_ratio
                        - spend_ratio
                    )
                    /
                    core_slot_min_target_ratio
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
                2.0
                *
                side_pair_penalty

-
                deprioritized_penalty
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

            value_efficiency = (
                calculate_value_efficiency(
                    state[0]
                )
            )


            return (
                0.30
                *
                average_ovr

                +

                0.22
                *
                weakest_ovr

                +

                34.0
                *
                value_efficiency

                -
                0.20
                *
                balance_gap

                +
                2.0
                *
                core_ratio

                -
                2.0
                *
                other_overspend

                -
                0.75
                *
                core_error

                -
                1.0
                *
                core_slot_underinvestment

                -
                1.50
                *
                side_pair_penalty
            )


        return (
            average_ovr

            + META_POPULARITY_WEIGHT
            * popularity_average

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

            - 2.25
            * side_pair_penalty
        )


    def final_rank(
        state,
    ):

        squad_priority = (
            _quick_squad_squad_priority(
                state[0]
            )
        )

        if recommendation_mode == "value":

            return (
                squad_priority,

                final_score(
                    state
                ),

                # 가성비가 같다면 더 저렴한 팀
                -state[2],

                # 그다음 가장 약한 자리
                state[9],

                # 그다음 전체 성능
                state[4],

                # 인기도는 최후
                state[8],
            )

        if recommendation_mode == "performance":

            return (
                squad_priority,

                # 1순위: 11명 총 OVR
                state[4],

                # 2순위: 최약 포지션 OVR
                state[9],

                # 3순위: 성능 내부 종합 점수
                final_score(
                    state
                ),

                # 같은 성능이라면 적게 쓰는 쪽
                -state[2],
            )


        # =====================================
        # META
        #
        # 실제 유저 사용률이 가장 중요하다.
        #
        # popularity_score 합계가 높은 조합을
        # 먼저 선택하고, 그다음 성능을 본다.
        # =====================================

        return (
            squad_priority,

            # 1순위: 실제 사용 인기
            round(
                state[8],
                6,
            ),

            # 2순위: 메타 내부 종합 점수
            final_score(
                state
            ),

            # 3순위: 총 OVR
            state[4],

            # 4순위: 가장 약한 포지션 OVR
            state[9],

            # 마지막: 사용 예산
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