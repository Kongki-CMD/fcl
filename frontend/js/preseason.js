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


const manualSet1TeamAElement =
    document.querySelector(
        "#manual-set1-team-a"
    );


const manualSet1TeamBElement =
    document.querySelector(
        "#manual-set1-team-b"
    );


const manualSet2TeamAElement =
    document.querySelector(
        "#manual-set2-team-a"
    );


const manualSet2TeamBElement =
    document.querySelector(
        "#manual-set2-team-b"
    );


const manualSet3TeamAElement =
    document.querySelector(
        "#manual-set3-team-a"
    );


const manualSet3TeamBElement =
    document.querySelector(
        "#manual-set3-team-b"
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


let currentSeriesId = null;

let currentTeamA = "";
let currentTeamB = "";

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


/* =========================
   STATUS 조회
========================= */

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


        renderSeriesStatus(
            data
        );


        if (
            data.series.status
            === "completed"
        ) {

            stopStatusPolling();

        }


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


    seriesStatusCardElement.classList.remove(
        "hidden"
    );

    currentTeamA =
        series.team_a;

    currentTeamB =
        series.team_b;

    seriesTitleElement.textContent =
        `${series.team_a} VS ${series.team_b}`;


    seriesProgressElement.textContent =
        `${series.set_count} / 3`;


    /* =========================
       세트 출력
    ========================= */

    seriesSetListElement.innerHTML =
        "";


    for (
        let setNumber = 1;
        setNumber <= 3;
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
       경기 완료
    ========================= */

    if (
        series.status === "completed"
    ) {

        seriesActionButtonsElement.classList.add(
            "hidden"
        );

        manualResultPanelElement.classList.add(
            "hidden"
        );

        seriesStatusBadgeElement.textContent =
            "COMPLETE";

        seriesStatusBadgeElement.classList.add(
            "complete"
        );


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

    } else {

        seriesStatusBadgeElement.textContent =
            "LIVE";

        seriesStatusBadgeElement.classList.remove(
            "complete"
        );

        seriesActionButtonsElement.classList.remove(
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


        preseasonMessageElement.textContent =
            "친선전이 취소되었습니다.";


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


    manualResultMessageElement.textContent =
        "";


    manualResultPanelElement.classList.remove(
        "hidden"
    );


    seriesActionButtonsElement.classList.add(
        "hidden"
    );

}


function closeManualResultPanel() {

    manualResultPanelElement.classList.add(
        "hidden"
    );


    seriesActionButtonsElement.classList.remove(
        "hidden"
    );

}


/* =========================
   수동 결과 완료
========================= */

async function completeManualResult() {

    if (!currentSeriesId) {
        return;
    }


    const scoreElements = [
        manualSet1TeamAElement,
        manualSet1TeamBElement,

        manualSet2TeamAElement,
        manualSet2TeamBElement,

        manualSet3TeamAElement,
        manualSet3TeamBElement,
    ];


    const hasEmptyScore =
        scoreElements.some(
            element =>
                element.value === ""
        );


    if (hasEmptyScore) {

        manualResultMessageElement.textContent =
            "3세트 점수를 모두 입력해주세요.";

        return;

    }


    const scores =
        scoreElements.map(
            element =>
                Number(
                    element.value
                )
        );


    const hasInvalidScore =
        scores.some(
            score =>
                !Number.isInteger(score)
                ||
                score < 0
        );


    if (hasInvalidScore) {

        manualResultMessageElement.textContent =
            "점수는 0 이상의 정수만 입력해주세요.";

        return;

    }


    const confirmed =
        window.confirm(
            "입력한 결과로 친선전을 완료하시겠습니까?"
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

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${currentSeriesId}/manual-complete`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    set1_team_a:
                        scores[0],

                    set1_team_b:
                        scores[1],

                    set2_team_a:
                        scores[2],

                    set2_team_b:
                        scores[3],

                    set3_team_a:
                        scores[4],

                    set3_team_b:
                        scores[5]
                })
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


    statusTimer = setInterval(
        loadSeriesStatus,
        10000
    );

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

function restoreSeries() {

    const savedSeriesId =
        localStorage.getItem(
            "fclCurrentSeriesId"
        );


    if (!savedSeriesId) {
        return;
    }


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


    startStatusPolling();

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


/* =========================
   초기 실행
========================= */

loadParticipants();

restoreSeries();