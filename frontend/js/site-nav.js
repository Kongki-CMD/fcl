const siteMainMenuElement =
    document.querySelector(
        ".main-menu"
    );


const siteFooterElement =
    document.querySelector(
        "#site-footer"
    );


const siteVersion =
    "V1.2";


// =========================================
// 공통 헤더 메뉴
// =========================================

if (siteMainMenuElement) {

    const siteNavigationItems = [
        {
            label:
                "경기",

            children: [
                {
                    label:
                        "경기 일정",

                    href:
                        "./schedule.html",
                },

                {
                    label:
                        "경기 결과",

                    href:
                        "./results.html",
                },

                {
                    label:
                        "경기 규칙",

                    href:
                        "./rules.html",
                },
            ],
        },

        {
            label:
                "기록",

            children: [
                {
                    label:
                        "팀 기록",

                    href:
                        "./standings.html",
                },

                {
                    label:
                        "선수 기록",

                    href:
                        "./players.html",
                },
            ],
        },

        {
            label:
                "커뮤니티",

            children: [
                {
                    label:
                        "친선전 예약",

                    href:
                        "./preseason.html",
                },

                {
                    label:
                        "자유게시판",

                    href:
                        "./community.html",
                },

                {
                    label:
                        "선수 사진 요청",

                    href:
                        "./player-photo-request.html",
                },
            ],
        },

        {
            label:
                "패치노트",

            href:
                "./patch-notes.html",
        },
    ];


    siteMainMenuElement
        .innerHTML = "";


    const currentPageName =
        window.location.pathname
            .split("/")
            .pop()
        || "index.html";


    siteNavigationItems.forEach(
        (navigationItem) => {

            const menuItemElement =
                document.createElement(
                    "li"
                );


            menuItemElement.classList.add(
                "menu-item"
            );


            const menuTitleElement =
                document.createElement(
                    "a"
                );


            menuTitleElement.textContent =
                navigationItem.label;


            // =====================================
            // 단독 메뉴
            // =====================================

            if (navigationItem.href) {

                menuTitleElement.href =
                    navigationItem.href;


                const linkPageName =
                    navigationItem.href
                        .replace(
                            "./",
                            ""
                        );


                if (
                    linkPageName
                    === currentPageName
                ) {

                    menuTitleElement.setAttribute(
                        "aria-current",
                        "page"
                    );

                }


                menuItemElement.appendChild(
                    menuTitleElement
                );


                siteMainMenuElement
                    .appendChild(
                        menuItemElement
                    );


                return;

            }


            // =====================================
            // 하위 메뉴가 있는 메뉴
            // =====================================

            menuTitleElement.href =
                "#";


            const subMenuElement =
                document.createElement(
                    "ul"
                );


            subMenuElement.classList.add(
                "sub-menu"
            );


            navigationItem.children.forEach(
                (childItem) => {

                    const subMenuItemElement =
                        document.createElement(
                            "li"
                        );


                    const linkElement =
                        document.createElement(
                            "a"
                        );


                    linkElement.href =
                        childItem.href;


                    linkElement.textContent =
                        childItem.label;


                    const linkPageName =
                        childItem.href
                            .replace(
                                "./",
                                ""
                            );


                    if (
                        linkPageName
                        === currentPageName
                    ) {

                        linkElement.setAttribute(
                            "aria-current",
                            "page"
                        );

                    }


                    subMenuItemElement
                        .appendChild(
                            linkElement
                        );


                    subMenuElement
                        .appendChild(
                            subMenuItemElement
                        );

                }
            );


            menuItemElement.append(
                menuTitleElement,
                subMenuElement
            );


            siteMainMenuElement
                .appendChild(
                    menuItemElement
                );

        }
    );

}


// =========================================
// 공통 FOOTER
// =========================================

if (siteFooterElement) {

    siteFooterElement.innerHTML = `
        <p>
            [${siteVersion}]
            FCL Created by aria
        </p>
    `;

}