
"""
FCL NEXON 자동 동기화

- GitHub Actions에서 30분마다 실행
- 완료된 경기 중 pending 상태만 검사
- 경기 종료 150분 이후부터 검사
- 실행당 최대 2경기
- 기존 FCL 동기화 API 재사용
"""

import json
import os
import sys
import time

from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


KST = timezone(timedelta(hours=9))

MAX_PER_RUN = 2
LOOKBACK_DAYS = 30
MIN_DELAY_MINUTES = 150


# =========================================
# API 오류
# =========================================

class APIError(Exception):

    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


# =========================================
# 운영 서버 주소
# =========================================

def get_base_url():

    base = os.getenv(
        "FCL_BASE_URL", ""
    ).strip().rstrip("/")

    parsed = urlparse(base)

    is_local = parsed.hostname in {
        "localhost",
        "127.0.0.1",
    }

    valid_scheme = (
        parsed.scheme == "https"
        or (
            parsed.scheme == "http"
            and is_local
        )
    )

    if (
        not valid_scheme
        or not parsed.netloc
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "FCL_BASE_URL 설정을 확인해주세요."
        )

    return base


# =========================================
# FCL API 요청
# =========================================

def api_json(
    base,
    method,
    path,
    timeout=60,
):

    request = Request(
        f"{base}{path}",
        method=method,
        headers={
            "Accept": "application/json",
            "User-Agent": "FCL-AutoSync/1.0",
        },
    )

    try:

        with urlopen(
            request,
            timeout=timeout,
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except HTTPError as error:

        raise APIError(
            error.code,
            f"HTTP {error.code}",
        ) from error

    except (URLError, TimeoutError) as error:

        raise APIError(
            0,
            f"연결 오류: {error}",
        ) from error

    except (ValueError, UnicodeError) as error:

        raise APIError(
            0,
            "API JSON 응답 오류",
        ) from error


# =========================================
# 한국시간 변환
# =========================================

def parse_kst(value):

    if not value:
        return None

    try:

        result = datetime.fromisoformat(
            str(value).replace(
                "Z", "+00:00"
            )
        )

        if result.tzinfo is None:
            result = result.replace(
                tzinfo=KST
            )

        return result.astimezone(KST)

    except ValueError:
        return None


# =========================================
# 자동 동기화 대상 판정
# =========================================

def is_sync_target(row, now):

    if row.get("source") != "database":
        return False

    if row.get("stats_sync_status") != "pending":
        return False

    try:

        series_id = int(
            row["series_id"]
        )

        match_date = datetime.strptime(
            row["date"],
            "%Y-%m-%d",
        ).date()

    except (KeyError, ValueError, TypeError):
        return False

    if series_id <= 0:
        return False

    # 최근 30일 경기만 확인
    earliest = (
        now.date()
        - timedelta(days=LOOKBACK_DAYS)
    )

    if not (
        earliest <= match_date <= now.date()
    ):
        return False

    completed = parse_kst(
        row.get("completed_at")
    )

    # 완료 시각이 불명확하면 자동 처리하지 않음
    if completed is None:
        return False

    # 종료 후 최소 150분 경과
    if (
        now - completed
        < timedelta(minutes=MIN_DELAY_MINUTES)
    ):
        return False

    return True


# =========================================
# 대기 중인 경기 검색
# =========================================

def find_pending(base, now):

    season_data = api_json(
        base,
        "GET",
        "/api/seasons",
    )

    if not isinstance(season_data, dict):
        raise APIError(
            0,
            "시즌 API 응답 형식 오류",
        )

    seasons = season_data.get(
        "seasons", []
    )

    if not isinstance(seasons, list):
        raise APIError(
            0,
            "시즌 목록 형식 오류",
        )

    pending = {}

    season_numbers = sorted(
        {
            int(season["season_number"])
            for season in seasons
            if isinstance(season, dict)
            and str(
                season.get("season_number", "")
            ).isdigit()
        },
        reverse=True,
    )

    for season_number in season_numbers:

        results = api_json(
            base,
            "GET",
            "/api/fconline/series/completed-results"
            f"?season={season_number}",
        )

        if not isinstance(results, list):
            raise APIError(
                0,
                f"SEASON {season_number} 조회 오류",
            )

        for row in results:

            if not isinstance(row, dict):
                continue

            if not is_sync_target(row, now):
                continue

            series_id = int(
                row["series_id"]
            )

            # 시즌 간 중복 경기 제거
            pending[series_id] = {
                "series_id": series_id,
                "season": season_number,
                "date": row["date"],
            }

    return sorted(
        pending.values(),
        key=lambda item: (
            item["date"],
            item["series_id"],
        ),
        reverse=True,
    )


# =========================================
# 검사 대상 순환 선택
# =========================================

def choose_batch(candidates, now):

    if not candidates:
        return []

    # 매 30분마다 검사 시작 위치 변경
    start = (
        int(now.timestamp() // 1800)
        % len(candidates)
    )

    rotated = (
        candidates[start:]
        + candidates[:start]
    )

    return rotated[:MAX_PER_RUN]


# =========================================
# 자동 동기화 실행
# =========================================

def main():

    base = get_base_url()
    now = datetime.now(KST)

    # 초기 기본값은 안전한 미리보기 모드
    dry_run = (
        os.getenv(
            "FCL_DRY_RUN", "true"
        ).strip().lower() != "false"
    )

    candidates = find_pending(
        base, now
    )

    selected = choose_batch(
        candidates, now
    )

    print(
        f"[FCL] 대기 경기: {len(candidates)}건",
        flush=True,
    )

    print(
        f"[FCL] 이번 검사: {len(selected)}건",
        flush=True,
    )

    print(
        f"[FCL] 미리보기: {dry_run}",
        flush=True,
    )

    had_error = False

    for row in selected:

        series_id = row["series_id"]

        if dry_run:

            print(
                f"[DRY RUN] SEASON {row['season']} "
                f"/ SERIES {series_id} "
                f"/ {row['date']}",
                flush=True,
            )

            continue

        try:

            data = api_json(
                base,
                "POST",
                f"/api/fconline/series/{series_id}/sync",
                timeout=180,
            )

            if not isinstance(data, dict):
                raise APIError(
                    0,
                    "동기화 응답 형식 오류",
                )

            status = (
                data.get("series") or {}
            ).get(
                "stats_sync_status",
                "unknown",
            )

            message = str(
                data.get("sync_message") or ""
            )[:180]

            print(
                f"[FCL] SERIES {series_id} "
                f"→ {status} / {message}",
                flush=True,
            )

            # API 요청 간 간격
            time.sleep(1)

        except APIError as error:

            had_error = True

            print(
                f"[FCL] SERIES {series_id} "
                f"오류 ({error.status}): {error}",
                file=sys.stderr,
                flush=True,
            )

            # API 제한 시 추가 요청 중단
            if error.status == 429:
                break

    return 1 if had_error else 0


if __name__ == "__main__":

    try:
        sys.exit(main())

    except (
        APIError,
        ValueError,
        TypeError,
        KeyError,
    ) as error:

        print(
            f"[FCL] 자동 동기화 오류: {error}",
            file=sys.stderr,
            flush=True,
        )

        sys.exit(1)
