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

const playerTeamColorBonusElement =
    document.querySelector(
        "#player-database-team-color-bonus"
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


const playerGradeOptionsElement =
    document.querySelector(
        "#player-database-grade-options"
    );


const playerAdaptationOptionsElement =
    document.querySelector(
        "#player-database-adaptation-options"
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

let selectedGrade =
    1;

let selectedAdaptation =
    1;

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


playerGradeOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-grade]"
                );


            if (!buttonElement) {
                return;
            }


            selectedGrade =
                Number(
                    buttonElement.dataset.grade
                );


            playerGradeOptionsElement
                .querySelectorAll(
                    "button[data-grade]"
                )
                .forEach(
                    element => {

                        element.classList.toggle(
                            "selected",
                            element === buttonElement
                        );
                    }
                );
        }
    );


playerAdaptationOptionsElement
    .addEventListener(
        "click",
        event => {

            const buttonElement =
                event.target.closest(
                    "button[data-adaptation]"
                );


            if (!buttonElement) {
                return;
            }


            selectedAdaptation =
                Number(
                    buttonElement.dataset.adaptation
                );


            playerAdaptationOptionsElement
                .querySelectorAll(
                    "button[data-adaptation]"
                )
                .forEach(
                    element => {

                        element.classList.toggle(
                            "selected",
                            element === buttonElement
                        );
                    }
                );
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


    params.set(
        "grade",
        String(
            selectedGrade
        )
    );


    params.set(
        "adaptation",
        String(
            selectedAdaptation
        )
    );

            

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

    params.set(
        "team_color",
        playerTeamColorBonusElement.value
        || "0"
    );

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
    // 주발
    // =====================================

    const footElement =
        document.querySelector(
            "#player-database-foot"
        );


    if (
        footElement
        &&
        footElement.value
    ) {

        params.set(
            "preferred_foot",
            footElement.value
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


    const preferredFootText = {

        right:
            "오른발",

        left:
            "왼발",

        both:
            "양발",

    }[
        player.preferred_foot
    ]
    ?? "-";


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

                                <span>
                                    ${preferredFootText}
                                </span>

                            </div>

                        </div>


                        <!-- =========================
                            강화 / 적응도 / 팀컬러
                        ========================== -->

                        <div
                            class="player-database-player-bonus"
                        >

                            <span>
                                강화

                                <strong>
                                    +${player.grade}
                                </strong>
                            </span>


                            <span>
                                적응도

                                <strong>
                                    ${player.adaptation}
                                </strong>
                            </span>


                            <span>
                                팀컬러

                                <strong>
                                    +${player.team_color_bonus}
                                </strong>
                            </span>

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

    playerTeamColorBonusElement.value =
        "0";

    selectedSeasonIds.clear();
    selectedPositions.clear();

    selectedGrade =
        1;

    selectedAdaptation =
        1;


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


    playerGradeOptionsElement
        .querySelectorAll(
            "button[data-grade]"
        )
        .forEach(
            element => {

                element.classList.toggle(
                    "selected",
                    element.dataset.grade === "1"
                );
            }
        );


    playerAdaptationOptionsElement
        .querySelectorAll(
            "button[data-adaptation]"
        )
        .forEach(
            element => {

                element.classList.toggle(
                    "selected",
                    element.dataset.adaptation === "1"
                );
            }
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


    const footElement =
        document.querySelector(
            "#player-database-foot"
        );

    if (footElement) {

        footElement.value =
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