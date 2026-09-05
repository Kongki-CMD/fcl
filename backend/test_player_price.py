import html
import re

import httpx


SP_ID = 844273018


url = (
    "https://m.fconline.nexon.com/"
    f"datacenter/playerinfo?spid={SP_ID}"
)


headers = {
    "User-Agent":
        (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        ),

    "Referer":
        "https://m.fconline.nexon.com/",
}


response = httpx.get(
    url,
    headers=headers,
    timeout=20.0,
    follow_redirects=True,
)


response.raise_for_status()


raw_html = response.text


# =========================================
# 출력 방해하는 BASE64 이미지 제거
# =========================================

clean_html = re.sub(
    r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+",
    "[BASE64_IMAGE_REMOVED]",
    raw_html,
)


clean_html = html.unescape(
    clean_html
)


print(
    "=" * 70
)

print(
    "STATUS"
)

print(
    "=" * 70
)

print(
    response.status_code
)


print()

print(
    "=" * 70
)

print(
    "HTML LENGTH"
)

print(
    "=" * 70
)

print(
    len(raw_html)
)


# =========================================
# 1. BP 가격 추출
# =========================================

bp_pattern = re.compile(
    r"([\d,]+)\s*BP",
    re.IGNORECASE,
)


bp_matches = list(
    bp_pattern.finditer(
        clean_html
    )
)


print()

print(
    "=" * 70
)

print(
    "BP MATCHES"
)

print(
    "=" * 70
)


print(
    "COUNT:",
    len(bp_matches),
)


for (
    index,
    match,
) in enumerate(
    bp_matches,
    start=1,
):

    print(
        f"{index:02d}강 : "
        f"{match.group(1)} BP"
    )


# =========================================
# 2. 각 가격 주변 HTML 확인
# =========================================

print()

print(
    "=" * 70
)

print(
    "BP HTML CONTEXT"
)

print(
    "=" * 70
)


for (
    index,
    match,
) in enumerate(
    bp_matches,
    start=1,
):

    start = max(
        0,
        match.start() - 250,
    )

    end = min(
        len(clean_html),
        match.end() + 250,
    )


    context = (
        clean_html[
            start:end
        ]
    )


    context = re.sub(
        r"\s+",
        " ",
        context,
    )


    print()

    print(
        "-" * 70
    )

    print(
        f"PRICE #{index}"
    )

    print(
        "-" * 70
    )

    print(
        context
    )


# =========================================
# 3. eachPrice 검색
# =========================================

print()

print(
    "=" * 70
)

print(
    "EACH PRICE SEARCH"
)

print(
    "=" * 70
)


each_price_matches = list(
    re.finditer(
        r".{0,300}eachPrice.{0,600}",
        clean_html,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )
)


print(
    "COUNT:",
    len(
        each_price_matches
    )
)


for (
    index,
    match,
) in enumerate(
    each_price_matches,
    start=1,
):

    value = re.sub(
        r"\s+",
        " ",
        match.group(0),
    )


    print()

    print(
        f"[eachPrice #{index}]"
    )

    print(
        value
    )


# =========================================
# 4. 가격 관련 클래스 / 속성 검색
# =========================================

print()

print(
    "=" * 70
)

print(
    "PRICE KEYWORD SEARCH"
)

print(
    "=" * 70
)


price_keyword_matches = re.findall(
    r"<[^>]*(?:price|market|trade)[^>]*>",
    clean_html,
    flags=re.IGNORECASE,
)


print(
    "COUNT:",
    len(
        price_keyword_matches
    )
)


for tag in (
    price_keyword_matches[:50]
):

    print(
        tag
    )


# =========================================
# 5. HTML 저장
# =========================================

output_path = (
    "E:\\fcweb\\backend\\"
    "player_price_debug.html"
)


with open(
    output_path,
    "w",
    encoding="utf-8",
) as file:

    file.write(
        clean_html
    )


print()

print(
    "=" * 70
)

print(
    "HTML SAVED"
)

print(
    "=" * 70
)

print(
    output_path
)