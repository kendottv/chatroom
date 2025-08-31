document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM 載入完成，開始初始化...");

    // 夜間模式切換 - 使用 sessionStorage 或純記憶體存儲
    let isNightMode = false;

    // 嘗試從 sessionStorage 讀取，如果失敗則使用預設值
    try {
        const savedMode = sessionStorage.getItem("nightMode");
        if (savedMode === "true") {
            isNightMode = true;
            document.body.classList.add("dark-mode");
            console.log("夜間模式已啟用");
        }
    } catch (e) {
        console.warn("無法訪問 sessionStorage，使用記憶體存儲");
        isNightMode = document.body.classList.contains("dark-mode");
    }

    const toggleBtn = document.getElementById("toggleNightMode");
    if (toggleBtn) {
        toggleBtn.innerHTML = isNightMode ? '☀️ 日間模式' : '🌙 夜間模式';
        toggleBtn.setAttribute('aria-label', isNightMode ? '切換到日間模式' : '切換到夜間模式');

        toggleBtn.addEventListener("click", function () {
            document.body.classList.toggle("dark-mode");
            isNightMode = document.body.classList.contains("dark-mode");

            // 嘗試保存到 sessionStorage
            try {
                sessionStorage.setItem("nightMode", isNightMode);
            } catch (e) {
                console.warn("無法保存夜間模式設定到 sessionStorage");
            }

            toggleBtn.innerHTML = isNightMode ? '☀️ 日間模式' : '🌙 夜間模式';
            toggleBtn.setAttribute('aria-label', isNightMode ? '切換到日間模式' : '切換到夜間模式');
            console.log("夜間模式切換為: ", isNightMode);
        });
    }

    // 手機版側邊欄切換
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

        let sidebarIsOpen = false;

        // 關閉側邊欄函數
        function closeSidebar() {
            sidebar.style.transform = "translateX(-100%)";
            sidebar.style.visibility = "hidden";
            sidebar.style.opacity = "0";
            sidebar.classList.remove("active");
            menuToggle.classList.remove("active");
            document.body.classList.remove("sidebar-open");
            sidebarOverlay.classList.remove("active");
            menuToggle.setAttribute("aria-expanded", "false");
            sidebarIsOpen = false;
            console.log("側邊欄已關閉");
        }

        // 開啟側邊欄函數
        function openSidebar() {
            sidebar.style.transform = "translateX(0)";
            sidebar.style.visibility = "visible";
            sidebar.style.opacity = "1";
            sidebar.classList.add("active");
            menuToggle.classList.add("active");
            document.body.classList.add("sidebar-open");
            sidebarOverlay.classList.add("active");
            menuToggle.setAttribute("aria-expanded", "true");
            sidebarIsOpen = true;
            console.log("側邊欄已開啟");

            setTimeout(() => {
                const firstLink = sidebar.querySelector("a");
                if (firstLink) firstLink.focus();
            }, 300);
        }

        // 漢堡選單點擊事件
        menuToggle.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            console.log("漢堡選單被點擊");
            console.log("當前螢幕寬度:", window.innerWidth);
            console.log("側邊欄當前狀態:", sidebarIsOpen ? "開啟" : "關閉");
            if (sidebarIsOpen) closeSidebar();
            else openSidebar();
        });

        // 點擊遮罩層關閉側邊欄
        sidebarOverlay.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            console.log("點擊遮罩層");
            closeSidebar();
        });

        // 點擊主內容區域關閉側邊欄
        if (mainContent) {
            mainContent.addEventListener("click", function (event) {
                if (sidebarIsOpen && !event.target.closest('#menu-toggle')) {
                    console.log("點擊主內容區域");
                    closeSidebar();
                }
            });
        }

        // 防止點擊側邊欄內部時關閉
        sidebar.addEventListener("click", function (event) {
            event.stopPropagation();
            console.log("點擊側邊欄內部");
        });

        // 點擊側邊欄連結時關閉側邊欄（但不包括登出按鈕）
        const sidebarLinks = sidebar.querySelectorAll("a");
        sidebarLinks.forEach((link) => {
            link.addEventListener("click", function () {
                console.log("點擊側邊欄連結");
                setTimeout(closeSidebar, 100);
            });
        });

        // ESC 鍵關閉側邊欄
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && sidebarIsOpen) {
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
                if (window.innerWidth <= 768) {
                    sidebar.style.width = "100%";
                    sidebar.style.maxWidth = "300px";
                } else {
                    sidebar.style.width = "280px";
                }
            }, 100);
        });

        // 初始化側邊欄狀態
        console.log("初始化側邊欄狀態");
        closeSidebar();
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

    // 表單提交處理 - 完全排除登出表單
    const submitButtons = document.querySelectorAll('button[type="submit"]');
    submitButtons.forEach(button => {
        // 檢查是否有 data-no-js 屬性，如果有就跳過 JS 處理
        if (button.hasAttribute('data-no-js')) {
            console.log("按鈕有 data-no-js 屬性，跳過 JavaScript 處理");
            return;
        }
        
        const form = button.closest('form');
        
        // 檢查是否為登出表單 - 完全跳過處理
        if (form && (
            form.action.includes('logout') || 
            form.action.endsWith('/logout/') || 
            form.classList.contains('logout-form') ||
            button.classList.contains('logout-btn') ||
            button.textContent.includes('登出') ||
            button.innerHTML.includes('登出')
        )) {
            console.log("偵測到登出表單，完全跳過 JavaScript 處理");
            return; // 完全不處理，讓瀏覽器原生行為處理
        }

        // 對於非登出表單，使用 fetch 處理
        button.addEventListener("click", function (event) {
            if (form) {
                event.preventDefault(); // 阻止默認提交
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 處理中...';
                this.disabled = true;

                // 獲取 CSRF 令牌
                const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                if (!csrfToken) {
                    console.error("CSRF 令牌未找到");
                    this.innerHTML = originalText + ' (失敗: CSRF 令牌缺失)';
                    this.disabled = false;
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 3000);
                    return;
                }

                const formData = new FormData(form);
                console.log("表單數據:", Array.from(formData.entries()));
                console.log("表單 action:", form.action);

                fetch(form.action, {
                    method: form.method,
                    body: formData,
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                })
                .then(response => {
                    console.log("響應狀態:", response.status);
                    
                    if (response.status === 302) {
                        // 處理重定向
                        const redirectUrl = response.headers.get('Location');
                        console.log("執行重定向至:", redirectUrl);
                        if (redirectUrl) {
                            window.location.href = redirectUrl;
                        } else {
                            window.location.reload();
                        }
                        return null;
                    }
                    
                    if (!response.ok) {
                        throw new Error(`HTTP 錯誤! 狀態: ${response.status}`);
                    }
                    return response.text();
                })
                .then(data => {
                    if (data === null) return;
                    console.log("響應內容:", data.substring(0, 200) + (data.length > 200 ? '...' : ''));

                    // 解析 HTML 響應以提取 Django 訊息
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(data, 'text/html');
                    const messages = doc.querySelectorAll('.alert, .message');
                    let successMessage = '操作成功';
                    let isSuccess = false;

                    messages.forEach(msg => {
                        if (msg.classList.contains('alert-success') || msg.classList.contains('success')) {
                            isSuccess = true;
                            successMessage = msg.textContent.trim();
                        }
                    });

                    if (isSuccess) {
                        this.innerHTML = originalText + ` (成功: ${successMessage})`;
                        setTimeout(() => {
                            if (form.action.includes('teacher_exam')) {
                                window.location.href = '/teacher_exam/';
                            } else {
                                window.location.reload();
                            }
                        }, 500);
                    } else {
                        // 檢查錯誤訊息
                        const errorMessages = doc.querySelectorAll('.alert-danger, .alert-error, .message.error');
                        let errorText = '操作失敗';
                        if (errorMessages.length > 0) {
                            errorText = errorMessages[0].textContent.trim();
                        }
                        this.innerHTML = originalText + ` (失敗: ${errorText})`;
                        this.disabled = false;
                        setTimeout(() => {
                            this.innerHTML = originalText;
                            this.disabled = false;
                        }, 3000);
                    }
                })
                .catch(error => {
                    console.error("錯誤:", error);
                    this.innerHTML = originalText + ` (失敗: ${error.message})`;
                    this.disabled = false;
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                    }, 3000);
                });
            }
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
            setTimeout(() => (inThrottle = false), limit);
        }
    };
}

// 調試輔助函數
function debugSidebar() {
    const menuToggle = document.getElementById("menu-toggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebar-overlay");

    console.log("=== 側邊欄調試資訊 ===");
    console.log("menuToggle 元素:", menuToggle);
    console.log("sidebar 元素:", sidebar);
    console.log("sidebarOverlay 元素:", sidebarOverlay);

    if (sidebar) {
        console.log("sidebar classes:", sidebar.className);
        console.log("sidebar 計算樣式:", window.getComputedStyle(sidebar));
    }

    if (menuToggle) {
        console.log("menuToggle classes:", menuToggle.className);
        console.log("menuToggle aria-expanded:", menuToggle.getAttribute("aria-expanded"));
    }
}