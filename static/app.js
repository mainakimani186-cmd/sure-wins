const cards = document.getElementById("cards");
const count = document.getElementById("count");
const updated = document.getElementById("updated");
const search = document.getElementById("search");
const refreshBtn = document.getElementById("refresh");
const filters = document.querySelectorAll("#filters button");

let allMatches = [];
let currentTier = "ALL";
let expandedMatchId = null;

// Cache analysis so reopening a card does not keep
// making API-Football requests.
const analysisCache = {};

// Track loading states
const loadingAnalysis = new Set();


// --------------------------------------------------
// LOAD MATCHES
// --------------------------------------------------

async function loadMatches() {
    cards.innerHTML = `
        <p style="color:#aaa;padding:20px;">
            Loading matches...
        </p>
    `;

    try {
        const response = await fetch(
            "/api/matches?ts=" + Date.now()
        );

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();

        console.log("MATCH DATA:", data);

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


// --------------------------------------------------
// FETCH REAL ANALYSIS
// --------------------------------------------------

async function loadAnalysis(matchId) {

    // Already cached
    if (analysisCache[matchId]) {
        return;
    }

    // Already loading
    if (loadingAnalysis.has(matchId)) {
        return;
    }

    loadingAnalysis.add(matchId);

    renderMatches();

    try {

        const response = await fetch(
            `/api/matches/${matchId}/analysis`
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.error ||
                `Server returned ${response.status}`
            );
        }

        console.log("REAL ANALYSIS:", data);

        analysisCache[matchId] = data;

    } catch (error) {

        console.error(
            "Failed to load analysis:",
            error
        );

        analysisCache[matchId] = {
            error: error.message
        };

    } finally {

        loadingAnalysis.delete(matchId);

        // Only re-render if this match is still open
        if (expandedMatchId === matchId) {
            renderMatches();
        }
    }
}


// --------------------------------------------------
// ESCAPE HTML
// --------------------------------------------------

function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    const div = document.createElement("div");

    div.textContent = String(value);

    return div.innerHTML;
}


// --------------------------------------------------
// CREATE FORM BOXES
// --------------------------------------------------

function renderForm(games) {

    if (!games || games.length === 0) {
        return `
            <span style="color:#888;">
                No recent results available.
            </span>
        `;
    }

    return games.map(game => {

        const result = game.result || "?";

        let resultClass = "draw";

        if (result === "W") {
            resultClass = "win";
        }

        if (result === "L") {
            resultClass = "loss";
        }

        const title = `
${game.result || ""}
vs ${game.opponent || "Unknown"}
${game.score || ""}
${game.date || ""}
        `.trim();

        return `
            <span
                class="form ${resultClass}"
                title="${escapeHtml(title)}"
            >
                ${escapeHtml(result)}
            </span>
        `;

    }).join("");
}


// --------------------------------------------------
// RENDER ANALYSIS
// --------------------------------------------------

function renderAnalysis(match) {

    const matchId = match.id;

    // Loading
    if (loadingAnalysis.has(matchId)) {

        return `
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
                    <h3>Loading real match analysis...</h3>
                    <p>
                        Fetching head-to-head history and
                        recent team form.
                    </p>
                </div>

            </div>
        `;
    }


    const analysis = analysisCache[matchId];


    // Error
    if (analysis && analysis.error) {

        return `
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

                    <h3>Analysis unavailable</h3>

                    <p>
                        ${escapeHtml(analysis.error)}
                    </p>

                </div>

            </div>
        `;
    }


    // Analysis not loaded yet
    if (!analysis) {
        return "";
    }


    const h2h = analysis.head_to_head || {};

    const homeForm = analysis.home_form || [];

    const awayForm = analysis.away_form || [];

    const homeName =
        analysis.teams?.home?.name ||
        match.home;

    const awayName =
        analysis.teams?.away?.name ||
        match.away;


    return `
        <div class="match-analysis">

            <!-- HEADER -->

            <div class="analysis-header">

                <div>
                    <span>📊</span>
                    MATCH ANALYSIS
                </div>

                <span class="collapse-text">
                    Tap to collapse ▲
                </span>

            </div>


            <!-- PREDICTION -->

            <div class="prediction-box">

                <h3>Prediction Insight</h3>

                <p>
                    ${escapeHtml(
                        match.analysis ||
                        `${match.home} is currently ranked as a ${match.tier.toLowerCase()} consensus pick.`
                    )}
                </p>

            </div>


            <!-- HEAD TO HEAD -->

            <div class="analysis-section">

                <h3>🤝 Head to Head</h3>

                <div class="h2h-grid">

                    <div class="stat-box">

                        <strong>
                            ${h2h.total ?? 0}
                        </strong>

                        <span>Total Meetings</span>

                    </div>


                    <div class="stat-box">

                        <strong>
                            ${h2h.home_wins ?? 0}
                        </strong>

                        <span>
                            ${escapeHtml(homeName)} Wins
                        </span>

                    </div>


                    <div class="stat-box">

                        <strong>
                            ${h2h.draws ?? 0}
                        </strong>

                        <span>Draws</span>

                    </div>


                    <div class="stat-box">

                        <strong>
                            ${h2h.away_wins ?? 0}
                        </strong>

                        <span>
                            ${escapeHtml(awayName)} Wins
                        </span>

                    </div>

                </div>

            </div>


            <!-- HOME FORM -->

            <div class="analysis-section">

                <h3>
                    🔵 ${escapeHtml(homeName)}
                    — Last ${homeForm.length} Games
                </h3>

                <div class="form-row">

                    ${renderForm(homeForm)}

                </div>

            </div>


            <!-- AWAY FORM -->

            <div class="analysis-section">

                <h3>
                    🟠 ${escapeHtml(awayName)}
                    — Last ${awayForm.length} Games
                </h3>

                <div class="form-row">

                    ${renderForm(awayForm)}

                </div>

            </div>


            <!-- CONFIDENCE -->

            <div class="confidence-bar-section">

                <div class="confidence-label">

                    <span>Consensus Confidence</span>

                    <strong>
                        ${escapeHtml(match.confidence)}%
                    </strong>

                </div>


                <div class="progress-bar">

                    <div
                        class="progress-fill"
                        style="width:${match.confidence}%"
                    ></div>

                </div>

            </div>


            <!-- DISCLAIMER -->

            <div class="analysis-note">

                ⚠️ Analysis is for informational purposes.
                Predictions are estimates, not guarantees.

            </div>

        </div>
    `;
}


// --------------------------------------------------
// RENDER MATCHES
// --------------------------------------------------

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

        const isExpanded =
            expandedMatchId === match.id;


        return `
            <article
                class="match-wrapper ${
                    isExpanded ? "expanded" : ""
                }"
                data-id="${match.id}"
            >


                <!-- COMPACT ROW -->

                <div class="match-row">

                    <div class="match-number">

                        ${String(index + 1).padStart(2, "0")}

                    </div>


                    <div class="match-main">

                        <div class="match-teams">

                            ${escapeHtml(match.home)}

                            <span>vs</span>

                            ${escapeHtml(match.away)}

                        </div>


                        <div class="match-meta">

                            <span class="tier-label">

                                ${escapeHtml(match.tier)}

                            </span>


                            <span>

                                ${escapeHtml(
                                    match.region || "Global"
                                )}

                            </span>

                        </div>

                    </div>


                    <div class="match-confidence">

                        <strong>
                            ${escapeHtml(match.confidence)}%
                        </strong>

                        <small>confidence</small>

                    </div>

                </div>


                <!-- REAL ANALYSIS -->

                ${
                    isExpanded
                        ? renderAnalysis(match)
                        : ""
                }


            </article>
        `;

    }).join("");
}


// --------------------------------------------------
// CLICK MATCH TO EXPAND
// --------------------------------------------------

cards.addEventListener("click", (event) => {

    const matchWrapper =
        event.target.closest(".match-wrapper");

    if (!matchWrapper) return;

    const matchId =
        Number(matchWrapper.dataset.id);


    // Collapse current match
    if (expandedMatchId === matchId) {

        expandedMatchId = null;

        renderMatches();

        return;
    }


    // Expand new match
    expandedMatchId = matchId;

    renderMatches();


    // Fetch real data
    loadAnalysis(matchId);

});


// --------------------------------------------------
// FILTER BUTTONS
// --------------------------------------------------

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


// --------------------------------------------------
// SEARCH
// --------------------------------------------------

search.addEventListener("input", () => {

    expandedMatchId = null;

    renderMatches();

});


// --------------------------------------------------
// REFRESH
// --------------------------------------------------

refreshBtn.addEventListener("click", () => {

    expandedMatchId = null;

    loadMatches();

});


// --------------------------------------------------
// INITIAL LOAD
// --------------------------------------------------

loadMatches();
