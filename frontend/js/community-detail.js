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