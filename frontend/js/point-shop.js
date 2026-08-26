import {
    apiBaseUrl,
} from "./config.js";

import {
    getCurrentUser,
    getUserToken,
    removeUserToken,
} from "./auth.js";


// =========================================
// STATE
// =========================================

let currentUser =
    null;


let pointShopProducts =
    [];


// =========================================
// ELEMENTS
// =========================================

const pointShopBalanceElement =
    document.querySelector(
        "#point-shop-balance"
    );


const pointShopProductGridElement =
    document.querySelector(
        "#point-shop-product-grid"
    );


// =========================================
// 포인트 포맷
// =========================================

function formatPoints(
    points
) {

    return Number(
        points || 0
    ).toLocaleString(
        "ko-KR"
    );

}


// =========================================
// 보유 포인트
// =========================================

function renderUserPoints() {

    if (!currentUser) {

        pointShopBalanceElement.textContent =
            "로그인 후 확인 가능";

        return;

    }


    pointShopBalanceElement.textContent =
        `${formatPoints(
            currentUser.points
        )} P`;

}

// =========================================
// 상품 이미지 경로 정리
// =========================================

function normalizeProductImageUrl(
    imageUrl
) {

    if (!imageUrl) {
        return "";
    }


    let normalizedUrl =
        String(
            imageUrl
        )
            .trim()
            .replaceAll(
                "\\",
                "/"
            );


    // 외부 이미지 URL은 그대로 사용
    if (
        normalizedUrl.startsWith(
            "http://"
        )
        ||
        normalizedUrl.startsWith(
            "https://"
        )
    ) {

        return normalizedUrl;

    }


    // ./frontend/... 입력 대응
    if (
        normalizedUrl.startsWith(
            "./frontend/"
        )
    ) {

        normalizedUrl =
            "./"
            +
            normalizedUrl.slice(
                "./frontend/".length
            );

    }


    // frontend/... 입력 대응
    else if (
        normalizedUrl.startsWith(
            "frontend/"
        )
    ) {

        normalizedUrl =
            "./"
            +
            normalizedUrl.slice(
                "frontend/".length
            );

    }


    // assets/... 입력 대응
    else if (
        normalizedUrl.startsWith(
            "assets/"
        )
    ) {

        normalizedUrl =
            `./${normalizedUrl}`;

    }


    return normalizedUrl;

}


// =========================================
// 상품 이미지 placeholder
// =========================================

function renderProductPlaceholder(
    imageBoxElement
) {

    imageBoxElement.innerHTML =
        "";


    const placeholderElement =
        document.createElement(
            "span"
        );


    placeholderElement.textContent =
        "FCL REWARD";


    imageBoxElement.appendChild(
        placeholderElement
    );

}


// =========================================
// 상품 카드
// =========================================

function createProductCard(
    product
) {

    const cardElement =
        document.createElement(
            "article"
        );


    cardElement.className =
        "point-shop-product-card";


    // =====================================
    // 이미지
    // =====================================

    const imageBoxElement =
        document.createElement(
            "div"
        );


    imageBoxElement.className =
        "point-shop-product-image";


    if (
        product.image_url
    ) {

        const imageElement =
            document.createElement(
                "img"
            );


        imageElement.src =
            normalizeProductImageUrl(
                product.image_url
            );


        imageElement.alt =
            `${product.name} 이미지`;


        imageElement.addEventListener(
            "error",
            () => {

                console.error(
                    "상품 이미지 로드 실패:",
                    imageElement.src,
                    product
                );


                renderProductPlaceholder(
                    imageBoxElement
                );

            }
        );


        imageBoxElement.appendChild(
            imageElement
        );

    } else {

        renderProductPlaceholder(
            imageBoxElement
        );

    }


    // =====================================
    // 상품 정보
    // =====================================

    const infoElement =
        document.createElement(
            "div"
        );


    infoElement.className =
        "point-shop-product-info";


    const categoryElement =
        document.createElement(
            "span"
        );


    categoryElement.className =
        "point-shop-product-category";


    categoryElement.textContent =
        product.category
        ||
        "FCL REWARD";


    const nameElement =
        document.createElement(
            "h3"
        );


    nameElement.textContent =
        product.name;


    const descriptionElement =
        document.createElement(
            "p"
        );


    descriptionElement.textContent =
        product.description
        ||
        "FCL 포인트로 교환할 수 있는 상품입니다.";


    const priceElement =
        document.createElement(
            "strong"
        );


    priceElement.className =
        "point-shop-product-price";


    priceElement.textContent =
        `${formatPoints(
            product.price_points
        )} P`;


    infoElement.append(
        categoryElement,
        nameElement,
        descriptionElement,
        priceElement
    );


    // =====================================
    // 교환 버튼
    // =====================================

    const exchangeButtonElement =
        document.createElement(
            "button"
        );


    exchangeButtonElement.type =
        "button";


    exchangeButtonElement.className =
        "point-shop-exchange-button";


    if (!currentUser) {

        exchangeButtonElement.disabled =
            true;


        exchangeButtonElement.textContent =
            "로그인 필요";

    } else if (
        Number(
            currentUser.points
        )
        <
        Number(
            product.price_points
        )
    ) {

        exchangeButtonElement.disabled =
            true;


        exchangeButtonElement.textContent =
            "포인트 부족";

    } else {

        exchangeButtonElement.disabled =
            false;


        exchangeButtonElement.textContent =
            "교환하기";


        exchangeButtonElement.addEventListener(
            "click",
            () => {

                exchangePointShopProduct(
                    product,
                    exchangeButtonElement
                );

            }
        );

    }


    cardElement.append(
        imageBoxElement,
        infoElement,
        exchangeButtonElement
    );


    return cardElement;

}


// =========================================
// 상품 목록 출력
// =========================================

function renderProducts() {

    pointShopProductGridElement.innerHTML =
        "";


    if (
        pointShopProducts.length
        === 0
    ) {

        const emptyElement =
            document.createElement(
                "div"
            );


        emptyElement.className =
            "point-shop-empty";


        emptyElement.textContent =
            "현재 교환 가능한 상품이 없습니다.";


        pointShopProductGridElement
            .appendChild(
                emptyElement
            );


        return;

    }


    pointShopProducts.forEach(
        (product) => {

            pointShopProductGridElement
                .appendChild(
                    createProductCard(
                        product
                    )
                );

        }
    );

}


// =========================================
// 상품 조회
// =========================================

async function loadProducts() {

    const response =
        await fetch(
            `${apiBaseUrl}/api/point-shop/products`
        );


    const data =
        await response.json();


    if (!response.ok) {

        throw new Error(
            data.detail
            ||
            "교환 상품을 불러오지 못했습니다."
        );

    }


    pointShopProducts =
        data;

}


// =========================================
// 상품 교환
// =========================================

async function exchangePointShopProduct(
    product,
    buttonElement
) {

    const token =
        getUserToken();


    if (!token) {

        alert(
            "로그인 후 이용해주세요."
        );

        return;

    }


    const confirmed =
        confirm(
            `${product.name}\n\n`
            +
            `${formatPoints(
                product.price_points
            )}P를 사용하여 교환하시겠습니까?`
        );


    if (!confirmed) {
        return;
    }


    buttonElement.disabled =
        true;


    buttonElement.textContent =
        "교환 처리 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}`
                + "/api/point-shop/exchanges",
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
                        JSON.stringify({
                            product_id:
                                product.id,
                        }),
                }
            );


        const data =
            await response.json();


        if (
            response.status
            === 401
        ) {

            removeUserToken();


            alert(
                "로그인이 만료되었습니다."
            );


            window.location.reload();

            return;

        }


        if (!response.ok) {

            throw new Error(
                data.detail
                ||
                "상품 교환에 실패했습니다."
            );

        }


        alert(
            data.message
        );


        // 헤더 포인트까지 최신 상태 반영
        window.location.reload();


    } catch (
        error
    ) {

        console.error(
            error
        );


        alert(
            error.message
        );


        buttonElement.disabled =
            false;


        buttonElement.textContent =
            "교환하기";

    }

}


// =========================================
// 페이지 로딩
// =========================================

async function loadPointShopPage() {

    pointShopProductGridElement
        .textContent =
            "교환 상품을 불러오는 중...";


    try {

        currentUser =
            await getCurrentUser();


        await loadProducts();


        renderUserPoints();


        renderProducts();


    } catch (
        error
    ) {

        console.error(
            error
        );


        renderUserPoints();


        pointShopProductGridElement
            .textContent =
                error.message;

    }

}


// =========================================
// 실행
// =========================================

loadPointShopPage();