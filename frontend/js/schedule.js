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

    const sortedMatches = [...matches].sort(
        (matchA, matchB) => {

            const matchAIsPast =
                matchA.date < todayString;

            const matchBIsPast =
                matchB.date < todayString;


            // A만 지난 경기
            // → A를 아래로
            if (
                matchAIsPast &&
                !matchBIsPast
            ) {
                return 1;
            }


            // B만 지난 경기
            // → B를 아래로
            if (
                !matchAIsPast &&
                matchBIsPast
            ) {
                return -1;
            }


            // 둘 다 미래거나
            // 둘 다 과거면 날짜순
            return matchA.date.localeCompare(
                matchB.date
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
        // 지난 경기 여부
        // =====================================

        const isPastMatch =
            match.date < todayString;


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
        `;


        scheduleListElement.appendChild(
            scheduleCardElement
        );
    });
}


loadSchedule();
loadPlayoffSchedule();