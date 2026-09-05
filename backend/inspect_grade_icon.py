import re

import httpx


CSS_URLS = [
    (
        "PLAYER DETAIL",
        "https://m.fconline.nexon.com/"
        "content/DataCenter/playerDetail.css",
    ),
    (
        "MOBILE COMMON",
        "https://ssl.nexon.com/"
        "s3/fc/online/obt/fc.m_ssl.css",
    ),
]


SEARCH_TERMS = [
    "btnBuild",
    "build1",
    "build2",
    "build3",
    "build4",
    "build5",
    "build6",
    "build7",
    "build8",
    "build9",
    "build10",
    "build11",
    "build12",
    "build13",
    "enLevel1",
    "enLevel2",
    "enLevel3",
    "enLevel4",
    "enLevel5",
    "enLevel6",
    "enLevel7",
    "enLevel8",
    "enLevel9",
    "enLevel10",
    "enLevel11",
    "enLevel12",
    "enLevel13",
]


headers = {
    "User-Agent":
        (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),
}


with httpx.Client(
    timeout=20.0,
    follow_redirects=True,
    headers=headers,
) as client:

    for (
        css_name,
        css_url,
    ) in CSS_URLS:

        print()
        print(
            "=" * 100
        )

        print(
            css_name
        )

        print(
            css_url
        )

        print(
            "=" * 100
        )


        response = client.get(
            css_url
        )


        print(
            "STATUS:",
            response.status_code,
        )


        response.raise_for_status()


        css = response.text


        print(
            "CSS LENGTH:",
            len(css),
        )


        for term in SEARCH_TERMS:

            matches = list(
                re.finditer(
                    re.escape(term),
                    css,
                    flags=re.IGNORECASE,
                )
            )


            if not matches:
                continue


            print()
            print(
                "-" * 100
            )

            print(
                f"[{term}] "
                f"COUNT: {len(matches)}"
            )

            print(
                "-" * 100
            )


            for (
                index,
                match,
            ) in enumerate(
                matches[:5],
                start=1,
            ):

                start = max(
                    0,
                    match.start() - 700,
                )

                end = min(
                    len(css),
                    match.end() + 1400,
                )


                context = css[
                    start:end
                ]


                context = re.sub(
                    r"\s+",
                    " ",
                    context,
                )


                print()

                print(
                    f"--- {term} #{index} ---"
                )

                print(
                    context
                )