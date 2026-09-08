import { apiBaseUrl } from "./config.js";

const ASSETS = "https://fco.dn.nexoncdn.co.kr/live/externalAssets/common";
const escape = value => String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));
const number = (value, fallback = "-") => Number.isFinite(Number(value)) && value !== null
    && value !== "" && value !== undefined ? Number(value) : fallback;

// The official card is layered artwork, not a single image. OVR/grade always come
// from the caller so that enhancement/adaptation/team-color settings stay intact.
export function createOfficialPlayerCardHtml(player) {
    const spId = number(player.sp_id, 0);
    const grade = Math.max(1, Math.min(13, number(player.grade, 1)));
    return `<div class="fco-player-card" data-fco-card="${spId}"
        role="img" aria-label="${escape(player.player_name)} · ${escape(player.position || "-")}
        · OVR ${number(player.ovr)} · +${grade}강 공식 선수 카드">
        <div class="fco-card-placeholder" aria-hidden="true"></div>
        <img class="fco-card-background" data-card-asset="background_url" alt="" hidden>
        <div class="playerCardWrap">
            <div class="fco-card-portrait-wrap"><img class="fco-card-portrait" alt=""
                src="${ASSETS}/playersAction/p${spId}.png" data-card-portrait="${spId}" loading="lazy"></div>
            <div class="fco-card-side">
                <strong class="ovr">${number(player.ovr)}</strong>
                <span class="position">${escape(player.position || "-")}</span>
                <span class="pay"><span>${number(player.salary)}</span></span>
            </div>
            <span class="fco-card-grade ${grade >= 8 ? "gold" : grade >= 5 ? "silver" : "bronze"}">${grade}</span>
            <div class="fco-card-bottom">
                <div class="nameWrap"><img class="season" data-card-asset="season_url" alt="" hidden>
                    <span class="name">${escape(player.player_name)}</span></div>
                <div class="fco-card-emblems">${["nation", "league", "team"].map(kind =>
                    `<img data-card-asset="${kind}_url" alt="" hidden>`).join("")}</div>
            </div>
        </div>
        <span class="fco-card-status" aria-hidden="true">카드 로딩 중</span>
    </div>`;
}

const requests = new Map();
const queue = [];
let active = 0;
function pump() {
    while (active < 4 && queue.length) {
        const { spId, resolve, reject } = queue.shift();
        active++;
        fetch(`${apiBaseUrl}/api/player-database/card/${spId}`, { signal: AbortSignal.timeout(30000) })
            .then(response => {
                if (!response.ok) throw new Error("Official card unavailable");
                return response.json();
            }).then(resolve, reject).finally(() => { active--; pump(); });
    }
}
function loadAssets(spId) {
    if (!requests.has(spId)) {
        const request = new Promise((resolve, reject) => { queue.push({ spId, resolve, reject }); });
        requests.set(spId, request);
        request.catch(() => requests.delete(spId));
        // Bound memory even during long browsing sessions.
        if (requests.size > 512) requests.delete(requests.keys().next().value);
        pump();
    }
    return requests.get(spId);
}
function safeAsset(value) {
    try {
        const url = new URL(value);
        return url.protocol === "https:" && ["ssl.nexon.com", "fco.dn.nexoncdn.co.kr", "fo4.dn.nexoncdn.co.kr"].includes(url.hostname) ? url.href : "";
    } catch { return ""; }
}
async function hydrate(card) {
    try {
        const data = await loadAssets(card.dataset.fcoCard);
        if (!card.isConnected) return;
        const wrapper = card.querySelector(".playerCardWrap");
        if (/^_[a-zA-Z0-9_-]+$/.test(data.season_class)) wrapper.classList.add(data.season_class);
        card.querySelectorAll("[data-card-asset]").forEach(img => {
            const url = safeAsset(data[img.dataset.cardAsset]);
            if (url) { img.src = url; img.hidden = false; }
        });
        const portrait = card.querySelector("[data-card-portrait]");
        const url = safeAsset(data.portrait_url);
        if (url && portrait.src !== url) {
            portrait.hidden = false;
            delete portrait.dataset.fallbackStep;
            portrait.src = url;
        }
        portrait.classList.toggle("head", data.portrait_kind === "head");
        card.classList.add("is-ready");
        card.querySelector(".fco-card-status").textContent = "";
    } catch {
        if (card.isConnected) card.querySelector(".fco-card-status").textContent = "공식 카드 로딩 실패";
    }
}

// One delegated handler also covers cards inserted by search/recommendation rerenders.
if (typeof document !== "undefined") {
    document.addEventListener("error", event => {
        const img = event.target;
        if (!(img instanceof HTMLImageElement)) return;
        if (img.matches("[data-card-portrait]")) {
            const spId = Number(img.dataset.cardPortrait);
            const sources = [`${ASSETS}/playersAction/p${spId}.png`,
                `${ASSETS}/players/p${spId % 1000000}.png`, `${ASSETS}/players/not_found.png`];
            let step = Number(img.dataset.fallbackStep || 0);
            while (step < sources.length && sources[step] === img.src) step++;
            img.dataset.fallbackStep = String(step + 1);
            if (step < sources.length) {
                img.classList.toggle("head", step >= 1);
                img.src = sources[step];
            } else img.hidden = true;
        } else if (img.matches("[data-card-asset]")) {
            img.hidden = true;
            if (img.dataset.cardAsset === "background_url") {
                const card = img.closest("[data-fco-card]");
                card.classList.remove("is-ready");
                card.querySelector(".fco-card-status").textContent = "공식 카드 배경 로딩 실패";
            }
        }
    }, true);
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
        if (entry.isIntersecting) { observer.unobserve(entry.target); hydrate(entry.target); }
    }), { rootMargin: "150px" });
    const observe = root => {
        if (root.nodeType !== 1) return;
        if (root.matches("[data-fco-card]")) observer.observe(root);
        root.querySelectorAll("[data-fco-card]").forEach(card => observer.observe(card));
    };
    new MutationObserver(records => records.forEach(record => {
        record.addedNodes.forEach(observe);
        record.removedNodes.forEach(root => {
            if (root.nodeType !== 1) return;
            if (root.matches("[data-fco-card]")) observer.unobserve(root);
            root.querySelectorAll("[data-fco-card]").forEach(card => observer.unobserve(card));
        });
    }))
        .observe(document.documentElement, { childList: true, subtree: true });
    observe(document.documentElement);
}
