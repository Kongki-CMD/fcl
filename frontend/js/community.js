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