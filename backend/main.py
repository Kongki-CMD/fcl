from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from openpyxl import load_workbook


# =========================
# FastAPI
# =========================

app = FastAPI()


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 파일 경로
# =========================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

FRONTEND_DIR = PROJECT_DIR / "frontend"

EXCEL_PATH = BASE_DIR / "data" / "matches.xlsx"
RESULTS_PATH = BASE_DIR / "data" / "results.xlsx"
PLAYER_RANKINGS_PATH = BASE_DIR / "data" / "player_rankings.xlsx"
PLAYOFFS_PATH = BASE_DIR / "data" / "playoffs.xlsx"


# =========================
# 참가자
# =========================

PARTICIPANTS = [
    "문권기",
    "이준석",
    "주은성",
    "이상",
    "서종원",
]


# =========================
# 전체 경기 일정
# =========================

@app.get("/api/matches")
def get_matches():

    workbook = load_workbook(EXCEL_PATH)

    worksheet = workbook["경기일정"]

    matches = []

    for row in worksheet.iter_rows(
        min_row=2,
        max_col=3,
        values_only=True,
    ):
        match_date, team_a, team_b = row

        if match_date is None:
            continue

        if hasattr(match_date, "strftime"):
            match_date = match_date.strftime("%Y-%m-%d")

        matches.append(
            {
                "date": str(match_date),
                "team_a": team_a,
                "team_b": team_b,
            }
        )

    workbook.close()

    return matches


# =========================
# 오늘 경기
# =========================

@app.get("/api/matches/today")
def get_today_matches():

    workbook = load_workbook(EXCEL_PATH)

    worksheet = workbook["경기일정"]

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    matches = []

    for row in worksheet.iter_rows(
        min_row=2,
        max_col=3,
        values_only=True,
    ):
        match_date, team_a, team_b = row

        if match_date is None:
            continue

        if hasattr(match_date, "date"):
            match_date = match_date.date()

        if match_date == today:

            matches.append(
                {
                    "date": match_date.strftime("%Y-%m-%d"),
                    "team_a": team_a,
                    "team_b": team_b,
                }
            )

    workbook.close()

    return matches


# =========================
# 경기 결과
# =========================

@app.get("/api/results")
def get_results():

    workbook = load_workbook(RESULTS_PATH)

    worksheet = workbook["경기결과"]

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    results = []

    # 중요:
    # results.xlsx 오른쪽에 메모가 있어도
    # 실제 경기 데이터인 A~I열까지만 읽음
    for row in worksheet.iter_rows(
        min_row=2,
        max_col=9,
        values_only=True,
    ):

        (
            match_date,
            team_a,
            set1_a,
            set1_b,
            set2_a,
            set2_b,
            set3_a,
            set3_b,
            team_b,
        ) = row

        if match_date is None:
            continue

        if hasattr(match_date, "date"):
            match_date = match_date.date()

        # 경기 결과 페이지는 전날까지
        if match_date >= today:
            continue

        scores = [
            set1_a,
            set1_b,
            set2_a,
            set2_b,
            set3_a,
            set3_b,
        ]

        # 3세트 모두 입력되어야 완료 경기
        if any(score is None for score in scores):
            continue

        set1_a = int(set1_a)
        set1_b = int(set1_b)

        set2_a = int(set2_a)
        set2_b = int(set2_b)

        set3_a = int(set3_a)
        set3_b = int(set3_b)

        # 기존 결과 화면과의 호환을 위한 총 득점
        team_a_total_score = (
            set1_a
            + set2_a
            + set3_a
        )

        team_b_total_score = (
            set1_b
            + set2_b
            + set3_b
        )

        results.append(
            {
                "date": match_date.strftime("%Y-%m-%d"),

                "team_a": team_a,
                "team_b": team_b,

                # 기존 JS 호환용
                "team_a_score": team_a_total_score,
                "team_b_score": team_b_total_score,

                # 새 3세트 데이터
                "sets": [
                    {
                        "set": 1,
                        "team_a_score": set1_a,
                        "team_b_score": set1_b,
                    },
                    {
                        "set": 2,
                        "team_a_score": set2_a,
                        "team_b_score": set2_b,
                    },
                    {
                        "set": 3,
                        "team_a_score": set3_a,
                        "team_b_score": set3_b,
                    },
                ],
            }
        )

    workbook.close()

    # 최신 경기부터
    results.sort(
        key=lambda result: result["date"],
        reverse=True,
    )

    return results


# =========================
# 팀 순위
# =========================

@app.get("/api/standings")
def get_standings():

    workbook = load_workbook(RESULTS_PATH)

    worksheet = workbook["경기결과"]

    today = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).date()

    standings = {}

    # 모든 참가자 기본 데이터
    for participant in PARTICIPANTS:

        standings[participant] = {
            "name": participant,

            # 실제 매치 수
            "played": 0,

            # 승/무/패는 세트 기준
            "wins": 0,
            "draws": 0,
            "losses": 0,

            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,

            "points": 0,
        }


    # A~I열만 읽기
    for row in worksheet.iter_rows(
        min_row=2,
        max_col=9,
        values_only=True,
    ):

        (
            match_date,
            team_a,
            set1_a,
            set1_b,
            set2_a,
            set2_b,
            set3_a,
            set3_b,
            team_b,
        ) = row


        if match_date is None:
            continue


        if hasattr(match_date, "date"):
            match_date = match_date.date()


        # 미래 경기 제외
        if match_date > today:
            continue


        scores = [
            set1_a,
            set1_b,
            set2_a,
            set2_b,
            set3_a,
            set3_b,
        ]


        # 3세트 모두 입력되어야 순위 계산
        if any(score is None for score in scores):
            continue


        if (
            team_a not in standings
            or team_b not in standings
        ):
            continue


        team_a_record = standings[team_a]
        team_b_record = standings[team_b]


        # =========================
        # 매치 수
        # =========================

        team_a_record["played"] += 1
        team_b_record["played"] += 1


        # =========================
        # 3세트
        # =========================

        sets = [
            (
                int(set1_a),
                int(set1_b),
            ),
            (
                int(set2_a),
                int(set2_b),
            ),
            (
                int(set3_a),
                int(set3_b),
            ),
        ]


        # =========================
        # 세트별 계산
        # =========================

        for team_a_score, team_b_score in sets:

            # 득점 / 실점
            team_a_record["goals_for"] += team_a_score
            team_a_record["goals_against"] += team_b_score

            team_b_record["goals_for"] += team_b_score
            team_b_record["goals_against"] += team_a_score


            # -------------------------
            # 팀A 승리
            # -------------------------

            if team_a_score > team_b_score:

                team_a_record["wins"] += 1
                team_a_record["points"] += 3

                team_b_record["losses"] += 1


            # -------------------------
            # 팀B 승리
            # -------------------------

            elif team_a_score < team_b_score:

                team_b_record["wins"] += 1
                team_b_record["points"] += 3

                team_a_record["losses"] += 1


            # -------------------------
            # 무승부
            # -------------------------

            else:

                team_a_record["draws"] += 1
                team_b_record["draws"] += 1

                team_a_record["points"] += 1
                team_b_record["points"] += 1


    workbook.close()


    # =========================
    # 득실차
    # =========================

    for record in standings.values():

        record["goal_difference"] = (
            record["goals_for"]
            - record["goals_against"]
        )


    # =========================
    # 동률 시 기존 참가자 순서
    # =========================

    participant_order = {
        participant: index
        for index, participant in enumerate(PARTICIPANTS)
    }


    # =========================
    # 순위 정렬
    #
    # 1. 승점
    # 2. 득실차
    # 3. 득점
    # =========================

    sorted_standings = sorted(
        standings.values(),
        key=lambda record: (
            -record["points"],
            -record["goal_difference"],
            -record["goals_for"],
            participant_order[record["name"]],
        ),
    )


    # =========================
    # 순위 번호
    # =========================

    for index, record in enumerate(
        sorted_standings,
        start=1,
    ):
        record["rank"] = index


    return sorted_standings


# =========================
# 선수 득점 순위
# =========================

@app.get("/api/player-rankings")
def get_player_rankings():

    workbook = load_workbook(
        PLAYER_RANKINGS_PATH
    )

    worksheet = workbook["선수득점"]

    players = []


    for row in worksheet.iter_rows(
        min_row=2,
        max_col=3,
        values_only=True,
    ):

        season, player_name, goals = row


        # 완전 빈 행
        if (
            season is None
            and player_name is None
            and goals is None
        ):
            continue


        if player_name is None:
            continue


        if goals is None:
            goals = 0


        players.append(
            {
                "season": season,
                "player_name": player_name,
                "goals": int(goals),
            }
        )


    workbook.close()


    # 득점순
    players.sort(
        key=lambda player: player["goals"],
        reverse=True,
    )


    # 순위
    for index, player in enumerate(
        players,
        start=1,
    ):
        player["rank"] = index


    return players


# =========================
# 플레이오프 일정
# =========================

@app.get("/api/playoffs")
def get_playoffs():

    workbook = load_workbook(
        PLAYOFFS_PATH
    )

    worksheet = workbook["플레이오프"]

    playoffs = []


    for row in worksheet.iter_rows(
        min_row=2,
        max_col=4,
        values_only=True,
    ):

        (
            match_date,
            stage,
            team_a,
            team_b,
        ) = row


        if match_date is None:
            continue


        if hasattr(match_date, "strftime"):
            match_date = match_date.strftime(
                "%Y-%m-%d"
            )


        playoffs.append(
            {
                "date": str(match_date),
                "stage": stage,
                "team_a": team_a,
                "team_b": team_b,
            }
        )


    workbook.close()

    return playoffs


# =========================
# 프론트엔드
#
# 반드시 API 선언보다 아래에 위치
# =========================

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True,
    ),
    name="frontend",
)