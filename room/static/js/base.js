document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM 載入完成，開始初始化...");

    // 夜間模式切換
    const nightMode = localStorage.getItem("nightMode");
    if (nightMode === "true") {
        document.body.classList.add("dark-mode");
        console.log("夜間模式已啟用");
    }
    
    const toggleBtn = document.getElementById("toggleNightMode");
    if (toggleBtn) {
        toggleBtn.innerHTML = nightMode === "true" ? '☀️ 日間模式' : '🌙 夜間模式';
        toggleBtn.setAttribute('aria-label', nightMode === "true" ? '切換到日間模式' : '切換到夜間模式');
        toggleBtn.addEventListener("click", function () {
            document.body.classList.toggle("dark-mode");
            const isNight = document.body.classList.contains("dark-mode");
            localStorage.setItem("nightMode", isNight);
            toggleBtn.innerHTML = isNight ? '☀️ 日間模式' : '🌙 夜間模式';
            toggleBtn.setAttribute('aria-label', isNight ? '切換到日間模式' : '切換到夜間模式');
            console.log("夜間模式切換為: ", isNight);
        });
    }

    // 手機版側邊欄切換 - 改進版
    const menuToggle = document.getElementById("menu-toggle");
    const sidebar = document.getElementById("sidebar");
    const mainContent = document.querySelector(".main");
    const sidebarOverlay = document.getElementById("sidebar-overlay");

    console.log("尋找側邊欄元素...");
    console.log("menuToggle:", menuToggle ? "找到" : "未找到");
    console.log("sidebar:", sidebar ? "找到" : "未找到");
    console.log("mainContent:", mainContent ? "找到" : "未找到");
    console.log("sidebarOverlay:", sidebarOverlay ? "找到" : "未找到");

    if (menuToggle && sidebar && sidebarOverlay) {
        console.log("所有側邊欄元素已找到，開始設置事件監聽");

        // 檢查當前螢幕寬度
        function isMobileScreen() {
            return window.innerWidth <= 768;
        }

        // 關閉側邊欄函數
        function closeSidebar() {
            if (!isMobileScreen()) return; // 只在手機版執行
            
            sidebar.classList.remove("active");
            menuToggle.classList.remove("active");
            document.body.classList.remove("sidebar-open");
            sidebarOverlay.classList.remove("active");
            menuToggle.setAttribute("aria-expanded", "false");
            console.log("側邊欄已關閉");
        }

        // 開啟側邊欄函數
        function openSidebar() {
            if (!isMobileScreen()) return; // 只在手機版執行
            
            sidebar.classList.add("active");
            menuToggle.classList.add("active");
            document.body.classList.add("sidebar-open");
            sidebarOverlay.classList.add("active");
            menuToggle.setAttribute("aria-expanded", "true");
            console.log("側邊欄已開啟");
            
            // 焦點管理
            setTimeout(() => {
                const firstLink = sidebar.querySelector("a");
                if (firstLink) {
                    firstLink.focus();
                }
            }, 300);
        }

        // 漢堡選單點擊事件
        menuToggle.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            
            console.log("漢堡選單被點擊，當前螢幕寬度:", window.innerWidth);
            
            if (!isMobileScreen()) {
                console.log("非手機版，忽略點擊");
                return;
            }

            const isActive = sidebar.classList.contains("active");
            console.log("側邊欄當前狀態:", isActive ? "開啟" : "關閉");
            
            if (isActive) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        // 點擊遮罩層關閉側邊欄
        sidebarOverlay.addEventListener("click", function (event) {
            event.preventDefault();
            console.log("點擊遮罩層");
            closeSidebar();
        });

        // 點擊主內容區域關閉側邊欄（僅手機版）
        if (mainContent) {
            mainContent.addEventListener("click", function (event) {
                if (isMobileScreen() && sidebar.classList.contains("active")) {
                    // 檢查是否點擊的是漢堡選單本身
                    if (!event.target.closest('#menu-toggle')) {
                        console.log("點擊主內容區域");
                        closeSidebar();
                    }
                }
            });
        }

        // 防止點擊側邊欄內部時關閉
        sidebar.addEventListener("click", function (event) {
            event.stopPropagation();
            console.log("點擊側邊欄內部");
        });

        // 點擊側邊欄內的連結或按鈕時關閉側邊欄
        const sidebarLinks = sidebar.querySelectorAll("a, button");
        sidebarLinks.forEach((link, index) => {
            link.addEventListener("click", function () {
                console.log("點擊側邊欄連結", index);
                if (isMobileScreen()) {
                    // 稍微延遲關閉，讓用戶看到點擊效果
                    setTimeout(() => {
                        closeSidebar();
                    }, 100);
                }
            });
        });

        // ESC 鍵關閉側邊欄
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && isMobileScreen() && sidebar.classList.contains("active")) {
                console.log("ESC 鍵關閉側邊欄");
                closeSidebar();
                menuToggle.focus();
            }
        });

        // 監聽螢幕大小變化
        let resizeTimeout;
        window.addEventListener("resize", function () {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                console.log("螢幕大小變化:", window.innerWidth);
                
                // 如果從手機版切換到桌面版，重置側邊欄狀態
                if (!isMobileScreen()) {
                    sidebar.classList.remove("active");
                    menuToggle.classList.remove("active");
                    document.body.classList.remove("sidebar-open");
                    sidebarOverlay.classList.remove("active");
                    menuToggle.setAttribute("aria-expanded", "false");
                    console.log("切換到桌面版，側邊欄已重置");
                }
            }, 100);
        });

    } else {
        console.error("側邊欄初始化失敗 - 缺少必要元素:");
        if (!menuToggle) console.error("- menu-toggle 元素未找到");
        if (!sidebar) console.error("- sidebar 元素未找到");
        if (!sidebarOverlay) console.error("- sidebar-overlay 元素未找到");
    }

    // Django 訊息自動淡出
    const messages = document.querySelectorAll(".message");
    messages.forEach(message => {
        message.style.transition = "opacity 0.3s ease";
        setTimeout(() => {
            message.style.opacity = "0";
            setTimeout(() => message.remove(), 300);
        }, 5000);
    });

    // 表單提交載入狀態
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        button.addEventListener("click", function () {
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 處理中...';
            this.disabled = true;
            setTimeout(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            }, 5000);
        });
    });

    console.log("所有功能初始化完成");
});

// 效能優化：節流函數
function throttle(func, limit) {
    let inThrottle;
    return function () {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}