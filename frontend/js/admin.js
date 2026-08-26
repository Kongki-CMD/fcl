import {
    apiBaseUrl,
} from "./config.js";


const adminTokenStorageKey =
    "fclAdminToken";


const adminLoginSectionElement =
    document.querySelector(
        "#admin-login-section"
    );

const adminDashboardElement =
    document.querySelector(
        "#admin-dashboard"
    );

const adminLoginFormElement =
    document.querySelector(
        "#admin-login-form"
    );

const adminPasswordInputElement =
    document.querySelector(
        "#admin-password"
    );

const adminLoginMessageElement =
    document.querySelector(
        "#admin-login-message"
    );

const adminLogoutButtonElement =
    document.querySelector(
        "#admin-logout-button"
    );

const adminMenuButtonElements =
    document.querySelectorAll(
        ".admin-menu-button"
    );

const adminContentPageElements =
    document.querySelectorAll(
        ".admin-content-page"
    );

const adminParticipantListElement =
    document.querySelector(
        "#admin-participant-list"
    );

const adminUserListElement =
    document.querySelector(
        "#admin-user-list"
    );

const adminResultListElement =
    document.querySelector(
        "#admin-result-list"
    );

const adminPointShopFormElement =
    document.querySelector(
        "#admin-point-shop-form"
    );


const adminPointShopNameElement =
    document.querySelector(
        "#admin-point-shop-name"
    );


const adminPointShopCategoryElement =
    document.querySelector(
        "#admin-point-shop-category"
    );


const adminPointShopPriceElement =
    document.querySelector(
        "#admin-point-shop-price"
    );


const adminPointShopSortOrderElement =
    document.querySelector(
        "#admin-point-shop-sort-order"
    );


const adminPointShopImageUrlElement =
    document.querySelector(
        "#admin-point-shop-image-url"
    );


const adminPointShopDescriptionElement =
    document.querySelector(
        "#admin-point-shop-description"
    );


const adminPointShopActiveElement =
    document.querySelector(
        "#admin-point-shop-active"
    );


const adminPointShopFormMessageElement =
    document.querySelector(
        "#admin-point-shop-form-message"
    );


const adminPointShopCreateButtonElement =
    document.querySelector(
        "#admin-point-shop-create-button"
    );


const adminPointShopProductListElement =
    document.querySelector(
        "#admin-point-shop-product-list"
    );

const adminScheduleListElement =
    document.querySelector(
        "#admin-schedule-list"
    );

const adminPhotoRequestListElement =
    document.querySelector(
        "#admin-photo-request-list"
    );

const adminScheduleEditModalElement =
    document.querySelector(
        "#admin-schedule-edit-modal"
    );

const adminScheduleEditTitleElement =
    document.querySelector(
        "#admin-schedule-edit-title"
    );

const adminScheduleEditDateElement =
    document.querySelector(
        "#admin-schedule-edit-date"
    );

const adminScheduleEditMessageElement =
    document.querySelector(
        "#admin-schedule-edit-message"
    );

const adminScheduleEditCancelButtonElement =
    document.querySelector(
        "#admin-schedule-edit-cancel"
    );

const adminScheduleEditSaveButtonElement =
    document.querySelector(
        "#admin-schedule-edit-save"
    );


let editingAdminSchedule = null;

const adminResultEditModalElement =
    document.querySelector(
        "#admin-result-edit-modal"
    );

const adminResultEditTitleElement =
    document.querySelector(
        "#admin-result-edit-title"
    );

const adminResultEditMessageElement =
    document.querySelector(
        "#admin-result-edit-message"
    );

const adminResultEditCancelButtonElement =
    document.querySelector(
        "#admin-result-edit-cancel"
    );

const adminResultEditSaveButtonElement =
    document.querySelector(
        "#admin-result-edit-save"
    );

const adminResultEditGridElement =
document.querySelector(
    "#admin-result-edit-grid"
);

const adminPointShopExchangeListElement =
    document.querySelector(
        "#admin-point-shop-exchange-list"
    );


let editingAdminResult = null;





// =========================================
// 로그인 화면
// =========================================

function showAdminLogin() {

    adminLoginSectionElement
        .classList.remove(
            "hidden"
        );

    adminDashboardElement
        .classList.add(
            "hidden"
        );
}


// =========================================
// 관리자 화면
// =========================================

function showAdminDashboard() {

    adminLoginSectionElement
        .classList.add(
            "hidden"
        );

    adminDashboardElement
        .classList.remove(
            "hidden"
        );
}


// =========================================
// 저장된 관리자 토큰
// =========================================

function getAdminToken() {

    return sessionStorage.getItem(
        adminTokenStorageKey
    );
}


// =========================================
// 관리자 인증 확인
// =========================================

async function checkAdminSession() {

    const adminToken =
        getAdminToken();

    if (!adminToken) {

        showAdminLogin();

        return;
    }


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/check`,
            {
                headers: {
                    "X-Admin-Token":
                        adminToken,
                },
            }
        );


        if (!response.ok) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        showAdminDashboard();


    } catch (error) {

        console.error(
            error
        );

        showAdminLogin();
    }
}


// =========================================
// 관리자 로그인
// =========================================

adminLoginFormElement.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const password =
            adminPasswordInputElement
                .value
                .trim();


        if (!password) {

            adminLoginMessageElement
                .textContent =
                    "비밀번호를 입력해주세요.";

            return;
        }


        try {

            const response = await fetch(
                `${apiBaseUrl}/api/admin/login`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body: JSON.stringify({
                        password:
                            password,
                    }),
                }
            );


            const responseData =
                await response.json();


            if (!response.ok) {

                adminLoginMessageElement
                    .textContent =
                        responseData.detail
                        ?? "로그인에 실패했습니다.";

                return;
            }


            sessionStorage.setItem(
                adminTokenStorageKey,
                responseData.token
            );


            adminPasswordInputElement
                .value = "";

            adminLoginMessageElement
                .textContent = "";


            showAdminDashboard();


        } catch (error) {

            console.error(
                error
            );

            adminLoginMessageElement
                .textContent =
                    "서버 연결에 실패했습니다.";
        }
    }
);


// =========================================
// 로그아웃
// =========================================

adminLogoutButtonElement.addEventListener(
    "click",
    () => {

        sessionStorage.removeItem(
            adminTokenStorageKey
        );

        showAdminLogin();

        adminPasswordInputElement
            .focus();
    }
);


// =========================================
// 관리자 메뉴
// =========================================

adminMenuButtonElements.forEach(
    (buttonElement) => {

        buttonElement.addEventListener(
            "click",
            () => {

                const targetPage =
                    buttonElement.dataset
                        .adminPage;


                adminMenuButtonElements
                    .forEach(
                        (menuButtonElement) => {

                            menuButtonElement
                                .classList.remove(
                                    "active"
                                );
                        }
                    );


                buttonElement
                    .classList.add(
                        "active"
                    );


                adminContentPageElements
                    .forEach(
                        (contentPageElement) => {

                            const contentName =
                                contentPageElement
                                    .dataset
                                    .adminContent;


                            contentPageElement
                                .classList.toggle(
                                    "active",
                                    contentName
                                    === targetPage
                                );
                        }
                    );


                // 참가자 메뉴를 눌렀을 때
                // Neon 참가자 데이터 조회
                if (
                    targetPage
                    === "users"
                ) {

                    loadAdminUsers();
                }

                if (
                    targetPage
                    === "participants"
                ) {

                    loadAdminParticipants();
                }
                if (
                    targetPage
                    === "results"
                ) {

                    loadAdminResults();
                }
                if (
                    targetPage
                    === "schedule"
                ) {

                    loadAdminRegularSchedule();
                }

                if (
                    targetPage
                    === "photo-requests"
                ) {

                    loadAdminPhotoRequests();
                }

                if (
                    targetPage
                    === "point-shop"
                ) {

                    loadAdminPointShopProducts();

                    loadAdminPointShopExchanges();

                }

            }
        );
    }
);

// =========================================
// 참가자 / 현재 팀 조회
// =========================================

async function loadAdminParticipants() {

    const adminToken =
        getAdminToken();


    if (!adminToken) {
        return;
    }


    adminParticipantListElement
        .innerHTML =
            "참가자 정보를 불러오는 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/participants`,
            {
                headers: {
                    "X-Admin-Token":
                        adminToken,
                },
            }
        );


        if (response.status === 401) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        const responseData =
            await response.json();


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ?? "참가자 조회 실패"
            );
        }


        renderAdminParticipants(
            responseData
        );


    } catch (error) {

        console.error(
            error
        );

        adminParticipantListElement
            .textContent =
                "참가자 정보를 불러오지 못했습니다.";
    }
}

// =========================================
// 참가자 카드 출력
// =========================================

function renderAdminParticipants(
    participants
) {

    adminParticipantListElement
        .innerHTML = "";


    participants.forEach(
        (participant) => {

            const participantCardElement =
                document.createElement(
                    "article"
                );


            participantCardElement
                .classList.add(
                    "admin-participant-card"
                );


            participantCardElement
                .dataset.participantId =
                    participant.id;


            participantCardElement
                .innerHTML = `
                    <div
                        class="admin-participant-info"
                    >
                        <img
                            src="${participant.current_team_logo_path}"
                            alt="${participant.current_team_name} 로고"
                            class="admin-participant-logo"
                        >

                        <div>
                            <strong
                                class="admin-participant-name"
                            >
                                ${participant.fcl_name}
                            </strong>

                            <span
                                class="admin-participant-nickname"
                            >
                                ${participant.fc_nickname ?? ""}
                            </span>
                        </div>
                    </div>


                    <div
                        class="admin-team-fields"
                    >

                        <label>
                            현재 팀

                            <input
                                type="text"
                                class="admin-team-name-input"
                                value="${participant.current_team_name ?? ""}"
                            >
                        </label>


                        <label>
                            로고 경로

                            <input
                                type="text"
                                class="admin-team-logo-input"
                                value="${participant.current_team_logo_path ?? ""}"
                            >
                        </label>

                    </div>


                    <div
                        class="admin-participant-actions"
                    >

                        <span
                            class="admin-participant-message"
                        ></span>

                        <button
                            type="button"
                            class="admin-team-save-button"
                        >
                            저장
                        </button>

                    </div>
                `;


            const saveButtonElement =
                participantCardElement
                    .querySelector(
                        ".admin-team-save-button"
                    );


            saveButtonElement
                .addEventListener(
                    "click",
                    () => {

                        saveParticipantTeam(
                            participantCardElement
                        );
                    }
                );


            adminParticipantListElement
                .appendChild(
                    participantCardElement
                );
        }
    );
}

// =========================================
// 현재 팀 저장
// =========================================

async function saveParticipantTeam(
    participantCardElement
) {

    const participantId =
        participantCardElement
            .dataset
            .participantId;


    const teamNameInputElement =
        participantCardElement
            .querySelector(
                ".admin-team-name-input"
            );


    const teamLogoInputElement =
        participantCardElement
            .querySelector(
                ".admin-team-logo-input"
            );


    const messageElement =
        participantCardElement
            .querySelector(
                ".admin-participant-message"
            );


    const saveButtonElement =
        participantCardElement
            .querySelector(
                ".admin-team-save-button"
            );


    const currentTeamName =
        teamNameInputElement
            .value
            .trim();


    const currentTeamLogoPath =
        teamLogoInputElement
            .value
            .trim();


    if (
        !currentTeamName
        ||
        !currentTeamLogoPath
    ) {

        messageElement.textContent =
            "팀 이름과 로고 경로를 입력해주세요.";

        return;
    }


    const isConfirmed = confirm(
        `${currentTeamName}(으)로 `
        + "현재 팀을 변경하시겠습니까?"
    );


    if (!isConfirmed) {
        return;
    }


    saveButtonElement.disabled = true;

    messageElement.textContent =
        "저장 중...";


    try {

        const adminToken =
            getAdminToken();


        const response = await fetch(
            `${apiBaseUrl}`
            + `/api/admin/participants/`
            + `${participantId}/team`,
            {
                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-Admin-Token":
                        adminToken,
                },

                body: JSON.stringify({
                    current_team_name:
                        currentTeamName,

                    current_team_logo_path:
                        currentTeamLogoPath,
                }),
            }
        );


        const responseData =
            await response.json();


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ?? "현재 팀 저장 실패"
            );
        }


        messageElement.textContent =
            "저장되었습니다.";


        await loadAdminParticipants();


    } catch (error) {

        console.error(
            error
        );

        messageElement.textContent =
            error.message;

    } finally {

        saveButtonElement.disabled =
            false;
    }
}

// =========================================
// 완료 경기 결과 조회
// =========================================

async function loadAdminResults() {

    adminResultListElement.innerHTML =
        "경기 결과를 불러오는 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}`
            + "/api/fconline/series/completed-results"
        );


        if (!response.ok) {

            throw new Error(
                "경기 결과 조회 실패"
            );
        }


        const results =
            await response.json();


        renderAdminResults(
            results
        );


    } catch (error) {

        console.error(
            error
        );

        adminResultListElement.textContent =
            "경기 결과를 불러오지 못했습니다.";
    }
}

// =========================================
// 완료 경기 결과 출력
// =========================================

function renderAdminResults(
    results
) {

    adminResultListElement.innerHTML = "";


    if (results.length === 0) {

        adminResultListElement.textContent =
            "완료된 경기가 없습니다.";

        return;
    }


    results.forEach(
        (result) => {

            const resultCardElement =
                document.createElement(
                    "article"
                );


            resultCardElement.classList.add(
                "admin-result-card"
            );


            const teamAImagePath =
                result.team_a_snapshot_logo_path
                ?? "";

            const teamBImagePath =
                result.team_b_snapshot_logo_path
                ?? "";


            const setScoreHtml =
                (result.sets ?? [])
                    .map(
                        (setResult) => `
                            <span>
                                ${setResult.set}SET
                                ${setResult.team_a_score}
                                :
                                ${setResult.team_b_score}
                            </span>
                        `
                    )
                    .join("");


            resultCardElement.innerHTML = `
                <div class="admin-result-meta">

                    <span>
                        ${result.date ?? ""}
                    </span>

                    <strong>
                        ${result.match_type ?? ""}
                    </strong>

                </div>


                <div class="admin-result-match">

                    <div class="admin-result-team">

                        <img
                            src="${teamAImagePath}"
                            alt=""
                        >

                        <span>
                            ${result.team_a}
                        </span>

                    </div>


                    <strong class="admin-result-total-score">
                        ${result.team_a_score}
                        :
                        ${result.team_b_score}
                    </strong>


                    <div class="admin-result-team">

                        <img
                            src="${teamBImagePath}"
                            alt=""
                        >

                        <span>
                            ${result.team_b}
                        </span>

                    </div>

                </div>


                <div class="admin-result-sets">
                    ${setScoreHtml}
                </div>


                <div class="admin-result-actions">

                    <button
                        type="button"
                        class="admin-result-edit-button"
                        data-series-id="${result.series_id}"
                    >
                        수정
                    </button>

                    <button
                        type="button"
                        class="admin-result-delete-button"
                        data-series-id="${result.series_id}"
                    >
                        삭제
                    </button>

                </div>
            `;

            const editButtonElement =
                resultCardElement.querySelector(
                    ".admin-result-edit-button"
                );


            editButtonElement.addEventListener(
                "click",
                () => {

                    openAdminResultEdit(
                        result
                    );
                }
            );

            const deleteButtonElement =
                resultCardElement.querySelector(
                    ".admin-result-delete-button"
                );


            deleteButtonElement.addEventListener(
                "click",
                () => {

                    deleteAdminResult(
                        result
                    );
                }
            );


            adminResultListElement.appendChild(
                resultCardElement
            );
        }
    );
}

// =========================================
// 정규리그 일정 조회
// =========================================

async function loadAdminRegularSchedule() {

    const adminToken =
        getAdminToken();


    if (!adminToken) {
        return;
    }


    adminScheduleListElement
        .textContent =
            "정규리그 일정을 불러오는 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}`
            + "/api/admin/regular-schedule",
            {
                headers: {
                    "X-Admin-Token":
                        adminToken,
                },
            }
        );


        if (response.status === 401) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );


            showAdminLogin();

            return;
        }


        const schedules =
            await response.json();


        if (!response.ok) {

            throw new Error(
                schedules.detail
                ?? "정규리그 일정 조회 실패"
            );
        }


        renderAdminRegularSchedule(
            schedules
        );


    } catch (error) {

        console.error(
            error
        );


        adminScheduleListElement
            .textContent =
                "정규리그 일정을 불러오지 못했습니다.";
    }
}

// =========================================
// 정규리그 일정 출력
// =========================================

function renderAdminRegularSchedule(
    schedules
) {

    adminScheduleListElement
        .innerHTML = "";


    if (schedules.length === 0) {

        adminScheduleListElement
            .textContent =
                "등록된 정규리그 일정이 없습니다.";

        return;
    }


    schedules.forEach(
        (schedule) => {

            const scheduleCardElement =
                document.createElement(
                    "article"
                );


            scheduleCardElement
                .classList.add(
                    "admin-schedule-card"
                );


            let statusText =
                schedule.status;


            if (
                schedule.status
                === "scheduled"
            ) {

                statusText = "예정";

            } else if (
                schedule.status
                === "active"
            ) {

                statusText = "진행 중";

            } else if (
                schedule.status
                === "completed"
            ) {

                statusText = "완료";

            } else if (
                schedule.status
                === "cancelled"
            ) {

                statusText = "취소";
            }


            let scheduleActionHtml = "";


            if (
                schedule.status
                === "scheduled"
            ) {

                scheduleActionHtml = `
                    <button
                        type="button"
                        class="admin-schedule-edit-button"
                    >
                        날짜 변경
                    </button>
                `;
            }


            scheduleCardElement
                .innerHTML = `
                    <div class="admin-schedule-meta">

                        <strong>
                            ROUND ${schedule.round}
                        </strong>

                        <span>
                            경기 ${schedule.fixture_number}
                        </span>

                        <span>
                            ${statusText}
                        </span>

                    </div>


                    <div class="admin-schedule-date">
                        ${schedule.date ?? "-"}
                    </div>


                    <div class="admin-schedule-match">

                        <span>
                            ${schedule.team_a}
                        </span>

                        <strong>
                            VS
                        </strong>

                        <span>
                            ${schedule.team_b}
                        </span>

                    </div>


                    <div class="admin-schedule-actions">
                        ${scheduleActionHtml}
                    </div>
                `;


            const editButtonElement =
                scheduleCardElement
                    .querySelector(
                        ".admin-schedule-edit-button"
                    );


            if (editButtonElement) {

                editButtonElement
                    .addEventListener(
                        "click",
                        () => {

                            openAdminScheduleEdit(
                                schedule
                            );
                        }
                    );
            }


            adminScheduleListElement
                .appendChild(
                    scheduleCardElement
                );
        }
    );
}

// =========================================
// 정규리그 일정 수정 열기
// =========================================

function openAdminScheduleEdit(
    schedule
) {

    editingAdminSchedule =
        schedule;


    adminScheduleEditTitleElement
        .textContent =
            `ROUND ${schedule.round}`
            + ` / 경기 ${schedule.fixture_number}`
            + ` / ${schedule.team_a}`
            + " VS "
            + `${schedule.team_b}`;


    adminScheduleEditDateElement
        .value =
            schedule.date ?? "";


    adminScheduleEditMessageElement
        .textContent = "";


    adminScheduleEditModalElement
        .classList.remove(
            "hidden"
        );
}


// =========================================
// 정규리그 일정 수정 닫기
// =========================================

function closeAdminScheduleEdit() {

    editingAdminSchedule =
        null;


    adminScheduleEditMessageElement
        .textContent = "";


    adminScheduleEditModalElement
        .classList.add(
            "hidden"
        );
}

// =========================================
// 정규리그 일정 수정 저장
// =========================================

adminScheduleEditSaveButtonElement
    .addEventListener(
        "click",
        async () => {

            if (!editingAdminSchedule) {
                return;
            }


            const scheduledDate =
                adminScheduleEditDateElement
                    .value;


            if (!scheduledDate) {

                adminScheduleEditMessageElement
                    .textContent =
                        "경기 날짜를 선택해주세요.";

                return;
            }


            const isConfirmed =
                confirm(
                    `${editingAdminSchedule.date}`
                    + " → "
                    + `${scheduledDate}\n\n`
                    + "경기 날짜를 변경하시겠습니까?"
                );


            if (!isConfirmed) {
                return;
            }


            const adminToken =
                getAdminToken();


            adminScheduleEditSaveButtonElement
                .disabled = true;


            adminScheduleEditMessageElement
                .textContent =
                    "저장 중...";


            try {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + `/api/admin/series/`
                        + `${editingAdminSchedule.series_id}`
                        + "/schedule",
                        {
                            method: "PUT",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "X-Admin-Token":
                                    adminToken,
                            },

                            body:
                                JSON.stringify({
                                    scheduled_date:
                                        scheduledDate,
                                }),
                        }
                    );


                const responseData =
                    await response.json();


                if (
                    response.status
                    === 401
                ) {

                    sessionStorage
                        .removeItem(
                            adminTokenStorageKey
                        );


                    closeAdminScheduleEdit();

                    showAdminLogin();

                    return;
                }


                if (!response.ok) {

                    throw new Error(
                        responseData.detail
                        ?? "일정 변경 실패"
                    );
                }


                closeAdminScheduleEdit();


                await loadAdminRegularSchedule();


                alert(
                    responseData.message
                    ?? "일정이 변경되었습니다."
                );


            } catch (error) {

                console.error(
                    error
                );


                adminScheduleEditMessageElement
                    .textContent =
                        error.message;


            } finally {

                adminScheduleEditSaveButtonElement
                    .disabled = false;
            }
        }
    );

// =========================================
// 경기 결과 삭제
// =========================================

async function deleteAdminResult(
    result
) {

    if (!result.series_id) {

        alert(
            "삭제할 수 없는 경기입니다."
        );

        return;
    }


    let warningMessage =
        "경기 결과를 삭제하시겠습니까?";


    if (
        result.match_type
        === "정규리그"
    ) {

        warningMessage =
            "정규리그 경기 결과를 삭제하시겠습니까?\n\n"
            + "경기 일정은 유지되고 "
            + "경기 결과만 초기화됩니다.";

    } else if (
        result.match_type
        === "플레이오프"
    ) {

        warningMessage =
            `${result.playoff_stage ?? "플레이오프"} `
            + "경기 결과를 삭제하시겠습니까?\n\n"
            + "현재 경기는 예정 상태로 복구되며, "
            + "이후 자동 생성된 대진이 있으면 "
            + "함께 정리될 수 있습니다.";

    } else {

        warningMessage =
            "프리시즌 경기 결과를 삭제하시겠습니까?\n\n"
            + "해당 경기 데이터가 삭제됩니다.";
    }


    const isConfirmed =
        confirm(
            warningMessage
        );


    if (!isConfirmed) {
        return;
    }


    const adminToken =
        getAdminToken();


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/series/`
                + `${result.series_id}`,
                {
                    method: "DELETE",

                    headers: {
                        "X-Admin-Token":
                            adminToken,
                    },
                }
            );


        const responseData =
            await response.json();


        if (response.status === 401) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ?? "경기 결과 삭제 실패"
            );
        }


        alert(
            responseData.message
            ?? "경기 결과가 삭제되었습니다."
        );


        await loadAdminResults();


    } catch (error) {

        console.error(
            error
        );

        alert(
            error.message
        );
    }
}

// =========================================
// 경기 결과 수정
// 동점 승자 UI 표시 갱신
// =========================================

function updateAdminResultTieControls(
    setNumber
) {

    if (
        !editingAdminResult
        ||
        editingAdminResult.match_type
        !== "플레이오프"
    ) {
        return;
    }


    const teamAInputElement =
        adminResultEditGridElement
            .querySelector(
                `[data-set-number="${setNumber}"]`
                + `[data-score-side="team_a"]`
            );


    const teamBInputElement =
        adminResultEditGridElement
            .querySelector(
                `[data-set-number="${setNumber}"]`
                + `[data-score-side="team_b"]`
            );


    if (
        !teamAInputElement
        ||
        !teamBInputElement
    ) {
        return;
    }


    const teamAValue =
        teamAInputElement.value.trim();

    const teamBValue =
        teamBInputElement.value.trim();


    const isTie =
        teamAValue !== ""
        &&
        teamBValue !== ""
        &&
        Number(teamAValue)
        === Number(teamBValue);


    const tieControlElements =
        adminResultEditGridElement
            .querySelectorAll(
                `[data-tie-set="${setNumber}"]`
            );


    tieControlElements.forEach(
        (controlElement) => {

            controlElement.classList.toggle(
                "hidden",
                !isTie
            );
        }
    );
}


// =========================================
// 경기 결과 수정 열기
// =========================================

function openAdminResultEdit(
    result
) {

    if (!result.series_id) {

        alert(
            "수정할 수 없는 경기입니다."
        );

        return;
    }


    const isPlayoff =
        result.match_type
        === "플레이오프";


    const maxSets =
        isPlayoff
            ? Number(result.best_of)
            : 3;


    if (
        !Number.isInteger(maxSets)
        ||
        ![3, 5, 7].includes(maxSets)
    ) {

        alert(
            "경기 세트 정보를 확인할 수 없습니다."
        );

        return;
    }


    editingAdminResult =
        result;


    const sets =
        result.sets ?? [];


    let titleText =
        `${result.team_a}`
        + " VS "
        + `${result.team_b}`;


    if (isPlayoff) {

        titleText +=
            ` / ${result.playoff_stage}`
            + ` / BO${maxSets}`
            + ` / ${result.wins_required}선승`;
    }


    adminResultEditTitleElement
        .textContent =
            titleText;


    adminResultEditGridElement
        .innerHTML = "";


    for (
        let setNumber = 1;
        setNumber <= maxSets;
        setNumber += 1
    ) {

        const savedSet =
            sets.find(
                (setResult) =>
                    Number(
                        setResult.set
                    )
                    === setNumber
            )
            ?? null;


        const teamAScore =
            savedSet
                ?.team_a_score
            ?? "";

        const teamBScore =
            savedSet
                ?.team_b_score
            ?? "";


        const winnerSide =
            savedSet
                ?.winner_side
            ?? "";


        const teamASelected =
            winnerSide
            === "team_a";

        const teamBSelected =
            winnerSide
            === "team_b";


        let tieWinnerHtml = "";


        if (isPlayoff) {

            tieWinnerHtml = `
                <div
                    class="admin-result-edit-tie-row hidden"
                    data-tie-set="${setNumber}"
                >

                    <button
                        type="button"
                        class="admin-result-edit-winner-button"
                        data-set-number="${setNumber}"
                        data-winner-side="team_a"
                        data-team-name="${result.team_a}"
                    >
                        ${teamASelected ? "✓ " : ""}
                        ${result.team_a} 승
                    </button>

                    <span
                        class="admin-result-edit-tie-label"
                    >
                        동점 승자
                    </span>

                    <button
                        type="button"
                        class="admin-result-edit-winner-button"
                        data-set-number="${setNumber}"
                        data-winner-side="team_b"
                        data-team-name="${result.team_b}"
                    >
                        ${teamBSelected ? "✓ " : ""}
                        ${result.team_b} 승
                    </button>

                </div>
            `;
        }


        adminResultEditGridElement
            .insertAdjacentHTML(
                "beforeend",
                `
                    <span>
                        ${setNumber} SET
                    </span>

                    <input
                        type="number"
                        min="0"
                        step="1"
                        value="${teamAScore}"
                        data-set-number="${setNumber}"
                        data-score-side="team_a"
                    >

                    <span>:</span>

                    <input
                        type="number"
                        min="0"
                        step="1"
                        value="${teamBScore}"
                        data-set-number="${setNumber}"
                        data-score-side="team_b"
                    >

                    ${tieWinnerHtml}
                `
            );
    }


    const scoreInputElements =
        adminResultEditGridElement
            .querySelectorAll(
                "[data-score-side]"
            );


    scoreInputElements.forEach(
        (inputElement) => {

            inputElement.addEventListener(
                "input",
                () => {

                    updateAdminResultTieControls(
                        Number(
                            inputElement
                                .dataset
                                .setNumber
                        )
                    );
                }
            );
        }
    );


    const winnerButtonElements =
        adminResultEditGridElement
            .querySelectorAll(
                ".admin-result-edit-winner-button"
            );


    winnerButtonElements.forEach(
        (buttonElement) => {

            if (
                savedWinnerMatchesButton(
                    result,
                    buttonElement
                )
            ) {

                buttonElement.classList.add(
                    "selected"
                );
            }


            buttonElement.addEventListener(
                "click",
                () => {

                    const setNumber =
                        buttonElement
                            .dataset
                            .setNumber;


                    const sameSetButtons =
                        adminResultEditGridElement
                            .querySelectorAll(
                                ".admin-result-edit-winner-button"
                                + `[data-set-number="${setNumber}"]`
                            );


                    sameSetButtons.forEach(
                        (candidateButtonElement) => {

                            const isSelected =
                                candidateButtonElement
                                === buttonElement;


                            candidateButtonElement
                                .classList.toggle(
                                    "selected",
                                    isSelected
                                );


                            candidateButtonElement
                                .textContent =
                                    (
                                        isSelected
                                            ? "✓ "
                                            : ""
                                    )
                                    + candidateButtonElement
                                        .dataset
                                        .teamName
                                    + " 승";
                        }
                    );
                }
            );
        }
    );


    if (isPlayoff) {

        for (
            let setNumber = 1;
            setNumber <= maxSets;
            setNumber += 1
        ) {

            updateAdminResultTieControls(
                setNumber
            );
        }
    }


    adminResultEditMessageElement
        .textContent = "";


    adminResultEditModalElement
        .classList.remove(
            "hidden"
        );
}


// =========================================
// 기존 winner_side와 버튼 일치 확인
// =========================================

function savedWinnerMatchesButton(
    result,
    buttonElement
) {

    const setNumber =
        Number(
            buttonElement
                .dataset
                .setNumber
        );


    const savedSet =
        (result.sets ?? [])
            .find(
                (setResult) =>
                    Number(
                        setResult.set
                    )
                    === setNumber
            );


    if (!savedSet) {
        return false;
    }


    return (
        savedSet.winner_side
        === buttonElement
            .dataset
            .winnerSide
    );
}


// =========================================
// 경기 결과 수정 닫기
// =========================================

function closeAdminResultEdit() {

    editingAdminResult =
        null;


    adminResultEditGridElement
        .innerHTML = "";


    adminResultEditMessageElement
        .textContent = "";


    adminResultEditModalElement
        .classList.add(
            "hidden"
        );
}


// =========================================
// 경기 결과 수정 저장
// =========================================

adminResultEditSaveButtonElement
    .addEventListener(
        "click",
        async () => {

            if (!editingAdminResult) {
                return;
            }


            const isPlayoff =
                editingAdminResult
                    .match_type
                === "플레이오프";


            const maxSets =
                isPlayoff
                    ? Number(
                        editingAdminResult
                            .best_of
                    )
                    : 3;


            const winsRequired =
                isPlayoff
                    ? Number(
                        editingAdminResult
                            .wins_required
                    )
                    : null;


            const requestBody = {};


            let gapFound = false;

            let teamAWins = 0;
            let teamBWins = 0;

            let seriesWinnerFound =
                false;


            for (
                let setNumber = 1;
                setNumber <= maxSets;
                setNumber += 1
            ) {

                const teamAInputElement =
                    adminResultEditGridElement
                        .querySelector(
                            `[data-set-number="${setNumber}"]`
                            + `[data-score-side="team_a"]`
                        );


                const teamBInputElement =
                    adminResultEditGridElement
                        .querySelector(
                            `[data-set-number="${setNumber}"]`
                            + `[data-score-side="team_b"]`
                        );


                const teamARaw =
                    teamAInputElement
                        .value
                        .trim();

                const teamBRaw =
                    teamBInputElement
                        .value
                        .trim();


                if (
                    teamARaw === ""
                    &&
                    teamBRaw === ""
                ) {

                    if (
                        !isPlayoff
                        ||
                        setNumber <= 3
                    ) {

                        adminResultEditMessageElement
                            .textContent =
                                `${setNumber}세트 점수를 `
                                + "입력해주세요.";

                        return;
                    }


                    gapFound = true;

                    continue;
                }


                if (
                    teamARaw === ""
                    ||
                    teamBRaw === ""
                ) {

                    adminResultEditMessageElement
                        .textContent =
                            `${setNumber}세트의 `
                            + "양쪽 점수를 모두 입력해주세요.";

                    return;
                }


                if (gapFound) {

                    adminResultEditMessageElement
                        .textContent =
                            "중간 세트를 비워둔 채 "
                            + "다음 세트를 입력할 수 없습니다.";

                    return;
                }


                if (
                    isPlayoff
                    &&
                    seriesWinnerFound
                ) {

                    adminResultEditMessageElement
                        .textContent =
                            "선승 도달 이후의 "
                            + "추가 세트는 입력할 수 없습니다.";

                    return;
                }


                const teamAScore =
                    Number(teamARaw);

                const teamBScore =
                    Number(teamBRaw);


                if (
                    !Number.isInteger(
                        teamAScore
                    )
                    ||
                    !Number.isInteger(
                        teamBScore
                    )
                    ||
                    teamAScore < 0
                    ||
                    teamBScore < 0
                ) {

                    adminResultEditMessageElement
                        .textContent =
                            "점수는 0 이상의 "
                            + "정수여야 합니다.";

                    return;
                }


                let winnerSide = null;


                if (
                    teamAScore
                    >
                    teamBScore
                ) {

                    winnerSide =
                        "team_a";

                } else if (
                    teamBScore
                    >
                    teamAScore
                ) {

                    winnerSide =
                        "team_b";

                } else if (isPlayoff) {

                    const selectedWinnerButton =
                        adminResultEditGridElement
                            .querySelector(
                                ".admin-result-edit-winner-button.selected"
                                + `[data-set-number="${setNumber}"]`
                            );


                    if (!selectedWinnerButton) {

                        adminResultEditMessageElement
                            .textContent =
                                `${setNumber}세트가 동점입니다. `
                                + "실제 승자를 선택해주세요.";

                        return;
                    }


                    winnerSide =
                        selectedWinnerButton
                            .dataset
                            .winnerSide;
                }


                requestBody[
                    `set${setNumber}_team_a`
                ] = teamAScore;


                requestBody[
                    `set${setNumber}_team_b`
                ] = teamBScore;


                requestBody[
                    `set${setNumber}_winner_side`
                ] = (
                    isPlayoff
                        ? winnerSide
                        : null
                );


                if (isPlayoff) {

                    if (
                        winnerSide
                        === "team_a"
                    ) {

                        teamAWins += 1;

                    } else if (
                        winnerSide
                        === "team_b"
                    ) {

                        teamBWins += 1;
                    }


                    if (
                        teamAWins
                        >= winsRequired
                        ||
                        teamBWins
                        >= winsRequired
                    ) {

                        seriesWinnerFound =
                            true;
                    }
                }
            }


            if (
                isPlayoff
                &&
                !seriesWinnerFound
            ) {

                adminResultEditMessageElement
                    .textContent =
                        `${winsRequired}승에 도달한 `
                        + "참가자가 없습니다.";

                return;
            }


            const isConfirmed =
                confirm(
                    "경기 결과를 수정하시겠습니까?\n\n"
                    + "수정하면 기존 NEXON 연결과 "
                    + "선수 기록/MVP가 초기화됩니다."
                );


            if (!isConfirmed) {
                return;
            }


            const adminToken =
                getAdminToken();


            adminResultEditSaveButtonElement
                .disabled = true;


            adminResultEditMessageElement
                .textContent =
                    "저장 중...";


            try {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + `/api/admin/series/`
                        + `${editingAdminResult.series_id}`
                        + "/result",
                        {
                            method: "PUT",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "X-Admin-Token":
                                    adminToken,
                            },

                            body:
                                JSON.stringify(
                                    requestBody
                                ),
                        }
                    );


                const responseData =
                    await response.json();


                if (
                    response.status
                    === 401
                ) {

                    sessionStorage
                        .removeItem(
                            adminTokenStorageKey
                        );


                    closeAdminResultEdit();

                    showAdminLogin();

                    return;
                }


                if (!response.ok) {

                    throw new Error(
                        responseData.detail
                        ?? "경기 결과 수정 실패"
                    );
                }


                closeAdminResultEdit();


                await loadAdminResults();


                if (
                    responseData
                        .progression_warning
                ) {

                    alert(
                        responseData
                            .progression_warning
                    );
                }


            } catch (error) {

                console.error(
                    error
                );


                adminResultEditMessageElement
                    .textContent =
                        error.message;


            } finally {

                adminResultEditSaveButtonElement
                    .disabled = false;
            }
        }
    );

// 이벤트
adminResultEditCancelButtonElement
    .addEventListener(
        "click",
        closeAdminResultEdit
    );

adminScheduleEditCancelButtonElement
    .addEventListener(
        "click",
        closeAdminScheduleEdit
    );

// =========================================
// 선수 사진 요청 관리
// =========================================

function getAdminPhotoRequestStatusText(
    requestStatus
) {

    const statusTextMap = {
        pending:
            "대기중",

        in_progress:
            "처리중",

        completed:
            "완료",

        rejected:
            "반려",
    };


    return (
        statusTextMap[
            requestStatus
        ]
        ?? requestStatus
    );

}


function formatAdminPhotoRequestDate(
    dateValue
) {

    if (!dateValue) {
        return "-";
    }


    const date =
        new Date(
            dateValue
        );


    return date.toLocaleString(
        "ko-KR",
        {
            timeZone:
                "Asia/Seoul",

            year:
                "numeric",

            month:
                "2-digit",

            day:
                "2-digit",

            hour:
                "2-digit",

            minute:
                "2-digit",
        }
    );

}


// =========================================
// 요청 목록 조회
// =========================================

async function loadAdminPhotoRequests() {

    adminPhotoRequestListElement
        .textContent =
            "선수 사진 요청을 불러오는 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/community/player-photo-requests`
            );


        const requests =
            await response.json();


        if (!response.ok) {

            throw new Error(
                requests.detail
                ?? "선수 사진 요청 조회 실패"
            );

        }


        renderAdminPhotoRequests(
            requests
        );

    } catch (error) {

        console.error(
            error
        );


        adminPhotoRequestListElement
            .textContent =
                error.message;

    }

}


// =========================================
// 요청 목록 출력
// =========================================

function renderAdminPhotoRequests(
    requests
) {

    adminPhotoRequestListElement
        .innerHTML = "";


    if (
        requests.length === 0
    ) {

        adminPhotoRequestListElement
            .textContent =
                "등록된 선수 사진 요청이 없습니다.";

        return;

    }


    requests.forEach(
        (request) => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.classList.add(
                "admin-photo-request-card"
            );


            cardElement.dataset.postId =
                request.id;


            // =========================
            // 상단
            // =========================

            const headerElement =
                document.createElement(
                    "div"
                );

            headerElement.classList.add(
                "admin-photo-request-header"
            );


            const titleAreaElement =
                document.createElement(
                    "div"
                );


            const playerElement =
                document.createElement(
                    "strong"
                );

            playerElement.classList.add(
                "admin-photo-request-player"
            );

            playerElement.textContent =
                request.player_name;


            const seasonElement =
                document.createElement(
                    "span"
                );

            seasonElement.classList.add(
                "admin-photo-request-season"
            );

            seasonElement.textContent =
                request.season_name
                || "시즌 미입력";


            titleAreaElement.append(
                playerElement,
                seasonElement
            );


            const statusBadgeElement =
                document.createElement(
                    "span"
                );

            statusBadgeElement.classList.add(
                "admin-photo-request-status",
                `admin-photo-request-status-${request.request_status}`
            );

            statusBadgeElement.textContent =
                getAdminPhotoRequestStatusText(
                    request.request_status
                );


            headerElement.append(
                titleAreaElement,
                statusBadgeElement
            );


            // =========================
            // 기본 정보
            // =========================

            const metaElement =
                document.createElement(
                    "div"
                );

            metaElement.classList.add(
                "admin-photo-request-meta"
            );


            const authorElement =
                document.createElement(
                    "span"
                );

            authorElement.textContent =
                `작성자 ${request.author_name}`;


            const dateElement =
                document.createElement(
                    "span"
                );

            dateElement.textContent =
                formatAdminPhotoRequestDate(
                    request.created_at
                );


            const attachmentElement =
                document.createElement(
                    "span"
                );

            attachmentElement.textContent =
                `첨부 ${request.attachment_count}장`;


            metaElement.append(
                authorElement,
                dateElement,
                attachmentElement
            );


            // =========================
            // 상태 선택
            // =========================

            const fieldsElement =
                document.createElement(
                    "div"
                );

            fieldsElement.classList.add(
                "admin-photo-request-fields"
            );


            const statusLabelElement =
                document.createElement(
                    "label"
                );

            statusLabelElement.textContent =
                "처리 상태";


            const statusSelectElement =
                document.createElement(
                    "select"
                );

            statusSelectElement.classList.add(
                "admin-photo-request-status-select"
            );


            const statuses = [
                {
                    value:
                        "pending",

                    label:
                        "대기중",
                },

                {
                    value:
                        "in_progress",

                    label:
                        "처리중",
                },

                {
                    value:
                        "completed",

                    label:
                        "완료",
                },

                {
                    value:
                        "rejected",

                    label:
                        "반려",
                },
            ];


            statuses.forEach(
                (status) => {

                    const optionElement =
                        document.createElement(
                            "option"
                        );

                    optionElement.value =
                        status.value;

                    optionElement.textContent =
                        status.label;

                    optionElement.selected =
                        status.value
                        === request.request_status;


                    statusSelectElement.appendChild(
                        optionElement
                    );

                }
            );


            statusLabelElement.appendChild(
                statusSelectElement
            );


            // =========================
            // 관리자 메모
            // =========================

            const noteLabelElement =
                document.createElement(
                    "label"
                );

            noteLabelElement.textContent =
                "관리자 메모";


            const noteTextareaElement =
                document.createElement(
                    "textarea"
                );

            noteTextareaElement.classList.add(
                "admin-photo-request-note"
            );

            noteTextareaElement.rows =
                4;

            noteTextareaElement.placeholder =
                "처리 내용이나 반려 사유를 입력해주세요.";

            noteTextareaElement.value =
                request.admin_note
                ?? "";


            noteLabelElement.appendChild(
                noteTextareaElement
            );


            fieldsElement.append(
                statusLabelElement,
                noteLabelElement
            );


            // =========================
            // 하단 액션
            // =========================

            const actionsElement =
                document.createElement(
                    "div"
                );

            actionsElement.classList.add(
                "admin-photo-request-actions"
            );


            const messageElement =
                document.createElement(
                    "span"
                );

            messageElement.classList.add(
                "admin-photo-request-message"
            );


            const buttonAreaElement =
                document.createElement(
                    "div"
                );

            buttonAreaElement.classList.add(
                "admin-photo-request-buttons"
            );


            const detailLinkElement =
                document.createElement(
                    "a"
                );

            detailLinkElement.href =
                `./player-photo-request-detail.html?id=${request.id}`;

            detailLinkElement.target =
                "_blank";

            detailLinkElement.rel =
                "noopener";

            detailLinkElement.classList.add(
                "admin-photo-request-detail-button"
            );

            detailLinkElement.textContent =
                "상세보기";


            const saveButtonElement =
                document.createElement(
                    "button"
                );

            saveButtonElement.type =
                "button";

            saveButtonElement.classList.add(
                "admin-photo-request-save-button"
            );

            saveButtonElement.textContent =
                "저장";


            saveButtonElement.addEventListener(
                "click",
                () => {

                    saveAdminPhotoRequest(
                        request.id,
                        statusSelectElement,
                        noteTextareaElement,
                        saveButtonElement,
                        messageElement
                    );

                }
            );


            buttonAreaElement.append(
                detailLinkElement,
                saveButtonElement
            );


            actionsElement.append(
                messageElement,
                buttonAreaElement
            );


            cardElement.append(
                headerElement,
                metaElement,
                fieldsElement,
                actionsElement
            );


            adminPhotoRequestListElement
                .appendChild(
                    cardElement
                );

        }
    );

}


// =========================================
// 요청 상태 / 관리자 메모 저장
// =========================================

async function saveAdminPhotoRequest(
    postId,
    statusSelectElement,
    noteTextareaElement,
    saveButtonElement,
    messageElement
) {

    const adminToken =
        getAdminToken();


    if (!adminToken) {

        showAdminLogin();

        return;

    }


    const requestStatus =
        statusSelectElement
            .value;

    const adminNote =
        noteTextareaElement
            .value
            .trim();


    saveButtonElement.disabled =
        true;

    messageElement.textContent =
        "저장 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/community/player-photo-requests/`
                + `${postId}`,
                {
                    method:
                        "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-Admin-Token":
                            adminToken,
                    },

                    body:
                        JSON.stringify({
                            request_status:
                                requestStatus,

                            admin_note:
                                adminNote,
                        }),
                }
            );


        const responseData =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;

        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ?? "요청 저장 실패"
            );

        }


        messageElement.textContent =
            "저장되었습니다.";


        await loadAdminPhotoRequests();


    } catch (error) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


    } finally {

        saveButtonElement.disabled =
            false;

    }

}

// =========================================
// 회원 관리
// =========================================

async function loadAdminUsers() {

    const adminToken =
        getAdminToken();


    if (!adminToken) {
        return;
    }


    adminUserListElement
        .textContent =
            "회원 정보를 불러오는 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/admin/users`,
            {
                headers: {
                    "X-Admin-Token":
                        adminToken,
                },
            }
        );


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        const responseData =
            await response.json();


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "회원 조회에 실패했습니다."
            );
        }


        renderAdminUsers(
            responseData.users
            ?? []
        );


    } catch (error) {

        console.error(
            error
        );


        adminUserListElement
            .textContent =
                error.message;

    }
}


// =========================================
// 회원 목록 출력
// =========================================

function renderAdminUsers(
    users
) {

    adminUserListElement
        .innerHTML = "";


    if (
        users.length === 0
    ) {

        adminUserListElement
            .textContent =
                "가입된 회원이 없습니다.";

        return;
    }


    users.forEach(
        user => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.classList.add(
                "admin-user-card"
            );


            cardElement.dataset.userId =
                user.id;


            // -------------------------
            // 회원 기본정보
            // -------------------------

            const infoElement =
                document.createElement(
                    "div"
                );


            infoElement.classList.add(
                "admin-user-info"
            );


            const nameRowElement =
                document.createElement(
                    "div"
                );


            nameRowElement.classList.add(
                "admin-user-name-row"
            );


            const nicknameElement =
                document.createElement(
                    "strong"
                );


            nicknameElement.textContent =
                user.nickname;


            const roleBadgeElement =
                document.createElement(
                    "span"
                );


            roleBadgeElement.classList.add(
                "admin-user-role"
            );


            if (
                user.is_admin
            ) {

                roleBadgeElement
                    .classList
                    .add(
                        "administrator"
                    );

                roleBadgeElement
                    .textContent =
                        "ADMIN";

            } else {

                roleBadgeElement
                    .textContent =
                        "MEMBER";

            }


            nameRowElement.append(
                nicknameElement,
                roleBadgeElement
            );


            const emailElement =
                document.createElement(
                    "span"
                );


            emailElement.classList.add(
                "admin-user-email"
            );


            emailElement.textContent =
                user.email;


            const idElement =
                document.createElement(
                    "span"
                );


            idElement.classList.add(
                "admin-user-id"
            );


            idElement.textContent =
                `USER #${user.id}`;


            infoElement.append(
                nameRowElement,
                emailElement,
                idElement
            );


            // -------------------------
            // 포인트
            // -------------------------

            const pointElement =
                document.createElement(
                    "div"
                );


            pointElement.classList.add(
                "admin-user-point"
            );


            const pointLabelElement =
                document.createElement(
                    "span"
                );


            pointLabelElement.textContent =
                "보유 포인트";


            const pointValueElement =
                document.createElement(
                    "strong"
                );


            pointValueElement.textContent =
                `${Number(
                    user.points
                    ?? 0
                ).toLocaleString()} P`;


            pointElement.append(
                pointLabelElement,
                pointValueElement
            );


            // -------------------------
            // 포인트 조정
            // -------------------------

            const pointControlElement =
                document.createElement(
                    "div"
                );


            pointControlElement.classList.add(
                "admin-user-point-control"
            );


            const amountInputElement =
                document.createElement(
                    "input"
                );


            amountInputElement.type =
                "number";


            amountInputElement.classList.add(
                "admin-user-point-input"
            );


            amountInputElement.placeholder =
                "+5000 또는 -500";


            const descriptionInputElement =
                document.createElement(
                    "input"
                );


            descriptionInputElement.type =
                "text";


            descriptionInputElement.classList.add(
                "admin-user-point-description"
            );


            descriptionInputElement.placeholder =
                "포인트 변경 사유";


            descriptionInputElement.maxLength =
                200;


            const pointButtonElement =
                document.createElement(
                    "button"
                );


            pointButtonElement.type =
                "button";


            pointButtonElement.classList.add(
                "admin-user-point-button"
            );


            pointButtonElement.textContent =
                "포인트 반영";


            pointControlElement.append(
                amountInputElement,
                descriptionInputElement,
                pointButtonElement
            );


            // -------------------------
            // 권한
            // -------------------------

            const actionElement =
                document.createElement(
                    "div"
                );


            actionElement.classList.add(
                "admin-user-actions"
            );


            const roleButtonElement =
                document.createElement(
                    "button"
                );


            roleButtonElement.type =
                "button";


            roleButtonElement.classList.add(
                "admin-user-role-button"
            );


            if (
                user.is_admin
            ) {

                roleButtonElement
                    .classList
                    .add(
                        "remove"
                    );

                roleButtonElement
                    .textContent =
                        "관리자 해제";

            } else {

                roleButtonElement
                    .textContent =
                        "관리자 지정";

            }


            const messageElement =
                document.createElement(
                    "span"
                );


            messageElement.classList.add(
                "admin-user-message"
            );


            actionElement.append(
                messageElement,
                roleButtonElement
            );


            // -------------------------
            // 이벤트
            // -------------------------

            pointButtonElement
                .addEventListener(
                    "click",
                    () => {

                        changeAdminUserPoints(
                            user,
                            amountInputElement,
                            descriptionInputElement,
                            pointButtonElement,
                            messageElement
                        );

                    }
                );


            roleButtonElement
                .addEventListener(
                    "click",
                    () => {

                        changeAdminUserRole(
                            user,
                            roleButtonElement,
                            messageElement
                        );

                    }
                );


            cardElement.append(
                infoElement,
                pointElement,
                pointControlElement,
                actionElement
            );


            adminUserListElement.append(
                cardElement
            );

        }
    );

}


// =========================================
// 관리자 포인트 변경
// =========================================

async function changeAdminUserPoints(
    user,
    amountInputElement,
    descriptionInputElement,
    buttonElement,
    messageElement
) {

    const amount =
        Number(
            amountInputElement.value
        );


    if (
        !Number.isInteger(
            amount
        )
        ||
        amount === 0
    ) {

        messageElement.textContent =
            "0이 아닌 정수 포인트를 입력해주세요.";

        return;
    }


    const description =
        descriptionInputElement
            .value
            .trim();


    const actionText =
        amount > 0
            ? "지급"
            : "차감";


    const confirmed =
        window.confirm(
            `${user.nickname} 회원에게 `
            + `${Math.abs(
                amount
            ).toLocaleString()}P를 `
            + `${actionText}하시겠습니까?`
        );


    if (!confirmed) {
        return;
    }


    const adminToken =
        getAdminToken();


    buttonElement.disabled =
        true;


    messageElement.textContent =
        "처리 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}`
            + `/api/admin/users/${user.id}/points`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-Admin-Token":
                        adminToken,
                },

                body: JSON.stringify({
                    amount:
                        amount,

                    description:
                        description
                        || null,
                }),
            }
        );


        const responseData =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "포인트 변경에 실패했습니다."
            );
        }


        await loadAdminUsers();


    } catch (error) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


        buttonElement.disabled =
            false;

    }

}


// =========================================
// 관리자 권한 변경
// =========================================

async function changeAdminUserRole(
    user,
    buttonElement,
    messageElement
) {

    const nextAdminState =
        !user.is_admin;


    const actionText =
        nextAdminState
            ? "관리자로 지정"
            : "관리자 권한을 해제";


    const confirmed =
        window.confirm(
            `${user.nickname} 회원을 `
            + `${actionText}하시겠습니까?`
        );


    if (!confirmed) {
        return;
    }


    const adminToken =
        getAdminToken();


    buttonElement.disabled =
        true;


    messageElement.textContent =
        "처리 중...";


    try {

        const response = await fetch(
            `${apiBaseUrl}`
            + `/api/admin/users/${user.id}/role`,
            {
                method:
                    "PATCH",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-Admin-Token":
                        adminToken,
                },

                body: JSON.stringify({
                    is_admin:
                        nextAdminState,
                }),
            }
        );


        const responseData =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "관리자 권한 변경에 실패했습니다."
            );
        }


        await loadAdminUsers();


    } catch (error) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


        buttonElement.disabled =
            false;

    }

}

// =========================================
// POINT SHOP
// HTML escape
// =========================================

function escapeAdminHtml(
    value
) {

    return String(
        value ?? ""
    )
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            "\"",
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );

}


// =========================================
// POINT SHOP
// 상품 조회
// =========================================

async function loadAdminPointShopProducts() {

    const adminToken =
        getAdminToken();


    if (!adminToken) {
        return;
    }


    adminPointShopProductListElement
        .textContent =
            "상품을 불러오는 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + "/api/admin/point-shop/products",
                {
                    headers: {
                        "X-Admin-Token":
                            adminToken,
                    },
                }
            );


        const data =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;
        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "교환 상품 조회 실패"
            );

        }


        renderAdminPointShopProducts(
            data
        );


    } catch (
        error
    ) {

        console.error(
            error
        );


        adminPointShopProductListElement
            .textContent =
                error.message;

    }

}


// =========================================
// POINT SHOP
// 상품 출력
// =========================================

function renderAdminPointShopProducts(
    products
) {

    adminPointShopProductListElement
        .innerHTML = "";


    if (
        products.length
        === 0
    ) {

        adminPointShopProductListElement
            .textContent =
                "등록된 교환 상품이 없습니다.";

        return;

    }


    products.forEach(
        (product) => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.className =
                "admin-point-shop-product-card";


            cardElement.dataset.productId =
                product.id;


            cardElement.innerHTML = `
                <div
                    class="admin-point-shop-product-card-header"
                >

                    <div>

                        <strong>
                            ${escapeAdminHtml(
                                product.name
                            )}
                        </strong>

                        <span>
                            상품 ID #${product.id}
                        </span>

                    </div>

                    <span
                        class="
                            admin-point-shop-status
                            ${
                                product.is_active
                                    ? "active"
                                    : "inactive"
                            }
                        "
                    >
                        ${
                            product.is_active
                                ? "판매 중"
                                : "판매 중지"
                        }
                    </span>

                </div>


                <div
                    class="admin-point-shop-edit-grid"
                >

                    <label>
                        상품명

                        <input
                            type="text"
                            class="admin-point-shop-edit-name"
                            value="${escapeAdminHtml(
                                product.name
                            )}"
                        >
                    </label>


                    <label>
                        카테고리

                        <input
                            type="text"
                            class="admin-point-shop-edit-category"
                            value="${escapeAdminHtml(
                                product.category
                                ?? ""
                            )}"
                        >
                    </label>


                    <label>
                        필요 포인트

                        <input
                            type="number"
                            min="1"
                            class="admin-point-shop-edit-price"
                            value="${product.price_points}"
                        >
                    </label>


                    <label>
                        정렬 순서

                        <input
                            type="number"
                            min="0"
                            class="admin-point-shop-edit-sort-order"
                            value="${product.sort_order}"
                        >
                    </label>


                    <label
                        class="admin-point-shop-wide"
                    >
                        이미지 경로 / URL

                        <input
                            type="text"
                            class="admin-point-shop-edit-image-url"
                            value="${escapeAdminHtml(
                                product.image_url
                                ?? ""
                            )}"
                        >
                    </label>


                    <label
                        class="admin-point-shop-wide"
                    >
                        상품 설명

                        <textarea
                            rows="3"
                            class="admin-point-shop-edit-description"
                        >${escapeAdminHtml(
                            product.description
                            ?? ""
                        )}</textarea>
                    </label>

                </div>


                <div
                    class="admin-point-shop-card-actions"
                >

                    <label>

                        <input
                            type="checkbox"
                            class="admin-point-shop-edit-active"
                            ${
                                product.is_active
                                    ? "checked"
                                    : ""
                            }
                        >

                        판매 중

                    </label>


                    <span
                        class="admin-point-shop-card-message"
                    ></span>


                    <button
                        type="button"
                        class="admin-point-shop-save-button"
                    >
                        저장
                    </button>

                </div>
            `;


            const saveButtonElement =
                cardElement.querySelector(
                    ".admin-point-shop-save-button"
                );


            saveButtonElement.addEventListener(
                "click",
                () => {

                    saveAdminPointShopProduct(
                        cardElement
                    );

                }
            );


            adminPointShopProductListElement
                .appendChild(
                    cardElement
                );

        }
    );

}


// =========================================
// POINT SHOP
// 상품 등록
// =========================================

adminPointShopFormElement.addEventListener(
    "submit",
    async (
        event
    ) => {

        event.preventDefault();


        const name =
            adminPointShopNameElement
                .value
                .trim();


        const pricePoints =
            Number(
                adminPointShopPriceElement
                    .value
            );


        const sortOrder =
            Number(
                adminPointShopSortOrderElement
                    .value
            );


        if (!name) {

            adminPointShopFormMessageElement
                .textContent =
                    "상품명을 입력해주세요.";

            return;

        }


        if (
            !Number.isInteger(
                pricePoints
            )
            ||
            pricePoints <= 0
        ) {

            adminPointShopFormMessageElement
                .textContent =
                    "필요 포인트를 확인해주세요.";

            return;

        }


        if (
            !Number.isInteger(
                sortOrder
            )
            ||
            sortOrder < 0
        ) {

            adminPointShopFormMessageElement
                .textContent =
                    "정렬 순서를 확인해주세요.";

            return;

        }


        const adminToken =
            getAdminToken();


        adminPointShopCreateButtonElement
            .disabled = true;


        adminPointShopFormMessageElement
            .textContent =
                "등록 중...";


        try {

            const response =
                await fetch(
                    `${apiBaseUrl}`
                    + "/api/admin/point-shop/products",
                    {
                        method:
                            "POST",

                        headers: {
                            "Content-Type":
                                "application/json",

                            "X-Admin-Token":
                                adminToken,
                        },

                        body:
                            JSON.stringify({
                                name:
                                    name,

                                category:
                                    (
                                        adminPointShopCategoryElement
                                            .value
                                            .trim()
                                        ||
                                        null
                                    ),

                                description:
                                    (
                                        adminPointShopDescriptionElement
                                            .value
                                            .trim()
                                        ||
                                        null
                                    ),

                                price_points:
                                    pricePoints,

                                image_url:
                                    (
                                        adminPointShopImageUrlElement
                                            .value
                                            .trim()
                                        ||
                                        null
                                    ),

                                is_active:
                                    adminPointShopActiveElement
                                        .checked,

                                sort_order:
                                    sortOrder,
                            }),
                    }
                );


            const data =
                await response.json();


            if (
                response.status
                === 401
            ) {

                sessionStorage.removeItem(
                    adminTokenStorageKey
                );

                showAdminLogin();

                return;

            }


            if (!response.ok) {

                throw new Error(
                    data.detail
                    ??
                    "상품 등록 실패"
                );

            }


            adminPointShopFormElement
                .reset();


            adminPointShopSortOrderElement
                .value = "0";


            adminPointShopActiveElement
                .checked = true;


            adminPointShopFormMessageElement
                .textContent =
                    "상품이 등록되었습니다.";


            await loadAdminPointShopProducts();


        } catch (
            error
        ) {

            console.error(
                error
            );


            adminPointShopFormMessageElement
                .textContent =
                    error.message;


        } finally {

            adminPointShopCreateButtonElement
                .disabled = false;

        }

    }
);


// =========================================
// POINT SHOP
// 상품 수정
// =========================================

async function saveAdminPointShopProduct(
    cardElement
) {

    const productId =
        Number(
            cardElement.dataset
                .productId
        );


    const name =
        cardElement
            .querySelector(
                ".admin-point-shop-edit-name"
            )
            .value
            .trim();


    const category =
        cardElement
            .querySelector(
                ".admin-point-shop-edit-category"
            )
            .value
            .trim();


    const pricePoints =
        Number(
            cardElement
                .querySelector(
                    ".admin-point-shop-edit-price"
                )
                .value
        );


    const sortOrder =
        Number(
            cardElement
                .querySelector(
                    ".admin-point-shop-edit-sort-order"
                )
                .value
        );


    const imageUrl =
        cardElement
            .querySelector(
                ".admin-point-shop-edit-image-url"
            )
            .value
            .trim();


    const description =
        cardElement
            .querySelector(
                ".admin-point-shop-edit-description"
            )
            .value
            .trim();


    const isActive =
        cardElement
            .querySelector(
                ".admin-point-shop-edit-active"
            )
            .checked;


    const messageElement =
        cardElement
            .querySelector(
                ".admin-point-shop-card-message"
            );


    const saveButtonElement =
        cardElement
            .querySelector(
                ".admin-point-shop-save-button"
            );


    if (!name) {

        messageElement.textContent =
            "상품명을 입력해주세요.";

        return;

    }


    if (
        !Number.isInteger(
            pricePoints
        )
        ||
        pricePoints <= 0
    ) {

        messageElement.textContent =
            "포인트를 확인해주세요.";

        return;

    }


    if (
        !Number.isInteger(
            sortOrder
        )
        ||
        sortOrder < 0
    ) {

        messageElement.textContent =
            "정렬 순서를 확인해주세요.";

        return;

    }


    const adminToken =
        getAdminToken();


    saveButtonElement.disabled =
        true;


    messageElement.textContent =
        "저장 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/point-shop/products/${productId}`,
                {
                    method:
                        "PATCH",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-Admin-Token":
                            adminToken,
                    },

                    body:
                        JSON.stringify({
                            name:
                                name,

                            category:
                                category
                                || null,

                            description:
                                description
                                || null,

                            price_points:
                                pricePoints,

                            image_url:
                                imageUrl
                                || null,

                            is_active:
                                isActive,

                            sort_order:
                                sortOrder,
                        }),
                }
            );


        const data =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );

            showAdminLogin();

            return;

        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "상품 수정 실패"
            );

        }


        await loadAdminPointShopProducts();


    } catch (
        error
    ) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


    } finally {

        saveButtonElement.disabled =
            false;

    }

}

// =========================================
// POINT SHOP
// 교환 상태 표시
// =========================================

function getPointShopExchangeStatusText(
    status
) {

    if (
        status === "requested"
    ) {
        return "처리 대기";
    }


    if (
        status === "completed"
    ) {
        return "처리 완료";
    }


    if (
        status === "cancelled"
    ) {
        return "취소";
    }


    return status;

}


// =========================================
// POINT SHOP
// 날짜 표시
// =========================================

function formatPointShopDateTime(
    dateText
) {

    if (!dateText) {
        return "-";
    }


    const date =
        new Date(
            dateText
        );


    return date.toLocaleString(
        "ko-KR"
    );

}


// =========================================
// POINT SHOP
// 교환 신청 조회
// =========================================

async function loadAdminPointShopExchanges() {

    const adminToken =
        getAdminToken();


    if (!adminToken) {
        return;
    }


    adminPointShopExchangeListElement
        .textContent =
            "교환 신청을 불러오는 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + "/api/admin/point-shop/exchanges",
                {
                    headers: {
                        "X-Admin-Token":
                            adminToken,
                    },
                }
            );


        const data =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );


            showAdminLogin();

            return;

        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "교환 신청 조회 실패"
            );

        }


        renderAdminPointShopExchanges(
            data
        );


    } catch (
        error
    ) {

        console.error(
            error
        );


        adminPointShopExchangeListElement
            .textContent =
                error.message;

    }

}


// =========================================
// POINT SHOP
// 교환 신청 출력
// =========================================

function renderAdminPointShopExchanges(
    exchanges
) {

    adminPointShopExchangeListElement
        .innerHTML = "";


    if (
        exchanges.length
        === 0
    ) {

        adminPointShopExchangeListElement
            .textContent =
                "아직 교환 신청이 없습니다.";

        return;

    }


    exchanges.forEach(
        (exchange) => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.className =
                "admin-point-shop-exchange-card";


            const isRequested =
                exchange.status
                === "requested";


            cardElement.innerHTML = `
                <div
                    class="admin-point-shop-exchange-top"
                >

                    <div>

                        <span
                            class="
                                admin-point-shop-exchange-status
                                ${exchange.status}
                            "
                        >
                            ${getPointShopExchangeStatusText(
                                exchange.status
                            )}
                        </span>

                        <strong>
                            ${escapeAdminHtml(
                                exchange.product_name
                            )}
                        </strong>

                    </div>


                    <strong
                        class="admin-point-shop-exchange-price"
                    >
                        ${Number(
                            exchange.price_points
                        ).toLocaleString(
                            "ko-KR"
                        )} P
                    </strong>

                </div>


                <div
                    class="admin-point-shop-exchange-info"
                >

                    <div>
                        <span>
                            신청자
                        </span>

                        <strong>
                            ${escapeAdminHtml(
                                exchange.nickname
                            )}
                        </strong>
                    </div>


                    <div>
                        <span>
                            이메일
                        </span>

                        <strong>
                            ${escapeAdminHtml(
                                exchange.email
                            )}
                        </strong>
                    </div>


                    <div>
                        <span>
                            신청일
                        </span>

                        <strong>
                            ${formatPointShopDateTime(
                                exchange.created_at
                            )}
                        </strong>
                    </div>


                    <div>
                        <span>
                            처리일
                        </span>

                        <strong>
                            ${formatPointShopDateTime(
                                exchange.completed_at
                            )}
                        </strong>
                    </div>

                </div>


                <div
                    class="admin-point-shop-exchange-actions"
                >

                    <span
                        class="admin-point-shop-card-message"
                    ></span>


                    ${
                        isRequested
                            ?
                            `
                                <button
                                    type="button"
                                    class="admin-point-shop-complete-button"
                                >
                                    처리 완료
                                </button>
                            `
                            :
                            ""
                    }

                </div>
            `;


            if (
                isRequested
            ) {

                const completeButtonElement =
                    cardElement.querySelector(
                        ".admin-point-shop-complete-button"
                    );


                completeButtonElement
                    .addEventListener(
                        "click",
                        () => {

                            completeAdminPointShopExchange(
                                exchange,
                                cardElement
                            );

                        }
                    );

            }


            adminPointShopExchangeListElement
                .appendChild(
                    cardElement
                );

        }
    );

}


// =========================================
// POINT SHOP
// 교환 처리 완료
// =========================================

async function completeAdminPointShopExchange(
    exchange,
    cardElement
) {

    const confirmed =
        confirm(
            `${exchange.nickname}님의\n`
            +
            `${exchange.product_name}\n\n`
            +
            "상품 전달을 완료했습니까?"
        );


    if (!confirmed) {
        return;
    }


    const buttonElement =
        cardElement.querySelector(
            ".admin-point-shop-complete-button"
        );


    const messageElement =
        cardElement.querySelector(
            ".admin-point-shop-card-message"
        );


    buttonElement.disabled =
        true;


    buttonElement.textContent =
        "처리 중...";


    messageElement.textContent =
        "";


    try {

        const adminToken =
            getAdminToken();


        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/point-shop/exchanges/`
                + `${exchange.id}/complete`,
                {
                    method:
                        "PATCH",

                    headers: {
                        "X-Admin-Token":
                            adminToken,
                    },
                }
            );


        const data =
            await response.json();


        if (
            response.status
            === 401
        ) {

            sessionStorage.removeItem(
                adminTokenStorageKey
            );


            showAdminLogin();

            return;

        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "교환 처리 실패"
            );

        }


        await loadAdminPointShopExchanges();


    } catch (
        error
    ) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


        buttonElement.disabled =
            false;


        buttonElement.textContent =
            "처리 완료";

    }

}


// =========================================
// 최초 실행
// =========================================

checkAdminSession();