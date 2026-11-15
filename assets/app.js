const BN_MAP = {
  "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
  "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯"
};

const CAT_LABELS = {
  poultry: "মুরগি",
  egg: "ডিম",
  meat: "মাংস",
  fish: "মাছ"
};

let marketData = null;
let currentDivision = "dhaka";
let currentMode = "retail";
let currentCategory = "all";
let searchQuery = "";

function toBanglaDigits(value) {
  return String(value).replace(/[0-9]/g, (d) => BN_MAP[d]);
}

function formatChangeBadge(change) {
  if (change > 0) {
    return `<span class="badge-up">↑ +${toBanglaDigits(change)} ৳</span>`;
  }
  if (change < 0) {
    return `<span class="badge-down">↓ -${toBanglaDigits(Math.abs(change))} ৳</span>`;
  }
  return `<span class="badge-same">• অপরিবর্তিত</span>`;
}

function renderTable() {
  const tbody = document.getElementById("price-table-body");
  if (!marketData || !marketData.divisions[currentDivision]) return;

  const divInfo = marketData.divisions[currentDivision];
  const modeLabel = currentMode === "retail" ? "খুচরা বাজারদর" : "পাইকারি বাজারদর";

  document.getElementById("current-division-title").textContent = `${divInfo.name_bn} — ${modeLabel}`;
  document.getElementById("current-market-note").textContent = divInfo.market_note;
  document.getElementById("price-col-header").textContent =
    currentMode === "retail" ? "খুচরা দর (টাকা)" : "পাইকারি দর (টাকা)";

  const filtered = divInfo.items.filter((item) => {
    const matchCat = currentCategory === "all" || item.category === currentCategory;
    const matchSearch = item.name.toLowerCase().includes(searchQuery.trim().toLowerCase());
    return matchCat && matchSearch;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="loading-cell">দুঃখিত, এই নামে কোনো পণ্য পাওয়া যায়নি।</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered
    .map((item) => {
      const price = currentMode === "retail" ? item.retail : item.wholesale;
      return `
        <tr>
          <td>
            <span class="item-name">${item.name}</span>
            <span class="item-cat-badge">${CAT_LABELS[item.category] || ""}</span>
          </td>
          <td>${item.unit}</td>
          <td class="price-val">৳ ${toBanglaDigits(price)}</td>
          <td>${formatChangeBadge(item.change)}</td>
        </tr>
      `;
    })
    .join("");
}

async function initApp() {
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = toBanglaDigits(new Date().getFullYear());

  try {
    const res = await fetch(`data/prices.json?v=${Date.now()}`);
    if (!res.ok) throw new Error("Failed to load prices");
    marketData = await res.json();

    document.getElementById("last-updated").textContent = marketData.meta.last_updated;
    document.getElementById("primary-source-tag").textContent = `সূত্র: ${marketData.meta.primary_source}`;

    renderTable();
  } catch (err) {
    document.getElementById("price-table-body").innerHTML =
      `<tr><td colspan="4" class="loading-cell">ডেটা লোড করতে সমস্যা হয়েছে। অনুগ্রহ করে পেজটি রিফ্রেশ করুন।</td></tr>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initApp();

  const divisionSelect = document.getElementById("division-select");
  if (divisionSelect) {
    divisionSelect.addEventListener("change", (e) => {
      currentDivision = e.target.value;
      renderTable();
    });
  }

  document.querySelectorAll(".price-mode-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".price-mode-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentMode = btn.dataset.mode;
      renderTable();
    });
  });

  document.querySelectorAll(".cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".cat-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentCategory = btn.dataset.cat;
      renderTable();
    });
  });

  const searchInput = document.getElementById("search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value;
      renderTable();
    });
  }
});
