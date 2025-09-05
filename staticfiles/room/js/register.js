document.addEventListener("DOMContentLoaded", function () {
    const nightMode = localStorage.getItem("nightMode");
    if (nightMode === "true") {
        document.body.classList.add("dark-mode");
    }
});