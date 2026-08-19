import {
    apiBaseUrl,
    getTeamImagePath,
} from "./config.js";


const todayMatchListElement =
    document.querySelector(".match-list");

const recentResultListElement =
    document.querySelector(".result-list");

const teamRankingListElement =
    document.querySelector(".team-ranking-list");


// ======================================================
// 오늘의 경기
// ======================================================

async function loadTodayMatches() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/matches/today`
        );

        if (!response.ok) {
            throw new Error(
                "오늘 경기 정보를 불러오지 못했습니다."
            );
        }

        const matchData = await response.json();

        renderTodayMatches(matchData);

    } catch (error) {
        console.error(error);

        todayMatchListElement.innerHTML = `
            <p>
                경기 정보를 불러오는 중 오류가 발생했습니다.
            </p>
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

        const seriesStatus =
            match.series_status
            ?? match.status;


        let seriesControlHtml = "";


        if (
            seriesStatus === "completed"
        ) {

            seriesControlHtml = `
                <div class="today-series-control">
                    <span class="today-series-completed">
                        경기 완료
                    </span>
                </div>
            `;

        } else if (
            seriesStatus === "active"
        ) {

            seriesControlHtml = `
                <div class="today-series-control">

                    <button
                        type="button"
                        class="today-series-button"
                        data-series-action="view"
                        data-series-id="${match.series_id}"
                    >
                        경기 보기
                    </button>

                </div>
            `;

        } else if (
            seriesStatus === "scheduled"
        ) {

            seriesControlHtml = `
                <div class="today-series-control">

                    <button
                        type="button"
                        class="today-series-button"
                        data-series-action="start"
                        data-series-id="${match.series_id}"
                    >
                        경기 시작
                    </button>

                </div>
            `;
        }

        const todayMatchCardElement =
            document.createElement("div");

        todayMatchCardElement.classList.add(
            "today-match-card"
        );


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

            ${seriesControlHtml}

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


        todayMatchListElement.appendChild(
            todayMatchCardElement
        );
    });
}

// ======================================================
// 오늘 경기 SERIES 버튼
// ======================================================

todayMatchListElement.addEventListener(
    "click",
    async (event) => {

        const buttonElement =
            event.target.closest(
                "[data-series-action]"
            );


        if (!buttonElement) {
            return;
        }


        const seriesId =
            Number(
                buttonElement.dataset.seriesId
            );


        const action =
            buttonElement.dataset.seriesAction;


        // ================================
        // 진행 중 경기 보기
        // ================================

        if (action === "view") {

            localStorage.setItem(
                "fclCurrentSeriesId",
                seriesId
            );


            window.location.href =
                "./preseason.html";


            return;
        }


        // ================================
        // 예약된 경기 시작
        // ================================

        if (action === "start") {

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
                        "경기 시작에 실패했습니다."
                    );
                }


                localStorage.setItem(
                    "fclCurrentSeriesId",
                    seriesId
                );


                window.location.href =
                    "./preseason.html";


            } catch (error) {

                console.error(
                    error
                );


                alert(
                    error.message
                );


                buttonElement.disabled =
                    false;


                buttonElement.textContent =
                    originalText;
            }
        }
    }
);


// ======================================================
// 이전 경기 결과
// ======================================================

async function loadRecentResults() {

    try {

        // =====================================
        // 기존 Excel 경기 결과
        // =====================================

        const excelResponse = await fetch(
            `${apiBaseUrl}/api/results`
        );


        if (!excelResponse.ok) {

            throw new Error(
                "이전 경기 결과를 불러오지 못했습니다."
            );
        }


        const excelResults =
            await excelResponse.json();


        // =====================================
        // Neon DB 완료 SERIES 결과
        // 자동 완료 / 수동 완료 / 과거 경기 등록
        // =====================================

        let databaseResults = [];


        try {

            const databaseResponse =
                await fetch(
                    `${apiBaseUrl}/api/fconline/series/completed-results`
                );


            if (databaseResponse.ok) {

                databaseResults =
                    await databaseResponse.json();

            } else {

                console.error(
                    "DB 경기 결과를 불러오지 못했습니다."
                );
            }


        } catch (databaseError) {

            console.error(
                "DB 경기 결과 조회 오류",
                databaseError
            );
        }


        // =====================================
        // 중복 제거
        //
        // 같은 날짜
        // 같은 경기 종류
        // 같은 두 참가자
        //
        // DB 데이터가 있으면 DB 우선
        // =====================================

        const resultMap =
            new Map();


        function makeResultKey(result) {

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


        // Excel 먼저
        excelResults.forEach(
            (result) => {

                resultMap.set(
                    makeResultKey(result),
                    result
                );

            }
        );


        // DB 나중
        // → 같은 경기면 DB 데이터가 덮어씀
        databaseResults.forEach(
            (result) => {

                resultMap.set(
                    makeResultKey(result),
                    result
                );

            }
        );


        const mergedResults =
            Array.from(
                resultMap.values()
            );


        renderRecentResults(
            mergedResults
        );


    } catch (error) {

        console.error(error);


        recentResultListElement.innerHTML = `
            <p>
                경기 결과를 불러오는 중 오류가 발생했습니다.
            </p>
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


    // 가장 최근 경기 날짜 찾기
    const latestDate = results.reduce(
        (latestDateValue, result) => {

            if (result.date > latestDateValue) {
                return result.date;
            }

            return latestDateValue;
        },
        results[0].date
    );


    // 가장 최근 날짜에 열린 경기만 표시
    const latestResults = results.filter(
        (result) => result.date === latestDate
    );


    latestResults.forEach((result) => {

        const recentResultCardElement =
            document.createElement("div");

        recentResultCardElement.classList.add(
            "result-card"
        );


        // 프리시즌 / 정규리그 표시
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


        // 세트별 결과 HTML 생성
        const setScoreHtml = (result.sets ?? [])
            .map((setResult) => {

                let teamAResult = "";
                let teamBResult = "";


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


        recentResultCardElement.innerHTML = `

            <div class="result-date">

                ${result.date}

                ${resultLabel}

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
        `;


        recentResultListElement.appendChild(
            recentResultCardElement
        );
    });
}


// ======================================================
// 팀 순위
// ======================================================

async function loadTeamRanking() {
    try {
        const response = await fetch(
            `${apiBaseUrl}/api/standings`
        );

        if (!response.ok) {
            throw new Error(
                "팀 순위를 불러오지 못했습니다."
            );
        }

        const standingsData =
            await response.json();

        renderTeamRanking(
            standingsData
        );

    } catch (error) {
        console.error(error);

        teamRankingListElement.innerHTML = `
            <p>
                팀 순위를 불러오는 중 오류가 발생했습니다.
            </p>
        `;
    }
}


function renderTeamRanking(standings) {
    teamRankingListElement.innerHTML = "";


    standings.forEach((team) => {

        const rankingRowElement =
            document.createElement("div");

        rankingRowElement.classList.add(
            "dashboard-ranking-row"
        );


        rankingRowElement.innerHTML = `

            <span class="dashboard-rank">
                ${team.rank}
            </span>


            <div class="dashboard-team">

                <img
                    src="${getTeamImagePath(team.name)}"
                    alt="${team.name} 로고"
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


// ======================================================
// 페이지 로딩
// ======================================================

loadTodayMatches();

loadRecentResults();

loadTeamRanking();