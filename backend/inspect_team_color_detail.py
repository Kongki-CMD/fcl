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
    before=1500,
    after=3000,
):
    start = (
        text.find(
            needle
        )
    )


    if (
        start < 0
    ):
        print(
            f"[NOT FOUND] {needle}"
        )
        return


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


def main():

    with httpx.Client(
        headers=HEADERS,
        timeout=30.0,
        follow_redirects=True,
    ) as client:

        # =====================================
        # 팀컬러 메인 페이지
        # =====================================

        response = client.get(
            TEAM_COLOR_URL
        )


        print(
            "PAGE STATUS:",
            response.status_code,
        )


        response.raise_for_status()


        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )


        # =====================================
        # 공식 teamcolor JS 찾기
        # =====================================

        script_src = None


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


            if (
                "datacenter.teamcolor.js"
                in src
            ):

                script_src = src
                break


        if (
            not script_src
        ):
            raise RuntimeError(
                "datacenter.teamcolor.js를 찾지 못했습니다."
            )


        script_url = urljoin(
            TEAM_COLOR_URL,
            script_src,
        )


        print(
            "SCRIPT URL:",
            script_url,
        )


        # =====================================
        # 공식 JS 다운로드
        # =====================================

        script_response = (
            client.get(
                script_url
            )
        )


        print(
            "SCRIPT STATUS:",
            script_response.status_code,
        )


        script_response.raise_for_status()


        javascript = (
            script_response.text
        )


        print(
            "SCRIPT LENGTH:",
            len(
                javascript
            ),
        )


        # =====================================
        # 핵심 함수 주변 원문
        # =====================================

        for needle in (
            "GetTeamColorDetail",
            "SearchTeamColor",
            "searchtxtteamcolorlist",
            "teamcolorPop",
        ):

            print_section(
                needle
            )


            print_context(
                javascript,
                needle,
            )


        # =====================================
        # 팀컬러 관련 endpoint 후보
        # =====================================

        print_section(
            "TEAM COLOR ENDPOINT CANDIDATES"
        )


        endpoints = set()


        for match in re.finditer(
            r"""["']([^"']+)["']""",
            javascript,
        ):

            value = (
                match.group(
                    1
                )
                .strip()
            )


            lowered = (
                value.lower()
            )


            if (
                "teamcolor"
                not in lowered
            ):
                continue


            if (
                value.startswith("/")
            ):

                endpoints.add(
                    value
                )


        for endpoint in sorted(
            endpoints
        ):

            print(
                endpoint
            )


        # =====================================
        # AJAX 코드만 따로 추출
        # =====================================

        print_section(
            "AJAX BLOCKS"
        )


        ajax_positions = [
            match.start()

            for match in re.finditer(
                r"\$\.ajax|ajax\s*\(",
                javascript,
                flags=re.IGNORECASE,
            )
        ]


        shown = 0


        for position in (
            ajax_positions
        ):

            start = max(
                0,
                position - 500,
            )


            end = min(
                len(javascript),
                position + 2000,
            )


            block = (
                javascript[
                    start:end
                ]
            )


            if (
                "teamcolor"
                not in block.lower()
            ):
                continue


            print()
            print(
                f"--- AJAX BLOCK {shown + 1} ---"
            )

            print(
                block
            )


            shown += 1


            if (
                shown >= 10
            ):
                break


        print_section(
            "DONE"
        )


if __name__ == "__main__":
    main()