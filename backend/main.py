from pathlib import Path
from fastapi.staticfiles import StaticFiles


from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openpyxl import load_workbook


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

FRONTEND_DIR = PROJECT_DIR / "frontend"
EXCEL_PATH = BASE_DIR / "data" / "matches.xlsx"
RESULTS_PATH = BASE_DIR / "data" / "results.xlsx"
PLAYER_RANKINGS_PATH = BASE_DIR / "data" / "player_rankings.xlsx"

PARTICIPANTS = [
    "문권기",
    "이준석",
    "주은성",
    "이상",
    "서종원",
]


@app.get("/api/matches")
def get_matches():
    workbook = load_workbook(EXCEL_PATH)
    worksheet = workbook.active

    matches = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
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

@app.get("/api/matches/today")
def get_today_matches():
    workbook = load_workbook(EXCEL_PATH)
    worksheet = workbook.active

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()

    matches = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
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

@app.get("/api/results")
def get_results():
    workbook = load_workbook(RESULTS_PATH)
    worksheet = workbook.active

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()

    results = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        match_date, team_a, team_a_score, team_b_score, team_b = row

        if match_date is None:
            continue

        if hasattr(match_date, "date"):
            match_date = match_date.date()

        # 오늘 경기는 제외하고 어제까지의 결과만
        if match_date < today:
            results.append(
                {
                    "date": match_date.strftime("%Y-%m-%d"),
                    "team_a": team_a,
                    "team_a_score": team_a_score,
                    "team_b_score": team_b_score,
                    "team_b": team_b,
                }
            )

    workbook.close()

    # 최근 경기부터 표시
    results.sort(
        key=lambda result: result["date"],
        reverse=True
    )

    return results

@app.get("/api/standings")
def get_standings():
    workbook = load_workbook(RESULTS_PATH)
    worksheet = workbook["경기결과"]

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()

    standings = {}

    # 아직 경기를 하지 않은 참가자도 순위표에 표시하기 위해
    # 처음부터 모두 0으로 생성
    for participant in PARTICIPANTS:
        standings[participant] = {
            "name": participant,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "goal_difference": 0,
            "points": 0,
        }

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        match_date, team_a, team_a_score, team_b_score, team_b = row

        if match_date is None:
            continue

        if hasattr(match_date, "date"):
            match_date = match_date.date()

        # 미래 경기 제외
        if match_date > today:
            continue

        # 아직 점수가 입력되지 않은 경기는 제외
        if team_a_score is None or team_b_score is None:
            continue

        # 혹시 모르는 팀명이 들어간 경우 제외
        if team_a not in standings or team_b not in standings:
            continue

        team_a_score = int(team_a_score)
        team_b_score = int(team_b_score)

        team_a_record = standings[team_a]
        team_b_record = standings[team_b]

        # 경기수
        team_a_record["played"] += 1
        team_b_record["played"] += 1

        # 득점 / 실점
        team_a_record["goals_for"] += team_a_score
        team_a_record["goals_against"] += team_b_score

        team_b_record["goals_for"] += team_b_score
        team_b_record["goals_against"] += team_a_score

        # 승 / 무 / 패 / 승점
        if team_a_score > team_b_score:
            team_a_record["wins"] += 1
            team_a_record["points"] += 3

            team_b_record["losses"] += 1

        elif team_a_score < team_b_score:
            team_b_record["wins"] += 1
            team_b_record["points"] += 3

            team_a_record["losses"] += 1

        else:
            team_a_record["draws"] += 1
            team_b_record["draws"] += 1

            team_a_record["points"] += 1
            team_b_record["points"] += 1

    workbook.close()

    # 득실차 계산
    for record in standings.values():
        record["goal_difference"] = (
            record["goals_for"] - record["goals_against"]
        )

    participant_order = {
        participant: index
        for index, participant in enumerate(PARTICIPANTS)
    }

    # 승점 → 득실차 → 득점 순
    sorted_standings = sorted(
        standings.values(),
        key=lambda record: (
            -record["points"],
            -record["goal_difference"],
            -record["goals_for"],
            participant_order[record["name"]],
        ),
    )

    # 순위 추가
    for index, record in enumerate(sorted_standings, start=1):
        record["rank"] = index

    return sorted_standings

@app.get("/api/player-rankings")
def get_player_rankings():
    workbook = load_workbook(PLAYER_RANKINGS_PATH)
    worksheet = workbook["선수득점"]

    players = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        season, player_name, goals = row

        # 빈 행 제외
        if season is None and player_name is None and goals is None:
            continue

        # 선수 이름이 없는 행 제외
        if player_name is None:
            continue

        # 득점이 비어 있으면 0점
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

    # 득점 높은 순
    players.sort(
        key=lambda player: player["goals"],
        reverse=True
    )

    # 순위 추가
    for index, player in enumerate(players, start=1):
        player["rank"] = index

    return players

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True,
    ),
    name="frontend",
)