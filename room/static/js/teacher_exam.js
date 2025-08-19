/**
 * 全域變數，用於儲存當前選中的題目資料。
 * 每個題目包含 id、title、type、points 和 ai_limit。
 */
let selectedQuestions = [];

/**
 * 切換標籤頁（新增題目、題目庫、創建考試）。
 * @param {string} tabId - 要顯示的標籤頁 ID（'create-question'、'question-bank' 或 'create-exam'）。
 * 功能：隱藏所有標籤頁和按鈕的 active 狀態，僅顯示指定的標籤頁並高亮對應按鈕。
 * 若切換到題目庫標籤，更新選中題目資訊。
 */
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    document.querySelector(`button[onclick="switchTab('${tabId}')"]`).classList.add('active');
    
    if (tabId === 'question-bank') {
        updateSelection();
    }
}

/**
 * 全選題目庫中的所有題目。
 * 功能：將所有題目checkbox設為選中，並更新選中題目資訊。
 */
function selectAll() {
    document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = true);
    updateSelection();
}

/**
 * 清除所有選中的題目。
 * 功能：將所有題目checkbox設為未選中，並更新選中題目資訊。
 */
function clearSelection() {
    document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = false);
    updateSelection();
}

/**
 * 更新選中題目資訊並顯示。
 * 功能：收集選中的題目資料，計算總題數、總分和總 AI 問答次數限制，
 * 更新題目庫和創建考試頁面的顯示，並同步隱藏輸入欄位。
 */
function updateSelection() {
    const checkboxes = document.querySelectorAll('.question-checkbox:checked');
    selectedQuestions = [];
    let totalPoints = 0;
    let totalAiLimit = 0;

    checkboxes.forEach(cb => {
        const questionItem = cb.closest('.question-item');
        selectedQuestions.push({
            id: cb.value,
            title: questionItem.dataset.title,
            type: questionItem.dataset.type,
            points: parseInt(questionItem.dataset.points) || 0,
            ai_limit: parseInt(questionItem.dataset.aiLimit) || 1 // 預設至少 1
        });
        totalPoints += parseInt(questionItem.dataset.points) || 0;
        totalAiLimit += parseInt(questionItem.dataset.aiLimit) || 1;
    });

    document.getElementById('selected-count').textContent = selectedQuestions.length;
    document.getElementById('total-questions').textContent = selectedQuestions.length;
    document.getElementById('total-points').textContent = totalPoints;
    document.getElementById('total-ai-limit').textContent = totalAiLimit;

    document.getElementById('total-questions-exam').textContent = selectedQuestions.length;
    document.getElementById('total-points-exam').textContent = totalPoints;
    document.getElementById('total-ai-limit-exam').textContent = totalAiLimit;

    const selectedList = document.getElementById('selected-list');
    selectedList.innerHTML = selectedQuestions.map(q => 
        `<p>題目: ${q.title} (${q.type}, ${q.points} 分, AI 次數: ${q.ai_limit})</p>`
    ).join('');

    document.getElementById('selected_questions_input').value = selectedQuestions.map(q => q.id).join(',');
    
    document.getElementById('create-exam-btn').disabled = selectedQuestions.length === 0;
}

/**
 * 顯示或隱藏選中題目摘要。
 * 功能：根據是否有選中題目，顯示或隱藏題目庫中的選中題目摘要區塊。
 */
function showSelectedQuestions() {
    const summary = document.getElementById('selected-summary');
    summary.style.display = selectedQuestions.length > 0 ? 'block' : 'none';
}

/**
 * 確認刪除選中題目。
 * @returns {boolean} - 返回是否確認刪除。
 * 功能：檢查是否有選中題目，若有則彈出確認對話框。
 */
function confirmDelete() {
    return selectedQuestions.length > 0 && confirm('確定要刪除選定的題目嗎？');
}

/**
 * 根據題型動態更新表單顯示。
 * 功能：根據選擇的題型（單選、多選、是非、簡答）顯示或隱藏選項、真假答案或簡答答案輸入區域。
 */
function updateForm() {
    const questionType = document.getElementById('question_type').value;
    const optionsContainer = document.getElementById('options_container');
    const trueFalseContainer = document.getElementById('true_false_container');
    const shortAnswerContainer = document.getElementById('short_answer_container');
    const scAnswers = document.querySelectorAll('.sc-answer');
    const mcqAnswers = document.querySelectorAll('.mcq-answer');
    const optionInputs = document.querySelectorAll('.option-input');

    optionsContainer.style.display = (questionType === 'sc' || questionType === 'mcq') ? 'block' : 'none';
    trueFalseContainer.style.display = questionType === 'tf' ? 'block' : 'none';
    shortAnswerContainer.style.display = questionType === 'sa' ? 'block' : 'none';

    scAnswers.forEach(answer => {
        answer.style.display = questionType === 'sc' ? 'inline' : 'none';
    });
    mcqAnswers.forEach(answer => {
        answer.style.display = questionType === 'mcq' ? 'inline' : 'none';
    });

    optionInputs.forEach(input => {
        input.disabled = !(questionType === 'sc' || questionType === 'mcq');
    });
}

/**
 * 驗證新增/編輯題目表單。
 * @returns {boolean} - 返回表單是否有效。
 * 功能：檢查題目內容、選項、正確答案、嘗試次數、配分和 AI 次數限制是否有效，
 * 若有效則將編輯器內容存入隱藏輸入欄位。
 */
function validateForm() {
    const questionType = document.getElementById('question_type').value;
    const editorContent = quill.root.innerHTML.trim();
    const optionInputs = document.querySelectorAll('.option-input');
    const scAnswers = document.querySelectorAll('.sc-answer:checked');
    const mcqAnswers = document.querySelectorAll('.mcq-answer:checked');
    const tfAnswers = document.querySelectorAll('input[name="is_correct"]:checked'); // 修正為 is_correct
    const maxAttempts = document.querySelector('input[name="max_attempts"]').value;
    const points = document.querySelector('input[name="points"]').value;
    const aiLimit = document.querySelector('input[name="ai_limit"]').value;

    // 驗證題目內容
    if (editorContent === '<p><br></p>' || editorContent === '') {
        alert('請輸入題目內容！');
        return false;
    }

    // 驗證單選/多選題
    if (questionType === 'sc' || questionType === 'mcq') {
        let hasOptions = false;
        optionInputs.forEach(input => {
            if (input.value.trim() !== '') {
                hasOptions = true;
            }
        });
        if (!hasOptions) {
            alert('請至少輸入一個選項！');
            return false;
        }
        if (questionType === 'sc' && scAnswers.length === 0) {
            alert('請選擇一個正確答案！');
            return false;
        }
        if (questionType === 'mcq' && mcqAnswers.length === 0) {
            alert('請至少選擇一個正確答案！');
            return false;
        }
    } else if (questionType === 'tf' && tfAnswers.length === 0) {
        alert('請選擇真或假作為正確答案！');
        return false;
    }

    // 驗證嘗試次數
    if (parseInt(maxAttempts) < 1) {
        alert('最大嘗試次數必須大於 0！');
        return false;
    }
    
    // 驗證配分
    if (parseInt(points) < 0 || parseInt(points) > 100) {
        alert('配分必須在 0 到 100 之間！');
        return false;
    }
    
    // 驗證 AI 問答次數限制
    if (parseInt(aiLimit) < 1) {
        alert('AI 問答次數限制必須至少為 1！');
        return false;
    }

    // 將編輯器內容存入隱藏輸入欄位
    document.getElementById('hidden_question').value = editorContent;
    return true;
}

/**
 * 初始化 Quill 編輯器，支援富文本編輯題目內容。
 * 配置工具欄，包含粗體、斜體、下劃線、圖片、程式碼區塊、清單和清除格式。
 */
const quill = new Quill('#editor-container', {
    theme: 'snow',
    modules: {
        toolbar: [
            ['bold', 'italic', 'underline'],
            ['image', 'code-block'],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            ['clean']
        ]
    }
});

// 監聽內容變化，實時同步到隱藏輸入
quill.on('text-change', function() {
    const content = quill.root.innerHTML;
    document.getElementById('hidden_question').value = content;
});

/**
 * 頁面載入時初始化表單和選中題目。
 * 功能：確保題型表單和選中題目顯示正確。
 */
document.addEventListener('DOMContentLoaded', () => {
    updateForm();
    updateSelection();
    // 添加表單提交驗證
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!validateForm()) {
                event.preventDefault();
            }
        });
    }
});