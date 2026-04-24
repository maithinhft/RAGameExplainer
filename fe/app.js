/* ═══════════════════════════════════════════════════════════
   RAGameExplainer — Frontend Application
   ═══════════════════════════════════════════════════════════ */

const API_BASE = "https://fe9f-34-125-12-177.ngrok-free.app";

// ─── API Helper (bypass ngrok warning page) ───
function apiFetch(path, options = {}) {
    const headers = {
        "ngrok-skip-browser-warning": "true",
        ...(options.headers || {}),
    };
    return fetch(`${API_BASE}${path}`, { ...options, headers });
}

// ─── State ───
const state = {
    champions: [],
    items: [],
    selectedChampion: null,
    selectedItems: [null, null, null, null, null, null],
    activeSlot: null,
    isLoading: false,
};

// ─── DOM Elements ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const chatMessages = $("#chatMessages");
const chatInput = $("#chatInput");
const sendBtn = $("#sendBtn");
const championGrid = $("#championGrid");
const itemGrid = $("#itemGrid");
const champSearch = $("#champSearch");
const itemSearch = $("#itemSearch");
const selectedChampionEl = $("#selectedChampion");
const itemSlots = $("#itemSlots");
const askBuildBtn = $("#askBuildBtn");
const buildResponse = $("#buildResponse");

// ═══════════════════════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════════════════════

$$(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        $$(".nav-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        $$(".panel").forEach((p) => p.classList.remove("active"));
        $(`#${btn.dataset.panel}Panel`).classList.add("active");
    });
});

// ═══════════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════════

function addMessage(text, type = "bot") {
    const div = document.createElement("div");
    div.className = `message ${type}`;
    const avatar = type === "bot" ? "🤖" : "⚔";
    div.innerHTML = `
    <div class="msg-avatar">${avatar}</div>
    <div class="msg-bubble">${formatAnswer(text)}</div>
  `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
}

function addTypingIndicator() {
    const div = document.createElement("div");
    div.className = "message bot";
    div.id = "typingMsg";
    div.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const el = $("#typingMsg");
    if (el) el.remove();
}

function formatAnswer(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/`(.*?)`/g, "<code>$1</code>")
        .replace(/\n/g, "<br>");
}

async function sendChat() {
    const question = chatInput.value.trim();
    if (!question || state.isLoading) return;

    state.isLoading = true;
    sendBtn.disabled = true;
    chatInput.value = "";

    addMessage(question, "user");
    addTypingIndicator();

    try {
        const res = await apiFetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, top_k: 5, show_context: false }),
        });

        removeTypingIndicator();

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            addMessage(`❌ Lỗi: ${err.detail || res.statusText}`);
            return;
        }

        const data = await res.json();
        addMessage(data.answer);
    } catch (e) {
        removeTypingIndicator();
        addMessage(`❌ Không thể kết nối server: ${e.message}`);
    } finally {
        state.isLoading = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }
}

sendBtn.addEventListener("click", sendChat);
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendChat();
    }
});

// ═══════════════════════════════════════════════════════════
// CHAMPION SELECTOR
// ═══════════════════════════════════════════════════════════

async function loadChampions() {
    try {
        const res = await apiFetch("/champions");
        const data = await res.json();
        state.champions = data.champions || [];
        renderChampions();
    } catch (e) {
        console.error("Failed to load champions:", e);
        championGrid.innerHTML = `<p style="grid-column:1/-1;color:var(--text-dim);">Không thể tải danh sách tướng</p>`;
    }
}

function renderChampions(filter = "") {
    const filtered = state.champions.filter(
        (c) =>
            c.name.toLowerCase().includes(filter.toLowerCase()) ||
            c.id.toLowerCase().includes(filter.toLowerCase())
    );

    championGrid.innerHTML = filtered
        .map(
            (c) => `
    <div class="champ-card ${state.selectedChampion?.id === c.id ? "selected" : ""}" 
         data-id="${c.id}" 
         title="${c.name} — ${c.title}">
      <img src="${c.image}" alt="${c.name}" loading="lazy" 
           onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2260%22 height=%2260%22><rect fill=%22%23111827%22 width=%2260%22 height=%2260%22/><text x=%2230%22 y=%2235%22 text-anchor=%22middle%22 fill=%22%23a09b8c%22 font-size=%2216%22>${c.name[0]}</text></svg>'">
      <span class="champ-name">${c.name}</span>
    </div>
  `
        )
        .join("");

    $$(".champ-card").forEach((card) => {
        card.addEventListener("click", () => selectChampion(card.dataset.id));
    });
}

function selectChampion(champId) {
    state.selectedChampion = state.champions.find((c) => c.id === champId);
    if (!state.selectedChampion) return;

    // Update grid visuals
    $$(".champ-card").forEach((c) => c.classList.remove("selected"));
    const card = document.querySelector(`.champ-card[data-id="${champId}"]`);
    if (card) card.classList.add("selected");

    // Update display
    const champ = state.selectedChampion;
    selectedChampionEl.innerHTML = `
    <img src="${champ.image}" alt="${champ.name}" 
         onerror="this.style.display='none'">
    <div class="info">
      <h3>${champ.name}</h3>
      <p>${champ.title} — ${(champ.tags || []).join(", ")}</p>
    </div>
  `;

    updateAskBuildBtn();
}

champSearch.addEventListener("input", (e) => renderChampions(e.target.value));

// ═══════════════════════════════════════════════════════════
// ITEM BUILDER
// ═══════════════════════════════════════════════════════════

async function loadItems() {
    try {
        const res = await apiFetch("/items");
        const data = await res.json();
        state.items = data.items || [];
        renderItems();
    } catch (e) {
        console.error("Failed to load items:", e);
        itemGrid.innerHTML = `<p style="color:var(--text-dim);">Không thể tải trang bị</p>`;
    }
}

function renderItems(filter = "", tagFilter = "") {
    const filtered = state.items.filter((item) => {
        const matchName = item.name.toLowerCase().includes(filter.toLowerCase());
        const matchTag = !tagFilter || (item.tags && item.tags.includes(tagFilter));
        return matchName && matchTag;
    });

    itemGrid.innerHTML = filtered
        .map(
            (item) => `
    <div class="item-card" data-id="${item.id}" title="${item.name}">
      <img src="${item.image}" alt="${item.name}" loading="lazy"
           onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2248%22 height=%2248%22><rect fill=%22%23111827%22 width=%2248%22 height=%2248%22/><text x=%2224%22 y=%2230%22 text-anchor=%22middle%22 fill=%22%23a09b8c%22 font-size=%2212%22>?</text></svg>'">
      <div class="item-tooltip">
        ${item.name} — <span class="item-gold">${item.gold}g</span>
      </div>
    </div>
  `
        )
        .join("");

    $$(".item-card").forEach((card) => {
        card.addEventListener("click", () => addItemToBuild(card.dataset.id));
    });
}

function addItemToBuild(itemId) {
    const item = state.items.find((i) => i.id === itemId);
    if (!item) return;

    // Find first empty slot
    const emptyIdx = state.selectedItems.findIndex((s) => s === null);
    if (emptyIdx === -1) return; // All slots full

    state.selectedItems[emptyIdx] = item;
    updateItemSlots();
    updateAskBuildBtn();
}

function removeItemFromBuild(slotIdx) {
    state.selectedItems[slotIdx] = null;
    updateItemSlots();
    updateAskBuildBtn();
}

function updateItemSlots() {
    const slots = $$(".item-slot");
    slots.forEach((slot, idx) => {
        const item = state.selectedItems[idx];
        if (item) {
            slot.classList.add("filled");
            slot.innerHTML = `
        <img src="${item.image}" alt="${item.name}" title="${item.name} (${item.gold}g)">
        <button class="remove-item" title="Xóa">&times;</button>
      `;
            slot.querySelector(".remove-item").addEventListener("click", (e) => {
                e.stopPropagation();
                removeItemFromBuild(idx);
            });
        } else {
            slot.classList.remove("filled");
            slot.innerHTML = "+";
        }
    });
}

function updateAskBuildBtn() {
    const hasChamp = state.selectedChampion !== null;
    const hasItems = state.selectedItems.some((s) => s !== null);
    askBuildBtn.disabled = !(hasChamp && hasItems);
}

// Item search
itemSearch.addEventListener("input", (e) => {
    const activeTag = $(".tag-btn.active")?.dataset.tag || "";
    renderItems(e.target.value, activeTag);
});

// Tag filter
$$(".tag-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        $$(".tag-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderItems(itemSearch.value, btn.dataset.tag);
    });
});

// ═══════════════════════════════════════════════════════════
// ASK BUILD
// ═══════════════════════════════════════════════════════════

askBuildBtn.addEventListener("click", async () => {
    if (!state.selectedChampion || state.isLoading) return;

    const champ = state.selectedChampion;
    const items = state.selectedItems.filter((i) => i !== null);

    if (items.length === 0) return;

    const itemNames = items.map((i) => i.name).join(", ");
    const totalGold = items.reduce((sum, i) => sum + (i.gold || 0), 0);

    const question = `Đánh giá build sau cho tướng ${champ.name} (${champ.tags?.join("/")}): ${itemNames}. Tổng giá: ${totalGold} vàng. Build này có hợp lý không? Có gợi ý thay đổi gì không?`;

    state.isLoading = true;
    askBuildBtn.disabled = true;
    askBuildBtn.innerHTML = '<span class="spinner"></span> Đang hỏi AI...';

    buildResponse.classList.add("visible");
    buildResponse.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

    try {
        const res = await apiFetch("/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question, top_k: 5 }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            buildResponse.innerHTML = `❌ Lỗi: ${err.detail || res.statusText}`;
            return;
        }

        const data = await res.json();
        buildResponse.innerHTML = formatAnswer(data.answer);
    } catch (e) {
        buildResponse.innerHTML = `❌ Không thể kết nối: ${e.message}`;
    } finally {
        state.isLoading = false;
        askBuildBtn.disabled = false;
        askBuildBtn.innerHTML = "🤖 Hỏi AI đánh giá build này";
        updateAskBuildBtn();
    }
});

// ═══════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
    loadChampions();
    loadItems();
    chatInput.focus();
});
