const cards = document.getElementById("cards");
const count = document.getElementById("count");
const updated = document.getElementById("updated");
const search = document.getElementById("search");
const refreshBtn = document.getElementById("refresh");
const filters = document.querySelectorAll("#filters button");

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

        console.log("API DATA:", data);

        allMatches = data.matches || [];

        count.textContent = allMatches.length;

        if (data.updated) {
            updated.textContent = new Date(data.updated).toLocaleTimeString();
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
        <article class="card">
            <div class="card-top">
                <span class="tier ${match.tier.replace(" ", "-").toLowerCase()}">
                    ${match.tier}
                </span>
                <span class="confidence">${match.confidence}%</span>
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
        </article>
    `).join("");
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

loadMatches();
