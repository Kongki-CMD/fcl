// Quick Squad player detail controller
export function createQuickSquadDetailModal({
    apiBaseUrl,
    modal,
    body,
    saveButton,
    formatPrice,
    onSave,
}) {
    const titleWrap = modal.querySelector(".quick-squad-player-modal-title-wrap");
    if (titleWrap) {
        titleWrap.innerHTML = `
            <h2 id="quick-squad-player-modal-title" class="quick-squad-player-modal-title">선수 상세 정보</h2>
            <p class="quick-squad-player-modal-kicker">퀵 스쿼드 추천 선수 상세 보기</p>`;
    }
    const BONUS = {
        1: 0, 2: 1, 3: 2, 4: 4, 5: 6, 6: 8, 7: 11,
        8: 15, 9: 17, 10: 19, 11: 21, 12: 24, 13: 27,
    };
    const cache = new Map();
    let state = null;
    let generation = 0;
    let previousFocus = null;
    let previousOverflow = "";
    let saving = false;

    const saveStatus = modal.querySelector(
        "[data-qs-save-status]"
    );

    const $ = (selector) => body.querySelector(selector);
    const all = (selector) => [...body.querySelectorAll(selector)];
    const escape = (value) => String(value ?? "")
        .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    const number = (value, fallback = 0) => {
        if (value === null || value === undefined || value === "") return fallback;
        const n = Number(value);
        return Number.isFinite(n) ? n : fallback;
    };
    const imageUrl = (value) => {
        if (!value) return "";
        try {
            const url = new URL(String(value), window.location.href);
            return ["http:", "https:"].includes(url.protocol) ? url.href : "";
        } catch {
            return "";
        }
    };
    const priceText = (value) => {
        const price = number(value);
        return price > 0 ? formatPrice(price) : "시세 정보 없음";
    };
    const statClass = (value) => {
        if (value >= 160) return "stat-color-mint";
        if (value >= 140) return "stat-color-gold";
        if (value >= 130) return "stat-color-red";
        if (value >= 120) return "stat-color-pink";
        if (value >= 100) return "stat-color-blue";
        return "stat-color-gray";
    };
const footHtml = (
    label,
    value,
    otherValue
) => {
    const rating = Math.max(
        0,
        Math.min(
            5,
            number(value)
        )
    );

    const otherRating = Math.max(
        0,
        Math.min(
            5,
            number(otherValue)
        )
    );

    const isMain =
        rating > 0
        &&
        rating >= otherRating;

    const side =
        label === "L"
            ? "left"
            : "right";

    const sideName =
        label === "L"
            ? "왼발"
            : "오른발";

    return `
        <span
            class="player-database-foot player-database-foot-${side} ${rating === 5 ? "active" : "inactive"}"
            title="${sideName} ${rating}${isMain ? " · 주발" : ""}"
            aria-label="${sideName} ${rating}${isMain ? ", 주발" : ""}"
        >
            ${
                isMain
                    ? `
                        <span
                            class="player-database-foot-star"
                            aria-hidden="true"
                        >★</span>
                    `
                    : ""
            }

            <span class="player-database-foot-value">
                ${label}${rating}
            </span>
        </span>
    `;
};
    const gradeBadge = (grade) => {
        const n = Math.max(1, Math.min(13, number(grade, 1)));
        return `<span class="player-database-card-grade grade-${n} quick-squad-detail-grade-badge">+${n}</span>`;
    };

    async function fetchJson(path) {
        const response = await fetch(`${apiBaseUrl}${path}`);
        const text = await response.text();
        let data;
        try {
            data = text ? JSON.parse(text) : null;
        } catch {
            throw new Error(`서버 응답을 읽을 수 없습니다. (${response.status})`);
        }
        if (!response.ok) {
            throw new Error(typeof data?.detail === "string"
                ? data.detail : `조회에 실패했습니다. (${response.status})`);
        }
        if (!data || typeof data !== "object") {
            throw new Error("서버에서 올바른 데이터를 받지 못했습니다.");
        }
        return data;
    }

    function cached(key, loader) {
        if (!cache.has(key)) {
            const promise = Promise.resolve().then(loader);
            cache.set(key, promise);
            promise.catch(() => {
                if (cache.get(key) === promise) cache.delete(key);
            });
        }
        return cache.get(key);
    }

    function calculate() {
        const bonus = BONUS[state.grade] + (state.adaptation === 5 ? 4 : 0) + state.teamColor;
        const player = state.detail;
        const stats = Object.fromEntries(
            Object.entries(player.stats ?? {}).map(([name, value]) => [
                name, value === null || value === undefined ? null : number(value) + bonus,
            ])
        );
        return { bonus, ovr: number(player.base_ovr) + bonus, stats };
    }

    function selectedPrice() {
        const item = state?.prices?.find(
            row => number(row.grade) === state.grade
        );

        const price = number(item?.price);

        return Number.isFinite(price) && price > 0
            ? price
            : null;
    }

    function syncSaveButton() {
        if (!saveButton) return;

        const canSave = (
            Boolean(state?.detail)
            && state?.priceStatus === "ready"
            && selectedPrice() !== null
            && !saving
        );

        saveButton.disabled = !canSave;

        if (!saving) {
            saveButton.textContent = "저장";
        }
    }

    function renderPrice() {
        if (!state || !$('[data-qs-market]')) return;
        const holder = $('[data-qs-market]');
        const price = selectedPrice();
        let caption = "FC Online DataCenter · 실제 거래 가능 여부는 게임 내 확인";
        let label;
        if (state.priceStatus === "loading") {
            label = "시세 조회 중...";
        } else if (state.priceStatus === "error") {
            label = state.grade === number(state.summary.grade, 1) && number(state.summary.price) > 0
                ? priceText(state.summary.price) : "시세 조회 실패";
            caption = `${state.priceError} · 추천 당시 가격은 현재 시세가 아닐 수 있습니다.`;
        } else {
            label = priceText(price);
            if (price) caption = `${number(price).toLocaleString("ko-KR")} BP · ${caption}`;
            else caption = "선택한 강화등급의 시세가 제공되지 않습니다.";
        }
        holder.innerHTML = `
            <div class="quick-squad-detail-market-heading">
                ${gradeBadge(state.grade)}
                <span>선택 강화 시세</span>
            </div>
            <div class="quick-squad-player-market-price">${escape(label)}</div>
            <div class="quick-squad-player-market-caption">${escape(caption)}</div>
        `;

        syncSaveButton();
    
    }

    function renderTraits() {
        if (!state || !$('[data-qs-traits]')) return;
        const holder = $('[data-qs-traits]');
        if (state.traitStatus === "loading") {
            holder.textContent = "공식 특성 아이콘 불러오는 중...";
            return;
        }
        const items = state.traitItems;
        if (items?.length) {
            holder.innerHTML = items.map((trait) => {
                const name = escape(trait.name ?? "");
                const src = imageUrl(trait.image_url);
                return `<div class="quick-squad-player-trait-item" title="${name}">
                    ${src ? `<img src="${escape(src)}" alt="" loading="lazy">` : ""}
                    <span>${name}</span>
                </div>`;
            }).join("");
            return;
        }
        const fallback = Array.isArray(state.detail?.traits) ? state.detail.traits : [];
        holder.innerHTML = fallback.length
            ? fallback.map((name) => `<div class="quick-squad-player-trait-item"><span>${escape(name)}</span></div>`).join("")
            : '<span class="quick-squad-detail-muted">특성 없음</span>';
        if (state.traitStatus === "error" && fallback.length) {
            holder.insertAdjacentHTML("beforeend", '<small class="quick-squad-detail-muted">공식 아이콘을 불러오지 못해 DB 특성명을 표시합니다.</small>');
        }
    }

    function refreshValues() {
        if (!state?.detail) return;
        const { bonus, ovr, stats } = calculate();
        const ovrElement = $('[data-qs-ovr]');
        if (ovrElement) ovrElement.textContent = ovr;
        const cardOvr = $('[data-qs-card-ovr]');
        if (cardOvr) cardOvr.textContent = ovr;
        const bonusElement = $('[data-qs-bonus]');
        if (bonusElement) bonusElement.textContent = `강화 +${BONUS[state.grade]} · 적응도 +${state.adaptation === 5 ? 4 : 0} · 팀컬러 +${state.teamColor} = 총 +${bonus}`;
        all('[data-qs-stat]').forEach((element) => {
            const value = stats[element.dataset.qsStat];
            element.textContent = value === null || value === undefined ? "-" : value;
            element.className = `qsd-stat-value ${value === null || value === undefined ? "" : statClass(value)}`;
        });
        all('[data-qs-grade]').forEach((button) => {
            const selected = number(button.dataset.qsGrade) === state.grade;
            button.classList.toggle("selected", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
        all('[data-qs-adaptation]').forEach((button) => {
            const selected = number(button.dataset.qsAdaptation) === state.adaptation;
            button.classList.toggle("is-active", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
        const select = $('[data-qs-team-bonus]');
        if (select) select.value = String(state.teamColor);
        renderPrice();
    }


    function renderDetail() {
        const player = state.detail;
        const name = escape(player.player_name);
        const position = escape(player.position || "-");
        const slot = escape(state.summary.slot_position || "");
        const photo = imageUrl(player.image_url);
const seasonId = [
    player.season_id,
    Math.floor(number(player.sp_id) / 1_000_000),
]
    .map(value => Number(value))
    .find(value =>
        Number.isSafeInteger(value)
        && value > 0
    ) ?? null;

        const season = seasonId === null
            ? ""
            : `${apiBaseUrl}/api/fconline/metadata/seasons/${seasonId}/image`;
        const frame = new URL("../assets/quick-squad-card-frame.svg", import.meta.url).href;
        const stats = Object.entries(player.stats ?? {});
        const teamNames = (player.team_colors ?? []).map(t => t.team_name).filter(Boolean);
        const flags = {
            "대한민국":"🇰🇷","한국":"🇰🇷","브라질":"🇧🇷","아르헨티나":"🇦🇷",
            "독일":"🇩🇪","프랑스":"🇫🇷","스페인":"🇪🇸","잉글랜드":"🏴",
            "포르투갈":"🇵🇹","이탈리아":"🇮🇹","네덜란드":"🇳🇱","벨기에":"🇧🇪",
            "우루과이":"🇺🇾","크로아티아":"🇭🇷","일본":"🇯🇵","미국":"🇺🇸"
        };
        const flag = flags[player.nation_name] || "⚽";
        const info = [
            player.nation_name || "-",
            player.height != null ? `${player.height}cm` : "-",
            player.weight != null ? `${player.weight}kg` : "-",
            player.skill_moves != null ? `개인기 ${player.skill_moves}` : ""
        ].filter(Boolean).map(escape).join(" · ");
        const groups = new Set(["속력","짧은 패스","드리블","몸싸움","헤더","GK 다이빙"]);
        const officialUrl = `https://fconline.nexon.com/datacenter/PlayerInfo?spid=${number(player.sp_id)}`;

        body.innerHTML = `
            <div class="qsd-layout">
                <section class="qsd-column qsd-left" aria-label="선수 카드 및 기본 정보">
                    <div class="qsd-card">
                        <img class="qsd-card-art" src="${escape(frame)}" alt="">
                        <div class="qsd-card-photo">
                            ${photo ? `<img src="${escape(photo)}" alt="${name}" loading="eager">`
                                : '<span class="qsd-no-image">NO IMAGE</span>'}
                        </div>
                        <div class="qsd-card-top">
                            ${season
                                ? `<img src="${escape(season)}" alt="" loading="lazy">`
                                : ""
                            }
                        </div>
                        <div class="qsd-card-rating">
                            <strong data-qs-card-ovr></strong>
                            <span class="qsd-card-pos">${position}</span>
                        </div>
                        <div class="qsd-card-namebar">
                            <span class="qsd-flag" aria-label="${escape(player.nation_name || '국적 정보 없음')}">${flag}</span>
                            <strong>${name}</strong>
                            <span class="qsd-card-salary" title="급여">${number(player.salary)}</span>
                        </div>
                    </div>

                    <div class="qsd-identity">
                        <span class="qsd-identity-pos">${position}</span>
                        <strong>${name}</strong>
                    </div>
                    <div class="qsd-salary-line">급여 <span class="qsd-salary-shield">${number(player.salary)}</span></div>
                    <div class="qsd-foot-line">
                        <span>주로 사용하는 발</span>
                        <div class="qsd-feet">
                            ${footHtml(
                                "L",
                                player.left_foot,
                                player.right_foot
                            )}

                            ${footHtml(
                                "R",
                                player.right_foot,
                                player.left_foot
                            )}
                        </div>
                    </div>
                    <div class="qsd-details-line">${info}</div>
                    ${slot && slot !== position
                        ? `<p class="qsd-position-note">추천 배치 ${slot} · DB 대표 포지션 ${position}</p>` : ""}
                    <div class="qsd-action-row">
                        <a href="${escape(officialUrl)}" target="_blank" rel="noopener noreferrer" class="qsd-small-action">
                            <span aria-hidden="true">↗</span> 공식 선수 정보
                        </a>
                    </div>
                    <div class="qsd-team-list">
                        <span class="qsd-mini-label">소속 팀컬러</span>
                        <p>${teamNames.length ? teamNames.map(escape).join(" · ") : "정보 없음"}</p>
                    </div>
                    <p class="qsd-source-note">능력치는 DB 대표 포지션 기준입니다. 실제 다른 포지션의 OVR과 팀컬러 발동 여부는 게임에서 확인하세요.</p>
                </section>

                <section class="qsd-column qsd-center" aria-label="전체 능력치">
                    <div class="qsd-heading">전체 능력치</div>
                    <div class="qsd-stat-scroll">
                        ${stats.map(([label], i) => `
                            <div class="qsd-stat-row ${i && groups.has(label) ? "qsd-group-start" : ""}">
                                <span>${escape(label)}</span>
                                <strong class="qsd-stat-value" data-qs-stat="${escape(label)}"></strong>
                            </div>
                        `).join("")}
                    </div>
                </section>

                <section class="qsd-column qsd-right" aria-label="카드 설정 및 시세">
                    <div class="qsd-heading">카드 설정</div>
                    <div class="qsd-settings-scroll">
                        <div class="qsd-setting-panel">
                            <label class="qsd-setting-label">강화</label>
                            <div class="qsd-grade-grid">
                                ${Array.from({length:13},(_,i)=>{
                                    const grade=i+1;
                                    return `<button type="button" class="player-database-card-grade grade-${grade}"
                                        data-qs-grade="${grade}" aria-label="${grade}강" title="${grade}강">+${grade}</button>`;
                                }).join("")}
                            </div>
                        </div>
                        <div class="qsd-setting-panel">
                            <label class="qsd-setting-label">적응도</label>
                            <div class="qsd-adaptation-row">
                                ${[1,5].map(value=>`<button type="button" class="quick-squad-player-setting-chip"
                                    data-qs-adaptation="${value}">${value}</button>`).join("")}
                            </div>
                        </div>
                        <div class="qsd-setting-panel qsd-team-panel">
                            <label class="qsd-setting-label" for="quick-squad-detail-team-bonus">팀컬러</label>
                            <select id="quick-squad-detail-team-bonus" class="qsd-team-select" data-qs-team-bonus>
                                ${Array.from({length:10},(_,value)=>`<option value="${value}">+${value} (전체 능력치 +${value})</option>`).join("")}
                            </select>
                        </div>
                        <div class="qsd-market-section">
                            <div class="qsd-section-heading"><span>이적시장 시세</span><small>선택 강화 기준</small></div>
                            <div class="quick-squad-player-market-box" data-qs-market aria-live="polite"></div>
                        </div>
                        <div class="qsd-traits-section">
                            <div class="qsd-section-heading"><span>특성</span></div>
                            <div class="quick-squad-player-traits-list" data-qs-traits aria-live="polite"></div>
                        </div>
                        <p class="qsd-calculation-note" data-qs-bonus></p>
                    </div>
                </section>
            </div>`;
        const heading = modal.querySelector("#quick-squad-player-modal-title");
        if (heading) heading.textContent = "선수 상세 정보";
        refreshValues();
        renderTraits();
    }

    function setStatus(message, retry = false) {
        body.innerHTML = `<div class="quick-squad-player-detail-panel quick-squad-detail-status" role="status">
            <p>${escape(message)}</p>
            ${retry ? '<button type="button" class="quick-squad-player-setting-chip" data-qs-retry>다시 시도</button>' : ""}
        </div>`;
    }

    async function open(summary) {
        if (!summary?.sp_id) return;
        const token = ++generation;
        if (modal.classList.contains("hidden")) {
            previousFocus = document.activeElement;
            previousOverflow = document.body.style.overflow;
        }
        state = {
            summary: { ...summary },
            detail: null,

            grade: Math.max(
                1,
                Math.min(13, number(summary.grade, 1))
            ),

            adaptation:
                number(summary.adaptation, 1) === 5
                    ? 5
                    : 1,

            teamColor: Math.max(
                0,
                Math.min(
                    9,
                    number(summary.team_color_bonus, 0)
                )
            ),

            prices: null,
            priceStatus: "loading",
            priceError: "",

            traitItems: null,
            traitStatus: "loading",
        };

        saving = false;

        if (saveStatus) {
            saveStatus.textContent = "";
        }

        syncSaveButton();
        modal.classList.remove("hidden");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        setStatus("선수 상세 정보를 불러오는 중...");
        modal.querySelector(".quick-squad-player-modal-close")?.focus();

        const spId = Number(summary.sp_id);
        try {
            const detail = await cached(`detail:${spId}`, () =>
                fetchJson(`/api/quick-squad/player-detail/${spId}`));
            if (token !== generation || !state) return;
            state.detail = detail;
            renderDetail();
        } catch (error) {
            if (token !== generation) return;
            setStatus(error.message || "선수 정보를 불러오지 못했습니다.", true);
            return;
        }

        // 상세창을 새로 열 때마다 현재 시세를 확인한다.
        const pricesPromise = fetchJson(
            `/api/player-database/price/${spId}`
        );
        const traitsPromise = cached(`traits:${spId}`, () =>
            fetchJson(`/api/player-database/traits/${spId}`));

        pricesPromise.then((data) => {
            if (token !== generation || !state) return;
            state.prices = Array.isArray(data.prices) ? data.prices : [];
            state.priceStatus = "ready";
            renderPrice();
        }).catch((error) => {
            if (token !== generation || !state) return;
            state.priceStatus = "error";
            state.priceError = error.message || "시세를 불러오지 못했습니다.";
            renderPrice();
        });

        traitsPromise.then((data) => {
            if (token !== generation || !state) return;
            state.traitItems = Array.isArray(data.traits) ? data.traits : [];
            state.traitStatus = "ready";
            renderTraits();
        }).catch(() => {
            if (token !== generation || !state) return;
            state.traitStatus = "error";
            renderTraits();
        });
    }

    function close() {
        if (modal.classList.contains("hidden")) return;
        ++generation;
        modal.classList.add("hidden");
        modal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = previousOverflow;
        state = null;
        if (previousFocus?.isConnected) previousFocus.focus();
        previousFocus = null;
    }

    body.addEventListener("click", (event) => {
        const gradeButton = event.target.closest("[data-qs-grade]");
        if (gradeButton && body.contains(gradeButton) && state?.detail) {
            state.grade = number(gradeButton.dataset.qsGrade, 1);
            refreshValues();
            return;
        }
        const adaptationButton = event.target.closest("[data-qs-adaptation]");
        if (adaptationButton && body.contains(adaptationButton) && state?.detail) {
            state.adaptation = number(adaptationButton.dataset.qsAdaptation, 1);
            refreshValues();
            return;
        }
        const retryButton = event.target.closest("[data-qs-retry]");
        if (retryButton && body.contains(retryButton) && state?.summary) {
            open(state.summary);
        }
    });

    body.addEventListener("change", (event) => {
        if (!event.target.matches("[data-qs-team-bonus]") || !state?.detail) return;
        state.teamColor = Math.max(0, Math.min(9, number(event.target.value)));
        refreshValues();
    });

    modal.addEventListener("keydown", (event) => {
        if (event.key !== "Tab" || modal.classList.contains("hidden")) return;
        const focusable = [...modal.querySelectorAll(
            'button:not([disabled]):not([hidden]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'
        )].filter((element) => element.getClientRects().length > 0);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    if (saveButton) {
        saveButton.addEventListener("click", async () => {
            if (
                saving
                || !state?.detail
                || state.priceStatus !== "ready"
            ) {
                return;
            }

            const price = selectedPrice();

            if (price === null) {
                if (saveStatus) {
                    saveStatus.textContent =
                        "선택한 강화등급의 시세를 확인해주세요.";
                }
                return;
            }

            const token = generation;
            const { bonus, ovr } = calculate();

            const summary = { ...state.summary };

            const selection = {
                grade: state.grade,
                adaptation: state.adaptation,
                team_color_bonus: state.teamColor,
                ability_bonus: bonus,
                base_ovr: number(state.detail.base_ovr),
                ovr,
                price,
                price_checked_at: new Date().toISOString(),
            };

            saving = true;
            saveButton.disabled = true;
            saveButton.textContent = "저장 중...";

            if (saveStatus) {
                saveStatus.textContent = "";
            }

            try {
                if (typeof onSave !== "function") {
                    throw new Error(
                        "스쿼드 저장 기능이 연결되지 않았습니다."
                    );
                }

                await onSave(summary, selection);

                if (token === generation) {
                    close();
                }

            } catch (error) {
                if (saveStatus) {
                    saveStatus.textContent =
                        error.message
                        || "선수 설정 저장에 실패했습니다.";
                }

            } finally {
                saving = false;
                syncSaveButton();
            }
        });
    }

    return { open, close };
}
