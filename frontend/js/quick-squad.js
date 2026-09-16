import {
    apiBaseUrl,
} from "./config.js";

import {
    DEFAULT_ADAPTATION_LEVEL,
} from "./player-stat-engine.js?v=2";

import {
    createQuickSquadDetailModal,
} from "./quick-squad-detail.js?v=7";

import {
    createQuickSquadLockController,
} from "./quick-squad-locks.js?v=3";

import {
    readQuickSquadLocks,
} from "./quick-squad-locks.js?v=2";

import {
    createQuickSquadBudgetController,
} from "./quick-squad-budget.js?v=3";

import {
    normalizeQuickSquadResult,
    createQuickSquadDraft,
    sameQuickSquadLocks,
    applyQuickSquadPlayerSettings,
    readSavedQuickSquad,
    writeSavedQuickSquad,
    mergeQuickSquadLockSettings,
} from "./quick-squad-state.js?v=3";

// =========================================
// DOM
// =========================================

const quickSquadTeamColorElement =
    document.getElementById(
        "quick-squad-team-color"
    );

const quickSquadTeamColorSearchElement =
    document.getElementById(
        "quick-squad-team-color-search"
    );


const quickSquadBudgetElement =
    document.getElementById(
        "quick-squad-budget"
    );

const quickSquadEnhancementGradeElement =
    document.getElementById(
        "quick-squad-enhancement-grade"
    );


const quickSquadFormationElement =
    document.getElementById(
        "quick-squad-formation"
    );


const quickSquadFormationTitleElement =
    document.getElementById(
        "quick-squad-formation-title"
    );

const quickSquadActiveTeamColorsElement =
    document.getElementById(
        "quick-squad-active-team-colors"
    );


const quickSquadPlayerLayerElement =
    document.getElementById(
        "quick-squad-player-layer"
    );


const quickSquadResultStatusElement =
    document.getElementById(
        "quick-squad-result-status"
    );


const quickSquadSummaryTeamColorElement =
    document.getElementById(
        "quick-squad-summary-team-color"
    );


const quickSquadSummaryFormationElement =
    document.getElementById(
        "quick-squad-summary-formation"
    );


const quickSquadSummaryBudgetElement =
    document.getElementById(
        "quick-squad-summary-budget"
    );

const quickSquadSummaryTotalPriceElement =
    document.getElementById(
        "quick-squad-summary-total-price"
    );


const quickSquadSummarySalaryElement =
    document.getElementById(
        "quick-squad-summary-salary"
    );


const quickSquadGenerateButtonElement =
    document.getElementById(
        "quick-squad-generate-button"
    );

const quickSquadPlayerModal = document.getElementById(
    "quick-squad-player-modal"
);

const quickSquadPlayerModalBody = document.getElementById(
    "quick-squad-player-modal-body"
);

const quickSquadPlayerSaveButton = document.getElementById(
    "quick-squad-player-save-button"
);

let currentQuickSquadPlayerModalData = null;


// 현재 화면에 표시 중인 포메이션 11자리
let currentQuickSquadSlots = [];

let currentQuickSquadResult = null;

let quickSquadLocksController = null;

let quickSquadBudgetController = null;

let quickSquadTeamColors = [];


// =========================================
// ACTIVE TEAM COLOR TOOLTIP STATE
// =========================================

let currentQuickSquadActiveTeamColors = [];

let quickSquadTeamColorTooltipTarget = null;


const QUICK_SQUAD_CONDITION_STORAGE_KEY =
    "fcl.quick-squad.conditions.v1";


function readQuickSquadConditions() {

    try {

        const raw =
            localStorage.getItem(
                QUICK_SQUAD_CONDITION_STORAGE_KEY
            );


        if (!raw) {
            return null;
        }


        const data =
            JSON.parse(
                raw
            );


        if (
            !data
            ||
            typeof data !== "object"
        ) {
            return null;
        }


        return data;

    } catch {

        return null;
    }
}


function saveQuickSquadConditions() {

    try {

        const data = {
            team_color_id:
                quickSquadTeamColorElement
                    ?.value
                ??
                "",

            budget:
                quickSquadBudgetElement
                    ?.value
                ??
                "",

            enhancement_grade:
                quickSquadEnhancementGradeElement
                    ?.value
                ??
                "auto",

            formation:
                quickSquadFormationElement
                    ?.value
                ??
                "",

            recommendation_mode:
                getQuickSquadRecommendationMode(),
        };


        localStorage.setItem(
            QUICK_SQUAD_CONDITION_STORAGE_KEY,
            JSON.stringify(
                data
            )
        );

    } catch (error) {

        console.warn(
            "퀵 스쿼드 조건 저장 실패:",
            error
        );
    }
}


function restoreQuickSquadConditions() {

    const saved =
        readQuickSquadConditions();


    if (!saved) {
        return false;
    }


    if (
        saved.team_color_id
        &&
        [
            ...quickSquadTeamColorElement.options,
        ].some(
            option =>
                option.value
                ===
                String(
                    saved.team_color_id
                )
        )
    ) {

        quickSquadTeamColorElement.value =
            String(
                saved.team_color_id
            );
    }


    if (
        saved.formation
        &&
        [
            ...quickSquadFormationElement.options,
        ].some(
            option =>
                option.value
                ===
                String(
                    saved.formation
                )
        )
    ) {

        quickSquadFormationElement.value =
            String(
                saved.formation
            );
    }


    if (
        quickSquadBudgetElement
        &&
        saved.budget !== undefined
    ) {

        quickSquadBudgetElement.value =
            String(
                saved.budget
                ??
                ""
            );
    }


    if (
        quickSquadEnhancementGradeElement
        &&
        saved.enhancement_grade
        &&
        [
            ...quickSquadEnhancementGradeElement.options,
        ].some(
            option =>
                option.value
                ===
                String(
                    saved.enhancement_grade
                )
        )
    ) {

        quickSquadEnhancementGradeElement.value =
            String(
                saved.enhancement_grade
            );
    }


    const recommendationMode =
        [
            "meta",
            "performance",
            "value",
        ].includes(
            saved.recommendation_mode
        )
            ? saved.recommendation_mode
            : "meta";


    document
        .querySelectorAll(
            (
                ".quick-squad-"
                +
                "recommendation-mode-button"
            )
        )
        .forEach(
            button => {

                const selected =
                    (
                        button.dataset
                            .quickSquadRecommendationMode
                        ===
                        recommendationMode
                    );


                button.classList.toggle(
                    "is-active",
                    selected
                );

                button.setAttribute(
                    "aria-pressed",
                    String(
                        selected
                    )
                );
            }
        );

    saveQuickSquadConditions();


    renderQuickSquadFormation();
    updateQuickSquadConditionSummary();


    return true;
}

// =========================================
// 기존에 위치를 확정한 포메이션
// =========================================

const QUICK_SQUAD_FORMATION_OVERRIDES = {

    "4-3-3": [

        {
            position: "LW",
            left: 20,
            top: 16,
        },

        {
            position: "ST",
            left: 50,
            top: 12,
        },

        {
            position: "RW",
            left: 80,
            top: 16,
        },


        {
            position: "LCM",
            left: 27,
            top: 39,
        },

        {
            position: "CM",
            left: 50,
            top: 43,
        },

        {
            position: "RCM",
            left: 73,
            top: 39,
        },


        {
            position: "LB",
            left: 15,
            top: 67,
        },

        {
            position: "LCB",
            left: 37,
            top: 64,
        },

        {
            position: "RCB",
            left: 63,
            top: 64,
        },

        {
            position: "RB",
            left: 85,
            top: 67,
        },


        {
            position: "GK",
            left: 50,
            top: 86,
        },

    ],


    "4-2-3-1": [

        {
            position: "ST",
            left: 50,
            top: 12,
        },


        {
            position: "LAM",
            left: 22,
            top: 29,
        },

        {
            position: "CAM",
            left: 50,
            top: 26,
        },

        {
            position: "RAM",
            left: 78,
            top: 29,
        },


        {
            position: "LDM",
            left: 37,
            top: 48,
        },

        {
            position: "RDM",
            left: 63,
            top: 48,
        },


        {
            position: "LB",
            left: 15,
            top: 68,
        },

        {
            position: "LCB",
            left: 37,
            top: 65,
        },

        {
            position: "RCB",
            left: 63,
            top: 65,
        },

        {
            position: "RB",
            left: 85,
            top: 68,
        },


        {
            position: "GK",
            left: 50,
            top: 86,
        },

    ],


    "4-4-2": [

        {
            position: "LS",
            left: 38,
            top: 14,
        },

        {
            position: "RS",
            left: 62,
            top: 14,
        },


        {
            position: "LM",
            left: 16,
            top: 37,
        },

        {
            position: "LCM",
            left: 38,
            top: 41,
        },

        {
            position: "RCM",
            left: 62,
            top: 41,
        },

        {
            position: "RM",
            left: 84,
            top: 37,
        },


        {
            position: "LB",
            left: 15,
            top: 68,
        },

        {
            position: "LCB",
            left: 37,
            top: 65,
        },

        {
            position: "RCB",
            left: 63,
            top: 65,
        },

        {
            position: "RB",
            left: 85,
            top: 68,
        },


        {
            position: "GK",
            left: 50,
            top: 86,
        },

    ],

};


// =========================================
// POSITION GROUP
// =========================================

function getQuickSquadPositionGroup(
    position
) {

    const attackerPositions =
        new Set([
            "ST",
            "CF",
            "LW",
            "RW",
            "LS",
            "RS",
        ]);


    const midfielderPositions =
        new Set([
            "CAM",
            "LAM",
            "RAM",
            "CM",
            "LCM",
            "RCM",
            "CDM",
            "LDM",
            "RDM",
            "LM",
            "RM",
        ]);


    const defenderPositions =
        new Set([
            "CB",
            "LCB",
            "RCB",
            "LB",
            "RB",
            "LWB",
            "RWB",
        ]);


    if (
        attackerPositions.has(
            position
        )
    ) {
        return "fw";
    }


    if (
        midfielderPositions.has(
            position
        )
    ) {
        return "mf";
    }


    if (
        defenderPositions.has(
            position
        )
    ) {
        return "df";
    }


    return "gk";
}


// =========================================
// GENERIC FORMATION POSITION
// =========================================

const QUICK_SQUAD_LEFT_POSITIONS = {

    1:
        [50],

    2:
        [
            36,
            64,
        ],

    3:
        [
            22,
            50,
            78,
        ],

    4:
        [
            14,
            38,
            62,
            86,
        ],

    5:
        [
            10,
            30,
            50,
            70,
            90,
        ],

};


function getQuickSquadDefenseNames(
    count
) {

    const names = {

        3:
            [
                "LCB",
                "CB",
                "RCB",
            ],

        4:
            [
                "LB",
                "LCB",
                "RCB",
                "RB",
            ],

        5:
            [
                "LWB",
                "LCB",
                "CB",
                "RCB",
                "RWB",
            ],

    };


    return (
        names[
            count
        ]
        ??
        []
    );
}


function getQuickSquadAttackNames(
    count
) {

    const names = {

        1:
            [
                "ST",
            ],

        2:
            [
                "LS",
                "RS",
            ],

        3:
            [
                "LW",
                "ST",
                "RW",
            ],

        4:
            [
                "LW",
                "LS",
                "RS",
                "RW",
            ],

    };


    return (
        names[
            count
        ]
        ??
        []
    );
}


function getQuickSquadMidfieldNames(
    count,
    midfieldType
) {

    const centralNames = {

        1:
            [
                "CM",
            ],

        2:
            [
                "LCM",
                "RCM",
            ],

        3:
            [
                "LCM",
                "CM",
                "RCM",
            ],

        4:
            [
                "LM",
                "LCM",
                "RCM",
                "RM",
            ],

        5:
            [
                "LM",
                "LCM",
                "CAM",
                "RCM",
                "RM",
            ],

    };


    const defensiveNames = {

        1:
            [
                "CDM",
            ],

        2:
            [
                "LDM",
                "RDM",
            ],

        3:
            [
                "LCM",
                "CDM",
                "RCM",
            ],

        4:
            [
                "LM",
                "LDM",
                "RDM",
                "RM",
            ],

        5:
            [
                "LM",
                "LCM",
                "CDM",
                "RCM",
                "RM",
            ],

    };


    const attackingNames = {

        1:
            [
                "CAM",
            ],

        2:
            [
                "LAM",
                "RAM",
            ],

        3:
            [
                "LAM",
                "CAM",
                "RAM",
            ],

        4:
            [
                "LM",
                "LAM",
                "RAM",
                "RM",
            ],

        5:
            [
                "LM",
                "LAM",
                "CAM",
                "RAM",
                "RM",
            ],

    };


    if (
        midfieldType
        ===
        "defensive"
    ) {

        return (
            defensiveNames[
                count
            ]
            ??
            []
        );
    }


    if (
        midfieldType
        ===
        "attacking"
    ) {

        return (
            attackingNames[
                count
            ]
            ??
            []
        );
    }


    return (
        centralNames[
            count
        ]
        ??
        []
    );
}


function buildQuickSquadGenericFormation(
    formation
) {

    const normalizedFormation =
        String(
            formation
            ??
            ""
        )
            .replace(
                /\(2\)$/,
                ""
            );


    const lineCounts =
        normalizedFormation
            .split(
                "-"
            )
            .map(
                value =>
                    Number(
                        value
                    )
            );


    if (
        lineCounts.length < 2
        ||
        lineCounts.some(
            value =>
                !Number.isInteger(
                    value
                )
        )
        ||
        lineCounts.reduce(
            (
                total,
                value
            ) =>
                total
                +
                value,
            0
        )
        !==
        10
    ) {

        return (
            QUICK_SQUAD_FORMATION_OVERRIDES[
                "4-3-3"
            ]
        );
    }


    const slots = [];


    const lastLineIndex =
        lineCounts.length
        -
        1;


    lineCounts.forEach(
        (
            count,
            lineIndex
        ) => {

            const leftPositions =
                QUICK_SQUAD_LEFT_POSITIONS[
                    count
                ]
                ??
                [];


            const top =
                (
                    lineCounts.length
                    ===
                    1
                )
                    ? 50

                    : (
                        68
                        -
                        (
                            54
                            *
                            (
                                lineIndex
                                /
                                lastLineIndex
                            )
                        )
                    );


            let positionNames = [];


            if (
                lineIndex
                ===
                0
            ) {

                positionNames =
                    getQuickSquadDefenseNames(
                        count
                    );

            } else if (
                lineIndex
                ===
                lastLineIndex
            ) {

                positionNames =
                    getQuickSquadAttackNames(
                        count
                    );

            } else {

                const midfieldLineCount =
                    lineCounts.length
                    -
                    2;


                let midfieldType =
                    "central";


                if (
                    midfieldLineCount
                    >
                    1
                ) {

                    if (
                        lineIndex
                        ===
                        1
                    ) {

                        midfieldType =
                            "defensive";

                    } else if (
                        lineIndex
                        ===
                        lastLineIndex
                        -
                        1
                    ) {

                        midfieldType =
                            "attacking";
                    }
                }


                positionNames =
                    getQuickSquadMidfieldNames(
                        count,
                        midfieldType
                    );
            }


            leftPositions.forEach(
                (
                    left,
                    playerIndex
                ) => {

                    slots.push(
                        {
                            position:
                                (
                                    positionNames[
                                        playerIndex
                                    ]
                                    ??
                                    "CM"
                                ),

                            left:
                                left,

                            top:
                                top,
                        }
                    );
                }
            );
        }
    );


    slots.push(
        {
            position:
                "GK",

            left:
                50,

            top:
                86,
        }
    );


    return slots;
}

function getQuickSquadFormationSlots(
    formation
) {

    return (
        QUICK_SQUAD_FORMATION_OVERRIDES[
            formation
        ]
        ??
        buildQuickSquadGenericFormation(
            formation
        )
    );

}


// =========================================
// PLACEHOLDER
// =========================================

function createQuickSquadPlaceholderHtml(
    slot
) {

    const positionGroup =
        getQuickSquadPositionGroup(
            slot.position
        );


    return `
        <div
            class="quick-squad-player-slot"
            style="
                left: ${slot.left}%;
                top: ${slot.top}%;
            "
        >

            <div
                class="
                    quick-squad-player-card
                    quick-squad-player-card-empty
                "
            >

                <span
                    class="
                        quick-squad-player-position
                        quick-squad-player-position-${positionGroup}
                    "
                >
                    ${slot.position}
                </span>


                <div
                    class="quick-squad-player-placeholder"
                >
                    ?
                </div>


                <strong
                    class="quick-squad-player-name"
                >
                    추천 대기
                </strong>

            </div>

        </div>
    `;
}


// =========================================
// RENDER FORMATION
// =========================================

function renderQuickSquadFormation() {

    if (
        !quickSquadFormationElement
        ||
        !quickSquadPlayerLayerElement
    ) {
        return;
    }


    const formation =
        quickSquadFormationElement.value
        ||
        "4-3-3";


    const slots =
        getQuickSquadFormationSlots(
            formation
        );


    currentQuickSquadSlots =
        slots;

    currentQuickSquadResult =
        null;

    currentQuickSquadActiveTeamColors =
    [];

    hideQuickSquadTeamColorTooltip();

    if (
        quickSquadActiveTeamColorsElement
    ) {

        quickSquadActiveTeamColorsElement
            .innerHTML =
                "";


        quickSquadActiveTeamColorsElement
            .hidden =
                true;
    }

    quickSquadPlayerLayerElement
        .innerHTML =
            slots
                .map(
                    createQuickSquadPlaceholderHtml
                )
                .join(
                    ""
                );


    if (
        quickSquadFormationTitleElement
    ) {

        quickSquadFormationTitleElement
            .textContent =
                formation;
    }


    if (
        quickSquadSummaryFormationElement
    ) {

        quickSquadSummaryFormationElement
            .textContent =
                formation;
    }

    quickSquadLocksController?.syncFormation();

    quickSquadBudgetController?.clearResult();

}


// =========================================
// TEAM COLORS
// =========================================

function normalizeQuickSquadTeamColorSearch(
    value
) {

    return (
        String(
            value
            ??
            ""
        )
            .trim()
            .toLocaleLowerCase(
                "ko-KR"
            )
            .replace(
                /\s+/g,
                ""
            )
    );
}


function renderQuickSquadTeamColorOptions() {

    if (
        !quickSquadTeamColorElement
    ) {
        return;
    }


    const selectedValue =
        String(
            quickSquadTeamColorElement.value
            ??
            ""
        );


    const query =
        normalizeQuickSquadTeamColorSearch(
            quickSquadTeamColorSearchElement
                ?.value
            ??
            ""
        );


    let visibleTeams =
        query
            ? quickSquadTeamColors.filter(
                team =>
                    normalizeQuickSquadTeamColorSearch(
                        team.team_name
                    )
                        .includes(
                            query
                        )
            )
            : [
                ...quickSquadTeamColors,
            ];


    // 검색 중이어도 현재 선택된 팀컬러는
    // select에서 사라지지 않게 유지한다.
    if (
        selectedValue
        &&
        !visibleTeams.some(
            team =>
                String(
                    team.team_color_id
                )
                ===
                selectedValue
        )
    ) {

        const selectedTeam =
            quickSquadTeamColors.find(
                team =>
                    String(
                        team.team_color_id
                    )
                    ===
                    selectedValue
            );


        if (
            selectedTeam
        ) {

            visibleTeams = [
                selectedTeam,
                ...visibleTeams,
            ];
        }
    }


    quickSquadTeamColorElement
        .innerHTML =
            "";


    const defaultOption =
        document.createElement(
            "option"
        );


    defaultOption.value =
        "";


    defaultOption.textContent =
        query
            ? (
                visibleTeams.length
                    ? "검색 결과에서 선택"
                    : "검색 결과 없음"
            )
            : "팀컬러 선택";


    quickSquadTeamColorElement
        .appendChild(
            defaultOption
        );


    visibleTeams.forEach(
        team => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                String(
                    team.team_color_id
                );


            option.textContent =
                team.team_name;


            option.dataset.teamName =
                team.team_name;


            quickSquadTeamColorElement
                .appendChild(
                    option
                );
        }
    );


    if (
        selectedValue
        &&
        [
            ...quickSquadTeamColorElement.options,
        ].some(
            option =>
                option.value
                ===
                selectedValue
        )
    ) {

        quickSquadTeamColorElement.value =
            selectedValue;
    }
}

async function loadQuickSquadTeamColors() {

    if (
        !quickSquadTeamColorElement
    ) {
        return;
    }


    quickSquadTeamColorElement.disabled =
        true;


    try {

        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    "/api/player-database/filters"
                )
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(
                (
                    data.detail
                    ??
                    "팀컬러를 불러오지 못했습니다."
                )
            );
        }


        quickSquadTeamColors =
            (
                data.teams
                ??
                []
            )
                .map(
                    team => ({
                        team_color_id:
                            Number(
                                team.team_color_id
                            ),

                        team_name:
                            String(
                                team.team_name
                                ??
                                ""
                            ),
                    })
                )
                .filter(
                    team =>
                        Number.isInteger(
                            team.team_color_id
                        )
                        &&
                        team.team_color_id > 0
                        &&
                        team.team_name
                );


            renderQuickSquadTeamColorOptions();


    } catch (error) {

        console.error(
            error
        );


        quickSquadTeamColorElement
            .innerHTML =
                `
                    <option value="">
                        팀컬러 조회 실패
                    </option>
                `;

    } finally {

        quickSquadTeamColorElement.disabled =
            false;
    }

}


// =========================================
// OFFICIAL FORMATIONS
// =========================================

async function loadQuickSquadFormations() {

    if (
        !quickSquadFormationElement
    ) {
        return;
    }


    quickSquadFormationElement.disabled =
        true;


    try {

        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    "/api/quick-squad/formations"
                )
            );


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(
                (
                    data.detail
                    ??
                    "포메이션을 불러오지 못했습니다."
                )
            );
        }


        const formations =
            (
                data.formations
                ??
                []
            );


        quickSquadFormationElement
            .innerHTML =
                "";


        [
            3,
            4,
            5,
        ].forEach(
            backCount => {

                const groupFormations =
                    formations.filter(
                        item =>
                            Number(
                                item.back_count
                            )
                            ===
                            backCount
                    );


                if (
                    groupFormations.length
                    ===
                    0
                ) {
                    return;
                }


                const optionGroup =
                    document.createElement(
                        "optgroup"
                    );


                optionGroup.label =
                    `${backCount} Back`;


                groupFormations.forEach(
                    item => {

                        const option =
                            document.createElement(
                                "option"
                            );


                        option.value =
                            item.name;


                        option.textContent =
                            item.name;


                        optionGroup.appendChild(
                            option
                        );
                    }
                );


                quickSquadFormationElement
                    .appendChild(
                        optionGroup
                    );
            }
        );


        const has433 =
            formations.some(
                item =>
                    item.name
                    ===
                    "4-3-3"
            );


        if (
            has433
        ) {

            quickSquadFormationElement.value =
                "4-3-3";

        } else if (
            formations.length
            >
            0
        ) {

            quickSquadFormationElement.value =
                formations[
                    0
                ].name;
        }


        renderQuickSquadFormation();


    } catch (error) {

        console.error(
            error
        );


        quickSquadFormationElement
            .innerHTML =
                `
                    <option value="4-3-3">
                        4-3-3
                    </option>
                `;


        renderQuickSquadFormation();


    } finally {

        quickSquadFormationElement.disabled =
            false;
    }

}

// =========================================
// QUICK SQUAD RESULT
// =========================================

function escapeQuickSquadHtml(
    value
) {

    return String(
        value
        ??
        ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            "\"",
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );

}


function formatQuickSquadBp(
    value
) {

    const price =
        Number(
            value
            ??
            0
        );


    if (
        !Number.isFinite(
            price
        )
        ||
        price <= 0
    ) {

        return "-";
    }


    if (
        price
        >=
        1_000_000_000_000
    ) {

        const trillion =
            Math.floor(
                price
                /
                1_000_000_000_000
            );


        const hundredMillion =
            Math.floor(
                (
                    price
                    %
                    1_000_000_000_000
                )
                /
                100_000_000
            );


        if (
            hundredMillion > 0
        ) {

            return (
                `${trillion}조 `
                +
                `${hundredMillion.toLocaleString("ko-KR")}억 BP`
            );
        }


        return (
            `${trillion}조 BP`
        );
    }


    if (
        price
        >=
        100_000_000
    ) {

        const hundredMillion =
            (
                price
                /
                100_000_000
            );


        return (
            hundredMillion
                .toLocaleString(
                    "ko-KR",
                    {
                        maximumFractionDigits:
                            2,
                    }
                )
            +
            "억 BP"
        );
    }


    if (
        price
        >=
        10_000
    ) {

        return (
            Math.floor(
                price
                /
                10_000
            )
                .toLocaleString(
                    "ko-KR"
                )
            +
            "만 BP"
        );
    }


    return (
        price
            .toLocaleString(
                "ko-KR"
            )
        +
        " BP"
    );

}

// =========================================
// ACTIVE TEAM COLORS
// =========================================

function createQuickSquadActiveTeamColorTitle(
    teamColor
) {

    const teamName =
        String(
            teamColor.team_name
            ?? ""
        );


    const stage =
        Number(
            teamColor.stage
            ?? 0
        );


    const matchedPlayers =
        Number(
            teamColor.matched_players
            ?? 0
        );


    const requiredPlayers =
        Number(
            teamColor.required_players
            ?? 0
        );


    const effects =
        Array.isArray(
            teamColor.effects
        )
            ? teamColor.effects
            : [];


    const effectText =
        effects
            .map(
                effect => {

                    const statName =
                        String(
                            effect.stat_name
                            ?? ""
                        );


                    const bonus =
                        Number(
                            effect.bonus
                            ?? 0
                        );


                    if (!statName) {
                        return "";
                    }


                    return (
                        `${statName} `
                        +
                        `${bonus >= 0 ? "+" : ""}`
                        +
                        `${bonus}`
                    );
                }
            )
            .filter(Boolean)
            .join(" · ");


    return [
        teamName,

        stage > 0
            ? `${stage}단계`
            : "",

        (
            matchedPlayers > 0
            &&
            requiredPlayers > 0
        )
            ? (
                `${matchedPlayers}명 매칭`
                +
                ` / ${requiredPlayers}명 필요`
            )
            : "",

        effectText,
    ]
        .filter(Boolean)
        .join(" · ");
}


function createQuickSquadActiveTeamColorHtml(
    teamColor,
    index
) {

    const teamName =
        escapeQuickSquadHtml(
            teamColor.team_name
            ?? ""
        );


    const iconUrl =
        escapeQuickSquadHtml(
            teamColor.icon_url
            ?? ""
        );


    const stage =
        Number(
            teamColor.stage
            ?? 0
        );


    const category =
        String(
            teamColor.category
            ?? ""
        );


    const isSelected =
        teamColor.is_selected_team_color
        === true;


    const ariaLabel =
        escapeQuickSquadHtml(
            createQuickSquadActiveTeamColorTitle(
                teamColor
            )
        );


    return `
        <button
            type="button"
            class="
                quick-squad-active-team-color
                ${
                    isSelected
                        ? "is-selected"
                        : ""
                }
                ${
                    category === "enhance"
                        ? "is-enhancement"
                        : ""
                }
            "
            data-quick-squad-team-color-index="${index}"
            aria-label="${ariaLabel}"
        >

            ${
                iconUrl
                    ? `
                        <img
                            src="${iconUrl}"
                            alt=""
                            class="
                                quick-squad-active-team-color-icon
                            "
                            loading="lazy"
                        >
                    `
                    : `
                        <span
                            class="
                                quick-squad-active-team-color-fallback
                            "
                        >
                            TC
                        </span>
                    `
            }


            ${
                stage > 0
                    ? `
                        <span
                            class="
                                quick-squad-active-team-color-stage
                            "
                        >
                            ${stage}
                        </span>
                    `
                    : ""
            }

        </button>
    `;
}

// =========================================
// ACTIVE TEAM COLOR CUSTOM TOOLTIP
// =========================================

function getQuickSquadTeamColorTooltipElement() {

    let tooltipElement =
        document.getElementById(
            "quick-squad-team-color-tooltip"
        );


    if (tooltipElement) {
        return tooltipElement;
    }


    tooltipElement =
        document.createElement(
            "div"
        );


    tooltipElement.id =
        "quick-squad-team-color-tooltip";


    tooltipElement.className =
        "quick-squad-team-color-tooltip";


    tooltipElement.hidden =
        true;


    tooltipElement.setAttribute(
        "role",
        "tooltip"
    );


    document.body.appendChild(
        tooltipElement
    );


    return tooltipElement;
}

function escapeQuickSquadTeamColorTooltipHtml(
    value
) {

    return String(
        value
        ??
        ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            "\"",
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


function getQuickSquadTeamColorMatchedPlayers(
    teamColor
) {

    const matchedSpIds =
        new Set(
            (
                Array.isArray(
                    teamColor
                        ?.matched_sp_ids
                )
                    ? (
                        teamColor
                            .matched_sp_ids
                    )
                    : []
            )
                .map(
                    value =>
                        Number(
                            value
                        )
                )
                .filter(
                    value =>
                        Number
                            .isSafeInteger(
                                value
                            )
                )
        );


    if (
        matchedSpIds.size
        === 0
    ) {

        return [];
    }


    const players =
        Array.isArray(
            currentQuickSquadResult
                ?.players
        )
            ? (
                currentQuickSquadResult
                    .players
            )
            : [];


    return players
        .filter(
            player =>
                matchedSpIds.has(
                    Number(
                        player.sp_id
                    )
                )
        );
}


function getQuickSquadPlayerSeasonIconUrl(
    player
) {

    const explicitSeasonId =
        Number(
            player?.season_id
        );


    const spId =
        Number(
            player?.sp_id
        );


    const derivedSeasonId =
        Number.isSafeInteger(
            spId
        )
            ? Math.floor(
                spId
                /
                1_000_000
            )
            : 0;


    const seasonId =
        (
            Number.isSafeInteger(
                explicitSeasonId
            )
            &&
            explicitSeasonId > 0
        )
            ? explicitSeasonId
            : derivedSeasonId;


    if (
        !seasonId
    ) {

        return "";
    }


    return (
        `${apiBaseUrl}`
        +
        "/api/fconline/"
        +
        "metadata/seasons/"
        +
        `${seasonId}/image`
    );
}


function createQuickSquadTeamColorTooltipHtml(
    teamColor
) {

    const escape =
        escapeQuickSquadTeamColorTooltipHtml;


    const teamName =
        escape(
            teamColor
                ?.team_name
            ??
            "팀컬러"
        );


    const iconUrl =
        escape(
            teamColor
                ?.icon_url
            ??
            ""
        );


    const stage =
        Number(
            teamColor
                ?.stage
            ??
            teamColor
                ?.active_stage
            ??
            0
        );


    const matchedPlayersCount =
        Number(
            teamColor
                ?.matched_players
            ??
            0
        );


    const requiredPlayers =
        Number(
            teamColor
                ?.required_players
            ??
            0
        );


    const effects =
        Array.isArray(
            teamColor
                ?.effects
        )
            ? (
                teamColor
                    .effects
            )
            : [];


    const matchedPlayers =
        getQuickSquadTeamColorMatchedPlayers(
            teamColor
        );


    const effectsHtml =
        effects
            .map(
                effect => {

                    const statName =
                        escape(
                            effect
                                ?.stat_name
                            ??
                            effect
                                ?.stat_key
                            ??
                            ""
                        );


                    const bonus =
                        Number(
                            effect
                                ?.bonus
                            ??
                            0
                        );


                    if (
                        !statName
                        ||
                        !bonus
                    ) {

                        return "";
                    }


                    return `
                        <span>
                            ${statName}
                            +${bonus}
                        </span>
                    `;
                }
            )
            .filter(
                Boolean
            )
            .join(
                ""
            );


    const playerRowsHtml =
        matchedPlayers
            .map(
                player => {

                    const seasonIconUrl =
                        escape(
                            getQuickSquadPlayerSeasonIconUrl(
                                player
                            )
                        );


                    const playerName =
                        escape(
                            player
                                ?.player_name
                            ??
                            "-"
                        );


                    const playerOvr =
                        Number(
                            player
                                ?.ovr
                        );


                    return `
                        <div
                            class="
                                quick-squad-team-color-tooltip-player
                            "
                        >

                            <span
                                class="
                                    quick-squad-team-color-tooltip-player-season
                                "
                            >

                                ${
                                    seasonIconUrl
                                        ? `
                                            <img
                                                src="${seasonIconUrl}"
                                                alt=""
                                                loading="lazy"
                                            >
                                        `
                                        : ""
                                }

                            </span>


                            <span
                                class="
                                    quick-squad-team-color-tooltip-player-name
                                "
                            >
                                ${playerName}
                            </span>


                            <strong
                                class="
                                    quick-squad-team-color-tooltip-player-ovr
                                "
                            >
                                ${
                                    Number.isFinite(
                                        playerOvr
                                    )
                                        ? playerOvr
                                        : "-"
                                }
                            </strong>

                        </div>
                    `;
                }
            )
            .join(
                ""
            );


    return `
        <div
            class="
                quick-squad-team-color-tooltip-header
            "
        >

            ${
                iconUrl
                    ? `
                        <img
                            class="
                                quick-squad-team-color-tooltip-icon
                            "
                            src="${iconUrl}"
                            alt=""
                        >
                    `
                    : ""
            }


            <div
                class="
                    quick-squad-team-color-tooltip-title
                "
            >

                <strong>
                    ${teamName}
                </strong>


                ${
                    stage > 0
                        ? `
                            <small>
                                ${stage}단계
                            </small>
                        `
                        : ""
                }

            </div>

        </div>


        <div
            class="
                quick-squad-team-color-tooltip-meta
            "
        >

            ${
                matchedPlayersCount > 0
                    ? `
                        <span>
                            매칭 ${matchedPlayersCount}명
                        </span>
                    `
                    : ""
            }


            ${
                requiredPlayers > 0
                    ? `
                        <span>
                            필요 ${requiredPlayers}명
                        </span>
                    `
                    : ""
            }

        </div>


        ${
            effectsHtml
                ? `
                    <div
                        class="
                            quick-squad-team-color-tooltip-effects
                        "
                    >
                        ${effectsHtml}
                    </div>
                `
                : ""
        }


        ${
            playerRowsHtml
                ? `
                    <div
                        class="
                            quick-squad-team-color-tooltip-player-list
                        "
                    >
                        ${playerRowsHtml}
                    </div>
                `
                : ""
        }
    `;
}


function positionQuickSquadTeamColorTooltip(
    targetElement,
    tooltipElement
) {

    const targetRect =
        targetElement.getBoundingClientRect();


    tooltipElement.style.visibility =
        "hidden";

    tooltipElement.style.left =
        "0px";

    tooltipElement.style.top =
        "0px";

    tooltipElement.hidden =
        false;


    const tooltipRect =
        tooltipElement.getBoundingClientRect();


    const viewportWidth =
        document.documentElement.clientWidth;


    const viewportHeight =
        window.innerHeight;


    const margin =
        10;


    const gap =
        8;


    let left =
        (
            targetRect.right
            -
            tooltipRect.width
        );


    if (
        left < margin
    ) {

        left =
            margin;
    }


    if (
        left
        +
        tooltipRect.width
        >
        viewportWidth
        -
        margin
    ) {

        left =
            (
                viewportWidth
                -
                tooltipRect.width
                -
                margin
            );
    }


    let top =
        (
            targetRect.bottom
            +
            gap
        );


    if (
        top
        +
        tooltipRect.height
        >
        viewportHeight
        -
        margin
    ) {

        top =
            (
                targetRect.top
                -
                tooltipRect.height
                -
                gap
            );
    }


    if (
        top < margin
    ) {

        top =
            margin;
    }


    tooltipElement.style.left =
        `${Math.round(left)}px`;


    tooltipElement.style.top =
        `${Math.round(top)}px`;


    tooltipElement.style.visibility =
        "";
}


function showQuickSquadTeamColorTooltip(
    targetElement
) {

    const index =
        Number(
            targetElement.dataset
                .quickSquadTeamColorIndex
        );


    if (
        !Number.isInteger(index)
        ||
        index < 0
        ||
        index
        >=
        currentQuickSquadActiveTeamColors.length
    ) {

        return;
    }


    const teamColor =
        currentQuickSquadActiveTeamColors[
            index
        ];


    const tooltipElement =
        getQuickSquadTeamColorTooltipElement();


    if (
        quickSquadTeamColorTooltipTarget
        &&
        quickSquadTeamColorTooltipTarget
        !==
        targetElement
    ) {

        quickSquadTeamColorTooltipTarget
            .classList
            .remove(
                "is-tooltip-open"
            );
    }


    quickSquadTeamColorTooltipTarget =
        targetElement;


    targetElement.classList.add(
        "is-tooltip-open"
    );


    tooltipElement.innerHTML =
        createQuickSquadTeamColorTooltipHtml(
            teamColor
        );


    positionQuickSquadTeamColorTooltip(
        targetElement,
        tooltipElement
    );
}


function hideQuickSquadTeamColorTooltip() {

    const tooltipElement =
        document.getElementById(
            "quick-squad-team-color-tooltip"
        );


    if (tooltipElement) {

        tooltipElement.hidden =
            true;
    }


    if (
        quickSquadTeamColorTooltipTarget
    ) {

        quickSquadTeamColorTooltipTarget
            .classList
            .remove(
                "is-tooltip-open"
            );
    }


    quickSquadTeamColorTooltipTarget =
        null;
}


function renderQuickSquadActiveTeamColors(
    data
) {

    if (
        !quickSquadActiveTeamColorsElement
    ) {
        return;
    }

    hideQuickSquadTeamColorTooltip();


    currentQuickSquadActiveTeamColors =
        [];


    const activeTeamColors =
        Array.isArray(
            data?.active_team_colors
        )
            ? [
                ...data.active_team_colors,
            ]
            : [];


    if (
        activeTeamColors.length
        === 0
    ) {

        quickSquadActiveTeamColorsElement
            .innerHTML =
                "";


        quickSquadActiveTeamColorsElement
            .hidden =
                true;


        return;
    }


    // 선택 팀컬러 → 강화 팀컬러 → 나머지 순서
    activeTeamColors.sort(
        (
            a,
            b
        ) => {

            const aSelected =
                a.is_selected_team_color === true
                    ? 1
                    : 0;


            const bSelected =
                b.is_selected_team_color === true
                    ? 1
                    : 0;


            if (
                aSelected
                !==
                bSelected
            ) {

                return (
                    bSelected
                    -
                    aSelected
                );
            }


            const aEnhancement =
                a.category === "enhance"
                    ? 1
                    : 0;


            const bEnhancement =
                b.category === "enhance"
                    ? 1
                    : 0;


            if (
                aEnhancement
                !==
                bEnhancement
            ) {

                return (
                    bEnhancement
                    -
                    aEnhancement
                );
            }


            return String(
                a.team_name
                ?? ""
            )
                .localeCompare(
                    String(
                        b.team_name
                        ?? ""
                    ),
                    "ko-KR"
                );
        }
    );


    currentQuickSquadActiveTeamColors =
        activeTeamColors;


    quickSquadActiveTeamColorsElement
        .innerHTML =
            activeTeamColors
                .map(
                    (
                        teamColor,
                        index
                    ) =>
                        createQuickSquadActiveTeamColorHtml(
                            teamColor,
                            index
                        )
                )
                .join("");


    quickSquadActiveTeamColorsElement
        .hidden =
            false;
}


function createQuickSquadPlayerHtml(
    player,
    slot,
    index
) {

    const positionGroup =
        getQuickSquadPositionGroup(
            slot.position
        );


    const imageUrl =
        escapeQuickSquadHtml(
            player.image_url
            ??
            ""
        );


    const playerName =
        escapeQuickSquadHtml(
            player.player_name
        );

    const seasonId = [
        player.season_id,
        Math.floor(Number(player.sp_id) / 1_000_000),
    ]
        .map(value => Number(value))
        .find(value =>
            Number.isSafeInteger(value)
            && value > 0
        ) ?? null;

    const seasonImageUrl = seasonId !== null
        ? (
            `${apiBaseUrl}`
            + `/api/fconline/metadata/seasons/${seasonId}/image`
        )
        : "";


    return `
        <div
            class="quick-squad-player-slot"
            style="
                left: ${slot.left}%;
                top: ${slot.top}%;
            "
        >

            <div
                class="quick-squad-player-card ${player.locked ? "quick-squad-player-card-locked" : ""} ${player.generation_restricted === true ? "quick-squad-player-card-generation-restricted" : (player.supply_restricted === true ? "quick-squad-player-card-supply-restricted" : "")}"
                data-quick-squad-player-index="${index}"
            >

                <span
                    class="
                        quick-squad-player-position
                        quick-squad-player-position-${positionGroup}
                    "
                >
                    ${escapeQuickSquadHtml(
                        slot.position
                    )}
                </span>


                <img
                    src="${imageUrl}"
                    alt="${playerName}"
                    class="quick-squad-player-image"
                >

                ${player.locked
                    ? '<span class="qs-lock-field-badge">고정</span>'
                    : ""}

                <div
                    class="quick-squad-player-name-row"
                >

                ${seasonImageUrl
                    ? `
                        <img
                            src="${escapeQuickSquadHtml(seasonImageUrl)}"
                            alt=""
                            class="quick-squad-player-season-icon"
                            loading="lazy"
                        >
                    `
                    : ""
                }


                    <strong
                        class="quick-squad-player-name"
                        title="${playerName}"
                    >
                        ${playerName}
                    </strong>

                </div>


                <div
                    class="quick-squad-player-meta"
                >

                    <span
                        class="quick-squad-player-ovr"
                    >
                        ${Number(
                            player.ovr
                            ??
                            0
                        )}
                    </span>


                    <span
                        class="quick-squad-player-grade"
                    >
                        +${Number(
                            player.grade
                            ??
                            1
                        )}
                    </span>

                </div>

                ${player.manual_saved
                    ? `
                        <span class="quick-squad-player-setting-meta">
                            적${Number(
                                player.adaptation
                                ??
                                DEFAULT_ADAPTATION_LEVEL
                            )}
                            · 팀+${Number(
                                player.team_color_bonus ?? 0
                            )}
                        </span>
                    `
                    : ""
                }


                <span
                    class="quick-squad-player-price"
                >
                    ${formatQuickSquadBp(
                        player.price
                    )}
                </span>

                ${player.generation_restricted === true
                    ? `
                        <span
                            class="quick-squad-generation-restricted-label"
                            title="FC Online 공식 생성 제한 선수"
                        >
                            생성 제한
                        </span>
                    `
                    : (
                        player.supply_restricted === true
                            ? `
                                <span
                                    class="quick-squad-supply-restricted-label"
                                    title="FC Online 공식 공급 제한 클래스"
                                >
                                    공급 제한
                                </span>
                            `
                            : ""
                    )
                }

            </div>

        </div>
    `;

}

function renderQuickSquadLockedPreview(players) {
    const previous = currentQuickSquadResult;

    const context = {
        team_color_id:
            Number(quickSquadTeamColorElement.value) || null,

        team_name:
            quickSquadTeamColorElement
                .selectedOptions[0]?.textContent || "-",

        formation:
            quickSquadFormationElement.value,

        budget_bp:
            Math.round(
                Number(quickSquadBudgetElement.value || 0)
                * 100_000_000
            ),

        salary_cap: 310,
    };

    const sameContext =
        previous
        && previous.formation === context.formation
        && Number(previous.team_color_id)
            === Number(context.team_color_id);

    // 동일한 고정 선수의 단순 재조회라면
    // 완성된 추천 또는 저장 스쿼드를 덮어쓰지 않는다.
    if (
        sameContext
        && !previous.is_draft
        && sameQuickSquadLocks(
            previous.players,
            players
        )
    ) {
        quickSquadBudgetController?.refresh();
        return;
    }

    // 고정 선수만 있는 상태도 11개의 슬롯으로 관리한다.
    // 기존에 저장한 수동 설정이 있다면 같은 선수에 유지한다.
    const draft = createQuickSquadDraft(
        players,
        sameContext ? previous : null,
        context,
        currentQuickSquadSlots
    );

    renderQuickSquadResult(draft);
}


function renderQuickSquadResult(
    data
) {

    const normalized = normalizeQuickSquadResult(
        data,
        currentQuickSquadSlots
    );

    currentQuickSquadResult = normalized;
    data = normalized;

    window.__FCL_QUICK_SQUAD_RESULT__ =
        currentQuickSquadResult;

    renderQuickSquadActiveTeamColors(
        data
    );

    const players = data.players;


    if (
        players.length
        !==
        currentQuickSquadSlots.length
    ) {

        throw new Error(
            "추천 선수 수가 포메이션과 일치하지 않습니다."
        );
    }


    quickSquadPlayerLayerElement.innerHTML =
        players
            .map((player, index) =>
                player
                    ? createQuickSquadPlayerHtml(
                        player,
                        currentQuickSquadSlots[index],
                        index
                    )
                    : createQuickSquadPlaceholderHtml(
                        currentQuickSquadSlots[index]
                    )
            )
            .join("");


    if (
        quickSquadSummaryTeamColorElement
    ) {

        quickSquadSummaryTeamColorElement
            .textContent =
                (
                    data.team_name
                    ??
                    "-"
                );
    }


    if (
        quickSquadSummaryFormationElement
    ) {

        quickSquadSummaryFormationElement
            .textContent =
                (
                    data.formation
                    ??
                    "-"
                );
    }


    if (
        quickSquadSummaryBudgetElement
    ) {

        quickSquadSummaryBudgetElement
            .textContent =
                formatQuickSquadBp(
                    data.budget_bp
                );
    }


    if (
        quickSquadSummaryTotalPriceElement
    ) {

        quickSquadSummaryTotalPriceElement
            .textContent =
                formatQuickSquadBp(
                    data.total_price
                );
    }


    if (
        quickSquadSummarySalaryElement
    ) {

        const totalSalary =
            Number(
                data.total_salary
                ??
                0
            );


        const salaryCap =
            Number(
                data.salary_cap
                ??
                310
            );


        quickSquadSummarySalaryElement
            .textContent =
                (
                    totalSalary
                        .toLocaleString(
                            "ko-KR"
                        )
                    +
                    " / "
                    +
                    salaryCap
                        .toLocaleString(
                            "ko-KR"
                        )
                );
    }


    if (
        quickSquadResultStatusElement
    ) {

        if (quickSquadResultStatusElement) {
            const remaining = Number(
                data.remaining_budget ?? 0
            );

            const prefix = data.is_draft
                ? (
                    data.manually_modified
                        ? "고정 선수 설정 저장됨"
                        : `고정 선수 ${data.locked_count}명 · 나머지 자리 추천 대기`
                )
                : (
                    data.manually_modified
                        ? "저장된 카드 설정"
                        : "추천 완료"
                );

            quickSquadResultStatusElement.textContent =
                remaining < 0
                    ? (
                        `${prefix} · 예산 초과 `
                        + formatQuickSquadBp(
                            Math.abs(remaining)
                        )
                    )
                    : (
                        `${prefix} · 남은 예산 `
                        + formatQuickSquadBp(remaining)
                    );
        }
    }

    quickSquadBudgetController?.showResult(
        data.budget_allocation
    );


}

quickSquadPlayerLayerElement
    ?.addEventListener(
        "click",
        (event) => {

            const card =
                event.target.closest(
                    "[data-quick-squad-player-index]"
                );

            if (!card) {
                return;
            }

            const playerIndex =
                Number(
                    card.dataset.quickSquadPlayerIndex
                );

            if (
                !Number.isInteger(
                    playerIndex
                )
            ) {
                return;
            }

            const player =
                currentQuickSquadResult
                    ?.players
                    ?.[playerIndex];

            if (!player) {
                return;
            }

            openQuickSquadPlayerModal({
                ...player,

                slot_index: playerIndex,

                slot_position:
                    currentQuickSquadSlots[playerIndex].position,
            });
        }
    );


// =========================================
// CONDITION SUMMARY
// =========================================

function updateQuickSquadConditionSummary() {

    if (
        quickSquadSummaryTeamColorElement
    ) {

        const selectedOption =
            quickSquadTeamColorElement
                ?.selectedOptions[
                    0
                ];


        quickSquadSummaryTeamColorElement
            .textContent =
                (
                    quickSquadTeamColorElement
                        ?.value

                    ? (
                        selectedOption
                            ?.dataset
                            ?.teamName
                        ??
                        selectedOption
                            ?.textContent
                        ??
                        "-"
                    )

                    : "-"
                );
    }


    if (
        quickSquadSummaryBudgetElement
    ) {

        const budget =
            Number(
                quickSquadBudgetElement
                    ?.value
                ??
                0
            );


        quickSquadSummaryBudgetElement
            .textContent =
                (
                    budget > 0

                    ? (
                        budget
                            .toLocaleString(
                                "ko-KR"
                            )
                        +
                        "억 BP"
                    )

                    : "-"
                );
    }

}

// =========================================
// QUICK SQUAD
// TEAM COLOR RECALCULATION
// =========================================

async function recalculateQuickSquadTeamColors(
    data
) {

    const players =
        Array.isArray(
            data?.players
        )
            ? data.players
                .filter(
                    Boolean
                )
            : [];


    if (
        players.length
        !== 11
    ) {

        throw new Error(
            "팀컬러를 재계산할 11명의 선수가 없습니다."
        );
    }


    const teamColorId =
        Number(
            data.team_color_id
        );


    if (
        !Number.isSafeInteger(
            teamColorId
        )
        ||
        teamColorId <= 0
    ) {

        throw new Error(
            "현재 스쿼드의 기준 팀컬러를 확인할 수 없습니다."
        );
    }


    const response =
        await fetch(
            (
                `${apiBaseUrl}`
                +
                "/api/quick-squad/"
                +
                "team-colors/recalculate"
            ),
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify(
                        {
                            team_color_id:
                                teamColorId,

                            players:
                                players.map(
                                    player => ({
                                        sp_id:
                                            Number(
                                                player.sp_id
                                            ),

                                        grade:
                                            Number(
                                                player.grade
                                            ),
                                    })
                                ),
                        }
                    ),
            }
        );


    const text =
        await response.text();


    let result =
        null;


    try {

        result =
            text
                ? JSON.parse(
                    text
                )
                : null;

    } catch {

        throw new Error(
            (
                "팀컬러 재계산 응답을 "
                +
                "읽을 수 없습니다."
            )
        );
    }


    if (
        !response.ok
    ) {

        throw new Error(
            (
                typeof result?.detail
                ===
                "string"
            )
                ? result.detail

                : (
                    "팀컬러를 재계산하지 "
                    +
                    "못했습니다."
                )
        );
    }


    if (
        !result
        ||
        !Array.isArray(
            result.active_team_colors
        )
    ) {

        throw new Error(
            "팀컬러 재계산 결과가 올바르지 않습니다."
        );
    }


    return result;
}

async function saveQuickSquadPlayerSettings(
    summary,
    selection
) {

    const data =
        currentQuickSquadResult;


    const slotIndex =
        summary.slot_index;


    if (
        !Number.isInteger(
            slotIndex
        )
        ||
        slotIndex < 0
        ||
        slotIndex >= 11
        ||
        !data?.players?.[
            slotIndex
        ]
        ||
        Number(
            data.players[
                slotIndex
            ].sp_id
        )
        !==
        Number(
            summary.sp_id
        )
    ) {

        throw new Error(
            "현재 스쿼드에서 해당 선수를 찾지 못했습니다."
        );
    }


    const originalPlayer =
        data.players[
            slotIndex
        ];


    // =====================================
    // 1. 먼저 수정한 선수 설정을
    //    로컬 스쿼드에 반영
    //
    // 이 시점의 팀컬러는 아직 이전 판정
    // =====================================

    let next =
        applyQuickSquadPlayerSettings(
            data,
            slotIndex,
            selection,
            currentQuickSquadSlots
        );


    if (
        originalPlayer.locked
    ) {

        next.players[
            slotIndex
        ].locked_grade =
            Number(
                selection.grade
            );
    }


    // =====================================
    // 2. 현재 11명의 SPID + 강화등급으로
    //    서버에서 팀컬러 전체 재판정
    // =====================================

    const teamColorResult =
        await recalculateQuickSquadTeamColors(
            next
        );


    // =====================================
    // 3. 새 팀컬러 판정을 기존 스쿼드에 합침
    // =====================================

    next = {
        ...next,

        active_non_enhancement_team_color_count:
            Number(
                teamColorResult
                    .active_non_enhancement_team_color_count
                ??
                0
            ),

        active_enhancement_team_color_count:
            Number(
                teamColorResult
                    .active_enhancement_team_color_count
                ??
                0
            ),

        active_enhancement_team_colors:
            Array.isArray(
                teamColorResult
                    .active_enhancement_team_colors
            )
                ? (
                    teamColorResult
                        .active_enhancement_team_colors
                )
                : [],

        active_team_color_count:
            Number(
                teamColorResult
                    .active_team_color_count
                ??
                0
            ),

        active_team_colors:
            teamColorResult
                .active_team_colors,
    };


    // =====================================
    // 4. 11명 전체 재정규화
    //
    // 여기서:
    // - 선수별 팀컬러 다시 분리
    // - 세부 능력치 다시 적용
    // - 포지션 OVR 다시 계산
    // =====================================

    next =
        normalizeQuickSquadResult(
            next,
            currentQuickSquadSlots
        );


    if (
        originalPlayer.locked
    ) {

        next.players[
            slotIndex
        ].locked_grade =
            Number(
                selection.grade
            );
    }


    // =====================================
    // 5. 브라우저 저장
    // =====================================

    const savedKey =
        "fcl.quick-squad.saved.v1";


    const previousSaved =
        localStorage.getItem(
            savedKey
        );


    writeSavedQuickSquad(
        next
    );


    // =====================================
    // 6. 고정 선수라면
    //    저장 설정도 최종 계산값으로 갱신
    // =====================================

    try {

        if (
            originalPlayer.locked
        ) {

            quickSquadLocksController
                .updateSavedSettings(
                    next.players[
                        slotIndex
                    ]
                );
        }

    } catch (
        error
    ) {

        // 고정 선수 저장 실패 시
        // 이전 Quick Squad 저장본 복원
        if (
            previousSaved
            === null
        ) {

            localStorage.removeItem(
                savedKey
            );

        } else {

            localStorage.setItem(
                savedKey,
                previousSaved
            );
        }


        throw error;
    }


    // =====================================
    // 7. 화면 갱신
    //
    // renderQuickSquadResult 안에서
    // 팀컬러 아이콘 + XI 전체가 같이 갱신됨
    // =====================================

    renderQuickSquadResult(
        next
    );
}


// =========================================
// QUICK SQUAD PLAYER DETAIL
// =========================================

const quickSquadDetailModal =
    createQuickSquadDetailModal({
        apiBaseUrl:
            apiBaseUrl,

        modal:
            quickSquadPlayerModal,

        body:
            quickSquadPlayerModalBody,

        saveButton:
            quickSquadPlayerSaveButton,

        formatPrice:
            formatQuickSquadBp,

        onSave:
            saveQuickSquadPlayerSettings,
    });


function openQuickSquadPlayerModal(
    player
) {
    return quickSquadDetailModal.open(
        player
    );
}


function closeQuickSquadPlayerModal() {
    quickSquadDetailModal.close();
}

function getQuickSquadRecommendationMode() {

    const activeButton =
        document.querySelector(
            (
                ".quick-squad-"
                +
                "recommendation-mode-button"
                +
                ".is-active"
            )
        );


    const mode =
        (
            activeButton
                ?.dataset
                ?.quickSquadRecommendationMode
            ??
            "meta"
        );


    if (
        ![
            "meta",
            "performance",
            "value",
        ].includes(
            mode
        )
    ) {

        return "meta";
    }


    return mode;
}

// =========================================
// GENERATE SQUAD
// =========================================

async function generateQuickSquad() {

    const teamColorId =
        Number(
            quickSquadTeamColorElement
                ?.value
            ??
            0
        );


    const budgetHundredMillion =
        Number(
            quickSquadBudgetElement
                ?.value
            ??
            0
        );


    const formation =
        (
            quickSquadFormationElement
                ?.value
            ??
            ""
        );

    const enhancementGradeValue =
        quickSquadEnhancementGradeElement
            ?.value
        ??
        "auto";

    const enhancementGrade =
        enhancementGradeValue === "auto"
            ? null
            : Number(enhancementGradeValue);

    if (
        enhancementGrade !== null
        &&
        (
            !Number.isInteger(enhancementGrade)
            ||
            enhancementGrade < 1
            ||
            enhancementGrade > 13
        )
    ) {
        if (quickSquadResultStatusElement) {
            quickSquadResultStatusElement.textContent =
                "강화등급을 다시 선택해주세요.";
        }

        return;
    }


    if (
        !Number.isInteger(
            teamColorId
        )
        ||
        teamColorId <= 0
    ) {

        if (
            quickSquadResultStatusElement
        ) {

            quickSquadResultStatusElement
                .textContent =
                    "팀컬러를 선택해주세요.";
        }

        return;
    }


    if (
        !Number.isFinite(
            budgetHundredMillion
        )
        ||
        budgetHundredMillion <= 0
    ) {

        if (
            quickSquadResultStatusElement
        ) {

            quickSquadResultStatusElement
                .textContent =
                    "구단가치를 입력해주세요.";
        }

        return;
    }


    if (
        currentQuickSquadSlots.length
        !==
        11
    ) {

        if (
            quickSquadResultStatusElement
        ) {

            quickSquadResultStatusElement
                .textContent =
                    "포메이션 정보를 확인해주세요.";
        }

        return;
    }


    const budgetBp =
        Math.round(
            budgetHundredMillion
            *
            100_000_000
        );

    const requestBody = {
        team_color_id:
            teamColorId,

        budget_bp:
            budgetBp,

        formation:
            formation,

        slots:
            currentQuickSquadSlots.map(
                slot => slot.position
            ),

        recommendation_mode:
            getQuickSquadRecommendationMode(),

        enhancement_grade:
            enhancementGrade,

        locked_players: [],

        ...(
            quickSquadBudgetController
                ?.getPreferences()
            ?? {
                budget_mode: "core",
                core_strength: 200,
            }
        ),
    };


    if (
        quickSquadGenerateButtonElement
    ) {

        quickSquadGenerateButtonElement
            .disabled =
                true;


        quickSquadGenerateButtonElement
            .textContent =
                "추천 중...";
    }


    if (
        quickSquadResultStatusElement
    ) {

        quickSquadResultStatusElement
            .textContent =
                (
                    "선수와 이적시장 시세를 "
                    +
                    "분석하고 있습니다..."
                );
    }


    try {

        requestBody.locked_players =
            await quickSquadLocksController.collect(budgetBp);

        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    "/api/quick-squad/recommend"
                ),
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        ),
                }
            );


        const responseText =
            await response.text();


        let data = {};


        if (
            responseText
        ) {

            try {

                data =
                    JSON.parse(
                        responseText
                    );

            } catch (parseError) {

                console.error(
                    "퀵 스쿼드 응답 JSON 파싱 실패:",
                    parseError,
                    responseText
                );

            }

        }


        if (
            !response.ok
        ) {

            throw new Error(
                (
                    data.detail
                    ??
                    `스쿼드 추천에 실패했습니다. (${response.status})`
                )
            );
        }

        console.log(
            "[GENERATION RAW]",
            data.players
                ?.filter(
                    player =>
                        player.generation_restricted
                        ===
                        true
                )
                .map(
                    player => ({
                        sp_id:
                            player.sp_id,

                        name:
                            player.player_name,

                        generation_restricted:
                            player.generation_restricted,

                        source:
                            player.generation_status_source,
                    })
                )
        );

        const savedLocks = new Map(
            readQuickSquadLocks().map(entry => [
                entry.sp_id,
                entry,
            ])
        );

        const playersWithSettings = data.players.map(player => {
            if (!player.locked) {
                return player;
            }

            const entry = savedLocks.get(
                Number(player.sp_id)
            );

            return entry
                ? mergeQuickSquadLockSettings(player, entry)
                : player;
        });

        const result = normalizeQuickSquadResult(
            {
                ...data,
                players: playersWithSettings,

                manually_modified:
                    playersWithSettings.some(
                        player => player.manual_saved
                    ),
            },
            currentQuickSquadSlots
        );

        console.log(
            "[GENERATION NORMALIZED]",
            result.players
                ?.filter(
                    player =>
                        player?.generation_restricted
                        ===
                        true
                )
                .map(
                    player => ({
                        sp_id:
                            player.sp_id,

                        name:
                            player.player_name,

                        generation_restricted:
                            player.generation_restricted,

                        source:
                            player.generation_status_source,
                    })
                )
        );

        currentQuickSquadResult = result;

        renderQuickSquadResult(result);


} catch (error) {

    console.error(
        error
    );


    const errorMessage =
        (
            error?.message
            ||
            "스쿼드 추천 중 오류가 발생했습니다."
        );


    if (
        quickSquadResultStatusElement
    ) {

        quickSquadResultStatusElement
            .textContent =
                (
                    "추천 실패: "
                    +
                    errorMessage
                );
    }


    window.alert(
        (
            "퀵 스쿼드 추천에 실패했습니다.\n\n"
            +
            errorMessage
        )
    );


    } finally {

        if (
            quickSquadGenerateButtonElement
        ) {

            quickSquadGenerateButtonElement
                .disabled =
                    false;


            quickSquadGenerateButtonElement
                .textContent =
                    "스쿼드 추천";
        }

    }

}


// =========================================
// EVENTS
// =========================================

document
    .querySelectorAll(
        (
            ".quick-squad-"
            +
            "recommendation-mode-button"
        )
    )
    .forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    document
                        .querySelectorAll(
                            (
                                ".quick-squad-"
                                +
                                "recommendation-mode-button"
                            )
                        )
                        .forEach(
                            item => {

                                const selected =
                                    (
                                        item
                                        ===
                                        button
                                    );


                                item
                                    .classList
                                    .toggle(
                                        "is-active",
                                        selected
                                    );


                                item
                                    .setAttribute(
                                        "aria-pressed",
                                        String(
                                            selected
                                        )
                                    );
                            }
                        );


                    saveQuickSquadConditions();
                }
            );
        }
    );


quickSquadGenerateButtonElement
    ?.addEventListener(
        "click",
        generateQuickSquad
    );

// =========================================
// TEAM COLOR TOOLTIP EVENTS
// =========================================

function isQuickSquadHoverDevice() {

    return window.matchMedia(
        "(hover: hover) and (pointer: fine)"
    ).matches;
}


quickSquadActiveTeamColorsElement
    ?.addEventListener(
        "mouseover",
        event => {

            if (
                !isQuickSquadHoverDevice()
            ) {
                return;
            }


            const targetElement =
                event.target.closest(
                    "[data-quick-squad-team-color-index]"
                );


            if (
                !targetElement
                ||
                !quickSquadActiveTeamColorsElement
                    .contains(
                        targetElement
                    )
            ) {
                return;
            }


            if (
                event.relatedTarget
                &&
                targetElement.contains(
                    event.relatedTarget
                )
            ) {
                return;
            }


            showQuickSquadTeamColorTooltip(
                targetElement
            );
        }
    );


quickSquadActiveTeamColorsElement
    ?.addEventListener(
        "mouseout",
        event => {

            if (
                !isQuickSquadHoverDevice()
            ) {
                return;
            }


            const targetElement =
                event.target.closest(
                    "[data-quick-squad-team-color-index]"
                );


            if (!targetElement) {
                return;
            }


            if (
                event.relatedTarget
                &&
                targetElement.contains(
                    event.relatedTarget
                )
            ) {
                return;
            }


            hideQuickSquadTeamColorTooltip();
        }
    );


quickSquadActiveTeamColorsElement
    ?.addEventListener(
        "click",
        event => {

            const targetElement =
                event.target.closest(
                    "[data-quick-squad-team-color-index]"
                );


            if (!targetElement) {
                return;
            }


            // PC에서는 hover 사용.
            if (
                isQuickSquadHoverDevice()
            ) {
                return;
            }


            event.preventDefault();

            event.stopPropagation();


            if (
                quickSquadTeamColorTooltipTarget
                ===
                targetElement
            ) {

                hideQuickSquadTeamColorTooltip();

                return;
            }


            showQuickSquadTeamColorTooltip(
                targetElement
            );
        }
    );


document.addEventListener(
    "click",
    event => {

        if (
            !quickSquadTeamColorTooltipTarget
        ) {
            return;
        }


        if (
            quickSquadActiveTeamColorsElement
                ?.contains(
                    event.target
                )
        ) {
            return;
        }


        hideQuickSquadTeamColorTooltip();
    }
);


window.addEventListener(
    "resize",
    hideQuickSquadTeamColorTooltip
);


window.addEventListener(
    "scroll",
    hideQuickSquadTeamColorTooltip,
    true
);

quickSquadFormationElement
    ?.addEventListener(
        "change",
        () => {

            renderQuickSquadFormation();

            updateQuickSquadConditionSummary();

            saveQuickSquadConditions();
        }
    );


quickSquadTeamColorSearchElement
    ?.addEventListener(
        "input",
        () => {

            renderQuickSquadTeamColorOptions();
        }
    );


quickSquadTeamColorElement
    ?.addEventListener(
        "change",
        () => {

            // 팀컬러를 선택하면 검색어는 비우고
            // 전체 목록 상태로 되돌린다.
            if (
                quickSquadTeamColorSearchElement
            ) {

                quickSquadTeamColorSearchElement.value =
                    "";

                renderQuickSquadTeamColorOptions();
            }


            updateQuickSquadConditionSummary();

            saveQuickSquadConditions();

            quickSquadLocksController?.refresh();
        }
    );


quickSquadBudgetElement
    ?.addEventListener("input", () => {

        updateQuickSquadConditionSummary();

        saveQuickSquadConditions();

        quickSquadLocksController?.updateBudget();

        quickSquadBudgetController?.clearResult();
    });

quickSquadEnhancementGradeElement
    ?.addEventListener(
        "change",
        () => {

            saveQuickSquadConditions();
        }
    );

window.addEventListener(
    "pagehide",
    () => {

        saveQuickSquadConditions();
    }
);

document.querySelectorAll(
    "[data-quick-squad-player-close]"
).forEach((button) => {
    button.addEventListener(
        "click",
        closeQuickSquadPlayerModal
    );
});

document.addEventListener(
    "keydown",
    (event) => {
        if (
            event.key === "Escape"
            &&
            !quickSquadPlayerModal.classList.contains("hidden")
        ) {
            closeQuickSquadPlayerModal();
        }
    }
);


// =========================================
// INITIALIZE
// =========================================

async function initializeQuickSquad() {

    // =========================================
    // 실제 브라우저 새로고침일 때만 초기화
    // =========================================

    const navigationEntry =
        performance
            .getEntriesByType(
                "navigation"
            )
            ?.[0];


    const isPageReload =
        (
            navigationEntry
                ?.type
            ===
            "reload"
        );


    if (
        isPageReload
    ) {

        try {

            localStorage.removeItem(
                "fcl.quick-squad.locks.v1"
            );

            localStorage.removeItem(
                "fcl.quick-squad.saved.v1"
            );

            localStorage.removeItem(
                "fcl.quick-squad.budget.v1"
            );

            localStorage.removeItem(
                QUICK_SQUAD_CONDITION_STORAGE_KEY
            );

        } catch (error) {

            console.warn(
                "퀵 스쿼드 저장 상태 초기화 실패:",
                error
            );
        }


        if (
            quickSquadTeamColorElement
        ) {

            quickSquadTeamColorElement.value =
                "";
        }


        if (
            quickSquadBudgetElement
        ) {

            quickSquadBudgetElement.value =
                "";
        }


        if (
            quickSquadEnhancementGradeElement
        ) {

            quickSquadEnhancementGradeElement.value =
                "auto";
        }


        currentQuickSquadResult =
            null;
    }


    renderQuickSquadFormation();


    const results =
        await Promise.allSettled(
            [
                loadQuickSquadTeamColors(),

                loadQuickSquadFormations(),
            ]
        );

    const restoredConditions =
        restoreQuickSquadConditions();

    if (!quickSquadLocksController) {
        quickSquadLocksController =
            createQuickSquadLockController({
                apiBaseUrl,

                root: document.getElementById(
                    "quick-squad-locked-panel"
                ),

                getSlots: () => currentQuickSquadSlots,

                getTeamColorId: () =>
                    quickSquadTeamColorElement.value,

                getBudgetBp: () =>
                    Math.round(
                        Number(
                            quickSquadBudgetElement.value || 0
                        ) * 100_000_000
                    ),

                formatPrice: formatQuickSquadBp,

                onChange: renderQuickSquadLockedPreview,
            });
    }

    const preferredTeam =
        quickSquadLocksController.preferredTeamColorId();

        if (
            !quickSquadTeamColorElement.value
            && preferredTeam
            && [...quickSquadTeamColorElement.options]
                .some(option =>
                    Number(option.value) === preferredTeam
                )
        ) {
            quickSquadTeamColorElement.value =
                String(preferredTeam);
        }

    await quickSquadLocksController.initialize();

    if (!quickSquadBudgetController) {
        quickSquadBudgetController =
            createQuickSquadBudgetController({
                root: document.getElementById(
                    "quick-squad-budget-panel"
                ),

                getSlots: () => {
                    return currentQuickSquadSlots;
                },

                getBudgetBp: () => {
                    const budgetEok = Number(
                        quickSquadBudgetElement.value || 0
                    );

                    return Math.round(
                        budgetEok * 100_000_000
                    );
                },

                getLockedPlayers: () => {
                    const saved = new Map(
                        readQuickSquadLocks().map(
                            player => [
                                player.sp_id,
                                player,
                            ]
                        )
                    );

                    return (
                        quickSquadLocksController
                            ?.getPreview()
                        || []
                    ).map(player => ({
                        ...player,

                        slot_index:
                            saved.get(player.sp_id)
                                ?.slot_index
                            ?? null,
                    }));
                },

                formatPrice:
                    formatQuickSquadBp,

                onPreferenceChange: () => {
                    if (quickSquadResultStatusElement) {
                        quickSquadResultStatusElement
                            .textContent =
                                "예산 배분이 변경되었습니다. "
                                + "추천 버튼을 눌러 새 조합을 생성하세요.";
                    }
                },
            });
    }


    updateQuickSquadConditionSummary();


    const failed =
        results.some(
            result =>
                result.status
                ===
                "rejected"
        );


    if (
        quickSquadResultStatusElement
    ) {

        quickSquadResultStatusElement
            .textContent =
                failed
                    ? (
                        "일부 조건 정보를 "
                        +
                        "불러오지 못했습니다."
                    )
                    : (
                        "팀컬러와 구단가치를 "
                        +
                        "설정해주세요."
                    );
    }

   // 마지막 저장본은 서버 추천과 별도로 복원한다.
const savedSquad =
    readSavedQuickSquad();

if (
    savedSquad
    &&
    !restoredConditions
) {
    const formationOption = [
        ...quickSquadFormationElement.options
    ].find(
        option =>
            option.value === savedSquad.formation
    );

    const teamOption = [
        ...quickSquadTeamColorElement.options
    ].find(
        option =>
            Number(option.value)
            === Number(savedSquad.team_color_id)
    );

    if (formationOption && teamOption) {
        const expectedSlots =
            getQuickSquadFormationSlots(
                savedSquad.formation
            );

        const expectedPositions =
            expectedSlots.map(slot => slot.position);

        const savedPositions =
            savedSquad.slot_positions;

        const positionsValid =
            !savedPositions.some(Boolean)
            || JSON.stringify(savedPositions)
                === JSON.stringify(expectedPositions);

        if (positionsValid) {
            quickSquadFormationElement.value =
                savedSquad.formation;

            quickSquadTeamColorElement.value =
                String(savedSquad.team_color_id);

            quickSquadBudgetElement.value =
                String(
                    Number(savedSquad.budget_bp)
                    / 100_000_000
                );

            if (quickSquadEnhancementGradeElement) {
                const grade =
                    savedSquad.enhancement_grade;

                const optionValue =
                    grade == null
                        ? "auto"
                        : String(grade);

                if (
                    [...quickSquadEnhancementGradeElement.options]
                        .some(
                            option =>
                                option.value === optionValue
                        )
                ) {
                    quickSquadEnhancementGradeElement.value =
                        optionValue;
                }
            }

            renderQuickSquadFormation();
            updateQuickSquadConditionSummary();

            quickSquadLocksController?.updateBudget();

            try {
                const restored =
                    normalizeQuickSquadResult(
                        savedSquad,
                        currentQuickSquadSlots
                    );

                if (
                    sameQuickSquadLocks(
                        restored.players,
                        quickSquadLocksController.getPreview()
                    )
                ) {
                    renderQuickSquadResult(restored);

                } else if (quickSquadResultStatusElement) {
                    quickSquadResultStatusElement.textContent =
                        "저장본과 현재 고정 선수 구성이 다릅니다. "
                        + "저장본은 삭제하지 않았습니다.";
                }

            } catch (error) {
                console.warn(
                    "저장 스쿼드 복원 실패:",
                    error
                );
            }
        }
    }
}

}


initializeQuickSquad();