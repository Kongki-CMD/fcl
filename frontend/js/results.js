import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const resultsListElement = document.querySelector(".results-list");


async function loadResults() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/results`
        );

        if (!response.ok) {
            throw new Error("경기 결과를 불러오지 못했습니다.");
        }

        const resultData = await response.json();

        renderResults(resultData);
    } catch (error) {
        console.error(error);

        resultsListElement.innerHTML = `
            <p>경기 결과를 불러오는 중 오류가 발생했습니다.</p>
        `;
    }
}


function renderResults(results) {
    resultsListElement.innerHTML = "";

    if (results.length === 0) {
        resultsListElement.innerHTML = `
            <p>등록된 경기 결과가 없습니다.</p>
        `;

        return;
    }

    results.forEach((result) => {
        const resultCardElement = document.createElement("div");

        resultCardElement.classList.add("result-card");

        resultCardElement.innerHTML = `
            <div class="result-date">
                ${result.date}

                <span class="match-round">
                    ${result.round}라운드
                </span>
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

            <div class="set-score-list">

${result.sets.map((setResult) => {

    let teamAResult = "";
    let teamBResult = "";

    if (setResult.team_a_score > setResult.team_b_score) {
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
        } else if (setResult.team_a_score < setResult.team_b_score) {
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

}).join("")}

            </div>
                `;

        resultsListElement.appendChild(resultCardElement);
    });
}


loadResults();