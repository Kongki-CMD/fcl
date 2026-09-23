import {
    apiBaseUrl,
} from "./config.js";


const recordListElement =
    document.querySelector(
        "#tournament-record-list"
    );


const detailElement =
    document.querySelector(
        "#tournament-record-detail"
    );


const detailTitleElement =
    document.querySelector(
        "#tournament-record-title"
    );


const detailDateElement =
    document.querySelector(
        "#tournament-record-date"
    );


const detailInfoElement =
    document.querySelector(
        "#tournament-record-info"
    );


const championElement =
    document.querySelector(
        "#tournament-record-champion"
    );


const bracketElement =
    document.querySelector(
        "#tournament-record-bracket"
    );


let currentTournamentId =
    null;


// =====================================================
// HTML ESCAPE
// =====================================================

function escapeTournamentRecordHtml(
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
// 목록
// =====================================================

async function loadTournamentRecords() {

    try {

        const response = await fetch(
            `${apiBaseUrl}/api/tournaments`
        );


        if (!response.ok) {

            throw new Error(
                "토너먼트 기록을 불러오지 못했습니다."
            );
        }


        const tournaments =
            await response.json();


        const completedTournaments =
            tournaments.filter(
                tournament =>
                    tournament.status
                    === "completed"
            );


        renderTournamentRecords(
            completedTournaments
        );


        if (
            completedTournaments.length
            > 0
        ) {

            currentTournamentId =
                completedTournaments[0]
                    .tournament_id;


            await loadTournamentRecordDetail(
                currentTournamentId
            );
        }


    } catch (error) {

        console.error(
            error
        );


        recordListElement.innerHTML = `
            <p class="tournament-record-empty">
                토너먼트 기록을 불러오지 못했습니다.
            </p>
        `;
    }
}


function renderTournamentRecords(
    tournaments
) {

    recordListElement.innerHTML =
        "";


    if (
        tournaments.length === 0
    ) {

        recordListElement.innerHTML = `
            <p class="tournament-record-empty">
                아직 완료된 토너먼트 기록이 없습니다.
            </p>
        `;


        detailElement.classList.add(
            "hidden"
        );


        return;
    }


    tournaments.forEach(
        tournament => {

            const cardElement =
                document.createElement(
                    "button"
                );


            cardElement.type =
                "button";


            cardElement.classList.add(
                "tournament-record-card"
            );


            cardElement.dataset.tournamentId =
                tournament.tournament_id;


            if (
                tournament.tournament_id
                ===
                currentTournamentId
            ) {

                cardElement.classList.add(
                    "active"
                );
            }


            cardElement.innerHTML = `
                <div
                    class="
                        tournament-record-card-main
                    "
                >

                    <span
                        class="
                            tournament-record-card-date
                        "
                    >
                        ${
                            escapeTournamentRecordHtml(
                                tournament.date
                            )
                        }
                    </span>


                    <strong>
                        ${
                            escapeTournamentRecordHtml(
                                tournament.title
                            )
                        }
                    </strong>


                    <span
                        class="
                            tournament-record-card-count
                        "
                    >
                        ${
                            tournament
                                .participant_count
                        }명 참가
                    </span>

                </div>


                <div
                    class="
                        tournament-record-card-champion
                    "
                >

                    <span>
                        🏆 우승
                    </span>

                    <strong>
                        ${
                            escapeTournamentRecordHtml(
                                tournament.champion
                                    ?.name
                                ?? "-"
                            )
                        }
                    </strong>

                </div>
            `;


            recordListElement.appendChild(
                cardElement
            );
        }
    );
}


// =====================================================
// 상세
// =====================================================

async function loadTournamentRecordDetail(
    tournamentId
) {

    try {

        const response = await fetch(
            `${apiBaseUrl}`
            + `/api/tournaments/`
            + `${tournamentId}`
        );


        const tournament =
            await response.json();


        if (!response.ok) {

            throw new Error(
                tournament.detail
                ??
                "토너먼트 기록을 불러오지 못했습니다."
            );
        }


        renderTournamentRecordDetail(
            tournament
        );


    } catch (error) {

        console.error(
            error
        );


        detailElement.classList.remove(
            "hidden"
        );


        bracketElement.innerHTML = `
            <p class="tournament-record-empty">
                ${
                    escapeTournamentRecordHtml(
                        error.message
                    )
                }
            </p>
        `;
    }
}


function renderTournamentRecordParticipant(
    participant,
    winner
) {

    if (!participant) {

        return `
            <div
                class="
                    tournament-record-player
                    empty
                "
            >
                -
            </div>
        `;
    }


    const isWinner =
        winner
        &&
        winner.entry_id
        ===
        participant.entry_id;


    return `
        <div
            class="
                tournament-record-player
                ${
                    isWinner
                        ? "winner"
                        : ""
                }
            "
        >

            <span>
                ${
                    escapeTournamentRecordHtml(
                        participant.name
                    )
                }
            </span>

            ${
                isWinner
                    ? `
                        <strong>
                            WIN
                        </strong>
                    `
                    : ""
            }

        </div>
    `;
}


function renderTournamentRecordMatch(
    match
) {

    return `
        <article
            class="
                tournament-record-match
            "
        >

            <span
                class="
                    tournament-record-match-number
                "
            >
                MATCH
                ${match.match_number}
            </span>


            ${
                renderTournamentRecordParticipant(
                    match.participant_a,
                    match.winner
                )
            }


            <span
                class="
                    tournament-record-vs
                "
            >
                VS
            </span>


            ${
                renderTournamentRecordParticipant(
                    match.participant_b,
                    match.winner
                )
            }


            ${
                match.is_bye
                    ? `
                        <div
                            class="
                                tournament-record-result
                            "
                        >
                            부전승 ·
                            ${
                                escapeTournamentRecordHtml(
                                    match.winner
                                        ?.name
                                    ?? ""
                                )
                            }
                        </div>
                    `
                    : (
                        match.winner
                            ? `
                                <div
                                    class="
                                        tournament-record-result
                                    "
                                >
                                    승자 ·
                                    ${
                                        escapeTournamentRecordHtml(
                                            match.winner.name
                                        )
                                    }
                                </div>
                            `
                            : ""
                    )
            }

        </article>
    `;
}


function renderTournamentRecordDetail(
    tournament
) {

    detailElement.classList.remove(
        "hidden"
    );


    detailTitleElement.textContent =
        tournament.title;


    detailDateElement.textContent =
        tournament.date;


    detailInfoElement.textContent =
        (
            `${tournament.participant_count}명 참가`
            +
            ` · ${tournament.bracket_size}강`
        );


    championElement.innerHTML = `
        <span>
            🏆 CHAMPION
        </span>

        <strong>
            ${
                escapeTournamentRecordHtml(
                    tournament.champion
                        ?.name
                    ?? "-"
                )
            }
        </strong>
    `;


    bracketElement.innerHTML =
        "";


    tournament.rounds.forEach(
        round => {

            const roundElement =
                document.createElement(
                    "section"
                );


            roundElement.classList.add(
                "tournament-record-round"
            );


            roundElement.innerHTML = `
                <div
                    class="
                        tournament-record-round-title
                    "
                >
                    ${
                        escapeTournamentRecordHtml(
                            round.round_name
                        )
                    }
                </div>


                <div
                    class="
                        tournament-record-round-matches
                    "
                >

                    ${
                        round.matches
                            .map(
                                match =>
                                    renderTournamentRecordMatch(
                                        match
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
// 기록 선택
// =====================================================

recordListElement.addEventListener(
    "click",
    async event => {

        const cardElement =
            event.target.closest(
                "[data-tournament-id]"
            );


        if (!cardElement) {
            return;
        }


        currentTournamentId =
            Number(
                cardElement.dataset
                    .tournamentId
            );


        recordListElement
            .querySelectorAll(
                ".tournament-record-card"
            )
            .forEach(
                element => {

                    element.classList.remove(
                        "active"
                    );
                }
            );


        cardElement.classList.add(
            "active"
        );


        await loadTournamentRecordDetail(
            currentTournamentId
        );
    }
);


// =====================================================
// INIT
// =====================================================

loadTournamentRecords();