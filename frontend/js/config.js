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