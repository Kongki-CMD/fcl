import {
    apiBaseUrl,
    loadFclSeasons,
} from "./config.js?v=season-default-1";

import {
    getCurrentUser,
    getUserToken,
} from "./auth.js";

const seasonLabelElement =
    document.querySelector(
        "#draft-season-label"
    );

const connectionElement =
    document.querySelector(
        "#draft-connection"
    );

const connectionTextElement =
    document.querySelector(
        "#draft-connection-text"
    );

const messagePanelElement =
    document.querySelector(
        "#draft-message-panel"
    );

const messageTitleElement =
    document.querySelector(
        "#draft-message-title"
    );

const messageDescriptionElement =
    document.querySelector(
        "#draft-message-description"
    );

const draftContentElement =
    document.querySelector(
        "#draft-content"
    );

const currentActionElement =
    document.querySelector(
        "#draft-current-action"
    );

const currentParticipantElement =
    document.querySelector(
        "#draft-current-participant"
    );

const currentDescriptionElement =
    document.querySelector(
        "#draft-current-description"
    );

const turnTimerElement =
    document.querySelector(
        "#draft-turn-timer"
    );

const turnTimerTextElement =
    document.querySelector(
        "#draft-turn-timer-text"
    );

const adminControlsElement =
    document.querySelector(
        "#draft-admin-controls"
    );

const banPhaseSettingElement =
    document.querySelector(
        "#draft-ban-phase-setting"
    );


const banPhaseCheckboxElement =
    document.querySelector(
        "#draft-ban-phase-checkbox"
    );

const startButtonElement =
    document.querySelector(
        "#draft-start-button"
    );

const pauseButtonElement =
    document.querySelector(
        "#draft-pause-button"
    );

const resumeButtonElement =
    document.querySelector(
        "#draft-resume-button"
    );

const progressTextElement =
    document.querySelector(
        "#draft-progress-text"
    );

const progressBarElement =
    document.querySelector(
        "#draft-progress-bar"
    );

const phaseTextElement =
    document.querySelector(
        "#draft-phase-text"
    );

const statusTextElement =
    document.querySelector(
        "#draft-status-text"
    );

const participantListElement =
    document.querySelector(
        "#draft-participant-list"
    );


const clubSearchElement =
    document.querySelector(
        "#draft-club-search"
    );


const leagueFilterElement =
    document.querySelector(
        "#draft-league-filter"
    );


const clubCountElement =
    document.querySelector(
        "#draft-club-count"
    );


const clubListElement =
    document.querySelector(
        "#draft-club-list"
    );


const actionListElement =
    document.querySelector(
        "#draft-action-list"
    );

const actionCountElement =
    document.querySelector(
        "#draft-action-count"
    );

const lastUpdateElement =
    document.querySelector(
        "#draft-last-update"
    );


let currentSeasonNumber = null;
let draftSocket = null;
let reconnectTimer = null;
let pageClosing = false;

const adminTokenStorageKey =
    "fclAdminToken";


let latestDraftState = null;

let draftActionSubmitting = false;

let currentUser = null;

let draftTimerIntervalId =
    null;

let draftControlSubmitting =
    false;

const draftEventChannelName =
    "fcl-draft-events";


const draftCompletionEventStorageKey =
    "fclDraftCompletionEvent";


const draftCompletionSentPrefix =
    "fclDraftCompletionSent:";


let draftEventChannel =
    null;


let lastDraftCompletionKey =
    null;


if (
    "BroadcastChannel"
    in window
) {

    draftEventChannel =
        new BroadcastChannel(
            draftEventChannelName
        );
}

// =========================
// INIT
// =========================

async function initializeDraftPage() {

    setConnectionStatus(
        "connecting",
        "연결 중"
    );


    try {

        currentUser =
            await getCurrentUser();


        currentSeasonNumber =
            await resolveDraftSeasonNumber();


        if (!currentSeasonNumber) {

            throw new Error(
                "표시할 시즌을 찾을 수 없습니다."
            );
        }


        seasonLabelElement.textContent =
            `SEASON ${currentSeasonNumber}`;


        await loadInitialDraftState();


        connectDraftWebSocket();


    } catch (error) {

        console.error(
            error
        );


        showMessage(
            "Draft 정보를 불러오지 못했습니다.",
            error.message
        );


        setConnectionStatus(
            "offline",
            "연결 실패"
        );
    }
}


async function resolveDraftSeasonNumber() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const requestedSeason =
        Number(
            params.get(
                "season"
            )
        );


    if (
        Number.isInteger(
            requestedSeason
        )
        &&
        requestedSeason > 0
    ) {

        return requestedSeason;
    }


    const seasons =
        await loadFclSeasons();


    if (
        !Array.isArray(
            seasons
        )
        ||
        seasons.length === 0
    ) {

        return null;
    }


    const sortedSeasons =
        [
            ...seasons,
        ].sort(
            (
                left,
                right
            ) => (
                Number(
                    right.season_number
                )
                -
                Number(
                    left.season_number
                )
            )
        );


    const upcomingSeason =
        sortedSeasons.find(
            season =>
                season.status
                === "upcoming"
        );


    if (upcomingSeason) {

        return Number(
            upcomingSeason
                .season_number
        );
    }


    const activeSeason =
        sortedSeasons.find(
            season =>
                season.status
                === "active"
        );


    if (activeSeason) {

        return Number(
            activeSeason
                .season_number
        );
    }


    return Number(
        sortedSeasons[0]
            .season_number
    );
}


// =========================
// INITIAL REST LOAD
// =========================

async function loadInitialDraftState() {

    const response =
        await fetch(
            `${apiBaseUrl}`
            + `/api/seasons/`
            + `${currentSeasonNumber}`
            + `/draft`
        );


    if (
        response.status === 404
    ) {

        showWaitingForDraft();

        return;
    }


    if (!response.ok) {

        const detail =
            await readResponseError(
                response
            );


        throw new Error(
            detail
        );
    }


    const draftState =
        await response.json();


    renderDraftState(
        draftState
    );
}


// =========================
// WEBSOCKET
// =========================

function connectDraftWebSocket() {

    clearTimeout(
        reconnectTimer
    );


    if (
        draftSocket
        &&
        (
            draftSocket.readyState
            === WebSocket.OPEN

            ||

            draftSocket.readyState
            === WebSocket.CONNECTING
        )
    ) {

        draftSocket.close();
    }


    setConnectionStatus(
        "connecting",
        "연결 중"
    );


    const socketUrl =
        buildDraftWebSocketUrl(
            currentSeasonNumber
        );


    const socket =
        new WebSocket(
            socketUrl
        );


    draftSocket =
        socket;


    socket.addEventListener(
        "open",
        () => {

            if (
                socket
                !== draftSocket
            ) {
                return;
            }


            setConnectionStatus(
                "live",
                "실시간 연결"
            );
        }
    );


    socket.addEventListener(
        "message",
        event => {

            if (
                socket
                !== draftSocket
            ) {
                return;
            }


            handleDraftSocketMessage(
                event.data
            );
        }
    );


    socket.addEventListener(
        "close",
        () => {

            if (
                socket
                !== draftSocket
            ) {
                return;
            }


            setConnectionStatus(
                "offline",
                "재연결 중"
            );


            if (pageClosing) {
                return;
            }


            reconnectTimer =
                setTimeout(
                    connectDraftWebSocket,
                    2000
                );
        }
    );


    socket.addEventListener(
        "error",
        error => {

            console.error(
                "Draft WebSocket 오류:",
                error
            );
        }
    );
}


function handleDraftSocketMessage(
    rawMessage
) {

    let message;


    try {

        message =
            JSON.parse(
                rawMessage
            );

    } catch (error) {

        console.error(
            "Draft WebSocket JSON 오류:",
            error
        );

        return;
    }


    if (
        message.type
        === "draft_state"
    ) {

        renderDraftState(
            message.data
        );

        return;
    }


    if (
        message.type
        === "draft_error"
    ) {

        if (
            Number(
                message.status_code
            )
            === 404
        ) {

            showWaitingForDraft();

            return;
        }


        showMessage(
            "Draft 오류",
            message.detail
            ?? "Draft 상태를 불러오지 못했습니다."
        );
    }
}


function buildDraftWebSocketUrl(
    seasonNumber
) {

    if (apiBaseUrl) {

        const apiUrl =
            new URL(
                apiBaseUrl
            );


        const protocol =
            apiUrl.protocol
            === "https:"
                ? "wss:"
                : "ws:";


        return (
            `${protocol}//`
            + `${apiUrl.host}`
            + `/ws/seasons/`
            + `${seasonNumber}`
            + `/draft`
        );
    }


    const protocol =
        window.location.protocol
        === "https:"
            ? "wss:"
            : "ws:";


    return (
        `${protocol}//`
        + `${window.location.host}`
        + `/ws/seasons/`
        + `${seasonNumber}`
        + `/draft`
    );
}

// =========================================
// TURN TIMER
// =========================================

function formatDraftTimer(
    totalSeconds
) {

    const safeSeconds =
        Math.max(
            0,
            Math.ceil(
                totalSeconds
            )
        );


    const minutes =
        Math.floor(
            safeSeconds / 60
        );


    const seconds =
        safeSeconds % 60;


    return (
        String(
            minutes
        ).padStart(
            2,
            "0"
        )
        +
        ":"
        +
        String(
            seconds
        ).padStart(
            2,
            "0"
        )
    );
}


function getDraftRemainingSeconds(
    draftSession
) {

    if (!draftSession) {
        return null;
    }


    const turnSeconds =
        Number(
            draftSession.turn_seconds
            ?? 0
        );


    if (
        !Number.isFinite(
            turnSeconds
        )
        ||
        turnSeconds <= 0
    ) {

        return null;
    }


    const status =
        draftSession.status;


    const turnStartedAt =
        draftSession.turn_started_at
            ? new Date(
                draftSession.turn_started_at
            )
            : null;


    if (
        !turnStartedAt
        ||
        Number.isNaN(
            turnStartedAt.getTime()
        )
    ) {

        return null;
    }


    // =========================
    // 진행 중
    // =========================

    if (
        status === "active"
    ) {

        const elapsedSeconds =
            (
                Date.now()
                -
                turnStartedAt.getTime()
            )
            /
            1000;


        return Math.max(
            0,
            turnSeconds
            -
            elapsedSeconds
        );
    }


    // =========================
    // 일시정지
    // =========================

    if (
        status === "paused"
    ) {

        // 자동 시간초과 정지
        if (
            !draftSession.paused_at
        ) {

            return 0;
        }


        const pausedAt =
            new Date(
                draftSession.paused_at
            );


        if (
            Number.isNaN(
                pausedAt.getTime()
            )
        ) {

            return 0;
        }


        const elapsedSeconds =
            (
                pausedAt.getTime()
                -
                turnStartedAt.getTime()
            )
            /
            1000;


        return Math.max(
            0,
            turnSeconds
            -
            elapsedSeconds
        );
    }


    return null;
}


function updateDraftTimer() {

    if (
        !turnTimerTextElement
    ) {

        return;
    }


    const draftSession =
        latestDraftState
            ?.draft_session;


    if (!draftSession) {

        turnTimerTextElement
            .textContent =
                "--:--";

        return;
    }


    if (
        draftSession.status
        === "completed"
        ||
        draftSession.status
        === "setup"
    ) {

        turnTimerTextElement
            .textContent =
                "--:--";

        turnTimerElement
            ?.classList.remove(
                "warning",
                "danger",
                "paused"
            );

        return;
    }


    const remainingSeconds =
        getDraftRemainingSeconds(
            draftSession
        );


    if (
        remainingSeconds
        === null
    ) {

        turnTimerTextElement
            .textContent =
                "--:--";

        return;
    }


    turnTimerTextElement
        .textContent =
            formatDraftTimer(
                remainingSeconds
            );


    turnTimerElement
        ?.classList.toggle(
            "paused",
            draftSession.status
            === "paused"
        );


    turnTimerElement
        ?.classList.toggle(
            "warning",
            remainingSeconds <= 20
            &&
            remainingSeconds > 10
        );


    turnTimerElement
        ?.classList.toggle(
            "danger",
            remainingSeconds <= 10
        );
}


function startDraftTimer() {

    if (
        draftTimerIntervalId
        !== null
    ) {

        clearInterval(
            draftTimerIntervalId
        );
    }


    updateDraftTimer();


    draftTimerIntervalId =
        window.setInterval(
            updateDraftTimer,
            250
        );
}

// =========================================
// ADMIN PAUSE / RESUME
// =========================================

function renderDraftAdminControls(
    draftSession
) {

    if (
        !adminControlsElement
        ||
        !banPhaseSettingElement
        ||
        !banPhaseCheckboxElement
        ||
        !startButtonElement
        ||
        !pauseButtonElement
        ||
        !resumeButtonElement
    ) {

        return;
    }


    const adminToken =
        getAdminToken();


    const userToken =
        getUserToken();


    const isAdminMember =
        Boolean(
            userToken
        )
        &&
        Boolean(
            currentUser
                ?.is_admin
        );


    const canControl =
        (
            Boolean(
                adminToken
            )
            ||
            isAdminMember
        )
        &&
        (
            draftSession.status
            === "setup"
            ||
            draftSession.status
            === "active"
            ||
            draftSession.status
            === "paused"
        );


    adminControlsElement
        .classList.toggle(
            "hidden",
            !canControl
        );


    if (!canControl) {

        banPhaseSettingElement
            .classList.add(
                "hidden"
            );

        startButtonElement
            .classList.add(
                "hidden"
            );

        pauseButtonElement
            .classList.add(
                "hidden"
            );

        resumeButtonElement
            .classList.add(
                "hidden"
            );

        return;
    }


    const isSetup =
        draftSession.status
        === "setup";


    banPhaseSettingElement
        .classList.toggle(
            "hidden",
            !isSetup
        );


    banPhaseCheckboxElement.checked =
        draftSession.ban_enabled
        !== false;


    banPhaseCheckboxElement.disabled =
        (
            !isSetup
            ||
            draftControlSubmitting
        );


    startButtonElement
        .classList.toggle(
            "hidden",
            !isSetup
        );


    pauseButtonElement
        .classList.toggle(
            "hidden",
            draftSession.status
            !== "active"
        );


    resumeButtonElement
        .classList.toggle(
            "hidden",
            draftSession.status
            !== "paused"
        );
}

async function updateDraftBanPhaseSetting(
    banEnabled
) {

    if (
        draftControlSubmitting
    ) {

        return;
    }


    if (
        !canCurrentUserControlDraft()
    ) {

        window.alert(
            "Draft 관리자 권한이 필요합니다."
        );

        return;
    }


    draftControlSubmitting =
        true;


    banPhaseCheckboxElement.disabled =
        true;

    startButtonElement.disabled =
        true;


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/seasons/`
                + `${currentSeasonNumber}`
                + `/draft/settings`,
                {
                    method:
                        "PATCH",

                    headers:
                        getDraftControlHeaders(
                            true
                        ),

                    body:
                        JSON.stringify(
                            {
                                ban_enabled:
                                    Boolean(
                                        banEnabled
                                    ),
                            }
                        ),
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


            throw new Error(
                "관리자 로그인이 만료되었습니다."
            );
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "Draft 설정 변경에 실패했습니다."
            );
        }


        await loadInitialDraftState();


    } catch (error) {

        console.error(
            error
        );


        window.alert(
            error.message
        );


        if (latestDraftState) {

            renderDraftState(
                latestDraftState
            );
        }


    } finally {

        draftControlSubmitting =
            false;


        banPhaseCheckboxElement.disabled =
            false;

        startButtonElement.disabled =
            false;
    }
}

async function changeDraftRunState(
    action
) {

    if (
        draftControlSubmitting
    ) {

        return;
    }


    if (
        !canCurrentUserControlDraft()
    ) {

        window.alert(
            "Draft 관리자 권한이 필요합니다."
        );

        return;
    }


    if (
        action !== "start"
        &&
        action !== "pause"
        &&
        action !== "resume"
    ) {

        return;
    }


    draftControlSubmitting =
        true;


    startButtonElement.disabled =
        true;

    pauseButtonElement.disabled =
        true;

    resumeButtonElement.disabled =
        true;


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/seasons/`
                + `${currentSeasonNumber}`
                + `/draft/${action}`,
                {
                    method:
                        "POST",

                    headers:
                        getDraftControlHeaders(),
                }
            );


        const responseData =
            await response.json();


        if (
            response.status === 401
        ) {

            if (
                getAdminToken()
            ) {

                sessionStorage.removeItem(
                    adminTokenStorageKey
                );

            } else {

                localStorage.removeItem(
                    "fclUserToken"
                );


                currentUser =
                    null;
            }


            throw new Error(
                "로그인이 만료되었습니다."
            );
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "Draft 상태 변경에 실패했습니다."
            );
        }


    } catch (error) {

        console.error(
            error
        );


        window.alert(
            error.message
        );


    } finally {

        draftControlSubmitting =
            false;


        startButtonElement.disabled =
            false;

        pauseButtonElement.disabled =
            false;

        resumeButtonElement.disabled =
            false;
    }
}

function broadcastDraftCompletion(
    draftState
) {

    const draftSession =
        draftState
            ?.draft_session;


    if (
        !draftSession
        ||
        draftSession.status
        !== "completed"
    ) {

        return;
    }


    const participants =
        draftState.participants
        ?? [];


    const allParticipantsPicked =
        (
            participants.length > 0

            &&

            participants.every(
                participant =>
                    Boolean(
                        participant
                            .picked_club
                    )
            )
        );


    if (!allParticipantsPicked) {

        return;
    }


    const seasonNumber =
        Number(
            draftState
                ?.season
                ?.season_number

            ??

            currentSeasonNumber
        );


    const draftSessionId =
        Number(
            draftSession.id
            ?? 0
        );


    const stateVersion =
        Number(
            draftSession.state_version
            ?? 0
        );


    const completionKey =
        (
            `${seasonNumber}:`
            +
            `${draftSessionId}:`
            +
            `${stateVersion}`
        );


    if (
        lastDraftCompletionKey
        === completionKey
    ) {

        return;
    }


    const sentStorageKey =
        (
            draftCompletionSentPrefix
            +
            seasonNumber
        );


    if (
        localStorage.getItem(
            sentStorageKey
        )
        === completionKey
    ) {

        lastDraftCompletionKey =
            completionKey;

        return;
    }


    lastDraftCompletionKey =
        completionKey;


    localStorage.setItem(
        sentStorageKey,
        completionKey
    );


    const payload = {
        type:
            "draft_completed",

        season_number:
            seasonNumber,

        draft_session_id:
            draftSessionId,

        state_version:
            stateVersion,

        emitted_at:
            Date.now(),
    };


    if (draftEventChannel) {

        draftEventChannel.postMessage(
            payload
        );
    }


    // BroadcastChannel 미지원 브라우저용
    // 다른 탭에서는 storage 이벤트가 발생
    localStorage.setItem(
        draftCompletionEventStorageKey,
        JSON.stringify(
            payload
        )
    );
}


// =========================
// RENDER
// =========================

function renderDraftState(
    draftState
) {

    if (!draftState) {
        return;
    }


    latestDraftState =
        draftState;


    const draftSession =
        draftState.draft_session;


    if (!draftSession) {
        return;
    }


    messagePanelElement
        .classList
        .add(
            "hidden"
        );


    draftContentElement
        .classList
        .remove(
            "hidden"
        );


    renderCurrentTurn(
        draftState
    );


    renderProgress(
        draftState
    );


    renderParticipants(
        draftState
    );


    renderClubs(
        draftState
    );


    renderActions(
        draftState
    );


    renderDraftAdminControls(
        draftSession
    );

    broadcastDraftCompletion(
        draftState
    );


    updateDraftTimer();


    lastUpdateElement.textContent =
        (
            "실시간 업데이트 · "
            +
            new Date()
                .toLocaleTimeString(
                    "ko-KR"
                )
        );
}



function renderCurrentTurn(
    draftState
) {

    const draftSession =
        draftState.draft_session;

    const currentTurn =
        draftState.current_turn;


    currentActionElement
        .classList
        .remove(
            "ban",
            "pick"
        );


    if (
        draftSession.status
        === "completed"
    ) {

        currentActionElement.textContent =
            "END";


        currentParticipantElement.textContent =
            "Draft 완료";


        currentDescriptionElement.textContent =
            "모든 BAN / PICK이 완료되었습니다.";

        return;
    }


    if (!currentTurn) {

        currentActionElement.textContent =
            "-";


        currentParticipantElement.textContent =
            "Draft 대기";


        currentDescriptionElement.textContent =
            "현재 진행 중인 턴이 없습니다.";

        return;
    }


    const actionType =
        currentTurn.action_type;


    currentActionElement.textContent =
        actionType
            .toUpperCase();


    currentActionElement
        .classList
        .add(
            actionType
        );


    currentParticipantElement.textContent =
        currentTurn.fcl_name;


    currentDescriptionElement.textContent =
        (
            `${currentTurn.draft_order}순위 · `
            +
            `${currentTurn.fc_nickname}`
        );
}


function renderProgress(
    draftState
) {

    const progress =
        draftState.progress;

    const draftSession =
        draftState.draft_session;


    const completedActions =
        Number(
            progress.completed_actions
            ?? 0
        );

    const totalActions =
        Number(
            progress.total_actions
            ?? 10
        );


    progressTextElement.textContent =
        `${completedActions} / ${totalActions}`;


    const percent =
        totalActions > 0
            ? (
                completedActions
                /
                totalActions
            )
            * 100
            : 0;


    progressBarElement.style.width =
        `${Math.min(100, percent)}%`;


    phaseTextElement.textContent =
        `PHASE · ${
            formatPhase(
                draftSession.phase
            )
        }`;


    statusTextElement.textContent =
        `STATUS · ${
            formatDraftStatus(
                draftSession.status
            )
        }`;
}


function renderParticipants(
    draftState
) {

    const currentParticipantId =
        Number(
            draftState
                .current_turn
                ?.participant_id
        );


    const participants =
        [
            ...(
                draftState.participants
                ?? []
            ),
        ].sort(
            (
                left,
                right
            ) => (
                Number(
                    left.draft_order
                )
                -
                Number(
                    right.draft_order
                )
            )
        );


    participantListElement.innerHTML =
        participants
            .map(
                participant => {

                    const isCurrent =
                        Number(
                            participant
                                .participant_id
                        )
                        ===
                        currentParticipantId;


                    const pickedClub =
                        participant
                            .picked_club;


                    let pickedClubHtml =
                        `
                        <div class="draft-picked-club">
                            <span>
                                PICK 대기
                            </span>
                        </div>
                        `;


                    if (pickedClub) {

                        const logoUrl =
                            resolveApiAssetUrl(
                                pickedClub.logo_url
                            );


                        const fallbackText =
                            String(
                                pickedClub.short_name
                                ??
                                pickedClub.name
                                ??
                                "?"
                            )
                            .trim()
                            .slice(
                                0,
                                2
                            )
                            .toUpperCase();


                        const logoHtml =
                            logoUrl
                                ? `
                                    <img
                                        src="${escapeHtml(
                                            logoUrl
                                        )}"
                                        alt=""
                                    >
                                `
                                : `
                                    <span
                                        class="
                                            draft-picked-club-logo-placeholder
                                        "
                                    >
                                        ${escapeHtml(
                                            fallbackText
                                        )}
                                    </span>
                                `;


                        pickedClubHtml =
                            `
                            <div class="draft-picked-club">

                                ${logoHtml}

                                <span>
                                    ${escapeHtml(
                                        pickedClub.name
                                    )}
                                </span>

                            </div>
                            `;
                    }


                    return `
                        <article
                            class="
                                draft-participant-card
                                ${isCurrent
                                    ? "current"
                                    : ""}
                            "
                        >

                            <span class="draft-participant-order">
                                ${participant.draft_order}순위
                            </span>

                            <strong class="draft-participant-name">
                                ${escapeHtml(
                                    participant.fcl_name
                                )}
                            </strong>

                            <span class="draft-participant-nickname">
                                ${escapeHtml(
                                    participant.fc_nickname
                                )}
                            </span>

                            ${pickedClubHtml}

                        </article>
                    `;
                }
            )
            .join("");
}


function renderClubs(
    draftState
) {

    const clubs =
        draftState.clubs
        ?? [];


    const draftSession =
        draftState.draft_session;


    const currentTurn =
        draftState.current_turn;


    const adminToken =
        getAdminToken();

    const userToken =
        getUserToken();


    const currentUserParticipantId =
        Number(
            currentUser
                ?.participant_id
        );


    const currentTurnParticipantId =
        Number(
            currentTurn
                ?.participant_id
        );


    const isCurrentParticipant =
        (
            userToken
            &&
            Number.isInteger(
                currentUserParticipantId
            )
            &&
            currentUserParticipantId > 0
            &&
            currentUserParticipantId
            ===
            currentTurnParticipantId
        );


    // =========================
    // 리그 목록 생성
    // =========================

    const leaguesById =
        new Map();


    for (const club of clubs) {

        if (
            club.league_id == null
            ||
            !club.league_name
        ) {

            continue;
        }


        leaguesById.set(
            String(
                club.league_id
            ),
            {
                leagueId:
                    String(
                        club.league_id
                    ),

                leagueName:
                    String(
                        club.league_name
                    ),
            }
        );
    }


    const leagues =
        [
            ...leaguesById.values(),
        ].sort(
            (
                left,
                right
            ) => (
                left.leagueName.localeCompare(
                    right.leagueName,
                    "ko"
                )
            )
        );


    // =========================
    // 리그 SELECT 갱신
    // =========================

    if (leagueFilterElement) {

        const previousLeague =
            leagueFilterElement.value
            ||
            "all";


        leagueFilterElement.innerHTML =
            `
            <option value="all">
                전체 리그
            </option>

            ${
                leagues
                    .map(
                        league => `
                            <option
                                value="${escapeHtml(
                                    league.leagueId
                                )}"
                            >
                                ${escapeHtml(
                                    league.leagueName
                                )}
                            </option>
                        `
                    )
                    .join("")
            }
            `;


        const previousLeagueExists =
            (
                previousLeague
                === "all"
            )
            ||
            leagues.some(
                league => (
                    league.leagueId
                    ===
                    previousLeague
                )
            );


        leagueFilterElement.value =
            previousLeagueExists
                ? previousLeague
                : "all";
    }


    // =========================
    // 검색어
    // =========================

    const searchKeyword =
        String(
            clubSearchElement
                ?.value
            ??
            ""
        )
        .trim()
        .normalize(
            "NFKC"
        )
        .toLocaleLowerCase(
            "ko-KR"
        );


    // =========================
    // 선택된 리그
    // =========================

    const selectedLeagueId =
        leagueFilterElement
            ?.value
        ??
        "all";


    // =========================
    // 검색 + 리그 필터
    // =========================

    const filteredClubs =
        clubs.filter(
            club => {

                const matchesLeague =
                    (
                        selectedLeagueId
                        === "all"
                    )
                    ||
                    (
                        String(
                            club.league_id
                            ??
                            ""
                        )
                        ===
                        selectedLeagueId
                    );


                if (!matchesLeague) {

                    return false;
                }


                if (!searchKeyword) {

                    return true;
                }


                const searchTarget =
                    [
                        club.name,
                        club.short_name,
                        club.league_name,
                    ]
                    .filter(
                        Boolean
                    )
                    .join(
                        " "
                    )
                    .normalize(
                        "NFKC"
                    )
                    .toLocaleLowerCase(
                        "ko-KR"
                    );


                return (
                    searchTarget.includes(
                        searchKeyword
                    )
                );
            }
        );


    // =========================
    // 클럽 개수
    // =========================

    if (clubCountElement) {

        clubCountElement.textContent =
            (
                `${filteredClubs.length}`
                +
                " / "
                +
                `${clubs.length}`
            );
    }


    // =========================
    // 클럽 없음
    // =========================

    if (
        clubs.length === 0
    ) {

        clubListElement.innerHTML =
            `
            <div class="draft-action-empty">
                등록된 클럽이 없습니다.
            </div>
            `;

        return;
    }


    // =========================
    // 검색 결과 없음
    // =========================

    if (
        filteredClubs.length === 0
    ) {

        clubListElement.innerHTML =
            `
            <div class="draft-action-empty">
                검색 조건에 맞는 클럽이 없습니다.
            </div>
            `;

        return;
    }


    // =========================
    // 클럽 카드 렌더링
    // =========================

    clubListElement.innerHTML =
        filteredClubs
            .map(
                club => {

                    const status =
                        club.status
                        ??
                        "available";


                    const logoUrl =
                        resolveApiAssetUrl(
                            club.logo_url
                        );


                    const fallbackText =
                        String(
                            club.short_name
                            ??
                            club.name
                            ??
                            "?"
                        )
                        .trim()
                        .slice(
                            0,
                            2
                        )
                        .toUpperCase();


                    const logoHtml =
                        logoUrl
                            ? `
                                <img
                                    class="draft-club-logo"
                                    src="${escapeHtml(
                                        logoUrl
                                    )}"
                                    alt="${escapeHtml(
                                        club.name
                                    )}"
                                >
                            `
                            : `
                                <div
                                    class="
                                        draft-club-logo
                                        draft-club-logo-placeholder
                                    "
                                >
                                    ${escapeHtml(
                                        fallbackText
                                    )}
                                </div>
                            `;


                    const leagueHtml =
                        club.league_name
                            ? `
                                <span class="draft-club-league">
                                    ${escapeHtml(
                                        club.league_name
                                    )}
                                </span>
                            `
                            : "";


                    let actionButtonHtml =
                        "";


                    // =========================
                    // BAN / PICK 버튼
                    // =========================

                    if (
                        (
                            adminToken
                            ||
                            isCurrentParticipant
                        )
                        &&
                        draftSession?.status
                        === "active"
                        &&
                        currentTurn
                    ) {

                        const actionType =
                            currentTurn.action_type;


                        const canAct =
                            (
                                actionType
                                === "ban"
                                &&
                                club.can_ban
                            )
                            ||
                            (
                                actionType
                                === "pick"
                                &&
                                club.can_pick
                            );


                        if (canAct) {

                            actionButtonHtml =
                                `
                                <button
                                    type="button"
                                    class="
                                        draft-club-action-button
                                        ${escapeHtml(
                                            actionType
                                        )}
                                    "
                                    data-draft-club-action
                                    data-club-id="${club.club_id}"
                                >
                                    ${
                                        actionType
                                            .toUpperCase()
                                    } 실행
                                </button>
                                `;
                        }
                    }


                    return `
                        <article
                            class="
                                draft-club-card
                                ${escapeHtml(
                                    status
                                )}
                            "
                        >

                            ${logoHtml}

                            <strong
                                class="draft-club-name"
                            >
                                ${escapeHtml(
                                    club.name
                                )}
                            </strong>

                            ${leagueHtml}

                            <span
                                class="draft-club-status"
                            >
                                ${formatClubStatus(
                                    status
                                )}
                            </span>

                            ${actionButtonHtml}

                        </article>
                    `;
                }
            )
            .join("");
}


function renderActions(
    draftState
) {

    const actions =
        draftState.actions
        ?? [];


    actionCountElement.textContent =
        String(
            actions.length
        );


    if (
        actions.length === 0
    ) {

        actionListElement.innerHTML =
            `
            <div class="draft-action-empty">
                아직 진행된 BAN / PICK이 없습니다.
            </div>
            `;

        return;
    }


    actionListElement.innerHTML =
        [
            ...actions,
        ]
            .sort(
                (
                    left,
                    right
                ) => (
                    Number(
                        left.action_index
                    )
                    -
                    Number(
                        right.action_index
                    )
                )
            )
            .map(
                action => {

                    const actionType =
                        action.action_type;


                    return `
                        <div class="draft-action-row">

                            <span
                                class="
                                    draft-action-type
                                    ${escapeHtml(actionType)}
                                "
                            >
                                ${escapeHtml(
                                    actionType
                                        .toUpperCase()
                                )}
                            </span>

                            <span class="draft-action-player">
                                ${escapeHtml(
                                    action.fcl_name
                                )}
                            </span>

                            <span class="draft-action-club">
                                ${escapeHtml(
                                    action.club_name
                                )}
                            </span>

                        </div>
                    `;
                }
            )
            .join("");
}

async function createDraftSessionFromWaiting() {

    if (
        draftControlSubmitting
    ) {

        return;
    }


    if (
        !canCurrentUserControlDraft()
    ) {

        window.alert(
            "Draft 관리자 권한이 필요합니다."
        );

        return;
    }


    const createButton =
        document.querySelector(
            "#draft-waiting-create-button"
        );


    draftControlSubmitting =
        true;


    if (createButton) {

        createButton.disabled =
            true;

        createButton.textContent =
            "Draft 준비 중...";
    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/admin/seasons/`
                + `${currentSeasonNumber}`
                + `/draft`,
                {
                    method:
                        "POST",

                    headers:
                        getDraftControlHeaders(
                            true
                        ),

                    body:
                        JSON.stringify(
                            {
                                allow_duplicate_picks:
                                    false,

                                ban_enabled:
                                    true,

                                turn_seconds:
                                    60,

                                timeout_policy:
                                    "pause",
                            }
                        ),
                }
            );


        const responseData =
            await response.json();


        if (
            response.status === 401
        ) {

            throw new Error(
                "로그인이 만료되었습니다."
            );
        }


        if (
            response.status === 403
        ) {

            throw new Error(
                "Draft 관리자 권한이 없습니다."
            );
        }


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "Draft 생성에 실패했습니다."
            );
        }


        await loadInitialDraftState();


    } catch (error) {

        console.error(
            error
        );


        window.alert(
            error.message
        );


    } finally {

        draftControlSubmitting =
            false;


        if (createButton) {

            createButton.disabled =
                false;

            createButton.textContent =
                "Draft 준비";
        }
    }
}

// =========================
// EMPTY / ERROR
// =========================
function showWaitingForDraft() {

    draftContentElement
        .classList
        .add(
            "hidden"
        );


    messagePanelElement
        .classList
        .remove(
            "hidden"
        );


    messageTitleElement.textContent =
        "Draft 시작 대기 중";


    messageDescriptionElement.textContent =
        (
            `Season ${currentSeasonNumber} Draft가 `
            +
            "생성되면 이 화면에 자동으로 표시됩니다."
        );


    let createButton =
        document.querySelector(
            "#draft-waiting-create-button"
        );


    // =========================
    // MEMBER에게는 생성 버튼 숨김
    // =========================

    if (
        !canCurrentUserControlDraft()
    ) {

        if (createButton) {

            createButton.remove();
        }


        return;
    }


    // =========================
    // ADMIN 회원
    // Draft 준비 버튼
    // =========================

    if (!createButton) {

        createButton =
            document.createElement(
                "button"
            );


        createButton.type =
            "button";


        createButton.id =
            "draft-waiting-create-button";


        createButton.className =
            (
                "draft-control-button "
                +
                "start "
                +
                "draft-waiting-create-button"
            );


        createButton.textContent =
            "Draft 준비";


        createButton.addEventListener(
            "click",
            async () => {

                const confirmed =
                    window.confirm(
                        "새 Draft를 준비하시겠습니까?"
                    );


                if (!confirmed) {

                    return;
                }


                await createDraftSessionFromWaiting();
            }
        );


        messagePanelElement.append(
            createButton
        );
    }
}


function showMessage(
    title,
    description
) {

    draftContentElement
        .classList
        .add(
            "hidden"
        );


    messagePanelElement
        .classList
        .remove(
            "hidden"
        );


    messageTitleElement.textContent =
        title;


    messageDescriptionElement.textContent =
        description;
}


// =========================
// HELPERS
// =========================

function getAdminToken() {

    return sessionStorage.getItem(
        adminTokenStorageKey
    );
}

function canCurrentUserControlDraft() {

    const adminToken =
        getAdminToken();


    if (adminToken) {

        return true;
    }


    const userToken =
        getUserToken();


    return (
        Boolean(
            userToken
        )
        &&
        Boolean(
            currentUser
                ?.is_admin
        )
    );
}


function getDraftControlHeaders(
    includeJson = false
) {

    const headers = {};


    if (includeJson) {

        headers[
            "Content-Type"
        ] =
            "application/json";
    }


    const adminToken =
        getAdminToken();


    if (adminToken) {

        headers[
            "X-Admin-Token"
        ] =
            adminToken;


        return headers;
    }


    const userToken =
        getUserToken();


    if (
        userToken
        &&
        currentUser
            ?.is_admin
    ) {

        headers.Authorization =
            `Bearer ${userToken}`;
    }


    return headers;
}

async function submitDraftClubAction(
    clubId
) {

    if (
        draftActionSubmitting
    ) {
        return;
    }


    const draftState =
        latestDraftState;


    const currentTurn =
        draftState
            ?.current_turn;


    const draftSession =
        draftState
            ?.draft_session;


    if (
        !currentTurn
        ||
        !draftSession
        ||
        draftSession.status
        !== "active"
    ) {

        window.alert(
            "현재 실행할 수 있는 Draft 턴이 없습니다."
        );

        return;
    }


    const adminToken =
        getAdminToken();


    const userToken =
        getUserToken();


    const participantId =
        Number(
            currentUser
                ?.participant_id
        );


    const isParticipantTurn =
        (
            userToken
            &&
            Number.isInteger(
                participantId
            )
            &&
            participantId > 0
            &&
            participantId
            ===
            Number(
                currentTurn
                    .participant_id
            )
        );


    if (
        !adminToken
        &&
        !isParticipantTurn
    ) {

        window.alert(
            "현재 Draft를 실행할 권한이 없습니다."
        );

        return;
    }


    const club =
        (
            draftState.clubs
            ?? []
        ).find(
            item =>
                Number(
                    item.club_id
                )
                ===
                Number(
                    clubId
                )
        );


    if (!club) {

        window.alert(
            "클럽 정보를 찾을 수 없습니다."
        );

        return;
    }


    const actionType =
        currentTurn.action_type;


    const confirmed =
        window.confirm(
            `${currentTurn.fcl_name}님의 `
            +
            `${actionType.toUpperCase()}\n\n`
            +
            `${club.name}\n\n`
            +
            "실행하시겠습니까?"
        );


    if (!confirmed) {
        return;
    }


    draftActionSubmitting =
        true;


    try {

            let actionUrl;

            let actionHeaders;

            let actionBody;


            if (adminToken) {

                actionUrl =
                    `${apiBaseUrl}`
                    + `/api/admin/seasons/`
                    + `${currentSeasonNumber}`
                    + `/draft/action`;


                actionHeaders = {
                    "Content-Type":
                        "application/json",

                    "X-Admin-Token":
                        adminToken,
                };


                actionBody = {
                    participant_id:
                        Number(
                            currentTurn
                                .participant_id
                        ),

                    club_id:
                        Number(
                            clubId
                        ),
                };


            } else {

                actionUrl =
                    `${apiBaseUrl}`
                    + `/api/seasons/`
                    + `${currentSeasonNumber}`
                    + `/draft/action`;


                actionHeaders = {
                    "Content-Type":
                        "application/json",

                    Authorization:
                        `Bearer ${userToken}`,
                };


                actionBody = {
                    club_id:
                        Number(
                            clubId
                        ),
                };
            }


            const response =
                await fetch(
                    actionUrl,
                    {
                        method:
                            "POST",

                        headers:
                            actionHeaders,

                        body:
                            JSON.stringify(
                                actionBody
                            ),
                    }
                );


        const responseData =
            await response.json();


        if (!response.ok) {

            if (
                response.status === 401
            ) {

                if (adminToken) {

                    sessionStorage.removeItem(
                        adminTokenStorageKey
                    );

                } else {

                    localStorage.removeItem(
                        "fclUserToken"
                    );

                    currentUser =
                        null;
                }
            }


            throw new Error(
                responseData.detail
                ??
                "Draft 액션 처리에 실패했습니다."
            );
        }


    } catch (error) {

        console.error(
            error
        );


        window.alert(
            error.message
        );


    } finally {

        draftActionSubmitting =
            false;
    }
}

function setConnectionStatus(
    status,
    text
) {

    connectionElement
        .classList
        .remove(
            "connecting",
            "live",
            "offline"
        );


    connectionElement
        .classList
        .add(
            status
        );


    connectionTextElement.textContent =
        text;
}


function formatPhase(
    phase
) {

    if (
        phase === "ban"
    ) {
        return "BAN";
    }


    if (
        phase === "pick"
    ) {
        return "PICK";
    }


    if (
        phase === "completed"
    ) {
        return "COMPLETE";
    }


    return String(
        phase
        ?? "-"
    ).toUpperCase();
}


function formatDraftStatus(
    status
) {

    const statusMap = {
        setup:
            "대기",

        active:
            "진행 중",

        paused:
            "일시정지",

        completed:
            "완료",

        cancelled:
            "취소",
    };


    return (
        statusMap[
            status
        ]
        ??
        status
        ??
        "-"
    );
}


function formatClubStatus(
    status
) {

    const statusMap = {
        available:
            "AVAILABLE",

        banned:
            "BANNED",

        picked:
            "PICKED",

        inactive:
            "INACTIVE",
    };


    return (
        statusMap[
            status
        ]
        ??
        String(
            status
            ?? "-"
        ).toUpperCase()
    );
}


function resolveApiAssetUrl(
    path
) {

    if (!path) {
        return "";
    }


    if (
        path.startsWith(
            "http://"
        )
        ||
        path.startsWith(
            "https://"
        )
    ) {

        return path;
    }


    if (
        apiBaseUrl
        &&
        path.startsWith("/")
    ) {

        return (
            apiBaseUrl
            +
            path
        );
    }


    return path;
}


async function readResponseError(
    response
) {

    try {

        const data =
            await response.json();


        return (
            data.detail
            ??
            "요청을 처리하지 못했습니다."
        );

    } catch (error) {

        return (
            "요청을 처리하지 못했습니다."
        );
    }
}


function escapeHtml(
    value
) {

    return String(
        value
        ?? ""
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

// =========================
// ADMIN DRAFT ACTION
// =========================

clubListElement.addEventListener(
    "click",
    async event => {

        const actionButton =
            event.target.closest(
                "[data-draft-club-action]"
            );


        if (!actionButton) {
            return;
        }


        const clubId =
            Number(
                actionButton.dataset
                    .clubId
            );


        if (
            !Number.isInteger(
                clubId
            )
            ||
            clubId <= 0
        ) {
            return;
        }


        await submitDraftClubAction(
            clubId
        );
    }
);

// =========================
// PAGE CLOSE
// =========================

window.addEventListener(
    "beforeunload",
    () => {

        pageClosing = true;


        clearTimeout(
            reconnectTimer
        );


        if (
            draftSocket
            &&
            (
                draftSocket.readyState
                === WebSocket.OPEN

                ||

                draftSocket.readyState
                === WebSocket.CONNECTING
            )
        ) {

            draftSocket.close();
        }
    }
);

banPhaseCheckboxElement
    ?.addEventListener(
        "change",
        async () => {

            await updateDraftBanPhaseSetting(
                banPhaseCheckboxElement.checked
            );
        }
    );

startButtonElement
    ?.addEventListener(
        "click",
        async () => {

            const confirmed =
                window.confirm(
                    "Draft를 시작하시겠습니까?"
                );


            if (!confirmed) {
                return;
            }


            await changeDraftRunState(
                "start"
            );
        }
    );


pauseButtonElement
    ?.addEventListener(
        "click",
        async () => {

            const confirmed =
                window.confirm(
                    "Draft를 일시정지하시겠습니까?"
                );


            if (!confirmed) {
                return;
            }


            await changeDraftRunState(
                "pause"
            );
        }
    );


resumeButtonElement
    ?.addEventListener(
        "click",
        async () => {

            await changeDraftRunState(
                "resume"
            );
        }
    );


clubSearchElement
    ?.addEventListener(
        "input",
        () => {

            if (!latestDraftState) {
                return;
            }


            renderClubs(
                latestDraftState
            );
        }
    );


leagueFilterElement
    ?.addEventListener(
        "change",
        () => {

            if (!latestDraftState) {
                return;
            }


            renderClubs(
                latestDraftState
            );
        }
    );

startDraftTimer();

initializeDraftPage();