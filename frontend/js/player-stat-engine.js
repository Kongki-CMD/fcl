// =========================================
// FC ONLINE PLAYER STAT ENGINE
//
// 현재 단계:
// 강화 + 적응도 + 수동 팀컬러 보너스
//
// 이후 공식 팀컬러 엔진을 붙일 때도
// 이 파일을 최종 계산 진입점으로 사용한다.
// =========================================

export const DEFAULT_ADAPTATION_LEVEL = 5;


export const ENHANCEMENT_BONUS_MAP =
    Object.freeze({
        1: 0,
        2: 1,
        3: 2,
        4: 4,
        5: 6,
        6: 8,
        7: 11,
        8: 15,
        9: 17,
        10: 19,
        11: 21,
        12: 24,
        13: 27,
    });


export const ADAPTATION_BONUS_MAP =
    Object.freeze({
        1: 0,
        5: 4,
    });


export function normalizePlayerGrade(
    value,
    fallback = 1
) {
    const grade =
        Number(value);

    if (
        Number.isInteger(grade)
        &&
        grade >= 1
        &&
        grade <= 13
    ) {
        return grade;
    }

    return fallback;
}


export function normalizeAdaptationLevel(
    value,
    fallback = DEFAULT_ADAPTATION_LEVEL
) {
    const adaptation =
        Number(value);

    if (
        adaptation === 1
        ||
        adaptation === 5
    ) {
        return adaptation;
    }

    return fallback;
}


export function normalizeTeamColorBonus(
    value
) {
    const bonus =
        Number(value);

    if (!Number.isFinite(bonus)) {
        return 0;
    }

    return Math.max(
        0,
        Math.min(
            9,
            Math.trunc(bonus)
        )
    );
}

// =========================================
// OFFICIAL TEAM COLOR STAT EFFECTS
//
// 팀컬러는 단순 +N이 아니라
// 능력치별 효과를 가진다.
//
// "__all__"은 "전체 능력치"를 의미한다.
// =========================================

export function normalizeStatBonusMap(
    value
) {
    if (
        !value
        ||
        typeof value !== "object"
        ||
        Array.isArray(value)
    ) {
        return {};
    }


    const result = {};


    Object
        .entries(value)
        .forEach(
            ([
                statName,
                rawBonus,
            ]) => {

                const normalizedName =
                    String(
                        statName
                        ??
                        ""
                    )
                        .trim();


                const bonus =
                    Number(
                        rawBonus
                    );


                if (
                    !normalizedName
                    ||
                    !Number.isFinite(
                        bonus
                    )
                    ||
                    bonus === 0
                ) {
                    return;
                }


                result[
                    normalizedName
                ] =
                    (
                        result[
                            normalizedName
                        ]
                        ??
                        0
                    )
                    +
                    bonus;
            }
        );


    return result;
}


export function mergeStatBonusMaps(
    ...bonusMaps
) {
    const result = {};


    bonusMaps
        .forEach(
            bonusMap => {

                const normalized =
                    normalizeStatBonusMap(
                        bonusMap
                    );


                Object
                    .entries(
                        normalized
                    )
                    .forEach(
                        ([
                            statName,
                            bonus,
                        ]) => {

                            result[
                                statName
                            ] =
                                (
                                    result[
                                        statName
                                    ]
                                    ??
                                    0
                                )
                                +
                                bonus;
                        }
                    );
            }
        );


    return result;
}


export function getActiveTeamColorStatBonus(
    activeTeamColors = []
) {
    if (
        !Array.isArray(
            activeTeamColors
        )
    ) {
        return {};
    }


    return mergeStatBonusMaps(
        ...activeTeamColors
            .map(
                teamColor =>
                    teamColor?.effects
                    ??
                    {}
            )
    );
}


export function applyStatBonusMap(
    baseStats,
    bonusMap
) {
    const normalizedBonusMap =
        normalizeStatBonusMap(
            bonusMap
        );


    const allStatBonus =
        Number(
            normalizedBonusMap.__all__
            ??
            0
        );


    return Object.fromEntries(
        Object
            .entries(
                baseStats
                ??
                {}
            )
            .map(
                ([
                    statName,
                    statValue,
                ]) => {

                    if (
                        statValue === null
                        ||
                        statValue === undefined
                    ) {
                        return [
                            statName,
                            null,
                        ];
                    }


                    const numericValue =
                        Number(
                            statValue
                        );


                    if (
                        !Number.isFinite(
                            numericValue
                        )
                    ) {
                        return [
                            statName,
                            null,
                        ];
                    }


                    const specificBonus =
                        Number(
                            normalizedBonusMap[
                                statName
                            ]
                            ??
                            0
                        );


                    return [
                        statName,

                        numericValue
                        +
                        allStatBonus
                        +
                        specificBonus,
                    ];
                }
            )
    );
}


export function getEnhancementBonus(
    grade
) {
    const normalizedGrade =
        normalizePlayerGrade(
            grade
        );

    return (
        ENHANCEMENT_BONUS_MAP[
            normalizedGrade
        ]
        ??
        0
    );
}


export function getAdaptationBonus(
    adaptation
) {
    const normalizedAdaptation =
        normalizeAdaptationLevel(
            adaptation
        );

    return (
        ADAPTATION_BONUS_MAP[
            normalizedAdaptation
        ]
        ??
        0
    );
}


function isStatObject(
    value
) {
    return (
        value
        &&
        typeof value === "object"
        &&
        !Array.isArray(value)
    );
}


export function calculatePlayerStatSnapshot({
    player,
    grade = 1,
    adaptation = DEFAULT_ADAPTATION_LEVEL,

    // 기존 화면 호환용.
    // 공식 팀컬러 적용이 완료되면 제거 예정.
    teamColorBonus = 0,

    // 실제 활성 팀컬러.
    activeTeamColors = [],

    // 실제 활성 강화 팀컬러.
    activeEnhancementTeamColor = null,

    sourceAbilityBonus = null,
}) {
    const normalizedGrade =
        normalizePlayerGrade(
            grade
        );

    const normalizedAdaptation =
        normalizeAdaptationLevel(
            adaptation
        );

    const normalizedTeamColorBonus =
        normalizeTeamColorBonus(
            teamColorBonus
        );


    const enhancementBonus =
        getEnhancementBonus(
            normalizedGrade
        );

const adaptationBonus =
    getAdaptationBonus(
        normalizedAdaptation
    );


// =========================================
// 기존 공통 상승치
//
// 강화 + 적응도 + 기존 수동 팀컬러
// =========================================

const abilityBonus =
    enhancementBonus
    +
    adaptationBonus
    +
    normalizedTeamColorBonus;


// =========================================
// 실제 공식 팀컬러 효과
// =========================================

const teamColorStatBonus =
    getActiveTeamColorStatBonus(
        [
            ...(
                Array.isArray(
                    activeTeamColors
                )
                    ? activeTeamColors
                    : []
            ),

            ...(
                activeEnhancementTeamColor
                    ? [
                        activeEnhancementTeamColor,
                    ]
                    : []
            ),
        ]
    );


    let sourceBonus =
        Number(
            sourceAbilityBonus
        );

    if (
        sourceAbilityBonus === null
        ||
        sourceAbilityBonus === undefined
        ||
        !Number.isFinite(sourceBonus)
    ) {
        sourceBonus =
            Number(
                player?.ability_bonus
                ??
                0
            );

        if (!Number.isFinite(sourceBonus)) {
            sourceBonus = 0;
        }
    }


    const explicitBaseOvr =
        Number(
            player?.base_ovr
        );

    const sourceOvr =
        Number(
            player?.ovr
        );


    const baseOvr =
        (
            Number.isFinite(explicitBaseOvr)
            &&
            explicitBaseOvr > 0
        )
            ? explicitBaseOvr
            : (
                Number.isFinite(sourceOvr)
                    ? sourceOvr - sourceBonus
                    : 0
            );


    const hasBaseStats =
        isStatObject(
            player?.base_stats
        );

    const sourceStats =
        hasBaseStats
            ? player.base_stats
            : (
                isStatObject(player?.stats)
                    ? player.stats
                    : {}
            );


    const baseStats =
        Object.fromEntries(
            Object.entries(
                sourceStats
            )
                .map(
                    ([
                        statName,
                        statValue,
                    ]) => {
                        if (
                            statValue === null
                            ||
                            statValue === undefined
                        ) {
                            return [
                                statName,
                                null,
                            ];
                        }

                        const numericValue =
                            Number(
                                statValue
                            );

                        if (
                            !Number.isFinite(
                                numericValue
                            )
                        ) {
                            return [
                                statName,
                                null,
                            ];
                        }

                        return [
                            statName,
                            hasBaseStats
                                ? numericValue
                                : numericValue
                                    - sourceBonus,
                        ];
                    }
                )
        );


    const statsBeforeTeamColor =
        Object.fromEntries(
            Object
                .entries(
                    baseStats
                )
                .map(
                    ([
                        statName,
                        statValue,
                    ]) => [
                        statName,

                        statValue === null
                            ? null
                            : statValue
                                +
                                abilityBonus,
                    ]
                )
        );


    const finalStats =
        applyStatBonusMap(
            statsBeforeTeamColor,
            teamColorStatBonus
        );


    return {
        grade:
            normalizedGrade,

        adaptation_level:
            normalizedAdaptation,

        team_color_bonus:
            normalizedTeamColorBonus,

        active_team_colors:
            Array.isArray(
                activeTeamColors
            )
                ? activeTeamColors
                : [],

        active_enhancement_team_color:
            activeEnhancementTeamColor,

        team_color_stat_bonus:
            teamColorStatBonus,

        enhancement_bonus:
            enhancementBonus,

        adaptation_bonus:
            adaptationBonus,

        ability_bonus:
            abilityBonus,

        base_ovr:
            baseOvr,

        final_ovr:
            baseOvr
            +
            abilityBonus,

        base_stats:
            baseStats,

        stats_before_team_color:
            statsBeforeTeamColor,

        final_stats:
            finalStats,
    };
}