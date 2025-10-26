// filter.js
document.addEventListener("DOMContentLoaded", () => {
  const filterButtons = document.querySelectorAll(".filters .chip");
  const cards = document.querySelectorAll("#project-grid .card");

  filterButtons.forEach(button => {
    button.addEventListener("click", () => {
      // Update button styles
      filterButtons.forEach(btn => btn.classList.remove("active"));
      button.classList.add("active");

      const filter = button.getAttribute("data-filter");

      // Show/hide cards based on filter
      cards.forEach(card => {
        const tags = card.getAttribute("data-tags") || "";
        if (filter === "all" || tags.toLowerCase().includes(filter.toLowerCase())) {
          card.style.display = "block";
        } else {
          card.style.display = "none";
        }
      });
    });
  });
});
