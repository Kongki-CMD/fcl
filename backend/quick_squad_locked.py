"""고정 선수 기반 퀵 스쿼드 추천."""

from concurrent.futures import (
    ThreadPoolExecutor,
    wait,
    FIRST_COMPLETED,
)
from heapq import heappush, heapreplace
from itertools import count
from threading import BoundedSemaphore
from time import monotonic

from fastapi import HTTPException
from pydantic import BaseModel, Field
from backend.quick_squad_budget import (
    make_budget_plan,
    search_budget_squad,
    summarize_budget_plan,
)

from backend.player_supply_restriction import (
    get_supply_restriction_status_by_season_id,
)


LOCKED_RECOMMENDATION_GATE = BoundedSemaphore(1)

QUICK_SQUAD_POPULARITY_POSITION_MAP = {

    # 공격
    "LS": "ST",
    "RS": "ST",

    "LF": "CF",
    "RF": "CF",

    # 공격형 미드필더
    "LAM": "CAM",
    "RAM": "CAM",

    # 중앙 미드필더
    "LCM": "CM",
    "RCM": "CM",

    # 수비형 미드필더
    "LDM": "CDM",
    "RDM": "CDM",

    # 센터백
    "LCB": "CB",
    "RCB": "CB",
    "SW": "CB",
}


class LockedPlayerInput(BaseModel):
    sp_id: int = Field(gt=0, strict=True)
    grade: int = Field(ge=1, le=13, strict=True)
    slot_index: int | None = Field(
        default=None,
        ge=0,
        le=10,
        strict=True,
    )


class LockedPreviewRequest(BaseModel):
    team_color_id: int | None = Field(default=None, gt=0)
    locked_players: list[LockedPlayerInput] = Field(
        default_factory=list,
        max_length=11,
    )


class LockedSquadService:
    def __init__(
        self,
        *,
        db,
        prices,
        candidates,
        positions,
        bonus,
        team_name,
        valid_prices,
        cap=310,
        budget_candidates=None,
    ):
        self.db = db
        self.prices = prices
        self.candidates = candidates
        self.budget_candidates = budget_candidates
        self.positions = positions
        self.bonus = bonus
        self.team_name = team_name
        self.valid_prices = valid_prices
        self.cap = cap
        self.db = db
        self.prices = prices
        self.candidates = candidates
        self.positions = positions
        self.bonus = bonus
        self.team_name = team_name
        self.valid_prices = valid_prices
        self.cap = cap

    @staticmethod
    def name_key(value):
        return str(value).strip().casefold()

    @staticmethod
    def apply_slot_popularity(
        player,
        slot_index,
        slot_position,
    ):

        result = dict(
            player
        )


        normalized_slot = (
            str(
                slot_position
            )
            .strip()
            .upper()
        )


        popularity_position = (
            QUICK_SQUAD_POPULARITY_POSITION_MAP
            .get(
                normalized_slot,
                normalized_slot,
            )
        )


        popularity_by_position = (
            result.pop(
                "popularity_by_position",
                {},
            )
            or {}
        )


        popularity = (
            popularity_by_position.get(
                popularity_position
            )
        )


        result[
            "slot_index"
        ] = slot_index

        result[
            "slot_position"
        ] = normalized_slot


        if popularity is None:

            result[
                "usage_count"
            ] = 0

            result[
                "usage_rate"
            ] = 0.0

            result[
                "popularity_score"
            ] = 0.0

            result[
                "popularity_position"
            ] = popularity_position

            result[
                "popularity_snapshot_date"
            ] = None


        else:

            result[
                "usage_count"
            ] = int(
                popularity.get(
                    "usage_count"
                )
                or 0
            )

            result[
                "usage_rate"
            ] = float(
                popularity.get(
                    "usage_rate"
                )
                or 0
            )

            result[
                "popularity_score"
            ] = float(
                popularity.get(
                    "popularity_score"
                )
                or 0
            )

            result[
                "popularity_position"
            ] = popularity_position

            result[
                "popularity_snapshot_date"
            ] = popularity.get(
                "snapshot_date"
            )


        return result


    def resolve(
        self,
        entries,
        *,
        team_color_id=None,
        slots=None,
        strict_team=False,
        require_slots=False,
    ):
        if len(entries) > 11:
            raise HTTPException(
                422,
                "고정 선수는 최대 11명입니다.",
            )

        ids = [int(e.sp_id) for e in entries]

        if len(ids) != len(set(ids)):
            raise HTTPException(
                422,
                "동일한 선수 카드가 중복 등록되었습니다.",
            )

        if not ids:
            return []

        # 클라이언트가 보낸 가격·급여·이름은 신뢰하지 않는다.
        with self.db() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        p.sp_id,
                        p.player_name,
                        p.season_id,
                        p.image_url,
                        p.position,
                        p.salary,
                        p.ovr,
                        COALESCE(
                            gs.generation_restricted,
                            FALSE
                        ) AS generation_restricted,

                        gs.source_type
                            AS generation_status_source,

                        gs.source_note
                            AS generation_status_note,

                        gs.effective_date
                            AS generation_status_effective_date,

                        CASE
                            WHEN %s::integer IS NULL
                            THEN TRUE
                            ELSE EXISTS (
                                SELECT 1
                                FROM fconline_player_teams t
                                WHERE t.sp_id = p.sp_id
                                AND t.team_color_id = %s
                            )
                        END AS team_color_match
                    FROM fconline_players p

                    LEFT JOIN
                        fconline_player_generation_status gs
                        ON gs.sp_id = p.sp_id

                    WHERE p.sp_id = ANY(%s)
                    """,
                    (team_color_id, team_color_id, ids),
                )

                rows = {
                    int(row["sp_id"]): row
                    for row in cursor.fetchall()
                }

        for row in rows.values():

            row.update(
                get_supply_restriction_status_by_season_id(
                    row.get(
                        "season_id"
                    )
                )
            )

        result = []
        names = set()
        occupied = set()

        for entry in entries:
            row = rows.get(entry.sp_id)

            if row is None:
                raise HTTPException(
                    422,
                    f"선수 카드 {entry.sp_id}를 DB에서 찾을 수 없습니다.",
                )

            name = self.name_key(row["player_name"])

            if name in names:
                raise HTTPException(
                    422,
                    f"{row['player_name']}: 같은 선수의 "
                    "다른 시즌이 이미 등록되어 있습니다.",
                )

            names.add(name)

            if strict_team and not row["team_color_match"]:
                raise HTTPException(
                    422,
                    f"{row['player_name']}: 선택한 팀컬러에 속하지 않습니다.",
                )

            index = entry.slot_index

            if require_slots and index is None:
                raise HTTPException(
                    422,
                    f"{row['player_name']}: 포지션을 지정해주세요.",
                )

            if index is not None:
                if slots is None or index >= len(slots):
                    if require_slots:
                        raise HTTPException(
                            422,
                            "고정 선수의 포지션 번호가 올바르지 않습니다.",
                        )
                else:
                    if index in occupied:
                        raise HTTPException(
                            422,
                            "한 포지션에 두 명을 고정할 수 없습니다.",
                        )

                    occupied.add(index)

                    accepted = self.positions.get(
                        slots[index],
                        [slots[index]],
                    )

                    if row["position"] not in accepted:
                        raise HTTPException(
                            422,
                            f"{row['player_name']}: "
                            f"{slots[index]} 포지션에 배치할 수 없습니다.",
                        )

            try:
                market_prices = self.prices(entry.sp_id)
            except HTTPException:
                raise
            except Exception as error:
                raise HTTPException(
                    502,
                    "고정 선수의 시세를 조회하지 못했습니다.",
                ) from error

            price = next(
                (
                    item.get("price")
                    for item in market_prices or []
                    if int(item.get("grade", 0)) == entry.grade
                ),
                None,
            )

            if price is None or int(price) <= 0:
                raise HTTPException(
                    422,
                    f"{row['player_name']} +{entry.grade}: "
                    "시세 정보가 없습니다.",
                )

            result.append({
                "sp_id": entry.sp_id,
                "player_name": row["player_name"],
                "season_id": int(row["season_id"]),
                "image_url": row["image_url"] or "",
                "position": row["position"] or "",
                "salary": int(row["salary"] or 0),
                "base_ovr": int(row["ovr"] or 0),
                "grade": entry.grade,
                "ovr": (
                    int(row["ovr"] or 0)
                    + self.bonus[entry.grade]
                ),
                "price": int(price),
                "popularity_by_position":
                    row.get(
                        "popularity_by_position"
                    )
                    or {},
                "generation_restricted":
                    bool(
                        row.get(
                            "generation_restricted",
                            False,
                        )
                    ),

                "generation_status_source":
                    row.get(
                        "generation_status_source"
                    ),

                "generation_status_note":
                    row.get(
                        "generation_status_note"
                    ),

                "supply_restricted":
                    bool(
                        row.get(
                            "supply_restricted",
                            False,
                        )
                    ),

                "supply_restriction_class":
                    row.get(
                        "supply_restriction_class"
                    ),

                "supply_restriction_source":
                    row.get(
                        "supply_restriction_source"
                    ),

                "supply_restriction_notice_sn":
                    row.get(
                        "supply_restriction_notice_sn"
                    ),

                "supply_restriction_effective_date":
                    row.get(
                        "supply_restriction_effective_date"
                    ),

                "supply_restriction_note":
                    row.get(
                        "supply_restriction_note"
                    ),

                "generation_status_effective_date":
                    row.get(
                        "generation_status_effective_date"
                    ),
                "slot_index": index,
                "slot_position": (
                    slots[index]
                    if slots is not None
                    and index is not None
                    and index < len(slots)
                    else None
                ),
                "team_color_match": bool(
                    row["team_color_match"]
                ),
                "locked": True,
                "allowed_positions": [
                    slot
                    for slot, accepted in self.positions.items()
                    if row["position"] in accepted
                ],
            })

        return result

    @staticmethod
    def _select_options(options, budget):
        values = [
            p for p in options
            if 0 < p["price"] <= budget
        ]

        groups = (
            sorted(
                values,
                key=lambda p: (-p["ovr"], p["price"]),
            )[:10],
            sorted(
                values,
                key=lambda p: (p["price"], -p["ovr"]),
            )[:8],
            sorted(
                values,
                key=lambda p: (-p["price"], -p["ovr"]),
            )[:8],
            sorted(
                values,
                key=lambda p: (
                    p["salary"],
                    -p["ovr"],
                ),
            )[:8],
        )

        chosen = {}

        for group in groups:
            for player in group:
                chosen[
                    (player["sp_id"], player["grade"])
                ] = player

        return list(chosen.values())[:34]

    def _solve(
        self,
        options_by_slot,
        budget,
        salary_cap,
        excluded_names,
        max_high,
    ):
        if not options_by_slot:
            return []

        prepared = [
            self._select_options(options, budget)
            for options in options_by_slot
        ]

        if any(not options for options in prepared):
            return None

        order = sorted(
            range(len(prepared)),
            key=lambda i: len(prepared[i]),
        )

        ordered = [prepared[i] for i in order]
        n = len(ordered)

        minimum_cost = [0] * (n + 1)
        minimum_salary = [0] * (n + 1)

        for i in range(n - 1, -1, -1):
            minimum_cost[i] = (
                minimum_cost[i + 1]
                + min(p["price"] for p in ordered[i])
            )
            minimum_salary[i] = (
                minimum_salary[i + 1]
                + min(p["salary"] for p in ordered[i])
            )

        if (
            minimum_cost[0] > budget
            or minimum_salary[0] > salary_cap
        ):
            return None

        # 모든 조합을 저장하지 않고 각 단계 상위 상태만 유지.
        beam = [(
            (),
            frozenset(excluded_names),
            0,
            0,
            0,
            0,
        )]

        serial = count()

        def offer(heap, rank, state):
            item = (rank, next(serial), state)

            if len(heap) < 32:
                heappush(heap, item)
            elif rank > heap[0][0]:
                heapreplace(heap, item)

        for depth, options in enumerate(ordered):
            heaps = ([], [], [])

            for (
                selected,
                names,
                cost,
                salary,
                quality,
                high,
            ) in beam:
                for player in options:
                    key = self.name_key(player["player_name"])

                    if key in names:
                        continue

                    next_cost = cost + player["price"]
                    next_salary = salary + player["salary"]
                    next_high = (
                        high + int(player["grade"] >= 9)
                    )

                    if (
                        next_high > max_high
                        or next_cost
                        + minimum_cost[depth + 1] > budget
                        or next_salary
                        + minimum_salary[depth + 1] > salary_cap
                    ):
                        continue

                    next_quality = (
                        quality + player["ovr"]
                    )

                    state = (
                        selected + (player,),
                        names | {key},
                        next_cost,
                        next_salary,
                        next_quality,
                        next_high,
                    )

                    offer(
                        heaps[0],
                        (
                            next_quality,
                            -next_cost,
                            -next_salary,
                        ),
                        state,
                    )

                    offer(
                        heaps[1],
                        (
                            next_cost,
                            next_quality,
                            -next_salary,
                        ),
                        state,
                    )

                    offer(
                        heaps[2],
                        (
                            -next_cost,
                            -next_salary,
                            next_quality,
                        ),
                        state,
                    )

            merged = {}

            for heap in heaps:
                for _, _, state in heap:
                    key = (
                        state[1],
                        state[2],
                        state[3],
                        state[5],
                    )

                    if (
                        key not in merged
                        or state[4] > merged[key][4]
                    ):
                        merged[key] = state

            beam = list(merged.values())

            if not beam:
                return None

        best_quality = max(state[4] for state in beam)

        eligible = [
            state for state in beam
            if state[4] >= best_quality - n
        ]

        best = max(
            eligible,
            key=lambda state: (
                state[2],
                state[4],
                -state[3],
            ),
        )

        result = [None] * n

        for i, original_index in enumerate(order):
            result[original_index] = dict(
                best[0][i]
            )

        return result

    def _summary(
        self,
        team_color_id,
        budget,
        formation,
        slots,
        grade,
        players,
        locked_count,
        allocation_plan=None,
        recommendation_mode="meta",
    ):
        total = sum(p["price"] for p in players)
        salary = sum(p["salary"] for p in players)

        if (
            len(players) != 11
            or len({
                p["slot_index"] for p in players
            }) != 11
            or len({
                self.name_key(p["player_name"])
                for p in players
            }) != 11
            or total > budget
            or salary > self.cap
            or any(
                p["grade"] != grade
                for p in players
                if not p["locked"] and grade is not None
            )
        ):
            raise HTTPException(
                500,
                "스쿼드 최종 검증에 실패했습니다.",
            )

        players = sorted(
            players,
            key=lambda p: p["slot_index"],
        )

        result = {
            "recommendation_mode":
                recommendation_mode,
            "team_color_id": team_color_id,
            "team_name": self.team_name(team_color_id),
            "formation": formation,
            "budget_bp": budget,
            "enhancement_grade": grade,
            "total_price": total,
            "remaining_budget": budget - total,
            "total_salary": salary,
            "salary_cap": self.cap,
            "locked_count": locked_count,
            "locked_total_price": sum(
                p["price"] for p in players if p["locked"]
            ),
            "locked_total_salary": sum(
                p["salary"] for p in players if p["locked"]
            ),
            "players": players,
            "source": {
                "player": "FCL Player Database",
                "price": "FC Online DataCenter",
            },
        }

        if allocation_plan is not None:
            result["budget_allocation"] = (
                summarize_budget_plan(
                    allocation_plan,
                    players,
                )
            )

        return result

    def recommend(self, request):
        # Render 소형 인스턴스에서 새 고정 추천의 동시 실행 제한.
        if not LOCKED_RECOMMENDATION_GATE.acquire(
            blocking=False
        ):
            raise HTTPException(
                429,
                "다른 스쿼드 추천이 진행 중입니다. "
                "잠시 후 다시 시도해주세요.",
            )

        try:
            return self._recommend(request)
        finally:
            LOCKED_RECOMMENDATION_GATE.release()

    def _recommend(self, request):
        slots = [
            str(s).strip().upper()
            for s in request.slots
        ]

        budget = request.budget_bp

        if (
            len(slots) != 11
            or slots.count("GK") != 1
            or budget <= 0
            or request.team_color_id <= 0
        ):
            raise HTTPException(
                422,
                "팀컬러, 예산 또는 포메이션을 확인해주세요.",
            )

        fixed = self.resolve(
            request.locked_players,
            team_color_id=request.team_color_id,
            slots=slots,
            strict_team=True,
            require_slots=True,
        )

        cost = sum(p["price"] for p in fixed)
        salary = sum(p["salary"] for p in fixed)

        if cost > budget or salary > self.cap:
            raise HTTPException(
                422,
                "고정 선수만으로 구단가치 또는 급여 제한을 초과합니다.",
            )

        occupied = {
            p["slot_index"] for p in fixed
        }

        remaining = [
            (i, slot)
            for i, slot in enumerate(slots)
            if i not in occupied
        ]

        allocation_plan = None

        budget_mode = getattr(
            request,
            "budget_mode",
            "legacy",
        )

        if budget_mode != "legacy":
            allocation_plan = make_budget_plan(
                slots,
                budget,
                fixed,
                mode=budget_mode,
                strength=getattr(
                    request,
                    "core_strength",
                    200,
                ),
            )

        # 11명 전부 고정된 경우 외부 후보 조회 없이 반환.
        if not remaining:
            return self._summary(
                request.team_color_id,
                budget,
                request.formation,
                slots,
                request.enhancement_grade,
                fixed,
                len(fixed),
                allocation_plan,
                getattr(
                    request,
                    "recommendation_mode",
                    "meta",
                ),
            )

        remaining_budget = budget - cost
        remaining_salary = self.cap - salary

        cache = {}
        failed = False

        started_at = monotonic()
        deadline = started_at + 60

        best = None

        # 후보와 외부 시세 요청 수를 제한한다.
        # 1차: 적은 후보로 빠르게 구성.
        # 2차: 필요한 경우에만 후보 범위를 확대.
        for per_salary, limit in (
            (2, 48),
            (4, 96),
        ):
            candidate_source = (
                self.budget_candidates
                or self.candidates
            )

            rows = candidate_source(
                request.team_color_id,
                [s for _, s in remaining],
                per_salary_limit=per_salary,
                total_limit=limit,
            )

            print(
                "[QUICK SQUAD] CANDIDATES",
                "limit=", limit,
                "rows=", len(rows),
                "elapsed=", round(
                    monotonic() - started_at,
                    2,
                ),
                flush=True,
            )

            unique = {
                int(row["sp_id"]): row
                for row in rows
            }

            pending = [
                spid for spid in unique
                if spid not in cache
            ]

            if pending and monotonic() < deadline:
                executor = ThreadPoolExecutor(
                    max_workers=4
                )

                futures = {
                    executor.submit(self.prices, spid): spid
                    for spid in pending
                }

                try:
                    while (
                        futures
                        and monotonic() < deadline
                    ):
                        done, _ = wait(
                            futures,
                            timeout=max(
                                0,
                                deadline - monotonic(),
                            ),
                            return_when=FIRST_COMPLETED,
                        )

                        if not done:
                            break

                        for future in done:
                            spid = futures.pop(future)

                            try:
                                cache[spid] = future.result()

                            except Exception as error:
                                cache[spid] = None
                                failed = True

                                print(
                                    "[QUICK SQUAD LOCKED] PRICE FAILED",
                                    "spid=", spid,
                                    "type=", type(error).__name__,
                                    "error=", str(error),
                                    "cause=", repr(error.__cause__),
                                    flush=True,
                                )

                finally:
                    for future in futures:
                        future.cancel()

                    executor.shutdown(
                        wait=True,
                        cancel_futures=True,
                    )

            options = []

            for spid, row in unique.items():
                market = cache.get(spid)

                if not market:
                    continue

                if (
                    request.enhancement_grade is None
                    and not self.valid_prices(market)
                ):
                    continue

                for item in market:
                    grade = int(item.get("grade", 0))

                    if grade not in self.bonus:
                        continue

                    if (
                        request.enhancement_grade is not None
                        and grade != request.enhancement_grade
                    ):
                        continue

                    price = item.get("price")

                    if (
                        price is None
                        or not 0 < int(price) <= remaining_budget
                    ):
                        continue

                    options.append({
                        "sp_id": spid,
                        "player_name": row["player_name"],
                        "season_id": int(row["season_id"]),
                        "image_url": row["image_url"] or "",
                        "position": row["position"] or "",
                        "salary": int(row["salary"] or 0),
                        "base_ovr": int(row["ovr"] or 0),
                        "grade": grade,
                        "ovr": (
                            int(row["ovr"] or 0)
                            + self.bonus[grade]
                        ),
                        "price": int(price),
                        "popularity_by_position":
                            row.get(
                                "popularity_by_position"
                            )
                            or {},

                        "generation_restricted":
                            bool(
                                row.get(
                                    "generation_restricted",
                                    False,
                                )
                            ),

                        "generation_status_source":
                            row.get(
                                "generation_status_source"
                            ),

                        "generation_status_note":
                            row.get(
                                "generation_status_note"
                            ),

                        "generation_status_effective_date":
                            row.get(
                                "generation_status_effective_date"
                            ),

                        "supply_restricted":
                            bool(
                                row.get(
                                    "supply_restricted",
                                    False,
                                )
                            ),

                        "supply_restriction_class":
                            row.get(
                                "supply_restriction_class"
                            ),

                        "supply_restriction_source":
                            row.get(
                                "supply_restriction_source"
                            ),

                        "supply_restriction_notice_sn":
                            row.get(
                                "supply_restriction_notice_sn"
                            ),

                        "supply_restriction_effective_date":
                            row.get(
                                "supply_restriction_effective_date"
                            ),

                        "supply_restriction_note":
                            row.get(
                                "supply_restriction_note"
                            ),

                        "locked": False,
                    })

                    by_slot = [
                        [
                            self.apply_slot_popularity(
                                player,
                                i,
                                slot,
                            )

                            for player
                            in options

                            if (
                                player[
                                    "position"
                                ]
                                in
                                self.positions.get(
                                    slot,
                                    [slot],
                                )
                            )
                        ]

                        for i, slot
                        in remaining
                    ]

        print(
            "[QUICK SQUAD SLOT CANDIDATES]",
            flush=True,
        )

        for (
            slot_order,
            (
                slot_index,
                slot_position,
            ),
        ) in enumerate(remaining):

            slot_options = (
                by_slot[
                    slot_order
                ]
            )

            print(
                "slot_index=",
                slot_index,
                "slot=",
                slot_position,
                "count=",
                len(
                    slot_options
                ),
                "min_salary=",
                (
                    min(
                        int(
                            player["salary"]
                        )
                        for player
                        in slot_options
                    )
                    if slot_options
                    else None
                ),
                "min_price=",
                (
                    min(
                        int(
                            player["price"]
                        )
                        for player
                        in slot_options
                    )
                    if slot_options
                    else None
                ),
                "max_ovr=",
                (
                    max(
                        int(
                            player["ovr"]
                        )
                        for player
                        in slot_options
                    )
                    if slot_options
                    else None
                ),
                flush=True,
            )

            if request.enhancement_grade is not None:
                max_high = 11
            else:
                max_high = max(
                    0,
                    2 - sum(
                        p["grade"] >= 9 for p in fixed
                    ),
                )

            excluded_names = {
                self.name_key(p["player_name"])
                for p in fixed
            }

            if allocation_plan is not None:
                best = search_budget_squad(
                    by_slot,
                    [i for i, _ in remaining],
                    allocation_plan,
                    remaining_salary,
                    excluded_names,
                    max_high,
                    recommendation_mode=getattr(
                        request,
                        "recommendation_mode",
                        "meta",
                    ),
                )

            else:
                best = self._solve(
                    by_slot,
                    remaining_budget,
                    remaining_salary,
                    excluded_names,
                    max_high,
                )

            if best is not None:
                break

        if best is None:
            print(
                "[QUICK SQUAD LOCKED] NO SQUAD",
                "mode=", getattr(request, "budget_mode", "legacy"),
                "grade=", request.enhancement_grade,
                "locked=", len(fixed),
                "remaining_slots=", len(remaining),
                "budget=", remaining_budget,
                "salary=", remaining_salary,
                "prices_checked=", len(cache),
                "prices_success=", sum(
                    1 for value in cache.values()
                    if value
                ),
                "prices_failed=", sum(
                    1 for value in cache.values()
                    if value is None
                ),
                "elapsed=", round(
                    monotonic() - started_at,
                    2,
                ),
                "deadline_reached=", monotonic() >= deadline,
                flush=True,
            )

            if monotonic() >= deadline:
                raise HTTPException(
                    503,
                    "추천 후보 조회가 시간 제한에 도달했습니다. "
                    "조회 범위를 줄여 다시 시도해주세요.",
                )

            if failed:
                raise HTTPException(
                    502,
                    "일부 선수의 실제 시세를 조회하지 못했습니다. "
                    "잠시 후 다시 시도해주세요.",
                )

            raise HTTPException(
                422,
                "고정 선수를 유지하면서 예산과 급여를 "
                "만족하는 조합을 찾지 못했습니다.",
            )

        return self._summary(
            request.team_color_id,
            budget,
            request.formation,
            slots,
            request.enhancement_grade,
            fixed + best,
            len(fixed),
            allocation_plan,
        )