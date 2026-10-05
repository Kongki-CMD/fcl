import {
    apiBaseUrl,
    loadFclSeasons,
    resolvePublicDisplaySeason,
} from "./config.js?v=season-default-1";


const seasonSummarySelectorElement =
    document.querySelector(
        "#season-summary-selector"
    );

const seasonSummaryFinalizationBadgeElement =
    document.querySelector(
        "#season-summary-finalization-badge"
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

const seasonSummaryBest11PitchElement =
    document.querySelector(
        "#season-summary-best11-pitch"
    );

const seasonSummaryGoalsElement =
    document.querySelector(
        "#season-summary-goals"
    );


const seasonSummaryAssistsElement =
    document.querySelector(
        "#season-summary-assists"
    );


const seasonSummaryRatingsElement =
    document.querySelector(
        "#season-summary-ratings"
    );

const seasonSummaryStatusElement =
    document.querySelector(
        "#season-summary-status"
    );

const seasonSummaryCustomPlayerImages = {

    "주앙 칸셀루":
        "./assets/images/players/custom/cancelo.png",

    "닉 포프":
        "./assets/images/players/custom/nick_pope.png",

    "곤살루 게드스":
        "./assets/images/players/custom/goncalo_guedes.png",

    "로빈 반페르시":
        "./assets/images/players/custom/van_persie.png",
};


const seasonSummaryBest11Slots = [

    {
        slot: "st_left",
        position: "ST",
        className:
            "season-summary-slot-st-left",
    },

    {
        slot: "st_right",
        position: "ST",
        className:
            "season-summary-slot-st-right",
    },


    {
        slot: "lm",
        position: "LM",
        className:
            "season-summary-slot-lm",
    },

    {
        slot: "lcm",
        position: "LCM",
        className:
            "season-summary-slot-lcm",
    },

    {
        slot: "rcm",
        position: "RCM",
        className:
            "season-summary-slot-rcm",
    },

    {
        slot: "rm",
        position: "RM",
        className:
            "season-summary-slot-rm",
    },


    {
        slot: "lb",
        position: "LB",
        className:
            "season-summary-slot-lb",
    },

    {
        slot: "lcb",
        position: "LCB",
        className:
            "season-summary-slot-lcb",
    },

    {
        slot: "rcb",
        position: "RCB",
        className:
            "season-summary-slot-rcb",
    },

    {
        slot: "rb",
        position: "RB",
        className:
            "season-summary-slot-rb",
    },


    {
        slot: "gk",
        position: "GK",
        className:
            "season-summary-slot-gk",
    },
];


const seasonSummaryPageElement =
    document.querySelector(
        ".season-summary-page"
    );


let availableSeasonSummarySeasons =
    [];


let selectedSeasonSummaryNumber =
    null;

let seasonSummaryPlayerSeasonMap =
    new Map();

// =========================================
// FC ONLINE 선수 시즌 메타데이터
// =========================================

async function loadSeasonSummaryPlayerSeasonMetadata() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/fconline/metadata/seasons`
            );


        if (!response.ok) {

            throw new Error(
                "선수 시즌 메타데이터 조회 실패"
            );
        }


        const data =
            await response.json();


        seasonSummaryPlayerSeasonMap =
            new Map(
                (
                    Array.isArray(
                        data?.seasons
                    )
                        ? data.seasons
                        : []
                ).map(
                    season => [
                        Number(
                            season.season_id
                        ),
                        season,
                    ]
                )
            );

    } catch (error) {

        console.error(
            error
        );


        seasonSummaryPlayerSeasonMap =
            new Map();
    }
}


// =========================================
// spId → 시즌 정보
// =========================================

function getSeasonSummaryPlayerSeasonInfo(
    spId
) {

    const numericSpId =
        Number(
            spId
        );


    if (
        !Number.isFinite(
            numericSpId
        )
    ) {

        return null;
    }


    const seasonId =
        Math.floor(
            numericSpId
            /
            1_000_000
        );


    return (
        seasonSummaryPlayerSeasonMap.get(
            seasonId
        )
        ||
        null
    );
}


// =========================================
// BEST11 시즌 아이콘
// =========================================

function createSeasonSummaryPlayerSeasonIcon(
    spId
) {

    const season =
        getSeasonSummaryPlayerSeasonInfo(
            spId
        );


    if (
        !season
        ||
        !season.season_image_url
    ) {

        return null;
    }


    const imageElement =
        document.createElement(
            "img"
        );


    imageElement.className =
        "season-summary-best11-season-icon";


    imageElement.src =
        season.season_image_url;


    imageElement.alt =
        season.class_name
        || "시즌";


    imageElement.title =
        season.class_name
        || "시즌";


    return imageElement;
}

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
// 현재 선택 시즌
// =========================================

function getSelectedSeasonSummaryRecord() {

    return (
        availableSeasonSummarySeasons
            .find(
                season =>
                    Number(
                        season.season_number
                    )
                    ===
                    selectedSeasonSummaryNumber
            )
        ||
        null
    );
}

// =========================================
// 공통 시즌 표시
// =========================================

function updateSeasonSummaryLabels() {

    if (!selectedSeasonSummaryNumber) {
        return;
    }


    const selectedSeason =
        getSelectedSeasonSummaryRecord();


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


    if (
        seasonSummaryFinalizationBadgeElement
    ) {

        const seasonStatus =
            selectedSeason?.status
            || "";


        seasonSummaryFinalizationBadgeElement
            .classList
            .remove(
                "is-finalized",
                "is-pending"
            );


        if (
            seasonStatus
            === "completed"
        ) {

            seasonSummaryFinalizationBadgeElement
                .textContent =
                "확정";


            seasonSummaryFinalizationBadgeElement
                .classList
                .add(
                    "is-finalized"
                );


            seasonSummaryFinalizationBadgeElement
                .title =
                "종료된 시즌의 확정 기록입니다.";

        } else {

            seasonSummaryFinalizationBadgeElement
                .textContent =
                (
                    seasonStatus
                    === "active"

                    ?
                    "진행 중 · 미확정"

                    :
                    "미확정"
                );


            seasonSummaryFinalizationBadgeElement
                .classList
                .add(
                    "is-pending"
                );


            seasonSummaryFinalizationBadgeElement
                .title =
                (
                    "시즌 종료 전 기록은 "
                    +
                    "변동될 수 있습니다."
                );
        }
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
// SECTION LOAD ERROR
//
// 한 영역이 실패해도
// 다른 시즌 결산 영역은 유지
// =========================================

function renderSeasonSummarySectionError(
    sectionKey
) {

    if (
        sectionKey
        === "champion"
    ) {

        if (
            seasonSummaryChampionNameElement
        ) {

            seasonSummaryChampionNameElement
                .textContent =
                "정보 확인 불가";
        }


        if (
            seasonSummaryChampionNicknameElement
        ) {

            seasonSummaryChampionNicknameElement
                .textContent =
                "우승자 정보를 불러오지 못했습니다.";
        }


        if (
            seasonSummaryChampionTeamElement
        ) {

            seasonSummaryChampionTeamElement
                .textContent =
                "잠시 후 다시 확인해주세요.";
        }


        renderSeasonChampionLogo(
            null
        );


        return;
    }


    if (
        sectionKey
        === "standings"
    ) {

        renderSeasonFinalStandings(
            {
                finalized: false,

                standings: [],

                message:
                    "시즌 최종 순위를 불러오지 못했습니다.",
            }
        );


        return;
    }


    if (
        sectionKey
        === "best11"
    ) {

        renderSeasonBest11(
            {
                best11: [],

                empty_label:
                    "정보 없음",
            }
        );


        return;
    }


    if (
        sectionKey
        === "awards"
    ) {

        renderSeasonAwardList(
            seasonSummaryGoalsElement,
            [],
            "goals",
            "득점 순위를 불러오지 못했습니다."
        );


        renderSeasonAwardList(
            seasonSummaryAssistsElement,
            [],
            "assists",
            "도움 순위를 불러오지 못했습니다."
        );


        renderSeasonAwardList(
            seasonSummaryRatingsElement,
            [],
            "average_rating",
            "평점 순위를 불러오지 못했습니다."
        );
    }
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
// BEST11 PLAYER IMAGE
// =========================================

function getSeasonSummaryPlayerImage(
    player
) {

    return (
        seasonSummaryCustomPlayerImages[
            player?.player_name
        ]
        ||
        player?.image_url
        ||
        ""
    );
}


// =========================================
// BEST11 PITCH 기본 라인
// =========================================

function resetSeasonBest11Pitch() {

    if (!seasonSummaryBest11PitchElement) {
        return;
    }


    seasonSummaryBest11PitchElement
        .innerHTML =
        `
            <div
                class="
                    season-summary-pitch-line
                    season-summary-pitch-half-line
                "
            ></div>

            <div
                class="
                    season-summary-pitch-circle
                "
            ></div>

            <div
                class="
                    season-summary-pitch-box
                    season-summary-pitch-box-top
                "
            ></div>

            <div
                class="
                    season-summary-pitch-box
                    season-summary-pitch-box-bottom
                "
            ></div>
        `;
}


// =========================================
// BEST11 PLAYER CARD
// =========================================

function createSeasonBest11PlayerElement(
    slot,
    player,
    emptyLabel = "최소 2세트"
) {

    const playerElement =
        document.createElement(
            "div"
        );


    playerElement.className =
        (
            "season-summary-best11-player "
            +
            slot.className
        );


    const positionElement =
        document.createElement(
            "span"
        );


    positionElement.className =
        "season-summary-best11-position";


    positionElement.textContent =
        slot.position;


    const imageWrapElement =
        document.createElement(
            "div"
        );


    imageWrapElement.className =
        "season-summary-best11-image";


    const nameElement =
        document.createElement(
            "strong"
        );


    const statsElement =
        document.createElement(
            "span"
        );


    statsElement.className =
        "season-summary-best11-stats";


    const ratingElement =
        document.createElement(
            "small"
        );


    const ownerElement =
        document.createElement(
            "span"
        );


    ownerElement.className =
        "season-summary-best11-owner";


    // EMPTY
    if (!player) {

        playerElement.classList.add(
            "is-empty"
        );


        imageWrapElement.textContent =
            "-";


        nameElement.textContent =
            "미확정";

        statsElement.textContent =
            "골/도움 -";


        ratingElement.textContent =
            "평점 -";


        ownerElement.textContent =
            emptyLabel;


        playerElement.append(
            positionElement,
            imageWrapElement,
            nameElement,
            statsElement,
            ratingElement,
            ownerElement
        );


        return playerElement;
    }


    const imageUrl =
        getSeasonSummaryPlayerImage(
            player
        );


    if (imageUrl) {

        const imageElement =
            document.createElement(
                "img"
            );


        imageElement.src =
            imageUrl;


        imageElement.alt =
            player.player_name;


        imageElement.addEventListener(
            "error",
            () => {

                imageWrapElement.innerHTML =
                    "";


                imageWrapElement.textContent =
                    slot.position;
            },
            {
                once: true,
            }
        );


        imageWrapElement.appendChild(
            imageElement
        );

    } else {

        imageWrapElement.textContent =
            slot.position;
    }


    const seasonIconElement =
        createSeasonSummaryPlayerSeasonIcon(
            player.sp_id
        );


    const nameTextElement =
        document.createElement(
            "span"
        );


    nameTextElement.className =
        "season-summary-best11-name-text";


    nameTextElement.textContent =
        player.player_name
        || "-";


    if (seasonIconElement) {

        nameElement.append(
            seasonIconElement,
            nameTextElement
        );

    } else {

        nameElement.appendChild(
            nameTextElement
        );
    }

    statsElement.textContent =
        (
            `${Number(
                player.goals
                ?? 0
            )}골`
            +
            " · "
            +
            `${Number(
                player.assists
                ?? 0
            )}도움`
        );


    ratingElement.textContent =
        (
            "평점 "
            +
            Number(
                player.average_rating
                ?? 0
            ).toFixed(2)
        );


    ownerElement.textContent =
        player.fcl_name
        || "-";


    playerElement.title =
        (
            `${player.player_name}`
            +
            ` · ${player.fcl_name}`
            +
            ` · ${player.sets_played}세트`
            +
            ` · ${Number(
                player.goals
                ?? 0
            )}골`
            +
            ` · ${Number(
                player.assists
                ?? 0
            )}도움`
            +
            ` · 평균 ${Number(
                player.average_rating
                ?? 0
            ).toFixed(2)}`
        );


    playerElement.append(
        positionElement,
        imageWrapElement,
        nameElement,
        statsElement,
        ratingElement,
        ownerElement
    );


    return playerElement;
}


// =========================================
// BEST11 출력
// =========================================

function renderSeasonBest11(
    data
) {

    if (!seasonSummaryBest11PitchElement) {
        return;
    }


    resetSeasonBest11Pitch();


    const best11 =
        Array.isArray(
            data?.best11
        )
            ? data.best11
            : [];


    const playerBySlot =
        new Map(
            best11.map(
                player => [
                    player.slot,
                    player,
                ]
            )
        );


    seasonSummaryBest11Slots.forEach(
        slot => {

            const player =
                playerBySlot.get(
                    slot.slot
                )
                ||
                null;


            const playerElement =
                createSeasonBest11PlayerElement(
                    slot,
                    player,
                    data?.empty_label
                    || "최소 2세트"
                );


            seasonSummaryBest11PitchElement
                .appendChild(
                    playerElement
                );
        }
    );
}


// =========================================
// BEST11 불러오기
// =========================================

async function loadSeasonBest11() {

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
                "/api/season/best11"
                +
                `?season=${requestedSeasonNumber}`
            )
        );


    if (!response.ok) {

        throw new Error(
            "Season Best11을 불러오지 못했습니다."
        );
    }


    const data =
        await response.json();


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
            "요청한 시즌과 Best11 데이터의 시즌이 일치하지 않습니다."
        );
    }


    renderSeasonBest11(
        data
    );
}

// =========================================
// AWARD PLAYER
// =========================================

function createSeasonAwardPlayerElement(
    player,
    valueKey
) {

    const rowElement =
        document.createElement(
            "div"
        );


    rowElement.className =
        "season-summary-award-player";


    const rankElement =
        document.createElement(
            "span"
        );


    rankElement.className =
        "season-summary-award-rank";


    rankElement.textContent =
        String(
            player.rank
        );


    const imageWrapElement =
        document.createElement(
            "div"
        );


    imageWrapElement.className =
        "season-summary-award-image";


    const imageUrl =
        getSeasonSummaryPlayerImage(
            player
        );


    if (imageUrl) {

        const imageElement =
            document.createElement(
                "img"
            );


        imageElement.src =
            imageUrl;


        imageElement.alt =
            player.player_name
            || "선수";


        imageElement.addEventListener(
            "error",
            () => {

                imageWrapElement.innerHTML =
                    "";


                imageWrapElement.textContent =
                    "P";
            },
            {
                once: true,
            }
        );


        imageWrapElement.appendChild(
            imageElement
        );

    } else {

        imageWrapElement.textContent =
            "P";
    }


    const infoElement =
        document.createElement(
            "div"
        );


    infoElement.className =
        "season-summary-award-info";


    const nameElement =
        document.createElement(
            "strong"
        );


    nameElement.textContent =
        player.player_name
        || "-";


    const ownerElement =
        document.createElement(
            "span"
        );


    ownerElement.textContent =
        (
            player.nickname

            ?
            (
                `${player.fcl_name}`
                +
                ` · ${player.nickname}`
            )

            :
            (
                player.fcl_name
                || "-"
            )
        );


    infoElement.append(
        nameElement,
        ownerElement
    );


    const valueElement =
        document.createElement(
            "b"
        );


    if (
        valueKey
        === "average_rating"
    ) {

        valueElement.textContent =
            Number(
                player.average_rating
                ?? 0
            ).toFixed(2);

    } else {

        valueElement.textContent =
            String(
                Number(
                    player[
                        valueKey
                    ]
                    ?? 0
                )
            );
    }


    rowElement.title =
        (
            `${player.player_name}`
            +
            ` · ${player.fcl_name}`
            +
            ` · ${player.sets_played}세트`
        );


    rowElement.append(
        rankElement,
        imageWrapElement,
        infoElement,
        valueElement
    );


    return rowElement;
}


// =========================================
// AWARD LIST
// =========================================

function renderSeasonAwardList(
    element,
    players,
    valueKey,
    emptyMessage
) {

    if (!element) {
        return;
    }


    element.innerHTML =
        "";


    if (
        !Array.isArray(
            players
        )
        ||
        players.length === 0
    ) {

        const emptyElement =
            document.createElement(
                "div"
            );


        emptyElement.className =
            "season-summary-award-empty";


        emptyElement.textContent =
            emptyMessage;


        element.appendChild(
            emptyElement
        );


        return;
    }


    players.forEach(
        player => {

            element.appendChild(
                createSeasonAwardPlayerElement(
                    player,
                    valueKey
                )
            );
        }
    );
}


// =========================================
// AWARDS 출력
// =========================================

function renderSeasonAwards(
    data
) {

    renderSeasonAwardList(
        seasonSummaryGoalsElement,
        data?.goals,
        "goals",
        "아직 득점 기록이 없습니다."
    );


    renderSeasonAwardList(
        seasonSummaryAssistsElement,
        data?.assists,
        "assists",
        "아직 도움 기록이 없습니다."
    );


    renderSeasonAwardList(
        seasonSummaryRatingsElement,
        data?.ratings,
        "average_rating",
        "평점 순위를 계산할 기록이 없습니다."
    );
}


// =========================================
// AWARDS 불러오기
// =========================================

async function loadSeasonAwards() {

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
                "/api/season/awards"
                +
                `?season=${requestedSeasonNumber}`
            )
        );


    if (!response.ok) {

        throw new Error(
            "시즌 TOP3 기록을 불러오지 못했습니다."
        );
    }


    const data =
        await response.json();


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
            "요청한 시즌과 TOP3 데이터의 시즌이 일치하지 않습니다."
        );
    }


    renderSeasonAwards(
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
        return false;
    }


    const requestedSeasonNumber =
        selectedSeasonSummaryNumber;


    updateSeasonSummaryLabels();


    const sections = [

        {
            key: "champion",
            label: "우승자",
            loader:
                loadSeasonChampion,
        },

        {
            key: "standings",
            label: "최종 순위",
            loader:
                loadSeasonFinalStandings,
        },

        {
            key: "best11",
            label: "Best11",
            loader:
                loadSeasonBest11,
        },

        {
            key: "awards",
            label: "TOP3",
            loader:
                loadSeasonAwards,
        },
    ];


    const results =
        await Promise.allSettled(

            sections.map(
                section =>
                    section.loader()
            )
        );


    // 시즌을 빠르게 변경한 경우
    // 이전 refresh가 현재 화면의 상태 메시지를
    // 덮어쓰지 않도록 함
    if (
        requestedSeasonNumber
        !==
        selectedSeasonSummaryNumber
    ) {

        return true;
    }


    const failedSections = [];


    results.forEach(
        (
            result,
            index
        ) => {

            if (
                result.status
                !== "rejected"
            ) {

                return;
            }


            const section =
                sections[
                    index
                ];


            failedSections.push(
                section.label
            );


            console.error(
                (
                    `Season ${requestedSeasonNumber} `
                    +
                    `${section.label} 로드 실패`
                ),
                result.reason
            );


            renderSeasonSummarySectionError(
                section.key
            );
        }
    );


    if (
        failedSections.length > 0
    ) {

        showSeasonSummaryStatus(
            (
                "일부 시즌 결산 정보를 "
                +
                "불러오지 못했습니다: "
                +
                failedSections.join(
                    ", "
                )
            )
        );


        return false;
    }


    hideSeasonSummaryStatus();


    return true;
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


    showSeasonSummaryStatus(
        (
            `Season ${nextSeasonNumber} `
            +
            "결산 정보를 불러오는 중입니다."
        )
    );


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

        await loadSeasonSummaryPlayerSeasonMetadata();

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
