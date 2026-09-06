import {
    apiBaseUrl,
} from "./config.js";


// =========================================
// DOM
// =========================================

const quickSquadTeamColorElement =
    document.getElementById(
        "quick-squad-team-color"
    );


const quickSquadBudgetElement =
    document.getElementById(
        "quick-squad-budget"
    );


const quickSquadFormationElement =
    document.getElementById(
        "quick-squad-formation"
    );


const quickSquadFormationTitleElement =
    document.getElementById(
        "quick-squad-formation-title"
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


// 현재 화면에 표시 중인 포메이션 11자리
let currentQuickSquadSlots = [];

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

}


// =========================================
// TEAM COLORS
// =========================================

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


        const teams =
            (
                data.teams
                ??
                []
            );


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
            "팀컬러 선택";


        quickSquadTeamColorElement
            .appendChild(
                defaultOption
            );


        teams.forEach(
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


function createQuickSquadPlayerHtml(
    player,
    slot
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

    const seasonImageUrl =
        (
            `${apiBaseUrl}`
            +
            "/api/fconline/metadata/seasons/"
            +
            `${Number(
                player.season_id
            )}/image`
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
                class="quick-squad-player-card"
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


                <div
                    class="quick-squad-player-name-row"
                >

                    <img
                        src="${escapeQuickSquadHtml(
                            seasonImageUrl
                        )}"
                        alt=""
                        class="quick-squad-player-season-icon"
                        loading="lazy"
                    >


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


                <span
                    class="quick-squad-player-price"
                >
                    ${formatQuickSquadBp(
                        player.price
                    )}
                </span>

            </div>

        </div>
    `;

}


function renderQuickSquadResult(
    data
) {

    const players =
        (
            data.players
            ??
            []
        );


    if (
        players.length
        !==
        currentQuickSquadSlots.length
    ) {

        throw new Error(
            "추천 선수 수가 포메이션과 일치하지 않습니다."
        );
    }


    quickSquadPlayerLayerElement
        .innerHTML =
            players
                .map(
                    (
                        player,
                        index
                    ) => {

                        return (
                            createQuickSquadPlayerHtml(
                                player,
                                currentQuickSquadSlots[
                                    index
                                ]
                            )
                        );

                    }
                )
                .join(
                    ""
                );


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

        quickSquadResultStatusElement
            .textContent =
                (
                    "추천 완료 · 남은 예산 "
                    +
                    formatQuickSquadBp(
                        data.remaining_budget
                    )
                );
    }

}


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
            currentQuickSquadSlots
                .map(
                    slot =>
                        slot.position
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


        const data =
            await response.json();


        if (
            !response.ok
        ) {

            throw new Error(
                (
                    data.detail
                    ??
                    "스쿼드 추천에 실패했습니다."
                )
            );
        }


        renderQuickSquadResult(
            data
        );


    } catch (error) {

        console.error(
            error
        );


        if (
            quickSquadResultStatusElement
        ) {

            quickSquadResultStatusElement
                .textContent =
                    (
                        error.message
                        ??
                        "스쿼드 추천에 실패했습니다."
                    );
        }


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

quickSquadGenerateButtonElement
    ?.addEventListener(
        "click",
        generateQuickSquad
    );

quickSquadFormationElement
    ?.addEventListener(
        "change",
        () => {

            renderQuickSquadFormation();

            updateQuickSquadConditionSummary();
        }
    );


quickSquadTeamColorElement
    ?.addEventListener(
        "change",
        updateQuickSquadConditionSummary
    );


quickSquadBudgetElement
    ?.addEventListener(
        "input",
        updateQuickSquadConditionSummary
    );


// =========================================
// INITIALIZE
// =========================================

async function initializeQuickSquad() {

    renderQuickSquadFormation();


    const results =
        await Promise.allSettled(
            [
                loadQuickSquadTeamColors(),

                loadQuickSquadFormations(),
            ]
        );


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

}


initializeQuickSquad();