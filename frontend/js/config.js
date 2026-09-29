const isLiveServer =
    window.location.hostname === "127.0.0.1" &&
    window.location.port === "5500";

export const apiBaseUrl = isLiveServer
    ? "http://127.0.0.1:8000"
    : "";

// =========================================
// FCL 시즌 목록 캐시
//
// 페이지 이동마다 /api/seasons를
// 다시 호출하지 않도록 짧게 캐시
// =========================================

const fclSeasonsCacheKey =
    "fclSeasonsCacheV1";

const fclSeasonsCacheTtlMs =
    30 * 1000;


export async function loadFclSeasons() {

    const now =
        Date.now();


    try {

        const cachedText =
            sessionStorage.getItem(
                fclSeasonsCacheKey
            );


        if (cachedText) {

            const cached =
                JSON.parse(
                    cachedText
                );


            if (
                Array.isArray(
                    cached.seasons
                )
                &&
                (
                    now
                    -
                    Number(
                        cached.savedAt
                    )
                )
                <
                fclSeasonsCacheTtlMs
            ) {

                return cached.seasons;
            }
        }

    } catch (error) {

        console.error(
            error
        );
    }


    const response = await fetch(
        `${apiBaseUrl}/api/seasons`
    );


    if (!response.ok) {

        throw new Error(
            "시즌 정보를 불러오지 못했습니다."
        );
    }


    const data =
        await response.json();


    const seasons =
        data.seasons
        ?? [];


    try {

        sessionStorage.setItem(
            fclSeasonsCacheKey,
            JSON.stringify(
                {
                    savedAt:
                        now,

                    seasons:
                        seasons,
                }
            )
        );

    } catch (error) {

        console.error(
            error
        );
    }


    return seasons;
}

// =========================================
// 공개 페이지 기본 표시 시즌
//
// 명시적 ?season=N
//     ↓
// 첫 경기 2일 전이 된 최신 시즌
//     ↓
// 현재 active 시즌
//     ↓
// 가장 최근 completed 시즌
//     ↓
// 마지막 등록 시즌
//
// 실제 seasons.status를 변경하지 않고
// 공개 화면의 기본 표시만 전환한다.
// =========================================

const publicSeasonSwitchLeadDays =
    2;


function getKstTodayIsoDate() {

    const parts =
        new Intl.DateTimeFormat(
            "en-US",
            {
                timeZone:
                    "Asia/Seoul",

                year:
                    "numeric",

                month:
                    "2-digit",

                day:
                    "2-digit",
            }
        ).formatToParts(
            new Date()
        );


    const partMap = {};


    parts.forEach(
        part => {

            if (
                part.type
                !== "literal"
            ) {

                partMap[
                    part.type
                ] = part.value;
            }
        }
    );


    return (
        `${partMap.year}`
        + `-${partMap.month}`
        + `-${partMap.day}`
    );
}


function addDaysToIsoDate(
    isoDate,
    dayOffset
) {

    if (
        typeof isoDate
        !== "string"
        ||
        !/^\d{4}-\d{2}-\d{2}$/
            .test(
                isoDate
            )
    ) {

        return null;
    }


    const [
        year,
        month,
        day,
    ] = (
        isoDate
            .split("-")
            .map(Number)
    );


    const date =
        new Date(
            Date.UTC(
                year,
                month - 1,
                day
            )
        );


    date.setUTCDate(
        date.getUTCDate()
        + dayOffset
    );


    return (
        date
            .toISOString()
            .slice(
                0,
                10
            )
    );
}


export function resolvePublicDisplaySeason(
    seasons,
    requestedSeasonNumber = null
) {

    const safeSeasons =
        Array.isArray(
            seasons
        )
            ? seasons
            : [];


    if (
        safeSeasons.length
        === 0
    ) {

        return null;
    }


    // =========================
    // URL에서 시즌을 명시한 경우
    // 항상 최우선
    //
    // 예:
    // ?season=1
    // =========================

    if (
        Number.isInteger(
            requestedSeasonNumber
        )
        &&
        requestedSeasonNumber > 0
    ) {

        const requestedSeason =
            safeSeasons.find(
                season =>
                    Number(
                        season.season_number
                    )
                    ===
                    requestedSeasonNumber
            );


        if (requestedSeason) {

            return requestedSeason;
        }
    }


    const today =
        getKstTodayIsoDate();


    // =========================
    // 공개 화면 자동 전환 대상
    //
    // - upcoming 또는 active
    // - 시작일 존재
    // - 실제 SERIES 존재
    // - 첫 경기 2일 전 도달
    //
    // 여러 시즌이 해당되면
    // 가장 높은 시즌 번호 선택
    // =========================

    const automaticDisplaySeason =
        safeSeasons
            .filter(
                season => {

                    if (
                        season.status
                        !== "upcoming"
                        &&
                        season.status
                        !== "active"
                    ) {

                        return false;
                    }


                    if (
                        !season.start_date
                    ) {

                        return false;
                    }


                    if (
                        Number(
                            season.series_count
                            ?? 0
                        )
                        <= 0
                    ) {

                        return false;
                    }


                    const switchDate =
                        addDaysToIsoDate(
                            season.start_date,
                            -publicSeasonSwitchLeadDays
                        );


                    if (!switchDate) {

                        return false;
                    }


                    return (
                        today
                        >=
                        switchDate
                    );
                }
            )
            .sort(
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
            )[0]
            ?? null;


    if (automaticDisplaySeason) {

        return automaticDisplaySeason;
    }


    // 아직 다음 시즌 공개 시점 전이면
    // 실제 active 시즌 유지
    const activeSeason =
        safeSeasons.find(
            season =>
                season.status
                === "active"
        );


    if (activeSeason) {

        return activeSeason;
    }


    // active가 없는 시즌 종료 구간에서는
    // 가장 최근 종료 시즌 유지
    const completedSeason =
        safeSeasons
            .filter(
                season =>
                    season.status
                    === "completed"
            )
            .sort(
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
            )[0]
            ?? null;


    if (completedSeason) {

        return completedSeason;
    }


    // 최종 안전 fallback
    return (
        [...safeSeasons]
            .sort(
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
            )[0]
        ?? null
    );
}

export const teamImageMap = {
    "문권기": "./assets/images/teams/moon.png",
    "이준석": "./assets/images/teams/junseok.png",
    "주은성": "./assets/images/teams/joo.png",
    "이상": "./assets/images/teams/sang.png",
    "서종원": "./assets/images/teams/seo.png",
};

const defaultTeamImagePath = "./assets/images/teams/default.png";

export function getTeamImagePath(teamName) {
    return teamImageMap[teamName] ?? defaultTeamImagePath;
}

// =========================================
// ISO 시간 -> 한국시간(KST)
// =========================================

export function formatKstDateTime(
    isoDateTime
) {

    if (!isoDateTime) {
        return "-";
    }


    const dateTime =
        new Date(
            isoDateTime
        );


    if (
        Number.isNaN(
            dateTime.getTime()
        )
    ) {
        return isoDateTime;
    }


    const formatter =
        new Intl.DateTimeFormat(
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

                hourCycle:
                    "h23",
            }
        );


    const dateTimeParts =
        Object.fromEntries(
            formatter
                .formatToParts(
                    dateTime
                )
                .filter(
                    part =>
                        part.type
                        !== "literal"
                )
                .map(
                    part => [
                        part.type,
                        part.value,
                    ]
                )
        );


    return (
        `${dateTimeParts.year}`
        + `-${dateTimeParts.month}`
        + `-${dateTimeParts.day}`
        + ` ${dateTimeParts.hour}`
        + `:${dateTimeParts.minute}`
    );
}