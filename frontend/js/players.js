import {
    apiBaseUrl,
} from "./config.js";


const playersTableBodyElement =
    document.querySelector(
        ".players-table-body"
    );

let playerRankingData = [];


let playerSortKey =
    "goals";


let playerSortDirection =
    "desc";


const playerSortHeaderElements =
    document.querySelectorAll(
        ".player-sort-header"
    );

let playerSeasonMap =
    new Map();

const playerSyncStatusElement =
    document.querySelector(
        "#player-sync-status"
    );


const playerSyncStatusMessageElement =
    document.querySelector(
        "#player-sync-status-message"
    );


const playerSyncCheckIntervalMs =
    30 * 60 * 1000;


let playerSyncCheckRunning =
    false;


async function loadPlayerSeasonMetadata() {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/metadata/seasons`
        );


        if (!response.ok) {

            throw new Error(
                "시즌 정보를 불러오지 못했습니다."
            );

        }


        const data =
            await response.json();


        playerSeasonMap =
            new Map(
                data.seasons.map(
                    season => [
                        Number(
                            season.season_id
                        ),
                        season,
                    ]
                )
            );


    } catch (error) {

        console.error(
            error
        );

    }

}


function getPlayerSeasonInfo(
    spId
) {

    if (!spId) {
        return null;
    }


    const seasonId =
        Math.floor(
            Number(spId)
            / 1000000
        );


    return (
        playerSeasonMap.get(
            seasonId
        )
        ??
        null
    );

}


function createPlayerSeasonIconHtml(
    spId
) {

    const season =
        getPlayerSeasonInfo(
            spId
        );


    if (!season) {

        return "";

    }


    return `
        <img
            src="${season.season_image_url}"
            alt="${season.class_name}"
            class="player-record-season-icon"
        >
    `;

}

const playerRecordCustomImages = {
    "주앙 칸셀루":
        "./assets/images/players/custom/cancelo.png",

    "닉 포프":
        "./assets/images/players/custom/nick_pope.png",
};


function getPlayerRecordImage(
    player
) {

    return (
        playerRecordCustomImages[
            player.player_name
        ]
        ||
        player.image_url
    );

}


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


        playerRankingData =
            playerData;


        sortPlayerRankings();


    } catch (error) {

        console.error(
            error
        );


        playersTableBodyElement.innerHTML = `
            <tr>
                <td colspan="8">
                    선수 기록을 불러오는 중
                    오류가 발생했습니다.
                </td>
            </tr>
        `;

    }

}

//선수 정렬 함수

function sortPlayerRankings() {

    const sortedPlayers = [
        ...playerRankingData
    ];


    sortedPlayers.sort(
        (playerA, playerB) => {

            const valueA =
                playerA[playerSortKey];

            const valueB =
                playerB[playerSortKey];


            let compareResult = 0;


            if (
                typeof valueA === "string"
                || typeof valueB === "string"
            ) {

                compareResult =
                    String(
                        valueA ?? ""
                    ).localeCompare(
                        String(
                            valueB ?? ""
                        ),
                        "ko"
                    );

            } else {

                compareResult =
                    Number(
                        valueA ?? 0
                    )
                    -
                    Number(
                        valueB ?? 0
                    );

            }


            if (
                compareResult === 0
            ) {

                compareResult =
                    playerA.player_name.localeCompare(
                        playerB.player_name,
                        "ko"
                    );

            }


            return (
                playerSortDirection
                === "asc"
            )
                ? compareResult
                : -compareResult;
        }
    );


    renderPlayerRankings(
        sortedPlayers
    );


    updatePlayerSortHeaders();

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
                    colspan="8"
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


            const playerImageUrl =
                getPlayerRecordImage(
                    player
                );


            if (playerImageUrl) {

                playerImageHtml = `
                    <img
                        src="${playerImageUrl}"
                        alt="${player.player_name}"
                        class="player-record-image"
                        onerror="
                            this.style.display='none'
                        "
                    >
                `;

            }

            let ownerNicknameHtml =
                "";


            if (player.nickname) {

                ownerNicknameHtml = `
                    <span
                        class="
                            player-record-owner-nickname
                        "
                    >
                        (${player.nickname})
                    </span>
                `;

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

                        <div
                            class="
                                player-record-name-wrap
                            "
                        >
                            ${createPlayerSeasonIconHtml(
                                player.sp_id
                            )}

                            <span
                                class="
                                    player-record-name
                                "
                            >
                                ${player.player_name}
                            </span>
                        </div>

                    </div>
                </td>


                <td
                    class="
                        player-record-owner
                    "
                >
                    <span
                        class="
                            player-record-owner-name
                        "
                    >
                        ${player.fcl_name}
                    </span>

                    ${ownerNicknameHtml}
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
                        player-mvp-count
                    "
                >
                    ${player.mvp_count}
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


//이벤트
playerSortHeaderElements.forEach(
    (headerElement) => {

        headerElement.addEventListener(
            "click",
            () => {

                const sortKey =
                    headerElement.dataset.sortKey;


                if (
                    playerSortKey
                    === sortKey
                ) {

                    playerSortDirection =
                        playerSortDirection
                        === "desc"
                            ? "asc"
                            : "desc";

                } else {

                    playerSortKey =
                        sortKey;


                    if (
                        sortKey === "player_name"
                        || sortKey === "fcl_name"
                    ) {

                        playerSortDirection =
                            "asc";

                    } else {

                        playerSortDirection =
                            "desc";
                    }

                }


                sortPlayerRankings();

            }
        );

    }
);

function updatePlayerSortHeaders() {

    playerSortHeaderElements.forEach(
        (headerElement) => {

            const arrowElement =
                headerElement.querySelector(
                    ".player-sort-arrow"
                );


            if (!arrowElement) {
                return;
            }


            if (
                headerElement.dataset.sortKey
                !== playerSortKey
            ) {

                arrowElement.textContent =
                    "";

                return;
            }


            arrowElement.textContent =
                playerSortDirection
                === "asc"
                    ? "▲"
                    : "▼";

        }
    );

}

async function checkPlayerRankingSyncStatus() {

    if (playerSyncCheckRunning) {
        return;
    }


    playerSyncCheckRunning =
        true;


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/player-rankings/sync-status`
            );


        if (!response.ok) {

            throw new Error(
                "선수 기록 동기화 상태를 불러오지 못했습니다."
            );

        }


        const data =
            await response.json();


        if (
            data.conflict_count > 0
        ) {

            playerSyncStatusElement.hidden =
                false;


            playerSyncStatusMessageElement
                .textContent =
                    "선수 기록 확인이 필요한 경기가 있습니다.";


            return;
        }


        if (
            data.is_syncing
        ) {

            playerSyncStatusElement.hidden =
                false;


            playerSyncStatusMessageElement
                .textContent =
                    "선수 기록 집계 중입니다. "
                    + "30분마다 자동으로 다시 확인합니다.";


            return;
        }


        playerSyncStatusElement.hidden =
            true;


        playerSyncStatusMessageElement
            .textContent =
                "";


        await loadPlayerRankings();

    } catch (error) {

        console.error(
            error
        );

    } finally {

        playerSyncCheckRunning =
            false;

    }

}


async function initializePlayerRankings() {

    await loadPlayerSeasonMetadata();

    await loadPlayerRankings();

    await checkPlayerRankingSyncStatus();

}


initializePlayerRankings();


setInterval(
    checkPlayerRankingSyncStatus,
    playerSyncCheckIntervalMs
);