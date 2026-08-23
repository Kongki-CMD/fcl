import {
    apiBaseUrl,
} from "./config.js";


const photoRequestWriteFormElement =
    document.querySelector(
        "#photo-request-write-form"
    );

const photoRequestPlayerNameInputElement =
    document.querySelector(
        "#photo-request-player-name"
    );

const photoRequestSeasonNameInputElement =
    document.querySelector(
        "#photo-request-season-name"
    );

const photoRequestSpIdInputElement =
    document.querySelector(
        "#photo-request-sp-id"
    );

const photoRequestAuthorInputElement =
    document.querySelector(
        "#photo-request-author"
    );

const photoRequestPasswordInputElement =
    document.querySelector(
        "#photo-request-password"
    );

const photoRequestContentInputElement =
    document.querySelector(
        "#photo-request-content"
    );

const photoRequestImagesInputElement =
    document.querySelector(
        "#photo-request-images"
    );

const photoRequestImageListElement =
    document.querySelector(
        "#photo-request-image-list"
    );

const photoRequestWriteMessageElement =
    document.querySelector(
        "#photo-request-write-message"
    );


photoRequestImagesInputElement.addEventListener(
    "change",
    () => {

        const files =
            Array.from(
                photoRequestImagesInputElement.files
            );


        photoRequestImageListElement
            .innerHTML = "";


        if (files.length > 5) {

            photoRequestWriteMessageElement
                .textContent =
                    "이미지는 최대 5장까지 첨부할 수 있습니다.";

            photoRequestImagesInputElement
                .value = "";

            return;

        }


        for (const file of files) {

            if (file.size > 5 * 1024 * 1024) {

                photoRequestWriteMessageElement
                    .textContent =
                        `${file.name} 파일은 5MB를 초과합니다.`;

                photoRequestImagesInputElement
                    .value = "";

                photoRequestImageListElement
                    .innerHTML = "";

                return;

            }

        }


        photoRequestWriteMessageElement
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


                photoRequestImageListElement
                    .appendChild(
                        fileElement
                    );

            }
        );

    }
);


photoRequestWriteFormElement.addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();


        const playerName =
            photoRequestPlayerNameInputElement
                .value
                .trim();

        const seasonName =
            photoRequestSeasonNameInputElement
                .value
                .trim();

        const spIdText =
            photoRequestSpIdInputElement
                .value
                .trim();

        const authorName =
            photoRequestAuthorInputElement
                .value
                .trim();

        const password =
            photoRequestPasswordInputElement
                .value
                .trim();

        const content =
            photoRequestContentInputElement
                .value
                .trim();

        const files =
            Array.from(
                photoRequestImagesInputElement.files
            );


        if (
            !playerName
            || !authorName
            || !password
            || !content
        ) {

            photoRequestWriteMessageElement
                .textContent =
                    "선수명, 작성자, 비밀번호, 요청 내용을 모두 입력해주세요.";

            return;

        }


        if (password.length < 4) {

            photoRequestWriteMessageElement
                .textContent =
                    "비밀번호는 4자 이상 입력해주세요.";

            return;

        }


        if (files.length > 5) {

            photoRequestWriteMessageElement
                .textContent =
                    "이미지는 최대 5장까지 첨부할 수 있습니다.";

            return;

        }


        photoRequestWriteMessageElement
            .textContent =
                "요청을 등록하는 중...";


        try {

            const requestResponse =
                await fetch(
                    `${apiBaseUrl}/api/community/player-photo-requests`,
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
                                    player_name:
                                        playerName,

                                    season_name:
                                        seasonName,

                                    sp_id:
                                        spIdText
                                            ? Number(spIdText)
                                            : null,

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


            const requestData =
                await requestResponse.json();


            if (!requestResponse.ok) {

                throw new Error(
                    requestData.detail
                    ?? "선수 사진 요청 등록에 실패했습니다."
                );

            }


            if (files.length > 0) {

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
                        `${apiBaseUrl}/api/community/posts/${requestData.id}/attachments`,
                        {
                            method:
                                "POST",

                            body:
                                formData,
                        }
                    );


                const attachmentData =
                    await attachmentResponse.json();


                if (!attachmentResponse.ok) {

                    throw new Error(
                        attachmentData.detail
                        ?? "참고 이미지 업로드에 실패했습니다."
                    );

                }

            }


            window.location.href =
                "./player-photo-request.html";

        } catch (error) {

            console.error(
                error
            );


            photoRequestWriteMessageElement
                .textContent =
                    error.message;

        }

    }
);