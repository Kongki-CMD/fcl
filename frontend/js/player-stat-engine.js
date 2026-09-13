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
    teamColorBonus = 0,
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

    const abilityBonus =
        enhancementBonus
        +
        adaptationBonus
        +
        normalizedTeamColorBonus;


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


    const finalStats =
        Object.fromEntries(
            Object.entries(
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
                                + abilityBonus,
                    ]
                )
        );


    return {
        grade:
            normalizedGrade,

        adaptation_level:
            normalizedAdaptation,

        team_color_bonus:
            normalizedTeamColorBonus,

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

        final_stats:
            finalStats,
    };
}