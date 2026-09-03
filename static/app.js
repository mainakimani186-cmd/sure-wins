
const cards = document.getElementById("cards");
const count = document.getElementById("count");
const updated = document.getElementById("updated");
const search = document.getElementById("search");
const refreshBtn = document.getElementById("refresh");
const filters = document.querySelectorAll("#filters button");

const modal = document.getElementById("modal");
const detail = document.getElementById("detail");
const closeModal = document.querySelector(".close");

let allMatches = [];
let currentTier = "ALL";


async function loadMatches() {
    cards.innerHTML = '<p style="color:#aaa;padding:20px;">Loading matches...</p>';

    try {
        const response = await fetch("/api/matches?ts=" + Date.now());

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        allMatches = data.matches || [];

        count.textContent = allMatches.length;

        if (data.updated) {
            updated.textContent = new Date(
                data.updated
            ).toLocaleTimeString();
        }

        renderMatches();

    } catch (error) {
        console.error("Failed to load matches:", error);

        cards.innerHTML = `
            <div style="padding:20px;color:#ff6b6b;">
                Failed to load matches.<br>
                <small>${error.message}</small>
            </div>
        `;
    }
}


function renderMatches() {
    const query = search.value.toLowerCase();

    const filtered = allMatches.filter(match => {
        const matchesTier =
            currentTier === "ALL" || match.tier === currentTier;

        const matchesSearch =
            match.home.toLowerCase().includes(query) ||
            match.away.toLowerCase().includes(query);

        return matchesTier && matchesSearch;
    });

    if (filtered.length === 0) {
        cards.innerHTML = `
            <div style="padding:20px;color:#aaa;">
                No matches found.
            </div>
        `;
        return;
    }

    cards.innerHTML = filtered.map(match => `
        <article class="card match-card" data-id="${match.id}">
            <div class="card-top">
                <span class="tier ${match.tier.replace(" ", "-").toLowerCase()}">
                    ${match.tier}
                </span>

                <span class="confidence">
                    ${match.confidence}%
                </span>
            </div>

            <div class="teams">
                <div>${match.home}</div>
                <div class="vs">VS</div>
                <div>${match.away}</div>
            </div>

            <div class="card-footer">
                <span>${match.region || "Global"}</span>
                <span>${match.match_date || ""}</span>
            </div>

            <p class="analysis">
                ${match.analysis || ""}
            </p>

            <div class="view-details">
                Tap for full analysis →
            </div>
        </article>
    `).join("");

    document.querySelectorAll(".match-card").forEach(card => {
        card.addEventListener("click", () => {
            openMatch(card.dataset.id);
        });
    });
}


async function openMatch(id) {
    modal.classList.remove("hidden");

    detail.innerHTML = `
        <div class="loading">
            Loading match analysis...
        </div>
    `;

    try {
        const response = await fetch(`/api/matches/${id}`);

        if (!response.ok) {
            throw new Error("Could not load match details");
        }

        const match = await response.json();

        detail.innerHTML = `
            <div class="match-detail-header">
                <span class="detail-tier">${match.tier}</span>

                <span class="detail-confidence">
                    ${match.confidence}% Confidence
                </span>
            </div>

            <div class="detail-teams">

                <div class="detail-team">
                    <span>HOME</span>
                    <h2>${match.home}</h2>
                </div>

                <div class="detail-vs">VS</div>

                <div class="detail-team">
                    <span>AWAY</span>
                    <h2>${match.away}</h2>
                </div>

            </div>

            <div class="detail-info">

                <div>
                    <span>REGION</span>
                    <strong>${match.region || "Global"}</strong>
                </div>

                <div>
                    <span>MATCH DATE</span>
                    <strong>${match.match_date || "TBA"}</strong>
                </div>

            </div>

            <div class="analysis-box">
                <h3>📊 Match Analysis</h3>
                <p>
                    ${match.analysis || "Analysis coming soon."}
                </p>
            </div>

            <div class="confidence-bar">
                <div
                    class="confidence-fill"
                    style="width:${match.confidence}%">
                </div>
            </div>

            <div class="confidence-label">
                Prediction Confidence: ${match.confidence}%
            </div>
        `;

    } catch (error) {
        console.error(error);

        detail.innerHTML = `
            <div class="error">
                Unable to load match analysis.
            </div>
        `;
    }
}


filters.forEach(button => {
    button.addEventListener("click", () => {
        filters.forEach(btn => btn.classList.remove("active"));

        button.classList.add("active");

        currentTier = button.dataset.tier;

        renderMatches();
    });
});


search.addEventListener("input", renderMatches);


refreshBtn.addEventListener("click", () => {
    loadMatches();
});


closeModal.addEventListener("click", () => {
    modal.classList.add("hidden");
});


modal.addEventListener("click", event => {
    if (event.target === modal) {
        modal.classList.add("hidden");
    }
});


loadMatches();
