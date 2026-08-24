import {
    apiBaseUrl,
} from "./config.js";


import {
    getUserToken,
    removeUserToken,
} from "./auth.js";


const loginRequiredElement =
    document.querySelector(
        "#mypage-login-required"
    );


const contentElement =
    document.querySelector(
        "#mypage-content"
    );


const nicknameElement =
    document.querySelector(
        "#mypage-nickname"
    );


const emailElement =
    document.querySelector(
        "#mypage-email"
    );


const createdAtElement =
    document.querySelector(
        "#mypage-created-at"
    );


const pointsElement =
    document.querySelector(
        "#mypage-points"
    );


const pointListElement =
    document.querySelector(
        "#mypage-point-list"
    );


// =========================================
// 날짜
// =========================================

function formatDate(
    value
) {

    if (!value) {
        return "-";
    }


    const date =
        new Date(
            value
        );


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {
        return "-";
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
        }
    ).format(
        date
    );

}


// =========================================
// 거래 유형 표시
// =========================================

function getTransactionLabel(
    transactionType
) {

    const labels = {

        signup_bonus:
            "가입 보너스",

        prediction_bet:
            "승부예측 참여",

        prediction_win:
            "승부예측 적중",

        prediction_refund:
            "승부예측 환불",

        admin_grant:
            "관리자 지급",

        admin_deduct:
            "관리자 차감",

    };


    return (
        labels[
            transactionType
        ]
        ??
        transactionType
        ??
        "포인트 변동"
    );

}


// =========================================
// 로그인 필요
// =========================================

function showLoginRequired() {

    contentElement
        .classList
        .add(
            "hidden"
        );


    loginRequiredElement
        .classList
        .remove(
            "hidden"
        );

}


// =========================================
// 포인트 내역
// =========================================

function renderPointTransactions(
    transactions
) {

    pointListElement.innerHTML =
        "";


    if (
        !transactions
        ||
        transactions.length === 0
    ) {

        pointListElement.innerHTML = `
            <div class="mypage-empty">
                아직 포인트 내역이 없습니다.
            </div>
        `;

        return;

    }


    transactions.forEach(
        transaction => {

            const itemElement =
                document.createElement(
                    "div"
                );


            itemElement.classList.add(
                "mypage-point-item"
            );


            const amount =
                Number(
                    transaction.amount
                    ?? 0
                );


            const amountText =
                amount > 0
                    ? `+${amount.toLocaleString()} P`
                    : `${amount.toLocaleString()} P`;


            const infoElement =
                document.createElement(
                    "div"
                );


            infoElement.classList.add(
                "mypage-point-info"
            );


            const titleElement =
                document.createElement(
                    "strong"
                );


            titleElement.textContent =
                getTransactionLabel(
                    transaction
                        .transaction_type
                );


            const descriptionElement =
                document.createElement(
                    "span"
                );


            descriptionElement.textContent =
                transaction.description
                ??
                formatDate(
                    transaction.created_at
                );


            infoElement.append(
                titleElement,
                descriptionElement
            );


            const valueElement =
                document.createElement(
                    "div"
                );


            valueElement.classList.add(
                "mypage-point-value"
            );


            if (
                amount > 0
            ) {

                valueElement
                    .classList
                    .add(
                        "plus"
                    );

            } else {

                valueElement
                    .classList
                    .add(
                        "minus"
                    );

            }


            const amountElement =
                document.createElement(
                    "strong"
                );


            amountElement.textContent =
                amountText;


            const balanceElement =
                document.createElement(
                    "span"
                );


            balanceElement.textContent =
                `잔액 ${Number(
                    transaction
                        .balance_after
                    ?? 0
                ).toLocaleString()} P`;


            valueElement.append(
                amountElement,
                balanceElement
            );


            itemElement.append(
                infoElement,
                valueElement
            );


            pointListElement.append(
                itemElement
            );

        }
    );

}


// =========================================
// 마이페이지 불러오기
// =========================================

async function loadMyPage() {

    const token =
        getUserToken();


    if (!token) {

        showLoginRequired();

        return;

    }


    try {

        const headers = {
            Authorization:
                `Bearer ${token}`,
        };


        const [
            profileResponse,
            pointResponse,
        ] = await Promise.all(
            [
                fetch(
                    `${apiBaseUrl}/api/mypage`,
                    {
                        headers,
                    }
                ),

                fetch(
                    `${apiBaseUrl}/api/mypage/point-transactions`,
                    {
                        headers,
                    }
                ),
            ]
        );


        if (
            profileResponse.status
                === 401
            ||
            pointResponse.status
                === 401
        ) {

            removeUserToken();

            showLoginRequired();

            return;

        }


        const profileData =
            await profileResponse.json();


        const pointData =
            await pointResponse.json();


        if (!profileResponse.ok) {

            throw new Error(
                profileData.detail
                ??
                "회원 정보를 불러오지 못했습니다."
            );

        }


        if (!pointResponse.ok) {

            throw new Error(
                pointData.detail
                ??
                "포인트 내역을 불러오지 못했습니다."
            );

        }


        const user =
            profileData.user;


        nicknameElement.textContent =
            user.nickname;


        emailElement.textContent =
            user.email;


        createdAtElement.textContent =
            formatDate(
                user.created_at
            );


        pointsElement.textContent =
            `${Number(
                user.points
                ?? 0
            ).toLocaleString()} P`;


        renderPointTransactions(
            pointData.transactions
        );


        loginRequiredElement
            .classList
            .add(
                "hidden"
            );


        contentElement
            .classList
            .remove(
                "hidden"
            );


    } catch (error) {

        console.error(
            error
        );


        pointListElement.innerHTML = `
            <div class="mypage-empty">
                마이페이지 정보를 불러오지 못했습니다.
            </div>
        `;


        contentElement
            .classList
            .remove(
                "hidden"
            );

    }

}


loadMyPage();