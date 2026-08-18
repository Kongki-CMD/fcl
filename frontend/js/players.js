import {
    apiBaseUrl,
} from "./config.js";


const playersTableBodyElement =
    document.querySelector(
        ".players-table-body"
    );


// =========================================
// 선수 기록 불러오기
// =========================================

async function loadPlayerRankings() {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/player-rankings`
        );


        if (!response.ok) {

            throw new Error(
                "선수 기록을 불러오지 못했습니다."
            );

        }


        const playerData =
            await response.json();


        renderPlayerRankings(
            playerData
        );


    } catch (error) {

        console.error(
            error
        );


        playersTableBodyElement.innerHTML = `
            <tr>
                <td colspan="7">
                    선수 기록을 불러오는 중
                    오류가 발생했습니다.
                </td>
            </tr>
        `;

    }

}


// =========================================
// 선수 기록 출력
// =========================================

function renderPlayerRankings(
    players
) {

    playersTableBodyElement.innerHTML =
        "";


    // =====================================
    // 아직 정규리그 기록 없음
    // =====================================

    if (players.length === 0) {

        playersTableBodyElement.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="players-empty"
                >
                    아직 등록된 정규리그
                    선수 기록이 없습니다.
                </td>
            </tr>
        `;

        return;

    }


    // =====================================
    // 선수 출력
    // =====================================

    players.forEach(
        (player) => {

            const playerRowElement =
                document.createElement(
                    "tr"
                );


            let playerImageHtml = "";


            if (player.image_url) {

                playerImageHtml = `
                    <img
                        src="${player.image_url}"
                        alt="${player.player_name}"
                        class="player-record-image"
                        onerror="
                            this.style.display='none'
                        "
                    >
                `;

            }


            let ownerText =
                player.fcl_name;


            if (player.nickname) {

                ownerText +=
                    ` (${player.nickname})`;

            }


            playerRowElement.innerHTML = `

                <td
                    class="
                        player-ranking-number
                    "
                >
                    ${player.rank}
                </td>


                <td>
                    <div
                        class="
                            player-record-profile
                        "
                    >

                        ${playerImageHtml}

                        <span
                            class="
                                player-record-name
                            "
                        >
                            ${player.player_name}
                        </span>

                    </div>
                </td>


                <td
                    class="
                        player-record-owner
                    "
                >
                    ${ownerText}
                </td>


                <td
                    class="
                        player-goals
                    "
                >
                    ${player.goals}
                </td>


                <td>
                    ${player.assists}
                </td>


                <td>
                    ${player.sets_played}
                </td>


                <td
                    class="
                        player-average-rating
                    "
                >
                    ${player.average_rating}
                </td>

            `;


            playersTableBodyElement.appendChild(
                playerRowElement
            );

        }
    );

}


loadPlayerRankings();