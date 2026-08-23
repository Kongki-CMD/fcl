import {
    apiBaseUrl,
} from "./config.js";


const photoRequestListElement =
    document.querySelector(
        "#photo-request-list"
    );


function formatPhotoRequestDate(
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


function createPhotoRequestRow(
    request,
    displayNumber
) {

    const rowElement =
        document.createElement(
            "a"
        );


    rowElement.href =
        `./player-photo-request-detail.html?id=${request.id}`;

    rowElement.classList.add(
        "photo-request-row"
    );


    const numberElement =
        document.createElement(
            "span"
        );

    numberElement.classList.add(
        "photo-request-number"
    );

    numberElement.textContent =
        displayNumber;


    const playerElement =
        document.createElement(
            "span"
        );

    playerElement.classList.add(
        "photo-request-player"
    );

    playerElement.textContent =
        request.player_name;


    const seasonElement =
        document.createElement(
            "span"
        );

    seasonElement.classList.add(
        "photo-request-season"
    );

    seasonElement.textContent =
        request.season_name
        || "-";


    const authorElement =
        document.createElement(
            "span"
        );

    authorElement.classList.add(
        "photo-request-author"
    );

    authorElement.textContent =
        request.author_name;


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


    const dateElement =
        document.createElement(
            "span"
        );

    dateElement.classList.add(
        "photo-request-date"
    );

    dateElement.textContent =
        formatPhotoRequestDate(
            request.created_at
        );


    rowElement.append(
        numberElement,
        playerElement,
        seasonElement,
        authorElement,
        statusElement,
        dateElement
    );


    return rowElement;
}


function renderPhotoRequests(
    requests
) {

    photoRequestListElement
        .innerHTML = "";


    if (
        requests.length === 0
    ) {

        const emptyElement =
            document.createElement(
                "p"
            );

        emptyElement.classList.add(
            "community-empty"
        );

        emptyElement.textContent =
            "등록된 선수 사진 요청이 없습니다.";


        photoRequestListElement.appendChild(
            emptyElement
        );

        return;

    }


    requests.forEach(
        (
            request,
            index
        ) => {

            const displayNumber =
                requests.length
                - index;


            const rowElement =
                createPhotoRequestRow(
                    request,
                    displayNumber
                );


            photoRequestListElement.appendChild(
                rowElement
            );

        }
    );

}


async function loadPhotoRequests() {

    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/community/player-photo-requests`
            );


        if (!response.ok) {

            throw new Error(
                "선수 사진 요청 목록을 불러오지 못했습니다."
            );

        }


        const requests =
            await response.json();


        renderPhotoRequests(
            requests
        );

    } catch (error) {

        console.error(
            error
        );


        photoRequestListElement
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


        photoRequestListElement.appendChild(
            errorElement
        );

    }

}


loadPhotoRequests();