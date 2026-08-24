import {
    apiBaseUrl,
} from "./config.js";


const userTokenStorageKey =
    "fclUserToken";


export function getUserToken() {

    return localStorage.getItem(
        userTokenStorageKey
    );

}


export function saveUserToken(
    token
) {

    localStorage.setItem(
        userTokenStorageKey,
        token
    );

}


export function removeUserToken() {

    localStorage.removeItem(
        userTokenStorageKey
    );

}


export function getUserAuthHeaders() {

    const token =
        getUserToken();


    if (!token) {

        return {};

    }


    return {
        Authorization:
            `Bearer ${token}`,
    };

}


export async function getCurrentUser() {

    const token =
        getUserToken();


    if (!token) {

        return null;

    }


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/auth/me`,
                {
                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );


        if (
            response.status === 401
        ) {

            removeUserToken();

            return null;

        }


        if (!response.ok) {

            throw new Error(
                "회원 정보를 불러오지 못했습니다."
            );

        }


        const data =
            await response.json();


        return (
            data.user
            ?? null
        );


    } catch (error) {

        console.error(
            "회원 정보 조회 오류",
            error
        );


        return null;

    }

}


export async function loginUser(
    email,
    password
) {

    const response =
        await fetch(
            `${apiBaseUrl}/api/auth/login`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        email,
                        password,
                    }),
            }
        );


    const data =
        await response.json();


    if (!response.ok) {

        throw new Error(
            data.detail
            ?? "로그인에 실패했습니다."
        );

    }


    saveUserToken(
        data.token
    );


    return data.user;

}


export async function signupUser(
    email,
    password,
    nickname
) {

    const response =
        await fetch(
            `${apiBaseUrl}/api/auth/signup`,
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",
                },

                body:
                    JSON.stringify({
                        email,
                        password,
                        nickname,
                    }),
            }
        );


    const data =
        await response.json();


    if (!response.ok) {

        throw new Error(
            data.detail
            ?? "회원가입에 실패했습니다."
        );

    }


    return data.user;

}


export async function logoutUser() {

    const token =
        getUserToken();


    if (token) {

        try {

            await fetch(
                `${apiBaseUrl}/api/auth/logout`,
                {
                    method:
                        "POST",

                    headers: {
                        Authorization:
                            `Bearer ${token}`,
                    },
                }
            );

        } catch (error) {

            console.error(
                "로그아웃 요청 오류",
                error
            );

        }

    }


    removeUserToken();

}