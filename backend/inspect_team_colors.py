import re

import httpx

from bs4 import BeautifulSoup


TEAM_COLOR_URL = (
    "https://fconline.nexon.com/"
    "datacenter/teamcolor"
)


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


def print_section(
    title,
):
    print()
    print(
        "=" * 80
    )
    print(
        title
    )
    print(
        "=" * 80
    )


def main():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),
    }


    response = httpx.get(
        TEAM_COLOR_URL,
        headers=headers,
        timeout=30.0,
        follow_redirects=True,
    )


    print(
        "STATUS:",
        response.status_code,
    )


    response.raise_for_status()


    html = (
        response.text
    )


    soup = BeautifulSoup(
        html,
        "html.parser",
    )


    # =====================================
    # 1. 검색 Form 파라미터
    # =====================================

    print_section(
        "TEAM COLOR FILTER INPUTS"
    )


    for element in soup.find_all(
        [
            "input",
            "select",
            "option",
        ]
    ):

        name = (
            element.get(
                "name"
            )
        )


        element_id = (
            element.get(
                "id"
            )
        )


        value = (
            element.get(
                "value"
            )
        )


        text = normalize_text(
            element.get_text(
                " ",
                strip=True,
            )
        )


        joined = (
            f"{name} "
            f"{element_id} "
            f"{value} "
            f"{text}"
        ).lower()


        if (
            "teamcolor"
            not in joined
            and
            text
            not in {
                "소속 팀컬러",
                "특성 팀컬러",
                "강화 팀컬러",
                "클럽",
                "국가",
                "강화",
                "관계",
                "스페셜",
            }
        ):
            continue


        print(
            {
                "tag":
                    element.name,

                "name":
                    name,

                "id":
                    element_id,

                "value":
                    value,

                "text":
                    text,

                "class":
                    element.get(
                        "class"
                    ),
            }
        )


    # =====================================
    # 2. teamcolor 관련 attribute
    # =====================================

    print_section(
        "ELEMENTS WITH TEAMCOLOR ATTRIBUTE"
    )


    attribute_result_count = 0


    for element in soup.find_all(
        True
    ):

        interesting_attributes = {}


        for (
            attribute_name,
            attribute_value,
        ) in element.attrs.items():

            lowered_name = (
                str(
                    attribute_name
                )
                .lower()
            )


            lowered_value = (
                str(
                    attribute_value
                )
                .lower()
            )


            if (
                "teamcolor"
                in lowered_name
                or
                "teamcolor"
                in lowered_value
            ):

                interesting_attributes[
                    attribute_name
                ] = (
                    attribute_value
                )


        if (
            not interesting_attributes
        ):
            continue


        text = normalize_text(
            element.get_text(
                " ",
                strip=True,
            )
        )


        print(
            {
                "tag":
                    element.name,

                "attrs":
                    interesting_attributes,

                "text":
                    text[:300],
            }
        )


        attribute_result_count += 1


        if (
            attribute_result_count
            >= 40
        ):
            break


    # =====================================
    # 3. onclick / data-* / href 중
    #    팀컬러 상세나 선수목록 후보
    # =====================================

    print_section(
        "CLICKABLE TEAM COLOR CANDIDATES"
    )


    clickable_count = 0


    for element in soup.find_all(
        [
            "a",
            "button",
            "input",
        ]
    ):

        attributes = (
            element.attrs
        )


        attribute_text = (
            " ".join(
                (
                    f"{key}={value}"
                )

                for (
                    key,
                    value,
                )
                in attributes.items()
            )
        )


        text = normalize_text(
            element.get_text(
                " ",
                strip=True,
            )
        )


        combined = (
            f"{attribute_text} "
            f"{text}"
        ).lower()


        if (
            "teamcolor"
            not in combined
            and
            "team_color"
            not in combined
            and
            "player"
            not in combined
        ):
            continue


        print(
            {
                "tag":
                    element.name,

                "attrs":
                    attributes,

                "text":
                    text[:200],
            }
        )


        clickable_count += 1


        if (
            clickable_count
            >= 60
        ):
            break


    # =====================================
    # 4. 팀컬러 카드 후보 DOM
    #
    # "단계" + "+숫자" 효과가 같이 있는
    # 반복 영역을 찾아 구조 확인.
    # =====================================

    print_section(
        "TEAM COLOR CARD DOM CANDIDATES"
    )


    effect_pattern = re.compile(
        r"\+\s*\d+"
    )


    printed = set()

    candidate_count = 0


    for text_node in soup.find_all(
        string=effect_pattern
    ):

        parent = (
            text_node.parent
        )


        if (
            parent is None
        ):
            continue


        candidate = parent


        # 효과 텍스트 하나에서 시작해서
        # 반복 카드 단위로 보일 만한 부모까지 탐색.
        for _ in range(
            5
        ):

            if (
                candidate.parent
                is None
            ):
                break


            candidate_text = (
                normalize_text(
                    candidate.get_text(
                        " ",
                        strip=True,
                    )
                )
            )


            if (
                "단계"
                in candidate_text
                and
                effect_pattern.search(
                    candidate_text
                )
            ):
                break


            candidate = (
                candidate.parent
            )


        candidate_html = (
            str(
                candidate
            )
        )


        candidate_key = (
            candidate_html[:500]
        )


        if (
            candidate_key
            in printed
        ):
            continue


        printed.add(
            candidate_key
        )


        print()
        print(
            "--- CARD",
            candidate_count + 1,
            "---",
        )

        print(
            "TEXT:",
            normalize_text(
                candidate.get_text(
                    " ",
                    strip=True,
                )
            )[:700],
        )

        print(
            "TAG:",
            candidate.name,
        )

        print(
            "CLASS:",
            candidate.get(
                "class"
            ),
        )

        print(
            "ATTRS:",
            candidate.attrs,
        )

        print(
            "HTML:"
        )

        print(
            candidate_html[:3000]
        )


        candidate_count += 1


        if (
            candidate_count
            >= 8
        ):
            break


    # =====================================
    # 5. raw script에서 teamcolor 관련
    #    endpoint / JS function 찾기
    # =====================================

    print_section(
        "TEAM COLOR SCRIPT LINES"
    )


    script_lines = []


    for script in soup.find_all(
        "script"
    ):

        script_text = (
            script.get_text(
                "\n",
                strip=False,
            )
        )


        if (
            not script_text
        ):
            continue


        for line in (
            script_text.splitlines()
        ):

            normalized_line = (
                line.strip()
            )


            if (
                "teamcolor"
                in normalized_line.lower()
                or
                "team_color"
                in normalized_line.lower()
            ):

                script_lines.append(
                    normalized_line
                )


    for line in (
        script_lines[:100]
    ):

        print(
            line[:1000]
        )


    print_section(
        "DONE"
    )


    print(
        "html length:",
        len(
            html
        ),
    )

    print(
        "card candidates:",
        candidate_count,
    )


if __name__ == "__main__":
    main()