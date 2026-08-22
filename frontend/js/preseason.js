import {
    apiBaseUrl
} from "./config.js";


const teamASelectElement =
    document.querySelector(
        "#team-a-select"
    );

const teamBSelectElement =
    document.querySelector(
        "#team-b-select"
    );

const seriesStartButtonElement =
    document.querySelector(
        "#series-start-button"
    );

const historyImportButtonElement =
    document.querySelector(
        "#history-import-button"
    );

const preseasonMessageElement =
    document.querySelector(
        "#preseason-message"
    );

const seriesStatusCardElement =
    document.querySelector(
        "#series-status-card"
    );

const seriesStatusBadgeElement =
    document.querySelector(
        "#series-status-badge"
    );

const seriesTitleElement =
    document.querySelector(
        "#series-title"
    );

const seriesProgressElement =
    document.querySelector(
        "#series-progress"
    );

const seriesSetListElement =
    document.querySelector(
        "#series-set-list"
    );

const seriesTotalScoreElement =
    document.querySelector(
        "#series-total-score"
    );

const seriesMvpElement =
    document.querySelector(
        "#series-mvp"
    );

const preseasonStartCardElement =
    document.querySelector(
        "#preseason-start-card"
    );


const seriesActionButtonsElement =
    document.querySelector(
        "#series-action-buttons"
    );


const manualResultButtonElement =
    document.querySelector(
        "#manual-result-button"
    );


const seriesCancelButtonElement =
    document.querySelector(
        "#series-cancel-button"
    );


const manualResultPanelElement =
    document.querySelector(
        "#manual-result-panel"
    );


const manualTeamANameElement =
    document.querySelector(
        "#manual-team-a-name"
    );


const manualTeamBNameElement =
    document.querySelector(
        "#manual-team-b-name"
    );

const manualResultSetListElement =
    document.querySelector(
        "#manual-result-set-list"
    );


const manualBackButtonElement =
    document.querySelector(
        "#manual-back-button"
    );


const manualCompleteButtonElement =
    document.querySelector(
        "#manual-complete-button"
    );


const manualResultMessageElement =
    document.querySelector(
        "#manual-result-message"
    );

const preseasonDateInputElement =
    document.querySelector(
        "#preseason-date-input"
    );

const preseasonTodayButtonElement =
    document.querySelector(
        "#preseason-today-button"
    );

const historyRuleButtonElement =
    document.querySelector(
        "#history-rule-button"
    );

const historyRulePanelElement =
    document.querySelector(
        "#history-rule-panel"
    );

const reservationRuleButtonElement =
    document.querySelector(
        "#reservation-rule-button"
    );

const reservationRulePanelElement =
    document.querySelector(
        "#reservation-rule-panel"
    );

const seriesStatusHeaderElement =
    document.querySelector(
        ".series-status-header"
    );


let currentSeriesId = null;

let currentTeamA = "";
let currentTeamB = "";

let currentSeriesType = "";

let currentPlayoffStage = null;
let currentSeriesBestOf = 3;
let currentWinsRequired = null;

let statusTimer = null;


/* =========================
   참가자 불러오기
========================= */

async function loadParticipants() {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/database/participants`
        );


        if (!response.ok) {

            throw new Error(
                "참가자 정보를 불러오지 못했습니다."
            );

        }


        const participants =
            await response.json();


        const availableParticipants =
            participants.filter(
                participant =>
                    participant.fc_nickname
            );


        availableParticipants.forEach(
            participant => {

                const teamAOption =
                    document.createElement(
                        "option"
                    );

                teamAOption.value =
                    participant.fcl_name;

                teamAOption.textContent =
                    `${participant.fcl_name} (${participant.fc_nickname})`;


                const teamBOption =
                    teamAOption.cloneNode(
                        true
                    );


                teamASelectElement.append(
                    teamAOption
                );

                teamBSelectElement.append(
                    teamBOption
                );

            }
        );


    } catch (error) {

        preseasonMessageElement.textContent =
            error.message;

    }

}


/* =========================
   SERIES START
========================= */

async function startSeries() {

    const teamA =
        teamASelectElement.value;

    const teamB =
        teamBSelectElement.value;

    const scheduledDate =
    preseasonDateInputElement.value;

    if (!scheduledDate) {

    preseasonMessageElement.textContent =
        "친선전 날짜를 선택해주세요.";

    return;

}


    preseasonMessageElement.textContent =
        "";


    if (!teamA || !teamB) {

        preseasonMessageElement.textContent =
            "두 참가자를 모두 선택해주세요.";

        return;

    }


    if (teamA === teamB) {

        preseasonMessageElement.textContent =
            "서로 다른 참가자를 선택해주세요.";

        return;

    }


    seriesStartButtonElement.disabled =
        true;

    seriesStartButtonElement.textContent =
        "예약 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/start`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    team_a: teamA,
                    team_b: teamB,

                    series_type:
                        "프리시즌",

                    scheduled_date:
                        scheduledDate
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ?? "SERIES 시작에 실패했습니다."
            );

        }


        preseasonMessageElement.textContent =
            `${data.scheduled_date} 친선전이 예약되었습니다.`;


        seriesStartButtonElement.disabled =
            false;

        seriesStartButtonElement.textContent =
            "친선전 예약";


        setTimeout(
            () => {

                window.location.href =
                    "./schedule.html";

            },
            700
        );


    } catch (error) {

        preseasonMessageElement.textContent =
            error.message;


        seriesStartButtonElement.disabled =
            false;

        seriesStartButtonElement.textContent =
            "친선전 예약";

    }

}

/* =========================
   과거 PRE-SEASON 등록
========================= */

async function importHistorySeries() {

    const teamA =
        teamASelectElement.value;

    const teamB =
        teamBSelectElement.value;

    const matchDate =
        preseasonDateInputElement.value;


    preseasonMessageElement.textContent =
        "";


    if (!teamA || !teamB) {

        preseasonMessageElement.textContent =
            "두 참가자를 모두 선택해주세요.";

        return;
    }


    if (teamA === teamB) {

        preseasonMessageElement.textContent =
            "서로 다른 참가자를 선택해주세요.";

        return;
    }


    if (!matchDate) {

        preseasonMessageElement.textContent =
            "경기 날짜를 선택해주세요.";

        return;
    }


    const confirmed =
        window.confirm(
            `${matchDate}\n`
            + `${teamA} VS ${teamB}\n\n`
            + "실제 FC Online 경기 3세트를 찾아 등록합니다."
        );


    if (!confirmed) {
        return;
    }


    historyImportButtonElement.disabled =
        true;

    historyImportButtonElement.textContent =
        "경기 검색 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/history/import`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    team_a:
                        teamA,

                    team_b:
                        teamB,

                    match_date:
                        matchDate
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "과거 경기 등록에 실패했습니다."
            );
        }


        preseasonMessageElement.textContent =
            `${matchDate} 친선전 등록 완료`;


        setTimeout(
            () => {

                window.location.href =
                    "./results.html";

            },
            600
        );


    } catch (error) {

        preseasonMessageElement.textContent =
            error.message;


        historyImportButtonElement.disabled =
            false;

        historyImportButtonElement.textContent =
            "과거 경기 등록";
    }
}


async function loadSeriesStatus() {

    if (!currentSeriesId) {
        return;
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${currentSeriesId}/status`
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ?? "SERIES 상태 조회에 실패했습니다."
            );

        }

        if (
            data.series.status
            === "completed"
        ) {

            stopStatusPolling();


            localStorage.removeItem(
                "fclCurrentSeriesId"
            );


            currentSeriesId = null;

            currentTeamA = "";

            currentTeamB = "";


            seriesStatusCardElement.classList.add(
                "hidden"
            );


            manualResultPanelElement.classList.add(
                "hidden"
            );


            preseasonStartCardElement.classList.remove(
                "hidden"
            );


            seriesStartButtonElement.disabled =
                false;


            seriesStartButtonElement.textContent =
                "친선전 예약";


            return;
        }


        renderSeriesStatus(
            data
        );


    } catch (error) {

        console.error(
            error
        );

    }

}


/* =========================
   STATUS 화면 출력
========================= */

function renderSeriesStatus(data) {

    const series =
        data.series;

    const sets =
        data.sets;

    const mvp =
        data.mvp;


    const statsSyncStatus =
        series.stats_sync_status
        ?? "pending";


    seriesStatusCardElement.classList.remove(
        "hidden"
    );


    currentTeamA =
        series.team_a;

    currentTeamB =
        series.team_b;

    currentSeriesType =
        series.series_type;

    currentPlayoffStage =
    series.playoff_stage
    ?? null;

    currentSeriesBestOf =
        series.best_of
        ?? 3;

    currentWinsRequired =
        series.wins_required
        ?? null;


    seriesTitleElement.textContent =
        `${series.team_a} VS ${series.team_b}`;


    seriesProgressElement.textContent =
        `${series.set_count} / ${currentSeriesBestOf}`;


    /* =========================
       세트 출력
    ========================= */

    seriesSetListElement.innerHTML =
        "";


    for (
        let setNumber = 1;
        setNumber <= currentSeriesBestOf;
        setNumber++
    ) {

        const savedSet =
            sets.find(
                set =>
                    set.set === setNumber
            );


        const setElement =
            document.createElement(
                "div"
            );


        setElement.classList.add(
            "series-set-row"
        );


        if (savedSet) {

            setElement.classList.add(
                "completed"
            );


            setElement.innerHTML = `
                <span class="series-set-name">
                    ${setNumber} SET
                </span>

                <span class="series-set-score">
                    ${savedSet.team_a_score}
                    :
                    ${savedSet.team_b_score}
                </span>

                <span class="series-set-state">
                    COMPLETE
                </span>
            `;

        } else {

            setElement.innerHTML = `
                <span class="series-set-name">
                    ${setNumber} SET
                </span>

                <span class="series-set-score">
                    - : -
                </span>

                <span class="series-set-state">
                    WAITING
                </span>
            `;
        }


        seriesSetListElement.append(
            setElement
        );
    }


    /* =========================
       완료 SERIES
    ========================= */

    if (
        series.status === "completed"
    ) {

        manualResultPanelElement.classList.add(
            "hidden"
        );


        seriesStatusBadgeElement.textContent =
            "COMPLETE";

        seriesStatusBadgeElement.classList.add(
            "complete"
        );


        /* =========================
           최종 스코어
        ========================= */

        const teamATotal =
            sets.reduce(
                (
                    total,
                    set
                ) =>
                    total
                    + set.team_a_score,
                0
            );


        const teamBTotal =
            sets.reduce(
                (
                    total,
                    set
                ) =>
                    total
                    + set.team_b_score,
                0
            );


        seriesTotalScoreElement.innerHTML = `
            <div class="series-result-team">
                ${series.team_a}
            </div>

            <div class="series-result-score">
                ${teamATotal}
                :
                ${teamBTotal}
            </div>

            <div class="series-result-team">
                ${series.team_b}
            </div>
        `;


        seriesTotalScoreElement.classList.remove(
            "hidden"
        );


        renderMvp(
            mvp
        );


        /* =========================
           NEXON 통계 대기
        ========================= */

        if (
            statsSyncStatus === "pending"
            ||
            statsSyncStatus === "conflict"
        ) {

            // SERIES 자체는 완료됐지만
            // Nexon 통계 동기화가 아직 남아있음

            seriesActionButtonsElement.classList.remove(
                "hidden"
            );


            manualResultButtonElement.classList.add(
                "hidden"
            );


            seriesCancelButtonElement.classList.add(
                "hidden"
            );


            if (
                statsSyncStatus === "pending"
            ) {

                preseasonMessageElement.textContent =
                    "경기 결과가 저장되었습니다.";

            } else {

                preseasonMessageElement.textContent =
                    (
                        "수동 결과와 NEXON 기록이 "
                        + "일치하지 않습니다."
                    );
            }


            // 중요:
            // currentSeriesId 유지
            // localStorage 유지
            return;
        }


        /* =========================
           NEXON 동기화까지 완료
        ========================= */

        seriesActionButtonsElement.classList.add(
            "hidden"
        );


        seriesStartButtonElement.disabled =
            false;


        seriesStartButtonElement.textContent =
            "친선전 예약";


        localStorage.removeItem(
            "fclCurrentSeriesId"
        );


        currentSeriesId = null;

        currentTeamA = "";

        currentTeamB = "";


        preseasonStartCardElement.classList.remove(
            "hidden"
        );


        return;
    }


    /* =========================
       진행 중 SERIES
    ========================= */

    seriesStatusBadgeElement.textContent =
        "LIVE";


    seriesStatusBadgeElement.classList.remove(
        "complete"
    );


    seriesTotalScoreElement.classList.add(
        "hidden"
    );


    seriesActionButtonsElement.classList.remove(
        "hidden"
    );


    manualResultButtonElement.classList.remove(
        "hidden"
    );


    // 프리시즌만 경기 취소 가능
    if (
        currentSeriesType
        === "프리시즌"
    ) {

        seriesCancelButtonElement.classList.remove(
            "hidden"
        );

    } else {

        seriesCancelButtonElement.classList.add(
            "hidden"
        );
    }

}


/* =========================
   MVP 출력
========================= */

function renderMvp(mvp) {

    if (!mvp) {

        seriesMvpElement.classList.add(
            "hidden"
        );

        return;

    }


    seriesMvpElement.innerHTML = `
        <div class="series-mvp-title">
            MATCH MVP
        </div>

        <div class="series-mvp-content">

            <img
                src="${mvp.image_url}"
                alt="${mvp.player_name}"
                class="series-mvp-image"
            >

            <div class="series-mvp-info">

                <strong>
                    ${mvp.player_name}
                </strong>

                <span>
                    ${mvp.fcl_name}
                </span>

                <div class="series-mvp-record">

                    <span>
                        평점 합계
                        ${mvp.rating_total}
                    </span>

                    <span>
                        평균
                        ${mvp.average_rating}
                    </span>

                    <span>
                        ${mvp.goals}골
                    </span>

                    <span>
                        ${mvp.assists}도움
                    </span>

                </div>

            </div>

        </div>
    `;


    seriesMvpElement.classList.remove(
        "hidden"
    );

}

/* =========================
   친선전 취소
========================= */

async function cancelSeries() {

    if (!currentSeriesId) {
        return;
    }


    const confirmed =
        window.confirm(
            "현재 친선전을 취소하시겠습니까?"
        );


    if (!confirmed) {
        return;
    }


    seriesCancelButtonElement.disabled =
        true;

    seriesCancelButtonElement.textContent =
        "취소 중...";


    stopStatusPolling();


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${currentSeriesId}/cancel`,
            {
                method: "POST"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ?? "친선전 취소에 실패했습니다."
            );

        }


        localStorage.removeItem(
            "fclCurrentSeriesId"
        );

        currentSeriesId = null;

        currentTeamA = "";
        currentTeamB = "";


        window.location.href =
            "./schedule.html";


    } catch (error) {

        preseasonMessageElement.textContent =
            error.message;


        seriesCancelButtonElement.disabled =
            false;

        seriesCancelButtonElement.textContent =
            "경기 취소";


        startStatusPolling();

    }

}


function renderManualResultInputs() {

    manualResultSetListElement.innerHTML =
        "";


    for (
        let setNumber = 1;
        setNumber <= currentSeriesBestOf;
        setNumber++
    ) {

        const rowElement =
            document.createElement(
                "div"
            );


        rowElement.classList.add(
            "manual-result-row"
        );


        rowElement.dataset.setNumber =
            String(
                setNumber
            );


        rowElement.innerHTML = `
            <div class="manual-set-name">
                ${setNumber} SET
            </div>

            <input
                type="number"
                class="manual-score-input manual-team-a-score"
                min="0"
                step="1"
            >

            <div class="manual-score-divider">
                :
            </div>

            <input
                type="number"
                class="manual-score-input manual-team-b-score"
                min="0"
                step="1"
            >
        `;


        // =========================
        // 플레이오프 동점 승자 선택
        // =========================

        if (
            currentSeriesType
            === "플레이오프"
        ) {

            const winnerChoiceElement =
                document.createElement(
                    "div"
                );


            winnerChoiceElement.classList.add(
                "manual-winner-choice",
                "hidden"
            );


            winnerChoiceElement.innerHTML = `
                <button
                    type="button"
                    class="manual-winner-button"
                    data-winner-side="team_a"
                >
                    ${currentTeamA} 승
                </button>

                <button
                    type="button"
                    class="manual-winner-button"
                    data-winner-side="team_b"
                >
                    ${currentTeamB} 승
                </button>
            `;


            rowElement.append(
                winnerChoiceElement
            );


            const teamAScoreElement =
                rowElement.querySelector(
                    ".manual-team-a-score"
                );


            const teamBScoreElement =
                rowElement.querySelector(
                    ".manual-team-b-score"
                );


            const winnerButtons =
                winnerChoiceElement.querySelectorAll(
                    ".manual-winner-button"
                );


winnerButtons.forEach(
    buttonElement => {

        buttonElement.addEventListener(
            "click",
            () => {

                rowElement.dataset.winnerSide =
                    buttonElement.dataset.winnerSide;


                winnerButtons.forEach(
                    winnerButtonElement => {

                        const isSelected =
                            winnerButtonElement
                            === buttonElement;


                        const winnerName =
                            (
                                winnerButtonElement.dataset.winnerSide
                                === "team_a"
                            )
                                ? currentTeamA
                                : currentTeamB;


                        winnerButtonElement.classList.toggle(
                            "selected",
                            isSelected
                        );


                        winnerButtonElement.textContent =
                            isSelected
                                ? `✓ ${winnerName} 승`
                                : `${winnerName} 승`;
                    }
                );
            }
        );
    }
);

            const updateWinnerChoice =
                () => {

                    const teamAValue =
                        teamAScoreElement.value;

                    const teamBValue =
                        teamBScoreElement.value;


                    const isDraw =
                        teamAValue !== ""
                        &&
                        teamBValue !== ""
                        &&
                        Number(teamAValue)
                        === Number(teamBValue);


                    if (isDraw) {

                        winnerChoiceElement.classList.remove(
                            "hidden"
                        );

                        return;
                    }


                    winnerChoiceElement.classList.add(
                        "hidden"
                    );


                    delete rowElement.dataset.winnerSide;


winnerButtons.forEach(
    winnerButtonElement => {

        winnerButtonElement.classList.remove(
            "selected"
        );


        const winnerName =
            (
                winnerButtonElement.dataset.winnerSide
                === "team_a"
            )
                ? currentTeamA
                : currentTeamB;


        winnerButtonElement.textContent =
            `${winnerName} 승`;
    }
);
                };


            teamAScoreElement.addEventListener(
                "input",
                updateWinnerChoice
            );


            teamBScoreElement.addEventListener(
                "input",
                updateWinnerChoice
            );
        }


        // 플레이오프 여부와 관계없이
        // 모든 세트 행을 화면에 추가
        manualResultSetListElement.append(
            rowElement
        );
    }
}




/* =========================
   수동 결과 입력창
========================= */

function openManualResultPanel() {

    if (!currentSeriesId) {
        return;
    }


    manualTeamANameElement.textContent =
        currentTeamA;

    manualTeamBNameElement.textContent =
        currentTeamB;

    renderManualResultInputs();


    manualResultMessageElement.textContent =
        "";


    // =========================
    // 자동 감지 진행 화면 숨김
    // =========================

    seriesStatusHeaderElement.classList.add(
        "hidden"
    );

    seriesSetListElement.classList.add(
        "hidden"
    );

    seriesTotalScoreElement.classList.add(
        "hidden"
    );

    seriesMvpElement.classList.add(
        "hidden"
    );

    seriesActionButtonsElement.classList.add(
        "hidden"
    );

    // =========================
    // 프리시즌만 경기 취소 가능
    // =========================

    if (
        currentSeriesType
        === "프리시즌"
    ) {

        seriesCancelButtonElement.classList.remove(
            "hidden"
        );

    } else {

        seriesCancelButtonElement.classList.add(
            "hidden"
        );
    }


    // =========================
    // 수동 결과 입력만 표시
    // =========================

    manualResultPanelElement.classList.remove(
        "hidden"
    );
}


function closeManualResultPanel() {

    window.location.href =
        "./schedule.html";
}


/* =========================
   수동 결과 완료
========================= */

async function completeManualResult() {

    if (!currentSeriesId) {
        return;
    }


    const rowElements = [
        ...manualResultSetListElement.querySelectorAll(
            ".manual-result-row"
        )
    ];


    const requestBody = {};

    let gapFound = false;

    let playedSetCount = 0;


    for (
        const rowElement
        of rowElements
    ) {

        const setNumber =
            Number(
                rowElement.dataset.setNumber
            );


        const teamAScoreElement =
            rowElement.querySelector(
                ".manual-team-a-score"
            );


        const teamBScoreElement =
            rowElement.querySelector(
                ".manual-team-b-score"
            );


        const teamAValue =
            teamAScoreElement.value.trim();

        const teamBValue =
            teamBScoreElement.value.trim();


        /*
         * 양쪽 모두 비어있으면
         * 이후 세트는 아직 진행 안 한 것으로 처리
         */
        if (
            teamAValue === ""
            &&
            teamBValue === ""
        ) {

            gapFound = true;
            continue;
        }


        /*
         * 한쪽만 입력
         */
        if (
            teamAValue === ""
            ||
            teamBValue === ""
        ) {

            manualResultMessageElement.textContent =
                `${setNumber}세트 양쪽 점수를 모두 입력해주세요.`;

            return;
        }


        /*
         * 중간 세트를 비우고
         * 다음 세트가 입력된 경우
         */
        if (gapFound) {

            manualResultMessageElement.textContent =
                "중간 세트를 비워둔 채 다음 세트를 입력할 수 없습니다.";

            return;
        }


        const teamAScore =
            Number(
                teamAValue
            );

        const teamBScore =
            Number(
                teamBValue
            );


        if (
            !Number.isInteger(
                teamAScore
            )
            ||
            !Number.isInteger(
                teamBScore
            )
            ||
            teamAScore < 0
            ||
            teamBScore < 0
        ) {

            manualResultMessageElement.textContent =
                "점수는 0 이상의 정수만 입력해주세요.";

            return;
        }


        requestBody[
            `set${setNumber}_team_a`
        ] = teamAScore;


        requestBody[
            `set${setNumber}_team_b`
        ] = teamBScore;


        /*
         * 플레이오프 동점 세트
         * 실제 승자 선택
         */
        if (
            currentSeriesType
            === "플레이오프"
            &&
            teamAScore === teamBScore
        ) {

            const winnerSide =
                rowElement.dataset.winnerSide
                ?? "";


            if (!winnerSide) {

                manualResultMessageElement.textContent =
                    `${setNumber}세트의 실제 승자를 선택해주세요.`;

                return;
            }


            requestBody[
                `set${setNumber}_winner_side`
            ] = winnerSide;
        }


        playedSetCount++;
    }


    /*
     * 일반 SERIES는 정확히 3세트
     */
    if (
        currentSeriesType
        !== "플레이오프"
        &&
        playedSetCount !== 3
    ) {

        manualResultMessageElement.textContent =
            "3세트 점수를 모두 입력해주세요.";

        return;
    }


    /*
     * 플레이오프는
     * 최소한 한 세트 이상 입력 필요
     *
     * 최종 선승 여부는
     * 백엔드가 다시 검증
     */
    if (
        currentSeriesType
        === "플레이오프"
        &&
        playedSetCount === 0
    ) {

        manualResultMessageElement.textContent =
            "경기 결과를 입력해주세요.";

        return;
    }


    const seriesLabel =
        (
            currentSeriesType
            === "플레이오프"
        )
            ? (
                currentPlayoffStage
                ?? "플레이오프"
            )
            : currentSeriesType;


    const confirmed =
        window.confirm(
            `입력한 결과로 ${seriesLabel} 경기를 완료하시겠습니까?`
        );


    if (!confirmed) {
        return;
    }


    manualCompleteButtonElement.disabled =
        true;

    manualCompleteButtonElement.textContent =
        "저장 중...";


    stopStatusPolling();


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/fconline/series/${currentSeriesId}/manual-complete`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            requestBody
                        )
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "수동 결과 저장에 실패했습니다."
            );
        }


        localStorage.removeItem(
            "fclCurrentSeriesId"
        );


        currentSeriesId = null;

        currentTeamA = "";
        currentTeamB = "";

        currentSeriesType = "";

        currentPlayoffStage = null;
        currentSeriesBestOf = 3;
        currentWinsRequired = null;


        window.location.href =
            "./results.html";


    } catch (error) {

        manualResultMessageElement.textContent =
            error.message;


        manualCompleteButtonElement.disabled =
            false;

        manualCompleteButtonElement.textContent =
            "결과 완료";


        startStatusPolling();
    }
}

/* =========================
   STATUS POLLING
========================= */

function startStatusPolling() {

    stopStatusPolling();


    loadSeriesStatus();

}


function stopStatusPolling() {

    if (!statusTimer) {
        return;
    }


    clearInterval(
        statusTimer
    );


    statusTimer = null;

}


/* =========================
   새로고침 복구
========================= */

async function restoreSeries() {

    const urlParams =
        new URLSearchParams(
            window.location.search
        );


    const isResultMode =
        urlParams.get("mode")
        === "result";


    // =========================================
    // 친선전 예약 메뉴로 직접 들어온 경우
    // 예약 화면 그대로 출력
    // =========================================

    if (!isResultMode) {
        return;
    }


    const savedSeriesId =
        localStorage.getItem(
            "fclCurrentSeriesId"
        );


    if (!savedSeriesId) {

        window.location.href =
            "./schedule.html";

        return;
    }


    // =========================================
    // 경기 일정에서
    // 경기 시작 / 경기 결과 입력으로 들어온 경우
    // =========================================

    currentSeriesId =
        Number(
            savedSeriesId
        );


    preseasonStartCardElement.classList.add(
        "hidden"
    );


    seriesStatusCardElement.classList.remove(
        "hidden"
    );


    seriesStartButtonElement.disabled =
        true;


    seriesStartButtonElement.textContent =
        "SERIES 진행 중";


    // SERIES 데이터 조회
    await loadSeriesStatus();


    if (currentSeriesId) {

        openManualResultPanel();
    }
}

function setTodayMatchDate() {

    const formatter =
        new Intl.DateTimeFormat(
            "en-CA",
            {
                timeZone: "Asia/Seoul",

                year: "numeric",
                month: "2-digit",
                day: "2-digit",
            }
        );


    const dateParts =
        Object.fromEntries(
            formatter
                .formatToParts(
                    new Date()
                )
                .filter(
                    part =>
                        part.type !== "literal"
                )
                .map(
                    part => [
                        part.type,
                        part.value,
                    ]
                )
        );


    preseasonDateInputElement.value =
        `${dateParts.year}`
        + `-${dateParts.month}`
        + `-${dateParts.day}`;
}

/* =========================
   이벤트
========================= */

seriesStartButtonElement.addEventListener(
    "click",
    startSeries
);

historyImportButtonElement.addEventListener(
    "click",
    importHistorySeries
);

manualResultButtonElement.addEventListener(
    "click",
    openManualResultPanel
);


manualBackButtonElement.addEventListener(
    "click",
    closeManualResultPanel
);


manualCompleteButtonElement.addEventListener(
    "click",
    completeManualResult
);


seriesCancelButtonElement.addEventListener(
    "click",
    cancelSeries
);

historyRuleButtonElement.addEventListener(
    "click",
    () => {

        historyRulePanelElement.classList.toggle(
            "hidden"
        );


        const isHidden =
            historyRulePanelElement.classList.contains(
                "hidden"
            );


        historyRuleButtonElement.textContent =
            isHidden
                ? "등록 규칙"
                : "규칙 닫기";

    }
);

function toggleReservationRule() {

    const isOpen =
        !reservationRulePanelElement.classList.contains(
            "hidden"
        );


    if (isOpen) {

        reservationRulePanelElement.classList.add(
            "hidden"
        );

        reservationRuleButtonElement.textContent =
            "예약 규칙";

    } else {

        reservationRulePanelElement.classList.remove(
            "hidden"
        );

        reservationRuleButtonElement.textContent =
            "규칙 닫기";
    }
}


reservationRuleButtonElement.addEventListener(
    "click",
    toggleReservationRule
);

document.addEventListener(
    "click",
    (event) => {

        const clickedButton =
            reservationRuleButtonElement.contains(
                event.target
            );

        const clickedPanel =
            reservationRulePanelElement.contains(
                event.target
            );


        if (
            !clickedButton
            &&
            !clickedPanel
        ) {

            reservationRulePanelElement.classList.add(
                "hidden"
            );

            reservationRuleButtonElement.textContent =
                "예약 규칙";
        }

    }
);

preseasonTodayButtonElement.addEventListener(
    "click",
    setTodayMatchDate
);



/* =========================
   초기 실행
========================= */

loadParticipants();

restoreSeries();