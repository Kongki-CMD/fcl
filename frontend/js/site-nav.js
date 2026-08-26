const siteMainMenuElement =
    document.querySelector(
        ".main-menu"
    );


const siteFooterElement =
    document.querySelector(
        "#site-footer"
    );


const siteVersion =
    "v1.31";


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
            label: "놀이터",
            children: [
                {
                    label: "승부예측",
                    href: "./prediction.html",
                },
                {
                    label: "이벤트",
                    href: "./event.html",
                },
                {
                    label: "포인트 교환소",
                    href: "./point-shop.html",
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
            FCL Created by aria
            [${siteVersion}]
        </p>
    `;

}

// =========================================
// USER AUTH UI
// =========================================

async function initializeUserAuthUi() {

    const {
        getCurrentUser,
        loginUser,
        signupUser,
        logoutUser,
    } = await import(
        "./auth.js"
    );


    const headerContainerElement =
        document.querySelector(
            ".header-container"
        );


    if (!headerContainerElement) {
        return;
    }


    // =====================================
    // 헤더 회원 영역 생성
    // =====================================

    let authAreaElement =
        document.querySelector(
            "#site-auth-area"
        );


    if (!authAreaElement) {

        authAreaElement =
            document.createElement(
                "div"
            );


        authAreaElement.id =
            "site-auth-area";


        authAreaElement.classList.add(
            "site-auth-area"
        );


        headerContainerElement.append(
            authAreaElement
        );

    }


    // =====================================
    // 로그인 / 회원가입 모달 생성
    // =====================================

    let authModalElement =
        document.querySelector(
            "#site-auth-modal"
        );


    if (!authModalElement) {

        authModalElement =
            document.createElement(
                "div"
            );


        authModalElement.id =
            "site-auth-modal";


        authModalElement.className =
            "site-auth-modal hidden";


        authModalElement.innerHTML = `
            <div
                class="site-auth-modal-backdrop"
                data-auth-close
            ></div>

            <div class="site-auth-modal-card">

                <button
                    type="button"
                    class="site-auth-modal-close"
                    data-auth-close
                    aria-label="닫기"
                >
                    ×
                </button>

                <div class="site-auth-tabs">

                    <button
                        type="button"
                        class="
                            site-auth-tab
                            active
                        "
                        data-auth-tab="login"
                    >
                        로그인
                    </button>

                    <button
                        type="button"
                        class="site-auth-tab"
                        data-auth-tab="signup"
                    >
                        회원가입
                    </button>

                </div>


                <form
                    id="site-login-form"
                    class="site-auth-form"
                >

                    <h2>
                        FCL LOGIN
                    </h2>

                    <input
                        type="email"
                        id="site-login-email"
                        placeholder="이메일"
                        autocomplete="email"
                        required
                    >

                    <input
                        type="password"
                        id="site-login-password"
                        placeholder="비밀번호"
                        autocomplete="current-password"
                        required
                    >

                    <button
                        type="submit"
                        class="site-auth-submit"
                    >
                        로그인
                    </button>

                    <p
                        id="site-login-message"
                        class="site-auth-message"
                    ></p>

                </form>


                <form
                    id="site-signup-form"
                    class="
                        site-auth-form
                        hidden
                    "
                >

                    <h2>
                        FCL SIGN UP
                    </h2>

                    <input
                        type="email"
                        id="site-signup-email"
                        placeholder="이메일"
                        autocomplete="email"
                        required
                    >

                    <input
                        type="text"
                        id="site-signup-nickname"
                        placeholder="닉네임"
                        autocomplete="nickname"
                        minlength="2"
                        maxlength="20"
                        required
                    >

                    <input
                        type="password"
                        id="site-signup-password"
                        placeholder="비밀번호 (8자 이상)"
                        autocomplete="new-password"
                        minlength="8"
                        required
                    >

                    <button
                        type="submit"
                        class="site-auth-submit"
                    >
                        회원가입
                    </button>

                    <p
                        id="site-signup-message"
                        class="site-auth-message"
                    ></p>

                </form>

            </div>
        `;


        document.body.append(
            authModalElement
        );

    }


    const loginFormElement =
        authModalElement.querySelector(
            "#site-login-form"
        );


    const signupFormElement =
        authModalElement.querySelector(
            "#site-signup-form"
        );


    const loginMessageElement =
        authModalElement.querySelector(
            "#site-login-message"
        );


    const signupMessageElement =
        authModalElement.querySelector(
            "#site-signup-message"
        );


    // =====================================
    // 모달
    // =====================================

    function openAuthModal(
        tabName = "login"
    ) {

        authModalElement.classList.remove(
            "hidden"
        );


        document.body.classList.add(
            "site-auth-modal-open"
        );


        selectAuthTab(
            tabName
        );

    }


    function closeAuthModal() {

        authModalElement.classList.add(
            "hidden"
        );


        document.body.classList.remove(
            "site-auth-modal-open"
        );


        loginMessageElement.textContent =
            "";


        signupMessageElement.textContent =
            "";

    }


    function selectAuthTab(
        tabName
    ) {

        authModalElement
            .querySelectorAll(
                ".site-auth-tab"
            )
            .forEach(
                buttonElement => {

                    buttonElement
                        .classList.toggle(
                            "active",
                            buttonElement
                                .dataset
                                .authTab
                            === tabName
                        );

                }
            );


        loginFormElement
            .classList.toggle(
                "hidden",
                tabName !== "login"
            );


        signupFormElement
            .classList.toggle(
                "hidden",
                tabName !== "signup"
            );

    }


    // =====================================
    // 현재 회원 상태 출력
    // =====================================

    async function renderAuthState() {

        const user =
            await getCurrentUser();


        if (!user) {

            authAreaElement.innerHTML = `
                <button
                    type="button"
                    class="site-auth-button"
                    data-open-login
                >
                    로그인
                </button>

                <button
                    type="button"
                    class="
                        site-auth-button
                        signup
                    "
                    data-open-signup
                >
                    회원가입
                </button>
            `;


            authAreaElement
                .querySelector(
                    "[data-open-login]"
                )
                .addEventListener(
                    "click",
                    () => {
                        openAuthModal(
                            "login"
                        );
                    }
                );


            authAreaElement
                .querySelector(
                    "[data-open-signup]"
                )
                .addEventListener(
                    "click",
                    () => {
                        openAuthModal(
                            "signup"
                        );
                    }
                );


            return;

        }


        authAreaElement.innerHTML = `
            <div class="site-user-info">

                <a
                    href="./mypage.html"
                    class="site-user-nickname"
                ></a>

                <span class="site-user-points">
                    ${Number(
                        user.points ?? 0
                    ).toLocaleString()}
                    P
                </span>

                <button
                    type="button"
                    class="site-logout-button"
                >
                    로그아웃
                </button>

            </div>
        `;


authAreaElement
    .querySelector(
        ".site-user-nickname"
    )
    .textContent =
        user.nickname;


        authAreaElement
            .querySelector(
                ".site-logout-button"
            )
            .addEventListener(
                "click",
                async () => {

                    await logoutUser();

                    await renderAuthState();

                }
            );

    }


    // =====================================
    // 탭
    // =====================================

    authModalElement
        .querySelectorAll(
            ".site-auth-tab"
        )
        .forEach(
            buttonElement => {

                buttonElement
                    .addEventListener(
                        "click",
                        () => {

                            selectAuthTab(
                                buttonElement
                                    .dataset
                                    .authTab
                            );

                        }
                    );

            }
        );


    // =====================================
    // 닫기
    // =====================================

    authModalElement
        .querySelectorAll(
            "[data-auth-close]"
        )
        .forEach(
            element => {

                element.addEventListener(
                    "click",
                    closeAuthModal
                );

            }
        );


    // =====================================
    // 로그인
    // =====================================

    loginFormElement.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const email =
                authModalElement
                    .querySelector(
                        "#site-login-email"
                    )
                    .value
                    .trim();


            const password =
                authModalElement
                    .querySelector(
                        "#site-login-password"
                    )
                    .value;


            const submitButtonElement =
                loginFormElement.querySelector(
                    ".site-auth-submit"
                );


            submitButtonElement.disabled =
                true;


            submitButtonElement.textContent =
                "로그인 중...";


            loginMessageElement.textContent =
                "";


            try {

                await loginUser(
                    email,
                    password
                );


                loginFormElement.reset();


                closeAuthModal();


                await renderAuthState();


            } catch (error) {

                loginMessageElement.textContent =
                    error.message;


            } finally {

                submitButtonElement.disabled =
                    false;


                submitButtonElement.textContent =
                    "로그인";

            }

        }
    );


    // =====================================
    // 회원가입
    // =====================================

    signupFormElement.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const email =
                authModalElement
                    .querySelector(
                        "#site-signup-email"
                    )
                    .value
                    .trim();


            const nickname =
                authModalElement
                    .querySelector(
                        "#site-signup-nickname"
                    )
                    .value
                    .trim();


            const password =
                authModalElement
                    .querySelector(
                        "#site-signup-password"
                    )
                    .value;


            const submitButtonElement =
                signupFormElement.querySelector(
                    ".site-auth-submit"
                );


            submitButtonElement.disabled =
                true;


            submitButtonElement.textContent =
                "가입 중...";


            signupMessageElement.textContent =
                "";


            try {

                await signupUser(
                    email,
                    password,
                    nickname
                );


                signupFormElement.reset();


                signupMessageElement.textContent =
                    "회원가입이 완료되었습니다.";


                setTimeout(
                    () => {

                        selectAuthTab(
                            "login"
                        );

                        signupMessageElement
                            .textContent = "";

                        authModalElement
                            .querySelector(
                                "#site-login-email"
                            )
                            .value =
                                email;

                    },
                    700
                );


            } catch (error) {

                signupMessageElement.textContent =
                    error.message;


            } finally {

                submitButtonElement.disabled =
                    false;


                submitButtonElement.textContent =
                    "회원가입";

            }

        }
    );


    // =====================================
    // ESC 닫기
    // =====================================

    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
                &&
                !authModalElement
                    .classList
                    .contains(
                        "hidden"
                    )
            ) {

                closeAuthModal();

            }

        }
    );


    await renderAuthState();

}


initializeUserAuthUi();