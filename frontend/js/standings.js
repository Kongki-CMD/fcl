import {
    apiBaseUrl,
    getTeamImagePath,
    loadFclSeasons,
} from "./config.js?v=perf-2";


const standingsTableBodyElement = document.querySelector(
    ".standings-table-body"
);

const standingsSeasonTabsElement =
    document.querySelector(
        "#standings-season-tabs"
    );

const standingsDescriptionElement =
    document.querySelector(
        ".standings-header p"
    );


let selectedStandingsSeasonNumber =
    null;

let availableStandingsSeasons =
    [];

function getRequestedStandingsSeasonNumber() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const seasonValue =
        Number(
            params.get(
                "season"
            )
        );


    if (
        Number.isInteger(
            seasonValue
        )
        &&
        seasonValue > 0
    ) {

        return seasonValue;
    }


    return null;
}


function updateStandingsDescription() {

    if (!standingsDescriptionElement) {
        return;
    }


    if (!selectedStandingsSeasonNumber) {

        standingsDescriptionElement.textContent =
            "FC Online Champions League 정규리그 순위";

        return;
    }


    standingsDescriptionElement.textContent =
        (
            `SEASON ${selectedStandingsSeasonNumber} `
            + "정규리그 순위"
        );
}


function renderStandingsSeasonTabs() {

    if (!standingsSeasonTabsElement) {
        return;
    }


    standingsSeasonTabsElement.innerHTML =
        "";


    availableStandingsSeasons.forEach(
        season => {

            const seasonButtonElement =
                document.createElement(
                    "button"
                );


            seasonButtonElement.type =
                "button";


            seasonButtonElement.className =
                "season-tab-button";


            seasonButtonElement.textContent =
                `SEASON ${season.season_number}`;


            if (
                Number(
                    season.season_number
                )
                ===
                selectedStandingsSeasonNumber
            ) {

                seasonButtonElement
                    .classList.add(
                        "active"
                    );
            }


            seasonButtonElement.addEventListener(
                "click",
                async () => {

                    const nextSeasonNumber =
                        Number(
                            season.season_number
                        );


                    if (
                        nextSeasonNumber
                        ===
                        selectedStandingsSeasonNumber
                    ) {

                        return;
                    }


                    selectedStandingsSeasonNumber =
                        nextSeasonNumber;


                    const url =
                        new URL(
                            window.location.href
                        );


                    url.searchParams.set(
                        "season",
                        String(
                            selectedStandingsSeasonNumber
                        )
                    );


                    window.history.replaceState(
                        {},
                        "",
                        url
                    );


                    renderStandingsSeasonTabs();

                    updateStandingsDescription();


                    await loadStandings();
                }
            );


            standingsSeasonTabsElement
                .appendChild(
                    seasonButtonElement
                );
        }
    );
}


async function loadStandingsSeasonTabs() {

    try {

        availableStandingsSeasons =
            await loadFclSeasons();


        if (
            availableStandingsSeasons.length
            === 0
        ) {

            throw new Error(
                "등록된 시즌이 없습니다."
            );
        }


        const requestedSeasonNumber =
            getRequestedStandingsSeasonNumber();


        const requestedSeason =
            availableStandingsSeasons.find(
                season =>
                    Number(
                        season.season_number
                    )
                    ===
                    requestedSeasonNumber
            );


        const activeSeason =
            availableStandingsSeasons.find(
                season =>
                    season.status
                    ===
                    "active"
            );


        const fallbackSeason =
            availableStandingsSeasons[
                availableStandingsSeasons.length - 1
            ];


        const selectedSeason =
            requestedSeason
            ??
            activeSeason
            ??
            fallbackSeason;


        selectedStandingsSeasonNumber =
            Number(
                selectedSeason
                    .season_number
            );


        renderStandingsSeasonTabs();

        updateStandingsDescription();


        await loadStandings();


    } catch (error) {

        console.error(
            error
        );


        if (standingsSeasonTabsElement) {

            standingsSeasonTabsElement.innerHTML = `
                <p>
                    시즌 정보를 불러오는 중
                    오류가 발생했습니다.
                </p>
            `;
        }
    }
}


async function loadStandings() {

    try {

        if (!selectedStandingsSeasonNumber) {
            return;
        }


        const response = await fetch(
            `${apiBaseUrl}/api/standings`
            + `?season=${selectedStandingsSeasonNumber}`
        );

        if (!response.ok) {
            throw new Error("팀 순위를 불러오지 못했습니다.");
        }

        const standingsData = await response.json();

        renderStandings(standingsData);
    } catch (error) {
        console.error(error);

        standingsTableBodyElement.innerHTML = `
            <tr>
                <td colspan="10">
                    팀 순위를 불러오는 중 오류가 발생했습니다.
                </td>
            </tr>
        `;
    }
}


function renderStandings(standings) {
    standingsTableBodyElement.innerHTML = "";

    standings.forEach((team) => {
        const standingRowElement = document.createElement("tr");

        const goalDifferenceText =
            team.goal_difference > 0
                ? `+${team.goal_difference}`
                : team.goal_difference;

        standingRowElement.innerHTML = `
            <td class="ranking-number">
                ${team.rank}
            </td>

            <td>
                <div class="standing-team">
                    <img
                        src="${
                            team.current_team_logo_path
                            ?? getTeamImagePath(team.name)
                        }"
                        alt="${
                            team.current_team_name
                            ?? team.name
                        } 로고"
                        class="team-image"
                    >

                    <span class="standing-team-name">
                        ${team.name}
                    </span>
                </div>
            </td>

            <td>${team.played}</td>
            <td>${team.wins}</td>
            <td>${team.draws}</td>
            <td>${team.losses}</td>
            <td>${team.goals_for}</td>
            <td>${team.goals_against}</td>
            <td>${goalDifferenceText}</td>

            <td class="standing-points">
                ${team.points}
            </td>
        `;

        standingsTableBodyElement.appendChild(
            standingRowElement
        );
    });
}


loadStandingsSeasonTabs();