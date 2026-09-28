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