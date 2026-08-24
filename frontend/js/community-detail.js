import {
    apiBaseUrl,
} from "./config.js";


const communityDetailElement =
    document.querySelector(
        "#community-detail"
    );

const communityEditButtonElement =
    document.querySelector(
        "#community-edit-button"
    );

const communityDeleteButtonElement =
    document.querySelector(
        "#community-delete-button"
    );


const communityEditModalElement =
    document.querySelector(
        "#community-edit-modal"
    );

const communityEditCloseButtonElement =
    document.querySelector(
        "#community-edit-close-button"
    );

const communityEditCancelButtonElement =
    document.querySelector(
        "#community-edit-cancel-button"
    );

const communityEditSubmitButtonElement =
    document.querySelector(
        "#community-edit-submit-button"
    );

const communityEditTitleInputElement =
    document.querySelector(
        "#community-edit-title"
    );

const communityEditAuthorInputElement =
    document.querySelector(
        "#community-edit-author"
    );

const communityEditContentInputElement =
    document.querySelector(
        "#community-edit-content"
    );

const communityEditPasswordInputElement =
    document.querySelector(
        "#community-edit-password"
    );

const communityEditMessageElement =
    document.querySelector(
        "#community-edit-message"
    );


const communityDeleteModalElement =
    document.querySelector(
        "#community-delete-modal"
    );

const communityDeleteCloseButtonElement =
    document.querySelector(
        "#community-delete-close-button"
    );

const communityDeleteCancelButtonElement =
    document.querySelector(
        "#community-delete-cancel-button"
    );

const communityDeleteSubmitButtonElement =
    document.querySelector(
        "#community-delete-submit-button"
    );

const communityDeletePasswordInputElement =
    document.querySelector(
        "#community-delete-password"
    );

const communityDeleteMessageElement =
    document.querySelector(
        "#community-delete-message"
    );


let currentCommunityPost =
    null;

let currentCommunityPostId =
    null;


function formatCommunityDetailDate(
    dateValue
) {

    if (!dateValue) {
        return "-";
    }


    const date =
        new Date(
            dateValue
        );


    return date.toLocaleString(
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

            hour:
                "2-digit",

            minute:
                "2-digit",
        }
    );

}


function renderCommunityDetail(
    post
) {

    currentCommunityPost =
        post;

    communityDetailElement
        .innerHTML = "";


    const headerElement =
        document.createElement(
            "div"
        );

    headerElement.classList.add(
        "community-detail-header"
    );


    const titleElement =
        document.createElement(
            "h1"
        );

    titleElement.classList.add(
        "community-detail-title"
    );

    titleElement.textContent =
        post.title;


    const metaElement =
        document.createElement(
            "div"
        );

    metaElement.classList.add(
        "community-detail-meta"
    );


    const authorElement =
        document.createElement(
            "span"
        );

    authorElement.textContent =
        `작성자 ${post.author_name}`;


    const dateElement =
        document.createElement(
            "span"
        );

    dateElement.textContent =
        formatCommunityDetailDate(
            post.created_at
        );


    metaElement.append(
        authorElement,
        dateElement
    );


    headerElement.append(
        titleElement,
        metaElement
    );


    const contentElement =
        document.createElement(
            "div"
        );

    contentElement.classList.add(
        "community-detail-content"
    );

    contentElement.textContent =
        post.content;


    communityDetailElement.append(
        headerElement,
        contentElement
    );


    if (
        Array.isArray(
            post.attachments
        )
        &&
        post.attachments.length > 0
    ) {

        const attachmentListElement =
            document.createElement(
                "div"
            );

        attachmentListElement.classList.add(
            "community-detail-attachments"
        );


        post.attachments.forEach(
            (attachment) => {

                const imageElement =
                    document.createElement(
                        "img"
                    );


                imageElement.src =
                    `${apiBaseUrl}${attachment.image_url}`;

                imageElement.alt =
                    attachment.original_file_name;

                imageElement.loading =
                    "lazy";

                imageElement.classList.add(
                    "community-detail-image"
                );


                attachmentListElement.appendChild(
                    imageElement
                );

            }
        );


        communityDetailElement.appendChild(
            attachmentListElement
        );

    }

}

// =========================================
// 수정 팝업
// =========================================

function openCommunityEditModal() {

    if (!currentCommunityPost) {
        return;
    }


    communityEditTitleInputElement.value =
        currentCommunityPost.title;

    communityEditAuthorInputElement.value =
        currentCommunityPost.author_name;

    communityEditContentInputElement.value =
        currentCommunityPost.content;

    communityEditPasswordInputElement.value =
        "";

    communityEditMessageElement.textContent =
        "";


    communityEditModalElement.classList.remove(
        "hidden"
    );

}


function closeCommunityEditModal() {

    communityEditModalElement.classList.add(
        "hidden"
    );

}


communityEditButtonElement.addEventListener(
    "click",
    openCommunityEditModal
);


communityEditCloseButtonElement.addEventListener(
    "click",
    closeCommunityEditModal
);


communityEditCancelButtonElement.addEventListener(
    "click",
    closeCommunityEditModal
);


communityEditSubmitButtonElement.addEventListener(
    "click",
    async () => {

        const title =
            communityEditTitleInputElement
                .value
                .trim();

        const authorName =
            communityEditAuthorInputElement
                .value
                .trim();

        const content =
            communityEditContentInputElement
                .value
                .trim();

        const password =
            communityEditPasswordInputElement
                .value
                .trim();


        if (
            !title
            || !authorName
            || !content
            || !password
        ) {

            communityEditMessageElement
                .textContent =
                    "모든 항목을 입력해주세요.";

            return;

        }


        communityEditMessageElement
            .textContent =
                "수정하는 중...";


        try {

            const response =
                await fetch(
                    `${apiBaseUrl}/api/community/posts/${currentCommunityPostId}`,
                    {
                        method:
                            "PATCH",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    title:
                                        title,

                                    author_name:
                                        authorName,

                                    content:
                                        content,

                                    password:
                                        password,
                                }
                            ),
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail
                    ?? "게시글 수정에 실패했습니다."
                );

            }


            closeCommunityEditModal();


            await loadCommunityDetail();

        } catch (error) {

            communityEditMessageElement
                .textContent =
                    error.message;

        }

    }
);


async function loadCommunityDetail() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const postId =
        searchParams.get(
            "id"
        );

    currentCommunityPostId =
        postId;


    if (!postId) {

        communityDetailElement
            .innerHTML = `
                <p class="community-empty">
                    게시글 번호가 없습니다.
                </p>
            `;

        return;

    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/community/posts/${postId}`
            );


        if (!response.ok) {

            if (
                response.status === 404
            ) {

                throw new Error(
                    "게시글을 찾을 수 없습니다."
                );

            }


            throw new Error(
                "게시글을 불러오지 못했습니다."
            );

        }


        const post =
            await response.json();


        renderCommunityDetail(
            post
        );

    } catch (error) {

        console.error(
            error
        );


        communityDetailElement
            .innerHTML = "";


        const errorElement =
            document.createElement(
                "p"
            );

        errorElement.classList.add(
            "community-empty"
        );

        errorElement.textContent =
            error.message;


        communityDetailElement.appendChild(
            errorElement
        );

    }

}

// =========================================
// 삭제 팝업
// =========================================

function openCommunityDeleteModal() {

    communityDeletePasswordInputElement
        .value = "";

    communityDeleteMessageElement
        .textContent = "";


    communityDeleteModalElement.classList.remove(
        "hidden"
    );

}


function closeCommunityDeleteModal() {

    communityDeleteModalElement.classList.add(
        "hidden"
    );

}


communityDeleteButtonElement.addEventListener(
    "click",
    openCommunityDeleteModal
);


communityDeleteCloseButtonElement.addEventListener(
    "click",
    closeCommunityDeleteModal
);


communityDeleteCancelButtonElement.addEventListener(
    "click",
    closeCommunityDeleteModal
);


communityDeleteSubmitButtonElement.addEventListener(
    "click",
    async () => {

        const password =
            communityDeletePasswordInputElement
                .value
                .trim();


        if (!password) {

            communityDeleteMessageElement
                .textContent =
                    "비밀번호를 입력해주세요.";

            return;

        }


        communityDeleteMessageElement
            .textContent =
                "삭제하는 중...";


        try {

            const response =
                await fetch(
                    `${apiBaseUrl}/api/community/posts/${currentCommunityPostId}`,
                    {
                        method:
                            "DELETE",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    password:
                                        password,
                                }
                            ),
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail
                    ?? "게시글 삭제에 실패했습니다."
                );

            }


            window.location.href =
                "./community.html";

        } catch (error) {

            communityDeleteMessageElement
                .textContent =
                    error.message;

        }

    }
);

loadCommunityDetail();

// =========================================
// COMMUNITY ADMIN CONTROLS
// =========================================

async function initializeCommunityAdminControls() {

    try {

        const {
            getCurrentUser,
            getUserToken,
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


        const manageActionsElement =
            document.querySelector(
                ".community-detail-manage-actions"
            );


        if (!manageActionsElement) {
            return;
        }


        if (
            manageActionsElement.querySelector(
                ".community-admin-edit-button"
            )
        ) {

            return;
        }


        const editButtonElement =
            document.createElement(
                "button"
            );


        editButtonElement.type =
            "button";


        editButtonElement.classList.add(
            "community-admin-edit-button"
        );


        editButtonElement.textContent =
            "관리자 수정";


        const deleteButtonElement =
            document.createElement(
                "button"
            );


        deleteButtonElement.type =
            "button";


        deleteButtonElement.classList.add(
            "community-admin-delete-button"
        );


        deleteButtonElement.textContent =
            "관리자 삭제";


        manageActionsElement.append(
            editButtonElement,
            deleteButtonElement
        );


        editButtonElement
            .addEventListener(
                "click",
                () => {

                    openCommunityAdminEdit(
                        getUserToken
                    );

                }
            );


        deleteButtonElement
            .addEventListener(
                "click",
                () => {

                    deleteCommunityPostByAdmin(
                        getUserToken
                    );

                }
            );


    } catch (error) {

        console.error(
            "관리자 게시글 기능 초기화 오류",
            error
        );

    }

}


// =========================================
// 게시글 ID
// =========================================

function getCommunityAdminPostId() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const value =
        searchParams.get(
            "id"
        )
        ??
        searchParams.get(
            "post_id"
        );


    const postId =
        Number(
            value
        );


    if (
        !Number.isInteger(
            postId
        )
        ||
        postId <= 0
    ) {

        return null;
    }


    return postId;

}


// =========================================
// 관리자 수정 팝업 생성
// =========================================

function getCommunityAdminEditModal() {

    let modalElement =
        document.querySelector(
            "#community-admin-edit-modal"
        );


    if (modalElement) {

        return modalElement;

    }


    modalElement =
        document.createElement(
            "div"
        );


    modalElement.id =
        "community-admin-edit-modal";


    modalElement.classList.add(
        "community-modal",
        "hidden"
    );


    modalElement.innerHTML = `
        <div
            class="
                community-modal-panel
                community-admin-edit-panel
            "
        >

            <div class="community-modal-header">

                <h2>
                    관리자 게시글 수정
                </h2>

                <button
                    type="button"
                    class="community-modal-close-button"
                    data-community-admin-edit-close
                >
                    ×
                </button>

            </div>


            <div class="community-admin-edit-fields">

                <label>

                    제목

                    <input
                        type="text"
                        id="community-admin-edit-title"
                        maxlength="200"
                    >

                </label>


                <label>

                    내용

                    <textarea
                        id="community-admin-edit-content"
                    ></textarea>

                </label>

            </div>


            <p
                id="community-admin-edit-message"
                class="community-modal-message"
            ></p>


            <div class="community-modal-actions">

                <button
                    type="button"
                    class="community-modal-cancel-button"
                    data-community-admin-edit-close
                >
                    취소
                </button>

                <button
                    type="button"
                    id="community-admin-edit-submit"
                    class="community-modal-submit-button"
                >
                    수정 저장
                </button>

            </div>

        </div>
    `;


    document.body.append(
        modalElement
    );


    modalElement
        .querySelectorAll(
            "[data-community-admin-edit-close]"
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


    modalElement
        .addEventListener(
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
// 관리자 수정 열기
// =========================================

async function openCommunityAdminEdit(
    getUserToken
) {

    const postId =
        getCommunityAdminPostId();


    if (!postId) {

        alert(
            "게시글 ID를 찾을 수 없습니다."
        );

        return;
    }


    const modalElement =
        getCommunityAdminEditModal();


    const titleInputElement =
        modalElement.querySelector(
            "#community-admin-edit-title"
        );


    const contentInputElement =
        modalElement.querySelector(
            "#community-admin-edit-content"
        );


    const messageElement =
        modalElement.querySelector(
            "#community-admin-edit-message"
        );


    const submitButtonElement =
        modalElement.querySelector(
            "#community-admin-edit-submit"
        );


    messageElement.textContent =
        "게시글 정보를 불러오는 중...";


    modalElement
        .classList
        .remove(
            "hidden"
        );


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/community/posts/${postId}`
            );


        const post =
            await response.json();


        if (!response.ok) {

            throw new Error(
                post.detail
                ??
                "게시글을 불러오지 못했습니다."
            );

        }


        titleInputElement.value =
            post.title
            ?? "";


        contentInputElement.value =
            post.content
            ?? "";


        messageElement.textContent =
            "";


    } catch (error) {

        console.error(
            error
        );


        messageElement.textContent =
            error.message;


        return;
    }


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
                "수정 중...";


            try {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + `/api/community/admin/posts/${postId}`,
                        {
                            method:
                                "PATCH",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                Authorization:
                                    `Bearer ${token}`,
                            },

                            body:
                                JSON.stringify({
                                    title:
                                        title,

                                    content:
                                        content,
                                }),
                        }
                    );


                const responseData =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        responseData.detail
                        ??
                        "게시글 수정에 실패했습니다."
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
// 관리자 게시글 삭제
// =========================================

async function deleteCommunityPostByAdmin(
    getUserToken
) {

    const postId =
        getCommunityAdminPostId();


    if (!postId) {

        alert(
            "게시글 ID를 찾을 수 없습니다."
        );

        return;
    }


    const confirmed =
        window.confirm(
            "관리자 권한으로 이 게시글을 "
            + "삭제하시겠습니까?\n\n"
            + "삭제 후 복구할 수 없습니다."
        );


    if (!confirmed) {
        return;
    }


    const token =
        getUserToken();


    if (!token) {

        alert(
            "로그인이 필요합니다."
        );

        return;
    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/community/admin/posts/${postId}`,
                {
                    method:
                        "DELETE",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        const responseData =
            await response.json();


        if (!response.ok) {

            throw new Error(
                responseData.detail
                ??
                "게시글 삭제에 실패했습니다."
            );

        }


        window.location.href =
            "./community.html";


    } catch (error) {

        console.error(
            error
        );


        alert(
            error.message
        );

    }

}


// =========================================
// 실행
// =========================================

if (
    document.readyState
    === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeCommunityAdminControls
    );

} else {

    initializeCommunityAdminControls();

}

// =========================================
// COMMUNITY NOTICE DETAIL
// =========================================

async function initializeCommunityNoticeDetail() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const postId =
        Number(
            searchParams.get("id")
            ??
            searchParams.get("post_id")
        );


    if (
        !Number.isInteger(postId)
        ||
        postId <= 0
    ) {
        return;
    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/community/posts/${postId}`
            );


        if (!response.ok) {
            return;
        }


        const post =
            await response.json();


        if (!post.is_notice) {
            return;
        }


        // =============================
        // 공지 상세 카드 표시
        // =============================

        const detailElement =
            document.querySelector(
                ".community-detail"
            );


        if (detailElement) {

            detailElement.classList.add(
                "community-notice-detail"
            );

        }


        // =============================
        // 제목 앞 [공지] 표시
        // =============================

        const titleElement =
            document.querySelector(
                ".community-detail-title"
            );


        if (
            titleElement
            &&
            !titleElement.querySelector(
                ".community-detail-notice-badge"
            )
        ) {

            const badgeElement =
                document.createElement(
                    "span"
                );


            badgeElement.classList.add(
                "community-detail-notice-badge"
            );


            badgeElement.textContent =
                "공지";


            titleElement.prepend(
                badgeElement
            );

        }


        // =============================
        // 일반 비밀번호 수정 / 삭제 숨김
        // =============================

        const editButtonElement =
            document.querySelector(
                ".community-edit-button"
            );


        const deleteButtonElement =
            document.querySelector(
                ".community-delete-button"
            );


        if (editButtonElement) {

            editButtonElement.hidden =
                true;

        }


        if (deleteButtonElement) {

            deleteButtonElement.hidden =
                true;

        }


    } catch (error) {

        console.error(
            "공지 상세페이지 처리 오류",
            error
        );

    }

}


// =========================================
// 실행
// =========================================

if (
    document.readyState
    === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeCommunityNoticeDetail
    );

} else {

    initializeCommunityNoticeDetail();

}

// =========================================
// COMMUNITY COMMENTS
// 댓글 조회 / 작성 UI
// =========================================

let communityCommentCurrentUser =
    null;

let communityCommentGetUserToken =
    null;

let communityCommentRemoveUserToken =
    null;

async function initializeCommunityComments() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const postId =
        Number(
            searchParams.get("id")
            ??
            searchParams.get("post_id")
        );


    if (
        !Number.isInteger(postId)
        ||
        postId <= 0
    ) {
        return;
    }


    const detailPageElement =
        document.querySelector(
            ".community-detail-page"
        );


    if (!detailPageElement) {
        return;
    }


    if (
        document.querySelector(
            ".community-comments-section"
        )
    ) {
        return;
    }


    // =========================================
    // 댓글 영역 생성
    // =========================================

    const commentsSectionElement =
        document.createElement(
            "section"
        );


    commentsSectionElement.classList.add(
        "community-comments-section"
    );


    const headerElement =
        document.createElement(
            "div"
        );


    headerElement.classList.add(
        "community-comments-header"
    );


    const titleElement =
        document.createElement(
            "h2"
        );


    titleElement.textContent =
        "댓글";


    const countElement =
        document.createElement(
            "span"
        );


    countElement.classList.add(
        "community-comments-count"
    );


    countElement.textContent =
        "0";


    headerElement.append(
        titleElement,
        countElement
    );


    // =========================================
    // 댓글 작성 영역
    // =========================================

    const writeAreaElement =
        document.createElement(
            "div"
        );


    writeAreaElement.classList.add(
        "community-comment-write-area"
    );


    // =========================================
    // 댓글 목록 영역
    // =========================================

    const listElement =
        document.createElement(
            "div"
        );


    listElement.classList.add(
        "community-comment-list"
    );


    listElement.textContent =
        "댓글을 불러오는 중...";


    commentsSectionElement.append(
        headerElement,
        writeAreaElement,
        listElement
    );


    // =========================================
    // 상세페이지에 삽입
    // =========================================

    const actionsElement =
        document.querySelector(
            ".community-detail-actions"
        );


    if (actionsElement) {

        actionsElement.insertAdjacentElement(
            "beforebegin",
            commentsSectionElement
        );

    } else {

        detailPageElement.appendChild(
            commentsSectionElement
        );

    }


    // =========================================
    // 로그인 정보
    // =========================================

    let currentUser = null;
    let getUserToken = null;
    let removeUserToken = null;


    try {

        const authModule =
            await import(
                "./auth.js"
            );


        getUserToken =
            authModule.getUserToken;


        removeUserToken =
            authModule.removeUserToken;


        currentUser =
            await authModule
                .getCurrentUser();


    } catch (error) {

        console.error(
            "댓글 로그인 정보 확인 오류",
            error
        );

    }

    communityCommentCurrentUser =
        currentUser;

    communityCommentGetUserToken =
        getUserToken;

    communityCommentRemoveUserToken =
        removeUserToken;


    // =========================================
    // 댓글 작성 UI
    // =========================================

    if (currentUser) {

        const writerElement =
            document.createElement(
                "div"
            );


        writerElement.classList.add(
            "community-comment-writer"
        );


        const nicknameElement =
            document.createElement(
                "strong"
            );


        nicknameElement.textContent =
            currentUser.nickname;


        const textareaElement =
            document.createElement(
                "textarea"
            );


        textareaElement.classList.add(
            "community-comment-textarea"
        );


        textareaElement.placeholder =
            "댓글을 입력해주세요.";


        textareaElement.maxLength =
            1000;


        const bottomElement =
            document.createElement(
                "div"
            );


        bottomElement.classList.add(
            "community-comment-write-bottom"
        );


        const lengthElement =
            document.createElement(
                "span"
            );


        lengthElement.classList.add(
            "community-comment-length"
        );


        lengthElement.textContent =
            "0 / 1000";


        const submitButtonElement =
            document.createElement(
                "button"
            );


        submitButtonElement.type =
            "button";


        submitButtonElement.classList.add(
            "community-comment-submit-button"
        );


        submitButtonElement.textContent =
            "등록";


        bottomElement.append(
            lengthElement,
            submitButtonElement
        );


        writerElement.append(
            nicknameElement,
            textareaElement,
            bottomElement
        );


        writeAreaElement.appendChild(
            writerElement
        );


        textareaElement.addEventListener(
            "input",
            () => {

                lengthElement.textContent =
                    `${textareaElement.value.length}`
                    + " / 1000";

            }
        );


        submitButtonElement.addEventListener(
            "click",
            async () => {

                const content =
                    textareaElement.value
                        .trim();


                if (!content) {

                    alert(
                        "댓글 내용을 입력해주세요."
                    );

                    textareaElement.focus();

                    return;
                }


                const token =
                    getUserToken
                        ? getUserToken()
                        : null;


                if (!token) {

                    alert(
                        "로그인이 필요합니다."
                    );

                    return;
                }


                submitButtonElement.disabled =
                    true;


                submitButtonElement.textContent =
                    "등록 중...";


                try {

                    const response =
                        await fetch(
                            `${apiBaseUrl}`
                            + `/api/community/posts/${postId}/comments`,
                            {
                                method:
                                    "POST",

                                headers: {
                                    "Content-Type":
                                        "application/json",

                                    "Authorization":
                                        `Bearer ${token}`,
                                },

                                body:
                                    JSON.stringify(
                                        {
                                            content:
                                                content,
                                        }
                                    ),
                            }
                        );


                    const data =
                        await response.json();


                    if (
                        response.status
                        === 401
                    ) {

                        if (
                            removeUserToken
                        ) {

                            removeUserToken();

                        }


                        alert(
                            "로그인이 만료되었습니다."
                        );


                        window.location.reload();

                        return;
                    }


                    if (!response.ok) {

                        throw new Error(
                            data.detail
                            ??
                            "댓글 등록에 실패했습니다."
                        );

                    }


                    textareaElement.value =
                        "";


                    lengthElement.textContent =
                        "0 / 1000";


                    await loadCommunityComments(
                        postId,
                        listElement,
                        countElement
                    );


                } catch (error) {

                    console.error(
                        "댓글 등록 오류",
                        error
                    );


                    alert(
                        error.message
                    );


                } finally {

                    submitButtonElement.disabled =
                        false;


                    submitButtonElement.textContent =
                        "등록";

                }

            }
        );


    } else {

        const loginMessageElement =
            document.createElement(
                "div"
            );


        loginMessageElement.classList.add(
            "community-comment-login-message"
        );


        loginMessageElement.textContent =
            "로그인 후 댓글을 작성할 수 있습니다.";


        writeAreaElement.appendChild(
            loginMessageElement
        );

    }


    // =========================================
    // 최초 댓글 조회
    // =========================================

    await loadCommunityComments(
        postId,
        listElement,
        countElement
    );

}


// =========================================
// 댓글 목록 조회
// =========================================

async function loadCommunityComments(
    postId,
    listElement,
    countElement
) {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/community/posts/${postId}/comments`
            );


        const comments =
            await response.json();


        if (!response.ok) {

            throw new Error(
                comments.detail
                ??
                "댓글을 불러오지 못했습니다."
            );

        }


        countElement.textContent =
            String(
                comments.length
            );


        listElement.innerHTML =
            "";


        if (
            comments.length
            === 0
        ) {

            const emptyElement =
                document.createElement(
                    "div"
                );


            emptyElement.classList.add(
                "community-comment-empty"
            );


            emptyElement.textContent =
                "등록된 댓글이 없습니다.";


            listElement.appendChild(
                emptyElement
            );


            return;
        }


        comments.forEach(
            (comment) => {

                const commentElement =
                    createCommunityCommentElement(
                        comment
                    );


                listElement.appendChild(
                    commentElement
                );

            }
        );


    } catch (error) {

        console.error(
            "댓글 조회 오류",
            error
        );


        listElement.textContent =
            error.message;

    }

}


// =========================================
// 댓글 한 개 출력
// =========================================

function createCommunityCommentElement(
    comment
) {

    const commentElement =
        document.createElement(
            "article"
        );


    commentElement.classList.add(
        "community-comment"
    );


    commentElement.dataset.commentId =
        String(
            comment.id
        );


    const isOwner =
        (
            communityCommentCurrentUser
            &&
            Number(
                communityCommentCurrentUser.id
            )
            ===
            Number(
                comment.user_id
            )
        );


    const isAdmin =
        Boolean(
            communityCommentCurrentUser
                ?.is_admin
        );


    // =========================================
    // 상단
    // =========================================

    const topElement =
        document.createElement(
            "div"
        );


    topElement.classList.add(
        "community-comment-top"
    );


    const authorElement =
        document.createElement(
            "div"
        );


    authorElement.classList.add(
        "community-comment-author"
    );


    const nicknameElement =
        document.createElement(
            "strong"
        );


    nicknameElement.textContent =
        comment.author_nickname;


    authorElement.appendChild(
        nicknameElement
    );


    if (
        comment.author_is_admin
    ) {

        const adminBadgeElement =
            document.createElement(
                "span"
            );


        adminBadgeElement.classList.add(
            "community-comment-admin-badge"
        );


        adminBadgeElement.textContent =
            "관리자";


        authorElement.appendChild(
            adminBadgeElement
        );

    }


    // =========================================
    // 날짜 + 버튼
    // =========================================

    const topRightElement =
        document.createElement(
            "div"
        );


    topRightElement.classList.add(
        "community-comment-top-right"
    );


    const dateElement =
        document.createElement(
            "time"
        );


    dateElement.classList.add(
        "community-comment-date"
    );


    dateElement.textContent =
        formatCommunityCommentDate(
            comment.created_at
        );


    topRightElement.appendChild(
        dateElement
    );


    if (
        isOwner
        ||
        isAdmin
    ) {

        const actionsElement =
            document.createElement(
                "div"
            );


        actionsElement.classList.add(
            "community-comment-actions"
        );


        // 작성자 본인만 수정
        if (isOwner) {

            const editButtonElement =
                document.createElement(
                    "button"
                );


            editButtonElement.type =
                "button";


            editButtonElement.classList.add(
                "community-comment-edit-button"
            );


            editButtonElement.textContent =
                "수정";


            editButtonElement.addEventListener(
                "click",
                () => {

                    openCommunityCommentEdit(
                        commentElement,
                        comment
                    );

                }
            );


            actionsElement.appendChild(
                editButtonElement
            );

        }


        // 작성자 또는 관리자 삭제
        const deleteButtonElement =
            document.createElement(
                "button"
            );


        deleteButtonElement.type =
            "button";


        deleteButtonElement.classList.add(
            "community-comment-delete-button"
        );


        deleteButtonElement.textContent =
            (
                isAdmin
                &&
                !isOwner
            )
                ? "관리자 삭제"
                : "삭제";


        deleteButtonElement.addEventListener(
            "click",
            async () => {

                await deleteCommunityComment(
                    comment
                );

            }
        );


        actionsElement.appendChild(
            deleteButtonElement
        );


        topRightElement.appendChild(
            actionsElement
        );

    }


    topElement.append(
        authorElement,
        topRightElement
    );


    // =========================================
    // 내용
    // =========================================

    const contentElement =
        document.createElement(
            "div"
        );


    contentElement.classList.add(
        "community-comment-content"
    );


    contentElement.textContent =
        comment.content;


    commentElement.append(
        topElement,
        contentElement
    );


    return commentElement;

}

// =========================================
// 댓글 수정창
// =========================================

function openCommunityCommentEdit(
    commentElement,
    comment
) {

    if (
        commentElement.querySelector(
            ".community-comment-edit-area"
        )
    ) {
        return;
    }


    const contentElement =
        commentElement.querySelector(
            ".community-comment-content"
        );


    if (!contentElement) {
        return;
    }


    contentElement.hidden =
        true;


    const editAreaElement =
        document.createElement(
            "div"
        );


    editAreaElement.classList.add(
        "community-comment-edit-area"
    );


    const textareaElement =
        document.createElement(
            "textarea"
        );


    textareaElement.classList.add(
        "community-comment-edit-textarea"
    );


    textareaElement.maxLength =
        1000;


    textareaElement.value =
        comment.content;


    const actionElement =
        document.createElement(
            "div"
        );


    actionElement.classList.add(
        "community-comment-edit-actions"
    );


    const cancelButtonElement =
        document.createElement(
            "button"
        );


    cancelButtonElement.type =
        "button";


    cancelButtonElement.textContent =
        "취소";


    cancelButtonElement.classList.add(
        "community-comment-edit-cancel"
    );


    const saveButtonElement =
        document.createElement(
            "button"
        );


    saveButtonElement.type =
        "button";


    saveButtonElement.textContent =
        "저장";


    saveButtonElement.classList.add(
        "community-comment-edit-save"
    );


    actionElement.append(
        cancelButtonElement,
        saveButtonElement
    );


    editAreaElement.append(
        textareaElement,
        actionElement
    );


    contentElement.insertAdjacentElement(
        "afterend",
        editAreaElement
    );


    textareaElement.focus();


    cancelButtonElement.addEventListener(
        "click",
        () => {

            editAreaElement.remove();

            contentElement.hidden =
                false;

        }
    );


    saveButtonElement.addEventListener(
        "click",
        async () => {

            const content =
                textareaElement.value
                    .trim();


            if (!content) {

                alert(
                    "댓글 내용을 입력해주세요."
                );

                return;
            }


            const token =
                communityCommentGetUserToken
                    ? communityCommentGetUserToken()
                    : null;


            if (!token) {

                alert(
                    "로그인이 필요합니다."
                );

                return;
            }


            saveButtonElement.disabled =
                true;


            try {

                const response =
                    await fetch(
                        `${apiBaseUrl}`
                        + `/api/community/comments/${comment.id}`,
                        {
                            method:
                                "PATCH",

                            headers: {
                                "Content-Type":
                                    "application/json",

                                "Authorization":
                                    `Bearer ${token}`,
                            },

                            body:
                                JSON.stringify(
                                    {
                                        content:
                                            content,
                                    }
                                ),
                        }
                    );


                const data =
                    await response.json();


                if (
                    response.status
                    === 401
                ) {

                    if (
                        communityCommentRemoveUserToken
                    ) {

                        communityCommentRemoveUserToken();

                    }


                    alert(
                        "로그인이 만료되었습니다."
                    );


                    window.location.reload();

                    return;
                }


                if (!response.ok) {

                    throw new Error(
                        data.detail
                        ??
                        "댓글 수정에 실패했습니다."
                    );

                }


                await reloadCommunityComments();


            } catch (error) {

                console.error(
                    "댓글 수정 오류",
                    error
                );


                alert(
                    error.message
                );


            } finally {

                saveButtonElement.disabled =
                    false;

            }

        }
    );

}


// =========================================
// 댓글 삭제
// =========================================

async function deleteCommunityComment(
    comment
) {

    const isConfirmed =
        confirm(
            "댓글을 삭제하시겠습니까?"
        );


    if (!isConfirmed) {
        return;
    }


    const token =
        communityCommentGetUserToken
            ? communityCommentGetUserToken()
            : null;


    if (!token) {

        alert(
            "로그인이 필요합니다."
        );

        return;
    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + `/api/community/comments/${comment.id}`,
                {
                    method:
                        "DELETE",

                    headers: {
                        "Authorization":
                            `Bearer ${token}`,
                    },
                }
            );


        let data = {};


        try {

            data =
                await response.json();

        } catch {
            // 응답 본문 없음
        }


        if (
            response.status
            === 401
        ) {

            if (
                communityCommentRemoveUserToken
            ) {

                communityCommentRemoveUserToken();

            }


            alert(
                "로그인이 만료되었습니다."
            );


            window.location.reload();

            return;
        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ??
                "댓글 삭제에 실패했습니다."
            );

        }


        await reloadCommunityComments();


    } catch (error) {

        console.error(
            "댓글 삭제 오류",
            error
        );


        alert(
            error.message
        );

    }

}


// =========================================
// 댓글 목록 새로고침
// =========================================

async function reloadCommunityComments() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const postId =
        Number(
            searchParams.get("id")
            ??
            searchParams.get("post_id")
        );


    const listElement =
        document.querySelector(
            ".community-comment-list"
        );


    const countElement =
        document.querySelector(
            ".community-comments-count"
        );


    if (
        !Number.isInteger(postId)
        ||
        postId <= 0
        ||
        !listElement
        ||
        !countElement
    ) {
        return;
    }


    await loadCommunityComments(
        postId,
        listElement,
        countElement
    );

}

// =========================================
// 댓글 날짜 표시
// =========================================

function formatCommunityCommentDate(
    dateText
) {

    const date =
        new Date(
            dateText
        );


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "";
    }


    return new Intl.DateTimeFormat(
        "ko-KR",
        {
            year:
                "numeric",

            month:
                "2-digit",

            day:
                "2-digit",

            hour:
                "2-digit",

            minute:
                "2-digit",
        }
    ).format(
        date
    );

}


// =========================================
// 댓글 UI 실행
// =========================================

if (
    document.readyState
    === "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeCommunityComments
    );

} else {

    initializeCommunityComments();

}