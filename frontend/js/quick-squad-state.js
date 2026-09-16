import {
    DEFAULT_ADAPTATION_LEVEL,
    calculatePlayerStatSnapshot,
    normalizeAdaptationLevel,
    normalizeTeamColorBonus,
    getPlayerActiveTeamColors,
} from "./player-stat-engine.js?v=2";

const STORAGE_KEY = "fcl.quick-squad.saved.v1";

const positiveId = value =>
    Number.isSafeInteger(Number(value))
    && Number(value) > 0;

const integer = (value, fallback) =>
    Number.isInteger(Number(value))
        ? Number(value)
        : fallback;

const validIndex = value =>
    Number.isInteger(value)
    && value >= 0
    && value < 11;

const amount = value =>
    Number.isFinite(Number(value))
        ? Number(value)
        : 0;

const positionName = slot =>
    typeof slot === "string"
        ? slot
        : slot?.position || "";


function normalizePlayer(
    player,
    index,
    slotPosition,
    activeTeamColors = []
) {

    const spId =
        Number(
            player.sp_id
        );


    const grade =
        Number(
            player.grade
        );


    const price =
        Number(
            player.price
        );


    if (
        !positiveId(
            spId
        )
        ||
        !Number.isInteger(
            grade
        )
        ||
        grade < 1
        ||
        grade > 13
        ||
        !Number.isSafeInteger(
            price
        )
        ||
        price <= 0
    ) {

        throw new Error(
            "저장할 선수 ID, 강화등급 또는 시세가 올바르지 않습니다."
        );
    }


    const adaptation =
        normalizeAdaptationLevel(
            player.adaptation,
            DEFAULT_ADAPTATION_LEVEL
        );


    const legacyTeamColor =
        normalizeTeamColorBonus(
            player.team_color_bonus
            ??
            0
        );


    // =====================================
    // 이 선수에게 실제 적용되는 공식 팀컬러만
    // =====================================

    const officialTeamColors =
        getPlayerActiveTeamColors(
            activeTeamColors,
            spId
        );


    // 공식 자동 팀컬러가 있으면
    // 과거 수동 +N 팀컬러는 중복 적용하지 않는다.
    const effectiveLegacyTeamColor =
        officialTeamColors.length > 0
            ? 0
            : legacyTeamColor;


    const sourceAbilityBonus =
        (
            player.manual_saved
            &&
            Number.isFinite(
                Number(
                    player.ability_bonus
                )
            )
        )
            ? Number(
                player.ability_bonus
            )
            : null;


    const statPosition =
        (
            player.position
            ||
            slotPosition
            ||
            ""
        );


    const snapshot =
        calculatePlayerStatSnapshot({

            player,

            grade,

            adaptation,

            teamColorBonus:
                effectiveLegacyTeamColor,

            activeTeamColors:
                officialTeamColors,

            position:
                statPosition,

            sourceAbilityBonus,
        });


    const bonus =
        snapshot.ability_bonus;


    const base =
        snapshot.base_ovr;


    if (
        !Number.isFinite(
            base
        )
        ||
        base <= 0
    ) {

        throw new Error(
            "선수의 기본 OVR을 확인할 수 없습니다."
        );
    }


    const season =
        positiveId(
            player.season_id
        )
            ? Number(
                player.season_id
            )
            : Math.floor(
                spId
                /
                1_000_000
            );


    const lockedGrade =
        player.locked
            ? integer(
                (
                    player.locked_grade
                    ??
                    player.recommended_grade
                    ??
                    grade
                ),
                grade
            )
            : null;


    return {

        ...player,


        sp_id:
            spId,

        season_id:
            positiveId(
                season
            )
                ? season
                : null,


        slot_index:
            index,

        slot_position:
            slotPosition,


        grade,

        adaptation,


        // 기존 저장 데이터 호환용
        team_color_bonus:
            legacyTeamColor,


        official_team_colors:
            officialTeamColors,

        official_team_color_count:
            officialTeamColors.length,


        team_color_stat_bonus:
            snapshot
                .team_color_stat_bonus,


        team_color_ovr_bonus:
            snapshot
                .team_color_ovr_bonus,


        ovr_calculation_source:
            snapshot
                .ovr_calculation_source,


        ability_bonus:
            bonus,


        base_ovr:
            base,


        ovr:
            snapshot.final_ovr,


        base_stats:
            snapshot.base_stats,


        stats:
            snapshot.final_stats,


        price,


        locked_grade:
            lockedGrade,
    };
}



export function normalizeQuickSquadResult(data, slots) {
    const positions = (slots || []).map(positionName);

    const activeTeamColors =
        Array.isArray(
            data?.active_team_colors
        )
            ? data.active_team_colors
            : [];

    if (
        !data
        || !Array.isArray(data.players)
        || data.players.length > 11
        || positions.length !== 11
        || positions.some(p => !p)
    ) {
        throw new Error(
            "스쿼드 포메이션 또는 선수 정보가 올바르지 않습니다."
        );
    }

    const players = Array(11).fill(null);
    const ids = new Set();

    data.players.forEach((player, i) => {
        if (player == null) return;

        const index = validIndex(player.slot_index)
            ? player.slot_index
            : i;

        if (!validIndex(index) || players[index]) {
            throw new Error("선수 배치가 중복되었습니다.");
        }

        const next = normalizePlayer(
            player,
            index,
            positions[index],
            activeTeamColors
        );

        if (ids.has(next.sp_id)) {
            throw new Error(
                "동일한 선수 카드가 중복되었습니다."
            );
        }

        ids.add(next.sp_id);
        players[index] = next;
    });

    const present = players.filter(Boolean);
    const locked = present.filter(p => p.locked);

    const total = present.reduce(
        (sum, p) => sum + p.price,
        0
    );

    const salary = present.reduce(
        (sum, p) => sum + amount(p.salary),
        0
    );

    const budget = amount(data.budget_bp);

    const lockedTotal = locked.reduce(
        (sum, p) => sum + p.price,
        0
    );

    const result = {
        ...data,
        players,
        slot_positions: positions,
        is_draft:
            Boolean(data.is_draft)
            || present.length !== 11,
        total_price: total,
        total_salary: salary,
        remaining_budget: budget - total,
        salary_cap: amount(data.salary_cap) || 310,
        locked_count: locked.length,
        locked_total_price: lockedTotal,
        locked_total_salary: locked.reduce(
            (sum, p) => sum + amount(p.salary),
            0
        ),
    };

    if (data.budget_allocation) {
        const plan = data.budget_allocation;
        const actuals = players.map(p => p?.price || 0);

        const sumIndices = indices =>
            (Array.isArray(indices) ? indices : [])
                .reduce(
                    (sum, i) =>
                        sum + (
                            validIndex(i)
                                ? actuals[i]
                                : 0
                        ),
                    0
                );

        const core = sumIndices(plan.core_indices);
        const other = sumIndices(plan.other_indices);

        result.budget_allocation = {
            ...plan,
            actuals,
            locked_total_price: lockedTotal,
            remaining_budget: budget - lockedTotal,
            core_actual: core,
            other_actual: other,
            remaining_actual: core + other,
            unspent_budget:
                budget - lockedTotal - core - other,
        };
    }

    return result;
}

const lockIdentity = p => [
    p.sp_id,
    p.slot_index,
    p.locked_grade
        ?? p.recommended_grade
        ?? p.grade,
];

export function sameQuickSquadLocks(players, preview) {
    const sorted = rows =>
        rows
            .filter(Boolean)
            .map(lockIdentity)
            .sort((a, b) => a[0] - b[0]);

    return JSON.stringify(
        sorted((players || []).filter(p => p?.locked))
    ) === JSON.stringify(
        sorted(preview || [])
    );
}

export function createQuickSquadDraft(
    preview,
    previous,
    context,
    slots
) {
    const positions = slots.map(positionName);
    const players = Array(11).fill(null);

    for (const fresh of preview) {
        const index = fresh.slot_index;

        if (!validIndex(index)) continue;

        const old = previous?.players?.[index];

        const originalGrade =
            old?.locked_grade
            ?? old?.recommended_grade
            ?? old?.grade;

        if (
            old?.manual_saved
            && Number(old.sp_id) === Number(fresh.sp_id)
            && Number(originalGrade) === Number(fresh.grade)
        ) {
            const {
                grade,
                adaptation,
                team_color_bonus,
                ability_bonus,
                base_ovr,
                ovr,
                price,
                price_checked_at,
                recommended_grade,
                recommended_price,
                recommended_ovr,
                manual_saved,
                base_stats,
                stats,
            } = old;

            players[index] = {
                ...fresh,
                grade,
                adaptation,
                team_color_bonus,
                ability_bonus,
                base_ovr,
                ovr,
                price,
                price_checked_at,
                recommended_grade,
                recommended_price,
                recommended_ovr,
                manual_saved,
                base_stats,
                stats,
                locked_grade: fresh.grade,
            };
        } else {
            players[index] = {
                ...fresh,
                locked_grade: fresh.grade,
            };
        }
    }

    return normalizeQuickSquadResult(
        {
            ...context,
            players,
            is_draft: true,
            manually_modified:
                players.some(p => p?.manual_saved),
        },
        positions
    );
}

export function applyQuickSquadPlayerSettings(
    data,
    slotIndex,
    selection,
    slots
) {
    if (
        !validIndex(slotIndex)
        || !data?.players?.[slotIndex]
    ) {
        throw new Error(
            "저장할 선수를 현재 스쿼드에서 찾지 못했습니다."
        );
    }

    const grade = Number(selection.grade);
    const adaptation = Number(selection.adaptation);
    const teamColor = Number(selection.team_color_bonus);
    const price = Number(selection.price);
    const base = Number(selection.base_ovr);

    if (
        !Number.isInteger(grade)
        || grade < 1
        || grade > 13
        || ![1, 5].includes(adaptation)
        || !Number.isInteger(teamColor)
        || teamColor < 0
        || teamColor > 9
        || !Number.isSafeInteger(price)
        || price <= 0
        || !Number.isFinite(base)
        || base <= 0
    ) {
        throw new Error(
            "선택한 선수 설정 또는 시세가 올바르지 않습니다."
        );
    }

    const original = data.players[slotIndex];

    const players = data.players.map(
        p => p ? { ...p } : null
    );

    players[slotIndex] = {
        ...original,

        recommended_grade:
            original.recommended_grade ?? original.grade,

        recommended_price:
            original.recommended_price ?? original.price,

        recommended_ovr:
            original.recommended_ovr ?? original.ovr,

        grade,
        adaptation,
        team_color_bonus: teamColor,
        base_ovr: base,
        price,
        base_stats:
            selection.base_stats
            ??
            original.base_stats,

        stats:
            selection.stats
            ??
            original.stats,
        price_checked_at: selection.price_checked_at,
        manual_saved: true,
    };

    return normalizeQuickSquadResult(
        {
            ...data,
            players,
            manually_modified: true,
            last_saved_at: new Date().toISOString(),
        },
        slots
    );
}

export function readSavedQuickSquad() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);

        if (!raw) return null;

        const data = JSON.parse(raw);

        if (
            !Array.isArray(data?.players)
            || data.players.length !== 11
            || typeof data.formation !== "string"
            || !positiveId(data.budget_bp)
        ) {
            return null;
        }

        const slots =
            Array.isArray(data.slot_positions)
            && data.slot_positions.length === 11
                ? data.slot_positions
                : data.players.map(
                    p => p?.slot_position || ""
                );

        return {
            ...data,
            slot_positions: slots,
        };
    } catch {
        return null;
    }
}

export function writeSavedQuickSquad(data) {
    try {
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(data)
        );
    } catch {
        throw new Error(
            "브라우저 저장 공간에 저장하지 못했습니다."
        );
    }
}

// =========================================
// LOCKED PLAYER SAVED SETTINGS
// =========================================

export function normalizeQuickSquadLockSettings(value) {
    if (!value || typeof value !== "object") {
        return null;
    }

    const grade = Number(value.grade);
    const adaptation = Number(value.adaptation);
    const teamColor = Number(value.team_color_bonus);
    const price = Number(value.price);
    const baseOvr = Number(value.base_ovr);

    if (
        !Number.isInteger(grade)
        || grade < 1
        || grade > 13
        || ![1, 5].includes(adaptation)
        || !Number.isInteger(teamColor)
        || teamColor < 0
        || teamColor > 9
        || !Number.isSafeInteger(price)
        || price <= 0
        || !Number.isFinite(baseOvr)
        || baseOvr <= 0
    ) {
        return null;
    }

    const snapshot =
        calculatePlayerStatSnapshot({
            player: {
                base_ovr:
                    baseOvr,
            },

            grade,

            adaptation,

            teamColorBonus:
                teamColor,

            sourceAbilityBonus:
                0,
        });


    const bonus =
        snapshot.ability_bonus;

    return {
        grade,
        adaptation,
        team_color_bonus: teamColor,
        ability_bonus: bonus,
        base_ovr: baseOvr,
        ovr:
            snapshot.final_ovr,
        price,

        price_checked_at:
            typeof value.price_checked_at === "string"
                ? value.price_checked_at
                : null,

        ...(value.base_stats
            && typeof value.base_stats === "object"
            && !Array.isArray(value.base_stats)
                ? {base_stats: {...value.base_stats}}
                : {}),

        ...(value.stats
            && typeof value.stats === "object"
            && !Array.isArray(value.stats)
                ? {stats: {...value.stats}}
                : {}),
    };
}

export function mergeQuickSquadLockSettings(
    player,
    entry
) {
    if (!player || !entry) return player;

    const grade = Number(entry.grade);

    const result = {
        ...player,
        grade,
        locked_grade: grade,
        slot_index: entry.slot_index ?? null,
        slot_position: entry.slot_position || null,
        locked: true,
    };

    const saved = normalizeQuickSquadLockSettings(
        entry.saved_settings
    );

    const rawPrice = Number(player.price);

    const hasCurrentGradePrice =
        Number(player.grade) === grade
        && Number.isSafeInteger(rawPrice)
        && rawPrice > 0;

    // 다른 강화등급의 오래된 가격을 사용하지 않는다.
    if (!saved || saved.grade !== grade) {
        if (!hasCurrentGradePrice) {
            result.price = null;
        }

        return result;
    }

    const baseOvr =
        Number(player.base_ovr) > 0
            ? Number(player.base_ovr)
            : saved.base_ovr;

    return {
        ...result,
        ...saved,

        grade,
        locked_grade: grade,

        base_ovr: baseOvr,
        ovr: baseOvr + saved.ability_bonus,

        // 서버가 현재 강화의 시세를 조회했다면
        // 그 가격을 우선 사용한다.
        price: hasCurrentGradePrice
            ? rawPrice
            : saved.price,

        price_checked_at: hasCurrentGradePrice
            ? (
                player.price_checked_at
                ?? saved.price_checked_at
            )
            : saved.price_checked_at,

        manual_saved: true,
    };
}