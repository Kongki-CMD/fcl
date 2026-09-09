const STORAGE_KEY =
    "fcl.quick-squad.budget.v1";

const CORE_POSITIONS = new Set(`
    ST CF LS RS LF RF LW RW
    CAM LAM RAM CM LCM RCM
    CDM LDM RDM LM RM
    CB LCB RCB SW
`.trim().split(/\s+/));


function isCorePosition(position) {
    return CORE_POSITIONS.has(
        String(position || "")
            .trim()
            .toUpperCase()
    );
}


function normalizeStrength(value) {
    const number = Number(value);

    return (
        Number.isInteger(number)
        && number >= 100
        && number <= 300
    )
        ? number
        : 200;
}


function readPreferences() {
    try {
        const value = JSON.parse(
            localStorage.getItem(STORAGE_KEY) || "{}"
        );

        return {
            budget_mode:
                value.budget_mode === "balanced"
                    ? "balanced"
                    : "core",

            core_strength: normalizeStrength(
                value.core_strength
            ),
        };

    } catch {
        return {
            budget_mode: "core",
            core_strength: 200,
        };
    }
}


function savePreferences(value) {
    try {
        localStorage.setItem(
            STORAGE_KEY,
            JSON.stringify(value)
        );
    } catch {
        // 저장이 차단되어도 현재 선택은 동작한다.
    }
}


function buildBudgetPreview(
    slots,
    budgetBp,
    lockedPlayers,
    preferences,
) {
    const mode =
        preferences.budget_mode === "balanced"
            ? "balanced"
            : "core";

    const strength =
        mode === "core"
            ? normalizeStrength(
                preferences.core_strength
            )
            : 100;

    // Number(null)가 0이 되는 문제를 피하기 위해
    // 실제 정수 슬롯만 고정된 자리로 취급한다.
    const occupied = new Set(
        lockedPlayers
            .map(p => p.slot_index)
            .filter(i =>
                Number.isInteger(i)
                && i >= 0
                && i < slots.length
            )
    );

    const lockedCost = lockedPlayers.reduce(
        (sum, p) =>
            sum + Number(p.price || 0),
        0
    );

    const budget = Math.max(
        0,
        Math.round(Number(budgetBp) || 0)
    );

    const remaining = Math.max(
        0,
        budget - lockedCost
    );

    const indices = slots
        .map((slot, i) => i)
        .filter(i => !occupied.has(i));

    const coreIndices = indices.filter(
        i => isCorePosition(
            slots[i].position
        )
    );

    const otherIndices = indices.filter(
        i => !isCorePosition(
            slots[i].position
        )
    );

    const totalWeight =
        coreIndices.length * strength
        + otherIndices.length * 100;

    const coreTarget = totalWeight > 0
        ? Math.round(
            remaining
            * coreIndices.length
            * strength
            / totalWeight
        )
        : 0;

    return {
        mode,
        strength,
        remaining,
        coreCount: coreIndices.length,
        otherCount: otherIndices.length,
        coreTarget,
        otherTarget: remaining - coreTarget,
    };
}


export function createQuickSquadBudgetController({
    root,
    getSlots,
    getBudgetBp,
    getLockedPlayers,
    formatPrice,
    onPreferenceChange,
}) {
    let preferences = readPreferences();
    let actual = null;

    const $ = selector =>
        root.querySelector(selector);

    function refresh() {
        const plan = buildBudgetPreview(
            getSlots(),
            getBudgetBp(),
            getLockedPlayers(),
            preferences,
        );

        const hasSlots =
            plan.coreCount + plan.otherCount > 0;

        root.querySelectorAll(
            '[name="qs-budget-mode"]'
        ).forEach(input => {
            input.checked =
                input.value
                === preferences.budget_mode;
        });

        const range = $(
            "[data-qs-budget-strength]"
        );

        range.value =
            String(preferences.core_strength);

        range.disabled =
            preferences.budget_mode !== "core"
            || !hasSlots;

        $(
            "[data-qs-budget-strength-value]"
        ).textContent =
            `${
                (
                    preferences.core_strength / 100
                ).toFixed(1)
            }배`;

        $(
            "[data-qs-budget-strength-wrap]"
        ).hidden =
            preferences.budget_mode !== "core";

        $(
            "[data-qs-budget-core-count]"
        ).textContent =
            `${plan.coreCount}명`;

        $(
            "[data-qs-budget-other-count]"
        ).textContent =
            `${plan.otherCount}명`;

        $(
            "[data-qs-budget-core-target]"
        ).textContent =
            formatPrice(plan.coreTarget);

        $(
            "[data-qs-budget-other-target]"
        ).textContent =
            formatPrice(plan.otherTarget);

        const percent = plan.remaining > 0
            ? plan.coreTarget
              / plan.remaining * 100
            : 0;

        $(
            "[data-qs-budget-core-share]"
        ).textContent =
            `${percent.toFixed(1)}%`;

        $(
            "[data-qs-budget-explanation]"
        ).textContent =
            !hasSlots
                ? "모든 포지션이 고정되어 추가 추천 예산이 없습니다."
                : preferences.budget_mode === "core"
                    ? (
                        "코어 한 명당 기타 포지션의 "
                        + `${
                            (
                                plan.strength / 100
                            ).toFixed(1)
                        }배를 목표로 배분합니다.`
                    )
                    : (
                        "남은 선수의 자리별 목표 예산을 "
                        + "동일하게 배분합니다."
                    );

        if (actual) {
            const core = Number(
                actual.core_actual || 0
            );

            const other = Number(
                actual.other_actual || 0
            );

            const spent = core + other;

            const actualShare = spent > 0
                ? core / spent * 100
                : 0;

            $(
                "[data-qs-budget-actual]"
            ).hidden = false;

            $(
                "[data-qs-budget-actual-core]"
            ).textContent =
                formatPrice(core);

            $(
                "[data-qs-budget-actual-other]"
            ).textContent =
                formatPrice(other);

            $(
                "[data-qs-budget-actual-share]"
            ).textContent =
                `${actualShare.toFixed(1)}%`;

        } else {
            $(
                "[data-qs-budget-actual]"
            ).hidden = true;
        }
    }


    function changed() {
        actual = null;

        savePreferences(preferences);
        refresh();

        onPreferenceChange?.();
    }


    root.addEventListener(
        "change",
        event => {
            const input = event.target.closest(
                '[name="qs-budget-mode"]'
            );

            if (!input) {
                return;
            }

            preferences.budget_mode =
                input.value === "balanced"
                    ? "balanced"
                    : "core";

            changed();
        }
    );


    root.addEventListener(
        "input",
        event => {
            if (
                !event.target.matches(
                    "[data-qs-budget-strength]"
                )
            ) {
                return;
            }

            preferences.core_strength =
                normalizeStrength(
                    event.target.value
                );

            changed();
        }
    );


    refresh();

    return {
        refresh,

        getPreferences() {
            return {...preferences};
        },

        showResult(allocation) {
            actual = allocation || null;
            refresh();
        },

        clearResult() {
            actual = null;
            refresh();
        },
    };
}