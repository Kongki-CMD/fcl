// =========================================
// FC ONLINE PLAYER STAT ENGINE
// =========================================

export const DEFAULT_ADAPTATION_LEVEL =
    5;


// =========================================
// ENHANCEMENT
// =========================================

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


// =========================================
// ADAPTATION
// =========================================

export const ADAPTATION_BONUS_MAP =
    Object.freeze({

        1: 0,
        5: 4,
    });


// =========================================
// STAT KEY ↔ KOREAN LABEL
// =========================================

export const STAT_KEY_LABEL_MAP =
    Object.freeze({

        sprint_speed:
            "속력",

        acceleration:
            "가속력",

        finishing:
            "골 결정력",

        shot_power:
            "슛 파워",

        long_shots:
            "중거리 슛",

        positioning:
            "위치 선정",

        volleys:
            "발리슛",

        penalties:
            "페널티 킥",

        short_pass:
            "짧은 패스",

        vision:
            "시야",

        crossing:
            "크로스",

        long_pass:
            "긴 패스",

        free_kick:
            "프리킥",

        curve:
            "커브",

        dribbling:
            "드리블",

        ball_control:
            "볼 컨트롤",

        agility:
            "민첩성",

        balance:
            "밸런스",

        reactions:
            "반응 속도",

        marking:
            "대인 수비",

        tackle:
            "태클",

        interceptions:
            "가로채기",

        heading:
            "헤더",

        sliding_tackle:
            "슬라이딩 태클",

        strength:
            "몸싸움",

        stamina:
            "스태미너",

        aggression:
            "적극성",

        jumping:
            "점프",

        composure:
            "침착성",

        gk_diving:
            "GK 다이빙",

        gk_handling:
            "GK 핸들링",

        gk_kick:
            "GK 킥",

        gk_reflexes:
            "GK 반응속도",

        gk_positioning:
            "GK 위치 선정",
    });

const STAT_LABEL_KEY_MAP =
    Object.freeze(
        Object.fromEntries(
            Object
                .entries(
                    STAT_KEY_LABEL_MAP
                )
                .map(
                    (
                        [
                            key,
                            label,
                        ]
                    ) => [
                        label,
                        key,
                    ]
                )
        )
    );


// =========================================
// TEAM COLOR STAT KEY ALIASES
//
// 팀컬러 DB의 공식 key
// → 선수 DB 내부 key
// =========================================

const TEAM_COLOR_STAT_KEY_ALIAS_MAP =
    Object.freeze({

        short_passing:
            "short_pass",

        long_passing:
            "long_pass",

        free_kick_accuracy:
            "free_kick",

        standing_tackle:
            "tackle",

        heading_accuracy:
            "heading",

        gk_kicking:
            "gk_kick",
    });


// =========================================
// POSITION OVR WEIGHTS
//
// 각 포지션 가중치 합계 = 100
// =========================================

export const POSITION_OVR_WEIGHT_MAP =
    Object.freeze({

        GK: Object.freeze({

            gk_diving: 21,
            gk_handling: 21,
            gk_positioning: 21,
            gk_reflexes: 21,
            reactions: 11,
            gk_kick: 5,
        }),


        CB: Object.freeze({

            tackle: 17,
            marking: 14,
            interceptions: 13,
            heading: 10,
            sliding_tackle: 10,
            strength: 10,
            aggression: 7,
            short_pass: 5,
            reactions: 5,
            ball_control: 4,
            jumping: 3,
            sprint_speed: 2,
        }),


        FB: Object.freeze({

            sliding_tackle: 14,
            interceptions: 12,
            tackle: 11,
            crossing: 9,
            marking: 8,
            stamina: 8,
            reactions: 8,
            short_pass: 7,
            ball_control: 7,
            sprint_speed: 7,
            acceleration: 5,
            heading: 4,
        }),


        WB: Object.freeze({

            crossing: 12,
            interceptions: 12,
            sliding_tackle: 11,
            short_pass: 10,
            stamina: 10,
            tackle: 8,
            ball_control: 8,
            reactions: 8,
            marking: 7,
            sprint_speed: 6,
            dribbling: 4,
            acceleration: 4,
        }),


        CDM: Object.freeze({

            short_pass: 14,
            interceptions: 14,
            tackle: 12,
            ball_control: 10,
            long_pass: 10,
            marking: 9,
            reactions: 7,
            stamina: 6,
            sliding_tackle: 5,
            aggression: 5,
            strength: 4,
            vision: 4,
        }),


        CM: Object.freeze({

            short_pass: 17,
            ball_control: 14,
            long_pass: 13,
            vision: 13,
            reactions: 8,
            dribbling: 7,
            stamina: 6,
            positioning: 6,
            tackle: 5,
            interceptions: 5,
            long_shots: 4,
            finishing: 2,
        }),


        CAM: Object.freeze({

            short_pass: 16,
            ball_control: 15,
            vision: 14,
            dribbling: 13,
            positioning: 9,
            finishing: 7,
            reactions: 7,
            long_shots: 5,
            long_pass: 4,
            acceleration: 4,
            sprint_speed: 3,
            agility: 3,
        }),


        WM: Object.freeze({

            dribbling: 15,
            ball_control: 13,
            short_pass: 11,
            crossing: 10,
            positioning: 8,
            acceleration: 7,
            reactions: 7,
            vision: 7,
            finishing: 6,
            sprint_speed: 6,
            long_pass: 5,
            stamina: 5,
        }),


        W: Object.freeze({

            dribbling: 16,
            ball_control: 14,
            finishing: 10,
            crossing: 9,
            short_pass: 9,
            positioning: 9,
            acceleration: 7,
            reactions: 7,
            sprint_speed: 6,
            vision: 6,
            long_shots: 4,
            agility: 3,
        }),


        CF: Object.freeze({

            ball_control: 15,
            dribbling: 14,
            positioning: 13,
            finishing: 11,
            short_pass: 9,
            reactions: 9,
            vision: 8,
            shot_power: 5,
            acceleration: 5,
            sprint_speed: 5,
            long_shots: 4,
            heading: 2,
        }),


        ST: Object.freeze({

            finishing: 18,
            positioning: 13,
            heading: 10,
            ball_control: 10,
            shot_power: 10,
            reactions: 8,
            dribbling: 7,
            short_pass: 5,
            strength: 5,
            sprint_speed: 5,
            acceleration: 4,
            long_shots: 3,
            volleys: 2,
        }),
    });


// =========================================
// NORMALIZE
// =========================================

export function normalizePlayerGrade(
    value,
    fallback = 1
) {

    const grade =
        Number(
            value
        );


    if (
        Number.isInteger(
            grade
        )
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
    fallback =
        DEFAULT_ADAPTATION_LEVEL
) {

    const adaptation =
        Number(
            value
        );


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
        Number(
            value
        );


    if (
        !Number.isFinite(
            bonus
        )
    ) {

        return 0;
    }


    return Math.max(
        0,

        Math.min(
            9,

            Math.trunc(
                bonus
            )
        )
    );
}


// =========================================
// BASIC BONUSES
// =========================================

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


// =========================================
// STAT HELPERS
// =========================================

function isStatObject(
    value
) {

    return (
        value
        &&
        typeof value
        ===
        "object"
        &&
        !Array.isArray(
            value
        )
    );
}


function getCanonicalStatKey(
    value
) {

    const name =
        String(
            value
            ??
            ""
        )
            .trim();


    if (!name) {
        return "";
    }


    if (
        name
        ===
        "__all__"
        ||
        name
        ===
        "전체 능력치"
    ) {

        return "__all__";
    }

    const aliasedStatKey =
        TEAM_COLOR_STAT_KEY_ALIAS_MAP[
            name
        ];


    if (aliasedStatKey) {

        return aliasedStatKey;
    }


    if (
        Object.prototype
            .hasOwnProperty
            .call(
                STAT_KEY_LABEL_MAP,
                name
            )
    ) {

        return name;
    }


    return (
        STAT_LABEL_KEY_MAP[
            name
        ]
        ??
        name
    );
}


function getStatValue(
    stats,
    statKey
) {

    if (
        !isStatObject(
            stats
        )
    ) {

        return null;
    }


    if (
        stats[
            statKey
        ]
        !==
        undefined
        &&
        stats[
            statKey
        ]
        !==
        null
    ) {

        const value =
            Number(
                stats[
                    statKey
                ]
            );


        return Number.isFinite(
            value
        )
            ? value
            : null;
    }


    const koreanLabel =
        STAT_KEY_LABEL_MAP[
            statKey
        ];


    if (
        koreanLabel
        &&
        stats[
            koreanLabel
        ]
        !==
        undefined
        &&
        stats[
            koreanLabel
        ]
        !==
        null
    ) {

        const value =
            Number(
                stats[
                    koreanLabel
                ]
            );


        return Number.isFinite(
            value
        )
            ? value
            : null;
    }


    return null;
}


// =========================================
// TEAM COLOR EFFECTS
// =========================================

export function normalizeStatBonusMap(
    value
) {

    if (
        !value
        ||
        typeof value !== "object"
        ||
        Array.isArray(
            value
        )
    ) {

        return {};
    }


    const result = {};


    Object
        .entries(
            value
        )
        .forEach(
            (
                [
                    rawStatName,
                    rawBonus,
                ]
            ) => {

                const statKey =
                    getCanonicalStatKey(
                        rawStatName
                    );


                const bonus =
                    Number(
                        rawBonus
                    );


                if (
                    !statKey
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
                    statKey
                ] =
                    (
                        result[
                            statKey
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


export function teamColorEffectsToBonusMap(
    effects
) {

    if (
        !Array.isArray(
            effects
        )
    ) {

        return normalizeStatBonusMap(
            effects
        );
    }


    const result = {};


    effects
        .forEach(
            effect => {

                if (
                    !effect
                    ||
                    typeof effect
                    !==
                    "object"
                ) {

                    return;
                }


                const statKey =
                    getCanonicalStatKey(
                        effect.stat_key
                        ??
                        effect.stat_name
                    );


                const bonus =
                    Number(
                        effect.bonus
                        ??
                        0
                    );


                if (
                    !statKey
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
                    statKey
                ] =
                    (
                        result[
                            statKey
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
                        (
                            [
                                statKey,
                                bonus,
                            ]
                        ) => {

                            result[
                                statKey
                            ] =
                                (
                                    result[
                                        statKey
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


// =========================================
// PLAYER-SPECIFIC ACTIVE TEAM COLORS
// =========================================

export function getPlayerActiveTeamColors(
    activeTeamColors = [],
    spId = null
) {

    if (
        !Array.isArray(
            activeTeamColors
        )
    ) {

        return [];
    }


    const numericSpId =
        Number(
            spId
        );


    return activeTeamColors
        .filter(
            teamColor => {

                if (
                    !teamColor
                    ||
                    typeof teamColor
                    !==
                    "object"
                ) {

                    return false;
                }


                const matchedSpIds =
                    Array.isArray(
                        teamColor.matched_sp_ids
                    )
                        ? teamColor
                            .matched_sp_ids
                        : [];


                // 매칭 목록이 없는 다른 화면에서는
                // 기존처럼 전체 적용
                if (
                    matchedSpIds.length
                    === 0
                ) {

                    return true;
                }


                if (
                    !Number.isFinite(
                        numericSpId
                    )
                    ||
                    numericSpId <= 0
                ) {

                    return false;
                }


                return matchedSpIds
                    .some(
                        matchedSpId =>
                            Number(
                                matchedSpId
                            )
                            ===
                            numericSpId
                    );
            }
        );
}


export function getActiveTeamColorStatBonus(
    activeTeamColors = [],
    spId = null
) {

    const playerTeamColors =
        getPlayerActiveTeamColors(
            activeTeamColors,
            spId
        );


    return mergeStatBonusMaps(
        ...playerTeamColors
            .map(
                teamColor =>
                    teamColorEffectsToBonusMap(
                        teamColor.effects
                    )
            )
    );
}


// =========================================
// APPLY TEAM COLOR TO STATS
// =========================================

function getSpecificStatBonus(
    statName,
    bonusMap
) {

    const canonicalKey =
        getCanonicalStatKey(
            statName
        );


    return Number(
        bonusMap[
            canonicalKey
        ]
        ??
        0
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
                (
                    [
                        statName,
                        statValue,
                    ]
                ) => {

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
                        getSpecificStatBonus(
                            statName,
                            normalizedBonusMap
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


// =========================================
// POSITION NORMALIZATION
// =========================================

export function normalizeOvrPosition(
    value
) {

    const position =
        String(
            value
            ??
            ""
        )
            .trim()
            .toUpperCase();


    if (
        [
            "RS",
            "ST",
            "LS",
        ].includes(
            position
        )
    ) {

        return "ST";
    }


    if (
        [
            "RF",
            "CF",
            "LF",
        ].includes(
            position
        )
    ) {

        return "CF";
    }


    if (
        [
            "RW",
            "LW",
        ].includes(
            position
        )
    ) {

        return "W";
    }


    if (
        [
            "RM",
            "LM",
        ].includes(
            position
        )
    ) {

        return "WM";
    }


    if (
        [
            "RAM",
            "CAM",
            "LAM",
        ].includes(
            position
        )
    ) {

        return "CAM";
    }


    if (
        [
            "RCM",
            "CM",
            "LCM",
        ].includes(
            position
        )
    ) {

        return "CM";
    }


    if (
        [
            "RDM",
            "CDM",
            "LDM",
        ].includes(
            position
        )
    ) {

        return "CDM";
    }


    if (
        [
            "RWB",
            "LWB",
        ].includes(
            position
        )
    ) {

        return "WB";
    }


    if (
        [
            "RB",
            "LB",
        ].includes(
            position
        )
    ) {

        return "FB";
    }


    if (
        [
            "SW",
            "RCB",
            "CB",
            "LCB",
        ].includes(
            position
        )
    ) {

        return "CB";
    }


    if (
        position === "GK"
    ) {

        return "GK";
    }


    return "";
}


// =========================================
// POSITION-WEIGHTED OVR
// =========================================

export function calculatePositionWeightedOvr(
    stats,
    position
) {

    const normalizedPosition =
        normalizeOvrPosition(
            position
        );


    const weights =
        POSITION_OVR_WEIGHT_MAP[
            normalizedPosition
        ];


    if (!weights) {

        return null;
    }


    let weightedPoints =
        0;


    for (
        const [
            statKey,
            weight,
        ]
        of Object.entries(
            weights
        )
    ) {

        const statValue =
            getStatValue(
                stats,
                statKey
            );


        if (
            statValue === null
        ) {

            return null;
        }


        weightedPoints +=
            (
                statValue
                *
                weight
            );
    }


    const weightedValue =
        (
            weightedPoints
            /
            100
        );


    return {

        position:
            normalizedPosition,

        weighted_points:
            weightedPoints,

        weighted_value:
            weightedValue,

        displayed_ovr:
            Math.floor(
                weightedValue
                +
                1e-9
            ),
    };
}


// =========================================
// FINAL SNAPSHOT
// =========================================

export function calculatePlayerStatSnapshot({

    player,

    grade = 1,

    adaptation =
        DEFAULT_ADAPTATION_LEVEL,

    // 선수도감의 수동 시뮬레이션용
    teamColorBonus = 0,

    // 실제 활성 팀컬러
    activeTeamColors = [],

    // 기존 호출 호환
    activeEnhancementTeamColor = null,

    position = null,

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


    // =====================================
    // 기존 공통 상승치
    //
    // 강화 + 적응도 + 수동 팀컬러
    // =====================================

    const abilityBonus =
        enhancementBonus
        +
        adaptationBonus
        +
        normalizedTeamColorBonus;


    // =====================================
    // 공식 활성 팀컬러
    // =====================================

    const allActiveTeamColors = [
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
    ];


    const playerActiveTeamColors =
        getPlayerActiveTeamColors(
            allActiveTeamColors,

            player?.sp_id
        );


    const teamColorStatBonus =
        getActiveTeamColorStatBonus(
            playerActiveTeamColors,

            player?.sp_id
        );


    // =====================================
    // 기존 데이터가 이미 보정된 값일 때
    // 원본 OVR / 원본 세부 능력치 복원
    // =====================================

    let sourceBonus =
        Number(
            sourceAbilityBonus
        );


    if (
        sourceAbilityBonus === null
        ||
        sourceAbilityBonus === undefined
        ||
        !Number.isFinite(
            sourceBonus
        )
    ) {

        sourceBonus =
            Number(
                player?.ability_bonus
                ??
                0
            );


        if (
            !Number.isFinite(
                sourceBonus
            )
        ) {

            sourceBonus =
                0;
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


    let baseOvr =
        (
            Number.isFinite(
                explicitBaseOvr
            )
            &&
            explicitBaseOvr > 0
        )
            ? explicitBaseOvr

            : (
                Number.isFinite(
                    sourceOvr
                )
                    ? (
                        sourceOvr
                        -
                        sourceBonus
                    )
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
                isStatObject(
                    player?.stats
                )
                    ? player.stats
                    : {}
            );


    const baseStats =
        Object.fromEntries(
            Object
                .entries(
                    sourceStats
                )
                .map(
                    (
                        [
                            statName,
                            statValue,
                        ]
                    ) => {

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

                                : (
                                    numericValue
                                    -
                                    sourceBonus
                                ),
                        ];
                    }
                )
        );


    // =====================================
    // 강화 + 적응도 + 수동 보너스
    // =====================================

    const statsBeforeTeamColor =
        Object.fromEntries(
            Object
                .entries(
                    baseStats
                )
                .map(
                    (
                        [
                            statName,
                            statValue,
                        ]
                    ) => [

                        statName,

                        statValue === null
                            ? null
                            : (
                                statValue
                                +
                                abilityBonus
                            ),
                    ]
                )
        );


    // =====================================
    // 공식 팀컬러 세부 능력치 적용
    // =====================================

    const finalStats =
        applyStatBonusMap(
            statsBeforeTeamColor,
            teamColorStatBonus
        );


    const resolvedPosition =
        (
            position
            ||
            player?.position
            ||
            ""
        );


    const baseWeightedOvr =
        calculatePositionWeightedOvr(
            baseStats,
            resolvedPosition
        );


    const beforeTeamColorWeightedOvr =
        calculatePositionWeightedOvr(
            statsBeforeTeamColor,
            resolvedPosition
        );


    const finalWeightedOvr =
        calculatePositionWeightedOvr(
            finalStats,
            resolvedPosition
        );


    // =====================================
    // DB 기본 OVR을 기준점으로 사용
    //
    // 가중치 산식은 "증가량" 계산에 사용.
    // 이렇게 해야 DB 기본 OVR과 소수점/표시 차이가
    // 있더라도 기준 OVR을 망가뜨리지 않는다.
    // =====================================

    let finalOvr;

    let teamColorOvrBonus =
        0;

    let ovrCalculationSource =
        "fallback";


    if (
        baseWeightedOvr
        &&
        beforeTeamColorWeightedOvr
        &&
        finalWeightedOvr
    ) {

        if (
            !Number.isFinite(
                baseOvr
            )
            ||
            baseOvr <= 0
        ) {

            baseOvr =
                baseWeightedOvr
                    .displayed_ovr;
        }


        const totalWeightedOvrGain =
            (
                finalWeightedOvr
                    .displayed_ovr
                -
                baseWeightedOvr
                    .displayed_ovr
            );


        teamColorOvrBonus =
            (
                finalWeightedOvr
                    .displayed_ovr
                -
                beforeTeamColorWeightedOvr
                    .displayed_ovr
            );


        finalOvr =
            (
                baseOvr
                +
                totalWeightedOvrGain
            );


        ovrCalculationSource =
            "position-weighted";

    } else {

        const allStatBonus =
            Number(
                teamColorStatBonus.__all__
                ??
                0
            );


        teamColorOvrBonus =
            allStatBonus;


        finalOvr =
            (
                baseOvr
                +
                abilityBonus
                +
                allStatBonus
            );
    }


    return {

        grade:
            normalizedGrade,

        adaptation_level:
            normalizedAdaptation,

        team_color_bonus:
            normalizedTeamColorBonus,


        active_team_colors:
            playerActiveTeamColors,


        team_color_stat_bonus:
            teamColorStatBonus,


        enhancement_bonus:
            enhancementBonus,

        adaptation_bonus:
            adaptationBonus,

        ability_bonus:
            abilityBonus,


        team_color_ovr_bonus:
            teamColorOvrBonus,


        base_ovr:
            baseOvr,

        final_ovr:
            finalOvr,


        ovr_calculation_source:
            ovrCalculationSource,


        weighted_base_ovr:
            baseWeightedOvr,

        weighted_before_team_color_ovr:
            beforeTeamColorWeightedOvr,

        weighted_final_ovr:
            finalWeightedOvr,


        base_stats:
            baseStats,

        stats_before_team_color:
            statsBeforeTeamColor,

        final_stats:
            finalStats,
    };
}