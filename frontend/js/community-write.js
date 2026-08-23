import {
    apiBaseUrl,
} from "./config.js";


const communityWriteFormElement =
    document.querySelector(
        "#community-write-form"
    );

const communityTitleInputElement =
    document.querySelector(
        "#community-title"
    );

const communityAuthorInputElement =
    document.querySelector(
        "#community-author"
    );

const communityPasswordInputElement =
    document.querySelector(
        "#community-password"
    );

const communityContentInputElement =
    document.querySelector(
        "#community-content"
    );

const communityImagesInputElement =
    document.querySelector(
        "#community-images"
    );

const communityImageListElement =
    document.querySelector(
        "#community-image-list"
    );

const communityWriteMessageElement =
    document.querySelector(
        "#community-write-message"
    );


communityImagesInputElement.addEventListener(
    "change",
    () => {

        const files =
            Array.from(
                communityImagesInputElement.files
            );


        communityImageListElement
            .innerHTML = "";


        if (
            files.length > 5
        ) {

            communityWriteMessageElement
                .textContent =
                    "이미지는 최대 5장까지 첨부할 수 있습니다.";

            communityImagesInputElement
                .value = "";

            return;

        }


        communityWriteMessageElement
            .textContent = "";


        files.forEach(
            (file) => {

                const fileElement =
                    document.createElement(
                        "div"
                    );


                fileElement.classList.add(
                    "community-image-item"
                );


                fileElement.textContent =
                    file.name;


                communityImageListElement
                    .appendChild(
                        fileElement
                    );

            }
        );

    }
);


communityWriteFormElement.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const title =
            communityTitleInputElement
                .value
                .trim();

        const authorName =
            communityAuthorInputElement
                .value
                .trim();

        const password =
            communityPasswordInputElement
                .value
                .trim();

        const content =
            communityContentInputElement
                .value
                .trim();

        const files =
            Array.from(
                communityImagesInputElement.files
            );


        if (
            !title
            || !authorName
            || !password
            || !content
        ) {

            communityWriteMessageElement
                .textContent =
                    "제목, 작성자 닉네임, 비밀번호, 내용을 모두 입력해주세요.";

            return;

        }


        if (
            files.length > 5
        ) {

            communityWriteMessageElement
                .textContent =
                    "이미지는 최대 5장까지 첨부할 수 있습니다.";

            return;

        }


        communityWriteMessageElement
            .textContent =
                "게시글을 등록하는 중...";


        try {

            const postResponse =
                await fetch(
                    `${apiBaseUrl}/api/community/posts`,
                    {
                        method:
                            "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body:
                            JSON.stringify(
                                {
                                    board_type:
                                        "free",

                                    title:
                                        title,

                                    content:
                                        content,

                                    author_name:
                                        authorName,

                                    password:
                                        password,
                                }
                            ),
                    }
                );


            const postData =
                await postResponse.json();


            if (
                !postResponse.ok
            ) {

                throw new Error(
                    postData.detail
                    ?? "게시글 등록에 실패했습니다."
                );

            }


            if (
                files.length > 0
            ) {

                const formData =
                    new FormData();


                files.forEach(
                    (file) => {

                        formData.append(
                            "files",
                            file
                        );

                    }
                );


                const attachmentResponse =
                    await fetch(
                        `${apiBaseUrl}/api/community/posts/${postData.id}/attachments`,
                        {
                            method:
                                "POST",

                            body:
                                formData,
                        }
                    );


                const attachmentData =
                    await attachmentResponse.json();


                if (
                    !attachmentResponse.ok
                ) {

                    throw new Error(
                        attachmentData.detail
                        ?? "이미지 업로드에 실패했습니다."
                    );

                }

            }


            window.location.href =
                "./community.html";

        } catch (error) {

            console.error(
                error
            );


            communityWriteMessageElement
                .textContent =
                    error.message;

        }

    }
);