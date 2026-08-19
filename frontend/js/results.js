import {
    apiBaseUrl,
    getTeamImagePath,
    formatKstDateTime,
} from "./config.js";


const resultsListElement =
    document.querySelector(".results-list");

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

        resultCardElement.classList.add(
            "result-card"
        );


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
                                ${mvp.player_name}
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
                        src="${getTeamImagePath(result.team_a)}"
                        alt="${result.team_a} 로고"
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
                        src="${getTeamImagePath(result.team_b)}"
                        alt="${result.team_b} 로고"
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
// 실행
// =========================================

loadResults();

