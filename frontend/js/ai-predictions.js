import {
    apiBaseUrl,
} from "./config.js";


const seriesAccuracyElement =
    document.querySelector(
        "#ai-series-accuracy"
    );


const seriesDetailElement =
    document.querySelector(
        "#ai-series-detail"
    );


const seriesBrierElement =
    document.querySelector(
        "#ai-series-brier"
    );


const setAccuracyElement =
    document.querySelector(
        "#ai-set-accuracy"
    );


const setDetailElement =
    document.querySelector(
        "#ai-set-detail"
    );


const setBrierElement =
    document.querySelector(
        "#ai-set-brier"
    );


const historyListElement =
    document.querySelector(
        "#ai-history-list"
    );


const historyEmptyElement =
    document.querySelector(
        "#ai-history-empty"
    );


// =========================================
// 결과 표시명
// =========================================

function getResultLabel(
    result,
    teamA,
    teamB
) {

    if (
        result
        === "team_a"
    ) {

        return `${teamA} 승`;

    }


    if (
        result
        === "team_b"
    ) {

        return `${teamB} 승`;

    }


    if (
        result
        === "draw"
    ) {

        return "무승부";

    }


    return "-";
}


// =========================================
// 확률
// =========================================

function formatProbability(
    value
) {

    const numberValue =
        Number(value);


    if (
        !Number.isFinite(
            numberValue
        )
    ) {

        return "-";

    }


    if (
        Number.isInteger(
            numberValue
        )
    ) {

        return `${numberValue}%`;

    }


    return `${
        numberValue.toFixed(1)
    }%`;
}


// =========================================
// Brier
// =========================================

function formatBrier(
    value
) {

    if (
        value === null
        ||
        value === undefined
    ) {

        return "-";

    }


    const numberValue =
        Number(value);


    if (
        !Number.isFinite(
            numberValue
        )
    ) {

        return "-";

    }


    return numberValue.toFixed(4);
}


// =========================================
// 적중 상태
// =========================================

function createCorrectBadge(
    isCorrect
) {

    if (
        isCorrect === true
    ) {

        return `
            <span
                class="
                    ai-history-result-badge
                    is-correct
                "
            >
                적중
            </span>
        `;

    }


    if (
        isCorrect === false
    ) {

        return `
            <span
                class="
                    ai-history-result-badge
                    is-wrong
                "
            >
                실패
            </span>
        `;

    }


    return `
        <span
            class="
                ai-history-result-badge
                is-neutral
            "
        >
            판정 없음
        </span>
    `;
}


// =========================================
// 확률 BAR
// =========================================

function createProbabilityBar(
    prediction,
    teamA,
    teamB
) {

    if (!prediction) {

        return "";

    }


    const teamAWin =
        Math.max(
            0,
            Number(
                prediction.team_a_win
            )
            || 0
        );


    const draw =
        Math.max(
            0,
            Number(
                prediction.draw
            )
            || 0
        );


    const teamBWin =
        Math.max(
            0,
            Number(
                prediction.team_b_win
            )
            || 0
        );


    const total =
        teamAWin
        +
        draw
        +
        teamBWin;


    if (total <= 0) {

        return "";

    }


    const teamAWidth =
        (
            teamAWin
            /
            total
        )
        * 100;


    const drawWidth =
        (
            draw
            /
            total
        )
        * 100;


    const teamBWidth =
        (
            teamBWin
            /
            total
        )
        * 100;


    return `
        <div class="ai-history-probability-bar">

            <div
                class="
                    ai-history-probability-segment
                    team-a
                "
                style="
                    width:
                    ${teamAWidth}%;
                "
            >
                <span>
                    ${teamA}
                    ${formatProbability(
                        teamAWin
                    )}
                </span>
            </div>


            <div
                class="
                    ai-history-probability-segment
                    draw
                "
                style="
                    width:
                    ${drawWidth}%;
                "
            >
                <span>
                    무
                    ${formatProbability(
                        draw
                    )}
                </span>
            </div>


            <div
                class="
                    ai-history-probability-segment
                    team-b
                "
                style="
                    width:
                    ${teamBWidth}%;
                "
            >
                <span>
                    ${teamB}
                    ${formatProbability(
                        teamBWin
                    )}
                </span>
            </div>

        </div>
    `;
}


// =========================================
// SET 결과
// =========================================

function createSetResultsHtml(
    prediction
) {

    const sets =
        prediction.sets
        ?? [];


    if (
        sets.length === 0
    ) {

        return `
            <p class="ai-history-no-set">
                SET 결과 없음
            </p>
        `;

    }


    return `
        <div class="ai-history-set-list">

            ${
                sets.map(
                    setResult => {

                        const actualLabel =
                            getResultLabel(
                                setResult
                                    .actual_result,

                                prediction
                                    .team_a,

                                prediction
                                    .team_b
                            );


                        return `
                            <div
                                class="
                                    ai-history-set-row
                                "
                            >

                                <span
                                    class="
                                        ai-history-set-number
                                    "
                                >
                                    ${
                                        setResult
                                            .set_number
                                    }SET
                                </span>


                                <span
                                    class="
                                        ai-history-set-score
                                    "
                                >
                                    ${
                                        setResult
                                            .team_a_score
                                    }
                                    :
                                    ${
                                        setResult
                                            .team_b_score
                                    }
                                </span>


                                <span
                                    class="
                                        ai-history-set-result
                                    "
                                >
                                    ${actualLabel}
                                </span>


                                ${
                                    createCorrectBadge(
                                        setResult
                                            .is_correct
                                    )
                                }

                            </div>
                        `;

                    }
                ).join("")
            }

        </div>
    `;
}


// =========================================
// SUMMARY
// =========================================

function renderSummary(
    data
) {

    const seriesSummary =
        data.series_summary
        ?? {};


    const setSummary =
        data.set_summary
        ?? {};


    seriesAccuracyElement.textContent =
        (
            seriesSummary.accuracy
            !== null
            &&
            seriesSummary.accuracy
            !== undefined
        )
            ? `${
                seriesSummary.accuracy
            }%`
            : "-";


    seriesDetailElement.textContent =
        seriesSummary
            .prediction_count
        > 0
            ? `${
                seriesSummary.correct_count
            } / ${
                seriesSummary
                    .decisive_prediction_count
            } 적중`
            : "기록 없음";


    seriesBrierElement.textContent =
        formatBrier(
            seriesSummary
                .normalized_brier_score
        );


    setAccuracyElement.textContent =
        (
            setSummary.accuracy
            !== null
            &&
            setSummary.accuracy
            !== undefined
        )
            ? `${
                setSummary.accuracy
            }%`
            : "-";


    setDetailElement.textContent =
        setSummary
            .prediction_count
        > 0
            ? `${
                setSummary.correct_count
            } / ${
                setSummary
                    .decisive_prediction_count
            } 적중`
            : "기록 없음";


    setBrierElement.textContent =
        formatBrier(
            setSummary
                .normalized_brier_score
        );
}


// =========================================
// 경기 카드
// =========================================

function renderPredictionHistory(
    predictions
) {

    historyListElement.innerHTML =
        "";


    if (
        !Array.isArray(
            predictions
        )
        ||
        predictions.length === 0
    ) {

        historyEmptyElement.hidden =
            false;

        return;

    }


    historyEmptyElement.hidden =
        true;


    predictions.forEach(
        prediction => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.className =
                "ai-history-card";


            const roundText =
                prediction.round
                    ? `${
                        prediction.round
                    }R`
                    : "";


            const fixtureText =
                prediction.fixture_number
                    ? `#${
                        prediction
                            .fixture_number
                    }`
                    : "";


            const modelText =
                prediction.model
                ?? "모델 정보 없음";


            const actualResultText =
                getResultLabel(
                    prediction
                        .actual_result,

                    prediction.team_a,
                    prediction.team_b
                );


            const predictedResultText =
                getResultLabel(
                    prediction
                        .predicted_result,

                    prediction.team_a,
                    prediction.team_b
                );


            cardElement.innerHTML = `

                <div
                    class="
                        ai-history-card-header
                    "
                >

                    <div>

                        <div
                            class="
                                ai-history-card-date
                            "
                        >
                            ${
                                prediction.date
                                ?? "-"
                            }

                            ${
                                roundText
                            }

                            ${
                                fixtureText
                            }
                        </div>


                        <h2>
                            ${
                                prediction.team_a
                            }

                            <span>
                                VS
                            </span>

                            ${
                                prediction.team_b
                            }
                        </h2>

                    </div>


                    <div
                        class="
                            ai-history-card-meta
                        "
                    >
                        ${modelText}
                    </div>

                </div>


                <div
                    class="
                        ai-history-prediction-section
                    "
                >

                    <div
                        class="
                            ai-history-section-title
                        "
                    >
                        당시 1SET AI 예측
                    </div>


                    ${
                        createProbabilityBar(
                            prediction
                                .set_prediction,

                            prediction
                                .team_a,

                            prediction
                                .team_b
                        )
                    }

                </div>


                <div
                    class="
                        ai-history-prediction-section
                    "
                >

                    <div
                        class="
                            ai-history-section-title
                        "
                    >
                        ${
                            prediction
                                .target_set_count
                        }SET 경기 전체 예상
                    </div>


                    ${
                        createProbabilityBar(
                            prediction
                                .series_prediction,

                            prediction
                                .team_a,

                            prediction
                                .team_b
                        )
                    }

                </div>


                <div
                    class="
                        ai-history-outcome-grid
                    "
                >

                    <div
                        class="
                            ai-history-outcome-item
                        "
                    >
                        <span>
                            AI 1순위
                        </span>

                        <strong>
                            ${
                                predictedResultText
                            }
                        </strong>
                    </div>


                    <div
                        class="
                            ai-history-outcome-item
                        "
                    >
                        <span>
                            실제 경기
                        </span>

                        <strong>
                            ${
                                actualResultText
                            }
                        </strong>
                    </div>


                    <div
                        class="
                            ai-history-outcome-item
                        "
                    >
                        <span>
                            승점
                        </span>

                        <strong>
                            ${
                                prediction
                                    .team_a_points
                            }
                            :
                            ${
                                prediction
                                    .team_b_points
                            }
                        </strong>
                    </div>


                    <div
                        class="
                            ai-history-outcome-item
                        "
                    >
                        <span>
                            경기 예측
                        </span>

                        ${
                            createCorrectBadge(
                                prediction
                                    .is_correct
                            )
                        }
                    </div>


                    <div
                        class="
                            ai-history-outcome-item
                        "
                    >
                        <span>
                            Brier
                        </span>

                        <strong>
                            ${
                                formatBrier(
                                    (
                                        prediction
                                            .brier_score
                                        ?? null
                                    )
                                    /
                                    (
                                        prediction
                                            .brier_score
                                        === null
                                        ||
                                        prediction
                                            .brier_score
                                        === undefined
                                            ? 1
                                            : 2
                                    )
                                )
                            }
                        </strong>
                    </div>

                </div>


                <div
                    class="
                        ai-history-set-section
                    "
                >

                    <div
                        class="
                            ai-history-section-title
                        "
                    >
                        SET 결과
                    </div>


                    ${
                        createSetResultsHtml(
                            prediction
                        )
                    }

                </div>

            `;


            historyListElement
                .appendChild(
                    cardElement
                );

        }
    );
}


// =========================================
// LOAD
// =========================================

async function loadAiPredictionHistory() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                +
                "/api/ai-predictions/history"
            );


        if (!response.ok) {

            throw new Error(
                "AI 예측 기록을 불러오지 못했습니다."
            );

        }


        const data =
            await response.json();


        renderSummary(
            data
        );


        renderPredictionHistory(
            data.predictions
        );


    } catch (error) {

        console.error(
            error
        );


        historyEmptyElement.hidden =
            false;


        historyEmptyElement.innerHTML = `
            <strong>
                AI 예측 기록을 불러오지 못했습니다.
            </strong>

            <p>
                잠시 후 다시 시도해주세요.
            </p>
        `;

    }

}


loadAiPredictionHistory();