// 確認提交動作
function confirmSubmit() {
    return confirm('確定要提交考卷嗎？提交後將無法修改答案。');
}

function confirmEndExam() {
    return confirm('確定要結束考試嗎？這將結束所有學生的考試。');
}

function confirmAction(event, form) {
    const submitButton = event.submitter;
    if (submitButton.classList.contains('end-btn')) {
        return confirmEndExam();
    } else {
        return confirmSubmit();
    }
}

// AI 問答功能
function askAI() {
    const question = document.getElementById('ai_question').value.trim();
    if (!question) {
        alert('請輸入問題！');
        return;
    }
    
    const responseDiv = document.getElementById('ai-response');
    responseDiv.innerHTML = '🤖 正在處理您的問題，請稍候...';
    
    const paperId = document.getElementById('current-paper-id').value;
    if (!paperId) {
        responseDiv.innerHTML = '❌ 未找到當前考卷！';
        return;
    }

    fetch('/ask_ai/', {  // 改為 /ask_ai/
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: `prompt=${encodeURIComponent(question)}&paper_id=${encodeURIComponent(paperId)}`  // 使用 prompt 參數
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            responseDiv.innerHTML = `❌ ${data.error}`;
        } else {
            responseDiv.innerHTML = `🤖 ${data.response}`;
            // 注意：目前 ask_ai 視圖未返回 remaining，需根據需求調整
        }
    })
    .catch(error => {
        console.error('Error:', error);
        responseDiv.innerHTML = '❌ 發生錯誤，請檢查網路連接或稍後再試。';
    });
}

// 夜間模式切換
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    if (currentTheme === 'dark') {
        body.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    } else {
        body.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
}

// 頁面載入時初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('考試頁面已載入');
    const submitForm = document.querySelector('form');
    if (submitForm) {
        submitForm.addEventListener('submit', function(event) {
            if (!confirmAction(event, this)) {
                event.preventDefault();
                return;
            }
            const answers = {};
            document.querySelectorAll('[name^="answers_"]').forEach(input => {
                const questionId = input.name.replace('answers_', '');
                if (input.type === 'checkbox') {
                    const checked = document.querySelectorAll(`[name="answers_${questionId}"]:checked`);
                    answers[questionId] = Array.from(checked).map(cb => cb.value);
                } else if (input.type === 'radio' && input.checked) {
                    answers[questionId] = input.value;
                } else if (input.type === 'text' || input.tagName === 'TEXTAREA') {
                    answers[questionId] = input.value || null;
                }
            });
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'answers';
            hiddenInput.value = JSON.stringify(answers);
            submitForm.appendChild(hiddenInput);
        });
    }

    // 檢查系統偏好
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.body.setAttribute('data-theme', 'dark');
    }
    // 檢查 localStorage
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.body.setAttribute('data-theme', savedTheme);
    }

    // 添加主題切換按鈕
    const themeToggle = document.createElement('button');
    themeToggle.innerHTML = '🌙 切換主題';
    themeToggle.style.cssText = 'position: fixed; top: 10px; right: 10px; padding: 8px 16px; background: var(--btn-bg); color: white; border: none; border-radius: 8px; cursor: pointer;';
    themeToggle.addEventListener('click', toggleTheme);
    document.body.appendChild(themeToggle);

    // 檢查考卷是否已完成
    const examRecordsStr = '{{ exam_records|default:"{}" }}'.replace(/'/g, '"');
    const examRecords = JSON.parse(examRecordsStr);
    const examPapers = document.querySelectorAll('.exam-paper');
    examPapers.forEach(paper => {
        const paperId = paper.querySelector('input[name="paper_id"]').value;
        if (examRecords[paperId] && examRecords[paperId].is_completed) {
            paper.classList.add('completed');
        }
    });
});