document.addEventListener("DOMContentLoaded", () => {
  const progress = document.getElementById("progress-list");
  if (!progress) return;
  const orderId = progress.dataset.order;
  async function refreshStatus() {
    try {
      const response = await fetch(`/api/order/${orderId}/status`, {headers: {"Accept": "application/json"}});
      if (!response.ok) return;
      const data = await response.json();
      progress.dataset.status = data.status_index;
      const steps = progress.querySelectorAll(".progress-step");
      steps.forEach((step, index) => {
        step.classList.toggle("complete", index <= data.status_index);
        const dot = step.querySelector(".progress-dot");
        dot.textContent = index <= data.status_index ? "✓" : String(index + 1);
        const old = step.querySelector(".muted");
        if (old) old.remove();
        if (index === data.status_index) {
          const note = document.createElement("p");
          note.className = "muted";
          note.textContent = "Current status";
          step.querySelector("div").appendChild(note);
        }
      });
    } catch (error) {
      // Keep the page usable if polling is temporarily unavailable.
    }
  }
  window.setInterval(refreshStatus, 10000);
});
