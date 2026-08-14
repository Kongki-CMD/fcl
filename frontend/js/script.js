import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const todayMatchListElement = document.querySelector(".match-list");
const recentResultListElement = document.querySelector(".result-list");


async function loadTodayMatches() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/matches/today`
        );

        if (!response.ok) {
            throw new Error("오늘 경기 정보를 불러오지 못했습니다.");
        }

        const matchData = await response.json();

        renderTodayMatches(matchData);
    } catch (error) {
        console.error(error);

        todayMatchListElement.innerHTML = `
            <p>경기 정보를 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}


function renderTodayMatches(matches) {
    todayMatchListElement.innerHTML = "";

    if (matches.length === 0) {
        todayMatchListElement.innerHTML = `
            <p>오늘 예정된 경기가 없습니다.</p>
        `;

        return;
    }

    matches.forEach((match) => {
        const todayMatchCardElement = document.createElement("div");

        todayMatchCardElement.classList.add("today-match-card");

        todayMatchCardElement.innerHTML = `
            <div class="team-box">
                <img
                    src="${getTeamImagePath(match.team_a)}"
                    alt="${match.team_a} 로고"
                    class="team-image"
                >

                <span class="today-team">
                    ${match.team_a}
                </span>
            </div>

            <span class="today-versus">
                VS
            </span>

            <div class="team-box">
                <img
                    src="${getTeamImagePath(match.team_b)}"
                    alt="${match.team_b} 로고"
                    class="team-image"
                >

                <span class="today-team">
                    ${match.team_b}
                </span>
            </div>
        `;

        todayMatchListElement.appendChild(todayMatchCardElement);
    });
}


async function loadRecentResults() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/results`
        );

        if (!response.ok) {
            throw new Error("이전 경기 결과를 불러오지 못했습니다.");
        }

        const resultData = await response.json();

        renderRecentResults(resultData);
    } catch (error) {
        console.error(error);

        recentResultListElement.innerHTML = `
            <p>경기 결과를 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}


function renderRecentResults(results) {
    recentResultListElement.innerHTML = "";

    if (results.length === 0) {
        recentResultListElement.innerHTML = `
            <p>이전 경기 결과가 없습니다.</p>
        `;

        return;
    }

    const latestDate = results.reduce(
        (latestDateValue, result) => {
            if (result.date > latestDateValue) {
                return result.date;
            }

            return latestDateValue;
        },
        results[0].date
    );

    const latestResults = results.filter(
        (result) => result.date === latestDate
    );

    latestResults.forEach((result) => {
        const recentResultCardElement = document.createElement("div");

        recentResultCardElement.classList.add("result-card");

        recentResultCardElement.innerHTML = `
            <div class="result-date">
                ${result.date}
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
                    <span>${result.team_a_score}</span>

                    <span class="score-divider">
                        :
                    </span>

                    <span>${result.team_b_score}</span>
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
        `;

        recentResultListElement.appendChild(recentResultCardElement);
    });
}

const teamRankingListElement = document.querySelector(
    ".team-ranking-list"
);


async function loadTeamRanking() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/standings`
        );

        if (!response.ok) {
            throw new Error("팀 순위를 불러오지 못했습니다.");
        }

        const standingsData = await response.json();

        renderTeamRanking(standingsData);
    } catch (error) {
        console.error(error);

        teamRankingListElement.innerHTML = `
            <p>팀 순위를 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}


function renderTeamRanking(standings) {
    teamRankingListElement.innerHTML = "";

    standings.forEach((team) => {
        const rankingRowElement = document.createElement("div");

        rankingRowElement.classList.add("dashboard-ranking-row");

        rankingRowElement.innerHTML = `
            <span class="dashboard-rank">
                ${team.rank}
            </span>

            <div class="dashboard-team">
                <img
                    src="${getTeamImagePath(team.name)}"
                    alt=""
                    class="dashboard-team-image"
                >

                <span class="dashboard-team-name">
                    ${team.name}
                </span>
            </div>

            <span class="dashboard-points">
                ${team.points}
            </span>
        `;

        teamRankingListElement.appendChild(
            rankingRowElement
        );
    });
}

loadTeamRanking();
loadTodayMatches();
loadRecentResults();