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

        playoffCardElement.innerHTML = `
            <div class="match-date">
                ${match.date}
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

    matches.forEach((match) => {
        const scheduleCardElement = document.createElement("div");

        scheduleCardElement.classList.add("schedule-card");

        scheduleCardElement.innerHTML = `
            <div class="match-date">
                ${match.date}
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

        scheduleListElement.appendChild(scheduleCardElement);
    });
}


loadSchedule();
loadPlayoffSchedule();