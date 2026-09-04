import {
    apiBaseUrl,
} from "./config.js";


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


const playerDataBySpId =
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


                const gradeTier =
                    getGradeTierClass(
                        grade
                    );


                return `
                    <button
                        type="button"
                        class="
                            player-database-card-grade
                            ${gradeTier}
                            ${
                                grade === selectedGrade
                                    ? "selected"
                                    : ""
                            }
                        "
                        data-card-grade="${grade}"
                        data-sp-id="${spId}"
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
            class="player-database-player-item"
            data-sp-id="${player.sp_id}"
        >

            <!-- =========================
                목록
            ========================== -->

            <button
                type="button"
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


                <strong
                    class="player-database-player-name"
                >
                    ${escapeHtml(
                        player.player_name
                    )}
                </strong>


                <span
                    class="player-database-player-arrow"
                    aria-hidden="true"
                >
                    ▼
                </span>

            </button>


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
                            )}"
                            alt="${escapeHtml(
                                player.player_name
                            )}"
                            class="player-database-player-photo"
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

    playerNameInputElement.value =
        "";

    selectedNationId =
        null;

    selectedNationName =
        "";

    selectedTeamColorId =
        null;

    selectedTeamName =
        "";


    playerNationSummaryElement
        .textContent =
            "전체 국적";

    playerTeamSummaryElement
        .textContent =
            "전체 팀";


    renderNationOptions();
    renderTeamOptions();


    closeNationPanel();
    closeTeamPanel();

    selectedSeasonIds.clear();
    selectedPositions.clear();

    playerSeasonOptionsElement
        .querySelectorAll(
            ".selected"
        )
        .forEach(
            element =>
                element.classList.remove(
                    "selected"
                )
        );


    playerPositionOptionsElement
        .querySelectorAll(
            ".selected"
        )
        .forEach(
            element =>
                element.classList.remove(
                    "selected"
                )
        );


    updateSeasonSummary();
    updatePositionSummary();


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
// EVENTS
// =========================================

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
        }
    );

playerSearchButtonElement
    .addEventListener(
        "click",
        () => {

            playerCardStates.clear();
            playerDataBySpId.clear();


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