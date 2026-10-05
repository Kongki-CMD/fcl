import {
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


    // =====================================
    // 다음 단계부터 실제 API 연결
    // =====================================
    //
    // await Promise.all([
    //     loadSeasonChampion(),
    //     loadSeasonFinalStandings(),
    //     loadSeasonBest11(),
    //     loadSeasonTopPlayers(),
    // ]);
    //
    // 모든 함수는
    // selectedSeasonSummaryNumber
    // 하나만 기준으로 사용한다.
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
