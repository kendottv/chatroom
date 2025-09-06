document.addEventListener("DOMContentLoaded", function () {
    console.log("學生考試歷史頁面腳本初始化...");

    // 卡片展開/摺疊處理
    document.querySelectorAll('.card-header').forEach(header => {
        header.addEventListener('click', function () {
            const card = this.closest('.card');
            const details = card.querySelector('.card-details');
            const isExpanded = this.getAttribute('aria-expanded') === 'true';

            // 切換展開狀態
            if (isExpanded) {
                details.style.display = 'none';
                this.setAttribute('aria-expanded', 'false');
                card.classList.remove('active');
            } else {
                details.style.display = 'block';
                this.setAttribute('aria-expanded', 'true');
                card.classList.add('active');
            }
        });
    });

    // 提交按鈕高亮卡片但不阻止表單提交
    document.querySelectorAll('button[type="submit"]').forEach(button => {
        button.addEventListener('click', function (event) {
            // 高亮當前卡片
            document.querySelectorAll('.card').forEach(card => card.classList.remove('active'));
            this.closest('.card').classList.add('active');
            // 不阻止默認表單提交行為
        });
    });
});