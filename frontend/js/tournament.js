import {
    apiBaseUrl,
} from "./config.js";

import {
    openResultDetail,
} from "./results.js";


const createPanelElement =
    document.querySelector(
        "#tournament-create-panel"
    );


const participantListElement =
    document.querySelector(
        "#tournament-participant-list"
    );


const participantCountElement =
    document.querySelector(
        "#tournament-participant-count"
    );


const titleInputElement =
    document.querySelector(
        "#tournament-title"
    );


const randomizeInputElement =
    document.querySelector(
        "#tournament-randomize"
    );


const addParticipantButtonElement =
    document.querySelector(
        "#tournament-add-participant"
    );


const createButtonElement =
    document.querySelector(
        "#tournament-create-button"
    );


const newTournamentButtonElement =
    document.querySelector(
        "#tournament-new-button"
    );


const formMessageElement =
    document.querySelector(
        "#tournament-form-message"
    );


const historyListElement =
    document.querySelector(
        "#tournament-history-list"
    );


const bracketPanelElement =
    document.querySelector(
        "#tournament-bracket-panel"
    );


const bracketElement =
    document.querySelector(
        "#tournament-bracket"
    );


const bracketTitleElement =
    document.querySelector(
        "#tournament-bracket-title"
    );


const bracketDateElement =
    document.querySelector(
        "#tournament-bracket-date"
    );


const bracketInfoElement =
    document.querySelector(
        "#tournament-bracket-info"
    );


const championElement =
    document.querySelector(
        "#tournament-champion"
    );


let currentTournamentId = null;


// =====================================================
// HTML ESCAPE
// =====================================================

function escapeTournamentHtml(
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
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


// =====================================================
// 참가자 입력
// =====================================================

function getParticipantInputElements() {

    return Array.from(
        participantListElement.querySelectorAll(
            ".tournament-participant-input"
        )
    );
}


function updateParticipantCount() {

    const count =
        getParticipantInputElements()
            .length;


    participantCountElement.textContent =
        `${count} / 16명`;


    addParticipantButtonElement.disabled =
        count >= 16;


    const removeButtons =
        participantListElement.querySelectorAll(
            ".tournament-participant-remove"
        );


    removeButtons.forEach(
        buttonElement => {

            buttonElement.disabled =
                count <= 2;
        }
    );
}


function createParticipantInput(
    value = ""
) {

    const rowElement =
        document.createElement(
            "div"
        );


    rowElement.classList.add(
        "tournament-participant-row"
    );


    const participantNumber =
        getParticipantInputElements()
            .length
        + 1;


    rowElement.innerHTML = `
        <span
            class="
                tournament-participant-number
            "
        >
            ${participantNumber}
        </span>

        <input
            type="text"
            maxlength="50"
            class="
                tournament-participant-input
            "
            placeholder="참가자 이름"
            value="${
                escapeTournamentHtml(
                    value
                )
            }"
        >

        <input
            type="text"
            maxlength="100"
            class="
                tournament-participant-nickname-input
            "
            placeholder="FC Online 닉네임"
        >

        <button
            type="button"
            class="
                tournament-participant-remove
            "
            aria-label="참가자 삭제"
        >
            ×
        </button>
    `;


    participantListElement.appendChild(
        rowElement
    );


    updateParticipantRows();
}


function updateParticipantRows() {

    const rows =
        participantListElement.querySelectorAll(
            ".tournament-participant-row"
        );


    rows.forEach(
        (
            rowElement,
            index
        ) => {

            const numberElement =
                rowElement.querySelector(
                    ".tournament-participant-number"
                );


            numberElement.textContent =
                String(
                    index + 1
                );
        }
    );


    updateParticipantCount();
}


function resetTournamentForm() {

    titleInputElement.value =
        "";


    randomizeInputElement.checked =
        true;


    participantListElement.innerHTML =
        "";


    createParticipantInput();

    createParticipantInput();


    formMessageElement.textContent =
        "";
}


addParticipantButtonElement.addEventListener(
    "click",
    () => {

        const count =
            getParticipantInputElements()
                .length;


        if (count >= 16) {
            return;
        }


        createParticipantInput();


        const inputs =
            getParticipantInputElements();


        inputs[
            inputs.length - 1
        ].focus();
    }
);


participantListElement.addEventListener(
    "click",
    event => {

        const removeButtonElement =
            event.target.closest(
                ".tournament-participant-remove"
            );


        if (!removeButtonElement) {
            return;
        }


        const rows =
            participantListElement.querySelectorAll(
                ".tournament-participant-row"
            );


        if (rows.length <= 2) {
            return;
        }


        removeButtonElement
            .closest(
                ".tournament-participant-row"
            )
            ?.remove();


        updateParticipantRows();
    }
);


// =====================================================
// 토너먼트 생성
// =====================================================

async function createTournament() {

    const title =
        titleInputElement.value
            .trim();


    const participantRows =
        Array.from(
            participantListElement
                .querySelectorAll(
                    ".tournament-participant-row"
                )
        );


    const participants =
        participantRows
            .map(
                rowElement => {

                    const name =
                        rowElement
                            .querySelector(
                                ".tournament-participant-input"
                            )
                            ?.value
                            .trim()
                        ?? "";


                    const fcNickname =
                        rowElement
                            .querySelector(
                                ".tournament-participant-nickname-input"
                            )
                            ?.value
                            .trim()
                        ?? "";


                    return {
                        name,

                        fc_nickname:
                            fcNickname
                            || null,
                    };
                }
            )
            .filter(
                participant =>
                    participant.name.length > 0
            );


    if (!title) {

        formMessageElement.textContent =
            "대회명을 입력해주세요.";

        return;
    }


    if (participants.length < 2) {

        formMessageElement.textContent =
            "참가자는 최소 2명이 필요합니다.";

        return;
    }


    const normalizedParticipants =
        participants.map(
            participant =>
                participant.name
                    .toLocaleLowerCase(
                        "ko-KR"
                    )
        );


    if (
        new Set(
            normalizedParticipants
        ).size
        !==
        normalizedParticipants.length
    ) {

        formMessageElement.textContent =
            "동일한 참가자 이름을 중복해서 사용할 수 없습니다.";

        return;
    }


    const originalText =
        createButtonElement.textContent;


    createButtonElement.disabled =
        true;


    createButtonElement.textContent =
        "생성 중...";


    formMessageElement.textContent =
        "";


    try {

        const response = await fetch(
            `${apiBaseUrl}/api/tournaments`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify(
                        {
                            title,
                            participants,

                            randomize:
                                randomizeInputElement
                                    .checked,
                        }
                    ),
            }
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "토너먼트 생성에 실패했습니다."
            );
        }


        currentTournamentId =
            data.tournament_id;


        await loadTournamentList();

        await loadTournamentDetail(
            currentTournamentId
        );


        createPanelElement.classList.add(
            "hidden"
        );


    } catch (error) {

        console.error(
            error
        );


        formMessageElement.textContent =
            error.message;

    } finally {

        createButtonElement.disabled =
            false;


        createButtonElement.textContent =
            originalText;
    }
}


createButtonElement.addEventListener(
    "click",
    createTournament
);


// =====================================================
// 토너먼트 목록
// =====================================================

async function loadTournamentList() {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/tournaments`
        );


        if (!response.ok) {

            throw new Error(
                "토너먼트 목록을 불러오지 못했습니다."
            );
        }


        const tournaments =
            await response.json();


        renderTournamentList(
            tournaments
        );


        if (
            currentTournamentId === null
            &&
            tournaments.length > 0
        ) {

            currentTournamentId =
                tournaments[0]
                    .tournament_id;


            await loadTournamentDetail(
                currentTournamentId
            );
        }


    } catch (error) {

        console.error(
            error
        );


        historyListElement.innerHTML = `
            <p class="tournament-empty-message">
                토너먼트 목록을 불러오지 못했습니다.
            </p>
        `;
    }
}


function renderTournamentList(
    tournaments
) {

    historyListElement.innerHTML =
        "";


    if (
        tournaments.length === 0
    ) {

        historyListElement.innerHTML = `
            <p class="tournament-empty-message">
                아직 생성된 토너먼트가 없습니다.
            </p>
        `;

        return;
    }


    tournaments.forEach(
        tournament => {

            const buttonElement =
                document.createElement(
                    "button"
                );


            buttonElement.type =
                "button";


            buttonElement.classList.add(
                "tournament-history-item"
            );


            if (
                tournament.tournament_id
                ===
                currentTournamentId
            ) {

                buttonElement.classList.add(
                    "active"
                );
            }


            buttonElement.dataset.tournamentId =
                tournament.tournament_id;


            const statusText =
                tournament.status
                === "completed"
                    ? "완료"
                    : "진행 중";


            buttonElement.innerHTML = `
                <div
                    class="
                        tournament-history-main
                    "
                >

                    <strong>
                        ${
                            escapeTournamentHtml(
                                tournament.title
                            )
                        }
                    </strong>

                    <span>
                        ${
                            escapeTournamentHtml(
                                tournament.date
                            )
                        }
                    </span>

                </div>


                <div
                    class="
                        tournament-history-meta
                    "
                >

                    <span>
                        ${
                            tournament
                                .participant_count
                        }명
                    </span>

                    <span
                        class="
                            tournament-status-badge
                            ${
                                tournament.status
                            }
                        "
                    >
                        ${statusText}
                    </span>

                </div>
            `;


            historyListElement.appendChild(
                buttonElement
            );
        }
    );
}


historyListElement.addEventListener(
    "click",
    async event => {

        const itemElement =
            event.target.closest(
                "[data-tournament-id]"
            );


        if (!itemElement) {
            return;
        }


        currentTournamentId =
            Number(
                itemElement.dataset
                    .tournamentId
            );


        await loadTournamentDetail(
            currentTournamentId
        );


        await loadTournamentList();
    }
);


// =====================================================
// 토너먼트 상세
// =====================================================

async function loadTournamentDetail(
    tournamentId
) {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/tournaments/${tournamentId}`
        );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "토너먼트를 불러오지 못했습니다."
            );
        }


        renderTournamentDetail(
            data
        );


    } catch (error) {

        console.error(
            error
        );


        bracketPanelElement.classList.remove(
            "hidden"
        );


        bracketElement.innerHTML = `
            <p class="tournament-empty-message">
                ${escapeTournamentHtml(
                    error.message
                )}
            </p>
        `;
    }
}

function createTournamentParticipantHtml(
    participant,
    winner,
    score
) {

    if (!participant) {

        return `
            <div
                class="
                    tournament-match-player
                    empty
                "
            >
                <span>
                    대기
                </span>

                <strong
                    class="
                        tournament-player-score
                    "
                >
                    -
                </strong>
            </div>
        `;
    }


    const isWinner =
        winner
        &&
        winner.entry_id
        ===
        participant.entry_id;


    const scoreText =
        score !== null
        &&
        score !== undefined
            ? String(score)
            : "-";


    return `
        <div
            class="
                tournament-match-player
                ${
                    isWinner
                        ? "winner"
                        : ""
                }
            "
        >

            <span
                class="
                    tournament-player-name
                "
            >
                ${
                    escapeTournamentHtml(
                        participant.name
                    )
                }
            </span>


            <strong
                class="
                    tournament-player-score
                "
            >
                ${
                    escapeTournamentHtml(
                        scoreText
                    )
                }
            </strong>

        </div>
    `;
}


function renderTournamentMatch(
    match,
    tournamentStatus
) {

    const isReady =
        match.status
        === "ready";


    const isCompleted =
        match.status
        === "completed";

    const canOpenDetail =
        Boolean(
            match.series_id
        )
        &&
        match.series_status
        === "completed";


    const participantAHtml =
        createTournamentParticipantHtml(
            match.participant_a,
            match.winner,
            match.team_a_score
        );


    const participantBHtml =
        createTournamentParticipantHtml(
            match.participant_b,
            match.winner,
            match.team_b_score
        );


let actionHtml = "";

if (
    match.series_id
) {

    // =============================
    // 경기 시작 전
    // =============================

    if (
        tournamentStatus === "active"
        &&
        match.series_status === "scheduled"
    ) {

        actionHtml = `
            <div
                class="
                    tournament-winner-actions
                "
            >
                <button
                    type="button"
                    data-tournament-series-id="${
                        match.series_id
                    }"
                    data-tournament-series-status="scheduled"
                >
                    MATCH START
                </button>
            </div>
        `;

    }


    // =============================
    // 진행 중
    // =============================

    else if (
        tournamentStatus === "active"
        &&
        match.series_status === "active"
    ) {

        actionHtml = `
            <div
                class="
                    tournament-winner-actions
                "
            >
                <button
                    type="button"
                    data-tournament-series-id="${
                        match.series_id
                    }"
                    data-tournament-series-status="active"
                >
                    경기 결과 입력
                </button>
            </div>
        `;
    }


    // =============================
    // 결과 입력 완료
    // NEXON 기록 대기
    // =============================

    else if (
        match.series_status === "completed"
        &&
        (
            match.stats_sync_status === "pending"
            ||
            match.stats_sync_status === "conflict"
        )
    ) {

        const syncButtonText =
            match.stats_sync_status
            === "conflict"
                ? "NEXON 기록 다시 확인"
                : "NEXON 기록 확인";


        actionHtml = `
            <div
                class="
                    tournament-winner-actions
                "
            >
                <button
                    type="button"
                    class="tournament-sync-button"
                    data-tournament-sync-series-id="${
                        match.series_id
                    }"
                >
                    ${syncButtonText}
                </button>
            </div>
        `;
    }


    // =============================
    // NEXON 동기화 완료
    // =============================

    else if (
        match.series_status === "completed"
        &&
        match.stats_sync_status === "synced"
    ) {

        actionHtml = `
            <div
                class="
                    tournament-match-detail-guide
                "
            >
                경기 카드를 클릭하면
                상세 기록을 볼 수 있습니다.
            </div>
        `;
    }
}


    let resultHtml = "";


    if (
        isCompleted
        &&
        match.winner
    ) {

        resultHtml = `
            <div
                class="
                    tournament-match-result
                "
            >
                ${
                    match.is_bye
                        ? "부전승"
                        : "승자"
                }
                ·
                <strong>
                    ${
                        escapeTournamentHtml(
                            match.winner.name
                        )
                    }
                </strong>
            </div>
        `;
    }


    return `
        <article
            class="
                tournament-match-card
                ${
                    isCompleted
                        ? "completed"
                        : ""
                }
                ${
                    canOpenDetail
                        ? "detail-enabled"
                        : ""
                }
            "

            data-match-id="${
                match.match_id
            }"

            ${
                canOpenDetail
                    ? `
                        data-tournament-detail-series-id="${
                            match.series_id
                        }"
                    `
                    : ""
            }
        >

            <div
                class="
                    tournament-match-number
                "
            >
                MATCH
                ${match.match_number}
            </div>


            ${participantAHtml}


            <div
                class="
                    tournament-match-vs
                "
            >
                VS
            </div>


            ${participantBHtml}


            ${actionHtml}

            ${resultHtml}

        </article>
    `;
}


function renderTournamentDetail(
    tournament
) {

    bracketPanelElement.classList.remove(
        "hidden"
    );


    bracketTitleElement.textContent =
        tournament.title;


    bracketDateElement.textContent =
        tournament.date;


    bracketInfoElement.textContent =
        `${tournament.participant_count}명 참가`;


    if (
        tournament.status
        === "completed"
        &&
        tournament.champion
    ) {

        championElement.classList.remove(
            "hidden"
        );


        championElement.innerHTML = `
            <span>
                🏆 CHAMPION
            </span>

            <strong>
                ${
                    escapeTournamentHtml(
                        tournament.champion
                            .name
                    )
                }
            </strong>
        `;

    } else {

        championElement.classList.add(
            "hidden"
        );


        championElement.innerHTML =
            "";
    }


    bracketElement.innerHTML =
        "";


    tournament.rounds.forEach(
        (
            round,
            roundIndex
        ) => {

            // =============================
            // BYE 경기는 화면에서 숨김
            //
            // DB에서는 자동 진출 처리를 위해
            // 그대로 유지
            // =============================

            const visibleMatches =
                round.matches.filter(
                    match =>
                        !match.is_bye
                );


            // =============================
            // 해당 라운드가 전부 BYE뿐이면
            // 화면에 라운드 자체를 표시하지 않음
            // =============================

            if (
                visibleMatches.length === 0
            ) {
                return;
            }


            // =============================
            // 첫 라운드에 BYE가 존재하면
            // "8강" 대신
            // "4강 진출전"처럼 표시
            // =============================

            const hasBye =
                round.matches.some(
                    match =>
                        match.is_bye
                );


            let roundTitle =
                round.round_name;


            if (
                roundIndex === 0
                &&
                hasBye
                &&
                tournament.rounds[
                    roundIndex + 1
                ]
            ) {

                roundTitle =
                    `${
                        tournament.rounds[
                            roundIndex + 1
                        ].round_name
                    } 진출전`;
            }


            const roundElement =
                document.createElement(
                    "section"
                );


            roundElement.classList.add(
                "tournament-round"
            );


            roundElement.innerHTML = `
                <div
                    class="
                        tournament-round-title
                    "
                >
                    ${
                        escapeTournamentHtml(
                            roundTitle
                        )
                    }
                </div>

                <div
                    class="
                        tournament-round-matches
                    "
                >
                    ${
                        visibleMatches
                            .map(
                                match =>
                                    renderTournamentMatch(
                                        match,
                                        tournament.status
                                    )
                            )
                            .join("")
                    }
                </div>
            `;


            bracketElement.appendChild(
                roundElement
            );
        }
    );
}


// =====================================================
// 승자 선택
// =====================================================

// =====================================================
// NEXON 기록 확인
// =====================================================

async function syncTournamentSeries(
    seriesId,
    buttonElement
) {

    if (
        !Number.isInteger(
            seriesId
        )
        ||
        seriesId <= 0
    ) {

        return;
    }


    const originalText =
        buttonElement.textContent;


    buttonElement.disabled =
        true;


    buttonElement.textContent =
        "NEXON 확인 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/fconline/series/`
                + `${seriesId}`
                + `/sync`,
                {
                    method:
                        "POST",
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            if (
                response.status
                === 429
            ) {

                throw new Error(
                    "NEXON API 호출 제한 중입니다. "
                    + "잠시 후 다시 확인해주세요."
                );
            }


            throw new Error(
                data.detail
                ??
                "NEXON 기록 확인에 실패했습니다."
            );
        }


        await loadTournamentDetail(
            currentTournamentId
        );


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

// =====================================================
// MATCH START / 결과 입력
// =====================================================

bracketElement.addEventListener(
    "click",
    async event => {

        // =============================
        // 1. NEXON 기록 확인
        // 버튼이 카드 안에 있으므로
        // 상세 클릭보다 먼저 처리
        // =============================

        const syncButtonElement =
            event.target.closest(
                "[data-tournament-sync-series-id]"
            );


        if (syncButtonElement) {

            const syncSeriesId =
                Number(
                    syncButtonElement
                        .dataset
                        .tournamentSyncSeriesId
                );


            await syncTournamentSeries(
                syncSeriesId,
                syncButtonElement
            );


            return;
        }


        // =============================
        // 2. 완료 경기 상세
        // =============================

        const detailCardElement =
            event.target.closest(
                "[data-tournament-detail-series-id]"
            );


        if (detailCardElement) {

            const detailSeriesId =
                Number(
                    detailCardElement
                        .dataset
                        .tournamentDetailSeriesId
                );


            if (
                Number.isInteger(
                    detailSeriesId
                )
                &&
                detailSeriesId > 0
            ) {

                await openResultDetail(
                    detailSeriesId,
                    "ONE-DAY TOURNAMENT"
                );
            }


            return;
        }


        // =============================
        // 3. MATCH START / 결과 입력
        // =============================

        const buttonElement =
            event.target.closest(
                "[data-tournament-series-id]"
            );

        if (!buttonElement) {
            return;
        }


        const seriesId =
            Number(
                buttonElement.dataset
                    .tournamentSeriesId
            );


        const seriesStatus =
            buttonElement.dataset
                .tournamentSeriesStatus
                ?.trim();


        if (
            !Number.isInteger(
                seriesId
            )
            ||
            seriesId <= 0
        ) {

            return;
        }


        buttonElement.disabled =
            true;


        try {

            // =============================
            // 아직 시작 전
            // =============================

            if (
                seriesStatus
                === "scheduled"
            ) {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + `/api/fconline/series/`
                        + `${seriesId}`
                        + `/activate`,
                        {
                            method:
                                "POST",
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
            }


            localStorage.setItem(
                "fclCurrentSeriesId",
                String(
                    seriesId
                )
            );


            localStorage.setItem(
                "fclCurrentTournamentId",
                String(
                    currentTournamentId
                )
            );


            window.location.href =
                "./preseason.html?mode=result";


        } catch (error) {

            console.error(
                error
            );


            alert(
                error.message
            );


            buttonElement.disabled =
                false;
        }
    }
);


// =====================================================
// 새 대회
// =====================================================

newTournamentButtonElement.addEventListener(
    "click",
    () => {

        resetTournamentForm();


        createPanelElement.classList.remove(
            "hidden"
        );


        createPanelElement.scrollIntoView(
            {
                behavior:
                    "smooth",

                block:
                    "start",
            }
        );
    }
);


// =====================================================
// INIT
// =====================================================

resetTournamentForm();

loadTournamentList();