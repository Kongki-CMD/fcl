import {
    apiBaseUrl,
    getTeamImagePath,
    formatKstDateTime,
} from "./config.js";


const resultsListElement =
    document.querySelector(".results-list");

const adminModeButtonElement =
    document.querySelector(
        "#admin-mode-button"
    );


const adminStatusElement =
    document.querySelector(
        "#admin-status"
    );


const adminLogoutButtonElement =
    document.querySelector(
        "#admin-logout-button"
    );


const adminLoginModalElement =
    document.querySelector(
        "#admin-login-modal"
    );


const adminLoginFormElement =
    document.querySelector(
        "#admin-login-form"
    );


const adminPasswordInputElement =
    document.querySelector(
        "#admin-password-input"
    );


const adminLoginMessageElement =
    document.querySelector(
        "#admin-login-message"
    );


const adminLoginCancelButtonElement =
    document.querySelector(
        "#admin-login-cancel-button"
    );


const adminLoginSubmitButtonElement =
    document.querySelector(
        "#admin-login-submit-button"
    );


let isAdminMode = false;

const resultEditModalElement =
    document.querySelector(
        "#result-edit-modal"
    );

const resultEditFormElement =
    document.querySelector(
        "#result-edit-form"
    );

const resultEditTitleElement =
    document.querySelector(
        "#result-edit-title"
    );

const resultEditMessageElement =
    document.querySelector(
        "#result-edit-message"
    );

const resultEditCancelButtonElement =
    document.querySelector(
        "#result-edit-cancel-button"
    );

const resultEditSaveButtonElement =
    document.querySelector(
        "#result-edit-save-button"
    );


const editSet1TeamAElement =
    document.querySelector(
        "#edit-set1-team-a"
    );

const editSet1TeamBElement =
    document.querySelector(
        "#edit-set1-team-b"
    );

const editSet2TeamAElement =
    document.querySelector(
        "#edit-set2-team-a"
    );

const editSet2TeamBElement =
    document.querySelector(
        "#edit-set2-team-b"
    );

const editSet3TeamAElement =
    document.querySelector(
        "#edit-set3-team-a"
    );

const editSet3TeamBElement =
    document.querySelector(
        "#edit-set3-team-b"
    );


let currentEditSeriesId = null;


// =========================================
// Excel / DB 중복 판별용 키
// =========================================

function createResultKey(result) {

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


// =========================================
// 관리자 모드
// =========================================

function setAdminMode(
    enabled
) {

    isAdminMode = enabled;


    if (enabled) {

        adminModeButtonElement.classList.add(
            "hidden"
        );


        adminStatusElement.classList.remove(
            "hidden"
        );


        adminLogoutButtonElement.classList.remove(
            "hidden"
        );

    } else {

        adminModeButtonElement.classList.remove(
            "hidden"
        );


        adminStatusElement.classList.add(
            "hidden"
        );


        adminLogoutButtonElement.classList.add(
            "hidden"
        );
    }
}


function openAdminLoginModal() {

    adminLoginMessageElement.textContent =
        "";


    adminPasswordInputElement.value =
        "";


    adminLoginModalElement.classList.remove(
        "hidden"
    );


    adminPasswordInputElement.focus();
}


function closeAdminLoginModal() {

    adminLoginModalElement.classList.add(
        "hidden"
    );


    adminLoginMessageElement.textContent =
        "";
}


async function checkAdminSession() {

    const adminToken =
        sessionStorage.getItem(
            "fclAdminToken"
        );


    if (!adminToken) {

        setAdminMode(
            false
        );

        return;
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/check`,
            {
                headers: {
                    "X-Admin-Token":
                        adminToken
                }
            }
        );


        if (!response.ok) {

            sessionStorage.removeItem(
                "fclAdminToken"
            );


            setAdminMode(
                false
            );

            return;
        }


        setAdminMode(
            true
        );


    } catch (error) {

        console.error(
            error
        );


        setAdminMode(
            false
        );
    }
}

// =========================================
// 관리자 경기 삭제
// =========================================

async function deleteSeriesResult(
    seriesId
) {

    const adminToken =
        sessionStorage.getItem(
            "fclAdminToken"
        );


    if (!adminToken) {

        alert(
            "관리자 로그인이 필요합니다."
        );

        setAdminMode(
            false
        );

        return;
    }


    const confirmed =
        window.confirm(
            "이 경기 결과를 삭제하시겠습니까?\n\n"
            + "세트 결과, MVP, 선수 기록도 "
            + "함께 삭제됩니다."
        );


    if (!confirmed) {
        return;
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/series/${seriesId}`,
            {
                method: "DELETE",

                headers: {
                    "X-Admin-Token":
                        adminToken
                }
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status
                === 401
            ) {

                sessionStorage.removeItem(
                    "fclAdminToken"
                );


                setAdminMode(
                    false
                );
            }


            throw new Error(
                data.detail
                ??
                "경기 삭제에 실패했습니다."
            );
        }


        await loadResults();


        alert(
            data.message
        );


    } catch (error) {

        alert(
            error.message
        );
    }
}

async function openResultEditModal(
    seriesId
) {

    const adminToken =
        sessionStorage.getItem(
            "fclAdminToken"
        );


    if (!adminToken) {

        alert(
            "관리자 로그인이 필요합니다."
        );

        setAdminMode(false);

        return;
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/status`
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "경기 정보를 불러오지 못했습니다."
            );
        }


        if (
            !data.sets
            ||
            data.sets.length !== 3
        ) {

            throw new Error(
                "3세트 결과를 찾을 수 없습니다."
            );
        }


        currentEditSeriesId =
            seriesId;


        resultEditTitleElement.textContent =
            (
                `${data.series.team_a}`
                + " VS "
                + `${data.series.team_b}`
            );


        editSet1TeamAElement.value =
            data.sets[0].team_a_score;

        editSet1TeamBElement.value =
            data.sets[0].team_b_score;


        editSet2TeamAElement.value =
            data.sets[1].team_a_score;

        editSet2TeamBElement.value =
            data.sets[1].team_b_score;


        editSet3TeamAElement.value =
            data.sets[2].team_a_score;

        editSet3TeamBElement.value =
            data.sets[2].team_b_score;


        resultEditMessageElement.textContent =
            "";


        resultEditModalElement.classList.remove(
            "hidden"
        );


    } catch (error) {

        alert(
            error.message
        );
    }
}

function closeResultEditModal() {

    resultEditModalElement.classList.add(
        "hidden"
    );

    resultEditMessageElement.textContent =
        "";

    currentEditSeriesId = null;
}

async function saveEditedSeriesResult(
    event
) {

    event.preventDefault();


    if (!currentEditSeriesId) {
        return;
    }


    const adminToken =
        sessionStorage.getItem(
            "fclAdminToken"
        );


    if (!adminToken) {

        closeResultEditModal();

        setAdminMode(false);

        alert(
            "관리자 로그인이 필요합니다."
        );

        return;
    }


    const scoreElements = [
        editSet1TeamAElement,
        editSet1TeamBElement,
        editSet2TeamAElement,
        editSet2TeamBElement,
        editSet3TeamAElement,
        editSet3TeamBElement,
    ];


    if (
        scoreElements.some(
            element =>
                element.value === ""
        )
    ) {

        resultEditMessageElement.textContent =
            "3세트 점수를 모두 입력해주세요.";

        return;
    }


    const scores =
        scoreElements.map(
            element =>
                Number(
                    element.value
                )
        );


    if (
        scores.some(
            score =>
                !Number.isInteger(score)
                ||
                score < 0
        )
    ) {

        resultEditMessageElement.textContent =
            "0 이상의 정수만 입력해주세요.";

        return;
    }


    const confirmed =
        window.confirm(
            "입력한 점수로 경기 결과를 수정하시겠습니까?"
        );


    if (!confirmed) {
        return;
    }


    resultEditSaveButtonElement.disabled =
        true;

    resultEditSaveButtonElement.textContent =
        "수정 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/series/${currentEditSeriesId}/result`,
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-Admin-Token":
                        adminToken
                },

                body: JSON.stringify({
                    set1_team_a:
                        scores[0],

                    set1_team_b:
                        scores[1],

                    set2_team_a:
                        scores[2],

                    set2_team_b:
                        scores[3],

                    set3_team_a:
                        scores[4],

                    set3_team_b:
                        scores[5]
                })
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status === 401
            ) {

                sessionStorage.removeItem(
                    "fclAdminToken"
                );

                setAdminMode(false);
            }


            throw new Error(
                data.detail
                ??
                "경기 결과 수정에 실패했습니다."
            );
        }


        closeResultEditModal();


        await loadResults();


        alert(
            data.message
        );


    } catch (error) {

        resultEditMessageElement.textContent =
            error.message;


    } finally {

        resultEditSaveButtonElement.disabled =
            false;

        resultEditSaveButtonElement.textContent =
            "수정 완료";
    }
}



// =========================================
// 경기 결과 불러오기
// =========================================

async function loadResults() {

    try {

        // ================================
        // Excel 결과 + Neon 결과
        // ================================

        const [
            excelResponse,
            databaseResponse,
        ] = await Promise.all([
            fetch(
                `${apiBaseUrl}/api/results`
            ),

            fetch(
                `${apiBaseUrl}/api/fconline/series/completed-results`
            ),
        ]);


        // ================================
        // Excel 결과
        // ================================

        if (!excelResponse.ok) {

            throw new Error(
                "경기 결과를 불러오지 못했습니다."
            );

        }


        const excelResults =
            await excelResponse.json();


        // ================================
        // Neon 결과
        // ================================

        let databaseResults = [];


        if (databaseResponse.ok) {

            databaseResults =
                await databaseResponse.json();

        } else {

            console.error(
                "DB 경기 결과를 불러오지 못했습니다."
            );

        }


        // ================================
        // DB와 중복되는 기존 Excel 결과 제거
        //
        // DB 결과를 우선 사용
        // ================================

        const databaseResultKeys =
            new Set(
                databaseResults.map(
                    createResultKey
                )
            );


        const filteredExcelResults =
            excelResults.filter(
                result =>
                    !databaseResultKeys.has(
                        createResultKey(
                            result
                        )
                    )
            );


        // ================================
        // 결과 합치기
        // ================================

        const combinedResults = [
            ...databaseResults,
            ...filteredExcelResults,
        ];


        // 최신 경기 우선
        combinedResults.sort(
            (resultA, resultB) => {

                const dateCompare =
                    resultB.date.localeCompare(
                        resultA.date
                    );


                if (dateCompare !== 0) {

                    return dateCompare;

                }


                return (
                    (resultB.series_id ?? 0)
                    -
                    (resultA.series_id ?? 0)
                );

            }
        );


        renderResults(
            combinedResults
        );


    } catch (error) {

        console.error(
            error
        );


        resultsListElement.innerHTML = `
            <p>
                경기 결과를 불러오는 중
                오류가 발생했습니다.
            </p>
        `;

    }

}

// =========================================
// 완료 SERIES NEXON 기록 동기화
// =========================================

async function syncCompletedSeries(
    seriesId,
    buttonElement,
    messageElement
) {

    if (!seriesId) {
        return;
    }


    const originalText =
        buttonElement.textContent;


    buttonElement.disabled =
        true;


    buttonElement.textContent =
        "NEXON 확인 중...";


    if (messageElement) {

        messageElement.textContent =
            "";
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/fconline/series/${seriesId}/sync`,
            {
                method: "POST"
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status === 429
            ) {

                throw new Error(
                    "NEXON API 호출 제한 중입니다. 잠시 후 다시 확인해주세요."
                );
            }


            throw new Error(
                data.detail
                ??
                "NEXON 기록 확인에 실패했습니다."
            );
        }


        const statsSyncStatus =
            data.series
                ?.stats_sync_status;


        if (messageElement) {

            messageElement.textContent =
                data.sync_message
                ??
                "NEXON 경기 기록을 확인했습니다.";
        }


        // =============================
        // 동기화 완료
        // 결과 목록 다시 불러오기
        // MVP도 새로 표시됨
        // =============================

        if (
            statsSyncStatus
            === "synced"
        ) {

            await loadResults();

            return;
        }


        // =============================
        // 점수 충돌
        // =============================

        if (
            statsSyncStatus
            === "conflict"
        ) {

            buttonElement.disabled =
                false;


            buttonElement.textContent =
                "NEXON 기록 다시 확인";


            return;
        }


        // =============================
        // 아직 NEXON 반영 대기
        // =============================

        buttonElement.disabled =
            false;


        buttonElement.textContent =
            "NEXON 기록 확인";


    } catch (error) {

        console.error(
            error
        );


        if (messageElement) {

            messageElement.textContent =
                error.message;
        }


        buttonElement.disabled =
            false;


        buttonElement.textContent =
            originalText;
    }
}


// =========================================
// 경기 결과 출력
// =========================================

function renderResults(
    results
) {

    resultsListElement.innerHTML = "";


    if (results.length === 0) {

        resultsListElement.innerHTML = `
            <p>
                등록된 경기 결과가 없습니다.
            </p>
        `;

        return;
    }


    results.forEach((result) => {

        const resultCardElement =
            document.createElement("div");

        resultCardElement.classList.add(
            "result-card"
        );

        const adminControlHtml =
    (
        isAdminMode
        &&
        result.series_id
    )
        ? `
            <div class="result-admin-controls">

                <button
                    type="button"
                    class="result-admin-edit-button"
                    data-admin-action="edit"
                    data-series-id="${result.series_id}"
                >
                    수정
                </button>


                <button
                    type="button"
                    class="result-admin-delete-button"
                    data-admin-action="delete"
                    data-series-id="${result.series_id}"
                >
                    삭제
                </button>

            </div>
        `
        : "";


        // =====================================
        // 프리시즌 / 정규리그 표시
        // =====================================

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

        const finishedTimeHtml =
            result.completed_at
                ? `
                    <span class="result-finished-time">
                        종료시간 :
                        ${formatKstDateTime(
                            result.completed_at
                        )}
                        KST
                    </span>
                `
                : "";


        // =====================================
        // 세트별 결과
        // =====================================

        const setScoreHtml = (result.sets ?? [])
            .map((setResult) => {

                let teamAResult = "";
                let teamBResult = "";


                // 팀A 승리
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


                // 팀B 승리
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


                // 무승부
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


        // =====================================
        // MVP
        // Neon SERIES 결과에 저장된 MVP 사용
        // =====================================

        let mvpHtml = "";


        const mvp =
            result.mvp;


        if (mvp) {

            mvpHtml = `
                <div class="match-mvp">

                    <div class="match-mvp-title">
                        ★ MATCH MVP
                    </div>


                    <div class="match-mvp-content">

                        <img
                            src="${mvp.image_url}"
                            alt="${mvp.player_name}"
                            class="match-mvp-image"
                        >


                        <div class="match-mvp-info">

                            <strong class="match-mvp-name">
                                ${mvp.player_name}
                            </strong>


                            <span class="match-mvp-owner">
                                ${mvp.fcl_name}
                                (${mvp.nickname})
                            </span>


                            <div class="match-mvp-stats">

                                <span>
                                    합산 평점
                                    <strong>
                                        ${mvp.rating_total}
                                    </strong>
                                </span>


                                <span>
                                    평균
                                    <strong>
                                        ${mvp.average_rating}
                                    </strong>
                                </span>


                                <span>
                                    ${mvp.goals}골
                                    ${mvp.assists}도움
                                </span>


                                <span>
                                    ${mvp.sets_played}세트 출전
                                </span>

                            </div>

                        </div>

                    </div>

                </div>
            `;

        }

// =====================================
// NEXON 기록 동기화
// =====================================

let syncHtml = "";


const statsSyncStatus =
    result.stats_sync_status;


const canSyncNexon =
    result.source === "database"
    &&
    result.series_id
    &&
    (
        statsSyncStatus === "pending"
        ||
        statsSyncStatus === "conflict"
    );


if (canSyncNexon) {

    const syncButtonText =
        statsSyncStatus === "conflict"
            ? "NEXON 기록 다시 확인"
            : "NEXON 기록 확인";


    const syncStatusText =
        statsSyncStatus === "conflict"
            ? "수동 점수와 NEXON 기록 확인 필요"
            : `
                MVP 선수 선정 대기 중
                <br>
                <span class="result-sync-guide">
                    경기 후 2시간 뒤 클릭 바랍니다.
                    (NEXON 데이터 반영 시간)
                </span>
            `;


    syncHtml = `
        <div class="result-sync-panel">

            <div class="result-sync-status">
                ${syncStatusText}
            </div>

            <button
                type="button"
                class="result-sync-button"
                data-series-sync-button
                data-series-id="${result.series_id}"
            >
                ${syncButtonText}
            </button>

            <div
                class="result-sync-message"
                data-series-sync-message
            ></div>

        </div>
    `;
}


        // =====================================
        // 경기 결과 카드
        // =====================================

        resultCardElement.innerHTML = `

            <div class="result-date">

                <div class="result-date-info">

                    <span>
                        ${result.date}
                    </span>

                    ${resultLabel}

                </div>


                ${finishedTimeHtml}

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

            ${syncHtml}

            ${mvpHtml}


            ${adminControlHtml}
        `;


        resultsListElement.appendChild(
            resultCardElement
        );

    });

}

// =========================================
// NEXON 기록 확인 버튼
// =========================================

resultsListElement.addEventListener(
    "click",
    (event) => {

        const syncButtonElement =
            event.target.closest(
                "[data-series-sync-button]"
            );


        if (!syncButtonElement) {
            return;
        }


        const seriesId =
            Number(
                syncButtonElement.dataset
                    .seriesId
            );


        const resultCardElement =
            syncButtonElement.closest(
                ".result-card"
            );


        const syncMessageElement =
            resultCardElement
                ?.querySelector(
                    "[data-series-sync-message]"
                );


        syncCompletedSeries(
            seriesId,
            syncButtonElement,
            syncMessageElement
        );
    }
);


adminModeButtonElement.addEventListener(
    "click",
    openAdminLoginModal
);


adminLoginCancelButtonElement.addEventListener(
    "click",
    closeAdminLoginModal
);


adminLoginFormElement.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const password =
            adminPasswordInputElement.value;


        if (!password) {

            adminLoginMessageElement.textContent =
                "비밀번호를 입력해주세요.";

            return;
        }


        adminLoginSubmitButtonElement.disabled =
            true;


        adminLoginSubmitButtonElement.textContent =
            "확인 중...";


        try {

            const response = await fetch(
                `${apiBaseUrl}/api/admin/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        password: password
                    })
                }
            );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail
                    ??
                    "관리자 로그인에 실패했습니다."
                );
            }


            sessionStorage.setItem(
                "fclAdminToken",
                data.token
            );


            setAdminMode(
                true
            );


            closeAdminLoginModal();


            await loadResults();


        } catch (error) {

            adminLoginMessageElement.textContent =
                error.message;

        } finally {

            adminLoginSubmitButtonElement.disabled =
                false;


            adminLoginSubmitButtonElement.textContent =
                "로그인";
        }
    }
);


adminLogoutButtonElement.addEventListener(
    "click",
    async () => {

        sessionStorage.removeItem(
            "fclAdminToken"
        );


        setAdminMode(
            false
        );


        await loadResults();
    }
);

// 이벤트
resultsListElement.addEventListener(
    "click",
    async (event) => {

        const buttonElement =
            event.target.closest(
                "[data-admin-action]"
            );


        if (!buttonElement) {
            return;
        }


        const seriesId =
            Number(
                buttonElement.dataset.seriesId
            );


        if (!seriesId) {
            return;
        }


        const action =
            buttonElement.dataset.adminAction;


        if (action === "edit") {

            await openResultEditModal(
                seriesId
            );

            return;
        }


        if (action === "delete") {

            await deleteSeriesResult(
                seriesId
            );
        }
    }
);

resultEditCancelButtonElement.addEventListener(
    "click",
    closeResultEditModal
);


resultEditFormElement.addEventListener(
    "submit",
    saveEditedSeriesResult
);



// =========================================
// 실행
// =========================================

async function initializeResultsPage() {

    await checkAdminSession();

    await loadResults();
}


initializeResultsPage();

