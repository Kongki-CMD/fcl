import {
    apiBaseUrl,
} from "./config.js";


const photoRequestDetailElement =
    document.querySelector(
        "#photo-request-detail"
    );


function formatPhotoRequestDetailDate(
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


function getPhotoRequestStatusText(
    requestStatus
) {

    const statusTextMap = {
        pending:
            "대기중",

        in_progress:
            "처리중",

        completed:
            "완료",

        rejected:
            "반려",
    };


    return (
        statusTextMap[
            requestStatus
        ]
        ?? requestStatus
    );

}


function createInfoItem(
    label,
    value
) {

    const itemElement =
        document.createElement(
            "div"
        );

    itemElement.classList.add(
        "photo-request-detail-info-item"
    );


    const labelElement =
        document.createElement(
            "span"
        );

    labelElement.classList.add(
        "photo-request-detail-info-label"
    );

    labelElement.textContent =
        label;


    const valueElement =
        document.createElement(
            "span"
        );

    valueElement.classList.add(
        "photo-request-detail-info-value"
    );

    valueElement.textContent =
        value || "-";


    itemElement.append(
        labelElement,
        valueElement
    );


    return itemElement;
}


function renderPhotoRequestDetail(
    request
) {

    photoRequestDetailElement
        .innerHTML = "";


    // =========================
    // HEADER
    // =========================

    const headerElement =
        document.createElement(
            "div"
        );

    headerElement.classList.add(
        "photo-request-detail-header"
    );


    const titleAreaElement =
        document.createElement(
            "div"
        );

    titleAreaElement.classList.add(
        "photo-request-detail-title-area"
    );


    const titleElement =
        document.createElement(
            "h1"
        );

    titleElement.textContent =
        request.title;


    const statusElement =
        document.createElement(
            "span"
        );

    statusElement.classList.add(
        "photo-request-status",
        `photo-request-status-${request.request_status}`
    );

    statusElement.textContent =
        getPhotoRequestStatusText(
            request.request_status
        );


    titleAreaElement.append(
        titleElement,
        statusElement
    );


    const metaElement =
        document.createElement(
            "div"
        );

    metaElement.classList.add(
        "photo-request-detail-meta"
    );


    const authorElement =
        document.createElement(
            "span"
        );

    authorElement.textContent =
        `작성자 ${request.author_name}`;


    const dateElement =
        document.createElement(
            "span"
        );

    dateElement.textContent =
        formatPhotoRequestDetailDate(
            request.created_at
        );


    metaElement.append(
        authorElement,
        dateElement
    );


    headerElement.append(
        titleAreaElement,
        metaElement
    );


    // =========================
    // PLAYER INFO
    // =========================

    const infoElement =
        document.createElement(
            "div"
        );

    infoElement.classList.add(
        "photo-request-detail-info"
    );


    infoElement.append(
        createInfoItem(
            "선수",
            request.player_name
        ),

        createInfoItem(
            "시즌",
            request.season_name
        ),

        createInfoItem(
            "sp_id",
            request.sp_id
                ? String(
                    request.sp_id
                )
                : "-"
        )
    );


    // =========================
    // CONTENT
    // =========================

    const contentSectionElement =
        document.createElement(
            "section"
        );

    contentSectionElement.classList.add(
        "photo-request-detail-section"
    );


    const contentTitleElement =
        document.createElement(
            "h2"
        );

    contentTitleElement.textContent =
        "요청 내용";


    const contentElement =
        document.createElement(
            "div"
        );

    contentElement.classList.add(
        "photo-request-detail-content"
    );

    contentElement.textContent =
        request.content;


    contentSectionElement.append(
        contentTitleElement,
        contentElement
    );


    photoRequestDetailElement.append(
        headerElement,
        infoElement,
        contentSectionElement
    );


    // =========================
    // ATTACHMENTS
    // =========================

    if (
        Array.isArray(
            request.attachments
        )
        &&
        request.attachments.length > 0
    ) {

        const attachmentSectionElement =
            document.createElement(
                "section"
            );

        attachmentSectionElement.classList.add(
            "photo-request-detail-section"
        );


        const attachmentTitleElement =
            document.createElement(
                "h2"
            );

        attachmentTitleElement.textContent =
            "참고 이미지";


        const attachmentListElement =
            document.createElement(
                "div"
            );

        attachmentListElement.classList.add(
            "photo-request-detail-images"
        );


        request.attachments.forEach(
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
                    "photo-request-detail-image"
                );


                attachmentListElement.appendChild(
                    imageElement
                );

            }
        );


        attachmentSectionElement.append(
            attachmentTitleElement,
            attachmentListElement
        );


        photoRequestDetailElement.appendChild(
            attachmentSectionElement
        );

    }


    // =========================
    // ADMIN RESULT
    // =========================

    const adminSectionElement =
        document.createElement(
            "section"
        );

    adminSectionElement.classList.add(
        "photo-request-detail-section",
        "photo-request-admin-section"
    );


    const adminTitleElement =
        document.createElement(
            "h2"
        );

    adminTitleElement.textContent =
        "처리 결과";


    const adminNoteElement =
        document.createElement(
            "div"
        );

    adminNoteElement.classList.add(
        "photo-request-admin-note"
    );


    if (request.admin_note) {

        adminNoteElement.textContent =
            request.admin_note;

    } else {

        adminNoteElement.textContent =
            "아직 관리자 메모가 없습니다.";

    }


    adminSectionElement.append(
        adminTitleElement,
        adminNoteElement
    );


    if (request.completed_at) {

        const completedDateElement =
            document.createElement(
                "p"
            );

        completedDateElement.classList.add(
            "photo-request-completed-date"
        );

        completedDateElement.textContent =
            `처리일 ${formatPhotoRequestDetailDate(
                request.completed_at
            )}`;


        adminSectionElement.appendChild(
            completedDateElement
        );

    }


    photoRequestDetailElement.appendChild(
        adminSectionElement
    );

}


async function loadPhotoRequestDetail() {

    const searchParams =
        new URLSearchParams(
            window.location.search
        );


    const postId =
        searchParams.get(
            "id"
        );


    if (!postId) {

        photoRequestDetailElement
            .innerHTML = `
                <p class="community-empty">
                    요청 번호가 없습니다.
                </p>
            `;

        return;

    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/community/player-photo-requests/${postId}`
            );


        if (!response.ok) {

            const data =
                await response.json();


            throw new Error(
                data.detail
                ?? "선수 사진 요청을 불러오지 못했습니다."
            );

        }


        const request =
            await response.json();


        renderPhotoRequestDetail(
            request
        );

    } catch (error) {

        console.error(
            error
        );


        photoRequestDetailElement
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


        photoRequestDetailElement.appendChild(
            errorElement
        );

    }

}


loadPhotoRequestDetail();