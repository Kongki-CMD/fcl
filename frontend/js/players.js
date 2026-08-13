import {
    apiBaseUrl,
} from "./config.js";


const playersTableBodyElement = document.querySelector(
    ".players-table-body"
);


async function loadPlayerRankings() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/player-rankings`
        );

        if (!response.ok) {
            throw new Error("선수 순위를 불러오지 못했습니다.");
        }

        const playerData = await response.json();

        renderPlayerRankings(playerData);
    } catch (error) {
        console.error(error);

        playersTableBodyElement.innerHTML = `
            <tr>
                <td colspan="4">
                    선수 순위를 불러오는 중 오류가 발생했습니다.
                </td>
            </tr>
        `;
    }
}


function renderPlayerRankings(players) {
    playersTableBodyElement.innerHTML = "";

    if (players.length === 0) {
        playersTableBodyElement.innerHTML = `
            <tr>
                <td colspan="4">
                    등록된 선수 기록이 없습니다.
                </td>
            </tr>
        `;

        return;
    }

    players.forEach((player) => {
        const playerRowElement = document.createElement("tr");

        playerRowElement.innerHTML = `
            <td class="player-ranking-number">
                ${player.rank}
            </td>

            <td>
                ${player.season}
            </td>

            <td class="player-name">
                ${player.player_name}
            </td>

            <td class="player-goals">
                ${player.goals}
            </td>
        `;

        playersTableBodyElement.appendChild(
            playerRowElement
        );
    });
}


loadPlayerRankings();