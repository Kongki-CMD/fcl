const patchNoteVersionFilterElement =
    document.querySelector(
        "#patch-note-version-filter"
    );


const patchNoteListElement =
    document.querySelector(
        "#patch-note-list"
    );


// =========================================
// 패치노트 데이터
// =========================================

const patchNoteData = [
    {
        version:
            "v1.2",

        date:
            "2026.08.23",

        title:
            "플레이오프 및 경기 기록 시스템 업데이트",

        summary: [
            "플레이오프 시스템 추가",
            "과거 경기 Snapshot 시스템 강화",
            "경기 상세보기 및 실제 포메이션 화면 추가",
            "SET MVP / MATCH MVP 및 시즌 아이콘 기능 개선",
            "모바일 경기 상세화면 및 관리자 기능 개선",
        ],

        sections: [
            {
                title:
                    "🏆 플레이오프 시스템 추가",

                items: [
                    "정규리그 종료 이후 진행되는 플레이오프 시스템이 추가되었습니다.",
                    "정규리그 상위 4명이 플레이오프에 진출합니다.",
                    "3위 vs 4위 준플레이오프가 진행됩니다.",
                    "2위 vs 준플레이오프 승자의 플레이오프가 진행됩니다.",
                    "1위 vs 플레이오프 승자의 결승전이 진행됩니다.",
                    "준플레이오프와 플레이오프는 BO5, 3선승제로 진행됩니다.",
                    "결승전은 BO7, 4선승제로 진행됩니다.",
                    "각 경기 결과에 따라 다음 라운드가 자동으로 구성됩니다.",
                    "결승 종료 시 최종 우승자가 확정됩니다.",
                    "동점 경기의 경우 승부차기 승자를 기준으로 승패를 처리할 수 있도록 개선했습니다.",
                    "정규리그 마지막 경기 종료 후 최초 준플레이오프가 생성되는 전체 진행 과정도 검증을 완료했습니다.",
                ],
            },

            {
                title:
                    "📅 정규리그 일정 관리 기능 추가",

                items: [
                    "정규리그 일정 변경 기능이 추가되었습니다.",
                    "참가자가 직접 일정을 수정하는 방식이 아닌, 참가자 간 협의 후 관리자가 최종적으로 경기 일정을 변경하는 방식으로 운영됩니다.",
                    "예정 상태의 경기만 변경할 수 있습니다.",
                    "진행 중 또는 종료된 경기는 변경할 수 없습니다.",
                    "경기 날짜를 변경할 수 있습니다.",
                    "관리자 페이지에서 일정을 통합 관리할 수 있습니다.",
                    "이미 진행된 경기 기록이 일정 변경으로 영향을 받는 문제를 방지했습니다.",
                ],
            },

            {
                title:
                    "❌ 친선전 취소 처리 개선",

                items: [
                    "친선전 예약 및 진행 중 취소에 대한 처리 로직을 정리했습니다.",
                    "경기 취소 시 불필요한 데이터가 남지 않도록 관련 데이터를 정리합니다.",
                    "취소된 경기가 이후 정상 경기 기록에 영향을 주지 않도록 개선했습니다.",
                ],
            },

            {
                title:
                    "📸 과거 경기 Snapshot 시스템 강화",

                items: [
                    "기존에는 참가자의 현재 팀이 변경되면 과거 경기에서도 현재 팀 정보가 노출될 가능성이 있었습니다.",
                    "이제 경기가 종료되는 순간 당시 정보를 Snapshot으로 저장합니다.",
                    "경기 종료 시 당시 팀명과 당시 팀 로고를 보존합니다.",
                    "경기 결과와 세트별 선수 구성을 보존합니다.",
                    "선수 시즌과 포지션, 강화 등급을 보존합니다.",
                    "선수 평점과 골, 도움 기록을 보존합니다.",
                    "이후 참가자가 다른 팀으로 변경하더라도 과거 경기에서는 당시 사용했던 팀과 스쿼드가 그대로 유지됩니다.",
                ],
            },

            {
                title:
                    "🛡️ 현재 팀과 과거 팀 기록 분리",

                items: [
                    "참가자의 현재 팀 정보와 과거 경기 기록을 완전히 분리했습니다.",
                    "관리자는 참가자의 현재 팀명과 팀 로고를 변경할 수 있습니다.",
                    "현재 팀 정보를 변경하더라도 이미 종료된 경기의 팀 정보에는 영향을 주지 않습니다.",
                    "예를 들어 과거에 일본 대표팀으로 참가했던 선수가 이후 다른 팀으로 변경해도 과거 경기에는 일본 팀이 유지됩니다.",
                    "변경된 팀 정보는 신규 경기부터 적용됩니다.",
                ],
            },

            {
                title:
                    "⚽ 경기 상세보기 기능 추가",

                items: [
                    "경기 결과에서 단순히 스코어만 확인하는 것이 아니라 실제 경기에서 사용한 스쿼드까지 확인할 수 있는 상세보기 기능이 추가되었습니다.",
                    "각 SET별 경기 결과를 확인할 수 있습니다.",
                    "참가자별 스쿼드를 확인할 수 있습니다.",
                    "선발 11명과 선수 포지션을 확인할 수 있습니다.",
                    "선수 이미지와 강화 등급을 확인할 수 있습니다.",
                    "평점, 득점, 도움 기록을 확인할 수 있습니다.",
                    "각 SET을 자유롭게 선택하여 해당 경기의 실제 스쿼드를 확인할 수 있습니다.",
                ],
            },

            {
                title:
                    "🟩 실제 포메이션 화면 추가",

                items: [
                    "선수 목록 형태가 아닌 실제 축구 경기장 형태의 포메이션 UI가 추가되었습니다.",
                    "FC Online 경기 데이터의 포지션 정보를 기반으로 선수를 경기장 위에 배치합니다.",
                    "GK부터 수비, 미드필더, 공격진까지 경기 당시 포지션에 맞춰 표시됩니다.",
                    "선수 이미지와 포지션을 확인할 수 있습니다.",
                    "강화 등급과 선수명을 확인할 수 있습니다.",
                    "평점과 득점, 도움 기록을 한 화면에서 확인할 수 있습니다.",
                    "포지션 간 겹침 문제를 조정하여 수비진과 수비형 미드필더를 보다 명확하게 구분했습니다.",
                ],
            },

            {
                title:
                    "⭐ SET MVP 추가",

                items: [
                    "각 세트마다 가장 좋은 활약을 기록한 SET MVP가 표시됩니다.",
                    "실제 해당 세트에 출전한 선수 중 평점, 득점, 도움 순으로 비교하여 선정됩니다.",
                    "SET을 변경하면 해당 SET의 MVP 역시 함께 변경됩니다.",
                ],
            },

            {
                title:
                    "🌟 MATCH MVP 개선",

                items: [
                    "전체 경기의 최고의 선수를 보여주는 MATCH MVP 표시를 개선했습니다.",
                    "MATCH MVP 영역에서 선수 이름뿐 아니라 해당 경기에서 사용한 정확한 선수 시즌까지 함께 확인할 수 있습니다.",
                ],
            },

            {
                title:
                    "🪪 FC Online 공식 시즌 아이콘 추가",

                items: [
                    "선수 이름 앞에 FC Online의 공식 시즌 아이콘이 표시됩니다.",
                    "시즌 아이콘은 선수 이름으로 추정하지 않고 경기 당시 저장된 정확한 spId를 기준으로 판별합니다.",
                    "포메이션 선수명에 시즌 아이콘이 적용되었습니다.",
                    "SET MVP에 시즌 아이콘이 적용되었습니다.",
                    "MATCH MVP에 시즌 아이콘이 적용되었습니다.",
                    "동일한 선수를 여러 시즌 카드로 사용하더라도 실제 경기에서 사용한 시즌을 정확하게 표시합니다.",
                ],
            },

            {
                title:
                    "💾 시즌 아이콘 영구 보존 시스템 추가",

                items: [
                    "FC Online 서비스 종료 또는 이미지 서버 변경에 대비하여 시즌 아이콘 자체도 별도로 보존합니다.",
                    "기존에는 FC Online 서버의 시즌 이미지 주소를 직접 사용했지만, 이제 한 번 사용된 시즌은 FCL 데이터베이스에 이미지 원본을 Snapshot으로 저장합니다.",
                    "현재 과거 경기에서 실제 사용된 총 41개 시즌의 시즌 아이콘 Snapshot 저장을 완료했습니다.",
                    "모든 시즌 이미지의 실제 데이터가 정상적으로 보존되어 있는 것도 확인했습니다.",
                ],
            },

            {
                title:
                    "🔐 FC Online 서비스 종료 이후에도 기록 유지",

                items: [
                    "이미 저장된 시즌의 경우 외부 FC Online 이미지 서버가 사라지더라도 FCL 자체 서버를 통해 시즌 아이콘을 제공할 수 있습니다.",
                    "사용 선수를 장기적으로 보존합니다.",
                    "선수 시즌과 시즌 아이콘을 보존합니다.",
                    "강화 등급과 포지션을 보존합니다.",
                    "경기 기록과 당시 스쿼드를 보존합니다.",
                    "당시 팀명과 당시 팀 로고를 보존합니다.",
                    "외부 서비스 변경과 관계없이 FCL의 과거 기록을 유지할 수 있도록 데이터 구조를 개선했습니다.",
                ],
            },

            {
                title:
                    "🔄 신규 경기 시즌 자동 Snapshot",

                items: [
                    "앞으로 새 경기에서 기존에 사용되지 않았던 새로운 시즌 카드가 등장하면 자동으로 시즌 Snapshot을 생성합니다.",
                    "이미 저장된 시즌은 다시 다운로드하지 않습니다.",
                    "처음 등장한 시즌만 자동으로 보존됩니다.",
                    "별도의 관리자 작업 없이 향후 경기 기록도 지속적으로 축적됩니다.",
                ],
            },

            {
                title:
                    "🗃️ 기존 경기 스쿼드 데이터 복구",

                items: [
                    "상세보기 기능 추가 이전에 완료되었던 과거 경기들도 다시 조회하여 세트별 스쿼드 Snapshot을 생성했습니다.",
                    "기존 경기에서도 신규 경기와 동일하게 포메이션을 확인할 수 있습니다.",
                    "기존 경기에서도 선수 정보와 SET MVP를 확인할 수 있습니다.",
                    "기존 경기에서도 실제 선수 시즌을 확인할 수 있습니다.",
                    "대표 검증 경기에서는 3 SET, 총 108명의 선수 Snapshot이 정상적으로 유지되는 것을 확인했습니다.",
                ],
            },

            {
                title:
                    "🛠️ 관리자 기능 개선",

                items: [
                    "통합 관리자 페이지에서 리그 운영에 필요한 주요 기능들을 관리할 수 있도록 개선했습니다.",
                    "참가자 현재 팀을 관리할 수 있습니다.",
                    "현재 팀 로고를 관리할 수 있습니다.",
                    "정규리그 일정을 변경할 수 있습니다.",
                    "경기 결과를 수정하거나 삭제할 수 있습니다.",
                    "플레이오프 경기를 관리할 수 있습니다.",
                    "과거 스쿼드 데이터를 복구할 수 있습니다.",
                    "경기 진행 상태를 관리할 수 있습니다.",
                    "과거 기록과 현재 운영 데이터를 분리하여 관리자 작업이 이미 완료된 경기 기록을 훼손하지 않도록 설계했습니다.",
                ],
            },

            {
                title:
                    "📱 모바일 경기 상세화면 개선",

                items: [
                    "경기 상세보기와 포메이션 화면을 모바일에서도 확인하기 쉽도록 UI를 조정했습니다.",
                    "경기 헤더 크기를 조정했습니다.",
                    "팀 로고 및 팀명 배치를 개선했습니다.",
                    "SET 선택 UI를 최적화했습니다.",
                    "참가자 선택 영역을 축소했습니다.",
                    "SET MVP 모바일 배치를 개선했습니다.",
                    "포메이션 선수 카드 크기를 최적화했습니다.",
                    "시즌 아이콘의 모바일 크기를 조정했습니다.",
                    "작은 화면에서도 포메이션 전체를 한눈에 확인할 수 있도록 공간 사용을 개선했습니다.",
                ],
            },

            {
                title:
                    "✅ 이번 업데이트 핵심 요약",

                items: [
                    "FCL은 단순한 경기 결과 사이트에서 경기 당시의 실제 데이터를 그대로 보존하는 기록 시스템으로 확장되었습니다.",
                    "경기가 종료되는 순간의 팀, 스쿼드, 선수 시즌, 포메이션, 개인 기록을 보존합니다.",
                    "이후 정보가 변경되거나 FC Online 서비스 환경이 변경되더라도 과거 기록은 유지됩니다.",
                    "앞으로도 실제 리그 운영 과정에서 필요한 기능과 기록 시스템을 지속적으로 개선해 나갈 예정입니다.",
                ],
            },
        ],
    },

    {
        version:
            "v1.1",

        date:
            "2026.08.23",

        title:
            "경기 진행 및 프리시즌 기능 개선",

        summary: [
            "경기 일정의 지난 경기 표시 및 정렬 개선",
            "경기 진행 및 결과 입력 흐름 개선",
            "프리시즌 경기 취소 및 결과 입력 UI 개선",
            "메인 화면의 진행 중 경기 결과 입력 경로 수정",
        ],

        sections: [
            {
                title:
                    "📅 경기 일정",

                items: [
                    "지난 경기를 경기 일정 하단에 배치했습니다.",
                    "지난 경기를 날짜순으로 정렬하도록 개선했습니다.",
                ],
            },

            {
                title:
                    "⚽ 경기 진행",

                items: [
                    "LIVE / WAITING 화면을 제거했습니다.",
                    "경기 시작 이후 수동 결과 입력 방식으로 변경했습니다.",
                    "진행 중 경기에서 경기 결과를 입력할 수 있도록 변경했습니다.",
                    "예약 페이지와 결과 입력 페이지의 진입 경로를 분리했습니다.",
                ],
            },

            {
                title:
                    "📝 프리시즌",

                items: [
                    "경기 취소 버튼을 추가했습니다.",
                    "수동 결과 입력 UI를 개선했습니다.",
                    "MATCH DATE TODAY 버튼을 추가했습니다.",
                ],
            },

            {
                title:
                    "🏠 메인",

                items: [
                    "진행 중 경기의 결과 입력 경로를 수정했습니다.",
                ],
            },
        ],
    },
];


let selectedPatchNoteVersion =
    "all";


// =========================================
// 버전 필터 출력
// =========================================

function renderPatchNoteVersionFilter() {

    patchNoteVersionFilterElement.innerHTML =
        "";


    const versionList = [
        "all",

        ...patchNoteData.map(
            (patchNote) =>
                patchNote.version
        ),
    ];


    versionList.forEach(
        (version) => {

            const buttonElement =
                document.createElement(
                    "button"
                );


            buttonElement.type =
                "button";


            buttonElement.classList.add(
                "patch-note-version-button"
            );


            buttonElement.textContent =
                version === "all"
                    ? "전체"
                    : version;


            if (
                selectedPatchNoteVersion
                === version
            ) {

                buttonElement.classList.add(
                    "active"
                );

            }


            buttonElement.addEventListener(
                "click",
                () => {

                    selectedPatchNoteVersion =
                        version;


                    renderPatchNoteVersionFilter();

                    renderPatchNotes();

                }
            );


            patchNoteVersionFilterElement
                .appendChild(
                    buttonElement
                );

        }
    );

}


// =========================================
// 패치노트 카드 출력
// =========================================

function renderPatchNotes() {

    patchNoteListElement.innerHTML =
        "";


    const filteredPatchNotes =
        selectedPatchNoteVersion
        === "all"
            ? patchNoteData
            : patchNoteData.filter(
                (patchNote) =>
                    patchNote.version
                    === selectedPatchNoteVersion
            );


    if (
        filteredPatchNotes.length
        === 0
    ) {

        patchNoteListElement.innerHTML = `
            <div class="patch-note-empty">
                등록된 패치노트가 없습니다.
            </div>
        `;

        return;

    }


    filteredPatchNotes.forEach(
        (patchNote) => {

            const cardElement =
                document.createElement(
                    "article"
                );


            cardElement.classList.add(
                "patch-note-card"
            );


            const summaryHtml =
                patchNote.summary
                    .map(
                        (summaryItem) => `
                            <li>
                                ${summaryItem}
                            </li>
                        `
                    )
                    .join("");


            const detailHtml =
                createPatchNoteDetailHtml(
                    patchNote.sections
                );


            cardElement.innerHTML = `
                <div
                    class="
                        patch-note-card-header
                    "
                >
                    <span
                        class="
                            patch-note-version
                        "
                    >
                        ${patchNote.version}
                    </span>

                    <time
                        class="
                            patch-note-date
                        "
                    >
                        ${patchNote.date}
                    </time>
                </div>


                <h2
                    class="
                        patch-note-title
                    "
                >
                    ${patchNote.title}
                </h2>


                <ul
                    class="
                        patch-note-summary
                    "
                >
                    ${summaryHtml}
                </ul>


                <div
                    class="
                        patch-note-detail
                    "
                    hidden
                >
                    ${detailHtml}
                </div>


                <button
                    type="button"
                    class="
                        patch-note-detail-button
                    "
                >
                    자세히 보기
                </button>
            `;


            const detailElement =
                cardElement.querySelector(
                    ".patch-note-detail"
                );


            const detailButtonElement =
                cardElement.querySelector(
                    ".patch-note-detail-button"
                );


            detailButtonElement.addEventListener(
                "click",
                () => {

                    const isOpen =
                        !detailElement.hidden;


                    detailElement.hidden =
                        isOpen;


                    detailButtonElement.textContent =
                        isOpen
                            ? "자세히 보기"
                            : "접기";

                }
            );


            patchNoteListElement.appendChild(
                cardElement
            );

        }
    );

}


// =========================================
// 패치 상세 내용 생성
// =========================================

function createPatchNoteDetailHtml(
    sections
) {

    return sections
        .map(
            (section) => {

                const itemHtml =
                    section.items
                        .map(
                            (item) => `
                                <li>
                                    ${item}
                                </li>
                            `
                        )
                        .join("");


                return `
                    <section
                        class="
                            patch-note-detail-section
                        "
                    >
                        <h3>
                            ${section.title}
                        </h3>

                        <ul>
                            ${itemHtml}
                        </ul>
                    </section>
                `;

            }
        )
        .join("");

}


// =========================================
// 초기화
// =========================================

function initializePatchNotes() {

    renderPatchNoteVersionFilter();

    renderPatchNotes();

}


initializePatchNotes();