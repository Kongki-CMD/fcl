import os
import re

import httpx
import psycopg

from bs4 import BeautifulSoup


# =========================================
# FC ONLINE TEAM COLOR CATALOG
# =========================================

BASE_URL = (
    "https://fconline.nexon.com"
)

TEAM_COLOR_URL = (
    f"{BASE_URL}"
    "/datacenter/teamcolor"
)

TEAM_COLOR_DETAIL_URL = (
    f"{BASE_URL}"
    "/datacenter/TeamColorDetail"
)

TEAM_COLOR_PLAYER_LIST_URL = (
    f"{BASE_URL}"
    "/DataCenter/TeamColorPlayerList"
)

TEAM_COLOR_PLAYER_RESULT_LIMIT = 100

TEAM_COLOR_PLAYER_OVR_MIN = 1
TEAM_COLOR_PLAYER_OVR_MAX = 200

TEAM_COLOR_PLAYER_SALARY_MIN = 0
TEAM_COLOR_PLAYER_SALARY_MAX = 999

TEAM_COLOR_SEASON_META_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/seasonid.json"
)


TEAM_COLOR_POSITION_GROUPS = (
    (
        "FW",
        ",24,25,26,20,21,22,27,23,",
        (
            ",24,",
            ",25,",
            ",26,",
            ",20,",
            ",21,",
            ",22,",
            ",27,",
            ",23,",
        ),
    ),
    (
        "MF",
        ",13,14,15,17,18,19,9,10,11,16,12,",
        (
            ",13,",
            ",14,",
            ",15,",
            ",17,",
            ",18,",
            ",19,",
            ",9,",
            ",10,",
            ",11,",
            ",16,",
            ",12,",
        ),
    ),
    (
        "DF",
        ",1,4,5,6,3,7,2,8,",
        (
            ",1,",
            ",4,",
            ",5,",
            ",6,",
            ",3,",
            ",7,",
            ",2,",
            ",8,",
        ),
    ),
    (
        "GK",
        ",0,",
        (
            ",0,",
        ),
    ),
)


TEAM_COLOR_SEASON_IDS_CACHE = None


DATABASE_URL = os.getenv(
    "DATABASE_URL"
)


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
}


TEAM_COLOR_CATEGORY_VALUES = {
    "affiliation":
        "affiliation",

    "feature":
        "feature",

    "enhance":
        "enhance",
}


TEAM_COLOR_TYPE_VALUES = {
    "club":
        "club",

    "nation":
        "nation",

    "grade":
        "grade",

    "relation":
        "relation",

    "special":
        "special",
}


TEAM_COLOR_ID_PATTERN = re.compile(
    r"GetTeamColorDetail"
    r"\(\s*(\d+)\s*\)"
)


TEAM_COLOR_STAGE_PATTERN = re.compile(
    r"(\d+)\s*단계"
)


TEAM_COLOR_EFFECT_PATTERN = re.compile(
    r"^(.*?)\s*\+\s*(-?\d+)\s*$"
)


# =========================================
# 공식 능력치명 → 내부 key
#
# 지금 단계에서는 저장만 하고,
# 3-5에서 player stat key와 최종 연결한다.
# =========================================

TEAM_COLOR_STAT_KEY_MAP = {

    "전체 능력치":
        "__all__",

    "속력":
        "sprint_speed",

    "가속력":
        "acceleration",

    "골 결정력":
        "finishing",

    "골결정력":
        "finishing",

    "슛 파워":
        "shot_power",

    "슛파워":
        "shot_power",

    "중거리 슛":
        "long_shots",

    "중거리슛":
        "long_shots",

    "위치 선정":
        "positioning",

    "위치선정":
        "positioning",

    "발리슛":
        "volleys",

    "발리 슛":
        "volleys",

    "패널티킥":
        "penalties",

    "페널티킥":
        "penalties",

    "패널티 킥":
        "penalties",

    "페널티 킥":
        "penalties",

    "짧은 패스":
        "short_passing",

    "짧은패스":
        "short_passing",

    "시야":
        "vision",

    "크로스":
        "crossing",

    "긴 패스":
        "long_passing",

    "긴패스":
        "long_passing",

    "가로채기":
        "interceptions",

    "프리킥":
        "free_kick_accuracy",

    "커브":
        "curve",

    "드리블":
        "dribbling",

    "볼 컨트롤":
        "ball_control",

    "볼컨트롤":
        "ball_control",

    "민첩성":
        "agility",

    "밸런스":
        "balance",

    "반응 속도":
        "reactions",

    "반응속도":
        "reactions",

    "대인 수비":
        "marking",

    "대인수비":
        "marking",

    "태클":
        "standing_tackle",

    "헤더":
        "heading_accuracy",

    "슬라이딩 태클":
        "sliding_tackle",

    "슬라이딩태클":
        "sliding_tackle",

    "몸싸움":
        "strength",

    "스태미너":
        "stamina",

    "적극성":
        "aggression",

    "점프":
        "jumping",

    "침착성":
        "composure",

    "GK 다이빙":
        "gk_diving",

    "GK 핸들링":
        "gk_handling",

    "GK 킥":
        "gk_kicking",

    "GK 반응속도":
        "gk_reflexes",

    "GK 반응 속도":
        "gk_reflexes",

    "GK 위치 선정":
        "gk_positioning",

    "GK 위치선정":
        "gk_positioning",
}


# =========================================
# TEXT
# =========================================

def normalize_text(
    value,
):

    return (
        " ".join(
            str(
                value
                or ""
            )
            .split()
        )
    )


def normalize_stat_name(
    value,
):

    return normalize_text(
        value
    )


def get_stat_key(
    stat_name,
):

    normalized_name = (
        normalize_stat_name(
            stat_name
        )
    )


    return (
        TEAM_COLOR_STAT_KEY_MAP
        .get(
            normalized_name
        )
        or
        (
            "unknown:"
            +
            normalized_name
        )
    )


# =========================================
# HTML FETCH
# =========================================

def fetch_team_color_page(
    client,
    params=None,
):

    response = client.get(
        TEAM_COLOR_URL,
        params=(
            params
            or {}
        ),
    )


    response.raise_for_status()


    return BeautifulSoup(
        response.text,
        "html.parser",
    )

# =========================================
# TEAM COLOR DETAIL FETCH
# =========================================

def fetch_team_color_detail(
    client,
    team_color_id,
):

    detail_url = (
        f"{TEAM_COLOR_DETAIL_URL}"
        f"?teamcolorid={int(team_color_id)}"
        f"&_1"
    )


    response = client.get(
        detail_url,
        headers={
            "Referer":
                TEAM_COLOR_URL,

            "X-Requested-With":
                "XMLHttpRequest",
        },
    )


    response.raise_for_status()


    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )


    # =========================
    # 넥슨 공통 오류 페이지 방어
    # =========================

    if soup.select_one(
        "#ErrorMessage"
    ):

        raise RuntimeError(
            (
                "팀컬러 상세 페이지 대신 "
                "NEXON 오류 페이지가 반환됐습니다: "
                f"{team_color_id} "
                f"url={response.url}"
            )
        )


    return soup


def serialize_team_color_search_form(
    detail_soup,
):

    form = detail_soup.select_one(
        "#teacolorSearchform"
    )


    if form is None:

        raise RuntimeError(
            (
                "팀컬러 상세 페이지에서 "
                "#teacolorSearchform을 "
                "찾을 수 없습니다."
            )
        )


    params = []


    # =========================
    # INPUT
    # =========================

    for element in form.select(
        "input[name]"
    ):

        if element.has_attr(
            "disabled"
        ):
            continue


        input_type = (
            element.get(
                "type",
                "text",
            )
            .lower()
        )


        if (
            input_type
            in (
                "checkbox",
                "radio",
            )
            and
            not element.has_attr(
                "checked"
            )
        ):

            continue


        params.append(
            (
                element.get(
                    "name"
                ),
                element.get(
                    "value",
                    "",
                ),
            )
        )


    # =========================
    # SELECT
    # =========================

    for element in form.select(
        "select[name]"
    ):

        if element.has_attr(
            "disabled"
        ):
            continue


        name = (
            element.get(
                "name"
            )
        )


        selected_options = (
            element.select(
                "option[selected]"
            )
        )


        if not selected_options:

            first_option = (
                element.select_one(
                    "option"
                )
            )


            if first_option is None:
                continue


            selected_options = [
                first_option
            ]


        for option in selected_options:

            params.append(
                (
                    name,
                    option.get(
                        "value",
                        "",
                    ),
                )
            )


    # =========================
    # TEXTAREA
    # =========================

    for element in form.select(
        "textarea[name]"
    ):

        if element.has_attr(
            "disabled"
        ):
            continue


        params.append(
            (
                element.get(
                    "name"
                ),
                element.get_text(),
            )
        )


    return params


def fetch_team_color_player_list(
    client,
    detail_soup,
    overrides=None,
):

    params = dict(
        serialize_team_color_search_form(
            detail_soup
        )
    )


    for (
        parameter_name,
        parameter_value,
    ) in (
        overrides
        or {}
    ).items():

        params[
            parameter_name
        ] = str(
            parameter_value
        )


    params[
        "rd"
    ] = "1"


    response = client.get(
        TEAM_COLOR_PLAYER_LIST_URL,
        params=params,
        headers={
            "Referer":
                TEAM_COLOR_DETAIL_URL,

            "X-Requested-With":
                "XMLHttpRequest",
        },
    )


    response.raise_for_status()


    try:

        data = (
            response.json()
        )

    except ValueError as error:

        raise RuntimeError(
            (
                "팀컬러 선수 목록이 "
                "JSON 형식이 아닙니다. "
                f"url={response.url} "
                f"응답 앞부분="
                f"{response.text[:500]}"
            )
        ) from error


    players = (
        data.get(
            "players"
        )
    )


    if (
        players is None
        or
        players == ""
    ):

        return []


    if not isinstance(
        players,
        list,
    ):

        raise RuntimeError(
            (
                "팀컬러 선수 목록의 "
                "players 형식이 예상과 다릅니다: "
                f"{type(players)}"
            )
        )


    return players

def get_team_color_season_ids(
    client,
):

    global TEAM_COLOR_SEASON_IDS_CACHE


    if (
        TEAM_COLOR_SEASON_IDS_CACHE
        is not None
    ):

        return (
            TEAM_COLOR_SEASON_IDS_CACHE
        )


    response = client.get(
        TEAM_COLOR_SEASON_META_URL
    )


    response.raise_for_status()


    try:

        data = response.json()

    except ValueError as error:

        raise RuntimeError(
            "FC Online 시즌 메타데이터가 "
            "JSON 형식이 아닙니다."
        ) from error


    season_ids = sorted(
        {
            int(
                season[
                    "seasonId"
                ]
            )

            for season in data

            if (
                season.get(
                    "seasonId"
                )
                is not None
            )
        }
    )


    if not season_ids:

        raise RuntimeError(
            "FC Online 시즌 ID를 "
            "가져오지 못했습니다."
        )


    TEAM_COLOR_SEASON_IDS_CACHE = (
        season_ids
    )


    return season_ids


def fetch_all_team_color_players(
    client,
    detail_soup,
):

    players_by_sp_id = {}


    def add_players(
        players,
    ):

        for player in players:

            sp_id = (
                player.get(
                    "spid"
                )
            )


            if sp_id is None:
                continue


            try:

                normalized_sp_id = int(
                    sp_id
                )

            except (
                TypeError,
                ValueError,
            ):

                continue


            players_by_sp_id[
                normalized_sp_id
            ] = {
                "sp_id":
                    normalized_sp_id,

                "player_name":
                    normalize_text(
                        player.get(
                            "name"
                        )
                    ),
            }


    # =====================================
    # 시즌까지 분할
    #
    # OVR + 급여 + 개별 포지션으로도
    # 100명이 꽉 찰 때 최종 fallback
    # =====================================

    def collect_season_ranges(
        exact_ovr,
        exact_salary,
        position_filter,
    ):

        print(
            (
                "[TEAM COLOR PLAYER SPLIT] "
                f"OVR={exact_ovr} "
                f"salary={exact_salary} "
                f"position={position_filter} "
                "-> season split"
            ),
            flush=True,
        )


        season_ids = (
            get_team_color_season_ids(
                client
            )
        )


        for season_id in season_ids:

            players = (
                fetch_team_color_player_list(
                    client,
                    detail_soup,
                    overrides={
                        "n4OvrMin":
                            exact_ovr,

                        "n4OvrMax":
                            exact_ovr,

                        "n4SalaryMin":
                            exact_salary,

                        "n4SalaryMax":
                            exact_salary,

                        "strPosition":
                            position_filter,

                        "strSeason":
                            f",{season_id},",
                    },
                )
            )


            add_players(
                players
            )


            if (
                len(
                    players
                )
                >=
                TEAM_COLOR_PLAYER_RESULT_LIMIT
            ):

                raise RuntimeError(
                    (
                        "팀컬러 선수 목록이 "
                        "시즌 + 포지션 + OVR + 급여 "
                        "단일 구간에서도 "
                        "100명 이상입니다. "
                        f"season={season_id}, "
                        f"position={position_filter}, "
                        f"OVR={exact_ovr}, "
                        f"salary={exact_salary}"
                    )
                )


    # =====================================
    # 포지션 분할
    # =====================================

    def collect_position_ranges(
        exact_ovr,
        exact_salary,
    ):

        print(
            (
                "[TEAM COLOR PLAYER SPLIT] "
                f"OVR={exact_ovr} "
                f"salary={exact_salary} "
                "-> position split"
            ),
            flush=True,
        )


        for (
            group_name,
            group_filter,
            position_filters,
        ) in TEAM_COLOR_POSITION_GROUPS:

            group_players = (
                fetch_team_color_player_list(
                    client,
                    detail_soup,
                    overrides={
                        "n4OvrMin":
                            exact_ovr,

                        "n4OvrMax":
                            exact_ovr,

                        "n4SalaryMin":
                            exact_salary,

                        "n4SalaryMax":
                            exact_salary,

                        "strPosition":
                            group_filter,
                    },
                )
            )


            add_players(
                group_players
            )


            # 그룹 자체가 100명 미만이면
            # 이 그룹은 완료
            if (
                len(
                    group_players
                )
                <
                TEAM_COLOR_PLAYER_RESULT_LIMIT
            ):

                continue


            print(
                (
                    "[TEAM COLOR PLAYER SPLIT] "
                    f"{group_name} "
                    "-> individual positions"
                ),
                flush=True,
            )


            # =================================
            # 그룹도 100명이면
            # 개별 포지션으로 다시 분할
            # =================================

            for position_filter in (
                position_filters
            ):

                position_players = (
                    fetch_team_color_player_list(
                        client,
                        detail_soup,
                        overrides={
                            "n4OvrMin":
                                exact_ovr,

                            "n4OvrMax":
                                exact_ovr,

                            "n4SalaryMin":
                                exact_salary,

                            "n4SalaryMax":
                                exact_salary,

                            "strPosition":
                                position_filter,
                        },
                    )
                )


                add_players(
                    position_players
                )


                if (
                    len(
                        position_players
                    )
                    <
                    TEAM_COLOR_PLAYER_RESULT_LIMIT
                ):

                    continue


                # =============================
                # 개별 포지션까지 100명
                # → 시즌별 최종 분할
                # =============================

                collect_season_ranges(
                    exact_ovr,
                    exact_salary,
                    position_filter,
                )


    # =====================================
    # 급여 분할
    # =====================================

    def collect_salary_range(
        exact_ovr,
        salary_min,
        salary_max,
    ):

        players = (
            fetch_team_color_player_list(
                client,
                detail_soup,
                overrides={
                    "n4OvrMin":
                        exact_ovr,

                    "n4OvrMax":
                        exact_ovr,

                    "n4SalaryMin":
                        salary_min,

                    "n4SalaryMax":
                        salary_max,
                },
            )
        )


        add_players(
            players
        )


        if (
            len(
                players
            )
            <
            TEAM_COLOR_PLAYER_RESULT_LIMIT
        ):

            return


        # =================================
        # 급여까지 단일값인데
        # 100명 이상
        #
        # 기존에는 여기서 RuntimeError
        # 이제 포지션으로 추가 분할
        # =================================

        if (
            salary_min
            >=
            salary_max
        ):

            collect_position_ranges(
                exact_ovr,
                salary_min,
            )

            return


        middle = (
            salary_min
            +
            salary_max
        ) // 2


        collect_salary_range(
            exact_ovr,
            salary_min,
            middle,
        )


        collect_salary_range(
            exact_ovr,
            middle + 1,
            salary_max,
        )


    # =====================================
    # OVR 분할
    # =====================================

    def collect_ovr_range(
        ovr_min,
        ovr_max,
    ):

        players = (
            fetch_team_color_player_list(
                client,
                detail_soup,
                overrides={
                    "n4OvrMin":
                        ovr_min,

                    "n4OvrMax":
                        ovr_max,
                },
            )
        )


        add_players(
            players
        )


        if (
            len(
                players
            )
            <
            TEAM_COLOR_PLAYER_RESULT_LIMIT
        ):

            return


        if (
            ovr_min
            >=
            ovr_max
        ):

            collect_salary_range(
                ovr_min,
                TEAM_COLOR_PLAYER_SALARY_MIN,
                TEAM_COLOR_PLAYER_SALARY_MAX,
            )

            return


        middle = (
            ovr_min
            +
            ovr_max
        ) // 2


        collect_ovr_range(
            ovr_min,
            middle,
        )


        collect_ovr_range(
            middle + 1,
            ovr_max,
        )


    # =====================================
    # 1차 기본 요청
    # =====================================

    initial_players = (
        fetch_team_color_player_list(
            client,
            detail_soup,
        )
    )


    add_players(
        initial_players
    )


    # 100명 미만이면
    # 분할 필요 없음
    if (
        len(
            initial_players
        )
        <
        TEAM_COLOR_PLAYER_RESULT_LIMIT
    ):

        return sorted(
            players_by_sp_id.values(),
            key=lambda item:
                item[
                    "sp_id"
                ],
        )


    # =====================================
    # 100명 이상이면
    # OVR부터 재귀 분할 시작
    # =====================================

    collect_ovr_range(
        TEAM_COLOR_PLAYER_OVR_MIN,
        TEAM_COLOR_PLAYER_OVR_MAX,
    )


    return sorted(
        players_by_sp_id.values(),
        key=lambda item:
            item[
                "sp_id"
            ],
    )


# =========================================
# CARD PARSER
# =========================================

def parse_team_color_effect(
    raw_text,
):

    text = (
        normalize_text(
            raw_text
        )
    )


    match = (
        TEAM_COLOR_EFFECT_PATTERN
        .match(
            text
        )
    )


    if not match:

        return None


    stat_name = (
        normalize_stat_name(
            match.group(
                1
            )
        )
    )


    bonus = int(
        match.group(
            2
        )
    )


    if not stat_name:

        return None


    return {
        "stat_name":
            stat_name,

        "stat_key":
            get_stat_key(
                stat_name
            ),

        "bonus":
            bonus,
    }


def parse_team_color_card(
    element,
):

    detail_link = (
        element.select_one(
            "a.btn_detail_link"
        )
    )


    if (
        detail_link
        is None
    ):

        return None


    onclick = (
        detail_link.get(
            "onclick"
        )
        or ""
    )


    id_match = (
        TEAM_COLOR_ID_PATTERN
        .search(
            onclick
        )
    )


    if (
        id_match
        is None
    ):

        return None


    team_color_id = int(
        id_match.group(
            1
        )
    )


    name_element = (
        element.select_one(
            ".name"
        )
    )


    if (
        name_element
        is None
    ):

        return None


    team_name = (
        normalize_text(
            name_element.get_text(
                " ",
                strip=True,
            )
        )
    )


    if not team_name:

        return None


    required_element = (
        element.select_one(
            ".crests .num"
        )
    )


    max_required_players = None


    if (
        required_element
        is not None
    ):

        required_text = (
            normalize_text(
                required_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        if (
            required_text.isdigit()
        ):

            max_required_players = int(
                required_text
            )


    level_element = (
        element.select_one(
            ".level"
        )
    )


    max_stage = None


    if (
        level_element
        is not None
    ):

        level_text = (
            normalize_text(
                level_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        stage_match = (
            TEAM_COLOR_STAGE_PATTERN
            .search(
                level_text
            )
        )


        if (
            stage_match
            is not None
        ):

            max_stage = int(
                stage_match.group(
                    1
                )
            )


    icon_element = (
        element.select_one(
            ".crests img"
        )
    )


    icon_url = None


    if (
        icon_element
        is not None
    ):

        icon_url = (
            icon_element.get(
                "src"
            )
        )


        if icon_url:

            icon_url = (
                str(
                    icon_url
                )
                .strip()
            )


    effects = []


    for effect_index, effect_element in enumerate(
        element.select(
            ".desc .item"
        ),
        start=1,
    ):

        effect = (
            parse_team_color_effect(
                effect_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        if (
            effect
            is None
        ):

            continue


        effect[
            "effect_order"
        ] = (
            effect_index
        )


        effects.append(
            effect
        )


    return {
        "team_color_id":
            team_color_id,

        "team_name":
            team_name,

        "max_stage":
            max_stage,

        "max_required_players":
            max_required_players,

        "icon_url":
            icon_url,

        "effects":
            effects,

        "category":
            None,

        "team_color_type":
            None,
    }


def parse_team_color_cards(
    soup,
):

    result = []


    seen_ids = set()


    for element in soup.select(
        ".teamcolor_item"
    ):

        item = (
            parse_team_color_card(
                element
            )
        )


        if (
            item is None
        ):

            continue


        team_color_id = (
            item[
                "team_color_id"
            ]
        )


        if (
            team_color_id
            in seen_ids
        ):

            continue


        seen_ids.add(
            team_color_id
        )


        result.append(
            item
        )


    return result

# =========================================
# DETAIL PARSER
# =========================================

def parse_team_color_detail_levels(
    detail_soup,
):

    levels = []


    level_elements = (
        detail_soup.select(
            ".content_header .content .level"
        )
    )


    if not level_elements:

        raise RuntimeError(
            (
                "팀컬러 상세 페이지에서 "
                "단계 정보를 찾지 못했습니다."
            )
        )


    for level_element in (
        level_elements
    ):

        title_element = (
            level_element.select_one(
                ".tit"
            )
        )


        if title_element is None:
            continue


        title_text = (
            normalize_text(
                title_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        stage_match = (
            TEAM_COLOR_STAGE_PATTERN
            .search(
                title_text
            )
        )


        if stage_match is None:
            continue


        stage = int(
            stage_match.group(
                1
            )
        )


        level_text = (
            normalize_text(
                level_element.get_text(
                    " ",
                    strip=True,
                )
            )
        )


        required_match = re.search(
            r"(\d+)\s*명",
            level_text,
        )


        if required_match is None:

            raise RuntimeError(
                (
                    "팀컬러 단계의 "
                    "필요 인원을 찾지 못했습니다: "
                    f"stage={stage}, "
                    f"text={level_text}"
                )
            )


        required_players = int(
            required_match.group(
                1
            )
        )


        effects = []


        for raw_text in (
            level_element.stripped_strings
        ):

            effect = (
                parse_team_color_effect(
                    raw_text
                )
            )


            if effect is None:
                continue


            effect[
                "effect_order"
            ] = (
                len(
                    effects
                )
                + 1
            )


            effects.append(
                effect
            )


        levels.append(
            {
                "stage":
                    stage,

                "required_players":
                    required_players,

                "effects":
                    effects,
            }
        )


    levels.sort(
        key=lambda item:
            item[
                "stage"
            ]
    )


    if not levels:

        raise RuntimeError(
            "유효한 팀컬러 단계를 파싱하지 못했습니다."
        )


    return levels


def validate_team_color_detail(
    item,
    levels,
):

    max_level = max(
        levels,
        key=lambda level:
            level[
                "stage"
            ],
    )


    expected_max_stage = (
        item.get(
            "max_stage"
        )
    )


    if (
        expected_max_stage
        is not None
        and
        int(
            expected_max_stage
        )
        !=
        int(
            max_level[
                "stage"
            ]
        )
    ):

        raise RuntimeError(
            (
                "팀컬러 최고 단계가 "
                "카탈로그와 상세 페이지에서 "
                "일치하지 않습니다: "
                f"{item['team_name']} "
                f"catalog={expected_max_stage}, "
                f"detail={max_level['stage']}"
            )
        )


    expected_required_players = (
        item.get(
            "max_required_players"
        )
    )


    if (
        expected_required_players
        is not None
        and
        int(
            expected_required_players
        )
        !=
        int(
            max_level[
                "required_players"
            ]
        )
    ):

        raise RuntimeError(
            (
                "팀컬러 최고 단계 필요 인원이 "
                "카탈로그와 상세 페이지에서 "
                "일치하지 않습니다: "
                f"{item['team_name']} "
                f"catalog={expected_required_players}, "
                f"detail="
                f"{max_level['required_players']}"
            )
        )


    catalog_effects = {
        (
            effect[
                "stat_key"
            ],
            int(
                effect[
                    "bonus"
                ]
            ),
        )

        for effect in (
            item.get(
                "effects"
            )
            or []
        )
    }


    detail_effects = {
        (
            effect[
                "stat_key"
            ],
            int(
                effect[
                    "bonus"
                ]
            ),
        )

        for effect in (
            max_level.get(
                "effects"
            )
            or []
        )
    }


    if (
        catalog_effects
        !=
        detail_effects
    ):

        raise RuntimeError(
            (
                "팀컬러 최고 단계 효과가 "
                "카탈로그와 상세 페이지에서 "
                "일치하지 않습니다: "
                f"{item['team_name']} "
                f"catalog={sorted(catalog_effects)} "
                f"detail={sorted(detail_effects)}"
            )
        )


def enrich_team_color_details(
    client,
    catalog,
    connection,
):

    total_count = len(
        catalog
    )


    completed_ids = (
        get_completed_team_color_detail_ids(
            connection
        )
    )


    print(
        (
            "[TEAM COLOR CHECKPOINT] "
            f"resume={len(completed_ids)}/"
            f"{total_count}"
        ),
        flush=True,
    )


    saved_count = 0
    skipped_count = 0


    for (
        index,
        item,
    ) in enumerate(
        catalog,
        start=1,
    ):

        team_color_id = int(
            item[
                "team_color_id"
            ]
        )


        # =====================================
        # 이미 정상 저장된 팀컬러
        # =====================================

        if (
            team_color_id
            in completed_ids
        ):

            skipped_count += 1


            if (
                index == 1
                or
                index % 50 == 0
                or
                index == total_count
            ):

                print(
                    (
                        "[TEAM COLOR DETAIL] "
                        f"{index}/{total_count} "
                        f"id={team_color_id} "
                        "SKIP"
                    ),
                    flush=True,
                )


            continue


        try:

            # =================================
            # 공식 상세 페이지
            # =================================

            detail_soup = (
                fetch_team_color_detail(
                    client,
                    team_color_id,
                )
            )


            # =================================
            # 단계별 조건 / 효과
            # =================================

            levels = (
                parse_team_color_detail_levels(
                    detail_soup
                )
            )


            validate_team_color_detail(
                item,
                levels,
            )


            item[
                "levels"
            ] = levels


            # =================================
            # 적용 선수
            #
            # 강화 팀컬러는 SPID 목록 불필요
            # =================================

            if (
                item.get(
                    "category"
                )
                ==
                "enhance"
            ):

                item[
                    "players"
                ] = []

            else:

                item[
                    "players"
                ] = (
                    fetch_all_team_color_players(
                        client,
                        detail_soup,
                    )
                )


            # =================================
            # unknown 능력치 검증
            #
            # DB 저장 전에 해당 팀컬러만 검증
            # =================================

            validate_team_color_item_effects(
                item
            )


            # =================================
            # 중요
            #
            # 여기서 팀컬러 1개 즉시 저장 + COMMIT
            # =================================

            save_team_color_detail_item(
                connection,
                item,
            )


            completed_ids.add(
                team_color_id
            )


            saved_count += 1


            print(
                (
                    "[TEAM COLOR DETAIL] "
                    f"{index}/{total_count} "
                    f"id={team_color_id} "
                    f"levels={len(levels)} "
                    f"players="
                    f"{len(item['players'])} "
                    "SAVED"
                ),
                flush=True,
            )


        except Exception as error:

            # 현재 처리 중인 팀컬러는
            # 체크포인트가 기록되지 않는다.

            try:
                connection.rollback()

            except Exception:
                pass


            print(
                (
                    "[TEAM COLOR DETAIL ERROR] "
                    f"{index}/{total_count} "
                    f"id={team_color_id} "
                    f"name={item.get('team_name')} "
                    f"error={error}"
                ),
                flush=True,
            )


            raise


    print(
        (
            "[TEAM COLOR CHECKPOINT] "
            f"completed={len(completed_ids)}/"
            f"{total_count} "
            f"saved_now={saved_count} "
            f"skipped={skipped_count}"
        ),
        flush=True,
    )


# =========================================
# FILTER RESOLUTION
# =========================================

def fetch_filtered_team_color_ids(
    client,
    parameter_name,
    parameter_value,
    total_count,
):

    # 사이트 JS에서 여러 선택값을
    # hidden input에 이어붙이는 경우를 대비해
    # bare / comma 형태 둘 다 확인한다.
    candidates = [
        parameter_value,
        f",{parameter_value},",
    ]


    for query_value in candidates:

        params = {
            "strTeamColorCategory":
                "",

            "strTeamColorType":
                "",

            "strTeamColorName":
                "",
        }


        params[
            parameter_name
        ] = (
            query_value
        )


        soup = (
            fetch_team_color_page(
                client,
                params=params,
            )
        )


        items = (
            parse_team_color_cards(
                soup
            )
        )


        ids = {
            int(
                item[
                    "team_color_id"
                ]
            )

            for item
            in items
        }


        print(
            (
                "[TEAM COLOR FILTER] "
                f"{parameter_name}="
                f"{query_value!r} "
                f"count={len(ids)}"
            ),
            flush=True,
        )


        # 필터가 먹지 않았으면
        # 전체 개수와 동일하게 나온다.
        if (
            ids
            and
            len(
                ids
            )
            <
            total_count
        ):

            return ids


    raise RuntimeError(
        (
            "FC Online 팀컬러 필터를 "
            "정상적으로 적용하지 못했습니다: "
            f"{parameter_name}="
            f"{parameter_value}"
        )
    )


def resolve_team_color_classification(
    client,
    catalog,
):

    total_count = (
        len(
            catalog
        )
    )


    by_id = {
        int(
            item[
                "team_color_id"
            ]
        ):
            item

        for item
        in catalog
    }


    # =====================================
    # CATEGORY
    # =====================================

    for (
        normalized_category,
        official_value,
    ) in (
        TEAM_COLOR_CATEGORY_VALUES
        .items()
    ):

        ids = (
            fetch_filtered_team_color_ids(
                client,
                "strTeamColorCategory",
                official_value,
                total_count,
            )
        )


        for team_color_id in ids:

            item = (
                by_id.get(
                    team_color_id
                )
            )


            if (
                item is None
            ):

                continue


            item[
                "category"
            ] = (
                normalized_category
            )


    # =====================================
    # TYPE
    # =====================================

    for (
        normalized_type,
        official_value,
    ) in (
        TEAM_COLOR_TYPE_VALUES
        .items()
    ):

        ids = (
            fetch_filtered_team_color_ids(
                client,
                "strTeamColorType",
                official_value,
                total_count,
            )
        )


        for team_color_id in ids:

            item = (
                by_id.get(
                    team_color_id
                )
            )


            if (
                item is None
            ):

                continue


            item[
                "team_color_type"
            ] = (
                normalized_type
            )


    unresolved_category = [
        item

        for item
        in catalog

        if (
            not item.get(
                "category"
            )
        )
    ]


    unresolved_type = [
        item

        for item
        in catalog

        if (
            not item.get(
                "team_color_type"
            )
        )
    ]


    if (
        unresolved_category
        or
        unresolved_type
    ):

        print(
            (
                "[TEAM COLOR] "
                "unresolved category="
                f"{len(unresolved_category)} "
                "type="
                f"{len(unresolved_type)}"
            ),
            flush=True,
        )


        print(
            "unresolved category sample=",
            [
                (
                    item[
                        "team_color_id"
                    ],
                    item[
                        "team_name"
                    ],
                )

                for item
                in (
                    unresolved_category[:10]
                )
            ],
            flush=True,
        )


        print(
            "unresolved type sample=",
            [
                (
                    item[
                        "team_color_id"
                    ],
                    item[
                        "team_name"
                    ],
                )

                for item
                in (
                    unresolved_type[:10]
                )
            ],
            flush=True,
        )


        raise RuntimeError(
            (
                "일부 공식 팀컬러의 "
                "category/type 분류에 실패했습니다."
            )
        )


# =========================================
# DATABASE
# =========================================

def ensure_team_color_tables(
    connection,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_team_colors (
                    team_color_id BIGINT
                        PRIMARY KEY,

                    team_name TEXT
                        NOT NULL,

                    category VARCHAR(30)
                        NOT NULL,

                    team_color_type VARCHAR(30)
                        NOT NULL,

                    icon_url TEXT,

                    max_stage INTEGER,

                    max_required_players INTEGER,

                    is_active BOOLEAN
                        NOT NULL
                        DEFAULT TRUE,

                    source_url TEXT
                        NOT NULL
                        DEFAULT
                        'https://fconline.nexon.com/datacenter/teamcolor',

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_team_color_levels (
                    team_color_id BIGINT
                        NOT NULL,

                    stage INTEGER
                        NOT NULL,

                    required_players INTEGER,

                    is_max_stage BOOLEAN
                        NOT NULL
                        DEFAULT FALSE,

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    PRIMARY KEY (
                        team_color_id,
                        stage
                    )
                )
            """
        )


        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_team_color_effects (
                    team_color_id BIGINT
                        NOT NULL,

                    stage INTEGER
                        NOT NULL,

                    stat_key TEXT
                        NOT NULL,

                    stat_name TEXT
                        NOT NULL,

                    bonus INTEGER
                        NOT NULL,

                    effect_order INTEGER
                        NOT NULL
                        DEFAULT 0,

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    PRIMARY KEY (
                        team_color_id,
                        stage,
                        stat_key
                    )
                )
            """
        )


        # 3-2B에서 공식 선수목록 저장 예정
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_team_color_players (
                    team_color_id BIGINT
                        NOT NULL,

                    sp_id BIGINT
                        NOT NULL,

                    player_name TEXT,

                    updated_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW(),

                    PRIMARY KEY (
                        team_color_id,
                        sp_id
                    )
                )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_fconline_team_colors_category
            ON
                fconline_team_colors (
                    category
                )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_fconline_team_colors_type
            ON
                fconline_team_colors (
                    team_color_type
                )
            """
        )


        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_fconline_team_color_players_sp_id
            ON
                fconline_team_color_players (
                    sp_id
                )
            """
        )


def ensure_team_color_detail_sync_table(
    connection,
):

    with connection.cursor() as cursor:

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
                fconline_team_color_detail_sync (
                    team_color_id BIGINT
                        PRIMARY KEY,

                    levels_count INTEGER
                        NOT NULL,

                    effects_count INTEGER
                        NOT NULL,

                    players_count INTEGER
                        NOT NULL,

                    synced_at TIMESTAMPTZ
                        NOT NULL
                        DEFAULT NOW()
                )
            """
        )


    connection.commit()


def save_team_color_catalog_metadata(
    connection,
    catalog,
):

    with connection.cursor() as cursor:

        # =====================================
        # 현재 공식 목록에 없는 팀컬러 inactive
        # =====================================

        cursor.execute(
            """
            UPDATE
                fconline_team_colors

            SET
                is_active = FALSE
            """
        )


        # =====================================
        # 기본 카탈로그 정보만 먼저 저장
        #
        # 상세 수집 성공 여부와 독립적
        # =====================================

        for item in catalog:

            team_color_id = int(
                item[
                    "team_color_id"
                ]
            )


            cursor.execute(
                """
                INSERT INTO
                    fconline_team_colors (
                        team_color_id,
                        team_name,
                        category,
                        team_color_type,
                        icon_url,
                        max_stage,
                        max_required_players,
                        is_active,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    TRUE,
                    NOW()
                )

                ON CONFLICT (
                    team_color_id
                )

                DO UPDATE SET
                    team_name =
                        EXCLUDED.team_name,

                    category =
                        EXCLUDED.category,

                    team_color_type =
                        EXCLUDED.team_color_type,

                    icon_url =
                        EXCLUDED.icon_url,

                    max_stage =
                        EXCLUDED.max_stage,

                    max_required_players =
                        EXCLUDED.max_required_players,

                    is_active =
                        TRUE,

                    updated_at =
                        NOW()
                """,
                (
                    team_color_id,

                    item[
                        "team_name"
                    ],

                    item[
                        "category"
                    ],

                    item[
                        "team_color_type"
                    ],

                    item.get(
                        "icon_url"
                    ),

                    item.get(
                        "max_stage"
                    ),

                    item.get(
                        "max_required_players"
                    ),
                ),
            )


    connection.commit()


def validate_team_color_item_effects(
    item,
):

    unknown_effects = []


    for level in (
        item.get(
            "levels"
        )
        or []
    ):

        for effect in (
            level.get(
                "effects"
            )
            or []
        ):

            if (
                str(
                    effect[
                        "stat_key"
                    ]
                )
                .startswith(
                    "unknown:"
                )
            ):

                unknown_effects.append(
                    (
                        item[
                            "team_color_id"
                        ],

                        item[
                            "team_name"
                        ],

                        level[
                            "stage"
                        ],

                        effect[
                            "stat_name"
                        ],
                    )
                )


    if unknown_effects:

        print(
            (
                "[TEAM COLOR] "
                "unknown official stats="
            ),
            unknown_effects[:30],
            flush=True,
        )


        raise RuntimeError(
            (
                "매핑되지 않은 공식 능력치가 있습니다. "
                "DB 저장 전에 "
                "TEAM_COLOR_STAT_KEY_MAP을 "
                "보완해야 합니다."
            )
        )


def get_completed_team_color_detail_ids(
    connection,
):

    # =====================================
    # 체크포인트만 믿지 않고
    # 실제 DB 행 개수도 함께 검증한다.
    #
    # 데이터가 지워졌다면 자동으로 재수집 대상.
    # =====================================

    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                sync.team_color_id

            FROM
                fconline_team_color_detail_sync
                AS sync

            WHERE
                sync.levels_count
                =
                (
                    SELECT
                        COUNT(*)

                    FROM
                        fconline_team_color_levels
                        AS levels

                    WHERE
                        levels.team_color_id
                        =
                        sync.team_color_id
                )

                AND

                sync.effects_count
                =
                (
                    SELECT
                        COUNT(*)

                    FROM
                        fconline_team_color_effects
                        AS effects

                    WHERE
                        effects.team_color_id
                        =
                        sync.team_color_id
                )

                AND

                sync.players_count
                =
                (
                    SELECT
                        COUNT(*)

                    FROM
                        fconline_team_color_players
                        AS players

                    WHERE
                        players.team_color_id
                        =
                        sync.team_color_id
                )
            """
        )


        return {
            int(
                row[0]
            )

            for row
            in cursor.fetchall()
        }


def save_team_color_detail_item(
    connection,
    item,
):

    team_color_id = int(
        item[
            "team_color_id"
        ]
    )


    levels = (
        item.get(
            "levels"
        )
        or []
    )


    players = (
        item.get(
            "players"
        )
        or []
    )


    if not levels:

        raise RuntimeError(
            (
                "DB 저장 전 팀컬러 "
                "상세 단계가 없습니다: "
                f"{item['team_name']}"
            )
        )


    max_level = max(
        levels,
        key=lambda level:
            int(
                level[
                    "stage"
                ]
            ),
    )


    max_stage = int(
        max_level[
            "stage"
        ]
    )


    max_required_players = int(
        max_level[
            "required_players"
        ]
    )


    effects_count = sum(
        len(
            level.get(
                "effects"
            )
            or []
        )

        for level
        in levels
    )


    with connection.cursor() as cursor:

        # =====================================
        # 최고 단계 정보도 상세 기준으로 갱신
        # =====================================

        cursor.execute(
            """
            UPDATE
                fconline_team_colors

            SET
                max_stage = %s,
                max_required_players = %s,
                is_active = TRUE,
                updated_at = NOW()

            WHERE
                team_color_id = %s
            """,
            (
                max_stage,
                max_required_players,
                team_color_id,
            ),
        )


        # =====================================
        # 기존 해당 팀컬러 상세만 초기화
        # =====================================

        cursor.execute(
            """
            DELETE FROM
                fconline_team_color_effects

            WHERE
                team_color_id = %s
            """,
            (
                team_color_id,
            ),
        )


        cursor.execute(
            """
            DELETE FROM
                fconline_team_color_levels

            WHERE
                team_color_id = %s
            """,
            (
                team_color_id,
            ),
        )


        cursor.execute(
            """
            DELETE FROM
                fconline_team_color_players

            WHERE
                team_color_id = %s
            """,
            (
                team_color_id,
            ),
        )


        # =====================================
        # 단계 / 단계별 효과
        # =====================================

        for level in levels:

            stage = int(
                level[
                    "stage"
                ]
            )


            required_players = int(
                level[
                    "required_players"
                ]
            )


            cursor.execute(
                """
                INSERT INTO
                    fconline_team_color_levels (
                        team_color_id,
                        stage,
                        required_players,
                        is_max_stage,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    NOW()
                )
                """,
                (
                    team_color_id,
                    stage,
                    required_players,
                    (
                        stage
                        ==
                        max_stage
                    ),
                ),
            )


            for effect in (
                level.get(
                    "effects"
                )
                or []
            ):

                cursor.execute(
                    """
                    INSERT INTO
                        fconline_team_color_effects (
                            team_color_id,
                            stage,
                            stat_key,
                            stat_name,
                            bonus,
                            effect_order,
                            updated_at
                        )

                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        NOW()
                    )
                    """,
                    (
                        team_color_id,
                        stage,

                        effect[
                            "stat_key"
                        ],

                        effect[
                            "stat_name"
                        ],

                        int(
                            effect[
                                "bonus"
                            ]
                        ),

                        int(
                            effect[
                                "effect_order"
                            ]
                        ),
                    ),
                )


        # =====================================
        # 적용 선수
        # =====================================

        for player in players:

            cursor.execute(
                """
                INSERT INTO
                    fconline_team_color_players (
                        team_color_id,
                        sp_id,
                        player_name,
                        updated_at
                    )

                VALUES (
                    %s,
                    %s,
                    %s,
                    NOW()
                )
                """,
                (
                    team_color_id,

                    int(
                        player[
                            "sp_id"
                        ]
                    ),

                    player.get(
                        "player_name"
                    ),
                ),
            )


        # =====================================
        # 마지막에만 체크포인트 저장
        #
        # 이 INSERT까지 성공해야
        # 해당 팀컬러가 완료 처리된다.
        # =====================================

        cursor.execute(
            """
            INSERT INTO
                fconline_team_color_detail_sync (
                    team_color_id,
                    levels_count,
                    effects_count,
                    players_count,
                    synced_at
                )

            VALUES (
                %s,
                %s,
                %s,
                %s,
                NOW()
            )

            ON CONFLICT (
                team_color_id
            )

            DO UPDATE SET
                levels_count =
                    EXCLUDED.levels_count,

                effects_count =
                    EXCLUDED.effects_count,

                players_count =
                    EXCLUDED.players_count,

                synced_at =
                    NOW()
            """,
            (
                team_color_id,
                len(
                    levels
                ),
                effects_count,
                len(
                    players
                ),
            ),
        )


    # =====================================
    # 가장 중요
    #
    # 팀컬러 한 개 단위 영구 저장
    # =====================================

    connection.commit()


# =========================================
# VERIFY
# =========================================

def print_database_summary():

    with psycopg.connect(
        DATABASE_URL,
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_team_colors

                WHERE
                    is_active = TRUE
                """
            )


            active_count = int(
                cursor.fetchone()[0]
            )


            print(
                (
                    "[TEAM COLOR DB] "
                    f"active={active_count}"
                ),
                flush=True,
            )


            cursor.execute(
                """
                SELECT
                    category,
                    COUNT(*)

                FROM
                    fconline_team_colors

                WHERE
                    is_active = TRUE

                GROUP BY
                    category

                ORDER BY
                    category
                """
            )


            print(
                "[TEAM COLOR DB] categories=",
                cursor.fetchall(),
                flush=True,
            )


            cursor.execute(
                """
                SELECT
                    team_color_type,
                    COUNT(*)

                FROM
                    fconline_team_colors

                WHERE
                    is_active = TRUE

                GROUP BY
                    team_color_type

                ORDER BY
                    team_color_type
                """
            )


            print(
                "[TEAM COLOR DB] types=",
                cursor.fetchall(),
                flush=True,
            )


            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_team_color_effects
                """
            )


            effect_count = int(
                cursor.fetchone()[0]
            )


            print(
                (
                    "[TEAM COLOR DB] "
                    f"effects={effect_count}"
                ),
                flush=True,
            )

            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_team_color_levels
                """
            )


            level_count = int(
                cursor.fetchone()[0]
            )


            print(
                (
                    "[TEAM COLOR DB] "
                    f"levels={level_count}"
                ),
                flush=True,
            )


            cursor.execute(
                """
                SELECT
                    COUNT(*)

                FROM
                    fconline_team_color_players
                """
            )


            player_count = int(
                cursor.fetchone()[0]
            )


            print(
                (
                    "[TEAM COLOR DB] "
                    f"players={player_count}"
                ),
                flush=True,
            )


            cursor.execute(
                """
                SELECT
                    stat_key,
                    stat_name

                FROM
                    fconline_team_color_effects

                WHERE
                    stat_key LIKE 'unknown:%'

                GROUP BY
                    stat_key,
                    stat_name

                ORDER BY
                    stat_name
                """
            )


            unknown_stats = (
                cursor.fetchall()
            )


            print(
                (
                    "[TEAM COLOR DB] "
                    "unknown_stats="
                ),
                unknown_stats,
                flush=True,
            )



# =========================================
# SYNC
# =========================================

def sync_team_color_catalog():

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL 환경변수가 없습니다."
        )


    with httpx.Client(
        headers=HTTP_HEADERS,
        timeout=30.0,
        follow_redirects=True,
    ) as client:

        print(
            "[TEAM COLOR] fetching official catalog...",
            flush=True,
        )


        soup = (
            fetch_team_color_page(
                client
            )
        )


        catalog = (
            parse_team_color_cards(
                soup
            )
        )


        print(
            (
                "[TEAM COLOR] "
                f"catalog count={len(catalog)}"
            ),
            flush=True,
        )


        # =====================================
        # 공식 목록 최소 개수 방어
        # =====================================

        if (
            len(
                catalog
            )
            <
            700
        ):

            raise RuntimeError(
                (
                    "공식 팀컬러 목록을 "
                    "충분히 읽지 못했습니다: "
                    f"{len(catalog)}"
                )
            )


        # =====================================
        # category / type 분류
        # =====================================

        resolve_team_color_classification(
            client,
            catalog,
        )


        # =====================================
        # DB + 체크포인트
        # =====================================

        with psycopg.connect(
            DATABASE_URL,
        ) as connection:

            ensure_team_color_tables(
                connection
            )


            ensure_team_color_detail_sync_table(
                connection
            )


            # 3-2A 기본 메타데이터는
            # 매 실행 시 최신 공식 목록으로 갱신

            save_team_color_catalog_metadata(
                connection,
                catalog,
            )


            completed_ids = (
                get_completed_team_color_detail_ids(
                    connection
                )
            )


            print(
                (
                    "[TEAM COLOR CHECKPOINT] "
                    f"before="
                    f"{len(completed_ids)}/"
                    f"{len(catalog)}"
                ),
                flush=True,
            )


            print(
                "[TEAM COLOR] fetching official details...",
                flush=True,
            )


            # =================================
            # 상세는 한 개씩 저장
            # =================================

            enrich_team_color_details(
                client,
                catalog,
                connection,
            )


            completed_ids = (
                get_completed_team_color_detail_ids(
                    connection
                )
            )


            print(
                (
                    "[TEAM COLOR CHECKPOINT] "
                    f"after="
                    f"{len(completed_ids)}/"
                    f"{len(catalog)}"
                ),
                flush=True,
            )


            # =================================
            # 최종 완료 검증
            # =================================

            if (
                len(
                    completed_ids
                )
                !=
                len(
                    catalog
                )
            ):

                raise RuntimeError(
                    (
                        "팀컬러 상세 동기화가 "
                        "완전히 끝나지 않았습니다. "
                        f"{len(completed_ids)}/"
                        f"{len(catalog)}"
                    )
                )


    print_database_summary()


    print(
        "[TEAM COLOR] sync completed",
        flush=True,
    )


if __name__ == "__main__":

    sync_team_color_catalog()