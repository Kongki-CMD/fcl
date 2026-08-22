import {
    apiBaseUrl,
    getTeamImagePath,
    formatKstDateTime,
} from "./config.js";


//선수 사진 추가
const resultDetailCustomPlayerImages = {
    "주앙 칸셀루":
        "./assets/images/players/custom/cancelo.png",

    "닉 포프":
        "./assets/images/players/custom/nick_pope.png",

};

const resultsListElement =
    document.querySelector(".results-list");

const resultDetailModalElement =
    document.querySelector(
        "#result-detail-modal"
    );

const resultDetailContentElement =
    document.querySelector(
        "#result-detail-content"
    );

let currentResultDetailData = null;

let currentResultDetailSide =
    "team_a";

let resultDetailSeasonMap = new Map();

const resultDetailPositionLayout = {

    // 골키퍼
    0: {
        name: "GK",
        left: 50,
        top: 88,
    },

    1: {
        name: "SW",
        left: 50,
        top: 82,
    },

    // 수비
    2: {
        name: "RWB",
        left: 88,
        top: 79,
    },

    3: {
        name: "RB",
        left: 86,
        top: 80,
    },

    4: {
        name: "RCB",
        left: 63,
        top: 80,
    },

    5: {
        name: "CB",
        left: 50,
        top: 80,
    },

    6: {
        name: "LCB",
        left: 37,
        top: 80,
    },

    7: {
        name: "LB",
        left: 14,
        top: 80,
    },

    8: {
        name: "LWB",
        left: 12,
        top: 79,
    },


   // 수비형 미드필더
    9: {
        name: "RDM",
        left: 65,
        top: 56,
    },

    10: {
        name: "CDM",
        left: 50,
        top: 56,
    },

    11: {
        name: "LDM",
        left: 35,
        top: 56,
    },

    12: {
        name: "RM",
        left: 84,
        top: 49,
    },

    13: {
        name: "RCM",
        left: 64,
        top: 49,
    },

    14: {
        name: "CM",
        left: 50,
        top: 49,
    },

    15: {
        name: "LCM",
        left: 36,
        top: 49,
    },

    16: {
        name: "LM",
        left: 16,
        top: 49,
    },

    17: {
        name: "RAM",
        left: 68,
        top: 35,
    },

    18: {
        name: "CAM",
        left: 50,
        top: 35,
    },

    19: {
        name: "LAM",
        left: 32,
        top: 35,
    },

    20: {
        name: "RF",
        left: 72,
        top: 21,
    },

    21: {
        name: "CF",
        left: 50,
        top: 30,
    },

    22: {
        name: "LF",
        left: 28,
        top: 21,
    },

    23: {
        name: "RW",
        left: 85,
        top: 17,
    },

    24: {
        name: "RS",
        left: 65,
        top: 12,
    },

    25: {
        name: "ST",
        left: 50,
        top: 9,
    },

    26: {
        name: "LS",
        left: 35,
        top: 12,
    },

    27: {
        name: "LW",
        left: 15,
        top: 17,
    },
};


//시즌 메타데이터 로딩 함수
async function loadResultDetailSeasonMetadata() {

    if (
        resultDetailSeasonMap.size > 0
    ) {
        return;
    }


    const response = await fetch(
        `${apiBaseUrl}/api/fconline/metadata/seasons`
    );


    if (!response.ok) {

        throw new Error(
            "시즌 메타데이터 조회 실패"
        );
    }


    const data =
        await response.json();


    resultDetailSeasonMap =
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
}

//공통 조회 함수
function getResultDetailSeasonInfo(
    spId
) {

    const numericSpId =
        Number(spId);


    if (
        !Number.isFinite(
            numericSpId
        )
    ) {
        return null;
    }


    const seasonId =
        Math.floor(
            numericSpId
            /
            1_000_000
        );


    return (
        resultDetailSeasonMap.get(
            seasonId
        )
        ||
        null
    );
}

//시즌아이콘 HTML 생성 함수
function createResultDetailSeasonIconHtml(
    spId,
    className = ""
) {

    const season =
        getResultDetailSeasonInfo(
            spId
        );


    if (
        !season
        ||
        !season.season_image_url
    ) {
        return "";
    }


    return `
        <img
            src="${season.season_image_url}"
            alt="${season.class_name}"
            title="${season.class_name}"
            class="result-detail-season-icon ${className}"
        >
    `;
}


//사진 추가 함수
function getResultDetailPlayerImage(player) {

    return (
        resultDetailCustomPlayerImages[
            player.player_name
        ]
        ||
        player.image_url
    );
}

// =========================================
// Excel / DB 중복 판별용 키
// =========================================

function createResultKey(result) {

    const teams = [
        result.team_a,
        result.team_b,
    ].sort();


    return [
        result.date,
        result.match_type,
        teams[0],
        teams[1],
    ].join("|");
}


// =========================================
// 경기 결과 불러오기
// =========================================

async function loadResults() {

    try {

        await loadResultDetailSeasonMetadata();

        // ================================
        // Excel 결과 + Neon 결과
        // ================================

        const [
            excelResponse,
            databaseResponse,
        ] = await Promise.all([
            fetch(
                `${apiBaseUrl}/api/results`
            ),

            fetch(
                `${apiBaseUrl}/api/fconline/series/completed-results`
            ),
        ]);


        // ================================
        // Excel 결과
        // ================================

        if (!excelResponse.ok) {

            throw new Error(
                "경기 결과를 불러오지 못했습니다."
            );

        }


        const excelResults =
            await excelResponse.json();


        // ================================
        // Neon 결과
        // ================================

        let databaseResults = [];


        if (databaseResponse.ok) {

            databaseResults =
                await databaseResponse.json();

        } else {

            console.error(
                "DB 경기 결과를 불러오지 못했습니다."
            );

        }


        // ================================
        // DB와 중복되는 기존 Excel 결과 제거
        //
        // DB 결과를 우선 사용
        // ================================

        const databaseResultKeys =
            new Set(
                databaseResults.map(
                    createResultKey
                )
            );


        const filteredExcelResults =
            excelResults.filter(
                result =>
                    !databaseResultKeys.has(
                        createResultKey(
                            result
                        )
                    )
            );


        // ================================
        // 결과 합치기
        // ================================

        const combinedResults = [
            ...databaseResults,
            ...filteredExcelResults,
        ];


        // 최신 경기 우선
        combinedResults.sort(
            (resultA, resultB) => {

                const dateCompare =
                    resultB.date.localeCompare(
                        resultA.date
                    );


                if (dateCompare !== 0) {

                    return dateCompare;

                }


                return (
                    (resultB.series_id ?? 0)
                    -
                    (resultA.series_id ?? 0)
                );

            }
        );


        renderResults(
            combinedResults
        );


    } catch (error) {

        console.error(
            error
        );


        resultsListElement.innerHTML = `
            <p>
                경기 결과를 불러오는 중
                오류가 발생했습니다.
            </p>
        `;

    }

}

// =========================================
// 완료 SERIES NEXON 기록 동기화
// =========================================

async function syncCompletedSeries(
    seriesId,
    buttonElement,
    messageElement
) {

    if (!seriesId) {
        return;
    }


    const originalText =
        buttonElement.textContent;


    buttonElement.disabled =
        true;


    buttonElement.textContent =
        "NEXON 확인 중...";


    if (messageElement) {

        messageElement.textContent =
            "";
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/sync`,
            {
                method: "POST"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status === 429
            ) {

                throw new Error(
                    "NEXON API 호출 제한 중입니다. 잠시 후 다시 확인해주세요."
                );
            }


            throw new Error(
                data.detail
                ??
                "NEXON 기록 확인에 실패했습니다."
            );
        }


        const statsSyncStatus =
            data.series
                ?.stats_sync_status;


        if (messageElement) {

            messageElement.textContent =
                data.sync_message
                ??
                "NEXON 경기 기록을 확인했습니다.";
        }


        // =============================
        // 동기화 완료
        // 결과 목록 다시 불러오기
        // MVP도 새로 표시됨
        // =============================

        if (
            statsSyncStatus
            === "synced"
        ) {

            await loadResults();

            return;
        }


        // =============================
        // 점수 충돌
        // =============================

        if (
            statsSyncStatus
            === "conflict"
        ) {

            buttonElement.disabled =
                false;


            buttonElement.textContent =
                "NEXON 기록 다시 확인";


            return;
        }


        // =============================
        // 아직 NEXON 반영 대기
        // =============================

        buttonElement.disabled =
            false;


        buttonElement.textContent =
            "NEXON 기록 확인";


    } catch (error) {

        console.error(
            error
        );


        if (messageElement) {

            messageElement.textContent =
                error.message;
        }


        buttonElement.disabled =
            false;


        buttonElement.textContent =
            originalText;
    }
}

// =========================================
// 경기 상세 모달
// =========================================

function closeResultDetail() {

    // 모달 내부에 포커스가 남아 있으면 먼저 제거
    const activeElement =
        document.activeElement;


    if (
        activeElement
        &&
        resultDetailModalElement.contains(
            activeElement
        )
    ) {

        activeElement.blur();
    }


    // 키보드/포커스 접근 차단
    resultDetailModalElement.inert =
        true;


    resultDetailModalElement.classList.add(
        "hidden"
    );


    resultDetailModalElement.setAttribute(
        "aria-hidden",
        "true"
    );


    document.body.classList.remove(
        "result-detail-modal-open"
    );


    resultDetailContentElement.innerHTML =
        "";


    currentResultDetailData =
        null;


    currentResultDetailSide =
        "team_a";
}


// =========================================
// 스쿼드 선수 카드
// =========================================

function createSquadPlayerHtml(
    player
) {

    const recordText = [];

    if (player.goals > 0) {

        recordText.push(
            `${player.goals}골`
        );
    }


    if (player.assists > 0) {

        recordText.push(
            `${player.assists}도움`
        );
    }


    return `
        <div class="result-detail-player">

            <img
                src="${player.image_url}"
                alt="${player.player_name}"
                class="result-detail-player-image"
            >

            <div class="result-detail-player-info">

                <strong>
                    ${player.player_name}
                </strong>

                <span>
                    +${player.sp_grade}
                </span>

                <span>
                    평점 ${player.rating.toFixed(1)}
                </span>

                ${
                    recordText.length > 0
                        ? `
                            <span class="result-detail-player-record">
                                ${recordText.join(" · ")}
                            </span>
                        `
                        : ""
                }

            </div>

        </div>
    `;
}


function createFormationPlayerHtml(
    player
) {

    const position =
        resultDetailPositionLayout[
            player.sp_position
        ];


    if (!position) {
        return "";
    }


    const recordText = [];


    if (player.goals > 0) {

        recordText.push(`
            <span class="result-detail-record-item">

                <span class="result-detail-goal-icon">
                    ⚽
                </span>

                ${player.goals}

            </span>
        `);
    }


    if (player.assists > 0) {

        recordText.push(`
            <span class="result-detail-record-item">

                <span class="result-detail-assist-icon">
                    A
                </span>

                ${player.assists}

            </span>
        `);
    }


    return `
        <div
            class="result-detail-formation-player"
            style="
                left: ${position.left}%;
                top: ${position.top}%;
            "
        >

            <span class="result-detail-formation-position">
                ${position.name}
            </span>


            <div class="result-detail-formation-image-wrap">

                <img
                    src="${getResultDetailPlayerImage(player)}"
                    alt="${player.player_name}"
                    class="result-detail-formation-image"
                >

                <span class="result-detail-formation-grade">
                    +${player.sp_grade}
                </span>

            </div>


            <div class="result-detail-formation-info">

                <strong class="result-detail-formation-player-name">

                    ${createResultDetailSeasonIconHtml(
                        player.sp_id,
                        "formation"
                    )}

                    <span>
                        ${player.player_name}
                    </span>

                </strong>

                <span>
                    ${player.rating.toFixed(1)}
                    &nbsp;
                ${
                    recordText.length > 0
                        ? `
                            ${recordText.join(" · ")}
                        `
                        : ""
                }
                </span>

            </div>

        </div>
    `;
}

// =========================================
// 선택 SET 스쿼드 출력
// =========================================



// =========================================
// 선택 참가자 스쿼드 화면
// =========================================

function renderResultDetailSquadView(
    setData,
    side
) {

    const squadViewElement =
        document.querySelector(
            "#result-detail-squad-view"
        );


    if (!squadViewElement) {
        return;
    }


    const isTeamA =
        side === "team_a";


    const participant =
        isTeamA
            ? currentResultDetailData.team_a
            : currentResultDetailData.team_b;


    const squad =
        isTeamA
            ? setData.team_a_squad
            : setData.team_b_squad;


    const startingPlayers =
        squad.filter(
            player =>
                player.sp_position !== 28
        );

    const formationPlayersHtml =
    startingPlayers
        .map(
            createFormationPlayerHtml
        )
        .join("");


    const benchPlayers =
        squad.filter(
            player =>
                player.sp_position === 28
        );

    squadViewElement.innerHTML = `

    <div class="result-detail-pitch">

        <div class="result-detail-pitch-center-line"></div>

        <div class="result-detail-pitch-center-circle"></div>

        <div class="
            result-detail-pitch-penalty-box
            top
        "></div>

        <div class="
            result-detail-pitch-penalty-box
            bottom
        "></div>


        ${formationPlayersHtml}

    </div>
`;


}


function getResultDetailSetMvp(
    setData
) {

    const players = [
        ...setData.team_a_squad.map(
            player => ({
                ...player,
                side: "team_a",
            })
        ),

        ...setData.team_b_squad.map(
            player => ({
                ...player,
                side: "team_b",
            })
        ),
    ];


    const playedPlayers =
        players.filter(
            player =>
                player.sp_position !== 28
        );


    if (
        playedPlayers.length === 0
    ) {
        return null;
    }


    playedPlayers.sort(
        (playerA, playerB) => {

            const ratingDifference =
                Number(
                    playerB.rating ?? 0
                )
                -
                Number(
                    playerA.rating ?? 0
                );


            if (
                ratingDifference !== 0
            ) {
                return ratingDifference;
            }


            const goalDifference =
                Number(
                    playerB.goals ?? 0
                )
                -
                Number(
                    playerA.goals ?? 0
                );


            if (
                goalDifference !== 0
            ) {
                return goalDifference;
            }


            return (
                Number(
                    playerB.assists ?? 0
                )
                -
                Number(
                    playerA.assists ?? 0
                )
            );
        }
    );


    return playedPlayers[0];
}

function createResultDetailSetMvpHtml(
    setData
) {

    const mvp =
        getResultDetailSetMvp(
            setData
        );


    if (!mvp) {

        return `
            <div class="result-detail-set-mvp">

                <span class="result-detail-set-mvp-label">
                    SET MVP
                </span>

                <p>
                    MVP 기록 없음
                </p>

            </div>
        `;
    }


    const participant =
        mvp.side === "team_a"
            ? currentResultDetailData.team_a
            : currentResultDetailData.team_b;


    return `
        <div class="result-detail-set-mvp">

            <span class="result-detail-set-mvp-label">
                SET MVP
            </span>


            <div class="result-detail-set-mvp-player">

                <img
                    src="${getResultDetailPlayerImage(mvp)}"
                    alt="${mvp.player_name}"
                >


                <div>

                <strong class="result-detail-set-mvp-name">

                    ${createResultDetailSeasonIconHtml(
                        mvp.sp_id,
                        "set-mvp"
                    )}

                    <span>
                        ${mvp.player_name}
                    </span>

                </strong>

                    <span>
                        ${participant.fcl_name}
                    </span>

                    <small>
                        평점
                        ${Number(
                            mvp.rating ?? 0
                        ).toFixed(1)}
                    </small>

                </div>

            </div>

        </div>
    `;
}

// =========================================
// 선택 SET 출력
// =========================================

function renderResultDetailSet(
    setNumber
) {

    if (!currentResultDetailData) {
        return;
    }


    const setData =
        currentResultDetailData.sets.find(
            item =>
                item.set === setNumber
        );


    if (!setData) {
        return;
    }


    const squadElement =
        document.querySelector(
            "#result-detail-squad"
        );


    if (!squadElement) {
        return;
    }


    squadElement.innerHTML = `

    <div class="result-detail-workspace">

        <aside class="result-detail-control-panel">

            <div class="result-detail-participant-select">

                <div class="result-detail-control-title">

                    <span>
                        2
                    </span>

                    <strong>
                        참가자 선택
                    </strong>

                </div>


                <div class="result-detail-participant-buttons">

                    <button
                        type="button"
                        class="
                            result-detail-participant-button
                            ${
                                currentResultDetailSide
                                    === "team_a"
                                    ? "active"
                                    : ""
                            }
                        "
                        data-result-detail-side="team_a"
                    >

                        <img
                            src="${currentResultDetailData.team_a.logo_path}"
                            alt=""
                        >

                        <span>
                            ${currentResultDetailData.team_a.fcl_name}
                        </span>

                    </button>


                    <button
                        type="button"
                        class="
                            result-detail-participant-button
                            ${
                                currentResultDetailSide
                                    === "team_b"
                                    ? "active"
                                    : ""
                            }
                        "
                        data-result-detail-side="team_b"
                    >

                        <img
                            src="${currentResultDetailData.team_b.logo_path}"
                            alt=""
                        >

                        <span>
                            ${currentResultDetailData.team_b.fcl_name}
                        </span>

                    </button>

                </div>

                ${createResultDetailSetMvpHtml(setData)}

            </div>

        </aside>


        <div
            id="result-detail-squad-view"
            class="result-detail-squad-view"
        ></div>

    </div>
`;


    document
        .querySelectorAll(
            "[data-result-detail-set]"
        )
        .forEach(
            buttonElement => {

                buttonElement.classList.toggle(
                    "active",
                    Number(
                        buttonElement.dataset
                            .resultDetailSet
                    )
                    === setNumber
                );
            }
        );


    renderResultDetailSquadView(
        setData,
        currentResultDetailSide
    );
}


async function openResultDetail(
    seriesId
) {

    await loadResultDetailSeasonMetadata();

    resultDetailModalElement.inert =
        false;

    resultDetailModalElement.classList.remove(
        "hidden"
    );

    resultDetailModalElement.setAttribute(
        "aria-hidden",
        "false"
    );

    document.body.classList.add(
        "result-detail-modal-open"
    );


    resultDetailContentElement.innerHTML = `
        <div class="result-detail-loading">
            경기 상세 정보를 불러오는 중...
        </div>
    `;


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/squads`
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "경기 상세 정보를 불러오지 못했습니다."
            );
        }

        currentResultDetailData =
            data;


        const setTabHtml =
            data.sets.map(
                (setData) => `
                    <button
                        type="button"
                        class="result-detail-set-tab"
                        data-result-detail-set="${setData.set}"
                    >
                        <strong>
                            SET ${setData.set}
                        </strong>

                        <span>
                            ${setData.team_a_score}
                            :
                            ${setData.team_b_score}
                        </span>
                    </button>
                `
            ).join("");


        resultDetailContentElement.innerHTML = `

        <div class="result-detail-match-title">

            <div class="result-detail-match-team">
                <img
                    src="${data.team_a.logo_path}"
                    alt=""
                    class="result-detail-match-team-logo"
                >

                <span>
                    ${data.team_a.fcl_name}
                </span>
            </div>


            <strong class="result-detail-match-vs">
                VS
            </strong>


            <div class="result-detail-match-team">
                <img
                    src="${data.team_b.logo_path}"
                    alt=""
                    class="result-detail-match-team-logo"
                >

                <span>
                    ${data.team_b.fcl_name}
                </span>
            </div>

        </div>


        <div class="result-detail-set-section">

            <div class="result-detail-set-title">

                <span>
                    1
                </span>

                <strong>
                    세트 선택
                </strong>

            </div>


            <div
                class="result-detail-set-tabs"
                style="
                    grid-template-columns:
                        repeat(
                            ${data.sets.length},
                            minmax(0, 1fr)
                        );
                "
            >
                ${setTabHtml}
            </div>

        </div>


            <div
                id="result-detail-squad"
                class="result-detail-squad"
            >
            </div>

        `;


    } catch (error) {

        console.error(
            error
        );


        resultDetailContentElement.innerHTML = `
            <div class="result-detail-error">
                ${error.message}
            </div>
        `;

        if (data.sets.length > 0) {

            renderResultDetailSet(
                data.sets[0].set
            );
        }
    }
}


// =========================================
// 경기 결과 출력
// =========================================

function renderResults(
    results
) {

    resultsListElement.innerHTML = "";


    if (results.length === 0) {

        resultsListElement.innerHTML = `
            <p>
                등록된 경기 결과가 없습니다.
            </p>
        `;

        return;
    }


    results.forEach((result) => {

        const resultCardElement =
            document.createElement("div");
        
        const teamAImagePath =
            result.team_a_snapshot_logo_path
            ?? getTeamImagePath(
                result.team_a
            );

        const teamBImagePath =
            result.team_b_snapshot_logo_path
            ?? getTeamImagePath(
                result.team_b
            );

        const teamALogoName =
            result.team_a_snapshot_name
            ?? result.team_a;

        const teamBLogoName =
            result.team_b_snapshot_name
            ?? result.team_b;
        
        resultCardElement.classList.add(
            "result-card"
        );

        // 여기 추가
        if (result.series_id) {

            resultCardElement.classList.add(
                "result-card-detail-enabled"
            );

            resultCardElement.dataset.seriesDetailId =
                result.series_id;
        }


        // =====================================
        // 프리시즌 / 정규리그 표시
        // =====================================

        let resultLabel = "";


        if (result.match_type === "프리시즌") {

            resultLabel = `
                <span class="match-preseason">
                    PRE-SEASON
                </span>
            `;

        } else if (result.round) {

            resultLabel = `
                <span class="match-round">
                    ROUND ${result.round}
                </span>
            `;

        }

        const finishedTimeHtml =
            result.completed_at
                ? `
                    <span class="result-finished-time">
                        종료시간 :
                        ${formatKstDateTime(
                            result.completed_at
                        )}
                        KST
                    </span>
                `
                : "";


        // =====================================
        // 세트별 결과
        // =====================================

        const setScoreHtml = (result.sets ?? [])
            .map((setResult) => {

                let teamAResult = "";
                let teamBResult = "";


                // 팀A 승리
                if (
                    setResult.team_a_score >
                    setResult.team_b_score
                ) {

                    teamAResult = `
                        <span class="set-result-badge win">
                            W
                        </span>
                    `;

                    teamBResult = `
                        <span class="set-result-badge loss">
                            L
                        </span>
                    `;


                // 팀B 승리
                } else if (
                    setResult.team_a_score <
                    setResult.team_b_score
                ) {

                    teamAResult = `
                        <span class="set-result-badge loss">
                            L
                        </span>
                    `;

                    teamBResult = `
                        <span class="set-result-badge win">
                            W
                        </span>
                    `;


                // 무승부
                } else {

                    teamAResult = `
                        <span class="set-result-badge draw">
                            D
                        </span>
                    `;

                    teamBResult = `
                        <span class="set-result-badge draw">
                            D
                        </span>
                    `;

                }


                return `
                    <div class="set-score-row">

                        <span class="set-name">
                            ${setResult.set}세트
                        </span>


                        <div class="set-score">

                            <span class="set-score-side">

                                ${teamAResult}

                                <span>
                                    ${setResult.team_a_score}
                                </span>

                            </span>


                            <span class="set-score-divider">
                                :
                            </span>


                            <span class="set-score-side">

                                <span>
                                    ${setResult.team_b_score}
                                </span>

                                ${teamBResult}

                            </span>

                        </div>

                    </div>
                `;
            })
            .join("");


        // =====================================
        // MVP
        // Neon SERIES 결과에 저장된 MVP 사용
        // =====================================

        let mvpHtml = "";


        const mvp =
            result.mvp;


        if (mvp) {

            mvpHtml = `
                <div class="match-mvp">

                    <div class="match-mvp-title">
                        ★ MATCH MVP
                    </div>


                    <div class="match-mvp-content">

                        <img
                            src="${mvp.image_url}"
                            alt="${mvp.player_name}"
                            class="match-mvp-image"
                        >


                        <div class="match-mvp-info">

                            <strong class="match-mvp-name">

                                ${createResultDetailSeasonIconHtml(
                                    mvp.sp_id,
                                    "match-mvp-season"
                                )}

                                <span>
                                    ${mvp.player_name}
                                </span>

                            </strong>


                            <span class="match-mvp-owner">
                                ${mvp.fcl_name}
                                (${mvp.nickname})
                            </span>


                            <div class="match-mvp-stats">

                                <span>
                                    합산 평점
                                    <strong>
                                        ${mvp.rating_total}
                                    </strong>
                                </span>


                                <span>
                                    평균
                                    <strong>
                                        ${mvp.average_rating}
                                    </strong>
                                </span>


                                <span>
                                    ${mvp.goals}골
                                    ${mvp.assists}도움
                                </span>


                                <span>
                                    ${mvp.sets_played}세트 출전
                                </span>

                            </div>

                        </div>

                    </div>

                </div>
            `;

        }

// =====================================
// NEXON 기록 동기화
// =====================================

let syncHtml = "";


const statsSyncStatus =
    result.stats_sync_status;


const canSyncNexon =
    result.source === "database"
    &&
    result.series_id
    &&
    (
        statsSyncStatus === "pending"
        ||
        statsSyncStatus === "conflict"
    );


if (canSyncNexon) {

    const syncButtonText =
        statsSyncStatus === "conflict"
            ? "NEXON 기록 다시 확인"
            : "NEXON 기록 확인";


    const syncStatusText =
        statsSyncStatus === "conflict"
            ? "수동 점수와 NEXON 기록 확인 필요"
            : `
                MVP 선수 선정 대기 중
                <br>
                <span class="result-sync-guide">
                    경기 후 2시간 뒤 클릭 바랍니다.
                    (NEXON 데이터 반영 시간)
                </span>
            `;


    syncHtml = `
        <div class="result-sync-panel">

            <div class="result-sync-status">
                ${syncStatusText}
            </div>

            <button
                type="button"
                class="result-sync-button"
                data-series-sync-button
                data-series-id="${result.series_id}"
            >
                ${syncButtonText}
            </button>

            <div
                class="result-sync-message"
                data-series-sync-message
            ></div>

        </div>
    `;
}


        // =====================================
        // 경기 결과 카드
        // =====================================

        resultCardElement.innerHTML = `

            <div class="result-date">

                <div class="result-date-info">

                    <span>
                        ${result.date}
                    </span>

                    ${resultLabel}

                </div>


                ${finishedTimeHtml}

            </div>


            <div class="result-teams">


                <div class="result-team-box">

                    <img
                        src="${teamAImagePath}"
                        alt="${teamALogoName} 로고"
                        class="team-image"
                    >

                    <span class="result-team-name">
                        ${result.team_a}
                    </span>

                </div>


                <div class="result-score">

                    <span>
                        ${result.team_a_score}
                    </span>

                    <span class="score-divider">
                        :
                    </span>

                    <span>
                        ${result.team_b_score}
                    </span>

                </div>


                <div class="result-team-box">

                    <img
                        src="${teamBImagePath}"
                        alt="${teamBLogoName} 로고"
                        class="team-image"
                    >

                    <span class="result-team-name">
                        ${result.team_b}
                    </span>

                </div>


            </div>


            <div class="set-score-list">

                ${setScoreHtml}

            </div>

            ${syncHtml}

            ${mvpHtml}

        `;


        resultsListElement.appendChild(
            resultCardElement
        );

    });

}

// =========================================
// NEXON 기록 확인 버튼
// =========================================

resultsListElement.addEventListener(
    "click",
    (event) => {

        const syncButtonElement =
            event.target.closest(
                "[data-series-sync-button]"
            );


        if (!syncButtonElement) {
            return;
        }


        const seriesId =
            Number(
                syncButtonElement.dataset
                    .seriesId
            );


        const resultCardElement =
            syncButtonElement.closest(
                ".result-card"
            );


        const syncMessageElement =
            resultCardElement
                ?.querySelector(
                    "[data-series-sync-message]"
                );


        syncCompletedSeries(
            seriesId,
            syncButtonElement,
            syncMessageElement
        );
    }
);

// =========================================
// 경기 상세 열기
// =========================================

resultsListElement.addEventListener(
    "click",
    (event) => {

        // NEXON 동기화 버튼은 제외
        if (
            event.target.closest(
                "[data-series-sync-button]"
            )
        ) {

            return;
        }


        const detailCardElement =
            event.target.closest(
                "[data-series-detail-id]"
            );


        if (!detailCardElement) {
            return;
        }


        const seriesId =
            Number(
                detailCardElement.dataset
                    .seriesDetailId
            );


        if (!seriesId) {
            return;
        }


        openResultDetail(
            seriesId
        );
    }
);


// =========================================
// 경기 상세 닫기
// =========================================

resultDetailModalElement.addEventListener(
    "click",
    (event) => {

        const closeElement =
            event.target.closest(
                "[data-result-detail-close]"
            );


        if (!closeElement) {
            return;
        }


        closeResultDetail();
    }
);


document.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Escape"
            &&
            !resultDetailModalElement
                .classList
                .contains("hidden")
        ) {

            closeResultDetail();
        }
    }
);

// =========================================
// 경기 상세 SET 선택
// =========================================

resultDetailModalElement.addEventListener(
    "click",
    (event) => {

        const setButtonElement =
            event.target.closest(
                "[data-result-detail-set]"
            );


        if (!setButtonElement) {
            return;
        }


        const setNumber =
            Number(
                setButtonElement.dataset
                    .resultDetailSet
            );


        renderResultDetailSet(
            setNumber
        );
    }
);

// =========================================
// 경기 상세 참가자 선택
// =========================================

resultDetailModalElement.addEventListener(
    "click",
    (event) => {

        const participantButtonElement =
            event.target.closest(
                "[data-result-detail-side]"
            );


        if (!participantButtonElement) {
            return;
        }


        currentResultDetailSide =
            participantButtonElement.dataset
                .resultDetailSide;


        const activeSetButtonElement =
            resultDetailModalElement
                .querySelector(
                    ".result-detail-set-tab.active"
                );


        if (!activeSetButtonElement) {
            return;
        }


        const setNumber =
            Number(
                activeSetButtonElement.dataset
                    .resultDetailSet
            );


        renderResultDetailSet(
            setNumber
        );
    }
);




// =========================================
// 실행
// =========================================



loadResults();

