// Sure Wins JavaScript
console.log("Sure Wins loaded successfully");
const grid = document.getElementById("grid");
const count = document.getElementById("count");
const filters = document.querySelectorAll("#filters button");

let matches = [];

async function loadMatches(tier = "ALL") {
  try {
    let url = "/api/matches";

    if (tier !== "ALL") {
      url += `?tier=${tier}`;
    }

    const response = await fetch(url);
    const data = await response.json();

    matches = data.matches || [];

    renderMatches(matches);
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

      <p class="region">${match.region}</p>

      <button onclick="showMatch(${match.id})">
        View Analysis
      </button>
    </article>
  `).join("");
}

async function showMatch(id) {
  try {
    const response = await fetch(`/api/matches/${id}`);
    const match = await response.json();

    alert(
      `${match.home} vs ${match.away}\n\n` +
      `Confidence: ${match.confidence}%\n` +
      `Tier: ${match.tier}\n\n` +
      `${match.analysis || "Analysis coming soon."}`
    );
  } catch (error) {
    console.error(error);
  }
}

filters.forEach(button => {
  button.addEventListener("click", () => {
    filters.forEach(btn => btn.classList.remove("active"));

    button.classList.add("active");

    loadMatches(button.dataset.tier);
  });
});

loadMatches();
