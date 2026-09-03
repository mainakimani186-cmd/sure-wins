const cards = document.getElementById("cards");
const count = document.getElementById("count");
const updated = document.getElementById("updated");
const search = document.getElementById("search");
const refreshBtn = document.getElementById("refresh");
const filters = document.querySelectorAll("#filters button");

let allMatches = [];
let currentTier = "ALL";
let expandedMatchId = null;


async function loadMatches() {
    cards.innerHTML = `
        <p style="color:#aaa;padding:20px;">
            Loading matches...
        </p>
    `;

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
            updated.textContent =
                new Date(data.updated).toLocaleTimeString();
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
            currentTier === "ALL" ||
            match.tier === currentTier;

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


    cards.innerHTML = filtered.map((match, index) => {

        const isExpanded = expandedMatchId === match.id;

        return `
            <article
                class="match-wrapper ${isExpanded ? "expanded" : ""}"
                data-id="${match.id}"
            >

                <!-- COMPACT MATCH ROW -->

                <div class="match-row">

                    <div class="match-number">
                        ${String(index + 1).padStart(2, "0")}
                    </div>

                    <div class="match-main">

                        <div class="match-teams">
                            ${match.home}
                            <span>vs</span>
                            ${match.away}
                        </div>

                        <div class="match-meta">
                            <span class="tier-label">
                                ${match.tier}
                            </span>

                            <span>
                                ${match.region || "Global"}
                            </span>
                        </div>

                    </div>

                    <div class="match-confidence">
                        <strong>${match.confidence}%</strong>
                        <small>confidence</small>
                    </div>

                </div>


                <!-- EXPANDED ANALYSIS -->

                <div class="match-analysis">

                    <div class="analysis-header">
                        <div>
                            <span>📊</span>
                            MATCH ANALYSIS
                        </div>

                        <span class="collapse-text">
                            Tap to collapse ▲
                        </span>
                    </div>


                    <div class="prediction-box">

                        <h3>Prediction Insight</h3>

                        <p>
                            ${match.analysis ||
                            `${match.home} is currently ranked as a ${match.tier.toLowerCase()} consensus pick.`}
                        </p>

                    </div>


                    <!-- HEAD TO HEAD -->

                    <div class="analysis-section">

                        <h3>🤝 Head to Head</h3>

                        <div class="h2h-grid">

                            <div class="stat-box">
                                <strong>12</strong>
                                <span>Total Meetings</span>
                            </div>

                            <div class="stat-box">
                                <strong>6</strong>
                                <span>${match.home} Wins</span>
                            </div>

                            <div class="stat-box">
                                <strong>3</strong>
                                <span>Draws</span>
                            </div>

                            <div class="stat-box">
                                <strong>3</strong>
                                <span>${match.away} Wins</span>
                            </div>

                        </div>

                    </div>


                    <!-- HOME FORM -->

                    <div class="analysis-section">

                        <h3>
                            🔵 ${match.home} — Last 10 Games
                        </h3>

                        <div class="form-row">

                            <span class="form win">W</span>
                            <span class="form win">W</span>
                            <span class="form draw">D</span>
                            <span class="form win">W</span>
                            <span class="form win">W</span>
                            <span class="form loss">L</span>
                            <span class="form win">W</span>
                            <span class="form draw">D</span>
                            <span class="form win">W</span>
                            <span class="form win">W</span>

                        </div>

                    </div>


                    <!-- AWAY FORM -->

                    <div class="analysis-section">

                        <h3>
                            🟠 ${match.away} — Last 10 Games
                        </h3>

                        <div class="form-row">

                            <span class="form loss">L</span>
                            <span class="form win">W</span>
                            <span class="form loss">L</span>
                            <span class="form draw">D</span>
                            <span class="form win">W</span>
                            <span class="form loss">L</span>
                            <span class="form draw">D</span>
                            <span class="form win">W</span>
                            <span class="form loss">L</span>
                            <span class="form win">W</span>

                        </div>

                    </div>


                    <!-- CONFIDENCE -->

                    <div class="confidence-bar-section">

                        <div class="confidence-label">
                            <span>Consensus Confidence</span>
                            <strong>${match.confidence}%</strong>
                        </div>

                        <div class="progress-bar">
                            <div
                                class="progress-fill"
                                style="width:${match.confidence}%"
                            ></div>
                        </div>

                    </div>


                    <div class="analysis-note">

                        ⚠️ Analysis is for informational purposes.
                        Predictions are estimates, not guarantees.

                    </div>

                </div>

            </article>
        `;

    }).join("");
}


/* CLICK MATCH TO EXPAND */

cards.addEventListener("click", (event) => {

    const matchWrapper =
        event.target.closest(".match-wrapper");

    if (!matchWrapper) return;

    const matchId =
        Number(matchWrapper.dataset.id);

    if (expandedMatchId === matchId) {
        expandedMatchId = null;
    } else {
        expandedMatchId = matchId;
    }

    renderMatches();
});


/* FILTER BUTTONS */

filters.forEach(button => {

    button.addEventListener("click", () => {

        filters.forEach(btn =>
            btn.classList.remove("active")
        );

        button.classList.add("active");

        currentTier = button.dataset.tier;

        expandedMatchId = null;

        renderMatches();

    });

});


/* SEARCH */

search.addEventListener("input", () => {

    expandedMatchId = null;

    renderMatches();

});


/* REFRESH */

refreshBtn.addEventListener("click", () => {

    expandedMatchId = null;

    loadMatches();

});


/* INITIAL LOAD */

loadMatches();
