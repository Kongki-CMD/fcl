const isLiveServer =
    window.location.hostname === "127.0.0.1" &&
    window.location.port === "5500";

export const apiBaseUrl = isLiveServer
    ? "http://127.0.0.1:8000"
    : "";

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