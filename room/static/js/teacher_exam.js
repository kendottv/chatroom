/**
 * 全域變數，用於儲存當前選中的題目資料。
 */
let selectedQuestions = [];
let quill; // 定義為全域變數

/**
 * 切換標籤頁。
 * @param {string} tabId - 要顯示的標籤頁 ID。
 */
function switchTab(tabId) {
    try {
        console.log('Switching to tab:', tabId);
        document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        const tab = document.getElementById(tabId);
        if (!tab) throw new Error(`Tab ${tabId} not found`);
        tab.classList.add('active');
        const button = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
        if (!button) throw new Error(`Button for tab ${tabId} not found`);
        button.classList.add('active');
        if (tabId === 'question-bank') updateSelection();
    } catch (error) {
        console.error('Error in switchTab:', error);
    }
}

/**
 * 全選題目庫中的所有題目。
 */
function selectAll() {
    try {
        console.log('Selecting all questions');
        document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = true);
        updateSelection();
    } catch (error) {
        console.error('Error in selectAll:', error);
    }
}

/**
 * 清除所有選中的題目。
 */
function clearSelection() {
    try {
        console.log('Clearing selection');
        document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = false);
        updateSelection();
    } catch (error) {
        console.error('Error in clearSelection:', error);
    }
}

/**
 * 更新選中題目資訊並顯示。
 */
function updateSelection() {
    try {
        console.log('Updating selection');
        const checkboxes = document.querySelectorAll('.question-checkbox:checked');
        selectedQuestions = [];
        let totalPoints = 0, totalAiLimit = 0;
        checkboxes.forEach(cb => {
            const questionItem = cb.closest('.question-item');
            if (!questionItem) throw new Error('Question item not found');
            selectedQuestions.push({
                id: cb.value,
                title: questionItem.dataset.title,
                type: questionItem.dataset.type,
                points: parseInt(questionItem.dataset.points) || 0,
                ai_limit: parseInt(questionItem.dataset.aiLimit) || 1
            });
            totalPoints += parseInt(questionItem.dataset.points) || 0;
            totalAiLimit += parseInt(questionItem.dataset.aiLimit) || 1;
        });
        ['selected-count', 'total-questions', 'total-questions-exam'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = selectedQuestions.length;
        });
        ['total-points', 'total-points-exam'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = totalPoints;
        });
        ['total-ai-limit', 'total-ai-limit-exam'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = totalAiLimit;
        });
        const selectedList = document.getElementById('selected-list');
        if (selectedList) selectedList.innerHTML = selectedQuestions.map(q => `<p>題目: ${q.title} (${q.type}, ${q.points} 分, AI 次數: ${q.ai_limit})</p>`).join('');
        const selectedInput = document.getElementById('selected_questions_input');
        if (selectedInput) selectedInput.value = selectedQuestions.map(q => q.id).join(',');
        const createBtn = document.getElementById('create-exam-btn');
        if (createBtn) createBtn.disabled = selectedQuestions.length === 0;
    } catch (error) {
        console.error('Error in updateSelection:', error);
    }
}

/**
 * 顯示或隱藏選中題目摘要。
 */
function showSelectedQuestions() {
    try {
        console.log('Showing selected questions');
        const summary = document.getElementById('selected-summary');
        if (summary) summary.style.display = selectedQuestions.length > 0 ? 'block' : 'none';
    } catch (error) {
        console.error('Error in showSelectedQuestions:', error);
    }
}

/**
 * 確認刪除選中題目。
 * @returns {boolean}
 */
function confirmDelete() {
    try {
        console.log('Confirming delete');
        return selectedQuestions.length > 0 && confirm('確定要刪除選定的題目嗎？');
    } catch (error) {
        console.error('Error in confirmDelete:', error);
        return false;
    }
}

/**
 * 根據題型動態更新表單顯示。
 */
function updateForm() {
    try {
        console.log('Updating form');
        const questionType = document.getElementById('question_type').value;
        const containers = { 'options_container': ['sc', 'mcq'], 'true_false_container': ['tf'], 'short_answer_container': ['sa'] };
        Object.entries(containers).forEach(([id, types]) => {
            const el = document.getElementById(id);
            if (el) el.style.display = types.includes(questionType) ? 'block' : 'none';
        });
        ['sc-answer', 'mcq-answer'].forEach(cls => {
            document.querySelectorAll(`.${cls}`).forEach(el => {
                el.style.display = (cls === 'sc-answer' && questionType === 'sc') || (cls === 'mcq-answer' && questionType === 'mcq') ? 'inline' : 'none';
            });
        });
        document.querySelectorAll('.option-input').forEach(input => {
            if (input) input.disabled = !['sc', 'mcq'].includes(questionType);
        });
    } catch (error) {
        console.error('Error in updateForm:', error);
    }
}

/**
 * 驗證新增/編輯題目表單。
 * @returns {boolean}
 */
function validateForm() {
    try {
        console.log('Validating form');
        const questionType = document.getElementById('question_type').value;
        if (!quill) throw new Error('Quill not initialized');
        const editorContent = quill.root.innerHTML.trim();
        const textContent = quill.getText().trim();
        console.log('Editor content:', editorContent, 'Text content:', textContent);

        if (!textContent || textContent === '' || textContent === '請輸入題目內容') {
            alert('請輸入題目內容！');
            return false;
        }

        const optionInputs = document.querySelectorAll('.option-input');
        const scAnswers = document.querySelectorAll('.sc-answer:checked');
        const mcqAnswers = document.querySelectorAll('.mcq-answer:checked');
        const tfAnswers = document.querySelectorAll('input[name="correct_answer"]:checked');
        const maxAttempts = document.querySelector('input[name="max_attempts"]').value;
        const points = document.querySelector('input[name="points"]').value;
        const aiLimit = document.querySelector('input[name="ai_limit"]').value;

        if (['sc', 'mcq'].includes(questionType)) {
            if (!Array.from(optionInputs).some(input => input.value.trim())) {
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

        if (parseInt(maxAttempts) < 1) {
            alert('最大嘗試次數必須大於 0！');
            return false;
        }
        if (parseInt(points) < 0 || parseInt(points) > 100) {
            alert('配分必須在 0 到 100 之間！');
            return false;
        }
        if (parseInt(aiLimit) < 1) {
            alert('AI 問答次數限制必須至少為 1！');
            return false;
        }

        document.getElementById('hidden_question').value = editorContent;
        return true;
    } catch (error) {
        console.error('Error in validateForm:', error);
        alert('表單驗證失敗，請檢查控制台以獲取詳細資訊。');
        return false;
    }
}

/**
 * 初始化 Quill 編輯器。
 */
function initializeQuill() {
    try {
        console.log('Initializing Quill');
        const editorContainer = document.getElementById('editor-container');
        if (editorContainer) {
            quill = new Quill('#editor-container', {
                theme: 'snow',
                modules: {
                    toolbar: [['bold', 'italic', 'underline'], ['image', 'code-block'], [{'list': 'ordered'}, {'list': 'bullet'}], ['clean']]
                }
            });
            console.log('Quill initialized successfully');

            // 監聽內容變化
            quill.on('text-change', () => {
                try {
                    const content = quill.root.innerHTML;
                    const hiddenInput = document.getElementById('hidden_question');
                    if (hiddenInput) {
                        hiddenInput.value = content;
                        console.log('Content synced:', content);
                    }
                } catch (error) {
                    console.error('Error in text-change:', error);
                }
            });

            // 填充編輯內容
            const editContent = editorContainer.innerHTML.trim();
            if (editContent && editContent !== '<p><br></p>') {
                quill.setContents(quill.clipboard.convert(editContent));
                console.log('Edit content set:', editContent);
            }
        } else {
            console.error('Editor container not found');
        }
    } catch (error) {
        console.error('Error initializing Quill:', error);
    }
}

/**
 * 頁面載入時初始化。
 */
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('DOM fully loaded');
        initializeQuill();
        updateForm();
        updateSelection();

        // 延遲確保 DOM 準備好
        setTimeout(() => {
            if (quill) {
                const initialContent = quill.root.innerHTML;
                const hiddenInput = document.getElementById('hidden_question');
                if (hiddenInput) {
                    hiddenInput.value = initialContent;
                    console.log('Initial content synced:', initialContent);
                }
                if (initialContent && initialContent.trim() !== '<p><br></p>') {
                    quill.updateContents(quill.getContents());
                }
            }
        }, 500);

        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            if (form.querySelector('#hidden_question')) {
                form.addEventListener('submit', (event) => {
                    console.log('Form submitting, validating...');
                    if (!validateForm()) {
                        console.log('Form validation failed');
                        event.preventDefault();
                    } else {
                        console.log('Form validation passed');
                    }
                });
            }
        });
    } catch (error) {
        console.error('Error in DOMContentLoaded:', error);
    }
});