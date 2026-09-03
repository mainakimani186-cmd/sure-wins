

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
    cards.innerHTML = '<div class="loading">Loading Sure Wins...</div>';

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
        console.error(error);

        cards.innerHTML = `
            <div class="error-message">
                Failed to load matches.<br>
                <small>${error.message}</small>
            </div>
        `;
    }
}


function renderMatches() {
    const query = search.value.toLowerCase().trim();

    const filtered = allMatches.filter(match => {
        const tierMatch =
            currentTier === "ALL" ||
            match.tier === currentTier;

        const searchMatch =
            match.home.toLowerCase().includes(query) ||
            match.away.toLowerCase().includes(query);

        return tierMatch && searchMatch;
    });

    if (!filtered.length) {
        cards.innerHTML = `
            <div class="empty-state">
                No matches found.
            </div>
        `;
        return;
    }

    cards.innerHTML = filtered.map((match, index) => `
        <article
            class="match-row"
            data-id="${match.id}"
        >
            <div class="match-rank">
                ${(index + 1).toString().padStart(2, "0")}
            </div>

            <div class="match-main">
                <div class="match-teams">
                    <strong>${match.home}</strong>
                    <span>vs</span>
                    <strong>${match.away}</strong>
                </div>

                <div class="match-meta">
                    <span class="row-tier ${match.tier.replace(" ", "-").toLowerCase()}">
                        ${match.tier}
                    </span>

                    <span>${match.region || "Global"}</span>
                </div>
            </div>

            <div class="match-confidence">
                <strong>${match.confidence}%</strong>
                <small>confidence</small>
            </div>

            <div class="match-arrow">›</div>
        </article>
    `).join("");

    document.querySelectorAll(".match-row").forEach(row => {
        row.addEventListener("click", () => {
            openMatch(row.dataset.id);
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
            <div class="analysis-header">
                <span class="detail-tier">
                    ${match.tier}
                </span>

                <button class="modal-close-inline" onclick="closeMatch()">
                    ×
                </button>
            </div>

            <div class="analysis-teams">
                <div>
                    <small>HOME</small>
                    <h2>${match.home}</h2>
                </div>

                <div class="analysis-vs">VS</div>

                <div>
                    <small>AWAY</small>
                    <h2>${match.away}</h2>
                </div>
            </div>

            <div class="confidence-section">
                <div class="confidence-top">
                    <span>Prediction Confidence</span>
                    <strong>${match.confidence}%</strong>
                </div>

                <div class="confidence-track">
                    <div
                        class="confidence-progress"
                        style="width:${match.confidence}%"
                    ></div>
                </div>
            </div>

            <div class="analysis-stats">
                <div>
                    <small>REGION</small>
                    <strong>${match.region || "Global"}</strong>
                </div>

                <div>
                    <small>MATCH DATE</small>
                    <strong>${match.match_date || "TBA"}</strong>
                </div>
            </div>

            <section class="analysis-section">
                <h3>🧠 Sure Wins Analysis</h3>
                <p>
                    ${match.analysis || "Detailed analysis coming soon."}
                </p>
            </section>

            <div class="coming-next">
                <div>📊 Head-to-Head Statistics</div>
                <small>
                    Historical meetings and results — Phase B
                </small>
            </div>

            <div class="coming-next">
                <div>📈 Last 10 Games Form</div>
                <small>
                    Recent wins, draws, losses and performance — Phase B
                </small>
            </div>
        `;

    } catch (error) {
        console.error(error);

        detail.innerHTML = `
            <div class="error-message">
                Unable to load match analysis.
            </div>
        `;
    }
}


function closeMatch() {
    modal.classList.add("hidden");
}


filters.forEach(button => {
    button.addEventListener("click", () => {
        filters.forEach(btn => {
            btn.classList.remove("active");
        });

        button.classList.add("active");

        currentTier = button.dataset.tier;
        renderMatches();
    });
});


search.addEventListener("input", renderMatches);


refreshBtn.addEventListener("click", loadMatches);


closeModal.addEventListener("click", closeMatch);


modal.addEventListener("click", event => {
    if (event.target === modal) {
        closeMatch();
    }
});


loadMatches();
