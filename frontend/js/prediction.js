import {
    apiBaseUrl,
} from "./config.js";

import {
    getCurrentUser,
    getUserToken,
    removeUserToken,
} from "./auth.js";


const predictionUserSummaryElement =
    document.querySelector(
        "#prediction-user-summary"
    );

const predictionMatchListElement =
    document.querySelector(
        "#prediction-match-list"
    );


let currentUser = null;
let predictionMatches = [];
let myPredictions = [];


// =========================================
// 포인트 표시
// =========================================

function formatPoints(
    points
) {

    return Number(
        points || 0
    ).toLocaleString(
        "ko-KR"
    );
}


// =========================================
// 예측 상태 표시
// =========================================

function getPredictionStatusText(
    status
) {

    if (
        status === "win"
    ) {
        return "적중";
    }

    if (
        status === "loss"
    ) {
        return "실패";
    }

    if (
        status === "refunded"
    ) {
        return "환불";
    }

    return "결과 대기";
}


// =========================================
// 내 예측 찾기
// 경기 + 세트 기준
// =========================================

function getMyPrediction(
    seriesId,
    setNumber
) {

    return myPredictions.find(
        (prediction) => {

            return (
                Number(
                    prediction.series_id
                )
                ===
                Number(
                    seriesId
                )

                &&

                Number(
                    prediction.set_number
                )
                ===
                Number(
                    setNumber
                )
            );
        }
    ) || null;
}


// =========================================
// 회원 정보
// =========================================

function renderUserSummary() {

    predictionUserSummaryElement.innerHTML =
        "";


    if (!currentUser) {

        const textElement =
            document.createElement(
                "span"
            );

        textElement.textContent =
            "로그인 후 승부예측에 참여할 수 있습니다.";

        predictionUserSummaryElement.appendChild(
            textElement
        );

        return;
    }


    const nicknameElement =
        document.createElement(
            "strong"
        );

    nicknameElement.textContent =
        currentUser.nickname;


    const pointsElement =
        document.createElement(
            "span"
        );

    pointsElement.textContent =
        `${formatPoints(
            currentUser.points
        )} P`;


    predictionUserSummaryElement.append(
        nicknameElement,
        pointsElement
    );
}


// =========================================
// 이미 참여한 세트 표시
// =========================================

function createCompletedSetElement(
    prediction
) {

    const containerElement =
        document.createElement(
            "div"
        );

    containerElement.className =
        "prediction-completed";


    const selectionElement =
        document.createElement(
            "strong"
        );

    selectionElement.textContent =
        prediction.selection_name;


    const stakeElement =
        document.createElement(
            "span"
        );

    stakeElement.textContent =
        `참여 ${formatPoints(
            prediction.stake_points
        )} P`;


    const payoutElement =
        document.createElement(
            "span"
        );

    payoutElement.textContent =
        `적중 시 ${formatPoints(
            prediction.expected_payout
        )} P`;


    const statusElement =
        document.createElement(
            "span"
        );

    statusElement.textContent =
        getPredictionStatusText(
            prediction.status
        );


    containerElement.append(
        selectionElement,
        stakeElement,
        payoutElement,
        statusElement
    );


    return containerElement;
}


// =========================================
// 세트 예측 영역
// =========================================

function createSetPredictionElement(
    match,
    setNumber
) {

    const setElement =
        document.createElement(
            "div"
        );

    setElement.className =
        "prediction-set-row";


    // =====================================
    // 세트 제목
    // =====================================

    const setTitleElement =
        document.createElement(
            "div"
        );

    setTitleElement.className =
        "prediction-set-title";

    setTitleElement.textContent =
        `${setNumber} SET`;


    setElement.appendChild(
        setTitleElement
    );


    // =====================================
    // 이미 참여했는지 확인
    // =====================================

    const existingPrediction =
        getMyPrediction(
            match.series_id,
            setNumber
        );


    if (existingPrediction) {

        setElement.appendChild(
            createCompletedSetElement(
                existingPrediction
            )
        );

        return setElement;
    }


    // =====================================
    // 선택 버튼
    // =====================================

    const optionContainerElement =
        document.createElement(
            "div"
        );

    optionContainerElement.className =
        "prediction-option-buttons";


    const teamAOdds =
        Number(
            match.odds?.team_a
            || 2.5
        );

    const drawOdds =
        Number(
            match.odds?.draw
            || 2.5
        );

    const teamBOdds =
        Number(
            match.odds?.team_b
            || 2.5
        );


    const options = [
        {
            side:
                "team_a",

            label:
                `${match.team_a.fcl_name} 승`,

            odds:
                teamAOdds,

            participantId:
                match.team_a.participant_id,
        },

        {
            side:
                "draw",

            label:
                "무승부",

            odds:
                drawOdds,

            participantId:
                null,
        },

        {
            side:
                "team_b",

            label:
                `${match.team_b.fcl_name} 승`,

            odds:
                teamBOdds,

            participantId:
                match.team_b.participant_id,
        },
    ];


    let selectedOption = null;


    // =====================================
    // 포인트 입력
    // =====================================

    const betAreaElement =
        document.createElement(
            "div"
        );

    betAreaElement.className =
        "prediction-bet-area";


    const stakeInputElement =
        document.createElement(
            "input"
        );

    stakeInputElement.type =
        "number";

    stakeInputElement.min =
        "1";

    stakeInputElement.max =
        String(
            match.max_stake_points
            || 1000
        );

    stakeInputElement.step =
        "1";

    stakeInputElement.placeholder =
        `1 ~ ${formatPoints(
            match.max_stake_points
            || 1000
        )} P`;

    stakeInputElement.className =
        "prediction-stake-input";


    const expectedElement =
        document.createElement(
            "span"
        );

    expectedElement.className =
        "prediction-expected";

    expectedElement.textContent =
        "예상 지급 0 P";


    // =====================================
    // 예상 지급액 업데이트
    // =====================================

    function updateExpectedPayout() {

        const stake =
            Number(
                stakeInputElement.value
            );


        if (
            !selectedOption
            ||
            !Number.isInteger(
                stake
            )
            ||
            stake <= 0
        ) {

            expectedElement.textContent =
                "예상 지급 0 P";

            return;
        }


        const expectedPayout =
            Math.floor(
                stake
                *
                selectedOption.odds
            );


        expectedElement.textContent =
            `예상 지급 ${formatPoints(
                expectedPayout
            )} P`;
    }


    options.forEach(
        (option) => {

            const buttonElement =
                document.createElement(
                    "button"
                );

            buttonElement.type =
                "button";

            buttonElement.className =
                "prediction-option-button";


            buttonElement.textContent =
                `${option.label} ×${option.odds.toFixed(
                    2
                )}`;


            buttonElement.addEventListener(
                "click",
                () => {

                    optionContainerElement
                        .querySelectorAll(
                            ".prediction-option-button"
                        )
                        .forEach(
                            (
                                otherButtonElement
                            ) => {

                                otherButtonElement
                                    .classList
                                    .remove(
                                        "selected"
                                    );
                            }
                        );


                    buttonElement.classList.add(
                        "selected"
                    );


                    selectedOption =
                        option;


                    updateExpectedPayout();
                }
            );


            optionContainerElement.appendChild(
                buttonElement
            );
        }
    );


    stakeInputElement.addEventListener(
        "input",
        updateExpectedPayout
    );


    // =====================================
    // 참여 버튼
    // =====================================

    const submitButtonElement =
        document.createElement(
            "button"
        );

    submitButtonElement.type =
        "button";

    submitButtonElement.className =
        "prediction-submit";

    submitButtonElement.textContent =
        `${setNumber}SET 예측 참여`;


    // 로그인 안 됨
    if (!currentUser) {

        optionContainerElement
            .querySelectorAll(
                "button"
            )
            .forEach(
                (
                    buttonElement
                ) => {

                    buttonElement.disabled =
                        true;
                }
            );


        stakeInputElement.disabled =
            true;

        submitButtonElement.disabled =
            true;

        submitButtonElement.textContent =
            "로그인 필요";
    }


    // 경기 당일 또는 마감
    if (!match.is_open) {

        optionContainerElement
            .querySelectorAll(
                "button"
            )
            .forEach(
                (
                    buttonElement
                ) => {

                    buttonElement.disabled =
                        true;
                }
            );


        stakeInputElement.disabled =
            true;

        submitButtonElement.disabled =
            true;

        submitButtonElement.textContent =
            "예측 마감";
    }


    submitButtonElement.addEventListener(
        "click",
        async () => {

            if (!currentUser) {

                alert(
                    "로그인이 필요합니다."
                );

                return;
            }


            if (!match.is_open) {

                alert(
                    "이미 마감된 경기입니다."
                );

                return;
            }


            if (!selectedOption) {

                alert(
                    "승 / 무 / 패 중 하나를 선택해주세요."
                );

                return;
            }


            const stakePoints =
                Number(
                    stakeInputElement.value
                );


            if (
                !Number.isInteger(
                    stakePoints
                )
                ||
                stakePoints <= 0
            ) {

                alert(
                    "1P 이상의 포인트를 입력해주세요."
                );

                return;
            }

            const maxStakePoints =
                Number(
                    match.max_stake_points
                    || 1000
                );


            if (
                stakePoints
                >
                maxStakePoints
            ) {

                alert(
                    `한 세트에는 최대 ${formatPoints(
                        maxStakePoints
                    )}P까지 예측할 수 있습니다.`
                );

                return;
            }


            if (
                stakePoints
                >
                Number(
                    currentUser.points
                    || 0
                )
            ) {

                alert(
                    "보유 포인트가 부족합니다."
                );

                return;
            }


            submitButtonElement.disabled =
                true;

            submitButtonElement.textContent =
                "처리 중...";


            try {

                const token =
                    getUserToken();


                const response =
                    await fetch(
                        `${apiBaseUrl}/api/predictions`,
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "Authorization":
                                    `Bearer ${token}`,
                            },

                            body:
                                JSON.stringify(
                                    {
                                        series_id:
                                            match.series_id,

                                        set_number:
                                            setNumber,

                                        prediction_type:
                                            (
                                                selectedOption.side
                                                === "draw"
                                                    ? "draw"
                                                    : "participant"
                                            ),

                                        participant_id:
                                            selectedOption
                                                .participantId,

                                        stake_points:
                                            stakePoints,
                                    }
                                ),
                        }
                    );


                if (
                    response.status
                    === 401
                ) {

                    removeUserToken();

                    currentUser =
                        null;

                    throw new Error(
                        "로그인 정보가 만료되었습니다."
                    );
                }


                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.detail
                        ||
                        "승부예측 참여에 실패했습니다."
                    );
                }


                await loadPredictionPage();


            } catch (
                error
            ) {

                console.error(
                    error
                );


                alert(
                    error.message
                );


                submitButtonElement.disabled =
                    false;

                submitButtonElement.textContent =
                    `${setNumber}SET 예측 참여`;
            }
        }
    );


    betAreaElement.append(
        stakeInputElement,
        expectedElement,
        submitButtonElement
    );


    setElement.append(
        optionContainerElement,
        betAreaElement
    );


    return setElement;
}


// =========================================
// 경기 카드
// =========================================

function createMatchCard(
    match
) {

    const cardElement =
        document.createElement(
            "article"
        );

    cardElement.className =
        "prediction-match-card";


    // =====================================
    // 경기 정보
    // =====================================

    const metaElement =
        document.createElement(
            "div"
        );

    metaElement.className =
        "prediction-match-meta";


    const roundElement =
        document.createElement(
            "span"
        );

    roundElement.textContent =
        match.round
            ? `ROUND ${match.round}`
            : "정규리그";


    const dateElement =
        document.createElement(
            "span"
        );

    dateElement.textContent =
        match.date;


    const openElement =
        document.createElement(
            "span"
        );

    openElement.textContent =
        match.is_open
            ? "예측 가능"
            : "예측 마감";


    metaElement.append(
        roundElement,
        dateElement,
        openElement
    );


    // =====================================
    // 대진
    // =====================================

    const versusElement =
        document.createElement(
            "div"
        );

    versusElement.className =
        "prediction-versus";


    const teamAElement =
        document.createElement(
            "div"
        );

    teamAElement.className =
        "prediction-team";


    if (
        match.team_a.logo_path
    ) {

        const imageElement =
            document.createElement(
                "img"
            );

        imageElement.src =
            match.team_a.logo_path;

        imageElement.alt =
            `${match.team_a.fcl_name} 로고`;


        teamAElement.appendChild(
            imageElement
        );
    }


    const teamANameElement =
        document.createElement(
            "strong"
        );

    teamANameElement.className =
        "prediction-team-name";

    teamANameElement.textContent =
        match.team_a.fcl_name;


    teamAElement.appendChild(
        teamANameElement
    );


    const vsElement =
        document.createElement(
            "span"
        );

    vsElement.className =
        "prediction-vs";

    vsElement.textContent =
        "VS";


    const teamBElement =
        document.createElement(
            "div"
        );

    teamBElement.className =
        "prediction-team";


    if (
        match.team_b.logo_path
    ) {

        const imageElement =
            document.createElement(
                "img"
            );

        imageElement.src =
            match.team_b.logo_path;

        imageElement.alt =
            `${match.team_b.fcl_name} 로고`;


        teamBElement.appendChild(
            imageElement
        );
    }


    const teamBNameElement =
        document.createElement(
            "strong"
        );

    teamANameElement.className =
        "prediction-team-name";

    teamBNameElement.textContent =
        match.team_b.fcl_name;


    teamBElement.appendChild(
        teamBNameElement
    );


    versusElement.append(
        teamAElement,
        vsElement,
        teamBElement
    );


    // =====================================
    // 1 / 2 / 3 세트
    // =====================================

    const setsElement =
        document.createElement(
            "div"
        );

    setsElement.className =
        "prediction-set-list";


    for (
        let setNumber = 1;
        setNumber <= 3;
        setNumber += 1
    ) {

        setsElement.appendChild(
            createSetPredictionElement(
                match,
                setNumber
            )
        );
    }


    cardElement.append(
        metaElement,
        versusElement,
        setsElement
    );


    return cardElement;
}


// =========================================
// 경기 목록
// =========================================

function renderMatches() {

    predictionMatchListElement.innerHTML =
        "";


    if (
        predictionMatches.length
        === 0
    ) {

        const emptyElement =
            document.createElement(
                "div"
            );

        emptyElement.className =
            "prediction-empty";

        emptyElement.textContent =
            "예측 가능한 정규리그 일정이 없습니다.";


        predictionMatchListElement.appendChild(
            emptyElement
        );

        return;
    }


    predictionMatches.forEach(
        (match) => {

            predictionMatchListElement.appendChild(
                createMatchCard(
                    match
                )
            );
        }
    );
}


// =========================================
// API
// =========================================

async function loadMatches() {

    const response =
        await fetch(
            `${apiBaseUrl}/api/predictions/matches`
        );


    if (!response.ok) {

        throw new Error(
            "승부예측 경기를 불러오지 못했습니다."
        );
    }


    predictionMatches =
        await response.json();
}


async function loadMyPredictions() {

    myPredictions = [];


    const token =
        getUserToken();


    if (!token) {
        return;
    }


    const response =
        await fetch(
            `${apiBaseUrl}/api/predictions/me`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`,
                },
            }
        );


    if (
        response.status
        === 401
    ) {

        removeUserToken();

        currentUser =
            null;

        return;
    }


    if (!response.ok) {

        throw new Error(
            "내 승부예측 내역을 불러오지 못했습니다."
        );
    }


    myPredictions =
        await response.json();
}


// =========================================
// 전체 로딩
// =========================================

async function loadPredictionPage() {

    predictionMatchListElement.textContent =
        "경기를 불러오는 중...";


    try {

        currentUser =
            await getCurrentUser();


        await Promise.all(
            [
                loadMatches(),
                loadMyPredictions(),
            ]
        );


        // 포인트 차감 후
        // 최신 회원 정보 다시 조회
        if (
            getUserToken()
        ) {

            currentUser =
                await getCurrentUser();
        }


        renderUserSummary();
        renderMatches();


    } catch (
        error
    ) {

        console.error(
            error
        );


        predictionMatchListElement.textContent =
            error.message;
    }
}


// =========================================
// 실행
// =========================================

loadPredictionPage();