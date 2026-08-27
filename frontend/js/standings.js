import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const standingsTableBodyElement = document.querySelector(
    ".standings-table-body"
);


async function loadStandings() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/standings`
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


loadStandings();