const grid = document.getElementById("grid");
const count = document.getElementById("count");
const filters = document.querySelectorAll("#filters button");
const searchInput = document.getElementById("search");

let matches = [];
let activeTier = "ALL";

async function loadMatches(tier = "ALL") {
  try {
    grid.innerHTML = `
      <div class="card">
        <p>Loading matches...</p>
      </div>
    `;

    let url = "/api/matches";

    if (tier !== "ALL") {
      url += `?tier=${encodeURIComponent(tier)}`;
    }

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const data = await response.json();

    matches = data.matches || [];

    renderMatches(matches);

    const updated = document.getElementById("updated");
    if (updated && data.updated) {
      updated.textContent = new Date(data.updated).toLocaleString();
    }

  } catch (error) {
    console.error("Error loading matches:", error);

    grid.innerHTML = `
      <div class="card">
        <h3>Unable to load matches</h3>
        <p>Please try again later.</p>
      </div>
    `;
  }
}

function renderMatches(items) {
  count.textContent = items.length;

  if (!items.length) {
    grid.innerHTML = `
      <div class="card">
        <h3>No matches available</h3>
        <p>Check back later for updated predictions.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = items.map(match => `
    <article class="card">
      <div class="card-top">
        <span class="tier">${match.tier}</span>
        <span class="confidence">${match.confidence}%</span>
      </div>

      <h3>${match.home} vs ${match.away}</h3>

      <p class="region">${match.region || "Global"}</p>

      <button onclick="showMatch(${match.id})">
        View Analysis
      </button>
    </article>
  `).join("");
}

async function showMatch(id) {
  try {
    const response = await fetch(`/api/matches/${id}`);

    if (!response.ok) {
      throw new Error("Unable to load match");
    }

    const match = await response.json();

    alert(
      `${match.home} vs ${match.away}\n\n` +
      `Confidence: ${match.confidence}%\n` +
      `Tier: ${match.tier}\n\n` +
      `${match.analysis || "Analysis coming soon."}`
    );

  } catch (error) {
    console.error(error);
    alert("Unable to load match analysis.");
  }
}

filters.forEach(button => {
  button.addEventListener("click", () => {
    filters.forEach(btn => btn.classList.remove("active"));

    button.classList.add("active");

    activeTier = button.dataset.tier || "ALL";

    loadMatches(activeTier);
  });
});

if (searchInput) {
  searchInput.addEventListener("input", event => {
    const term = event.target.value.toLowerCase().trim();

    const filtered = matches.filter(match =>
      match.home.toLowerCase().includes(term) ||
      match.away.toLowerCase().includes(term) ||
      (match.region || "").toLowerCase().includes(term)
    );

    renderMatches(filtered);
  });
}

loadMatches();
