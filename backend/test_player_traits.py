from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


# =========================================
# TEST PLAYER
# =========================================

SP_ID = 508200104
GRADE = 4


ABILITY_URL = (
    "https://fconline.nexon.com"
    "/datacenter/PlayerAbility"
)


PLAYER_INFO_URL = (
    "https://fconline.nexon.com/"
    f"datacenter/PlayerInfo"
    f"?spid={SP_ID}"
)


HEADERS = {
    "User-Agent":
        (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/150.0.0.0 Safari/537.36"
        ),

    "Referer":
        PLAYER_INFO_URL,
}


PAYLOAD = {
    "spid":
        str(
            SP_ID
        ),

    "n1Strong":
        str(
            GRADE
        ),

    "n1Grow":
        "0",

    "n4TeamColorId":
        "0",

    "n4TeamColorLv":
        "0",

    "n1Change":
        "0",

    "strPlayerImg":
        (
            "https://fo4.dn.nexoncdn.co.kr/"
            "live/externalAssets/common/"
            f"playersAction/p{SP_ID}.png"
        ),

    "rd":
        "0",
}


response = httpx.post(
    ABILITY_URL,
    data=PAYLOAD,
    headers=HEADERS,
    timeout=20.0,
    follow_redirects=True,
)


print("=" * 80)
print("STATUS")
print("=" * 80)
print(response.status_code)


print()
print("=" * 80)
print("FINAL URL")
print("=" * 80)
print(response.url)


response.raise_for_status()


html = response.text


soup = BeautifulSoup(
    html,
    "html.parser",
)


# =========================================
# TRAITS
# =========================================

trait_elements = soup.select(
    "div.skill_wrap span.desc"
)


print()
print("=" * 80)
print("TRAITS")
print("=" * 80)

print(
    "COUNT:",
    len(trait_elements),
)


for (
    index,
    desc_element,
) in enumerate(
    trait_elements,
    start=1,
):

    trait_name = (
        desc_element
        .get_text(
            " ",
            strip=True,
        )
    )


    print()
    print(
        "-" * 80
    )

    print(
        f"TRAIT #{index}"
    )

    print(
        "-" * 80
    )

    print(
        "NAME:",
        trait_name,
    )


    # =====================================
    # 가장 가까운 특성 컨테이너 찾기
    # =====================================

    container = (
        desc_element.find_parent(
            "li"
        )
        or
        desc_element.parent
    )


    print(
        "CONTAINER TAG:",
        container.name
        if container
        else None,
    )


    print(
        "CONTAINER CLASS:",
        container.get(
            "class"
        )
        if container
        else None,
    )


    # =====================================
    # IMG
    # =====================================

    images = (
        container.find_all(
            "img"
        )
        if container
        else []
    )


    print(
        "IMG COUNT:",
        len(images),
    )


    for (
        image_index,
        image
    ) in enumerate(
        images,
        start=1,
    ):

        image_src = (
            image.get(
                "src"
            )
            or
            image.get(
                "data-src"
            )
            or
            ""
        )


        if image_src:

            image_src = urljoin(
                PLAYER_INFO_URL,
                image_src,
            )


        print(
            f"IMG #{image_index}:",
            image_src,
        )


        print(
            f"IMG CLASS #{image_index}:",
            image.get(
                "class"
            ),
        )


    # =====================================
    # 부모 내부 요소
    # class / style / background 검사
    # =====================================

    print(
        "ELEMENTS:"
    )


    if container:

        for element in container.find_all(
            True
        ):

            classes = element.get(
                "class"
            )


            style = element.get(
                "style"
            )


            src = element.get(
                "src"
            )


            if (
                classes
                or
                style
                or
                src
            ):

                print(
                    " ",
                    element.name,
                    "CLASS=",
                    classes,
                    "STYLE=",
                    style,
                    "SRC=",
                    src,
                )


    # =====================================
    # HTML
    # =====================================

    if container:

        compact_html = (
            str(
                container
            )
            .replace(
                "\n",
                " ",
            )
        )


        print(
            "HTML:",
            compact_html[:2000],
        )


# =========================================
# SKILL WRAP RAW HTML
# =========================================

print()
print("=" * 80)
print("SKILL WRAP HTML")
print("=" * 80)


skill_wrap = soup.select_one(
    "div.skill_wrap"
)


if skill_wrap:

    skill_html = (
        str(
            skill_wrap
        )
        .replace(
            "\n",
            " ",
        )
    )


    print(
        skill_html[:6000]
    )

else:

    print(
        "skill_wrap 없음"
    )