import {
    apiBaseUrl,
    loadFclSeasons,
    resolvePublicDisplaySeason,
} from "./config.js?v=season-default-1";


const seasonSummarySelectorElement =
    document.querySelector(
        "#season-summary-selector"
    );


const seasonSummaryChampionSeasonElement =
    document.querySelector(
        ".season-summary-champion-season"
    );

const seasonSummaryChampionNameElement =
    document.querySelector(
        ".season-summary-champion-name"
    );


const seasonSummaryChampionNicknameElement =
    document.querySelector(
        ".season-summary-champion-nickname"
    );


const seasonSummaryChampionTeamElement =
    document.querySelector(
        ".season-summary-champion-team"
    );


const seasonSummaryChampionLogoElement =
    document.querySelector(
        ".season-summary-champion-logo"
    );

const seasonSummaryFinalStandingsElement =
    document.querySelector(
        "#season-summary-final-standings"
    );

const seasonSummaryStatusElement =
    document.querySelector(
        "#season-summary-status"
    );


const seasonSummaryPageElement =
    document.querySelector(
        ".season-summary-page"
    );


let availableSeasonSummarySeasons =
    [];


let selectedSeasonSummaryNumber =
    null;


// =========================================
// URL 시즌
// =========================================

function getRequestedSeasonSummaryNumber() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const seasonValue =
        Number(
            params.get(
                "season"
            )
        );


    if (
        Number.isInteger(
            seasonValue
        )
        &&
        seasonValue > 0
    ) {

        return seasonValue;
    }


    return null;
}


// =========================================
// URL 갱신
// =========================================

function updateSeasonSummaryUrl() {

    if (!selectedSeasonSummaryNumber) {
        return;
    }


    const url =
        new URL(
            window.location.href
        );


    url.searchParams.set(
        "season",
        String(
            selectedSeasonSummaryNumber
        )
    );


    window.history.replaceState(
        {},
        "",
        url
    );
}


// =========================================
// 시즌 SELECT 출력
// =========================================

function renderSeasonSummarySelector() {

    if (!seasonSummarySelectorElement) {
        return;
    }


    seasonSummarySelectorElement.innerHTML =
        "";


    const sortedSeasons =
        [
            ...availableSeasonSummarySeasons
        ].sort(
            (
                left,
                right
            ) =>
                Number(
                    right.season_number
                )
                -
                Number(
                    left.season_number
                )
        );


    sortedSeasons.forEach(
        season => {

            const seasonNumber =
                Number(
                    season.season_number
                );


            const optionElement =
                document.createElement(
                    "option"
                );


            optionElement.value =
                String(
                    seasonNumber
                );


            optionElement.textContent =
                `Season ${seasonNumber}`;


            if (
                seasonNumber
                ===
                selectedSeasonSummaryNumber
            ) {

                optionElement.selected =
                    true;
            }


            seasonSummarySelectorElement
                .appendChild(
                    optionElement
                );
        }
    );
}


// =========================================
// 공통 시즌 표시
// =========================================

function updateSeasonSummaryLabels() {

    if (!selectedSeasonSummaryNumber) {
        return;
    }


    if (
        seasonSummaryChampionSeasonElement
    ) {

        seasonSummaryChampionSeasonElement
            .textContent =
            (
                "FCL SEASON "
                +
                selectedSeasonSummaryNumber
            );
    }


    if (seasonSummaryPageElement) {

        seasonSummaryPageElement.dataset
            .season =
            String(
                selectedSeasonSummaryNumber
            );
    }
}


// =========================================
// 상태 표시
// =========================================

function showSeasonSummaryStatus(
    message
) {

    if (!seasonSummaryStatusElement) {
        return;
    }


    seasonSummaryStatusElement.textContent =
        message;


    seasonSummaryStatusElement
        .classList
        .remove(
            "hidden"
        );
}


function hideSeasonSummaryStatus() {

    if (!seasonSummaryStatusElement) {
        return;
    }


    seasonSummaryStatusElement.textContent =
        "";


    seasonSummaryStatusElement
        .classList
        .add(
            "hidden"
        );
}

// =========================================
// CHAMPION LOGO
// =========================================

function renderSeasonChampionLogo(
    champion
) {

    if (!seasonSummaryChampionLogoElement) {
        return;
    }


    seasonSummaryChampionLogoElement
        .innerHTML =
        "";


    if (
        !champion
        ||
        !champion.team_logo_path
    ) {

        const labelElement =
            document.createElement(
                "span"
            );


        labelElement.textContent =
            "TEAM";


        const valueElement =
            document.createElement(
                "strong"
            );


        valueElement.textContent =
            "LOGO";


        seasonSummaryChampionLogoElement
            .append(
                labelElement,
                valueElement
            );


        return;
    }


    const imageElement =
        document.createElement(
            "img"
        );


    imageElement.src =
        champion.team_logo_path;


    imageElement.alt =
        (
            `${champion.fcl_name} `
            +
            "우승 당시 팀 로고"
        );


    imageElement.addEventListener(
        "error",
        () => {

            seasonSummaryChampionLogoElement
                .innerHTML =
                "";


            const labelElement =
                document.createElement(
                    "span"
                );


            labelElement.textContent =
                "TEAM";


            const valueElement =
                document.createElement(
                    "strong"
                );


            valueElement.textContent =
                "LOGO";


            seasonSummaryChampionLogoElement
                .append(
                    labelElement,
                    valueElement
                );
        },
        {
            once: true,
        }
    );


    seasonSummaryChampionLogoElement
        .appendChild(
            imageElement
        );
}

// =========================================
// CHAMPION 출력
// =========================================

function renderSeasonChampion(
    data
) {

    const champion =
        data?.champion
        ?? null;


    if (
        !data?.completed
        ||
        !champion
    ) {

        if (
            seasonSummaryChampionNameElement
        ) {

            seasonSummaryChampionNameElement
                .textContent =
                "시즌 진행 중";
        }


        if (
            seasonSummaryChampionNicknameElement
        ) {

            seasonSummaryChampionNicknameElement
                .textContent =
                "우승자 미확정";
        }


        if (
            seasonSummaryChampionTeamElement
        ) {

            seasonSummaryChampionTeamElement
                .textContent =
                "결승 종료 후 확정";
        }


        renderSeasonChampionLogo(
            null
        );


        return;
    }


    if (
        seasonSummaryChampionNameElement
    ) {

        seasonSummaryChampionNameElement
            .textContent =
            champion.fcl_name
            || "-";
    }


    if (
        seasonSummaryChampionNicknameElement
    ) {

        seasonSummaryChampionNicknameElement
            .textContent =
            champion.nickname
            || "-";
    }


    if (
        seasonSummaryChampionTeamElement
    ) {

        seasonSummaryChampionTeamElement
            .textContent =
            champion.team_name
            || "팀 정보 없음";
    }


    renderSeasonChampionLogo(
        champion
    );
}

// =========================================
// CHAMPION 불러오기
// =========================================

async function loadSeasonChampion() {

    const requestedSeasonNumber =
        selectedSeasonSummaryNumber;


    if (!requestedSeasonNumber) {
        return;
    }


    const response =
        await fetch(
            (
                `${apiBaseUrl}`
                +
                "/api/season/champion"
                +
                `?season=${requestedSeasonNumber}`
            )
        );


    if (!response.ok) {

        throw new Error(
            "시즌 우승자 정보를 불러오지 못했습니다."
        );
    }


    const data =
        await response.json();


    // 시즌 변경 중 이전 요청이
    // 늦게 도착한 경우 화면에 반영하지 않음
    if (
        requestedSeasonNumber
        !==
        selectedSeasonSummaryNumber
    ) {

        return;
    }


    if (
        Number(
            data.season
        )
        !==
        requestedSeasonNumber
    ) {

        throw new Error(
            "요청한 시즌과 우승자 데이터의 시즌이 일치하지 않습니다."
        );
    }


    renderSeasonChampion(
        data
    );
}

// =========================================
// FINAL STANDINGS 출력
// =========================================

function renderSeasonFinalStandings(
    data
) {

    if (
        !seasonSummaryFinalStandingsElement
    ) {

        return;
    }


    seasonSummaryFinalStandingsElement
        .innerHTML =
        "";


    const standings =
        Array.isArray(
            data?.standings
        )
            ? data.standings
            : [];


    if (
        !data?.finalized
        ||
        standings.length !== 5
    ) {

        const emptyElement =
            document.createElement(
                "div"
            );


        emptyElement.className =
            "season-summary-standing-empty";


        emptyElement.textContent =
            (
                data?.message
                ||
                "시즌 최종 순위가 아직 확정되지 않았습니다."
            );


        seasonSummaryFinalStandingsElement
            .appendChild(
                emptyElement
            );


        return;
    }


    standings.forEach(
        standing => {

            const rowElement =
                document.createElement(
                    "div"
                );


            rowElement.className =
                "season-summary-standing-row";


            if (
                Number(
                    standing.rank
                )
                === 1
            ) {

                rowElement.classList.add(
                    "season-summary-standing-first"
                );
            }


            const rankElement =
                document.createElement(
                    "div"
                );


            rankElement.className =
                "season-summary-standing-rank";


            rankElement.textContent =
                String(
                    standing.rank
                );


            const logoElement =
                document.createElement(
                    "div"
                );


            logoElement.className =
                "season-summary-standing-logo";


            if (standing.team_logo_path) {

                const imageElement =
                    document.createElement(
                        "img"
                    );


                imageElement.src =
                    standing.team_logo_path;


                imageElement.alt =
                    (
                        `${standing.fcl_name} `
                        +
                        "팀 로고"
                    );


                imageElement.addEventListener(
                    "error",
                    () => {

                        logoElement.innerHTML =
                            "";


                        logoElement.textContent =
                            String(
                                standing.rank
                            );
                    },
                    {
                        once: true,
                    }
                );


                logoElement.appendChild(
                    imageElement
                );

            } else {

                logoElement.textContent =
                    String(
                        standing.rank
                    );
            }


            const participantElement =
                document.createElement(
                    "div"
                );


            participantElement.className =
                "season-summary-standing-participant";


            const nameElement =
                document.createElement(
                    "strong"
                );


            nameElement.textContent =
                standing.fcl_name
                || "-";


            const nicknameElement =
                document.createElement(
                    "span"
                );


            nicknameElement.textContent =
                standing.nickname
                || "-";


            participantElement.append(
                nameElement,
                nicknameElement
            );


            const teamElement =
                document.createElement(
                    "div"
                );


            teamElement.className =
                "season-summary-standing-team";


            teamElement.textContent =
                standing.team_name
                || "TEAM";


            rowElement.append(
                rankElement,
                logoElement,
                participantElement,
                teamElement
            );


            seasonSummaryFinalStandingsElement
                .appendChild(
                    rowElement
                );
        }
    );
}


// =========================================
// FINAL STANDINGS 불러오기
// =========================================

async function loadSeasonFinalStandings() {

    const requestedSeasonNumber =
        selectedSeasonSummaryNumber;


    if (!requestedSeasonNumber) {
        return;
    }


    const response =
        await fetch(
            (
                `${apiBaseUrl}`
                +
                "/api/season/final-standings"
                +
                `?season=${requestedSeasonNumber}`
            )
        );


    if (!response.ok) {

        throw new Error(
            "시즌 최종 순위를 불러오지 못했습니다."
        );
    }


    const data =
        await response.json();


    // 이전 시즌 요청이 늦게 도착한 경우
    // 현재 화면에 반영하지 않음
    if (
        requestedSeasonNumber
        !==
        selectedSeasonSummaryNumber
    ) {

        return;
    }


    if (
        Number(
            data.season
        )
        !==
        requestedSeasonNumber
    ) {

        throw new Error(
            "요청한 시즌과 최종 순위 데이터의 시즌이 일치하지 않습니다."
        );
    }


    renderSeasonFinalStandings(
        data
    );
}


// =========================================
// 시즌 데이터 새로고침
//
// 이후
// Champion
// 최종 순위
// Best11
// 득점 TOP3
// 도움 TOP3
// 평점 TOP3
//
// 모두 여기서 같은 시즌 번호를 사용한다.
// =========================================

async function refreshSeasonSummary() {

    if (!selectedSeasonSummaryNumber) {
        return;
    }


    updateSeasonSummaryLabels();


    await Promise.all([
        loadSeasonChampion(),
        loadSeasonFinalStandings(),
    ]);
}


// =========================================
// 시즌 변경
// =========================================

async function handleSeasonSummaryChange(
    event
) {

    const nextSeasonNumber =
        Number(
            event.target.value
        );


    if (
        !Number.isInteger(
            nextSeasonNumber
        )
        ||
        nextSeasonNumber <= 0
    ) {

        return;
    }


    if (
        nextSeasonNumber
        ===
        selectedSeasonSummaryNumber
    ) {

        return;
    }


    selectedSeasonSummaryNumber =
        nextSeasonNumber;


    updateSeasonSummaryUrl();


    await refreshSeasonSummary();
}


// =========================================
// 초기화
// =========================================

async function initializeSeasonSummary() {

    try {

        showSeasonSummaryStatus(
            "시즌 정보를 불러오는 중입니다."
        );


        availableSeasonSummarySeasons =
            await loadFclSeasons();


        if (
            availableSeasonSummarySeasons
                .length
            === 0
        ) {

            throw new Error(
                "등록된 시즌이 없습니다."
            );
        }


        const requestedSeasonNumber =
            getRequestedSeasonSummaryNumber();


        const selectedSeason =
            resolvePublicDisplaySeason(
                availableSeasonSummarySeasons,
                requestedSeasonNumber
            );


        if (!selectedSeason) {

            throw new Error(
                "표시할 시즌을 찾을 수 없습니다."
            );
        }


        selectedSeasonSummaryNumber =
            Number(
                selectedSeason
                    .season_number
            );


        renderSeasonSummarySelector();


        // URL에 직접 시즌이 들어온 경우는
        // 그대로 유지한다.
        //
        // 시즌 값이 없었거나 잘못된 값이면
        // 실제 선택된 시즌으로 URL 정규화.
        if (
            requestedSeasonNumber
            !==
            selectedSeasonSummaryNumber
        ) {

            updateSeasonSummaryUrl();
        }


        await refreshSeasonSummary();


        hideSeasonSummaryStatus();


    } catch (error) {

        console.error(
            error
        );


        showSeasonSummaryStatus(
            error.message
            ||
            "시즌 정보를 불러오지 못했습니다."
        );


        if (
            seasonSummarySelectorElement
        ) {

            seasonSummarySelectorElement
                .innerHTML =
                `
                    <option value="">
                        시즌 없음
                    </option>
                `;


            seasonSummarySelectorElement
                .disabled =
                true;
        }
    }
}


// =========================================
// EVENT
// =========================================

if (seasonSummarySelectorElement) {

    seasonSummarySelectorElement
        .addEventListener(
            "change",
            handleSeasonSummaryChange
        );
}


initializeSeasonSummary();
