import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const scheduleListElement = document.querySelector(".schedule-list");


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