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


def _prepare_options(
    options,
    target,
    budget,
    allow_high,
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

    target = max(1, target)

    # 비싼 카드만 남기지 않고 품질·목표·가성비·급여
    # 후보를 섞어 포지션당 최대 40개까지 유지한다.
    groups = (
        sorted(
            values,
            key=lambda p: (
                -p["ovr"],
                p["price"],
            ),
        )[:8],

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
                p["price"],
                -p["ovr"],
            ),
        )[:8],

        sorted(
            values,
            key=lambda p: (
                -p["price"],
                -p["ovr"],
            ),
        )[:6],

        sorted(
            values,
            key=lambda p: (
                p["salary"],
                -p["ovr"],
            ),
        )[:6],

        sorted(
            values,
            key=lambda p: (
                -p["ovr"]
                / max(p["price"], 1) ** 0.12,
                p["price"],
            ),
        )[:6],
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
):
    """
    목표 예산과 OVR을 함께 평가한다.
    한 단계에서 최대 128개 상태만 유지한다.
    """

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
        )
        for options, target in zip(
            options_by_slot,
            targets,
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

    # state:
    # 선수, 이름, 비용, 급여, OVR, 고강화 수,
    # 목표 편차, 코어 지출
    beam = [
        ((), names, 0, 0, 0, 0, 0.0, 0)
    ]

    serial = count()

    def offer(heap, rank, state):
        item = (rank, next(serial), state)

        if len(heap) < 32:
            heappush(heap, item)
        elif rank > heap[0][0]:
            heapreplace(heap, item)

    for depth, options in enumerate(ordered):
        heaps = ([], [], [], [])

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
                )

                # 품질, 예산 활용, 목표 근접도를
                # 모두 평가하는 점수.
                fit = (
                    next_quality / (depth + 1)
                    + 8 * min(
                        1.0,
                        next_cost
                        / max(assigned_target, 1),
                    )
                    - 10 * next_error / (depth + 1)
                    - 5 * abs(next_core - group_target)
                    / max(assigned_target, 1)
                )

                offer(
                    heaps[0],
                    (fit, next_quality, next_cost),
                    state,
                )

                offer(
                    heaps[1],
                    (
                        next_quality,
                        -next_error,
                        next_cost,
                    ),
                    state,
                )

                offer(
                    heaps[2],
                    (
                        next_cost,
                        next_quality,
                        -next_error,
                    ),
                    state,
                )

                offer(
                    heaps[3],
                    (
                        -next_cost,
                        next_quality,
                        -next_error,
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

    best = max(
        beam,
        key=lambda s: (
            s[4] / n
            + 8 * s[2] / budget
            - 10 * s[6] / n
            - 5 * abs(
                s[7] - plan["core_target"]
            ) / max(budget, 1),
            s[4],
            s[2],
        ),
    )

    result = [None] * n

    for ordered_index, original_index in enumerate(order):
        result[original_index] = dict(
            best[0][ordered_index]
        )

    return result