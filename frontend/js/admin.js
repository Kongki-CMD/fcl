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

const adminResultListElement =
    document.querySelector(
        "#admin-result-list"
    );

const adminScheduleListElement =
    document.querySelector(
        "#admin-schedule-list"
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


const adminEditSet1AElement =
    document.querySelector(
        "#admin-edit-set1-a"
    );

const adminEditSet1BElement =
    document.querySelector(
        "#admin-edit-set1-b"
    );

const adminEditSet2AElement =
    document.querySelector(
        "#admin-edit-set2-a"
    );

const adminEditSet2BElement =
    document.querySelector(
        "#admin-edit-set2-b"
    );

const adminEditSet3AElement =
    document.querySelector(
        "#admin-edit-set3-a"
    );

const adminEditSet3BElement =
    document.querySelector(
        "#admin-edit-set3-b"
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
// 경기 결과 수정 열기
// =========================================

function openAdminResultEdit(
    result
) {

    const sets =
        result.sets ?? [];


    if (sets.length !== 3) {

        alert(
            "현재는 3세트 경기만 "
            + "수정할 수 있습니다."
        );

        return;
    }


    if (!result.series_id) {

        alert(
            "수정할 수 없는 경기입니다."
        );

        return;
    }


    editingAdminResult =
        result;


    adminResultEditTitleElement
        .textContent =
            `${result.team_a}`
            + " VS "
            + `${result.team_b}`;


    adminEditSet1AElement.value =
        sets[0].team_a_score;

    adminEditSet1BElement.value =
        sets[0].team_b_score;


    adminEditSet2AElement.value =
        sets[1].team_a_score;

    adminEditSet2BElement.value =
        sets[1].team_b_score;


    adminEditSet3AElement.value =
        sets[2].team_a_score;

    adminEditSet3BElement.value =
        sets[2].team_b_score;


    adminResultEditMessageElement
        .textContent = "";


    adminResultEditModalElement
        .classList.remove(
            "hidden"
        );
}

// =========================================
// 경기 결과 수정 닫기
// =========================================

function closeAdminResultEdit() {

    editingAdminResult =
        null;


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


            const set1TeamA =
                Number(
                    adminEditSet1AElement.value
                );

            const set1TeamB =
                Number(
                    adminEditSet1BElement.value
                );

            const set2TeamA =
                Number(
                    adminEditSet2AElement.value
                );

            const set2TeamB =
                Number(
                    adminEditSet2BElement.value
                );

            const set3TeamA =
                Number(
                    adminEditSet3AElement.value
                );

            const set3TeamB =
                Number(
                    adminEditSet3BElement.value
                );


            const scores = [
                set1TeamA,
                set1TeamB,
                set2TeamA,
                set2TeamB,
                set3TeamA,
                set3TeamB,
            ];


            if (
                scores.some(
                    score =>
                        !Number.isInteger(score)
                        ||
                        score < 0
                )
            ) {

                adminResultEditMessageElement
                    .textContent =
                        "점수는 0 이상의 정수여야 합니다.";

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
                                JSON.stringify({
                                    set1_team_a:
                                        set1TeamA,

                                    set1_team_b:
                                        set1TeamB,

                                    set2_team_a:
                                        set2TeamA,

                                    set2_team_b:
                                        set2TeamB,

                                    set3_team_a:
                                        set3TeamA,

                                    set3_team_b:
                                        set3TeamB,
                                }),
                        }
                    );


                const responseData =
                    await response.json();


                if (response.status === 401) {

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
// 최초 실행
// =========================================

checkAdminSession();