import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const scheduleListElement = document.querySelector(".match-list");

const playoffMatchListElement = document.querySelector(
    ".playoff-match-list"
);

const scheduleViewButtonElement = document.querySelector(
    "#schedule-view-button"
);

const scheduleDescriptionElement = document.querySelector(
    ".schedule-description"
);


let isPlayoffView = false;


scheduleViewButtonElement.addEventListener("click", () => {
    isPlayoffView = !isPlayoffView;

    if (isPlayoffView) {
        scheduleListElement.style.display = "none";
        playoffMatchListElement.style.display = "block";

        scheduleDescriptionElement.textContent =
            "FC Online Champions League 플레이오프 일정";

        scheduleViewButtonElement.textContent =
            "전체 경기 일정";
    } else {
        scheduleListElement.style.display = "block";
        playoffMatchListElement.style.display = "none";

        scheduleDescriptionElement.textContent =
            "FC Online Champions League 전체 경기 일정";

        scheduleViewButtonElement.textContent =
            "플레이오프 일정";
    }
});

scheduleListElement.addEventListener(
    "click",
    (event) => {

        const regularViewButtonElement =
            event.target.closest(
                ".regular-series-view-button"
            );


        if (regularViewButtonElement) {

            openPreseasonSeries(
                regularViewButtonElement
            );

            return;
        }

        const regularButtonElement =
            event.target.closest(
                ".regular-series-start-button"
            );


        if (regularButtonElement) {

            startRegularSeries(
                regularButtonElement
            );

            return;
        }


        const preseasonStartButtonElement =
            event.target.closest(
                ".preseason-series-start-button"
            );


        if (preseasonStartButtonElement) {

            startPreseasonSeries(
                preseasonStartButtonElement
            );

            return;
        }


        const preseasonViewButtonElement =
            event.target.closest(
                ".preseason-series-view-button"
            );


        if (preseasonViewButtonElement) {

            openPreseasonSeries(
                preseasonViewButtonElement
            );
        }

    }
);


async function loadSchedule() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/matches`
        );

        if (!response.ok) {
            throw new Error("경기 일정을 불러오지 못했습니다.");
        }

        const matchData = await response.json();

        renderSchedule(matchData);
    } catch (error) {
        console.error(error);

        scheduleListElement.innerHTML = `
            <p>경기 일정을 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}

async function loadPlayoffSchedule() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/playoffs`
        );

        if (!response.ok) {
            throw new Error(
                "플레이오프 일정을 불러오지 못했습니다."
            );
        }

        const playoffData = await response.json();

        renderPlayoffSchedule(playoffData);
    } catch (error) {
        console.error(error);

        playoffMatchListElement.innerHTML = `
            <p>
                플레이오프 일정을 불러오는 중
                오류가 발생했습니다.
            </p>
        `;
    }
}

// =========================================
// 정규리그 SERIES START
// DB에 예약된 SERIES 활성화
// =========================================

async function startRegularSeries(
    buttonElement
) {

    const seriesId =
        Number(
            buttonElement.dataset.seriesId
        );


    if (!seriesId) {
        return;
    }


    const originalText =
        buttonElement.textContent;


    buttonElement.disabled =
        true;

    buttonElement.textContent =
        "STARTING...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/activate`,
            {
                method: "POST"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "SERIES 시작에 실패했습니다."
            );
        }


        localStorage.setItem(
            "fclCurrentSeriesId",
            data.series_id
        );


        window.location.href =
            "./preseason.html?mode=result";


    } catch (error) {

        alert(
            error.message
        );


        buttonElement.disabled =
            false;

        buttonElement.textContent =
            originalText;
    }
}

// =========================================
// PRE-SEASON SERIES START
// 예약 친선전 실제 경기 시작
// =========================================

async function startPreseasonSeries(
    buttonElement
) {

    const seriesId =
        Number(
            buttonElement.dataset.seriesId
        );


    if (!seriesId) {
        return;
    }


    const confirmed =
        window.confirm(
            "친선전 경기를 시작하시겠습니까?"
        );


    if (!confirmed) {
        return;
    }


    const originalText =
        buttonElement.textContent;


    buttonElement.disabled =
        true;

    buttonElement.textContent =
        "시작 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/activate`,
            {
                method: "POST"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "친선전 시작에 실패했습니다."
            );
        }


        localStorage.setItem(
            "fclCurrentSeriesId",
            data.series_id
        );


        window.location.href =
            "./preseason.html?mode=result";


    } catch (error) {

        alert(
            error.message
        );


        buttonElement.disabled =
            false;

        buttonElement.textContent =
            originalText;
    }
}


// =========================================
// 진행 중 PRE-SEASON 보기
// =========================================

function openPreseasonSeries(
    buttonElement
) {

    const seriesId =
        Number(
            buttonElement.dataset.seriesId
        );


    if (!seriesId) {
        return;
    }


    localStorage.setItem(
        "fclCurrentSeriesId",
        seriesId
    );


    window.location.href =
        "./preseason.html?mode=result";
}

function renderPlayoffSchedule(matches) {
    playoffMatchListElement.innerHTML = "";

    if (matches.length === 0) {
        playoffMatchListElement.innerHTML = `
            <p>등록된 플레이오프 일정이 없습니다.</p>
        `;

        return;
    }

    matches.forEach((match) => {
        const playoffCardElement =
            document.createElement("div");

        playoffCardElement.classList.add(
            "schedule-card",
            "playoff-schedule-card"
        );

        let playoffFormat = "";

        if (
            match.stage === "준플레이오프" ||
            match.stage === "플레이오프"
        ) {
            playoffFormat = "5판 3선승";
        } else if (match.stage === "결승 시리즈") {
            playoffFormat = "7판 4선승";
        }

        playoffCardElement.innerHTML = `
            <div class="match-date">
                ${match.date}

                    <span class="playoff-divider">
                        /
                    </span>

                <span class="playoff-format">
                    ${playoffFormat}
                </span>
            </div>

            <div class="playoff-stage">
                ${match.stage}
            </div>

            <div class="match-teams">

                <div class="team-box">
                    <span class="team-name">
                        ${match.team_a}
                    </span>
                </div>

                <span class="versus">
                    VS
                </span>

                <div class="team-box">
                    <span class="team-name">
                        ${match.team_b}
                    </span>
                </div>

            </div>
        `;

        playoffMatchListElement.appendChild(
            playoffCardElement
        );
    });
}


function renderSchedule(matches) {
    scheduleListElement.innerHTML = "";

    if (matches.length === 0) {
        scheduleListElement.innerHTML = `
            <p>등록된 경기 일정이 없습니다.</p>
        `;

        return;
    }


    // =========================================
    // 오늘 날짜 YYYY-MM-DD 만들기
    // =========================================

    const today = new Date();

    const todayString = [
        today.getFullYear(),
        String(
            today.getMonth() + 1
        ).padStart(2, "0"),
        String(
            today.getDate()
        ).padStart(2, "0"),
    ].join("-");


    // =========================================
    // 일정 정렬
    //
    // 1. 오늘 / 미래 경기
    // 2. 지난 경기
    //
    // 각 그룹 안에서는 날짜순
    // =========================================

    const sortedMatches =
        [...matches].sort(
            (matchA, matchB) => {

                const isPastMatchA =
                    matchA.date < todayString;

                const isPastMatchB =
                    matchB.date < todayString;


                // =====================================
                // 미래/오늘 경기는 위
                // 지난 경기는 아래
                // =====================================

                if (
                    isPastMatchA
                    !== isPastMatchB
                ) {

                    return isPastMatchA
                        ? 1
                        : -1;
                }


                // =====================================
                // 오늘 / 미래 경기
                // 가까운 날짜부터
                // =====================================

                if (!isPastMatchA) {

                    return (
                        matchA.date.localeCompare(
                            matchB.date
                        )
                    );
                }


                // =====================================
                // 지난 경기
                // 최근 경기부터
                // =====================================

                return (
                    matchB.date.localeCompare(
                        matchB.date
                    )
                );
            }
        );


    // =========================================
    // 카드 출력
    // =========================================

    sortedMatches.forEach((match) => {

        const scheduleCardElement =
            document.createElement("div");

        scheduleCardElement.classList.add(
            "schedule-card"
        );


        // =====================================
        // 프리시즌 / 정규리그 표시
        // =====================================

        let matchLabel = "";
        let matchStatusLabel = "";


        if (match.match_type === "프리시즌") {

            matchLabel = `
                <span class="match-preseason">
                    PRE-SEASON
                </span>
            `;

        } else {

            matchLabel = `
                <span class="match-round">
                    ROUND ${match.round}
                </span>
            `;
        }

                // =====================================
        // PRE-SEASON 상태
        // =====================================

        const isDatabaseSeries =
            match.series_id
                !== null;


        if (isDatabaseSeries) {

            if (
                match.status
                === "scheduled"
            ) {

                matchStatusLabel = `
                    <span class="match-status scheduled">
                        예약됨
                    </span>
                `;

            } else if (
                match.status
                === "active"
            ) {

                matchStatusLabel = `
                    <span class="match-status active">
                        진행 중
                    </span>
                `;

            } else if (
                match.status
                === "completed"
            ) {

                matchStatusLabel = `
                    <span class="match-status completed">
                        완료
                    </span>
                `;
            }
        }


        // =====================================
        // 지난 경기 여부
        // =====================================

        const isPastMatch =
            match.date < todayString;

        const isTodayMatch =
            match.date === todayString;


        const isRegularMatch =
            match.match_type
            === "정규리그";


        const isPreseasonMatch =
            match.match_type
            === "프리시즌";


        let seriesStartHtml = "";


        // =====================================
        // 정규리그
        // 예약됨 + 경기 당일
        // =====================================

        if (
            isRegularMatch
            &&
            match.series_id
                !== null
            &&
            match.status
                === "scheduled"
            &&
            isTodayMatch
        ) {

            seriesStartHtml = `
                <div class="schedule-series-control">

                    <button
                        type="button"
                        class="regular-series-start-button"

                        data-series-id="${match.series_id}"
                    >
                        SERIES START
                    </button>

                </div>
            `;
        }

        // =====================================
        // 정규리그
        // 이미 진행 중
        // =====================================

        if (
            isRegularMatch
            &&
            match.series_id
                !== null
            &&
            match.status
                === "active"
        ) {

            seriesStartHtml = `
                <div class="schedule-series-control">

                    <button
                        type="button"
                        class="regular-series-view-button"

                        data-series-id="${match.series_id}"
                    >
                        경기 결과 입력
                    </button>

                </div>
            `;
        }


        // =====================================
        // PRE-SEASON
        // 예약됨 + 경기 당일
        // =====================================

        if (
            isPreseasonMatch
            &&
            match.series_id
            !== null
            &&
            match.status
            === "scheduled"
            &&
            isTodayMatch
        ) {

            seriesStartHtml = `
                <div class="schedule-series-control">

                    <button
                        type="button"
                        class="preseason-series-start-button"

                        data-series-id="${match.series_id}"
                    >
                        경기 시작
                    </button>

                </div>
            `;
        }


        // =====================================
        // PRE-SEASON
        // 이미 진행 중
        // =====================================

        if (
            isPreseasonMatch
            &&
            match.series_id
            !== null
            &&
            match.status
            === "active"
        ) {

            seriesStartHtml = `
                <div class="schedule-series-control">

                    <button
                        type="button"
                        class="preseason-series-view-button"

                        data-series-id="${match.series_id}"
                    >
                        경기 결과 입력
                    </button>

                </div>
            `;
        }


        if (isPastMatch) {
            scheduleCardElement.classList.add(
                "past-match"
            );
        }


        // =====================================
        // HTML
        // =====================================

        scheduleCardElement.innerHTML = `

            <div class="match-date">

                ${match.date}

                ${matchLabel}

                ${matchStatusLabel}

            </div>

            <div class="match-teams">

                <div class="team-box">

                    <img
                        src="${getTeamImagePath(match.team_a)}"
                        alt="${match.team_a} 로고"
                        class="team-image"
                    >

                    <span class="team-name">
                        ${match.team_a}
                    </span>

                </div>


                <span class="versus">
                    VS
                </span>


                <div class="team-box">

                    <img
                        src="${getTeamImagePath(match.team_b)}"
                        alt="${match.team_b} 로고"
                        class="team-image"
                    >

                    <span class="team-name">
                        ${match.team_b}
                    </span>

                </div>

            </div>


            ${seriesStartHtml}
        `;


        scheduleListElement.appendChild(
            scheduleCardElement
        );
    });
}


loadSchedule();
loadPlayoffSchedule();