import {
    apiBaseUrl,
    loadFclSeasons,
    resolvePublicDisplaySeason,
} from "./config.js?v=season-default-1";


const playersTableBodyElement =
    document.querySelector(
        ".players-table-body"
    );


const playerSeasonTabsElement =
    document.querySelector(
        "#player-season-tabs"
    );


const playerDescriptionElement =
    document.querySelector(
        ".players-header p"
    );


let selectedPlayerSeasonNumber =
    null;


let availablePlayerSeasons =
    [];


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

    "곤살루 게드스":
        "./assets/images/players/custom/goncalo_guedes.png",
        
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
// FCL 시즌 선택
// =========================================

function getRequestedPlayerSeasonNumber() {

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


function updatePlayerDescription() {

    if (!playerDescriptionElement) {
        return;
    }


    if (!selectedPlayerSeasonNumber) {

        playerDescriptionElement.textContent =
            "FC Online Champions League 정규리그 선수 누적 기록";

        return;
    }


    playerDescriptionElement.textContent =
        (
            `SEASON ${selectedPlayerSeasonNumber} `
            + "정규리그 선수 누적 기록"
        );
}


function renderPlayerSeasonTabs() {

    if (!playerSeasonTabsElement) {
        return;
    }


    playerSeasonTabsElement.innerHTML =
        "";


    availablePlayerSeasons.forEach(
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
                selectedPlayerSeasonNumber
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
                        selectedPlayerSeasonNumber
                    ) {

                        return;
                    }


                    selectedPlayerSeasonNumber =
                        nextSeasonNumber;


                    const url =
                        new URL(
                            window.location.href
                        );


                    url.searchParams.set(
                        "season",
                        String(
                            selectedPlayerSeasonNumber
                        )
                    );


                    window.history.replaceState(
                        {},
                        "",
                        url
                    );


                    renderPlayerSeasonTabs();

                    updatePlayerDescription();


                    await Promise.all([
                        loadPlayerRankings(),
                        checkPlayerRankingSyncStatus(
                            false
                        ),
                    ]);
                }
            );


            playerSeasonTabsElement.appendChild(
                seasonButtonElement
            );
        }
    );
}


async function loadPlayerSeasonTabs() {

    try {

        availablePlayerSeasons =
            await loadFclSeasons();


        if (
            availablePlayerSeasons.length
            === 0
        ) {

            throw new Error(
                "등록된 시즌이 없습니다."
            );
        }


        const requestedSeasonNumber =
            getRequestedPlayerSeasonNumber();


        const selectedSeason =
            resolvePublicDisplaySeason(
                availablePlayerSeasons,
                requestedSeasonNumber
            );


        if (!selectedSeason) {

            throw new Error(
                "표시할 시즌을 찾을 수 없습니다."
            );
        }


        selectedPlayerSeasonNumber =
            Number(
                selectedSeason
                    .season_number
            );


        renderPlayerSeasonTabs();

        updatePlayerDescription();


        await Promise.all([
            loadPlayerRankings(),
            checkPlayerRankingSyncStatus(
                false
            ),
        ]);


    } catch (error) {

        console.error(
            error
        );


        if (playerSeasonTabsElement) {

            playerSeasonTabsElement.innerHTML = `
                <p>
                    시즌 정보를 불러오는 중
                    오류가 발생했습니다.
                </p>
            `;
        }
    }
}


// =========================================
// 선수 기록 불러오기
// =========================================

async function loadPlayerRankings() {

    try {

        if (!selectedPlayerSeasonNumber) {
            return;
        }


        const response = await fetch(
            `${apiBaseUrl}/api/player-rankings`
            + `?season=${selectedPlayerSeasonNumber}`
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
                    SEASON ${selectedPlayerSeasonNumber}에
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

async function checkPlayerRankingSyncStatus(
    reloadRankingsWhenReady = true
) {

    if (playerSyncCheckRunning) {
        return;
    }

    if (!selectedPlayerSeasonNumber) {
        return;
    }


    playerSyncCheckRunning =
        true;


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/player-rankings/sync-status`
                + `?season=${selectedPlayerSeasonNumber}`
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


        if (
            reloadRankingsWhenReady
        ) {

            await loadPlayerRankings();
        }

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

    await loadPlayerSeasonTabs();

}


initializePlayerRankings();


setInterval(
    checkPlayerRankingSyncStatus,
    playerSyncCheckIntervalMs
);