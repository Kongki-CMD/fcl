"""FC Online 공식 생성 제한/해제 공지 수집."""

from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser

import httpx


NOTICE_LIST_URL = (
    "https://fconline.nexon.com/"
    "news/notice/list"
)

NOTICE_VIEW_URL = (
    "https://fconline.nexon.com/"
    "news/notice/view"
)

SEASON_METADATA_URL = (
    "https://open.api.nexon.com/"
    "static/fconline/meta/seasonid.json"
)

SEASON_CLASS_CACHE = None

NOTICE_SEARCH_TERMS = (
    "생성 제한",
    "생성제한",
    "생성 해제",
)

ARTICLE_SN_PATTERN = re.compile(
    r"n4ArticleSN=(\d+)",
    flags=re.IGNORECASE,
)

NOTICE_DATE_PATTERN = re.compile(
    r"\b"
    r"(20\d{2})"
    r"[.\-/]"
    r"(\d{1,2})"
    r"[.\-/]"
    r"(\d{1,2})"
    r"\b"
)

RESTRICTION_PATTERN = re.compile(
    r"생성\s*"
    r"[‘’'\"“”]?\s*"
    r"제한",
    flags=re.IGNORECASE,
)

RELEASE_PATTERN = re.compile(
    r"(?:"
    r"생성\s*제한"
    r".{0,50}"
    r"해제"
    r"|"
    r"생성\s*해제"
    r")",
    flags=(
        re.IGNORECASE
        | re.DOTALL
    ),
)

ALL_CLASS_RESTRICT_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수의\s*모든\s*클래스가\s*"
    r"생성\s*[‘’'\"“”]?\s*제한\s*[‘’'\"“”]?\s*"
    r"됩니다",
    flags=re.IGNORECASE,
)


AVAILABLE_CHANGE_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수(?:가|는)?\s*"
    r"생성\s*가능으로\s*변경\s*됩니다"
    r"(?:"
    r".{0,180}?"
    r"일부\s*클래스는"
    r".{0,120}?"
    r"\("
    r"(?P<exceptions>[^)]+)"
    r"\)"
    r")?",
    flags=re.IGNORECASE,
)


DIRECT_RELEASE_PATTERN = re.compile(
    r"(?:\[|\()\s*"
    r"(?P<subject>[^\]\)]+?)"
    r"\s*(?:\]|\))"
    r"\s*선수(?:가|는)?\s*"
    r"생성\s*제한\s*해제"
    r"(?:됩니다|되었습니다|된)",
    flags=re.IGNORECASE,
)


DIRECT_RESTRICT_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수(?:가|는)?\s*"
    r"생성\s*제한\s*됩니다",
    flags=re.IGNORECASE,
)


RESTRICTED_LAUNCH_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수"
    r"(?:는|의\s*경우)?\s*"
    r"생성\s*제한\s*형태로\s*출시",
    flags=re.IGNORECASE,
)


PARTIAL_RESTRICTION_FIX_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수의\s*일부\s*클래스에\s*"
    r"생성\s*제한\s*처리가\s*되지\s*않았던\s*"
    r"현상이\s*수정",
    flags=re.IGNORECASE,
)


GENERATION_INFO_FIX_PATTERN = re.compile(
    r"\[\s*"
    r"(?P<subject>[^\]]+?)"
    r"\s*\]"
    r"\s*선수의\s*선수\s*생성\s*정보가\s*"
    r"가능이\s*아닌\s*,?\s*"
    r"제한으로\s*정상\s*안내",
    flags=re.IGNORECASE,
)


class NoticeHtmlParser(
    HTMLParser
):
    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.parts = []

        self.skip_depth = 0

        self.title = None


    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        normalized_tag = (
            str(tag)
            .strip()
            .lower()
        )

        if normalized_tag in (
            "script",
            "style",
            "noscript",
        ):
            self.skip_depth += 1
            return

        if normalized_tag == "meta":
            attributes = {
                str(key).lower():
                    value

                for key, value
                in attrs
            }

            property_name = (
                attributes.get(
                    "property"
                )
                or
                attributes.get(
                    "name"
                )
                or ""
            )

            if (
                str(property_name)
                .strip()
                .lower()
                in (
                    "og:title",
                    "twitter:title",
                )
            ):
                content = (
                    attributes.get(
                        "content"
                    )
                    or ""
                )

                content = (
                    str(content)
                    .strip()
                )

                if content:
                    self.title = content


    def handle_endtag(
        self,
        tag,
    ):
        normalized_tag = (
            str(tag)
            .strip()
            .lower()
        )

        if (
            normalized_tag
            in (
                "script",
                "style",
                "noscript",
            )
            and
            self.skip_depth > 0
        ):
            self.skip_depth -= 1


    def handle_data(
        self,
        data,
    ):
        if self.skip_depth:
            return

        text = (
            str(data)
            .strip()
        )

        if text:
            self.parts.append(
                text
            )


    def get_text(self):
        return "\n".join(
            self.parts
        )


def normalize_notice_text(
    text,
):
    return re.sub(
        r"[ \t\r\f\v]+",
        " ",
        str(text or ""),
    ).strip()

def get_generation_season_class_map():
    global SEASON_CLASS_CACHE

    if SEASON_CLASS_CACHE is not None:
        return SEASON_CLASS_CACHE

    response = httpx.get(
        SEASON_METADATA_URL,
        timeout=20.0,
        follow_redirects=True,
    )

    response.raise_for_status()

    season_map = {}

    for season in response.json():
        season_id = int(
            season[
                "seasonId"
            ]
        )

        class_name = (
            str(
                season.get(
                    "className",
                    "",
                )
            )
            .strip()
        )

        season_map[
            season_id
        ] = class_name

    SEASON_CLASS_CACHE = (
        season_map
    )

    return SEASON_CLASS_CACHE


def normalize_class_name(
    value,
):
    text = (
        str(value or "")
        .strip()
        .upper()
    )

    # =========================================
    # Nexon season className 예:
    #
    # "19 UCL (19 UEFA Champions League)"
    # "LH (Loyal Heroes)"
    # "BOE21 (Best of Europe 21)"
    #
    # 공지에서는:
    #
    # "19UCL", "LH", "BOE21"
    #
    # 형태로 표기되므로 괄호 앞의
    # 클래스 코드만 비교한다.
    # =========================================

    class_code = (
        text.split(
            "(",
            1,
        )[0]
        .strip()
        .replace(
            " ",
            "",
        )
    )

    return class_code

def compact_notice_text(
    text,
):
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def split_notice_subjects(
    value,
):
    return [
        re.sub(
            r"\s+",
            " ",
            part,
        ).strip()

        for part
        in re.split(
            r"\s*,\s*",
            str(value or ""),
        )

        if part.strip()
    ]


def split_class_tokens(
    value,
):
    if not value:
        return []

    return [
        token.strip()

        for token
        in re.split(
            r"\s*[,/]\s*",
            str(value),
        )

        if token.strip()
    ]


def extract_generation_actions(
    body_text,
):
    text = compact_notice_text(
        body_text
    )

    actions = []
    seen = set()


    def add_action(
        *,
        action,
        scope,
        match,
        requires_review=False,
        exception_classes=None,
    ):
        raw_subject = (
            match.groupdict()
            .get(
                "subject",
                "",
            )
            or ""
        ).strip()

        subjects = (
            split_notice_subjects(
                raw_subject
            )
        )

        exceptions = list(
            exception_classes
            or []
        )

        evidence = (
            match.group(0)
            .strip()
        )

        key = (
            action,
            scope,
            raw_subject,
            tuple(exceptions),
            evidence,
        )

        if key in seen:
            return

        seen.add(key)

        actions.append(
            {
                "action":
                    action,

                "desired_restricted":
                    (
                        True
                        if action == "restrict"
                        else False
                    ),

                "scope":
                    scope,

                "raw_subject":
                    raw_subject,

                "subjects":
                    subjects,

                "exception_classes":
                    exceptions,

                "requires_review":
                    bool(
                        requires_review
                    ),

                "evidence":
                    evidence,
            }
        )


    # =========================================
    # 모든 클래스 생성 제한
    # =========================================

    for match in (
        ALL_CLASS_RESTRICT_PATTERN
        .finditer(text)
    ):
        add_action(
            action="restrict",
            scope="all_classes",
            match=match,
        )


    # =========================================
    # 생성 가능으로 변경
    #
    # 일부 클래스 제한 유지 예외도 보존
    # =========================================

    for match in (
        AVAILABLE_CHANGE_PATTERN
        .finditer(text)
    ):
        exceptions = (
            split_class_tokens(
                match.groupdict()
                .get(
                    "exceptions"
                )
            )
        )

        add_action(
            action="release",
            scope=(
                "all_except_classes"
                if exceptions
                else "unknown"
            ),
            match=match,
            exception_classes=exceptions,
            requires_review=not bool(
                exceptions
            ),
        )


    # =========================================
    # 명시적 생성 제한 해제
    # =========================================

    for match in (
        DIRECT_RELEASE_PATTERN
        .finditer(text)
    ):
        add_action(
            action="release",
            scope="unknown",
            match=match,
            requires_review=True,
        )


    # =========================================
    # 명시적 생성 제한
    #
    # [] 안에 클래스 + 선수명이 같이
    # 들어가는 사례가 있으므로 일단 검토
    # =========================================

    for match in (
        DIRECT_RESTRICT_PATTERN
        .finditer(text)
    ):
        add_action(
            action="restrict",
            scope="subject_label",
            match=match,
            requires_review=True,
        )


    # =========================================
    # 특정 클래스가 제한 상태로 출시
    # =========================================

    for match in (
        RESTRICTED_LAUNCH_PATTERN
        .finditer(text)
    ):
        add_action(
            action="restrict",
            scope="subject_label",
            match=match,
            requires_review=True,
        )


    # =========================================
    # 일부 클래스 제한 누락 수정
    #
    # 어떤 클래스인지 확정할 수 없으므로
    # 절대 자동 적용하지 않는다.
    # =========================================

    for match in (
        PARTIAL_RESTRICTION_FIX_PATTERN
        .finditer(text)
    ):
        add_action(
            action="restrict",
            scope="partial_unknown",
            match=match,
            requires_review=True,
        )


    # =========================================
    # 생성 정보 표시 수정
    #
    # 실제 제한 범위가 불명확하므로 검토
    # =========================================

    for match in (
        GENERATION_INFO_FIX_PATTERN
        .finditer(text)
    ):
        add_action(
            action="restrict",
            scope="unknown",
            match=match,
            requires_review=True,
        )


    return actions


def parse_notice_date(
    text,
):
    match = (
        NOTICE_DATE_PATTERN
        .search(
            str(text or "")
        )
    )

    if not match:
        return None

    try:
        return date(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

    except ValueError:
        return None


def extract_notice_ids(
    html_text,
):
    return {
        int(match.group(1))

        for match
        in ARTICLE_SN_PATTERN
        .finditer(
            str(html_text or "")
        )
    }


def fetch_generation_notice_ids(
    *,
    max_pages=50,
):
    notice_ids = set()

    headers = {
        "User-Agent":
            (
                "Mozilla/5.0 "
                "FCL-Generation-Notice-Sync"
            ),
    }

    with httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers=headers,
    ) as client:

        for search_term in (
            NOTICE_SEARCH_TERMS
        ):

            empty_pages = 0

            for page in range(
                1,
                max_pages + 1,
            ):

                response = client.get(
                    NOTICE_LIST_URL,
                    params={
                        "emsearchtype":
                            "titlecontents",

                        "strsearch":
                            search_term,

                        "n4pageno":
                            page,

                        "n4articlecategorysn":
                            0,

                        "n4articlecategory2sn":
                            0,
                    },
                )

                response.raise_for_status()

                page_ids = (
                    extract_notice_ids(
                        response.text
                    )
                )

                if not page_ids:
                    empty_pages += 1

                    if empty_pages >= 2:
                        break

                    continue

                empty_pages = 0

                previous_count = len(
                    notice_ids
                )

                notice_ids.update(
                    page_ids
                )

                if (
                    len(notice_ids)
                    ==
                    previous_count
                    and
                    page >= 3
                ):
                    break

    return sorted(
        notice_ids
    )


def fetch_generation_notice(
    notice_sn,
):
    headers = {
        "User-Agent":
            (
                "Mozilla/5.0 "
                "FCL-Generation-Notice-Sync"
            ),
    }

    with httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers=headers,
    ) as client:

        response = client.get(
            NOTICE_VIEW_URL,
            params={
                "n4ArticleSN":
                    int(notice_sn),
            },
        )

        response.raise_for_status()


    parser = NoticeHtmlParser()

    parser.feed(
        response.text
    )

    body_text = (
        parser.get_text()
    )

    normalized_text = (
        normalize_notice_text(
            body_text
        )
    )


    has_restriction = bool(
        RESTRICTION_PATTERN.search(
            normalized_text
        )
    )

    has_release = bool(
        RELEASE_PATTERN.search(
            normalized_text
        )
    )


    if not (
        has_restriction
        or has_release
    ):
        return None


    title = (
        parser.title
        or
        (
            f"FC Online 공지 "
            f"{notice_sn}"
        )
    )


    notice_date = (
        parse_notice_date(
            body_text
        )
    )


    source_url = (
        f"{NOTICE_VIEW_URL}"
        f"?n4ArticleSN="
        f"{int(notice_sn)}"
    )


    return {
        "notice_sn":
            int(notice_sn),

        "title":
            str(title).strip(),

        "notice_date":
            notice_date,

        "source_url":
            source_url,

        "body_text":
            body_text,

        "has_restriction_keyword":
            has_restriction,

        "has_release_keyword":
            has_release,
    }


def sync_generation_notices(
    connection,
    *,
    max_pages=50,
):
    notice_ids = (
        fetch_generation_notice_ids(
            max_pages=max_pages
        )
    )

    saved = 0
    skipped = 0
    failed = []


    for notice_sn in notice_ids:

        try:
            notice = (
                fetch_generation_notice(
                    notice_sn
                )
            )

        except Exception as error:
            failed.append(
                {
                    "notice_sn":
                        int(notice_sn),

                    "error":
                        str(error),
                }
            )
            continue


        if notice is None:
            skipped += 1
            continue


        with connection.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO
                    fconline_generation_notices (
                        notice_sn,
                        title,
                        notice_date,
                        source_url,
                        body_text,
                        has_restriction_keyword,
                        has_release_keyword,
                        fetched_at,
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
                    NOW(),
                    NOW()
                )

                ON CONFLICT (
                    notice_sn
                )

                DO UPDATE SET
                    title =
                        EXCLUDED.title,

                    notice_date =
                        EXCLUDED.notice_date,

                    source_url =
                        EXCLUDED.source_url,

                    body_text =
                        EXCLUDED.body_text,

                    has_restriction_keyword =
                        EXCLUDED
                        .has_restriction_keyword,

                    has_release_keyword =
                        EXCLUDED
                        .has_release_keyword,

                    fetched_at =
                        NOW(),

                    updated_at =
                        NOW()
                """,
                (
                    notice[
                        "notice_sn"
                    ],

                    notice[
                        "title"
                    ],

                    notice[
                        "notice_date"
                    ],

                    notice[
                        "source_url"
                    ],

                    notice[
                        "body_text"
                    ],

                    notice[
                        "has_restriction_keyword"
                    ],

                    notice[
                        "has_release_keyword"
                    ],
                ),
            )

        saved += 1


    connection.commit()


    return {
        "discovered":
            len(notice_ids),

        "saved":
            saved,

        "skipped":
            skipped,

        "failed":
            failed,
    }


def get_generation_notice_status(
        
    connection,
):
    with connection.cursor() as cursor:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS notice_count,

                MAX(notice_date)
                    AS latest_notice_date,

                COUNT(*) FILTER (
                    WHERE
                        has_restriction_keyword
                )
                    AS restriction_count,

                COUNT(*) FILTER (
                    WHERE
                        has_release_keyword
                )
                    AS release_count

            FROM
                fconline_generation_notices
            """
        )

        row = cursor.fetchone()


    return {
        "notice_count":
            int(
                row[
                    "notice_count"
                ]
                or 0
            ),

        "latest_notice_date":
            (
                row[
                    "latest_notice_date"
                ].isoformat()

                if row[
                    "latest_notice_date"
                ]

                else None
            ),

        "restriction_count":
            int(
                row[
                    "restriction_count"
                ]
                or 0
            ),

        "release_count":
            int(
                row[
                    "release_count"
                ]
                or 0
            ),
    }

def get_generation_action_preview(
    connection,
    *,
    limit=100,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                notice_sn,
                title,
                notice_date,
                source_url,
                body_text
            FROM
                fconline_generation_notices
            ORDER BY
                notice_date DESC NULLS LAST,
                notice_sn DESC
            LIMIT %s
            """,
            (
                int(limit),
            ),
        )

        rows = cursor.fetchall()


    results = []


    for row in rows:

        actions = (
            extract_generation_actions(
                row[
                    "body_text"
                ]
            )
        )

        if not actions:
            continue


        results.append(
            {
                "notice_sn":
                    int(
                        row[
                            "notice_sn"
                        ]
                    ),

                "title":
                    row[
                        "title"
                    ],

                "notice_date":
                    (
                        row[
                            "notice_date"
                        ].isoformat()

                        if row[
                            "notice_date"
                        ]

                        else None
                    ),

                "source_url":
                    row[
                        "source_url"
                    ],

                "action_count":
                    len(
                        actions
                    ),

                "actions":
                    actions,
            }
        )


    return results

def get_generation_resolution_preview(
    connection,
    *,
    limit=100,
):
    season_class_map = (
        get_generation_season_class_map()
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                notice_sn,
                title,
                notice_date,
                source_url,
                body_text
            FROM
                fconline_generation_notices
            ORDER BY
                notice_date DESC NULLS LAST,
                notice_sn ASC
            LIMIT %s
            """,
            (
                int(limit),
            ),
        )

        rows = cursor.fetchall()

    # =========================================
    # DB에서는 최신 공지부터 필요한 수만 가져오되,
    # 실제 상태 해석은 오래된 공지 → 최신 공지
    # 순서로 진행한다.
    #
    # 그래야 나중의 해제/재제한 공지가
    # 과거 상태를 올바르게 덮어쓸 수 있다.
    # =========================================

    rows = sorted(
        rows,
        key=lambda row: (
            row["notice_date"]
            or date.min,
            int(
                row[
                    "notice_sn"
                ]
            ),
        ),
    )


    resolutions = []

    review_actions = []

    unmatched_subjects = []

    total_status_updates = 0


    for row in rows:

        actions = (
            extract_generation_actions(
                row[
                    "body_text"
                ]
            )
        )


        for action in actions:

            # =====================================
            # 사람이 확인해야 하는 공지는
            # 자동 SPID 적용 대상에서 제외
            # =====================================

            if action[
                "requires_review"
            ]:

                review_actions.append(
                    {
                        "notice_sn":
                            int(
                                row[
                                    "notice_sn"
                                ]
                            ),

                        "notice_date":
                            (
                                row[
                                    "notice_date"
                                ].isoformat()

                                if row[
                                    "notice_date"
                                ]

                                else None
                            ),

                        "action":
                            action[
                                "action"
                            ],

                        "scope":
                            action[
                                "scope"
                            ],

                        "subjects":
                            action[
                                "subjects"
                            ],

                        "evidence":
                            action[
                                "evidence"
                            ],
                    }
                )

                continue


            # =====================================
            # 현재 자동 적용 가능한 범위만 허용
            # =====================================

            if action[
                "scope"
            ] not in (
                "all_classes",
                "all_except_classes",
            ):
                continue


            exception_classes = {
                normalize_class_name(
                    value
                )

                for value
                in action[
                    "exception_classes"
                ]
            }


            for subject in action[
                "subjects"
            ]:

                with connection.cursor() as cursor:

                    cursor.execute(
                        """
                        SELECT
                            sp_id,
                            player_name,
                            season_id
                        FROM
                            fconline_players
                        WHERE
                            LOWER(
                                TRIM(
                                    player_name
                                )
                            )
                            =
                            LOWER(
                                TRIM(
                                    %s
                                )
                            )
                        ORDER BY
                            season_id,
                            sp_id
                        """,
                        (
                            subject,
                        ),
                    )

                    player_rows = (
                        cursor.fetchall()
                    )


                if not player_rows:

                    unmatched_subjects.append(
                        {
                            "notice_sn":
                                int(
                                    row[
                                        "notice_sn"
                                    ]
                                ),

                            "subject":
                                subject,

                            "action":
                                action[
                                    "action"
                                ],

                            "scope":
                                action[
                                    "scope"
                                ],
                        }
                    )

                    continue


                updates = []

                unknown_class_spids = []


                for player in player_rows:

                    season_id = int(
                        player[
                            "season_id"
                        ]
                    )

                    class_name = (
                        season_class_map.get(
                            season_id,
                            "",
                        )
                    )

                    normalized_class = (
                        normalize_class_name(
                            class_name
                        )
                    )


                    # =================================
                    # 시즌 클래스 메타를 못 찾으면
                    # 실제 자동 반영 시 제외 예정
                    # =================================

                    if not normalized_class:

                        unknown_class_spids.append(
                            int(
                                player[
                                    "sp_id"
                                ]
                            )
                        )

                        continue


                    # =================================
                    # 모든 클래스 생성 제한
                    # =================================

                    if (
                        action[
                            "scope"
                        ]
                        ==
                        "all_classes"
                    ):

                        desired_restricted = bool(
                            action[
                                "desired_restricted"
                            ]
                        )

                        reason = (
                            "all_classes"
                        )


                    # =================================
                    # 대부분 생성 가능으로 전환,
                    # 특정 클래스만 제한 유지
                    # =================================

                    else:

                        if (
                            normalized_class
                            in
                            exception_classes
                        ):

                            desired_restricted = (
                                True
                            )

                            reason = (
                                "exception_"
                                "keep_restricted"
                            )

                        else:

                            desired_restricted = (
                                False
                            )

                            reason = (
                                "released"
                            )


                    updates.append(
                        {
                            "sp_id":
                                int(
                                    player[
                                        "sp_id"
                                    ]
                                ),

                            "player_name":
                                player[
                                    "player_name"
                                ],

                            "season_id":
                                season_id,

                            "class_name":
                                class_name,

                            "generation_restricted":
                                desired_restricted,

                            "reason":
                                reason,
                        }
                    )


                total_status_updates += len(
                    updates
                )


                resolutions.append(
                    {
                        "notice_sn":
                            int(
                                row[
                                    "notice_sn"
                                ]
                            ),

                        "notice_date":
                            (
                                row[
                                    "notice_date"
                                ].isoformat()

                                if row[
                                    "notice_date"
                                ]

                                else None
                            ),

                        "subject":
                            subject,

                        "action":
                            action[
                                "action"
                            ],

                        "scope":
                            action[
                                "scope"
                            ],

                        "exception_classes":
                            action[
                                "exception_classes"
                            ],

                        "matched_player_rows":
                            len(
                                player_rows
                            ),

                        "resolved_update_count":
                            len(
                                updates
                            ),

                        "unknown_class_spids":
                            unknown_class_spids,

                        "updates":
                            updates,
                    }
                )


    return {
        "resolution_count":
            len(
                resolutions
            ),

        "status_update_count":
            total_status_updates,

        "unmatched_count":
            len(
                unmatched_subjects
            ),

        "review_action_count":
            len(
                review_actions
            ),

        "resolutions":
            resolutions,

        "unmatched_subjects":
            unmatched_subjects,

        "review_actions":
            review_actions,
    }

def sync_generation_status_from_notices(
    connection,
):
    # =========================================
    # 저장된 공식 공지 전체를 기준으로
    # 자동 확정 가능한 현재 상태를 재구성
    # =========================================

    preview = (
        get_generation_resolution_preview(
            connection,
            limit=10000,
        )
    )


    # =========================================
    # SPID를 못 찾은 선수가 있으면
    # 잘못된 상태를 반영하지 않고 중단
    # =========================================

    if (
        preview[
            "unmatched_count"
        ]
        > 0
    ):
        raise RuntimeError(
            (
                "생성 제한 상태 동기화 중 "
                "SPID를 찾지 못한 선수가 있습니다."
            )
        )


    unknown_class_spids = []

    for resolution in (
        preview[
            "resolutions"
        ]
    ):
        unknown_class_spids.extend(
            resolution[
                "unknown_class_spids"
            ]
        )


    if unknown_class_spids:
        raise RuntimeError(
            (
                "생성 제한 상태 동기화 중 "
                "시즌 클래스를 해석하지 못한 "
                "SPID가 있습니다: "
                f"{unknown_class_spids[:20]}"
            )
        )


    applied_count = 0

    restricted_count = 0

    available_count = 0

    notice_ids = set()


    with connection.cursor() as cursor:

        # =====================================
        # 기존 자동 생성 데이터는 삭제 후
        # 공식 공지 이벤트를 처음부터 재생한다.
        #
        # test / 수동 검토 데이터는
        # 여기서 삭제하지 않는다.
        # =====================================

        cursor.execute(
            """
            DELETE FROM
                fconline_player_generation_status
            WHERE
                source_type = 'official_notice'
            """
        )

        deleted_previous_count = int(
            cursor.rowcount
            or 0
        )


        # =====================================
        # resolution은 과거 → 최신 순서다.
        #
        # 동일 SPID가 여러 공지에 등장하면
        # 최신 공지가 최종 상태가 된다.
        # =====================================

        for resolution in (
            preview[
                "resolutions"
            ]
        ):

            notice_sn = int(
                resolution[
                    "notice_sn"
                ]
            )

            notice_ids.add(
                notice_sn
            )

            effective_date = (
                resolution[
                    "notice_date"
                ]
            )


            for update in (
                resolution[
                    "updates"
                ]
            ):

                sp_id = int(
                    update[
                        "sp_id"
                    ]
                )

                generation_restricted = bool(
                    update[
                        "generation_restricted"
                    ]
                )

                source_note = (
                    "FC Online 공식 공지 "
                    f"#{notice_sn}"
                    " | "
                    f"{resolution['subject']}"
                    " | "
                    f"{update['class_name']}"
                    " | "
                    f"{update['reason']}"
                )


                cursor.execute(
                    """
                    INSERT INTO
                        fconline_player_generation_status (
                            sp_id,
                            generation_restricted,
                            source_type,
                            source_note,
                            effective_date,
                            updated_at
                        )

                    VALUES (
                        %s,
                        %s,
                        'official_notice',
                        %s,
                        %s,
                        NOW()
                    )

                    ON CONFLICT (
                        sp_id
                    )

                    DO UPDATE SET
                        generation_restricted =
                            EXCLUDED
                            .generation_restricted,

                        source_type =
                            EXCLUDED
                            .source_type,

                        source_note =
                            EXCLUDED
                            .source_note,

                        effective_date =
                            EXCLUDED
                            .effective_date,

                        updated_at =
                            NOW()

                    WHERE
                        fconline_player_generation_status
                        .source_type
                        IN (
                            'official_notice',
                            'test'
                        )

                        OR

                        fconline_player_generation_status
                        .effective_date
                        IS NULL

                        OR

                        EXCLUDED.effective_date
                        >=
                        fconline_player_generation_status
                        .effective_date
                    """,
                    (
                        sp_id,
                        generation_restricted,
                        source_note,
                        effective_date,
                    ),
                )


                if (
                    cursor.rowcount
                    <= 0
                ):
                    continue


                applied_count += 1


                if generation_restricted:
                    restricted_count += 1

                else:
                    available_count += 1


    connection.commit()


    return {
        "notice_count":
            len(
                notice_ids
            ),

        "resolution_count":
            len(
                preview[
                    "resolutions"
                ]
            ),

        "applied_count":
            applied_count,

        "restricted_count":
            restricted_count,

        "available_count":
            available_count,

        "deleted_previous_count":
            deleted_previous_count,

        "review_action_count":
            preview[
                "review_action_count"
            ],

        "review_actions":
            preview[
                "review_actions"
            ],
    }

def get_generation_notice_preview(
    connection,
    *,
    limit=50,
):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                notice_sn,
                title,
                notice_date,
                source_url,
                body_text,
                has_restriction_keyword,
                has_release_keyword
            FROM
                fconline_generation_notices
            ORDER BY
                notice_date DESC NULLS LAST,
                notice_sn DESC
            LIMIT %s
            """,
            (
                int(limit),
            ),
        )

        rows = cursor.fetchall()


    results = []


    for row in rows:
        body_text = str(
            row["body_text"]
            or ""
        )

        normalized = (
            normalize_notice_text(
                body_text
            )
        )


        keyword_matches = []

        for pattern_name, pattern in (
            (
                "restriction",
                RESTRICTION_PATTERN,
            ),
            (
                "release",
                RELEASE_PATTERN,
            ),
        ):
            for match in pattern.finditer(
                normalized
            ):
                start = max(
                    0,
                    match.start() - 180,
                )

                end = min(
                    len(normalized),
                    match.end() + 280,
                )

                snippet = (
                    normalized[
                        start:end
                    ]
                    .strip()
                )

                keyword_matches.append(
                    {
                        "type":
                            pattern_name,

                        "snippet":
                            snippet,
                    }
                )


        results.append(
            {
                "notice_sn":
                    int(
                        row[
                            "notice_sn"
                        ]
                    ),

                "title":
                    row[
                        "title"
                    ],

                "notice_date":
                    (
                        row[
                            "notice_date"
                        ].isoformat()

                        if row[
                            "notice_date"
                        ]

                        else None
                    ),

                "source_url":
                    row[
                        "source_url"
                    ],

                "has_restriction_keyword":
                    bool(
                        row[
                            "has_restriction_keyword"
                        ]
                    ),

                "has_release_keyword":
                    bool(
                        row[
                            "has_release_keyword"
                        ]
                    ),

                "matches":
                    keyword_matches[
                        :8
                    ],
            }
        )


    return results