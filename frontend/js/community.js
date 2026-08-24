import {
    apiBaseUrl,
} from "./config.js";


const communityPostListElement =
    document.querySelector(
        ".community-post-list"
    );


function formatCommunityDate(
    dateValue
) {

    if (!dateValue) {
        return "-";
    }


    const date =
        new Date(
            dateValue
        );


    return date.toLocaleDateString(
        "ko-KR",
        {
            timeZone:
                "Asia/Seoul",

            year:
                "numeric",

            month:
                "2-digit",

            day:
                "2-digit",
        }
    );

}


function createCommunityMessage(
    message,
    className
) {

    const messageElement =
        document.createElement(
            "p"
        );


    messageElement.classList.add(
        className
    );


    messageElement.textContent =
        message;


    return messageElement;
}


async function loadCommunityPosts() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/community/posts?board_type=free`
            );


        if (!response.ok) {

            throw new Error(
                "게시글 목록을 불러오지 못했습니다."
            );

        }


        const posts =
            await response.json();


        renderCommunityPosts(
            posts
        );

    } catch (error) {

        console.error(
            error
        );


        communityPostListElement
            .replaceChildren(
                createCommunityMessage(
                    "게시글 목록을 불러오지 못했습니다.",
                    "community-empty"
                )
            );

    }

}


function renderCommunityPosts(
    posts
) {

    communityPostListElement
        .replaceChildren();


    if (
        posts.length === 0
    ) {

        communityPostListElement
            .appendChild(
                createCommunityMessage(
                    "등록된 게시글이 없습니다.",
                    "community-empty"
                )
            );

        return;

    }


    posts.forEach(
        (
            post,
            index
        ) => {

            const postRowElement =
                document.createElement(
                    "a"
                );


            postRowElement.href =
                `./community-detail.html?id=${post.id}`;


            postRowElement.classList.add(
                "community-post-row"
            );


            // =========================
            // 번호
            // =========================

            const postNumberElement =
                document.createElement(
                    "span"
                );


            postNumberElement.classList.add(
                "community-post-id"
            );


            postNumberElement.textContent =
                String(
                    posts.length
                    - index
                );


            // =========================
            // 제목
            // =========================

            const postTitleAreaElement =
                document.createElement(
                    "span"
                );


            postTitleAreaElement.classList.add(
                "community-post-title"
            );


            const postTitleElement =
                document.createElement(
                    "span"
                );


            postTitleElement.textContent =
                post.title;


            postTitleAreaElement.appendChild(
                postTitleElement
            );


            if (
                Number(
                    post.attachment_count
                ) > 0
            ) {

                const attachmentCountElement =
                    document.createElement(
                        "span"
                    );


                attachmentCountElement.classList.add(
                    "community-attachment-count"
                );


                attachmentCountElement.textContent =
                    `첨부 ${post.attachment_count}`;


                postTitleAreaElement.appendChild(
                    attachmentCountElement
                );

            }


            // =========================
            // 작성자
            // =========================

            const postAuthorElement =
                document.createElement(
                    "span"
                );


            postAuthorElement.classList.add(
                "community-post-author"
            );


            postAuthorElement.textContent =
                post.author_name;


            // =========================
            // 작성일
            // =========================

            const postDateElement =
                document.createElement(
                    "span"
                );


            postDateElement.classList.add(
                "community-post-date"
            );


            postDateElement.textContent =
                formatCommunityDate(
                    post.created_at
                );


            // =========================
            // ROW
            // =========================

            postRowElement.append(
                postNumberElement,
                postTitleAreaElement,
                postAuthorElement,
                postDateElement
            );


            communityPostListElement
                .appendChild(
                    postRowElement
                );

        }
    );

}


loadCommunityPosts();

// =========================================
// COMMUNITY NOTICE
// =========================================

async function initializeCommunityNoticeUi() {

    await decorateCommunityNotices();


    try {

        const {
            getCurrentUser,
            getUserToken,
            removeUserToken,
        } = await import(
            "./auth.js"
        );


        const user =
            await getCurrentUser();


        if (
            !user
            ||
            !user.is_admin
        ) {
            return;
        }


        createCommunityNoticeButton(
            getUserToken,
            removeUserToken
        );


    } catch (error) {

        console.error(
            "공지사항 UI 초기화 오류",
            error
        );

    }

}


// =========================================
// 공지 목록 표시
// =========================================

async function decorateCommunityNotices() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + "/api/community/posts"
                + "?board_type=free"
            );


        if (!response.ok) {
            return;
        }


        const posts =
            await response.json();


        const noticeIds =
            new Set(
                posts
                    .filter(
                        post =>
                            post.is_notice
                    )
                    .map(
                        post =>
                            Number(
                                post.id
                            )
                    )
            );


        if (
            noticeIds.size === 0
        ) {
            return;
        }


        // 기존 community.js의
        // 게시글 렌더링 완료를 조금 기다림
        for (
            let attempt = 0;
            attempt < 20;
            attempt += 1
        ) {

            const rows =
                document.querySelectorAll(
                    ".community-post-row"
                );


            if (
                rows.length > 0
            ) {

                rows.forEach(
                    rowElement => {

                        const href =
                            rowElement.getAttribute(
                                "href"
                            );


                        if (!href) {
                            return;
                        }


                        const url =
                            new URL(
                                href,
                                window.location.href
                            );


                        const postId =
                            Number(
                                url.searchParams.get(
                                    "id"
                                )
                                ??
                                url.searchParams.get(
                                    "post_id"
                                )
                            );


                        if (
                            !noticeIds.has(
                                postId
                            )
                        ) {
                            return;
                        }


                        rowElement
                            .classList
                            .add(
                                "community-notice-row"
                            );


                        const titleElement =
                            rowElement.querySelector(
                                ".community-post-title"
                            );


                        if (
                            !titleElement
                            ||
                            titleElement.querySelector(
                                ".community-notice-badge"
                            )
                        ) {
                            return;
                        }


                        const badgeElement =
                            document.createElement(
                                "span"
                            );


                        badgeElement.classList.add(
                            "community-notice-badge"
                        );


                        badgeElement.textContent =
                            "공지";


                        // DOM상 뒤에 붙이되
                        // CSS order로 제목 앞에 표시
                        titleElement.append(
                            badgeElement
                        );

                    }
                );


                return;

            }


            await new Promise(
                resolve => {
                    setTimeout(
                        resolve,
                        100
                    );
                }
            );

        }


    } catch (error) {

        console.error(
            "공지사항 표시 오류",
            error
        );

    }

}


// =========================================
// 관리자 공지 작성 버튼
// =========================================

function createCommunityNoticeButton(
    getUserToken,
    removeUserToken
) {

    if (
        document.querySelector(
            ".community-notice-write-button"
        )
    ) {
        return;
    }


    const headerElement =
        document.querySelector(
            ".community-header"
        );


    if (!headerElement) {
        return;
    }


    const writeButtonElement =
        headerElement.querySelector(
            ".community-write-button"
        );


    const actionsElement =
        document.createElement(
            "div"
        );


    actionsElement.classList.add(
        "community-header-actions"
    );


    const noticeButtonElement =
        document.createElement(
            "button"
        );


    noticeButtonElement.type =
        "button";


    noticeButtonElement.classList.add(
        "community-notice-write-button"
    );


    noticeButtonElement.textContent =
        "공지 작성";


    if (writeButtonElement) {

        writeButtonElement.replaceWith(
            actionsElement
        );


        actionsElement.append(
            noticeButtonElement,
            writeButtonElement
        );

    } else {

        actionsElement.append(
            noticeButtonElement
        );


        headerElement.append(
            actionsElement
        );

    }


    noticeButtonElement
        .addEventListener(
            "click",
            () => {

                openCommunityNoticeModal(
                    getUserToken,
                    removeUserToken
                );

            }
        );

}


// =========================================
// 공지 작성 모달 생성
// =========================================

function getCommunityNoticeModal() {

    let modalElement =
        document.querySelector(
            "#community-notice-modal"
        );


    if (modalElement) {
        return modalElement;
    }


    modalElement =
        document.createElement(
            "div"
        );


    modalElement.id =
        "community-notice-modal";


    modalElement.classList.add(
        "community-modal",
        "hidden"
    );


    modalElement.innerHTML = `
        <div
            class="
                community-modal-panel
                community-notice-modal-panel
            "
        >

            <div class="community-modal-header">

                <h2>
                    공지사항 작성
                </h2>

                <button
                    type="button"
                    class="community-modal-close-button"
                    data-community-notice-close
                >
                    ×
                </button>

            </div>


            <div
                class="community-notice-modal-fields"
            >

                <label>
                    <span>
                        제목
                    </span>

                    <input
                        type="text"
                        id="community-notice-title"
                        maxlength="200"
                        placeholder="공지사항 제목"
                    >
                </label>


                <label>
                    <span>
                        내용
                    </span>

                    <textarea
                        id="community-notice-content"
                        placeholder="공지사항 내용을 입력해주세요."
                    ></textarea>
                </label>

            </div>


            <p
                id="community-notice-message"
                class="community-write-message"
            ></p>


            <div class="community-modal-actions">

                <button
                    type="button"
                    class="community-modal-cancel-button"
                    data-community-notice-close
                >
                    취소
                </button>

                <button
                    type="button"
                    id="community-notice-submit"
                    class="community-notice-submit-button"
                >
                    공지 등록
                </button>

            </div>

        </div>
    `;


    document.body.append(
        modalElement
    );


    modalElement
        .querySelectorAll(
            "[data-community-notice-close]"
        )
        .forEach(
            buttonElement => {

                buttonElement
                    .addEventListener(
                        "click",
                        () => {

                            modalElement
                                .classList
                                .add(
                                    "hidden"
                                );

                        }
                    );

            }
        );


    modalElement.addEventListener(
        "click",
        event => {

            if (
                event.target
                === modalElement
            ) {

                modalElement
                    .classList
                    .add(
                        "hidden"
                    );

            }

        }
    );


    return modalElement;

}


// =========================================
// 공지 작성 모달 열기
// =========================================

function openCommunityNoticeModal(
    getUserToken,
    removeUserToken
) {

    const modalElement =
        getCommunityNoticeModal();


    const titleInputElement =
        modalElement.querySelector(
            "#community-notice-title"
        );


    const contentInputElement =
        modalElement.querySelector(
            "#community-notice-content"
        );


    const messageElement =
        modalElement.querySelector(
            "#community-notice-message"
        );


    const submitButtonElement =
        modalElement.querySelector(
            "#community-notice-submit"
        );


    titleInputElement.value =
        "";


    contentInputElement.value =
        "";


    messageElement.textContent =
        "";


    submitButtonElement.disabled =
        false;


    modalElement
        .classList
        .remove(
            "hidden"
        );


    titleInputElement.focus();


    submitButtonElement.onclick =
        async () => {

            const title =
                titleInputElement
                    .value
                    .trim();


            const content =
                contentInputElement
                    .value
                    .trim();


            if (!title) {

                messageElement.textContent =
                    "제목을 입력해주세요.";

                return;
            }


            if (!content) {

                messageElement.textContent =
                    "내용을 입력해주세요.";

                return;
            }


            const token =
                getUserToken();


            if (!token) {

                messageElement.textContent =
                    "로그인이 필요합니다.";

                return;
            }


            submitButtonElement.disabled =
                true;


            messageElement.textContent =
                "공지사항 등록 중...";


            try {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + "/api/community/admin/notices",
                        {
                            method:
                                "POST",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                Authorization:
                                    `Bearer ${token}`,
                            },

                            body:
                                JSON.stringify({
                                    title,
                                    content,
                                }),
                        }
                    );


                const responseData =
                    await response.json();


                if (
                    response.status
                    === 401
                ) {

                    removeUserToken();

                    throw new Error(
                        "로그인이 만료되었습니다."
                    );

                }


                if (!response.ok) {

                    throw new Error(
                        responseData.detail
                        ??
                        "공지사항 등록에 실패했습니다."
                    );

                }


                window.location.reload();


            } catch (error) {

                console.error(
                    error
                );


                messageElement.textContent =
                    error.message;


                submitButtonElement.disabled =
                    false;

            }

        };

}


// =========================================
// 공지 UI 실행
// =========================================

if (
    document.readyState
    === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeCommunityNoticeUi
    );

} else {

    initializeCommunityNoticeUi();

}