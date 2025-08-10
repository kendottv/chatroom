document.addEventListener("DOMContentLoaded", function () {
    const nightMode = localStorage.getItem("nightMode");
    if (nightMode === "true") {
        document.body.classList.add("dark-mode");
    }
    const toggleBtn = document.getElementById("toggleNightMode");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", function () {
            document.body.classList.toggle("dark-mode");
            const isNight = document.body.classList.contains("dark-mode");
            localStorage.setItem("nightMode", isNight);
        });
    }
});