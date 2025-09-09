document.addEventListener("DOMContentLoaded", function () {
    console.log("學生考試歷史頁面腳本初始化...");

    // 等待 DOM 完全加載後再初始化
    setTimeout(function() {
        initializeCards();
        setupEventListeners();
        setupResponsiveHandling();
    }, 100);

    function initializeCards() {
        const cards = document.querySelectorAll('.card');
        console.log(`找到 ${cards.length} 個卡片`);
        
        cards.forEach((card, index) => {
            const details = card.querySelector('.card-details');
            const header = card.querySelector('.card-header');
            const cardId = card.getAttribute('data-card-id');
            
            console.log(`處理第 ${index + 1} 個卡片, ID: ${cardId}`);
            
            if (details && header) {
                details.style.maxHeight = '0';
                details.style.opacity = '0';
                details.style.overflow = 'hidden';
                details.setAttribute('aria-hidden', 'true');
                header.setAttribute('aria-expanded', 'false');
                card.classList.remove('active');
                console.log(`初始化卡片 ${cardId} 為摺疊狀態`);
            } else {
                console.warn(`卡片 ${cardId} 缺少必要元素:`, {
                    hasDetails: !!details,
                    hasHeader: !!header
                });
            }
        });
    }

    function setupEventListeners() {
        // 使用事件委派來處理點擊事件
        document.addEventListener('click', function(event) {
            const header = event.target.closest('.card-header');
            if (!header) return;

            event.preventDefault();
            handleCardToggle(header);
        });

        // 鍵盤支持
        document.addEventListener('keydown', function(event) {
            const header = event.target.closest('.card-header');
            if (!header) return;
            
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                handleCardToggle(header);
            }
        });

        // 提交按鈕處理
        document.addEventListener('click', function(event) {
            const submitButton = event.target.closest('button[type="submit"]');
            if (!submitButton) return;

            const card = submitButton.closest('.card');
            if (card) {
                const cardId = card.getAttribute('data-card-id');
                console.log(`提交調分: 卡片 ${cardId}`);
                
                // 高亮當前卡片
                document.querySelectorAll('.card').forEach(c => c.classList.remove('active'));
                card.classList.add('active');
            }
        });
    }

    function handleCardToggle(header) {
        const card = header.closest('.card');
        if (!card) {
            console.error('找不到對應的卡片元素');
            return;
        }

        const details = card.querySelector('.card-details');
        if (!details) {
            console.error('找不到卡片詳情元素');
            return;
        }

        const isExpanded = header.getAttribute('aria-expanded') === 'true';
        const cardId = card.getAttribute('data-card-id');

        console.log(`點擊卡片: ${cardId}, 當前展開狀態: ${isExpanded}`);

        if (isExpanded) {
            // 摺疊當前卡片
            collapseCard(card, header, details);
            console.log(`卡片 ${cardId} 已摺疊`);
        } else {
            // 先摺疊所有其他卡片
            collapseAllCards();
            
            // 然後展開當前卡片
            setTimeout(() => {
                expandCard(card, header, details);
                console.log(`卡片 ${cardId} 已展開`);
            }, 50);
        }
    }

    function expandCard(card, header, details) {
        // 計算內容高度
        details.style.maxHeight = 'none';
        const height = details.scrollHeight;
        details.style.maxHeight = '0';

        // 強制重繪
        details.offsetHeight;

        // 展開動畫
        details.style.maxHeight = height + 'px';
        details.style.opacity = '1';
        header.setAttribute('aria-expanded', 'true');
        card.classList.add('active');
        details.setAttribute('aria-hidden', 'false');

        // 動畫完成後設置為 auto 以適應內容變化
        setTimeout(() => {
            if (header.getAttribute('aria-expanded') === 'true') {
                details.style.maxHeight = 'none';
            }
        }, 300);
    }

    function collapseCard(card, header, details) {
        // 設置當前高度
        details.style.maxHeight = details.scrollHeight + 'px';
        
        // 強制重繪
        details.offsetHeight;

        // 摺疊動畫
        details.style.maxHeight = '0';
        details.style.opacity = '0';
        header.setAttribute('aria-expanded', 'false');
        card.classList.remove('active');
        details.setAttribute('aria-hidden', 'true');
    }

    function collapseAllCards() {
        document.querySelectorAll('.card').forEach(otherCard => {
            const otherDetails = otherCard.querySelector('.card-details');
            const otherHeader = otherCard.querySelector('.card-header');
            
            if (otherDetails && otherHeader && otherHeader.getAttribute('aria-expanded') === 'true') {
                collapseCard(otherCard, otherHeader, otherDetails);
                const otherCardId = otherCard.getAttribute('data-card-id');
                console.log(`卡片 ${otherCardId} 已摺疊`);
            }
        });
    }

    function setupResponsiveHandling() {
        function adjustInputSizes() {
            const inputs = document.querySelectorAll('input[type="number"]');
            inputs.forEach(input => {
                if (window.innerWidth <= 576) {
                    input.style.width = '80px';
                } else {
                    input.style.width = '60px';
                }
            });
            console.log(`調整輸入框大小，當前螢幕寬度: ${window.innerWidth}px`);
        }

        // 初始調整
        adjustInputSizes();
        
        // 防抖動的 resize 處理
        let resizeTimeout;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(adjustInputSizes, 150);
        });
    }

    // 調試函數 - 在開發時可以在控制台調用
    window.debugCards = function() {
        const cards = document.querySelectorAll('.card');
        console.log(`總共找到 ${cards.length} 個卡片:`);
        
        cards.forEach((card, index) => {
            const cardId = card.getAttribute('data-card-id');
            const header = card.querySelector('.card-header');
            const details = card.querySelector('.card-details');
            
            console.log(`卡片 ${index + 1}:`, {
                id: cardId,
                hasHeader: !!header,
                hasDetails: !!details,
                isExpanded: header ? header.getAttribute('aria-expanded') : 'N/A',
                maxHeight: details ? details.style.maxHeight : 'N/A'
            });
        });
    };
});