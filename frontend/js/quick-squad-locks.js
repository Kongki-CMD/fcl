const STORAGE_KEY = "fcl.quick-squad.locks.v1";
const STORAGE_EVENT = "fcl:quick-squad-locks-changed";

const positiveInteger = value =>
    Number.isSafeInteger(Number(value))
    && Number(value) > 0;

const nameKey = value =>
    String(value ?? "").trim().toLocaleLowerCase("ko-KR");

const escapeHtml = value =>
    String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

const safeImage = value => {
    try {
        const url = new URL(
            String(value || ""),
            location.href
        );

        return ["http:", "https:"].includes(url.protocol)
            ? url.href
            : "";
    } catch {
        return "";
    }
};

export function readQuickSquadLocks() {
    try {
        const raw = JSON.parse(
            localStorage.getItem(STORAGE_KEY) || "[]"
        );

        if (!Array.isArray(raw)) {
            return [];
        }

        return raw.slice(0, 11)
            .filter(p =>
                positiveInteger(p.sp_id)
                && Number.isInteger(p.grade)
                && p.grade >= 1
                && p.grade <= 13
            )
            .map(p => ({
                sp_id: Number(p.sp_id),
                grade: Number(p.grade),
                player_name: String(p.player_name || ""),
                position: String(p.position || ""),
                slot_index: (
                    Number.isInteger(p.slot_index)
                    && p.slot_index >= 0
                    && p.slot_index <= 10
                        ? p.slot_index
                        : null
                ),
                slot_position: String(p.slot_position || ""),
                preferred_team_color_id: (
                    positiveInteger(p.preferred_team_color_id)
                        ? Number(p.preferred_team_color_id)
                        : null
                ),
            }));
    } catch {
        return [];
    }
}

function saveLocks(entries) {
    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(entries)
    );

    window.dispatchEvent(
        new CustomEvent(STORAGE_EVENT)
    );
}

export function addQuickSquadLock(player) {
    const sp_id = Number(player.sp_id);
    const grade = Number(player.grade);

    if (
        !positiveInteger(sp_id)
        || !Number.isInteger(grade)
        || grade < 1
        || grade > 13
    ) {
        throw new Error(
            "선수 카드와 강화등급을 확인해주세요."
        );
    }

    const entries = readQuickSquadLocks();
    const same = entries.find(p => p.sp_id === sp_id);

    if (
        !same
        && entries.some(p =>
            nameKey(p.player_name)
            === nameKey(player.player_name)
        )
    ) {
        throw new Error(
            "같은 선수의 다른 시즌이 이미 등록되어 있습니다. "
            + "기존 선수를 먼저 해제해주세요."
        );
    }

    if (!same && entries.length >= 11) {
        throw new Error("고정 선수는 최대 11명입니다.");
    }

    const entry = {
        sp_id,
        grade,
        player_name: String(player.player_name || ""),
        position: String(player.position || ""),
        slot_index: same?.slot_index ?? null,
        slot_position: same?.slot_position ?? "",
        preferred_team_color_id: (
            positiveInteger(player.preferred_team_color_id)
                ? Number(player.preferred_team_color_id)
                : same?.preferred_team_color_id ?? null
        ),
    };

    if (same) {
        Object.assign(same, entry);
    } else {
        entries.push(entry);
    }

    saveLocks(entries);
    return entries.length;
}

export function createQuickSquadLockController({
    apiBaseUrl,
    root,
    getSlots,
    getTeamColorId,
    getBudgetBp,
    formatPrice,
    onChange,
}) {
    let entries = readQuickSquadLocks();
    let preview = [];
    let error = "";
    let generation = 0;

    const $ = selector => root.querySelector(selector);
    const getPlayer = spid =>
        preview.find(p => p.sp_id === spid);

    const total = () =>
        preview.reduce(
            (sum, p) => sum + Number(p.price || 0),
            0
        );

    const salary = () =>
        preview.reduce(
            (sum, p) => sum + Number(p.salary || 0),
            0
        );

    const selectedTeam = () => {
        const id = Number(getTeamColorId());
        return positiveInteger(id) ? id : null;
    };

    const persist = () => saveLocks(entries);

    const notify = () => onChange(
        preview.map(p => {
            const entry = entries.find(
                e => e.sp_id === p.sp_id
            );

            return {
                ...p,
                slot_index: entry?.slot_index ?? null,
                slot_position: entry?.slot_position || null,
                locked: true,
            };
        })
    );

    function remap(autoAssign = true) {
        const slots = getSlots();
        const occupied = new Set();

        for (const entry of entries) {
            const player = getPlayer(entry.sp_id);
            const allowed = player?.allowed_positions
                || (entry.position ? [entry.position] : []);

            let index = entry.slot_index;

            if (
                index !== null
                && (
                    !slots[index]
                    || slots[index].position
                        !== entry.slot_position
                    || !allowed.includes(
                        slots[index].position
                    )
                    || occupied.has(index)
                )
            ) {
                index = slots.findIndex(
                    (slot, i) =>
                        slot.position === entry.slot_position
                        && allowed.includes(slot.position)
                        && !occupied.has(i)
                );

                if (index < 0) {
                    index = null;
                    entry.slot_position = "__unassigned__";
                }
            }

            if (
                index === null
                && autoAssign
                && player
                && !entry.slot_position
            ) {
                index = slots.findIndex(
                    (slot, i) =>
                        allowed.includes(slot.position)
                        && !occupied.has(i)
                );

                if (index < 0) {
                    index = null;
                }
            }

            entry.slot_index = index;
            entry.slot_position = (
                index === null
                    ? entry.slot_position
                    : slots[index].position
            );

            if (index !== null) {
                occupied.add(index);
            }
        }
    }

    function render() {
        const budget = Number(getBudgetBp()) || 0;

        $("[data-qs-lock-count]").textContent =
            `${entries.length} / 11`;

        $("[data-qs-lock-total]").textContent =
            formatPrice(total());

        $("[data-qs-lock-salary]").textContent =
            `${salary()} / 310`;

        $("[data-qs-lock-remaining]").textContent =
            budget > 0
                ? formatPrice(budget - total())
                : "예산 설정 대기";

        $("[data-qs-lock-error]").textContent = error;
        $("[data-qs-lock-clear]").disabled =
            entries.length === 0;

        const slots = getSlots();

        $("[data-qs-lock-list]").innerHTML =
            entries.length
                ? entries.map(entry => {
                    const p = getPlayer(entry.sp_id);

                    const occupied = new Set(
                        entries
                            .filter(e =>
                                e.sp_id !== entry.sp_id
                            )
                            .map(e => e.slot_index)
                    );

                    const allowed =
                        p?.allowed_positions
                        || (entry.position ? [entry.position] : []);

                    const options = slots
                        .map((slot, i) => ({slot, i}))
                        .filter(({slot, i}) =>
                            allowed.includes(slot.position)
                            && !occupied.has(i)
                        )
                        .map(({slot, i}) => `
                            <option
                                value="${i}"
                                ${entry.slot_index === i
                                    ? "selected"
                                    : ""}
                            >
                                ${escapeHtml(slot.position)}
                                · ${i + 1}번 자리
                            </option>
                        `)
                        .join("");

                    return `
                        <article
                            class="qs-lock-row"
                            data-lock-id="${entry.sp_id}"
                        >
                            <img
                                class="qs-lock-image"
                                src="${escapeHtml(safeImage(
                                    p?.image_url
                                ))}"
                                alt=""
                                loading="lazy"
                            >

                            <div class="qs-lock-info">
                                <strong>
                                    ${escapeHtml(
                                        p?.player_name
                                        || entry.player_name
                                    )}
                                </strong>

                                <span>
                                    시즌 ${escapeHtml(
                                        p?.season_id
                                        || Math.floor(
                                            entry.sp_id / 1000000
                                        )
                                    )}
                                    · +${entry.grade}
                                    · 급여 ${p?.salary ?? "-"}
                                </span>

                                <span>
                                    ${p
                                        ? formatPrice(p.price)
                                        : "시세 확인 중"}
                                </span>

                                ${p && !p.team_color_match
                                    ? `<small class="qs-lock-warning">
                                        선택한 팀컬러에 속하지 않습니다.
                                       </small>`
                                    : ""}
                            </div>

                            <label class="qs-lock-placement">
                                <span>고정 포지션</span>

                                <select
                                    data-lock-slot="${entry.sp_id}"
                                >
                                    <option
                                        value=""
                                        ${entry.slot_index === null
                                            ? "selected"
                                            : ""}
                                    >
                                        포지션 선택
                                    </option>

                                    ${options}
                                </select>
                            </label>

                            <button
                                type="button"
                                class="qs-lock-remove"
                                data-lock-remove="${entry.sp_id}"
                                aria-label="${escapeHtml(
                                    entry.player_name
                                )} 고정 해제"
                            >
                                해제
                            </button>
                        </article>
                    `;
                }).join("")
                : `
                    <p class="qs-lock-empty">
                        선수도감에서 원하는 선수를 등록하거나,
                        등록 없이 기존 추천을 이용할 수 있습니다.
                    </p>
                `;
    }

    async function refresh() {
        const token = ++generation;

        if (!entries.length) {
            preview = [];
            error = "";
            render();
            notify();
            return;
        }

        try {
            const response = await fetch(
                `${apiBaseUrl}/api/quick-squad/locked/preview`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        team_color_id: selectedTeam(),
                        locked_players: entries.map(
                            ({sp_id, grade, slot_index}) => ({
                                sp_id,
                                grade,
                                slot_index,
                            })
                        ),
                    }),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    typeof data.detail === "string"
                        ? data.detail
                        : "고정 선수 정보를 불러오지 못했습니다."
                );
            }

            if (token !== generation) {
                return;
            }

            preview = data.players || [];
            error = "";

            remap(true);
            persist();

        } catch (cause) {
            if (token !== generation) {
                return;
            }

            error = cause.message
                || "고정 선수 정보를 불러오지 못했습니다.";

            preview = [];
        }

        render();
        notify();
    }

    function changeSlot(spid, value) {
        const entry = entries.find(p => p.sp_id === spid);

        if (!entry) {
            return;
        }

        const index = value === "" ? null : Number(value);
        const slots = getSlots();
        const player = getPlayer(spid);

        if (
            index !== null
            && (
                !Number.isInteger(index)
                || !slots[index]
                || !player?.allowed_positions.includes(
                    slots[index].position
                )
                || entries.some(p =>
                    p.sp_id !== spid
                    && p.slot_index === index
                )
            )
        ) {
            error = "선택할 수 없는 포지션입니다.";
            render();
            return;
        }

        entry.slot_index = index;
        entry.slot_position = (
            index === null
                ? "__unassigned__"
                : slots[index].position
        );

        error = "";
        persist();
        render();
        notify();
    }

    root.addEventListener("change", event => {
        const select = event.target.closest(
            "[data-lock-slot]"
        );

        if (select) {
            changeSlot(
                Number(select.dataset.lockSlot),
                select.value
            );
        }
    });

    root.addEventListener("click", event => {
        const remove = event.target.closest(
            "[data-lock-remove]"
        );

        if (remove) {
            entries = entries.filter(
                p => p.sp_id
                    !== Number(remove.dataset.lockRemove)
            );

            preview = preview.filter(
                p => p.sp_id
                    !== Number(remove.dataset.lockRemove)
            );

            error = "";
            persist();
            render();
            notify();
        }

        if (
            event.target.closest(
                "[data-qs-lock-clear]"
            )
        ) {
            if (!confirm("고정 선수 전체를 해제할까요?")) {
                return;
            }

            entries = [];
            preview = [];
            error = "";

            persist();
            render();
            notify();
        }
    });

    window.addEventListener("storage", event => {
        if (event.key === STORAGE_KEY) {
            entries = readQuickSquadLocks();
            refresh();
        }
    });

    return {
        initialize: refresh,
        refresh,

        syncFormation() {
            remap(true);
            persist();
            render();
            notify();
        },

        updateBudget: render,

        preferredTeamColorId() {
            const ids = [
                ...new Set(
                    entries
                        .map(e => e.preferred_team_color_id)
                        .filter(Boolean)
                ),
            ];

            return ids.length === 1 ? ids[0] : null;
        },

        getPreview: () =>
            preview.map(p => ({...p})),

        async collect(budgetBp) {
            if (!entries.length) {
                return [];
            }

            await refresh();

            if (error) {
                throw new Error(error);
            }

            if (preview.length !== entries.length) {
                throw new Error(
                    "고정 선수 정보를 확인해주세요."
                );
            }

            if (
                entries.some(
                    e => e.slot_index === null
                )
            ) {
                throw new Error(
                    "모든 고정 선수의 포지션을 지정해주세요."
                );
            }

            if (
                preview.some(
                    p => !p.team_color_match
                )
            ) {
                throw new Error(
                    "팀컬러에 맞지 않는 고정 선수가 있습니다."
                );
            }

            if (
                total() > budgetBp
                || salary() > 310
            ) {
                throw new Error(
                    "고정 선수만으로 구단가치 또는 "
                    + "급여 제한을 초과합니다."
                );
            }

            return entries.map(
                ({sp_id, grade, slot_index}) => ({
                    sp_id,
                    grade,
                    slot_index,
                })
            );
        },
    };
}