import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


BASE_URL = (
    "https://fconline.nexon.com"
)

TEAM_COLOR_URL = (
    f"{BASE_URL}"
    "/datacenter/teamcolor"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
}


TARGET_NEEDLES = (
    "GetTeamColorDetail",
    "teacolorSearchform",
    "TeamColorPlayerList",
    "searchtxtteamcolorlist",
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


def print_context(
    text,
    needle,
    before=1800,
    after=3500,
):
    start = (
        text.find(
            needle
        )
    )


    if (
        start < 0
    ):
        return False


    context_start = max(
        0,
        start - before,
    )


    context_end = min(
        len(text),
        start + len(needle) + after,
    )


    print(
        text[
            context_start:
            context_end
        ]
    )


    return True


def main():

    with httpx.Client(
        headers=HEADERS,
        timeout=30.0,
        follow_redirects=True,
    ) as client:

        response = client.get(
            TEAM_COLOR_URL
        )


        print(
            "PAGE STATUS:",
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
        # 1. teacolorSearchform 원본
        # =====================================

        print_section(
            "TEACOLOR SEARCH FORM"
        )


        form = soup.find(
            id="teacolorSearchform"
        )


        if (
            form is None
        ):
            print(
                "FORM NOT FOUND"
            )

        else:

            print(
                str(
                    form
                )[:15000]
            )


            print_section(
                "FORM FIELDS"
            )


            for element in form.find_all(
                [
                    "input",
                    "select",
                    "textarea",
                ]
            ):

                print(
                    {
                        "tag":
                            element.name,

                        "name":
                            element.get(
                                "name"
                            ),

                        "id":
                            element.get(
                                "id"
                            ),

                        "type":
                            element.get(
                                "type"
                            ),

                        "value":
                            element.get(
                                "value"
                            ),

                        "class":
                            element.get(
                                "class"
                            ),
                    }
                )


        # =====================================
        # 2. 메인 HTML 안의 inline script 탐색
        # =====================================

        print_section(
            "INLINE SCRIPT MATCHES"
        )


        for needle in (
            TARGET_NEEDLES
        ):

            found = False


            for index, script in enumerate(
                soup.find_all(
                    "script"
                )
            ):

                if (
                    script.get(
                        "src"
                    )
                ):
                    continue


                script_text = (
                    script.get_text(
                        "\n",
                        strip=False,
                    )
                    or ""
                )


                if (
                    needle
                    not in script_text
                ):
                    continue


                print()
                print(
                    (
                        f"--- INLINE SCRIPT "
                        f"{index} / {needle} ---"
                    )
                )


                print_context(
                    script_text,
                    needle,
                )


                found = True


            if (
                not found
            ):
                print(
                    f"[INLINE NOT FOUND] {needle}"
                )


        # =====================================
        # 3. 모든 외부 JS에서 핵심 함수 검색
        # =====================================

        print_section(
            "EXTERNAL SCRIPT MATCHES"
        )


        script_urls = []


        for script in soup.find_all(
            "script",
            src=True,
        ):

            src = (
                script.get(
                    "src"
                )
                or ""
            )


            script_url = urljoin(
                TEAM_COLOR_URL,
                src,
            )


            if (
                script_url
                in script_urls
            ):
                continue


            script_urls.append(
                script_url
            )


        print(
            "SCRIPT COUNT:",
            len(
                script_urls
            ),
        )


        for script_url in (
            script_urls
        ):

            try:

                script_response = (
                    client.get(
                        script_url
                    )
                )


                if (
                    script_response.status_code
                    !=
                    200
                ):
                    continue


                javascript = (
                    script_response.text
                )


            except Exception:
                continue


            matched_needles = [
                needle

                for needle in (
                    TARGET_NEEDLES
                )

                if needle
                in javascript
            ]


            if (
                not matched_needles
            ):
                continue


            print()
            print(
                "SCRIPT:",
                script_url,
            )


            print(
                "MATCHES:",
                matched_needles,
            )


            for needle in (
                matched_needles
            ):

                print()
                print(
                    f"--- {needle} ---"
                )


                print_context(
                    javascript,
                    needle,
                )


        # =====================================
        # 4. GetTeamColorDetail 호출 ID 확인
        # =====================================

        print_section(
            "TEAM COLOR IDS"
        )


        team_color_ids = []


        for match in re.finditer(
            (
                r"GetTeamColorDetail"
                r"\(\s*(\d+)\s*\)"
            ),
            html,
        ):

            team_color_id = int(
                match.group(
                    1
                )
            )


            if (
                team_color_id
                not in team_color_ids
            ):
                team_color_ids.append(
                    team_color_id
                )


        print(
            "COUNT:",
            len(
                team_color_ids
            ),
        )


        print(
            "FIRST 30:",
            team_color_ids[:30],
        )


        print_section(
            "DONE"
        )


if __name__ == "__main__":
    main()