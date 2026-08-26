import { apiBaseUrl } from "./config.js";

import {
    getUserToken,
    removeUserToken,
} from "./auth.js";


// =========================================
// ELEMENTS
// =========================================

const eventTabButtonElements =
    document.querySelectorAll(
        ".event-tab-button"
    );


const eventPanelElements =
    document.querySelectorAll(
        ".event-panel"
    );


const attendanceTodayStatusElement =
    document.querySelector(
        "#attendance-today-status"
    );


const attendanceTotalCountElement =
    document.querySelector(
        "#attendance-total-count"
    );


const attendanceRewardPointsElement =
    document.querySelector(
        "#attendance-reward-points"
    );


const attendanceCheckButtonElement =
    document.querySelector(
        "#attendance-check-button"
    );


const attendanceMessageElement =
    document.querySelector(
        "#attendance-message"
    );

const attendanceCalendarTitleElement =
    document.querySelector(
        "#attendance-calendar-title"
    );


const attendanceCalendarGridElement =
    document.querySelector(
        "#attendance-calendar-grid"
    );


// =========================================
// EVENT TAB
// =========================================

function changeEventTab(
    eventName
) {

    eventTabButtonElements.forEach(
        (buttonElement) => {

            const isActive =
                buttonElement.dataset.eventTab
                === eventName;


            buttonElement.classList.toggle(
                "active",
                isActive
            );

        }
    );


    eventPanelElements.forEach(
        (panelElement) => {

            const isActive =
                panelElement.dataset.eventPanel
                === eventName;


            panelElement.classList.toggle(
                "active",
                isActive
            );

        }
    );

}


eventTabButtonElements.forEach(
    (buttonElement) => {

        buttonElement.addEventListener(
            "click",
            () => {

                changeEventTab(
                    buttonElement.dataset.eventTab
                );

            }
        );

    }
);


// =========================================
// 숫자 포맷
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
// 로그인 필요 상태
// =========================================

function renderLoginRequired() {

    attendanceTodayStatusElement.textContent =
        "-";


    attendanceTotalCountElement.textContent =
        "-";


    attendanceRewardPointsElement.textContent =
        "50 P";


    attendanceCheckButtonElement.disabled =
        true;


    attendanceCheckButtonElement.textContent =
        "로그인 후 참여 가능";


    attendanceMessageElement.textContent =
        "출석체크는 로그인한 회원만 참여할 수 있습니다.";

    attendanceCalendarTitleElement.textContent =
        "출석 달력";


    attendanceCalendarGridElement.innerHTML =
        `
            <p class="attendance-calendar-login-message">
                로그인하면 출석 달력을 확인할 수 있습니다.
            </p>
        `;

}

// =========================================
// 출석 달력
// =========================================

function renderAttendanceCalendar(
    attendanceData
) {

    attendanceCalendarGridElement.innerHTML =
        "";


    const currentMonth =
        attendanceData.current_month;


    if (!currentMonth) {
        return;
    }


    const [
        yearText,
        monthText,
    ] = currentMonth.split(
        "-"
    );


    const year =
        Number(
            yearText
        );


    const month =
        Number(
            monthText
        );


    attendanceCalendarTitleElement.textContent =
        `${year}년 ${month}월`;


    const firstDay =
        new Date(
            year,
            month - 1,
            1
        ).getDay();


    const daysInMonth =
        new Date(
            year,
            month,
            0
        ).getDate();


    const attendanceDateSet =
        new Set(
            attendanceData
                .month_attendance_dates
                || []
        );


    const today =
        attendanceData.attendance_date;


    // =====================================
    // 앞쪽 빈칸
    // =====================================

    for (
        let emptyIndex = 0;
        emptyIndex < firstDay;
        emptyIndex += 1
    ) {

        const emptyElement =
            document.createElement(
                "div"
            );


        emptyElement.className =
            "attendance-calendar-day empty";


        attendanceCalendarGridElement.appendChild(
            emptyElement
        );

    }


    // =====================================
    // 날짜
    // =====================================

    for (
        let day = 1;
        day <= daysInMonth;
        day += 1
    ) {

        const dayElement =
            document.createElement(
                "div"
            );


        dayElement.className =
            "attendance-calendar-day";


        const dateString =
            (
                `${year}-`
                +
                `${String(month).padStart(
                    2,
                    "0"
                )}-`
                +
                `${String(day).padStart(
                    2,
                    "0"
                )}`
            );


        if (
            dateString === today
        ) {

            dayElement.classList.add(
                "today"
            );

        }


        const dateNumberElement =
            document.createElement(
                "span"
            );


        dateNumberElement.className =
            "attendance-calendar-date";


        dateNumberElement.textContent =
            day;


        dayElement.appendChild(
            dateNumberElement
        );


        // =================================
        // 출석 도장
        // =================================

        if (
            attendanceDateSet.has(
                dateString
            )
        ) {

            dayElement.classList.add(
                "attended"
            );


            const stampElement =
                document.createElement(
                    "span"
                );


            stampElement.className =
                "attendance-stamp";


            stampElement.textContent =
                "출석";


            dayElement.appendChild(
                stampElement
            );

        }


        attendanceCalendarGridElement.appendChild(
            dayElement
        );

    }

}


// =========================================
// 출석 상태 출력
// =========================================

function renderAttendanceStatus(
    attendanceData
) {

    renderAttendanceCalendar(
        attendanceData
    );


    attendanceTotalCountElement.textContent =
        `${formatPoints(
            attendanceData.total_count
        )}일`;


    attendanceRewardPointsElement.textContent =
        `${formatPoints(
            attendanceData.today_reward_points
        )} P`;


    // =====================================
    // 오늘 이미 출석
    // =====================================

    if (
        attendanceData.today_attended
    ) {

        attendanceTodayStatusElement.textContent =
            "출석 완료";


        attendanceCheckButtonElement.disabled =
            true;


        attendanceCheckButtonElement.textContent =
            "오늘 출석 완료";


        if (
            Number(
                attendanceData.today_streak_bonus
                || 0
            ) > 0
        ) {

            attendanceMessageElement.textContent =
                (
                    `${attendanceData.current_streak}일 연속 출석 달성! `
                    +
                    `기본 ${formatPoints(
                        attendanceData.daily_reward_points
                    )}P + `
                    +
                    `연속 출석 보너스 ${formatPoints(
                        attendanceData.today_streak_bonus
                    )}P가 지급되었습니다.`
                );

        } else {

            attendanceMessageElement.textContent =
                (
                    `${attendanceData.current_streak}일 연속 출석 중입니다. `
                    +
                    `오늘 보상 ${formatPoints(
                        attendanceData.today_reward_points
                    )}P를 받았습니다.`
                );

        }


        return;
    }


    // =====================================
    // 오늘 아직 출석 전
    // =====================================

    attendanceTodayStatusElement.textContent =
        "미출석";


    attendanceCheckButtonElement.disabled =
        false;


    attendanceCheckButtonElement.textContent =
        (
            `출석체크 +${formatPoints(
                attendanceData.today_reward_points
            )}P`
        );


    const nextStreak =
        Number(
            attendanceData.next_streak
            || 1
        );


    const todayBonus =
        Number(
            attendanceData.today_streak_bonus
            || 0
        );


    if (
        todayBonus > 0
    ) {

        attendanceMessageElement.textContent =
            (
                `오늘 출석하면 ${nextStreak}일 연속 출석 달성! `
                +
                `기본 ${formatPoints(
                    attendanceData.daily_reward_points
                )}P + `
                +
                `보너스 ${formatPoints(
                    todayBonus
                )}P를 받을 수 있습니다.`
            );

    } else {

        attendanceMessageElement.textContent =
            (
                `오늘 출석하면 ${formatPoints(
                    attendanceData.today_reward_points
                )}P가 지급됩니다. `
                +
                `7일 연속 출석마다 추가 150P가 지급됩니다.`
            );

    }

}


// =========================================
// 출석 상태 조회
// =========================================

async function loadAttendanceStatus() {

    const token =
        getUserToken();


    if (!token) {

        renderLoginRequired();

        return;

    }


    attendanceTodayStatusElement.textContent =
        "확인 중";


    attendanceCheckButtonElement.disabled =
        true;


    attendanceCheckButtonElement.textContent =
        "확인 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/events/attendance`,
                {
                    headers: {
                        "Authorization":
                            `Bearer ${token}`,
                    },
                }
            );


        if (
            response.status
            === 401
        ) {

            removeUserToken();

            renderLoginRequired();

            return;
        }


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ||
                "출석 정보를 불러오지 못했습니다."
            );

        }


        renderAttendanceStatus(
            data
        );

    } catch (
        error
    ) {

        console.error(
            error
        );


        attendanceTodayStatusElement.textContent =
            "오류";


        attendanceCheckButtonElement.disabled =
            true;


        attendanceCheckButtonElement.textContent =
            "출석체크";


        attendanceMessageElement.textContent =
            error.message;

    }

}


// =========================================
// 출석체크 실행
// =========================================

async function submitAttendance() {

    const token =
        getUserToken();


    if (!token) {

        renderLoginRequired();

        return;

    }


    attendanceCheckButtonElement.disabled =
        true;


    attendanceCheckButtonElement.textContent =
        "처리 중...";


    try {

        const response =
            await fetch(
                `${apiBaseUrl}/api/events/attendance`,
                {
                    method:
                        "POST",

                    headers: {
                        "Authorization":
                            `Bearer ${token}`,
                    },
                }
            );


        if (
            response.status
            === 401
        ) {

            removeUserToken();

            renderLoginRequired();

            return;
        }


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail
                ||
                "출석체크에 실패했습니다."
            );

        }


        alert(
            data.message
        );


        // =====================================
        // 헤더 보유 포인트까지
        // 최신 상태로 다시 불러오기
        // =====================================

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


        await loadAttendanceStatus();

    }

}


// =========================================
// 출석 버튼
// =========================================

attendanceCheckButtonElement.addEventListener(
    "click",
    submitAttendance
);


// =========================================
// 실행
// =========================================

loadAttendanceStatus();