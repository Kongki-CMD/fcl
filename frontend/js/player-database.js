import {
    apiBaseUrl,
} from "./config.js";

const playerCompareModalElement =
    document.querySelector(
        "#player-compare-modal"
    );


const playerCompareContentElement =
    document.querySelector(
        "#player-compare-content"
    );

const playerRecommendModalElement =
    document.querySelector(
        "#player-recommend-modal"
    );

const playerRecommendContentElement =
    document.querySelector(
        "#player-recommend-content"
    );


// =========================================
// ELEMENTS
// =========================================

const playerNameInputElement =
    document.querySelector(
        "#player-database-name"
    );

const playerSearchButtonElement =
    document.querySelector(
        "#player-database-search-button"
    );

// =========================================
// NATION
// =========================================

const playerNationToggleElement =
    document.querySelector(
        "#player-database-nation-toggle"
    );

const playerNationPanelElement =
    document.querySelector(
        "#player-database-nation-panel"
    );

const playerNationSummaryElement =
    document.querySelector(
        "#player-database-nation-summary"
    );

const playerNationClearElement =
    document.querySelector(
        "#player-database-nation-clear"
    );

const playerContinentOptionsElement =
    document.querySelector(
        "#player-database-continent-options"
    );

const playerNationOptionsElement =
    document.querySelector(
        "#player-database-nation-options"
    );


// =========================================
// TEAM
// =========================================

const playerTeamToggleElement =
    document.querySelector(
        "#player-database-team-toggle"
    );

const playerTeamPanelElement =
    document.querySelector(
        "#player-database-team-panel"
    );

const playerTeamSummaryElement =
    document.querySelector(
        "#player-database-team-summary"
    );

const playerTeamClearElement =
    document.querySelector(
        "#player-database-team-clear"
    );

const playerLeagueOptionsElement =
    document.querySelector(
        "#player-database-league-options"
    );

const playerTeamOptionsElement =
    document.querySelector(
        "#player-database-team-options"
    );

const playerResultsElement =
    document.querySelector(
        "#player-database-results"
    );

const playerResultListElement =
    document.querySelector(
        "#player-database-result-list"
    );

const playerResultCountElement =
    document.querySelector(
        "#player-database-result-count"
    );

const playerPaginationElement =
    document.querySelector(
        "#player-database-pagination"
    );

const detailToggleElement =
    document.querySelector(
        "#player-database-detail-toggle"
    );

const detailPanelElement =
    document.querySelector(
        "#player-database-detail-panel"
    );

const detailArrowElement =
    document.querySelector(
        "#player-database-detail-arrow"
    );

const resetButtonElement =
    document.querySelector(
        "#player-database-reset-button"
    );

const playerSeasonToggleElement =
    document.querySelector(
        "#player-database-season-toggle"
    );

const playerSeasonPanelElement =
    document.querySelector(
        "#player-database-season-panel"
    );

const playerSeasonOptionsElement =
    document.querySelector(
        "#player-database-season-options"
    );

const playerSeasonSummaryElement =
    document.querySelector(
        "#player-database-season-summary"
    );


const playerPositionToggleElement =
    document.querySelector(
        "#player-database-position-toggle"
    );

const playerPositionPanelElement =
    document.querySelector(
        "#player-database-position-panel"
    );

const playerPositionOptionsElement =
    document.querySelector(
        "#player-database-position-options"
    );

const playerPositionSummaryElement =
    document.querySelector(
        "#player-database-position-summary"
    );


// =========================================
// STATE
// =========================================

let currentPage = 1;

const pageSize = 20;

const selectedSeasonIds =
    new Set();

const selectedPositions =
    new Set();

const playerCardStates =
    new Map();

const compareState = {
    basePlayerSpId: null,
    targetPlayerSpId: null,
    activePosition: "all",
};

const recommendState = {
    basePlayerSpId: null,

    currentPage: 1,

    selectedPosition:
        "same",

    selectedSalaryMode:
        "any",

    selectedTeamColorId:
        null,

    ovrMin:
        null,

    ovrMax:
        null,

    limit:
        10,
};

const compareControlState = {

    left: {
        grade: 1,
        adaptation: 1,
        teamColor: 0,
    },

    right: {
        grade: 1,
        adaptation: 1,
        teamColor: 0,
    },

};

const playerDataBySpId =
    new Map();

const playerMarketPriceBySpId =
    new Map();

const playerMarketPriceLoadingSpIds =
    new Set();

const playerMarketPriceErrorBySpId =
    new Map();


const enhancementBonusMap = {
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
};


const adaptationBonusMap = {
    1: 0,
    5: 4,
};

// =========================================
// NATION / TEAM STATE
// =========================================

let nationGroups =
    [];

let teamGroups =
    [];


let activeContinentId =
    null;

let activeLeagueId =
    null;


let selectedNationId =
    null;

let selectedNationName =
    "";


let selectedTeamColorId =
    null;

let selectedTeamName =
    "";

const playerPositions = [
    "GK",

    "SW",
    "RWB",
    "RB",
    "RCB",
    "CB",
    "LCB",
    "LB",
    "LWB",

    "RDM",
    "CDM",
    "LDM",

    "RM",
    "RCM",
    "CM",
    "LCM",
    "LM",

    "RAM",
    "CAM",
    "LAM",

    "RF",
    "CF",
    "LF",

    "RW",
    "RS",
    "ST",
    "LS",
    "LW",
];

// =========================================
// POSITION GROUP
// =========================================

const goalkeeperPositions =
    new Set([
        "GK",
    ]);


const defenderPositions =
    new Set([
        "SW",

        "RWB",
        "RB",
        "RCB",
        "CB",
        "LCB",
        "LB",
        "LWB",
    ]);


const midfielderPositions =
    new Set([
        "RDM",
        "CDM",
        "LDM",

        "RM",
        "RCM",
        "CM",
        "LCM",
        "LM",

        "RAM",
        "CAM",
        "LAM",
    ]);


const forwardPositions =
    new Set([
        "RF",
        "CF",
        "LF",

        "RW",
        "RS",
        "ST",
        "LS",
        "LW",
    ]);


function getPositionGroupClass(
    position
) {

    if (
        goalkeeperPositions.has(
            position
        )
    ) {
        return "position-gk";
    }


    if (
        defenderPositions.has(
            position
        )
    ) {
        return "position-df";
    }


    if (
        midfielderPositions.has(
            position
        )
    ) {
        return "position-mf";
    }


    if (
        forwardPositions.has(
            position
        )
    ) {
        return "position-fw";
    }


    return "";
}


function renderPositionOptions() {

    playerPositionOptionsElement
        .innerHTML =
            playerPositions
                .map(
                    position => {

                        const groupClass =
                            getPositionGroupClass(
                                position
                            );


                        return `
                            <button
                                type="button"
                                class="
                                    player-database-position-option
                                    ${groupClass}
                                "
                                data-position="${position}"
                            >
                                ${position}
                            </button>
                        `;
                    }
                )
                .join(
                    ""
                );
}

function updateSeasonSummary() {

    const count =
        selectedSeasonIds.size;


    playerSeasonSummaryElement
        .textContent =
            count === 0
                ? "전체 시즌"
                : `${count}개 시즌 선택`;
}


function updatePositionSummary() {

    const count =
        selectedPositions.size;


    if (
        count === 0
    ) {

        playerPositionSummaryElement
            .textContent =
                "전체 포지션";

        return;
    }


    if (
        count <= 3
    ) {

        playerPositionSummaryElement
            .textContent =
                [
                    ...selectedPositions,
                ].join(
                    ", "
                );

        return;
    }


    playerPositionSummaryElement
        .textContent =
            `${count}개 포지션 선택`;
}

// =========================================
// NATION
// =========================================

function renderContinentOptions() {

    playerContinentOptionsElement
        .innerHTML =
            nationGroups
                .map(
                    group => {

                        const isActive =
                            Number(
                                group.continent_id
                            )
                            ===
                            Number(
                                activeContinentId
                            );


                        return `
                            <button
                                type="button"
                                class="
                                    player-database-hierarchy-group
                                    ${
                                        isActive
                                            ? "active"
                                            : ""
                                    }
                                "
                                data-continent-id="${group.continent_id}"
                            >
                                ${escapeHtml(
                                    group.continent_name
                                )}
                            </button>
                        `;
                    }
                )
                .join(
                    ""
                );
}


function renderNationOptions() {

    const group =
        nationGroups.find(
            item =>
                Number(
                    item.continent_id
                )
                ===
                Number(
                    activeContinentId
                )
        );


    if (!group) {

        playerNationOptionsElement
            .innerHTML =
                "";

        return;
    }


    playerNationOptionsElement
        .innerHTML =
            group.nations
                .map(
                    nation => {

                        const isSelected =
                            Number(
                                nation.nation_id
                            )
                            ===
                            Number(
                                selectedNationId
                            );


                        return `
                            <button
                                type="button"
                                class="
                                    player-database-hierarchy-item
                                    ${
                                        isSelected
                                            ? "selected"
                                            : ""
                                    }
                                "
                                data-nation-id="${nation.nation_id}"
                                data-nation-name="${escapeHtml(
                                    nation.nation_name
                                )}"
                            >

                                <span>
                                    ${escapeHtml(
                                        nation.nation_name
                                    )}
                                </span>

                                <small>
                                    ${nation.player_count}
                                </small>

                            </button>
                        `;
                    }
                )
                .join(
                    ""
                );
}


// =========================================
// TEAM
// =========================================

function renderLeagueOptions() {

    playerLeagueOptionsElement
        .innerHTML =
            teamGroups
                .map(
                    group => {

                        const isActive =
                            Number(
                                group.league_id
                            )
                            ===
                            Number(
                                activeLeagueId
                            );


                        return `
                            <button
                                type="button"
                                class="
                                    player-database-hierarchy-group
                                    ${
                                        isActive
                                            ? "active"
                                            : ""
                                    }
                                "
                                data-league-id="${group.league_id}"
                            >
                                ${escapeHtml(
                                    group.league_name
                                )}
                            </button>
                        `;
                    }
                )
                .join(
                    ""
                );
}


function renderTeamOptions() {

    const group =
        teamGroups.find(
            item =>
                Number(
                    item.league_id
                )
                ===
                Number(
                    activeLeagueId
                )
        );


    if (!group) {

        playerTeamOptionsElement
            .innerHTML =
                "";

        return;
    }


    playerTeamOptionsElement
        .innerHTML =
            group.teams
                .map(
                    team => {

                        const isSelected =
                            Number(
                                team.team_color_id
                            )
                            ===
                            Number(
                                selectedTeamColorId
                            );


                        return `
                            <button
                                type="button"
                                class="
                                    player-database-hierarchy-item
                                    ${
                                        isSelected
                                            ? "selected"
                                            : ""
                                    }
                                "
                                data-team-color-id="${team.team_color_id}"
                                data-team-name="${escapeHtml(
                                    team.team_name
                                )}"
                            >

                                <span>
                                    ${escapeHtml(
                                        team.team_name
                                    )}
                                </span>

                                <small>
                                    ${team.player_count}
                                </small>

                            </button>
                        `;
                    }
                )
                .join(
                    ""
                );
}

// =========================================
// HTML ESCAPE
// =========================================

function escapeHtml(
    value
) {

    return String(
        value ?? ""
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
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


// =========================================
// FILTER OPTIONS
// =========================================

async function loadPlayerFilters() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/player-database/filters`
            );

        if (!response.ok) {

            throw new Error(
                "선수 검색 필터를 불러오지 못했습니다."
            );
        }

        const data =
            await response.json();

        nationGroups =
            data.nation_groups
            ?? [];

        teamGroups =
            data.team_groups
            ?? [];


        if (
            nationGroups.length
            > 0
        ) {

            activeContinentId =
                nationGroups[
                    0
                ].continent_id;
        }


        if (
            teamGroups.length
            > 0
        ) {

            activeLeagueId =
                teamGroups[
                    0
                ].league_id;
        }


        renderContinentOptions();
        renderNationOptions();

        renderLeagueOptions();
        renderTeamOptions();




        // =============================
        // 시즌
        // =============================

playerSeasonOptionsElement
    .innerHTML =
        data.seasons
            .map(
                season => {

                    return `
                        <button
                            type="button"
                            class="player-database-season-option"
                            data-season-id="${season.season_id}"
                            title="${escapeHtml(
                                season.class_name
                            )}"
                        >

                            ${
                                season.season_image_url
                                    ? `
                                        <img
                                            src="${escapeHtml(
                                                season.season_image_url
                                            )}"
                                            alt="${escapeHtml(
                                                season.class_name
                                            )}"
                                            loading="lazy"
                                        >
                                    `
                                    : `
                                        <span>
                                            ${escapeHtml(
                                                season.class_name
                                            )}
                                        </span>
                                    `
                            }

                        </button>
                    `;
                }
            )
            .join(
                ""
            );




playerSeasonOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-season-id]"
                );


            if (!buttonElement) {
                return;
            }


            const seasonId =
                Number(
                    buttonElement.dataset.seasonId
                );


            if (
                selectedSeasonIds.has(
                    seasonId
                )
            ) {

                selectedSeasonIds.delete(
                    seasonId
                );

                buttonElement
                    .classList
                    .remove(
                        "selected"
                    );

            } else {

                selectedSeasonIds.add(
                    seasonId
                );

                buttonElement
                    .classList
                    .add(
                        "selected"
                    );
            }


            updateSeasonSummary();
        }
    );


        // =============================
        // 국적
        // =============================

playerPositionOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-position]"
                );


            if (!buttonElement) {
                return;
            }


            const position =
                buttonElement.dataset.position;


            if (
                selectedPositions.has(
                    position
                )
            ) {

                selectedPositions.delete(
                    position
                );

                buttonElement
                    .classList
                    .remove(
                        "selected"
                    );

            } else {

                selectedPositions.add(
                    position
                );

                buttonElement
                    .classList
                    .add(
                        "selected"
                    );
            }


            updatePositionSummary();
        }
    );

// =========================================
// CONTINENT
// =========================================

playerContinentOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-continent-id]"
                );


            if (!buttonElement) {
                return;
            }


            activeContinentId =
                Number(
                    buttonElement.dataset.continentId
                );


            renderContinentOptions();
            renderNationOptions();
        }
    );


// =========================================
// NATION
// =========================================

playerNationOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-nation-id]"
                );


            if (!buttonElement) {
                return;
            }


            selectedNationId =
                Number(
                    buttonElement.dataset.nationId
                );


            selectedNationName =
                buttonElement.dataset.nationName;


            playerNationSummaryElement
                .textContent =
                    selectedNationName;


            renderNationOptions();

            closeNationPanel();
        }
    );


// =========================================
// LEAGUE
// =========================================

playerLeagueOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-league-id]"
                );


            if (!buttonElement) {
                return;
            }


            activeLeagueId =
                Number(
                    buttonElement.dataset.leagueId
                );


            renderLeagueOptions();
            renderTeamOptions();
        }
    );


// =========================================
// TEAM
// =========================================

playerTeamOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-team-color-id]"
                );


            if (!buttonElement) {
                return;
            }


            selectedTeamColorId =
                Number(
                    buttonElement.dataset.teamColorId
                );


            selectedTeamName =
                buttonElement.dataset.teamName;


            playerTeamSummaryElement
                .textContent =
                    selectedTeamName;


            renderTeamOptions();

            closeTeamPanel();
        }
    );

// =========================================
// SEASON / POSITION PANEL
// =========================================

function closeSeasonPanel() {

    playerSeasonPanelElement.hidden =
        true;

    playerSeasonToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );
}


function closePositionPanel() {

    playerPositionPanelElement.hidden =
        true;

    playerPositionToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );
}

function closeNationPanel() {

    playerNationPanelElement.hidden =
        true;

    playerNationToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );
}


function closeTeamPanel() {

    playerTeamPanelElement.hidden =
        true;

    playerTeamToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );
}

playerNationToggleElement
    .addEventListener(
        "click",
        () => {

            const willOpen =
                playerNationPanelElement.hidden;


            closeSeasonPanel();
            closePositionPanel();
            closeTeamPanel();


            playerNationPanelElement.hidden =
                !willOpen;


            playerNationToggleElement
                .setAttribute(
                    "aria-expanded",
                    String(
                        willOpen
                    )
                );
        }
    );


playerTeamToggleElement
    .addEventListener(
        "click",
        () => {

            const willOpen =
                playerTeamPanelElement.hidden;


            closeSeasonPanel();
            closePositionPanel();
            closeNationPanel();


            playerTeamPanelElement.hidden =
                !willOpen;


            playerTeamToggleElement
                .setAttribute(
                    "aria-expanded",
                    String(
                        willOpen
                    )
                );
        }
    );

playerNationClearElement
    .addEventListener(
        "click",
        () => {

            selectedNationId =
                null;

            selectedNationName =
                "";


            playerNationSummaryElement
                .textContent =
                    "전체 국적";


            renderNationOptions();

            closeNationPanel();
        }
    );


playerTeamClearElement
    .addEventListener(
        "click",
        () => {

            selectedTeamColorId =
                null;

            selectedTeamName =
                "";


            playerTeamSummaryElement
                .textContent =
                    "전체 팀";


            renderTeamOptions();

            closeTeamPanel();
        }
    );


playerSeasonToggleElement
    .addEventListener(
        "click",
        () => {

            const willOpen =
                playerSeasonPanelElement.hidden;


            // 포지션 패널은 닫기
            closePositionPanel();


            playerSeasonPanelElement.hidden =
                !willOpen;


            playerSeasonToggleElement
                .setAttribute(
                    "aria-expanded",
                    String(
                        willOpen
                    )
                );
        }
    );


playerPositionToggleElement
    .addEventListener(
        "click",
        () => {

            const willOpen =
                playerPositionPanelElement.hidden;


            // 시즌 패널은 닫기
            closeSeasonPanel();


            playerPositionPanelElement.hidden =
                !willOpen;


            playerPositionToggleElement
                .setAttribute(
                    "aria-expanded",
                    String(
                        willOpen
                    )
                );
        }
    );

// =========================================
// OUTSIDE CLICK
// =========================================

document.addEventListener(
    "click",
    event => {

        const eventPath =
            event.composedPath();


        const seasonFilterElement =
            playerSeasonToggleElement.closest(
                ".player-database-multi-filter"
            );


        const positionFilterElement =
            playerPositionToggleElement.closest(
                ".player-database-multi-filter"
            );


        const nationFilterElement =
            playerNationToggleElement.closest(
                ".player-database-multi-filter"
            );


        const teamFilterElement =
            playerTeamToggleElement.closest(
                ".player-database-multi-filter"
            );


        // =====================================
        // 시즌
        // =====================================

        if (
            !eventPath.includes(
                seasonFilterElement
            )
        ) {

            closeSeasonPanel();
        }


        // =====================================
        // 포지션
        // =====================================

        if (
            !eventPath.includes(
                positionFilterElement
            )
        ) {

            closePositionPanel();
        }


        // =====================================
        // 국적
        // =====================================

        if (
            !eventPath.includes(
                nationFilterElement
            )
        ) {

            closeNationPanel();
        }


        // =====================================
        // 소속팀
        // =====================================

        if (
            !eventPath.includes(
                teamFilterElement
            )
        ) {

            closeTeamPanel();
        }
    }
);


    } catch (error) {

        console.error(
            error
        );
    }
}

const playerDatabaseDetailFilterMap = {
    "player-database-salary-min":
        "salary_min",

    "player-database-salary-max":
        "salary_max",

    "player-database-ovr-min":
        "ovr_min",

    "player-database-height-min":
        "height_min",

    "player-database-height-max":
        "height_max",

    "player-database-sprint-speed-min":
        "sprint_speed_min",

    "player-database-acceleration-min":
        "acceleration_min",

    "player-database-finishing-min":
        "finishing_min",

    "player-database-shot-power-min":
        "shot_power_min",

    "player-database-long-shots-min":
        "long_shots_min",

    "player-database-positioning-min":
        "positioning_min",

    "player-database-volleys-min":
        "volleys_min",

    "player-database-penalties-min":
        "penalties_min",

    "player-database-short-pass-min":
        "short_pass_min",

    "player-database-vision-min":
        "vision_min",

    "player-database-crossing-min":
        "crossing_min",

    "player-database-long-pass-min":
        "long_pass_min",

    "player-database-free-kick-min":
        "free_kick_min",

    "player-database-curve-min":
        "curve_min",

    "player-database-dribbling-min":
        "dribbling_min",

    "player-database-ball-control-min":
        "ball_control_min",

    "player-database-agility-min":
        "agility_min",

    "player-database-balance-min":
        "balance_min",

    "player-database-reactions-min":
        "reactions_min",

    "player-database-marking-min":
        "marking_min",

    "player-database-tackle-min":
        "tackle_min",

    "player-database-interceptions-min":
        "interceptions_min",

    "player-database-heading-min":
        "heading_min",

    "player-database-sliding-tackle-min":
        "sliding_tackle_min",

    "player-database-strength-min":
        "strength_min",

    "player-database-stamina-min":
        "stamina_min",

    "player-database-aggression-min":
        "aggression_min",

    "player-database-jumping-min":
        "jumping_min",

    "player-database-composure-min":
        "composure_min",

    "player-database-gk-diving-min":
        "gk_diving_min",

    "player-database-gk-handling-min":
        "gk_handling_min",

    "player-database-gk-kick-min":
        "gk_kick_min",

    "player-database-gk-reflexes-min":
        "gk_reflexes_min",

    "player-database-gk-positioning-min":
        "gk_positioning_min",
};


// =========================================
// SEARCH PARAMS
// =========================================

function buildSearchParams(
    page
) {

    const params =
        new URLSearchParams();

    const playerName =
        playerNameInputElement
            .value
            .trim();

    if (
        selectedSeasonIds.size
        > 0
    ) {

        params.set(
            "season_ids",
            [
                ...selectedSeasonIds,
            ].join(
                ","
            )
        );
    }


    if (
        selectedPositions.size
        > 0
    ) {

        params.set(
            "positions",
            [
                ...selectedPositions,
            ].join(
                ","
            )
        );
    }
           

    if (playerName) {

        params.set(
            "player_name",
            playerName
        );
    }

    if (
        selectedNationId
        !== null
    ) {

        params.set(
            "nation_id",
            String(
                selectedNationId
            )
        );
    }


    if (
        selectedTeamColorId
        !== null
    ) {

        params.set(
            "team_color_id",
            String(
                selectedTeamColorId
            )
        );
    }

    // =====================================
    // 상세검색 숫자 조건
    // =====================================

    Object.entries(
        playerDatabaseDetailFilterMap
    )
        .forEach(
            (
                [
                    elementId,
                    queryName,
                ]
            ) => {

                const element =
                    document.getElementById(
                        elementId
                    );


                if (!element) {
                    return;
                }


                const value =
                    element.value.trim();


                if (!value) {
                    return;
                }


                params.set(
                    queryName,
                    value
                );
            }
        );


        // =====================================
        // 왼발 / 오른발
        // =====================================

        const leftFootElement =
            document.querySelector(
                "#player-database-left-foot"
            );


        const rightFootElement =
            document.querySelector(
                "#player-database-right-foot"
            );


        if (
            leftFootElement
            &&
            leftFootElement.value
        ) {

            params.set(
                "left_foot",
                leftFootElement.value
            );
        }


        if (
            rightFootElement
            &&
            rightFootElement.value
        ) {

            params.set(
                "right_foot",
                rightFootElement.value
            );
        }



    params.set(
        "page",
        String(page)
    );

    params.set(
        "page_size",
        String(pageSize)
    );


    return params;
}

// =========================================
// FC ONLINE STAT COLOR
// =========================================

function getPlayerStatColorClass(
    value
) {

    const statValue =
        Number(
            value
        );


    if (
        statValue >= 160
    ) {
        return "stat-160";
    }


    if (
        statValue >= 140
    ) {
        return "stat-140";
    }


    if (
        statValue >= 130
    ) {
        return "stat-130";
    }


    if (
        statValue >= 120
    ) {
        return "stat-120";
    }


    if (
        statValue >= 110
    ) {
        return "stat-110";
    }


    if (
        statValue >= 100
    ) {
        return "stat-100";
    }


    if (
        statValue >= 90
    ) {
        return "stat-90";
    }


    if (
        statValue >= 80
    ) {
        return "stat-80";
    }


    if (
        statValue >= 70
    ) {
        return "stat-70";
    }


    return "stat-low";
}


// =========================================
// PLAYER RESULT
// =========================================

function getPlayerCardState(
    spId
) {

    const numericSpId =
        Number(
            spId
        );


    if (
        !playerCardStates.has(
            numericSpId
        )
    ) {

        playerCardStates.set(
            numericSpId,
            {
                grade: 1,
                adaptation: 1,
                teamColor: 0,
            }
        );
    }


    return playerCardStates.get(
        numericSpId
    );
}


function getGradeTierClass(
    grade
) {

    if (grade <= 4) {
        return "bronze";
    }


    if (grade <= 7) {
        return "silver";
    }


    if (grade <= 10) {
        return "gold";
    }


    return "platinum";
}


function createPlayerGradeButtonsHtml(
    spId,
    selectedGrade
) {

    return Array
        .from(
            {
                length: 13,
            },
            (
                _,
                index
            ) => {

                const grade =
                    index + 1;


                return `
                    <button
                        type="button"
                        class="
                            player-database-card-grade
                            grade-${grade}
                            ${
                                grade === selectedGrade
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-card-grade="${grade}"
                        data-sp-id="${spId}"
                        aria-label="${grade}강"
                        title="${grade}강"
                    >
                         +${grade}
                    </button>
                `;
            }
        )
        .join(
            ""
        );
}


function createPlayerAdaptationButtonsHtml(
    spId,
    selectedAdaptation
) {

    return `
        <button
            type="button"
            class="
                player-database-card-adaptation
                ${
                    selectedAdaptation === 1
                        ? "selected"
                        : ""
                }
            "
            data-card-adaptation="1"
            data-sp-id="${spId}"
        >
            1
        </button>

        <button
            type="button"
            class="
                player-database-card-adaptation
                ${
                    selectedAdaptation === 5
                        ? "selected"
                        : ""
                }
            "
            data-card-adaptation="5"
            data-sp-id="${spId}"
        >
            5
        </button>
    `;
}

function createPlayerTeamColorOptionsHtml(
    selectedTeamColor
) {

    return Array
        .from(
            {
                length: 10,
            },
            (
                _,
                bonus
            ) => {

                return `
                    <option
                        value="${bonus}"
                        ${
                            bonus
                            === selectedTeamColor
                                ? "selected"
                                : ""
                        }
                    >
                        +${bonus}
                    </option>
                `;
            }
        )
        .join(
            ""
        );
}

function getAdjustedPlayer(
    player
) {

    const state =
        getPlayerCardState(
            player.sp_id
        );


    const gradeBonus =
        enhancementBonusMap[
            state.grade
        ]
        ?? 0;


    const adaptationBonus =
        adaptationBonusMap[
            state.adaptation
        ]
        ?? 0;


    const teamColorBonus =
        Number(
            state.teamColor
            ?? 0
        );


    const newAbilityBonus =
        gradeBonus
        +
        adaptationBonus
        +
        teamColorBonus;


    /*
     * API에서 내려온 stats에는
     * 검색 당시 ability_bonus가 들어가 있으므로
     * 먼저 원본값으로 되돌린다.
     */
    const sourceAbilityBonus =
        Number(
            player.ability_bonus
            ?? 0
        );


    const adjustedStats =
        Object.fromEntries(
            Object.entries(
                player.stats
                ?? {}
            )
                .map(
                    (
                        [
                            statName,
                            statValue,
                        ]
                    ) => {

                        const baseStat =
                            Number(
                                statValue
                            )
                            -
                            sourceAbilityBonus;


                        return [
                            statName,
                            baseStat
                            +
                            newAbilityBonus,
                        ];
                    }
                )
        );


    const baseOvr =
        Number(
            player.base_ovr
            ??
            (
                Number(
                    player.ovr
                    ?? 0
                )
                -
                sourceAbilityBonus
            )
        );


    return {
        ...player,

        grade:
            state.grade,

        adaptation:
            state.adaptation,

        team_color_bonus:
            state.teamColor,

        ability_bonus:
            newAbilityBonus,

        ovr:
            baseOvr
            +
            newAbilityBonus,

        stats:
            adjustedStats,
    };
}

function createPlayerStatsHtml(
    player
) {

    const stats =
        Object.entries(
            player.stats ?? {}
        );


    if (
        stats.length
        === 0
    ) {

        return `
            <div
                class="player-database-player-stats-empty"
            >
                능력치 정보가 없습니다.
            </div>
        `;
    }


    return stats
        .map(
            (
                [
                    statName,
                    statValue,
                ]
            ) => {

                return `
                    <div
                        class="player-database-player-stat"
                    >

                        <span>
                            ${escapeHtml(
                                statName
                            )}
                        </span>

                        <strong
                            class="${getPlayerStatColorClass(
                                statValue
                            )}"
                        >
                            ${statValue}
                        </strong>

                    </div>
                `;
            }
        )
        .join(
            ""
        );
}

function formatPlayerMarketPrice(
    price
) {

    const numericPrice =
        Number(
            price
        );


    if (
        !Number.isFinite(
            numericPrice
        )
        ||
        numericPrice <= 0
    ) {
        return "-";
    }


    return (
        numericPrice
            .toLocaleString(
                "ko-KR"
            )
        +
        " BP"
    );
}


function createPlayerMarketPriceHtml(
    player
) {

    const spId =
        Number(
            player.sp_id
        );


    const state =
        getPlayerCardState(
            spId
        );


    const grade =
        Number(
            state.grade
            ?? 1
        );


    const marketData =
        playerMarketPriceBySpId.get(
            spId
        );


    const isLoading =
        playerMarketPriceLoadingSpIds
            .has(
                spId
            );


    const errorMessage =
        playerMarketPriceErrorBySpId
            .get(
                spId
            );


    let contentHtml = "";


    if (isLoading) {

        contentHtml = `
            <div
                class="
                    player-database-market-price-status
                    loading
                "
            >
                FC Online 시세를 불러오는 중입니다.
            </div>
        `;

    } else if (errorMessage) {

        contentHtml = `
            <div
                class="
                    player-database-market-price-status
                    error
                "
            >
                ${escapeHtml(
                    errorMessage
                )}
            </div>
        `;

    } else if (marketData) {

        const priceData =
            (
                marketData.prices
                ??
                []
            )
                .find(
                    item =>
                        Number(
                            item.grade
                        )
                        ===
                        grade
                );


        const price =
            priceData
                ?.price
            ??
            null;


        contentHtml = `
            <div
                class="player-database-market-price-current"
            >

                <div
                    class="player-database-market-price-grade"
                >
                    <span>
                        현재 선택 강화
                    </span>

                    <strong>
                        +${grade}
                    </strong>
                </div>


                <div
                    class="player-database-market-price-value"
                >
                    <span>
                        데이터센터 기준 시세
                    </span>

                    <strong>
                        ${formatPlayerMarketPrice(
                            price
                        )}
                    </strong>
                </div>

            </div>
        `;

    } else {

        contentHtml = `
            <div
                class="
                    player-database-market-price-status
                    waiting
                "
            >
                선수 상세정보를 열면 시세를 조회합니다.
            </div>
        `;
    }


    return `
        <section
            class="player-database-market-price"
            data-market-price
            data-sp-id="${spId}"
        >

            <div
                class="player-database-market-price-header"
            >

                <div>
                    <strong>
                        이적시장 시세
                    </strong>

                    <span>
                        FC Online DataCenter
                    </span>
                </div>


                ${
                    marketData
                        ? `
                            <small>
                                1 ~ 13강 시세 조회 완료
                            </small>
                        `
                        : ""
                }

            </div>


            ${contentHtml}

        </section>
    `;
}


async function loadPlayerMarketPrice(
    spId
) {

    const numericSpId =
        Number(
            spId
        );


    if (
        !Number.isInteger(
            numericSpId
        )
    ) {
        return;
    }


    if (
        playerMarketPriceBySpId
            .has(
                numericSpId
            )
    ) {
        return;
    }


    if (
        playerMarketPriceLoadingSpIds
            .has(
                numericSpId
            )
    ) {
        return;
    }


    playerMarketPriceLoadingSpIds
        .add(
            numericSpId
        );


    playerMarketPriceErrorBySpId
        .delete(
            numericSpId
        );


    rerenderPlayerCard(
        numericSpId
    );


    try {

        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    `/api/player-database/price/`
                    +
                    `${numericSpId}`
                )
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "시세 조회에 실패했습니다."
            );
        }


        playerMarketPriceBySpId
            .set(
                numericSpId,
                data
            );


    } catch (error) {

        console.error(
            error
        );


        playerMarketPriceErrorBySpId
            .set(
                numericSpId,
                (
                    error.message
                    ??
                    "시세 조회에 실패했습니다."
                )
            );

    } finally {

        playerMarketPriceLoadingSpIds
            .delete(
                numericSpId
            );


        rerenderPlayerCard(
            numericSpId
        );
    }
}


function createPlayerCardHtml(
    player
) {

    playerDataBySpId.set(
        Number(
            player.sp_id
        ),
        player
    );


    player =
        getAdjustedPlayer(
            player
        );


    const playerCardState =
        getPlayerCardState(
            player.sp_id
        );


    const seasonImageUrl =
        (
            `${apiBaseUrl}`
            +
            `/api/fconline/metadata/seasons/`
            +
            `${player.season_id}/image`
        );


    const teams =
        (
            player.team_colors
            ??
            []
        )
            .map(
                team =>
                    escapeHtml(
                        team.team_name
                    )
            )
            .join(
                " · "
            );

    const leftFoot =
        Number(
            player.left_foot
            ?? 0
        );


    const rightFoot =
        Number(
            player.right_foot
            ?? 0
        );


    const leftFootIsMain =
        leftFoot >= rightFoot;


    const rightFootIsMain =
        rightFoot >= leftFoot;


    const footDisplayHtml = `
        <span class="player-database-foot-display">

            <span
                class="
                    player-database-foot
                    player-database-foot-left
                    ${leftFoot === 5 ? "active" : "inactive"}
                "
                title="왼발 ${leftFoot}"
            >

                ${
                    leftFootIsMain
                        ? `
                            <span
                                class="player-database-foot-star"
                                aria-label="주발"
                            >
                                ★
                            </span>
                        `
                        : ""
                }

                <span class="player-database-foot-value">
                    L${leftFoot}
                </span>

            </span>


            <span
                class="
                    player-database-foot
                    player-database-foot-right
                    ${rightFoot === 5 ? "active" : "inactive"}
                "
                title="오른발 ${rightFoot}"
            >

                ${
                    rightFootIsMain
                        ? `
                            <span
                                class="player-database-foot-star"
                                aria-label="주발"
                            >
                                ★
                            </span>
                        `
                        : ""
                }

                <span class="player-database-foot-value">
                    R${rightFoot}
                </span>

            </span>

        </span>
    `;


    return `
        <article
            class="
                player-database-player-item
                ${
                    compareState.basePlayerSpId
                    === Number(player.sp_id)
                        ? "compare-base"
                        : ""
                }
            "
            data-sp-id="${player.sp_id}"
        >

        <!-- =========================
            목록
        ========================== -->
        <div
            class="player-database-player-row"
            aria-expanded="false"
        >

            <span
                class="player-database-player-season"
            >

                <img
                    src="${escapeHtml(
                        seasonImageUrl
                    )}"
                    alt=""
                    class="player-database-player-season-icon"
                    loading="lazy"
                >

            </span>

            <span
                class="
                    player-database-player-position
                    ${getPositionGroupClass(
                        player.position
                    )}
                "
            >
                ${escapeHtml(
                    player.position
                    ?? "-"
                )}
            </span>


            <strong
                class="player-database-player-name"
            >
                ${escapeHtml(
                    player.player_name
                )}
            </strong>


                <div class="player-database-player-row-actions">

                    <button
                        type="button"
                        class="
                            player-database-recommend-button
                            player-database-recommend-button-row
                        "
                        data-recommend-player
                        data-sp-id="${player.sp_id}"
                    >
                        추천
                    </button>

                    <button
                        type="button"
                        class="
                            player-database-compare-button
                            player-database-compare-button-row
                            ${
                                compareState.basePlayerSpId
                                === Number(player.sp_id)
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-compare-player
                        data-sp-id="${player.sp_id}"
                    >

                        ${
                            compareState.basePlayerSpId
                            === Number(player.sp_id)
                                ? "비교 기준"
                                : "비교"
                        }

                    </button>


                    <span
                        class="player-database-player-arrow"
                        aria-hidden="true"
                    >
                        ▼
                    </span>

                </div>

        </div>


            <!-- =========================
                상세정보
            ========================== -->

            <div
                class="player-database-player-detail"
                hidden
            >

                <div
                    class="player-database-player-detail-layout"
                >

                    <!-- =========================
                        선수 사진
                    ========================== -->

                    <aside
                        class="player-database-player-photo-wrap"
                    >

                        <img
                            src="${escapeHtml(
                                player.image_url
                                ?? ""
                            )}"
                            alt="${escapeHtml(
                                player.player_name
                            )}"
                            class="player-database-player-photo"
                            data-player-image
                            loading="lazy"
                        >

                    </aside>


                    <!-- =========================
                        선수 정보
                    ========================== -->

                    <div
                        class="player-database-player-detail-content"
                    >

                        <div
                            class="player-database-player-summary"
                        >

                            <div
                                class="player-database-player-summary-main"
                            >

                                <strong>
                                    ${escapeHtml(
                                        player.position
                                    )}
                                </strong>


                                <span>
                                    OVR

                                    <b
                                        class="${getPlayerStatColorClass(
                                            player.ovr
                                        )}"
                                    >
                                        ${player.ovr}
                                    </b>
                                </span>


                                <span>
                                    급여

                                    <b>
                                        ${player.salary}
                                    </b>
                                </span>

                            </div>


                            <div
                                class="player-database-player-summary-sub"
                            >

                                <span>
                                    ${escapeHtml(
                                        player.nation_name
                                        ?? "-"
                                    )}
                                </span>

                                <span>
                                    ${player.height}cm
                                </span>

                                <span>
                                    ${player.weight}kg
                                </span>

                                ${footDisplayHtml}

                            </div>

                        </div>


                        <!-- =========================
                            강화 / 적응도 / 팀컬러
                        ========================== -->

                        <div class="player-database-card-settings">

                            <div class="player-database-card-setting">

                                <span class="player-database-card-setting-title">
                                    강화
                                </span>

                                <div class="player-database-card-grade-options">

                                    ${createPlayerGradeButtonsHtml(
                                        player.sp_id,
                                        playerCardState.grade
                                    )}

                                </div>

                            </div>


                            <div
                                class="
                                    player-database-card-setting
                                    player-database-card-setting-bottom
                                "
                            >

                                <span class="player-database-card-setting-title">
                                    적응도
                                </span>

                                <div class="player-database-card-adaptation-options">

                                    ${createPlayerAdaptationButtonsHtml(
                                        player.sp_id,
                                        playerCardState.adaptation
                                    )}

                                </div>


                                <label class="player-database-card-team-color">

                                    <span>
                                        팀컬러
                                    </span>

                                    <select
                                        class="player-database-card-team-color-select"
                                        data-card-team-color
                                        data-sp-id="${player.sp_id}"
                                    >

                                        ${createPlayerTeamColorOptionsHtml(
                                            playerCardState.teamColor
                                        )}

                                    </select>

                                </label>

                            </div>

                        </div>


                        <!-- =========================
                            소속팀
                        ========================== -->

                        ${
                            teams
                                ? `
                                    <div
                                        class="player-database-player-teams"
                                    >

                                        <span>
                                            소속팀
                                        </span>

                                        <p>
                                            ${teams}
                                        </p>

                                    </div>
                                `
                                : ""
                        }


                        <!-- =========================
                            능력치
                        ========================== -->

                        <div
                            class="player-database-player-stats"
                        >

                            ${createPlayerStatsHtml(
                                player
                            )}

                        </div>

                        <!-- =========================
                            이적시장 시세
                        ========================== -->

                        ${createPlayerMarketPriceHtml(
                            player
                        )}

                    </div>

                </div>

            </div>

        </article>
    `;
}

function rerenderPlayerCard(
    spId
) {

    const numericSpId =
        Number(
            spId
        );


    const player =
        playerDataBySpId.get(
            numericSpId
        );


    if (!player) {
        return;
    }


    const oldItemElement =
        playerResultListElement
            .querySelector(
                (
                    `.player-database-player-item`
                    +
                    `[data-sp-id="${numericSpId}"]`
                )
            );


    if (!oldItemElement) {
        return;
    }


    const oldDetailElement =
        oldItemElement.querySelector(
            ".player-database-player-detail"
        );


    const wasOpen =
        oldDetailElement
        &&
        !oldDetailElement.hidden;


    oldItemElement.outerHTML =
        createPlayerCardHtml(
            player
        );


    if (!wasOpen) {
        return;
    }


    const newItemElement =
        playerResultListElement
            .querySelector(
                (
                    `.player-database-player-item`
                    +
                    `[data-sp-id="${numericSpId}"]`
                )
            );


    if (!newItemElement) {
        return;
    }


    const newDetailElement =
        newItemElement.querySelector(
            ".player-database-player-detail"
        );


    const newRowElement =
        newItemElement.querySelector(
            ".player-database-player-row"
        );


    const newArrowElement =
        newItemElement.querySelector(
            ".player-database-player-arrow"
        );


    if (newDetailElement) {

        newDetailElement.hidden =
            false;
    }


    if (newRowElement) {

        newRowElement.setAttribute(
            "aria-expanded",
            "true"
        );
    }


    if (newArrowElement) {

        newArrowElement.textContent =
            "▲";
    }
}

function moveCompareBasePlayerToTop() {

    if (
        compareState.basePlayerSpId
        === null
    ) {
        return;
    }


    const basePlayerElement =
        playerResultListElement
            .querySelector(
                (
                    `.player-database-player-item`
                    +
                    `[data-sp-id="${compareState.basePlayerSpId}"]`
                )
            );


    if (!basePlayerElement) {
        return;
    }


    playerResultListElement.prepend(
        basePlayerElement
    );
}

function getComparePlayer(
    spId,
    side
) {

    const numericSpId =
        Number(
            spId
        );


    const originalPlayer =
        playerDataBySpId.get(
            numericSpId
        );


    if (!originalPlayer) {
        return null;
    }


    const state =
        compareControlState[
            side
        ];


    if (!state) {
        return null;
    }


    const gradeBonus =
        enhancementBonusMap[
            state.grade
        ]
        ?? 0;


    const adaptationBonus =
        adaptationBonusMap[
            state.adaptation
        ]
        ?? 0;


    const teamColorBonus =
        Number(
            state.teamColor
            ?? 0
        );


    const newAbilityBonus =
        gradeBonus
        +
        adaptationBonus
        +
        teamColorBonus;


    const sourceAbilityBonus =
        Number(
            originalPlayer.ability_bonus
            ?? 0
        );


    const adjustedStats =
        Object.fromEntries(
            Object.entries(
                originalPlayer.stats
                ?? {}
            )
                .map(
                    (
                        [
                            statName,
                            statValue,
                        ]
                    ) => {

                        const baseStat =
                            Number(
                                statValue
                            )
                            -
                            sourceAbilityBonus;


                        return [
                            statName,
                            baseStat
                            +
                            newAbilityBonus,
                        ];
                    }
                )
        );


    const baseOvr =
        Number(
            originalPlayer.base_ovr
            ??
            (
                Number(
                    originalPlayer.ovr
                    ?? 0
                )
                -
                sourceAbilityBonus
            )
        );


    return {
        ...originalPlayer,

        grade:
            state.grade,

        adaptation:
            state.adaptation,

        team_color_bonus:
            state.teamColor,

        ability_bonus:
            newAbilityBonus,

        ovr:
            baseOvr
            +
            newAbilityBonus,

        stats:
            adjustedStats,
    };
}

function getRecommendBasePlayer(
    spId
) {
    const numericSpId =
        Number(spId);

    const originalPlayer =
        playerDataBySpId.get(
            numericSpId
        );

    if (!originalPlayer) {
        return null;
    }

    const state =
        getPlayerCardState(
            numericSpId
        );

    const gradeBonus =
        enhancementBonusMap[
            Number(
                state.grade ?? 1
            )
        ] ?? 0;

    const adaptationBonus =
        adaptationBonusMap[
            Number(
                state.adaptation ?? 1
            )
        ] ?? 0;

    const teamColorBonus =
        Number(
            state.teamColor ?? 0
        );

    const newAbilityBonus =
        gradeBonus +
        adaptationBonus +
        teamColorBonus;

    const sourceAbilityBonus =
        Number(
            originalPlayer.ability_bonus
            ?? 0
        );

    const adjustedStats =
        Object.fromEntries(
            Object.entries(
                originalPlayer.stats ?? {}
            ).map(
                ([statName, statValue]) => {
                    const baseStat =
                        Number(statValue) -
                        sourceAbilityBonus;

                    return [
                        statName,
                        baseStat +
                        newAbilityBonus,
                    ];
                }
            )
        );

    const baseOvr =
        Number(
            originalPlayer.base_ovr
            ?? (
                Number(
                    originalPlayer.ovr ?? 0
                ) - sourceAbilityBonus
            )
        );

    return {
        ...originalPlayer,
        grade:
            Number(
                state.grade ?? 1
            ),
        adaptation:
            Number(
                state.adaptation ?? 1
            ),
        team_color_bonus:
            teamColorBonus,
        ability_bonus:
            newAbilityBonus,
        ovr:
            baseOvr +
            newAbilityBonus,
        stats:
            adjustedStats,
    };
}

let recommendationRows = [];

function createRecommendGradeOptionsHtml(
    selectedGrade
) {
    return Array
        .from(
            {
                length: 13,
            },
            (
                _,
                index
            ) => {

                const grade =
                    index + 1;


                return `
                    <button
                        type="button"
                        class="
                            player-compare-grade-option
                            grade-${grade}
                            ${
                                grade
                                === Number(
                                    selectedGrade
                                )
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-recommend-base-grade="${grade}"
                        aria-label="${grade}강"
                        title="${grade}강"
                    >
                        +${grade}
                    </button>
                `;
            }
        )
        .join(
            ""
        );
}


function createRecommendGradeDropdownHtml(
    selectedGrade
) {
    const grade =
        Number(
            selectedGrade
            ?? 1
        );


    return `
        <details
            class="
                player-compare-grade-dropdown
                player-recommend-grade-dropdown
            "
        >

            <summary
                class="
                    player-compare-grade-trigger
                    grade-${grade}
                "
                aria-label="${grade}강 선택"
                title="${grade}강"
            >
                +${grade}
            </summary>


            <div
                class="player-compare-grade-menu"
            >

                ${createRecommendGradeOptionsHtml(
                    grade
                )}

            </div>

        </details>
    `;
}


function createRecommendTeamColorOptionsHtml(
    selectedTeamColorId
) {
    const selectedId =
        (
            selectedTeamColorId
            === null
            ||
            selectedTeamColorId
            === undefined
            ||
            selectedTeamColorId
            === ""
        )
            ? null
            : Number(
                selectedTeamColorId
            );


    const groupHtml =
        teamGroups
            .map(
                group => {

                    const optionHtml =
                        (
                            group.teams
                            ?? []
                        )
                            .map(
                                team => {

                                    const teamColorId =
                                        Number(
                                            team.team_color_id
                                        );


                                    return `
                                        <option
                                            value="${teamColorId}"
                                            ${
                                                selectedId
                                                === teamColorId
                                                    ? "selected"
                                                    : ""
                                            }
                                        >
                                            ${escapeHtml(
                                                team.team_name
                                            )}
                                        </option>
                                    `;
                                }
                            )
                            .join(
                                ""
                            );


                    if (!optionHtml) {
                        return "";
                    }


                    return `
                        <optgroup
                            label="${escapeHtml(
                                group.league_name
                                ?? "기타"
                            )}"
                        >
                            ${optionHtml}
                        </optgroup>
                    `;
                }
            )
            .join(
                ""
            );


    return `
        <option
            value=""
            ${
                selectedId === null
                    ? "selected"
                    : ""
            }
        >
            전체 팀컬러
        </option>

        ${groupHtml}
    `;
}


function createRecommendOvrOptionsHtml(
    minimum,
    maximum,
    selectedValue
) {
    const start =
        Math.max(
            0,
            Number(
                minimum
                ?? 0
            )
        );


    const end =
        Math.max(
            start,
            Number(
                maximum
                ?? start
            )
        );


    const selected =
        Number(
            selectedValue
            ?? start
        );


    return Array
        .from(
            {
                length:
                    (
                        end
                        -
                        start
                        +
                        1
                    ),
            },
            (
                _,
                index
            ) => {

                const value =
                    start + index;


                return `
                    <option
                        value="${value}"
                        ${
                            value === selected
                                ? "selected"
                                : ""
                        }
                    >
                        ${value}
                    </option>
                `;
            }
        )
        .join(
            ""
        );
}


function createRecommendMarketPriceHtml(
    player
) {
    const spId =
        Number(
            player.sp_id
        );


    const grade =
        Number(
            player.grade
            ?? 1
        );


    const marketData =
        playerMarketPriceBySpId
            .get(
                spId
            );


    const isLoading =
        playerMarketPriceLoadingSpIds
            .has(
                spId
            );


    const errorMessage =
        playerMarketPriceErrorBySpId
            .get(
                spId
            );


    let statusClass =
        "";

    let priceText =
        "-";


    if (isLoading) {

        statusClass =
            "loading";

        priceText =
            "불러오는 중...";

    } else if (errorMessage) {

        statusClass =
            "error";

        priceText =
            "시세 조회 실패";

    } else if (marketData) {

        const priceData =
            (
                marketData.prices
                ?? []
            )
                .find(
                    item =>
                        Number(
                            item.grade
                        )
                        === grade
                );


        priceText =
            formatPlayerMarketPrice(
                priceData?.price
            );

    } else {

        priceText =
            "조회 대기";
    }


    return `
        <div
            class="
                player-recommend-market-price
                ${statusClass}
            "
            data-recommend-market-price
        >

            <span
                class="player-recommend-market-price-label"
            >
                이적시장 시세
            </span>


            <div
                class="player-recommend-market-price-info"
            >

                <span
                    class="
                        player-compare-market-grade
                        grade-${grade}
                    "
                >
                    +${grade}
                </span>


                <strong>
                    ${escapeHtml(
                        priceText
                    )}
                </strong>

            </div>

        </div>
    `;
}


function refreshRecommendMarketPrice() {

    const marketPriceElement =
        playerRecommendContentElement
            ?.querySelector(
                "[data-recommend-market-price]"
            );


    if (!marketPriceElement) {
        return;
    }


    const basePlayer =
        getRecommendBasePlayer(
            recommendState
                .basePlayerSpId
        );


    if (!basePlayer) {
        return;
    }


    marketPriceElement.outerHTML =
        createRecommendMarketPriceHtml(
            basePlayer
        );
}

function createRecommendBasePlayerHtml(
    player
) {
    const seasonImageUrl =
        `${apiBaseUrl}/api/fconline/metadata/seasons/${player.season_id}/image`;

    const speedValue =
        getCompareSummaryValue(
            player,
            ["속력", "가속력"]
        );

    const shotValue =
        getCompareSummaryValue(
            player,
            [
                "골 결정력",
                "슛 파워",
                "중거리 슛",
                "위치 선정",
                "발리슛",
            ]
        );

    const passValue =
        getCompareSummaryValue(
            player,
            [
                "짧은 패스",
                "긴 패스",
                "시야",
                "크로스",
                "커브",
            ]
        );

    const dribbleValue =
        getCompareSummaryValue(
            player,
            [
                "드리블",
                "볼 컨트롤",
                "민첩성",
                "밸런스",
                "반응 속도",
            ]
        );

    const defenseValue =
        getCompareSummaryValue(
            player,
            [
                "대인 수비",
                "태클",
                "가로채기",
                "슬라이딩 태클",
            ]
        );

    const physicalValue =
        getCompareSummaryValue(
            player,
            [
                "몸싸움",
                "스태미너",
                "적극성",
                "점프",
                "헤더",
            ]
        );

    return `
        <section class="player-recommend-panel player-recommend-base-panel">

            <div class="player-recommend-panel-title">
                기준 선수
            </div>

            <div class="player-recommend-base-card">

                <div class="player-recommend-base-top">
                    <div class="player-recommend-base-info">

                        <div class="player-recommend-base-name-row">
                            <img
                                src="${escapeHtml(seasonImageUrl)}"
                                alt=""
                                class="player-recommend-season-icon"
                            >

                            <strong class="player-recommend-base-name">
                                ${escapeHtml(player.player_name)}
                            </strong>
                        </div>

                        <div class="player-recommend-base-meta-row">
                            <span
                                class="
                                    player-recommend-base-position
                                    ${getPositionGroupClass(
                                        player.position
                                    )}
                                "
                            >
                                ${escapeHtml(
                                    player.position
                                )}
                            </span>

                            <strong class="player-recommend-base-ovr">
                                ${player.ovr}
                            </strong>
                        </div>

                        <div class="player-recommend-base-meta-text">
                            <span>${escapeHtml(player.nation_name ?? "-")}</span>
                            <span>급여 ${player.salary}</span>
                            <span>${player.height}cm</span>
                            <span>${player.weight}kg</span>
                        </div>

                        <div class="player-recommend-base-foot-row">
                            ${createCompareFootHtml(player)}
                        </div>

                    </div>

                    <div class="player-recommend-base-photo-wrap">
                        <img
                            src="${escapeHtml(
                                player.image_url
                                ?? ""
                            )}"
                            alt="${escapeHtml(
                                player.player_name
                            )}"
                            class="player-recommend-base-photo"
                            data-player-image
                        >
                    </div>
                </div>

                <div class="player-recommend-base-controls">
                    <div
                        class="player-recommend-base-control"
                    >
                        <span>
                            강화
                        </span>

                        ${createRecommendGradeDropdownHtml(
                            player.grade
                        )}
                    </div>

                    <label>
                        <span>적응도</span>
                        <select
                            data-recommend-base-adaptation
                        >
                            ${createCompareAdaptationSelectOptionsHtml(
                                player.adaptation
                            )}
                        </select>
                    </label>

                    <label>
                        <span>팀컬러</span>
                        <select
                            data-recommend-base-team-color
                        >
                            ${createPlayerTeamColorOptionsHtml(
                                player.team_color_bonus
                            )}
                        </select>
                    </label>
                </div>

                <div class="player-recommend-base-summary">

                    <div>
                        <span>스피드</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                speedValue
                            )}"
                        >
                            ${speedValue}
                        </strong>
                    </div>


                    <div>
                        <span>슛</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                shotValue
                            )}"
                        >
                            ${shotValue}
                        </strong>
                    </div>


                    <div>
                        <span>패스</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                passValue
                            )}"
                        >
                            ${passValue}
                        </strong>
                    </div>


                    <div>
                        <span>드리블</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                dribbleValue
                            )}"
                        >
                            ${dribbleValue}
                        </strong>
                    </div>


                    <div>
                        <span>수비</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                defenseValue
                            )}"
                        >
                            ${defenseValue}
                        </strong>
                    </div>


                    <div>
                        <span>피지컬</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                physicalValue
                            )}"
                        >
                            ${physicalValue}
                        </strong>
                    </div>


                    <div>
                        <span>OVR</span>

                        <strong
                            class="${getPlayerStatColorClass(
                                player.ovr
                            )}"
                        >
                            ${player.ovr}
                        </strong>
                    </div>

                </div>

                ${createRecommendMarketPriceHtml(
                    player
                )}

            </div>
        </section>
    `;
}

function createRecommendFilterPanelHtml(
    player
) {
    const playerOvr =
        Number(
            player.ovr
            ?? 0
        );


    const rangeMin =
        Math.max(
            0,
            playerOvr - 20
        );


    const rangeMax =
        playerOvr + 20;


    return `
        <section
            class="
                player-recommend-panel
                player-recommend-filter-panel
            "
        >

            <div class="player-recommend-panel-title">
                추천 조건
            </div>


            <!-- =================================
                 POSITION
            ================================== -->

            <div class="player-recommend-filter-group">

                <span class="player-recommend-filter-label">
                    포지션
                </span>


                <div
                    class="player-recommend-chip-row"
                    data-recommend-position-group
                >

                    <button
                        type="button"
                        class="
                            player-recommend-chip
                            ${
                                recommendState.selectedPosition
                                === "same"
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-recommend-position="same"
                    >
                        동일 포지션
                        (${escapeHtml(
                            player.position
                        )})
                    </button>


                    <button
                        type="button"
                        class="
                            player-recommend-chip
                            ${
                                recommendState.selectedPosition
                                === "all"
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-recommend-position="all"
                    >
                        모든 포지션
                    </button>

                </div>

            </div>


            <!-- =================================
                 SALARY
            ================================== -->

            <div class="player-recommend-filter-group">

                <span class="player-recommend-filter-label">
                    급여 범위
                </span>


                <div
                    class="player-recommend-chip-row"
                    data-recommend-salary-group
                >

                    <button
                        type="button"
                        class="
                            player-recommend-chip
                            ${
                                recommendState.selectedSalaryMode
                                === "any"
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-recommend-salary-mode="any"
                    >
                        상한없음
                    </button>


                    <button
                        type="button"
                        class="
                            player-recommend-chip
                            ${
                                recommendState.selectedSalaryMode
                                === "same_or_below"
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-recommend-salary-mode="same_or_below"
                    >
                        이하
                    </button>

                </div>

            </div>


            <!-- =================================
                 TEAM COLOR
            ================================== -->

            <div class="player-recommend-filter-group">

                <span class="player-recommend-filter-label">
                    팀컬러
                </span>


                <select
                    class="player-recommend-team-color-select"
                    data-recommend-team-color
                >
                    ${createRecommendTeamColorOptionsHtml(
                        recommendState.selectedTeamColorId
                    )}
                </select>

            </div>


            <!-- =================================
                 OVR
            ================================== -->

            <div class="player-recommend-filter-group">

                <span class="player-recommend-filter-label">
                    OVR 범위
                </span>


                <div
                    class="player-recommend-ovr-select-row"
                >

                    <label>
                        <span>
                            최소
                        </span>

                        <select
                            class="player-recommend-ovr-select"
                            data-recommend-ovr-min
                        >
                            ${createRecommendOvrOptionsHtml(
                                rangeMin,
                                rangeMax,
                                recommendState.ovrMin
                            )}
                        </select>
                    </label>


                    <label>
                        <span>
                            최대
                        </span>

                        <select
                            class="player-recommend-ovr-select"
                            data-recommend-ovr-max
                        >
                            ${createRecommendOvrOptionsHtml(
                                rangeMin,
                                rangeMax,
                                recommendState.ovrMax
                            )}
                        </select>
                    </label>

                </div>

            </div>


            <!-- =================================
                 LIMIT
            ================================== -->

            <div class="player-recommend-filter-group">

                <span class="player-recommend-filter-label">
                    추천 수
                </span>


                <select
                    class="player-recommend-limit-select"
                    data-recommend-limit
                >

                    <option
                        value="5"
                        ${
                            recommendState.limit === 5
                                ? "selected"
                                : ""
                        }
                    >
                        5명
                    </option>


                    <option
                        value="10"
                        ${
                            recommendState.limit === 10
                                ? "selected"
                                : ""
                        }
                    >
                        10명
                    </option>


                    <option
                        value="20"
                        ${
                            recommendState.limit === 20
                                ? "selected"
                                : ""
                        }
                    >
                        20명
                    </option>

                </select>

            </div>


            <!-- =================================
                 SEARCH
            ================================== -->

            <div class="player-recommend-filter-actions">

                <button
                    type="button"
                    class="player-recommend-refresh-button"
                    data-recommend-refresh
                >
                    재검색
                </button>

            </div>

        </section>
    `;
}

function createRecommendGuidePanelHtml() {
    return `
        <section class="player-recommend-panel player-recommend-guide-panel">

            <div class="player-recommend-panel-title">
                비교 기준 설명
            </div>

            <div class="player-recommend-radar-wrap">
                <canvas
                    id="player-recommend-radar-canvas"
                    width="280"
                    height="220"
                ></canvas>
            </div>

            <p class="player-recommend-guide-text">
                기준 선수의 6개 대표 능력치를 기준으로
                유사한 선수들을 추천합니다.
            </p>
        </section>
    `;
}

function createRecommendStarsHtml(
    count
) {
    return "★".repeat(count);
}

function createRecommendListHtml(
    rows = recommendationRows,
    options = {}
) {

    const loading =
        Boolean(
            options.loading
        );


    const errorMessage =
        String(
            options.errorMessage
            ?? ""
        );


    if (loading) {

        return `
            <section
                class="player-recommend-list-panel"
                id="player-recommend-list-panel"
            >

                <div class="player-recommend-list-header">
                    추천 선수 검색 중
                </div>

                <div class="player-recommend-empty">
                    실제 선수 데이터를 분석하고 있습니다.
                </div>

            </section>
        `;
    }


    if (errorMessage) {

        return `
            <section
                class="player-recommend-list-panel"
                id="player-recommend-list-panel"
            >

                <div class="player-recommend-list-header">
                    추천 선수 목록
                </div>

                <div class="player-recommend-empty">
                    ${escapeHtml(
                        errorMessage
                    )}
                </div>

            </section>
        `;
    }


    if (
        rows.length
        === 0
    ) {

        return `
            <section
                class="player-recommend-list-panel"
                id="player-recommend-list-panel"
            >

                <div class="player-recommend-list-header">
                    추천 선수 목록 (0명)
                </div>

                <div class="player-recommend-empty">
                    현재 조건에 맞는 추천 선수가 없습니다.
                </div>

            </section>
        `;
    }


    return `
        <section
            class="player-recommend-list-panel"
            id="player-recommend-list-panel"
        >

            <div class="player-recommend-list-header">
                추천 선수 목록 (${rows.length}명)
            </div>


            <div class="player-recommend-table-wrap">

                <table class="player-recommend-table">

                    <thead>

                        <tr>
                            <th>순위</th>
                            <th>선수 정보</th>
                            <th>유사도</th>
                            <th>급여</th>
                            <th>OVR</th>
                            <th>스피드</th>
                            <th>슛</th>
                            <th>패스</th>
                            <th>드리블</th>
                            <th>피지컬</th>
                            <th>주발</th>
                            <th>특징 요약</th>
                            <th>비교</th>
                        </tr>

                    </thead>


                    <tbody>

                        ${
                            rows
                                .map(
                                    row => {

                                        const seasonImageUrl =
                                            (
                                                `${apiBaseUrl}`
                                                +
                                                `/api/fconline/metadata/seasons/`
                                                +
                                                `${row.season_id}/image`
                                            );


                                        return `
                                            <tr>

                                                <td class="rank">

                                                    ${row.rank}

                                                </td>


                                                <td class="player-cell">

                                                    <div class="player-main">

                                                        <div class="season-badge">

                                                            <img
                                                                src="${escapeHtml(
                                                                    seasonImageUrl
                                                                )}"
                                                                alt=""
                                                                class="player-recommend-season-icon"
                                                            >

                                                        </div>


                                                        <div class="player-text">

                                                            <strong>

                                                                ${escapeHtml(
                                                                    row.player_name
                                                                )}

                                                            </strong>


                                                            <div>

                                                                ${escapeHtml(
                                                                    row.position
                                                                )}
                                                                ·
                                                                OVR
                                                                ${row.ovr}

                                                            </div>


                                                            <div>

                                                                ${escapeHtml(
                                                                    row.nation_name
                                                                    ?? ""
                                                                )}

                                                            </div>

                                                        </div>

                                                    </div>

                                                </td>


                                                <td class="similarity">

                                                    ${row.similarity}%

                                                    <div class="stars">

                                                        ${createRecommendStarsHtml(
                                                            row.stars
                                                        )}

                                                    </div>

                                                </td>


                                                <td>
                                                    ${row.salary}
                                                </td>


                                                <td>

                                                    ${row.ovr}

                                                </td>


                                                <td>
                                                    ${row.speed}
                                                </td>


                                                <td>
                                                    ${row.shot}
                                                </td>


                                                <td>
                                                    ${row.pass}
                                                </td>


                                                <td>
                                                    ${row.dribble}
                                                </td>


                                                <td>
                                                    ${row.physical}
                                                </td>


                                                <td>

                                                    ${escapeHtml(
                                                        row.foot
                                                    )}

                                                </td>


                                                <td class="summary-cell">

                                                    <div class="pros">

                                                        + ${
                                                            (
                                                                row.pros
                                                                ?? []
                                                            )
                                                                .join(
                                                                    ", "
                                                                )
                                                        }

                                                    </div>


                                                    ${
                                                        (
                                                            row.cons
                                                            ?? []
                                                        ).length > 0
                                                            ? `
                                                                <div class="cons">

                                                                    - ${
                                                                        row.cons.join(
                                                                            ", "
                                                                        )
                                                                    }

                                                                </div>
                                                            `
                                                            : ""
                                                    }

                                                </td>


                                                <td>

                                                    <button
                                                        type="button"
                                                        class="player-recommend-compare-button"
                                                        data-recommend-compare
                                                        data-sp-id="${row.sp_id}"
                                                    >
                                                        비교하기
                                                    </button>

                                                </td>

                                            </tr>
                                        `;
                                    }
                                )
                                .join(
                                    ""
                                )
                        }

                    </tbody>

                </table>

            </div>

        </section>
    `;
}

async function loadPlayerRecommendations(
    basePlayer
) {

    const listPanelElement =
        playerRecommendContentElement
            .querySelector(
                "#player-recommend-list-panel"
            );


    if (listPanelElement) {

        listPanelElement.outerHTML =
            createRecommendListHtml(
                [],
                {
                    loading:
                        true,
                }
            );
    }


    const params =
        new URLSearchParams();


    params.set(
        "base_sp_id",
        String(
            basePlayer.sp_id
        )
    );


    params.set(
        "grade",
        String(
            basePlayer.grade
            ?? 1
        )
    );


    params.set(
        "adaptation",
        String(
            basePlayer.adaptation
            ?? 1
        )
    );


    params.set(
        "team_color",
        String(
            basePlayer.team_color_bonus
            ?? 0
        )
    );


    params.set(
        "position_mode",
        recommendState
            .selectedPosition
    );


    params.set(
        "salary_mode",
        recommendState
            .selectedSalaryMode
    );

    if (
        recommendState.selectedTeamColorId
        !== null
    ) {

        params.set(
            "team_color_id",
            String(
                recommendState
                    .selectedTeamColorId
            )
        );
    }



    if (
        recommendState.ovrMin
        !== null
    ) {

        params.set(
            "ovr_min",
            String(
                recommendState.ovrMin
            )
        );
    }


    if (
        recommendState.ovrMax
        !== null
    ) {

        params.set(
            "ovr_max",
            String(
                recommendState.ovrMax
            )
        );
    }


    params.set(
        "limit",
        String(
            recommendState.limit
        )
    );


    try {

        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    "/api/player-database/recommend?"
                    +
                    params.toString()
                )
            );


        if (!response.ok) {

            const errorData =
                await response
                    .json()
                    .catch(
                        () => null
                    );


            throw new Error(
                errorData?.detail
                ??
                "추천 선수 검색에 실패했습니다."
            );
        }


        const data =
            await response.json();


        recommendationRows =
            data.players
            ?? [];


        const currentListPanelElement =
            playerRecommendContentElement
                .querySelector(
                    "#player-recommend-list-panel"
                );


        if (
            currentListPanelElement
        ) {

            currentListPanelElement.outerHTML =
                createRecommendListHtml(
                    recommendationRows
                );
        }

    }

    catch (
        error
    ) {

        console.error(
            error
        );


        const currentListPanelElement =
            playerRecommendContentElement
                .querySelector(
                    "#player-recommend-list-panel"
                );


        if (
            currentListPanelElement
        ) {

            currentListPanelElement.outerHTML =
                createRecommendListHtml(
                    [],
                    {
                        errorMessage:
                            (
                                error.message
                                ??
                                "추천 선수 검색에 실패했습니다."
                            ),
                    }
                );
        }
    }
}

function renderPlayerRecommendModal() {

    const basePlayer =
        getRecommendBasePlayer(
            recommendState
                .basePlayerSpId
        );


    if (!basePlayer) {

        playerRecommendContentElement
            .innerHTML =
                `
                    <div class="player-recommend-empty">

                        기준 선수 정보를 불러오지 못했습니다.

                    </div>
                `;

        return;
    }


    recommendationRows =
        [];


    playerRecommendContentElement
        .innerHTML =
            `
                <div class="player-recommend-top-grid">

                    ${createRecommendBasePlayerHtml(
                        basePlayer
                    )}

                    ${createRecommendFilterPanelHtml(
                        basePlayer
                    )}

                    ${createRecommendGuidePanelHtml()}

                </div>


                ${createRecommendListHtml(
                    [],
                    {
                        loading:
                            true,
                    }
                )}
            `;

    initializePlayerImageFallbacks(
        playerRecommendContentElement
    );


    requestAnimationFrame(
        () => {

            drawRecommendRadarChart(
                basePlayer
            );
        }
    );


    loadPlayerRecommendations(
        basePlayer
    );
}

function openPlayerRecommendModal(
    spId
) {

    recommendState.basePlayerSpId =
        Number(
            spId
        );


    recommendState
        .selectedPosition =
            "same";


    recommendState
        .selectedSalaryMode =
            "any";

    recommendState
        .selectedTeamColorId =
            null;


    recommendState.limit =
        10;


    const basePlayer =
        getRecommendBasePlayer(
            spId
        );


    if (
        basePlayer
    ) {

        recommendState.ovrMin =
            Math.max(
                0,
                Number(
                    basePlayer.ovr
                    ?? 0
                )
                -
                10
            );


        recommendState.ovrMax =
            (
                Number(
                    basePlayer.ovr
                    ?? 0
                )
                +
                10
            );
    }


    renderPlayerRecommendModal();


    playerRecommendModalElement.hidden =
        false;


    document.body
        .classList
        .add(
            "player-recommend-open"
        );

    const marketPricePromise =
        loadPlayerMarketPrice(
            Number(
                spId
            )
        );


    refreshRecommendMarketPrice();


    marketPricePromise
        .finally(
            () => {

                if (
                    Number(
                        recommendState
                            .basePlayerSpId
                    )
                    !==
                    Number(
                        spId
                    )
                ) {
                    return;
                }


                refreshRecommendMarketPrice();
            }
        );

}

function closePlayerRecommendModal() {
    playerRecommendModalElement.hidden =
        true;

    document.body.classList.remove(
        "player-recommend-open"
    );
}

function openRecommendedPlayerCompare(
    targetSpId
) {

    // =====================================
    // 기준 선수 / 비교 선수 ID
    // =====================================

    const baseSpId =
        Number(
            recommendState
                .basePlayerSpId
        );


    const numericTargetSpId =
        Number(
            targetSpId
        );


    if (
        !Number.isFinite(
            baseSpId
        )
        ||
        !Number.isFinite(
            numericTargetSpId
        )
    ) {

        return;
    }


    // =====================================
    // 추천 목록에서 비교 선수 찾기
    // =====================================

    const targetPlayer =
        recommendationRows.find(
            player =>
                Number(
                    player.sp_id
                )
                ===
                numericTargetSpId
        );


    if (!targetPlayer) {

        return;
    }


    // =====================================
    // 기준 선수의 현재 설정값
    //
    // 추천창에서 사용자가 선택한
    // 강화 / 적응도 / 팀컬러
    // =====================================

    const baseCardState =
        getPlayerCardState(
            baseSpId
        );


    const sharedGrade =
        Number(
            baseCardState.grade
            ?? 1
        );


    const sharedAdaptation =
        Number(
            baseCardState.adaptation
            ?? 1
        );


    const sharedTeamColor =
        Number(
            baseCardState.teamColor
            ?? 0
        );


    // =====================================
    // 추천 선수를 비교 시스템에 등록
    // =====================================

    const existingTargetPlayer =
        playerDataBySpId.get(
            numericTargetSpId
        );


    playerDataBySpId.set(
        numericTargetSpId,
        {
            ...(
                existingTargetPlayer
                ?? {}
            ),

            ...targetPlayer,
        }
    );


    // =====================================
    // 비교 선수도 기준 선수와
    // 완전히 동일한 조건으로 시작
    // =====================================

    const targetCardState =
        getPlayerCardState(
            numericTargetSpId
        );


    targetCardState.grade =
        sharedGrade;


    targetCardState.adaptation =
        sharedAdaptation;


    targetCardState.teamColor =
        sharedTeamColor;


    // =====================================
    // 포지션 비교 탭 초기화
    // =====================================

    compareState.activePosition =
        "all";


    // =====================================
    // 추천창 닫기
    // =====================================

    closePlayerRecommendModal();


    // =====================================
    // 기존 선수 비교창 열기
    // =====================================

    openPlayerCompareModal(
        baseSpId,
        numericTargetSpId
    );
}

function drawRecommendRadarChart(
    player
) {
    const canvas =
        document.querySelector(
            "#player-recommend-radar-canvas"
        );

    if (!canvas) {
        return;
    }

    const context =
        canvas.getContext("2d");

    const width =
        canvas.width;

    const height =
        canvas.height;

    context.clearRect(
        0,
        0,
        width,
        height
    );

    const categories = [
        {
            label: "스피드",
            value: getCompareSummaryValue(
                player,
                ["속력", "가속력"]
            ),
        },
        {
            label: "슛",
            value: getCompareSummaryValue(
                player,
                [
                    "골 결정력",
                    "슛 파워",
                    "중거리 슛",
                    "위치 선정",
                    "발리슛",
                ]
            ),
        },
        {
            label: "패스",
            value: getCompareSummaryValue(
                player,
                [
                    "짧은 패스",
                    "긴 패스",
                    "시야",
                    "크로스",
                    "커브",
                ]
            ),
        },
        {
            label: "드리블",
            value: getCompareSummaryValue(
                player,
                [
                    "드리블",
                    "볼 컨트롤",
                    "민첩성",
                    "밸런스",
                    "반응 속도",
                ]
            ),
        },
        {
            label: "수비",
            value: getCompareSummaryValue(
                player,
                [
                    "대인 수비",
                    "태클",
                    "가로채기",
                    "슬라이딩 태클",
                ]
            ),
        },
        {
            label: "피지컬",
            value: getCompareSummaryValue(
                player,
                [
                    "몸싸움",
                    "스태미너",
                    "적극성",
                    "점프",
                    "헤더",
                ]
            ),
        },
    ];

    const centerX = width / 2;
    const centerY = height / 2 + 6;
    const radius = 72;
    const steps = 5;
    const startAngle = -Math.PI / 2;

    context.strokeStyle =
        "rgba(255,255,255,0.10)";
    context.lineWidth = 1;

    for (
        let step = 1;
        step <= steps;
        step += 1
    ) {
        const currentRadius =
            (radius / steps) * step;

        context.beginPath();

        categories.forEach(
            (_category, index) => {
                const angle =
                    startAngle +
                    (
                        (Math.PI * 2) /
                        categories.length
                    ) *
                    index;

                const x =
                    centerX +
                    Math.cos(angle) *
                    currentRadius;

                const y =
                    centerY +
                    Math.sin(angle) *
                    currentRadius;

                if (index === 0) {
                    context.moveTo(x, y);
                } else {
                    context.lineTo(x, y);
                }
            }
        );

        context.closePath();
        context.stroke();
    }

    categories.forEach(
        (category, index) => {
            const angle =
                startAngle +
                (
                    (Math.PI * 2) /
                    categories.length
                ) *
                index;

            const x =
                centerX +
                Math.cos(angle) * radius;

            const y =
                centerY +
                Math.sin(angle) * radius;

            context.beginPath();
            context.moveTo(centerX, centerY);
            context.lineTo(x, y);
            context.stroke();

            const labelX =
                centerX +
                Math.cos(angle) * (radius + 18);

            const labelY =
                centerY +
                Math.sin(angle) * (radius + 18);

            context.fillStyle =
                "rgba(255,255,255,0.75)";
            context.font =
                "11px sans-serif";
            context.textAlign =
                "center";
            context.fillText(
                category.label,
                labelX,
                labelY
            );
        }
    );

    context.beginPath();

    categories.forEach(
        (category, index) => {
            const normalized =
                Math.max(
                    0,
                    Math.min(
                        1,
                        category.value / 160
                    )
                );

            const currentRadius =
                radius * normalized;

            const angle =
                startAngle +
                (
                    (Math.PI * 2) /
                    categories.length
                ) *
                index;

            const x =
                centerX +
                Math.cos(angle) *
                currentRadius;

            const y =
                centerY +
                Math.sin(angle) *
                currentRadius;

            if (index === 0) {
                context.moveTo(x, y);
            } else {
                context.lineTo(x, y);
            }
        }
    );

    context.closePath();
    context.fillStyle =
        "rgba(174, 79, 255, 0.28)";
    context.strokeStyle =
        "rgba(174, 79, 255, 0.9)";
    context.lineWidth = 2;
    context.fill();
    context.stroke();
}

function createCompareAdaptationOptionsHtml(
    side,
    selectedAdaptation
) {

    return `
        <button
            type="button"
            class="
                player-compare-adaptation-button
                ${
                    selectedAdaptation === 1
                        ? "selected"
                        : ""
                }
            "
            data-compare-adaptation="1"
            data-compare-side="${side}"
        >
            1
        </button>


        <button
            type="button"
            class="
                player-compare-adaptation-button
                ${
                    selectedAdaptation === 5
                        ? "selected"
                        : ""
                }
            "
            data-compare-adaptation="5"
            data-compare-side="${side}"
        >
            5
        </button>
    `;
}

function initializeCompareControlState() {

    const leftState =
        getPlayerCardState(
            compareState.basePlayerSpId
        );


    const rightState =
        getPlayerCardState(
            compareState.targetPlayerSpId
        );


    compareControlState.left = {
        grade:
            Number(
                leftState.grade
                ?? 1
            ),

        adaptation:
            Number(
                leftState.adaptation
                ?? 1
            ),

        teamColor:
            Number(
                leftState.teamColor
                ?? 0
            ),
    };


    compareControlState.right = {
        grade:
            Number(
                rightState.grade
                ?? 1
            ),

        adaptation:
            Number(
                rightState.adaptation
                ?? 1
            ),

        teamColor:
            Number(
                rightState.teamColor
                ?? 0
            ),
    };
}

function createCompareGradeOptionsHtml(
    side,
    selectedGrade
) {

    return Array
        .from(
            {
                length: 13,
            },
            (
                _,
                index
            ) => {

                const grade =
                    index + 1;


                return `
                    <button
                        type="button"
                        class="
                            player-compare-grade-option
                            grade-${grade}
                            ${
                                grade
                                === Number(
                                    selectedGrade
                                )
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-compare-grade="${grade}"
                        data-compare-side="${side}"
                        aria-label="${grade}강"
                        title="${grade}강"
                    >
                        +${grade}
                    </button>
                `;
            }
        )
        .join(
            ""
        );
}

function createCompareGradeDropdownHtml(
    side,
    selectedGrade
) {

    const grade =
        Number(
            selectedGrade
            ?? 1
        );


    return `
        <details
            class="player-compare-grade-dropdown"
        >

            <summary
                class="
                    player-compare-grade-trigger
                    grade-${grade}
                "
                aria-label="${grade}강 선택"
                title="${grade}강"
            >
                +${grade}
            </summary>


            <div
                class="player-compare-grade-menu"
            >

                ${createCompareGradeOptionsHtml(
                    side,
                    grade
                )}

            </div>

        </details>
    `;
}

function createCompareFootHtml(
    player
) {

    const leftFoot =
        Number(
            player.left_foot
            ?? 0
        );


    const rightFoot =
        Number(
            player.right_foot
            ?? 0
        );


    const leftMain =
        leftFoot >= rightFoot;


    const rightMain =
        rightFoot >= leftFoot;


    return `
        <div class="player-compare-foot">

            <span
                class="
                    player-compare-foot-item
                    ${
                        leftFoot === 5
                            ? "active"
                            : ""
                    }
                "
            >

                ${
                    leftMain
                        ? `
                            <small>
                                ★
                            </small>
                        `
                        : ""
                }

                L${leftFoot}

            </span>


            <span
                class="
                    player-compare-foot-item
                    ${
                        rightFoot === 5
                            ? "active"
                            : ""
                    }
                "
            >

                ${
                    rightMain
                        ? `
                            <small>
                                ★
                            </small>
                        `
                        : ""
                }

                R${rightFoot}

            </span>

        </div>
    `;
}

function createCompareGradeSelectOptionsHtml(
    selectedGrade
) {

    return Array
        .from(
            {
                length: 13,
            },
            (
                _,
                index
            ) => {

                const grade =
                    index + 1;


                return `
                    <option
                        value="${grade}"
                        ${
                            grade
                            === Number(selectedGrade)
                                ? "selected"
                                : ""
                        }
                    >
                        +${grade}
                    </option>
                `;
            }
        )
        .join(
            ""
        );
}


function createCompareAdaptationSelectOptionsHtml(
    selectedAdaptation
) {

    return [
        1,
        5,
    ]
        .map(
            adaptation => {

                return `
                    <option
                        value="${adaptation}"
                        ${
                            adaptation
                            === Number(selectedAdaptation)
                                ? "selected"
                                : ""
                        }
                    >
                        ${adaptation}
                    </option>
                `;
            }
        )
        .join(
            ""
        );
}

function createCompareMarketPriceHtml(
    player
) {

    const spId =
        Number(
            player.sp_id
        );


    const grade =
        Number(
            player.grade
            ?? 1
        );


    const marketData =
        playerMarketPriceBySpId
            .get(
                spId
            );


    const isLoading =
        playerMarketPriceLoadingSpIds
            .has(
                spId
            );


    const errorMessage =
        playerMarketPriceErrorBySpId
            .get(
                spId
            );


    let priceText =
        "-";


    let statusClass =
        "";


    if (isLoading) {

        priceText =
            "불러오는 중...";

        statusClass =
            "loading";

    } else if (errorMessage) {

        priceText =
            "조회 실패";

        statusClass =
            "error";

    } else if (marketData) {

        const priceData =
            (
                marketData.prices
                ??
                []
            )
                .find(
                    item =>
                        Number(
                            item.grade
                        )
                        === grade
                );


        priceText =
            formatPlayerMarketPrice(
                priceData?.price
            );
    }


    return `
        <div
            class="
                player-compare-market-price
                ${statusClass}
            "
        >

            <span
                class="player-compare-market-price-label"
            >
                이적시장 시세
            </span>


            <div
                class="player-compare-market-price-info"
            >

                <span
                    class="
                        player-compare-market-grade
                        grade-${grade}
                    "
                >
                    +${grade}
                </span>


                <strong>
                    ${escapeHtml(
                        priceText
                    )}
                </strong>

            </div>

        </div>
    `;
}

function createComparePlayerSummaryHtml(
    player,
    side
) {

    const seasonImageUrl =
        (
            `${apiBaseUrl}`
            +
            `/api/fconline/metadata/seasons/`
            +
            `${player.season_id}/image`
        );


    const isBasePlayer =
        side === "left";


    return `
        <article
            class="
                player-compare-player
                player-compare-player-${side}
            "
        >

            ${
                isBasePlayer
                    ? `
                        <span class="player-compare-base-badge">
                            비교 기준
                        </span>
                    `
                    : ""
            }


            <div class="player-compare-card-main">


                <!-- =================================
                     PLAYER INFO
                ================================== -->

                <div class="player-compare-card-info">


                    <div class="player-compare-card-identity">

                        <img
                            src="${escapeHtml(
                                seasonImageUrl
                            )}"
                            alt=""
                            class="player-compare-season"
                        >


                        <strong class="player-compare-name">
                            ${escapeHtml(
                                player.player_name
                            )}
                        </strong>

                    </div>


                    <div class="player-compare-card-position-row">

                        <strong class="player-compare-card-position">
                            ${escapeHtml(
                                player.position
                            )}
                        </strong>


                        <div class="player-compare-card-ovr">

                            <span>
                                OVR
                            </span>

                            <strong
                                class="${getPlayerStatColorClass(
                                    player.ovr
                                )}"
                            >
                                ${player.ovr}
                            </strong>

                        </div>

                    </div>


                    <div class="player-compare-basic-info">

                        <span>
                            ${escapeHtml(
                                player.nation_name
                                ?? "-"
                            )}
                        </span>

                        <span>
                            급여 ${player.salary}
                        </span>

                        <span>
                            ${player.height}cm
                        </span>

                        <span>
                            ${player.weight}kg
                        </span>

                    </div>


                    ${createCompareFootHtml(
                        player
                    )}

                </div>


                <!-- =================================
                     PLAYER PHOTO
                ================================== -->

                <div class="player-compare-photo-wrap">

                    <img
                        src="${escapeHtml(
                            player.image_url
                            ?? ""
                        )}"
                        alt="${escapeHtml(
                            player.player_name
                        )}"
                        class="player-compare-photo"
                        data-player-image
                    >

                </div>

            </div>


            <!-- =================================
                 CONTROLS
            ================================== -->

            <div class="player-compare-compact-controls">


                <div
                    class="
                        player-compare-compact-control
                        player-compare-grade-control
                    "
                >

                    <span>
                        강화
                    </span>


                    ${createCompareGradeDropdownHtml(
                        side,
                        player.grade
                    )}

                </div>


                <label class="player-compare-compact-control">

                    <span>
                        적응도
                    </span>

                    <select
                        data-compare-adaptation
                        data-compare-side="${side}"
                    >

                        ${createCompareAdaptationSelectOptionsHtml(
                            player.adaptation
                        )}

                    </select>

                </label>


                <label class="player-compare-compact-control">

                    <span>
                        팀컬러
                    </span>

                    <select
                        data-compare-team-color
                        data-compare-side="${side}"
                    >

                        ${createPlayerTeamColorOptionsHtml(
                            player.team_color_bonus
                        )}

                    </select>

                </label>

            </div>

            ${createCompareMarketPriceHtml(
                player
            )}

        </article>
    `;
}

const compareSummaryCategories = [

    {
        label:
            "스피드",

        stats: [
            "속력",
            "가속력",
        ],
    },


    {
        label:
            "슛",

        stats: [
            "골 결정력",
            "슛 파워",
            "중거리 슛",
            "위치 선정",
            "발리슛",
        ],
    },


    {
        label:
            "패스",

        stats: [
            "짧은 패스",
            "긴 패스",
            "시야",
            "크로스",
            "커브",
        ],
    },


    {
        label:
            "드리블",

        stats: [
            "드리블",
            "볼 컨트롤",
            "민첩성",
            "밸런스",
            "반응 속도",
        ],
    },


    {
        label:
            "수비",

        stats: [
            "대인 수비",
            "태클",
            "가로채기",
            "슬라이딩 태클",
        ],
    },


    {
        label:
            "피지컬",

        stats: [
            "몸싸움",
            "스태미너",
            "적극성",
            "점프",
            "헤더",
        ],
    },

];


function getCompareSummaryValue(
    player,
    statNames
) {

    const values =
        statNames
            .map(
                statName =>
                    Number(
                        player.stats?.[
                            statName
                        ]
                    )
            )
            .filter(
                value =>
                    Number.isFinite(
                        value
                    )
            );


    if (
        values.length
        === 0
    ) {

        return 0;
    }


    return Math.round(
        values.reduce(
            (
                total,
                value
            ) =>
                total + value,
            0
        )
        /
        values.length
    );
}


function createCompareSummaryHtml(
    basePlayer,
    targetPlayer
) {

    return `
        <div class="player-compare-summary">

            ${
                compareSummaryCategories
                    .map(
                        category => {

                            const leftValue =
                                getCompareSummaryValue(
                                    basePlayer,
                                    category.stats
                                );


                            const rightValue =
                                getCompareSummaryValue(
                                    targetPlayer,
                                    category.stats
                                );


                            return `
                                <div class="player-compare-summary-item">

                                    <span class="player-compare-summary-label">
                                        ${category.label}
                                    </span>


                                    <div class="player-compare-summary-values">

                                        <strong
                                            class="
                                                player-compare-summary-left
                                                ${
                                                    leftValue > rightValue
                                                        ? "higher"
                                                        : ""
                                                }
                                            "
                                        >
                                            ${leftValue}
                                        </strong>


                                        <strong
                                            class="
                                                player-compare-summary-right
                                                ${
                                                    rightValue > leftValue
                                                        ? "higher"
                                                        : ""
                                                }
                                            "
                                        >
                                            ${rightValue}
                                        </strong>

                                    </div>

                                </div>
                            `;
                        }
                    )
                    .join(
                        ""
                    )
            }

        </div>
    `;
}

// =========================================
// COMPARE POSITION STAT PRIORITY
// =========================================

function getComparePositionStatPriority(
    position
) {

    const positionValue =
        String(
            position
            ?? ""
        )
            .trim()
            .toUpperCase();


    // =====================================
    // GK
    // =====================================

    if (
        positionValue === "GK"
    ) {

        return [
            "GK 반응속도",
            "GK 다이빙",
            "GK 위치 선정",
            "GK 핸들링",
            "GK 킥",
            "반응 속도",
            "점프",
            "침착성",
        ];
    }


    // =====================================
    // CB / SW
    // =====================================

    if (
        [
            "SW",
            "RCB",
            "CB",
            "LCB",
        ].includes(
            positionValue
        )
    ) {

        return [
            "대인 수비",
            "태클",
            "가로채기",
            "헤더",
            "몸싸움",
            "적극성",
            "점프",
            "속력",
            "가속력",
            "반응 속도",
            "스태미너",
            "짧은 패스",
            "긴 패스",
            "침착성",
        ];
    }


    // =====================================
    // FB / WB
    // =====================================

    if (
        [
            "RWB",
            "RB",
            "LB",
            "LWB",
        ].includes(
            positionValue
        )
    ) {

        return [
            "속력",
            "가속력",
            "스태미너",
            "태클",
            "가로채기",
            "대인 수비",
            "크로스",
            "짧은 패스",
            "긴 패스",
            "적극성",
            "드리블",
            "볼 컨트롤",
            "민첩성",
            "몸싸움",
        ];
    }


    // =====================================
    // CDM
    // =====================================

    if (
        [
            "RDM",
            "CDM",
            "LDM",
        ].includes(
            positionValue
        )
    ) {

        return [
            "가로채기",
            "대인 수비",
            "태클",
            "몸싸움",
            "적극성",
            "스태미너",
            "짧은 패스",
            "긴 패스",
            "반응 속도",
            "헤더",
            "점프",
            "볼 컨트롤",
            "시야",
            "침착성",
        ];
    }


    // =====================================
    // CM
    // =====================================

    if (
        [
            "RCM",
            "CM",
            "LCM",
        ].includes(
            positionValue
        )
    ) {

        return [
            "짧은 패스",
            "긴 패스",
            "시야",
            "볼 컨트롤",
            "스태미너",
            "반응 속도",
            "드리블",
            "민첩성",
            "중거리 슛",
            "가로채기",
            "몸싸움",
            "침착성",
            "커브",
            "슛 파워",
        ];
    }


    // =====================================
    // RM / LM
    // =====================================

    if (
        [
            "RM",
            "LM",
        ].includes(
            positionValue
        )
    ) {

        return [
            "속력",
            "가속력",
            "스태미너",
            "크로스",
            "드리블",
            "볼 컨트롤",
            "민첩성",
            "짧은 패스",
            "시야",
            "커브",
            "골 결정력",
            "위치 선정",
            "반응 속도",
        ];
    }


    // =====================================
    // CAM
    // =====================================

    if (
        [
            "RAM",
            "CAM",
            "LAM",
        ].includes(
            positionValue
        )
    ) {

        return [
            "시야",
            "짧은 패스",
            "볼 컨트롤",
            "드리블",
            "민첩성",
            "중거리 슛",
            "골 결정력",
            "커브",
            "프리킥",
            "위치 선정",
            "반응 속도",
            "침착성",
            "가속력",
            "속력",
        ];
    }


    // =====================================
    // WING
    // =====================================

    if (
        [
            "RW",
            "LW",
            "RF",
            "LF",
        ].includes(
            positionValue
        )
    ) {

        return [
            "속력",
            "가속력",
            "드리블",
            "민첩성",
            "볼 컨트롤",
            "크로스",
            "골 결정력",
            "위치 선정",
            "커브",
            "짧은 패스",
            "시야",
            "반응 속도",
            "침착성",
            "슛 파워",
        ];
    }


    // =====================================
    // CF
    // =====================================

    if (
        positionValue === "CF"
    ) {

        return [
            "골 결정력",
            "위치 선정",
            "볼 컨트롤",
            "짧은 패스",
            "시야",
            "드리블",
            "반응 속도",
            "침착성",
            "속력",
            "가속력",
            "슛 파워",
            "중거리 슛",
            "몸싸움",
            "헤더",
        ];
    }


    // =====================================
    // ST
    // =====================================

    if (
        [
            "RS",
            "ST",
            "LS",
        ].includes(
            positionValue
        )
    ) {

        return [
            "골 결정력",
            "위치 선정",
            "속력",
            "가속력",
            "슛 파워",
            "헤더",
            "몸싸움",
            "반응 속도",
            "볼 컨트롤",
            "침착성",
            "점프",
            "드리블",
            "중거리 슛",
            "발리슛",
        ];
    }


    return [];
}

function getCompareStatNames(
    basePlayer,
    targetPlayer,
    position
) {

    const baseStats =
        basePlayer.stats
        ?? {};


    const targetStats =
        targetPlayer.stats
        ?? {};


    const allStatNames =
        Array.from(
            new Set([
                ...Object.keys(
                    baseStats
                ),

                ...Object.keys(
                    targetStats
                ),
            ])
        );


    // =====================================
    // 총 능력치
    //
    // 모든 상세 능력치 표시
    // =====================================

    if (
        position === "all"
    ) {

        return allStatNames;
    }


    // =====================================
    // 선택 포지션 핵심 능력치
    // =====================================

    const priorityStats =
        getComparePositionStatPriority(
            position
        );


    const existingPriorityStats =
        priorityStats.filter(
            statName =>
                allStatNames.includes(
                    statName
                )
        );


    // =====================================
    // 혹시 정의되지 않은 포지션이면
    // 빈 화면 대신 전체 능력치 표시
    // =====================================

    if (
        existingPriorityStats.length
        === 0
    ) {

        return allStatNames;
    }


    // =====================================
    // 포지션 선택 시
    // 핵심 능력치만 표시
    // =====================================

    return existingPriorityStats;
}

function createComparePositionTabsHtml(
    basePlayer,
    targetPlayer
) {

    const positions =
        Array.from(
            new Set([
                basePlayer.position,
                targetPlayer.position,
            ]
                .filter(
                    Boolean
                )
                .map(
                    position =>
                        String(
                            position
                        )
                            .trim()
                            .toUpperCase()
                )
            )
        );


    const tabs = [
        {
            value: "all",
            label: "총 능력치",
        },

        ...positions.map(
            position => ({
                value:
                    position,

                label:
                    position,
            })
        ),
    ];


    return tabs
        .map(
            tab => {

                const selected =
                    compareState.activePosition
                    === tab.value;


                const positionClass =
                    tab.value === "all"
                        ? ""
                        : getPositionGroupClass(
                            tab.value
                        );


                return `
                    <button
                        type="button"
                        class="
                            player-compare-position-tab
                            ${positionClass}
                            ${
                                selected
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-compare-position="${tab.value}"
                        aria-pressed="${
                            selected
                                ? "true"
                                : "false"
                        }"
                    >
                        ${escapeHtml(
                            tab.label
                        )}
                    </button>
                `;
            }
        )
        .join(
            ""
        );
}

function createCompareStatsHtml(
    basePlayer,
    targetPlayer,
    position = "all"
) {

    const baseStats =
        basePlayer.stats
        ?? {};


    const targetStats =
        targetPlayer.stats
        ?? {};


    const statNames =
        getCompareStatNames(
            basePlayer,
            targetPlayer,
            position
        );


    const priorityStats =
        position === "all"
            ? []
            : getComparePositionStatPriority(
                position
            );


    return statNames
        .map(
            statName => {

                const baseValue =
                    Number(
                        baseStats[
                            statName
                        ]
                        ?? 0
                    );


                const targetValue =
                    Number(
                        targetStats[
                            statName
                        ]
                        ?? 0
                    );


                const difference =
                    baseValue
                    -
                    targetValue;


                const leftDifference =
                    difference > 0
                        ? `+${difference}`
                        : "";


                const rightDifference =
                    difference < 0
                        ? `+${Math.abs(
                            difference
                        )}`
                        : "";


                const isPriorityStat =
                    position !== "all"
                    &&
                    priorityStats.includes(
                        statName
                    );


                return `
                    <div
                        class="
                            player-compare-stat-row
                            ${
                                isPriorityStat
                                    ? "priority"
                                    : ""
                            }
                        "
                    >

                        <div
                            class="
                                player-compare-stat-value
                                left
                            "
                        >

                            <strong
                                class="${getPlayerStatColorClass(
                                    baseValue
                                )}"
                            >
                                ${baseValue}
                            </strong>

                        </div>


                        <div class="player-compare-stat-center">

                            <span
                                class="
                                    player-compare-stat-difference
                                    left
                                "
                            >
                                ${leftDifference}
                            </span>


                            <span class="player-compare-stat-name">

                                ${escapeHtml(
                                    statName
                                )}

                            </span>


                            <span
                                class="
                                    player-compare-stat-difference
                                    right
                                "
                            >
                                ${rightDifference}
                            </span>

                        </div>


                        <div
                            class="
                                player-compare-stat-value
                                right
                            "
                        >

                            <strong
                                class="${getPlayerStatColorClass(
                                    targetValue
                                )}"
                            >
                                ${targetValue}
                            </strong>

                        </div>

                    </div>
                `;
            }
        )
        .join(
            ""
        );
}

function renderPlayerCompareModal() {

    const basePlayer =
        getComparePlayer(
            compareState.basePlayerSpId,
            "left"
        );


    const targetPlayer =
        getComparePlayer(
            compareState.targetPlayerSpId,
            "right"
        );


    if (
        !basePlayer
        ||
        !targetPlayer
    ) {

        return;
    }


    playerCompareContentElement
        .innerHTML = `

            <div class="player-compare-versus">

                ${createComparePlayerSummaryHtml(
                    basePlayer,
                    "left"
                )}


                <div class="player-compare-vs">

                    <span>
                        VS
                    </span>

                </div>


                ${createComparePlayerSummaryHtml(
                    targetPlayer,
                    "right"
                )}

            </div>

            ${createCompareSummaryHtml(
                basePlayer,
                targetPlayer
            )}

            <div class="player-compare-position-tabs">

                ${createComparePositionTabsHtml(
                    basePlayer,
                    targetPlayer
                )}

            </div>


            <section class="player-compare-stats-section">

                <div class="player-compare-stats-title">

                    <span>
                        ${escapeHtml(
                            basePlayer.player_name
                        )}
                    </span>

                    <strong>
                        ${
                            compareState.activePosition
                            === "all"
                                ? "상세 능력치"
                                : `${escapeHtml(
                                    compareState.activePosition
                                )} 기준`
                        }
                    </strong>

                    <span>
                        ${escapeHtml(
                            targetPlayer.player_name
                        )}
                    </span>

                </div>


                <div class="player-compare-stats">

                    ${createCompareStatsHtml(
                        basePlayer,
                        targetPlayer,
                        compareState.activePosition
                    )}

                </div>

            </section>

        `;

    initializePlayerImageFallbacks(
        playerCompareContentElement
    );
}

function openPlayerCompareModal(
    baseSpId,
    targetSpId
) {

    const numericBaseSpId =
        Number(
            baseSpId
        );


    const numericTargetSpId =
        Number(
            targetSpId
        );


    compareState.basePlayerSpId =
        numericBaseSpId;


    compareState.targetPlayerSpId =
        numericTargetSpId;


    compareState.activePosition =
        "all";


    initializeCompareControlState();


    const marketPricePromise =
        Promise.all(
            [
                loadPlayerMarketPrice(
                    numericBaseSpId
                ),

                loadPlayerMarketPrice(
                    numericTargetSpId
                ),
            ]
        );


    renderPlayerCompareModal();


    playerCompareModalElement.hidden =
        false;


    document.body
        .classList
        .add(
            "player-compare-open"
        );


    marketPricePromise
        .then(
            () => {

                if (
                    playerCompareModalElement
                        .hidden
                ) {
                    return;
                }


                if (
                    compareState
                        .basePlayerSpId
                    !== numericBaseSpId
                    ||
                    compareState
                        .targetPlayerSpId
                    !== numericTargetSpId
                ) {
                    return;
                }


                renderPlayerCompareModal();
            }
        )
        .catch(
            error => {

                console.error(
                    error
                );

            }
        );
}


function closePlayerCompareModal() {

    playerCompareModalElement.hidden =
        true;


    document.body
        .classList
        .remove(
            "player-compare-open"
        );
}

function selectCompareBasePlayer(
    spId
) {

    const numericSpId =
        Number(
            spId
        );


    const previousBaseSpId =
        compareState.basePlayerSpId;


    compareState.basePlayerSpId =
        numericSpId;


    compareState.targetPlayerSpId =
        null;


    // 기존 기준 선수 UI 원상복구
    if (
        previousBaseSpId !== null
        &&
        previousBaseSpId !== numericSpId
    ) {

        rerenderPlayerCard(
            previousBaseSpId
        );
    }


    // 새 기준 선수 다시 렌더링
    rerenderPlayerCard(
        numericSpId
    );


    // 검색결과 최상단 이동
    moveCompareBasePlayerToTop();
}

// =========================================
// RENDER RESULTS
// =========================================

function renderPlayers(
    data
) {

    playerResultsElement.hidden =
        false;

    playerResultCountElement
        .textContent =
            `${data.total_count.toLocaleString()}명`;


    if (
        data.players.length
        === 0
    ) {

        playerResultListElement
            .innerHTML =
                `
                    <div
                        class="player-database-empty"
                    >

                        <strong>
                            검색 결과가 없습니다.
                        </strong>

                    </div>
                `;

        initializePlayerImageFallbacks(
            playerResultListElement
        );

        renderPagination(
            data
        );

        return;
    }


    playerResultListElement
        .innerHTML =
            data.players
                .map(
                    createPlayerCardHtml
                )
                .join(
                    ""
                );


    moveCompareBasePlayerToTop();


    renderPagination(
        data
    );
}


// =========================================
// PAGINATION
// =========================================

function renderPagination(
    data
) {

    if (
        !playerPaginationElement
    ) {
        return;
    }


    if (
        data.page_count
        <= 1
    ) {

        playerPaginationElement
            .innerHTML =
                "";

        return;
    }


    const startPage =
        Math.max(
            1,
            data.page - 2
        );


    const endPage =
        Math.min(
            data.page_count,
            data.page + 2
        );


    const buttons = [];


    // =========================================
    // 이전
    // =========================================

    buttons.push(`
        <button
            type="button"
            class="
                player-database-page-button
                player-database-page-nav
            "
            data-page="${data.page - 1}"
            ${
                data.page <= 1
                    ? "disabled"
                    : ""
            }
        >
            <span aria-hidden="true">
                ‹
            </span>

            <span class="player-database-page-nav-text">
                이전
            </span>
        </button>
    `);


    // =========================================
    // 첫 페이지
    // =========================================

    if (
        startPage > 1
    ) {

        buttons.push(`
            <button
                type="button"
                class="player-database-page-button"
                data-page="1"
            >
                1
            </button>
        `);


        if (
            startPage > 2
        ) {

            buttons.push(`
                <span
                    class="player-database-page-ellipsis"
                >
                    ···
                </span>
            `);
        }
    }


    // =========================================
    // 페이지 번호
    // =========================================

    for (
        let page = startPage;
        page <= endPage;
        page += 1
    ) {

        buttons.push(`
            <button
                type="button"
                class="
                    player-database-page-button
                    ${
                        page === data.page
                            ? "active"
                            : ""
                    }
                "
                data-page="${page}"
                ${
                    page === data.page
                        ? 'aria-current="page"'
                        : ""
                }
            >
                ${page}
            </button>
        `);
    }


    // =========================================
    // 마지막 페이지
    // =========================================

    if (
        endPage < data.page_count
    ) {

        if (
            endPage
            <
            data.page_count - 1
        ) {

            buttons.push(`
                <span
                    class="player-database-page-ellipsis"
                >
                    ···
                </span>
            `);
        }


        buttons.push(`
            <button
                type="button"
                class="player-database-page-button"
                data-page="${data.page_count}"
            >
                ${data.page_count}
            </button>
        `);
    }


    // =========================================
    // 다음
    // =========================================

    buttons.push(`
        <button
            type="button"
            class="
                player-database-page-button
                player-database-page-nav
            "
            data-page="${data.page + 1}"
            ${
                data.page >= data.page_count
                    ? "disabled"
                    : ""
            }
        >
            <span class="player-database-page-nav-text">
                다음
            </span>

            <span aria-hidden="true">
                ›
            </span>
        </button>
    `);


    playerPaginationElement
        .innerHTML =
            buttons.join(
                ""
            );
}


// =========================================
// SEARCH
// =========================================

async function searchPlayers(
    page = 1
) {

    currentPage =
        page;


    playerSearchButtonElement.disabled =
        true;

    playerSearchButtonElement.textContent =
        "검색 중";

    playerResultsElement.hidden =
        true;


    playerResultListElement.innerHTML =
        "";


    playerPaginationElement.innerHTML =
        "";

    try {

        const params =
            buildSearchParams(
                page
            );


        const response =
            await fetch(
                (
                    `${apiBaseUrl}`
                    +
                    `/api/player-database/search?`
                    +
                    params.toString()
                )
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "선수 검색에 실패했습니다."
            );
        }


        renderPlayers(
            data
        );

    } catch (error) {

        console.error(
            error
        );

        playerResultsElement.hidden =
            false;


        playerResultCountElement
            .textContent =
                "0명";

        playerResultListElement
            .innerHTML =
                `
                    <div
                        class="player-database-empty"
                    >

                        <strong>
                            검색 중 오류가 발생했습니다.
                        </strong>

                        <p>
                            ${escapeHtml(
                                error.message
                            )}
                        </p>

                    </div>
                `;

    } finally {

        playerSearchButtonElement.disabled =
            false;

        playerSearchButtonElement.textContent =
            "검색";
    }
}


// =========================================
// RESET
// =========================================

function resetSearchConditions() {

    // =====================================
    // 선수명
    // =====================================

    playerNameInputElement.value =
        "";


    // =====================================
    // 시즌
    // =====================================

    selectedSeasonIds.clear();


    playerSeasonOptionsElement
        .querySelectorAll(
            ".selected"
        )
        .forEach(
            element => {

                element.classList.remove(
                    "selected"
                );
            }
        );


    updateSeasonSummary();


    playerSeasonPanelElement.hidden =
        true;


    playerSeasonToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );


    // =====================================
    // 포지션
    // =====================================

    selectedPositions.clear();


    playerPositionOptionsElement
        .querySelectorAll(
            ".selected"
        )
        .forEach(
            element => {

                element.classList.remove(
                    "selected"
                );
            }
        );


    updatePositionSummary();


    playerPositionPanelElement.hidden =
        true;


    playerPositionToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );


    // =====================================
    // 국적
    // =====================================

    selectedNationId =
        null;

    selectedNationName =
        "";


    playerNationSummaryElement
        .textContent =
            "전체 국적";


    renderNationOptions();


    playerNationPanelElement.hidden =
        true;


    playerNationToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );


    // =====================================
    // 소속팀
    // =====================================

    selectedTeamColorId =
        null;

    selectedTeamName =
        "";


    playerTeamSummaryElement
        .textContent =
            "전체 팀";


    renderTeamOptions();


    playerTeamPanelElement.hidden =
        true;


    playerTeamToggleElement
        .setAttribute(
            "aria-expanded",
            "false"
        );


    // =====================================
    // 상세검색 숫자 조건
    // =====================================

    document
        .querySelectorAll(
            (
                "#player-database-detail-panel "
                +
                "input"
            )
        )
        .forEach(
            inputElement => {

                inputElement.value =
                    "";
            }
        );


    // =====================================
    // 왼발 / 오른발
    // =====================================

    const leftFootElement =
        document.querySelector(
            "#player-database-left-foot"
        );


    const rightFootElement =
        document.querySelector(
            "#player-database-right-foot"
        );


    if (leftFootElement) {

        leftFootElement.value =
            "";
    }


    if (rightFootElement) {

        rightFootElement.value =
            "";
    }


    // =====================================
    // 선수 카드 개별 상태
    // =====================================

    playerCardStates.clear();

    playerDataBySpId.clear();


    // =====================================
    // 비교 상태
    // =====================================

    compareState.basePlayerSpId =
        null;

    compareState.targetPlayerSpId =
        null;

    compareState.activePosition =
        "all";


    // =====================================
    // 검색 결과
    // =====================================

    currentPage =
        1;


    playerResultsElement.hidden =
        true;


    playerResultCountElement.textContent =
        "0명";


    playerResultListElement.innerHTML =
        "";


    if (
        playerPaginationElement
    ) {

        playerPaginationElement.innerHTML =
            "";
    }
}


// =========================================
// DETAIL PANEL
// =========================================

function toggleDetailPanel() {

    const isHidden =
        detailPanelElement
            .classList
            .toggle(
                "hidden"
            );


    detailToggleElement.setAttribute(
        "aria-expanded",
        String(
            !isHidden
        )
    );


    detailArrowElement.textContent =
        isHidden
            ? "▼"
            : "▲";
}

// =========================================
// PLAYER IMAGE FALLBACK
// =========================================

function applyPlayerImageFallback(
    imageElement
) {

    if (
        !imageElement
        ||
        imageElement.dataset
            .fallbackApplied
        === "true"
    ) {

        return;
    }


    imageElement.dataset
        .fallbackApplied =
            "true";


    imageElement
        .classList
        .add(
            "player-image-load-error"
        );


    const wrapperElement =
        imageElement.parentElement;


    if (
        wrapperElement
    ) {

        wrapperElement
            .classList
            .add(
                "player-image-fallback"
            );
    }
}

document.addEventListener(
    "error",
    event => {

        const imageElement =
            event.target;


        if (
            !(imageElement instanceof HTMLImageElement)
            ||
            !imageElement.matches(
                "img[data-player-image]"
            )
        ) {

            return;
        }


        applyPlayerImageFallback(
            imageElement
        );

    },
    true
);

function initializePlayerImageFallbacks(
    rootElement = document
) {

    rootElement
        .querySelectorAll(
            "img[data-player-image]"
        )
        .forEach(
            imageElement => {

                const source =
                    String(
                        imageElement
                            .getAttribute(
                                "src"
                            )
                        ?? ""
                    )
                    .trim();


                if (
                    !source
                ) {

                    applyPlayerImageFallback(
                        imageElement
                    );
                }
            }
        );
}


// =========================================
// EVENTS
// =========================================

playerResultListElement
    .addEventListener(
        "click",
        event => {

            const recommendButtonElement =
                event.target.closest(
                    "button[data-recommend-player]"
                );


            if (!recommendButtonElement) {
                return;
            }


            event.preventDefault();

            event.stopPropagation();


            const spId =
                Number(
                    recommendButtonElement
                        .dataset
                        .spId
                );


            openPlayerRecommendModal(
                spId
            );
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {
            const closeElement =
                event.target.closest(
                    "[data-player-recommend-close]"
                );

            if (!closeElement) {
                return;
            }

            closePlayerRecommendModal();
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {

            const positionButtonElement =
                event.target.closest(
                    "button[data-recommend-position]"
                );


            if (!positionButtonElement) {
                return;
            }


            recommendState.selectedPosition =
                positionButtonElement
                    .dataset
                    .recommendPosition;


            const groupElement =
                positionButtonElement.closest(
                    "[data-recommend-position-group]"
                );


            groupElement
                ?.querySelectorAll(
                    "button[data-recommend-position]"
                )
                .forEach(
                    buttonElement => {

                        buttonElement
                            .classList
                            .toggle(
                                "selected",
                                buttonElement
                                ===
                                positionButtonElement
                            );
                    }
                );
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {

            const gradeButtonElement =
                event.target.closest(
                    "button[data-recommend-base-grade]"
                );


            if (!gradeButtonElement) {
                return;
            }


            const baseSpId =
                Number(
                    recommendState
                        .basePlayerSpId
                );


            const grade =
                Number(
                    gradeButtonElement
                        .dataset
                        .recommendBaseGrade
                );


            const cardState =
                getPlayerCardState(
                    baseSpId
                );


            cardState.grade =
                grade;


            const adjustedBasePlayer =
                getRecommendBasePlayer(
                    baseSpId
                );


            if (adjustedBasePlayer) {

                recommendState.ovrMin =
                    Math.max(
                        0,
                        Number(
                            adjustedBasePlayer.ovr
                            ?? 0
                        )
                        -
                        10
                    );


                recommendState.ovrMax =
                    (
                        Number(
                            adjustedBasePlayer.ovr
                            ?? 0
                        )
                        +
                        10
                    );
            }


            renderPlayerRecommendModal();

            refreshRecommendMarketPrice();
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {

            const salaryButtonElement =
                event.target.closest(
                    "button[data-recommend-salary-mode]"
                );


            if (!salaryButtonElement) {
                return;
            }


            recommendState.selectedSalaryMode =
                salaryButtonElement
                    .dataset
                    .recommendSalaryMode;


            const groupElement =
                salaryButtonElement.closest(
                    "[data-recommend-salary-group]"
                );


            groupElement
                ?.querySelectorAll(
                    "button[data-recommend-salary-mode]"
                )
                .forEach(
                    buttonElement => {

                        buttonElement
                            .classList
                            .toggle(
                                "selected",
                                buttonElement
                                ===
                                salaryButtonElement
                            );
                    }
                );
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "change",
        event => {

            const teamColorSelectElement =
                event.target.closest(
                    "select[data-recommend-team-color]"
                );


            const minSelectElement =
                event.target.closest(
                    "select[data-recommend-ovr-min]"
                );


            const maxSelectElement =
                event.target.closest(
                    "select[data-recommend-ovr-max]"
                );


            const limitSelectElement =
                event.target.closest(
                    "select[data-recommend-limit]"
                );


            if (
                !teamColorSelectElement
                &&
                !minSelectElement
                &&
                !maxSelectElement
                &&
                !limitSelectElement
            ) {
                return;
            }


            // =================================
            // 팀컬러
            // =================================

            if (
                teamColorSelectElement
            ) {

                const value =
                    teamColorSelectElement
                        .value;


                recommendState
                    .selectedTeamColorId =
                        value === ""
                            ? null
                            : Number(
                                value
                            );

                return;
            }


            // =================================
            // OVR 최소 / 최대
            // =================================

            if (
                minSelectElement
                ||
                maxSelectElement
            ) {

                const currentMinElement =
                    playerRecommendModalElement
                        .querySelector(
                            "select[data-recommend-ovr-min]"
                        );


                const currentMaxElement =
                    playerRecommendModalElement
                        .querySelector(
                            "select[data-recommend-ovr-max]"
                        );


                if (
                    !currentMinElement
                    ||
                    !currentMaxElement
                ) {
                    return;
                }


                let minimumValue =
                    Number(
                        currentMinElement.value
                    );


                let maximumValue =
                    Number(
                        currentMaxElement.value
                    );


                if (
                    minimumValue
                    >
                    maximumValue
                ) {

                    if (
                        minSelectElement
                    ) {

                        maximumValue =
                            minimumValue;

                        currentMaxElement.value =
                            String(
                                maximumValue
                            );

                    } else {

                        minimumValue =
                            maximumValue;

                        currentMinElement.value =
                            String(
                                minimumValue
                            );
                    }
                }


                recommendState.ovrMin =
                    minimumValue;


                recommendState.ovrMax =
                    maximumValue;

                return;
            }


            // =================================
            // 추천 수
            // =================================

            if (
                limitSelectElement
            ) {

                recommendState.limit =
                    Number(
                        limitSelectElement.value
                    );
            }
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "change",
        event => {

            const adaptationSelectElement =
                event.target.closest(
                    "select[data-recommend-base-adaptation]"
                );


            const teamColorSelectElement =
                event.target.closest(
                    "select[data-recommend-base-team-color]"
                );


            if (
                !adaptationSelectElement
                &&
                !teamColorSelectElement
            ) {
                return;
            }


            const baseSpId =
                Number(
                    recommendState
                        .basePlayerSpId
                );


            const cardState =
                getPlayerCardState(
                    baseSpId
                );


            if (
                adaptationSelectElement
            ) {

                cardState.adaptation =
                    Number(
                        adaptationSelectElement.value
                    );
            }


            if (
                teamColorSelectElement
            ) {

                cardState.teamColor =
                    Number(
                        teamColorSelectElement.value
                    );
            }


            const adjustedBasePlayer =
                getRecommendBasePlayer(
                    baseSpId
                );


            if (
                adjustedBasePlayer
            ) {

                recommendState.ovrMin =
                    Math.max(
                        0,
                        Number(
                            adjustedBasePlayer.ovr
                            ?? 0
                        )
                        -
                        10
                    );


                recommendState.ovrMax =
                    (
                        Number(
                            adjustedBasePlayer.ovr
                            ?? 0
                        )
                        +
                        10
                    );
            }


            renderPlayerRecommendModal();

            refreshRecommendMarketPrice();
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {

            const refreshButtonElement =
                event.target.closest(
                    "button[data-recommend-refresh]"
                );


            if (!refreshButtonElement) {
                return;
            }


            const basePlayer =
                getRecommendBasePlayer(
                    recommendState
                        .basePlayerSpId
                );


            if (!basePlayer) {
                return;
            }


            loadPlayerRecommendations(
                basePlayer
            );
        }
    );

playerRecommendModalElement
    ?.addEventListener(
        "click",
        event => {

            const compareButtonElement =
                event.target.closest(
                    "button[data-recommend-compare]"
                );


            if (!compareButtonElement) {

                return;
            }


            event.preventDefault();

            event.stopPropagation();


            const targetSpId =
                Number(
                    compareButtonElement
                        .dataset
                        .spId
                );


            openRecommendedPlayerCompare(
                targetSpId
            );
        }
    );



playerResultListElement
    .addEventListener(
        "click",
        event => {

            const compareButtonElement =
                event.target.closest(
                    "button[data-compare-player]"
                );


            if (!compareButtonElement) {
                return;
            }


            event.preventDefault();

            event.stopPropagation();


            const spId =
                Number(
                    compareButtonElement
                        .dataset
                        .spId
                );


            // =================================
            // 이미 기준 선수면 비교 해제
            // =================================

            if (
                compareState.basePlayerSpId
                === spId
            ) {

                compareState.basePlayerSpId =
                    null;


                compareState.targetPlayerSpId =
                    null;


                rerenderPlayerCard(
                    spId
                );


                return;
            }


            // =================================
            // 첫 번째 선수 선택
            // =================================

            if (
                compareState.basePlayerSpId
                === null
            ) {

                selectCompareBasePlayer(
                    spId
                );


                return;
            }


            // =================================
            // 두 번째 선수 선택
            // =================================

            compareState.targetPlayerSpId =
                spId;

            openPlayerCompareModal(
                compareState.basePlayerSpId,
                compareState.targetPlayerSpId
            );
        }
    );

playerResultListElement
    .addEventListener(
        "change",
        event => {

            const teamColorSelectElement =
                event.target.closest(
                    "select[data-card-team-color]"
                );


            if (!teamColorSelectElement) {
                return;
            }


            const spId =
                Number(
                    teamColorSelectElement
                        .dataset
                        .spId
                );


            const teamColor =
                Number(
                    teamColorSelectElement
                        .value
                );


            const state =
                getPlayerCardState(
                    spId
                );


            state.teamColor =
                teamColor;


            rerenderPlayerCard(
                spId
            );
        }
    );

playerResultListElement
    .addEventListener(
        "click",
        event => {

            // =================================
            // 강화
            // =================================

            const gradeButtonElement =
                event.target.closest(
                    "button[data-card-grade]"
                );


            if (gradeButtonElement) {

                const spId =
                    Number(
                        gradeButtonElement
                            .dataset
                            .spId
                    );


                const grade =
                    Number(
                        gradeButtonElement
                            .dataset
                            .cardGrade
                    );


                const state =
                    getPlayerCardState(
                        spId
                    );


                state.grade =
                    grade;


                rerenderPlayerCard(
                    spId
                );


                return;
            }


            // =================================
            // 적응도
            // =================================

            const adaptationButtonElement =
                event.target.closest(
                    "button[data-card-adaptation]"
                );


            if (adaptationButtonElement) {

                const spId =
                    Number(
                        adaptationButtonElement
                            .dataset
                            .spId
                    );


                const adaptation =
                    Number(
                        adaptationButtonElement
                            .dataset
                            .cardAdaptation
                    );


                const state =
                    getPlayerCardState(
                        spId
                    );


                state.adaptation =
                    adaptation;


                rerenderPlayerCard(
                    spId
                );
            }
        }
    );

playerResultListElement
    .addEventListener(
        "click",
        event => {

            const rowElement =
                event.target.closest(
                    ".player-database-player-row"
                );


            if (!rowElement) {
                return;
            }

            if (
                event.target.closest(
                    (
                        "button[data-compare-player],"
                        +
                        "button[data-recommend-player]"
                    )
                )
            ) {
                return;
            }


            const itemElement =
                rowElement.closest(
                    ".player-database-player-item"
                );


            const detailElement =
                itemElement.querySelector(
                    ".player-database-player-detail"
                );


            const arrowElement =
                rowElement.querySelector(
                    ".player-database-player-arrow"
                );


            const willOpen =
                detailElement.hidden;


            // 다른 선수 상세정보 닫기
            playerResultListElement
                .querySelectorAll(
                    ".player-database-player-item"
                )
                .forEach(
                    otherItemElement => {

                        if (
                            otherItemElement
                            ===
                            itemElement
                        ) {
                            return;
                        }


                        const otherDetailElement =
                            otherItemElement.querySelector(
                                ".player-database-player-detail"
                            );


                        const otherRowElement =
                            otherItemElement.querySelector(
                                ".player-database-player-row"
                            );


                        const otherArrowElement =
                            otherItemElement.querySelector(
                                ".player-database-player-arrow"
                            );


                        if (otherDetailElement) {
                            otherDetailElement.hidden =
                                true;
                        }


                        if (otherRowElement) {

                            otherRowElement
                                .setAttribute(
                                    "aria-expanded",
                                    "false"
                                );
                        }


                        if (otherArrowElement) {
                            otherArrowElement.textContent =
                                "▼";
                        }
                    }
                );


            detailElement.hidden =
                !willOpen;


            rowElement.setAttribute(
                "aria-expanded",
                String(
                    willOpen
                )
            );


            arrowElement.textContent =
                willOpen
                    ? "▲"
                    : "▼";

            if (willOpen) {

                const spId =
                    Number(
                        itemElement
                            .dataset
                            .spId
                    );


                loadPlayerMarketPrice(
                    spId
                );
            }
        }
    );

playerSearchButtonElement
    .addEventListener(
        "click",
        () => {

            playerCardStates.clear();
            playerDataBySpId.clear();

            compareState.basePlayerSpId =
                null;

            compareState.targetPlayerSpId =
                null;


            searchPlayers(
                1
            );
        }
    );


playerNameInputElement
    .addEventListener(
        "keydown",
        event => {
            if (
                event.key
                === "Enter"
            ) {

                playerCardStates.clear();
                playerDataBySpId.clear();

                compareState.basePlayerSpId =
                    null;

                compareState.targetPlayerSpId =
                    null;


                searchPlayers(
                    1
                );
            }
        }
    );


playerPaginationElement
    ?.addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-page]"
                );

            if (
                !buttonElement
                ||
                buttonElement.disabled
            ) {
                return;
            }


            const page =
                Number(
                    buttonElement.dataset.page
                );


            if (
                !Number.isInteger(
                    page
                )
                ||
                page < 1
            ) {
                return;
            }


            searchPlayers(
                page
            );


            window.scrollTo(
                {
                    top:
                        playerResultListElement
                            .offsetTop
                        -
                        120,

                    behavior:
                        "smooth",
                }
            );
        }
    );


detailToggleElement
    ?.addEventListener(
        "click",
        toggleDetailPanel
    );


resetButtonElement
    ?.addEventListener(
        "click",
        resetSearchConditions
    );

playerCompareModalElement
    ?.addEventListener(
        "click",
        event => {

            const closeElement =
                event.target.closest(
                    "[data-player-compare-close]"
                );


            if (!closeElement) {
                return;
            }


            closePlayerCompareModal();
        }
    );


document.addEventListener(
    "keydown",
    event => {

        if (
            event.key
            !== "Escape"
        ) {
            return;
        }


        if (
            playerCompareModalElement.hidden
        ) {
            return;
        }


        closePlayerCompareModal();
    }
);

playerCompareModalElement
    ?.addEventListener(
        "click",
        event => {

            // =================================
            // 강화
            // =================================

            const gradeButtonElement =
                event.target.closest(
                    "button[data-compare-grade]"
                );


            if (gradeButtonElement) {

                const side =
                    gradeButtonElement
                        .dataset
                        .compareSide;


                const grade =
                    Number(
                        gradeButtonElement
                            .dataset
                            .compareGrade
                    );


                if (
                    !compareControlState[
                        side
                    ]
                ) {
                    return;
                }


                compareControlState[
                    side
                ].grade =
                    grade;


                renderPlayerCompareModal();


                return;
            }


            // =================================
            // 적응도
            // =================================

            const adaptationButtonElement =
                event.target.closest(
                    "button[data-compare-adaptation]"
                );


            if (!adaptationButtonElement) {
                return;
            }


            const side =
                adaptationButtonElement
                    .dataset
                    .compareSide;


            const adaptation =
                Number(
                    adaptationButtonElement
                        .dataset
                        .compareAdaptation
                );


            if (
                !compareControlState[
                    side
                ]
            ) {
                return;
            }


            compareControlState[
                side
            ].adaptation =
                adaptation;


            renderPlayerCompareModal();
        }
    );

playerCompareModalElement
    ?.addEventListener(
        "change",
        event => {

            const selectElement =
                event.target.closest(
                    (
                        "select[data-compare-grade],"
                        +
                        "select[data-compare-adaptation],"
                        +
                        "select[data-compare-team-color]"
                    )
                );


            if (!selectElement) {
                return;
            }


            const side =
                selectElement
                    .dataset
                    .compareSide;


            const state =
                compareControlState[
                    side
                ];


            if (!state) {
                return;
            }


            // =================================
            // 강화
            // =================================

            if (
                selectElement.hasAttribute(
                    "data-compare-grade"
                )
            ) {

                state.grade =
                    Number(
                        selectElement.value
                    );
            }


            // =================================
            // 적응도
            // =================================

            if (
                selectElement.hasAttribute(
                    "data-compare-adaptation"
                )
            ) {

                state.adaptation =
                    Number(
                        selectElement.value
                    );
            }


            // =================================
            // 팀컬러
            // =================================

            if (
                selectElement.hasAttribute(
                    "data-compare-team-color"
                )
            ) {

                state.teamColor =
                    Number(
                        selectElement.value
                    );
            }


            renderPlayerCompareModal();
        }
    );

playerCompareModalElement
    ?.addEventListener(
        "click",
        event => {

            const positionButtonElement =
                event.target.closest(
                    "button[data-compare-position]"
                );


            if (!positionButtonElement) {
                return;
            }


            compareState.activePosition =
                positionButtonElement
                    .dataset
                    .comparePosition;


            renderPlayerCompareModal();
        }
    );



// =========================================
// INITIALIZE
// =========================================

async function initializePlayerDatabase() {

    await loadPlayerFilters();

    renderPositionOptions();

    updateSeasonSummary();
    updatePositionSummary();
}



initializePlayerDatabase();