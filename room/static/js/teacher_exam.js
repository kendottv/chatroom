let selectedQuestions = [];

// 確認刪除
function confirmDelete() {
    const checkedBoxes = document.querySelectorAll('input[name="delete_questions"]:checked');
    if (checkedBoxes.length === 0) {
        alert('請選擇要刪除的題目！');
        return false;
    }
    return confirm(`確定要刪除選中的 ${checkedBoxes.length} 個題目嗎？此操作無法復原。`);
}

// 標籤頁切換
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    const targetTab = document.getElementById(tabName);
    if (targetTab) targetTab.classList.add('active');
    
    document.querySelector(`.tab-button[onclick="switchTab('${tabName}')"]`).classList.add('active');
    
    if (tabName === 'create-exam') {
        updateExamQuestionsSummary();
    }
}

// 全選功能
function selectAll() {
    document.querySelectorAll('input[name="delete_questions"]').forEach(checkbox => {
        checkbox.checked = true;
    });
    updateSelection();
}

// 清除選擇
function clearSelection() {
    document.querySelectorAll('input[name="delete_questions"]').forEach(checkbox => {
        checkbox.checked = false;
    });
    updateSelection();
}

// 顯示/隱藏已選題目
function showSelectedQuestions() {
    const summaryDiv = document.getElementById('selected-summary');
    summaryDiv.style.display = summaryDiv.style.display === 'none' ? 'block' : 'none';
}

// 更新選擇狀態
function updateSelection() {
    const checkboxes = document.querySelectorAll('input[name="delete_questions"]:checked');
    selectedQuestions = [];
    
    checkboxes.forEach(cb => {
        const questionItem = cb.closest('.question-item');
        selectedQuestions.push({
            id: cb.value,
            title: questionItem.dataset.title,
            type: questionItem.dataset.type,
            points: parseInt(questionItem.dataset.points),
            element: questionItem
        });
    });

    document.querySelectorAll('.question-item').forEach(item => {
        item.classList.remove('selected');
    });
    selectedQuestions.forEach(q => {
        q.element.classList.add('selected');
    });

    document.getElementById('selected-count').textContent = selectedQuestions.length;
    let totalPoints = selectedQuestions.reduce((sum, q) => sum + q.points, 0);
    document.getElementById('total-questions').textContent = selectedQuestions.length;
    document.getElementById('total-points').textContent = totalPoints;
    
    updateSelectedList();
    updateCreateExamButton();
}

// 更新已選題目列表
function updateSelectedList() {
    const listDiv = document.getElementById('selected-list');
    if (selectedQuestions.length === 0) {
        listDiv.innerHTML = '<p>尚未選擇題目</p>';
        return;
    }
    
    let html = '';
    selectedQuestions.forEach((q, index) => {
        const questionTypeText = getQuestionTypeText(q.type);
        html += `<div style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px;">
            ${index + 1}. ${q.title} (${questionTypeText}, ${q.points}分)
        </div>`;
    });
    listDiv.innerHTML = html;
}

// 獲取題型文字
function getQuestionTypeText(type) {
    const typeMap = {
        'sc': '單選題',
        'mcq': '多選題',
        'tf': '是非題',
        'sa': '簡答題'
    };
    return typeMap[type] || type;
}

// 更新創建考試按鈕狀態
function updateCreateExamButton() {
    const createBtn = document.getElementById('create-exam-btn');
    const selectedQuestionsInput = document.getElementById('selected_questions_input');
    
    if (selectedQuestions.length > 0) {
        createBtn.disabled = false;
        selectedQuestionsInput.value = selectedQuestions.map(q => q.id).join(',');
    } else {
        createBtn.disabled = true;
        selectedQuestionsInput.value = '';
    }
}

// 更新考試題目摘要
function updateExamQuestionsSummary() {
    const summaryDiv = document.getElementById('exam-questions-summary');
    if (selectedQuestions.length === 0) {
        summaryDiv.innerHTML = '<p style="color: #666;">請先到「題目庫」標籤頁選擇要加入考試的題目</p>';
        return;
    }
    
    let totalPoints = selectedQuestions.reduce((sum, q) => sum + q.points, 0);
    let html = '<h4>已選題目：</h4>';
    
    selectedQuestions.forEach((q, index) => {
        const questionTypeText = getQuestionTypeText(q.type);
        html += `<div style="margin-bottom: 5px;">
            ${index + 1}. ${q.title} (${questionTypeText}, ${q.points}分)
        </div>`;
    });
    
    html += `<div style="margin-top: 15px; font-weight: bold; color: #1e355b;">
        總計：${selectedQuestions.length} 題，${totalPoints} 分
    </div>`;
    
    summaryDiv.innerHTML = html;
}

// Quill 編輯器初始化
document.addEventListener("DOMContentLoaded", function () {
    try {
        var quill = new Quill('#editor-container', {
            theme: 'snow',
            modules: {
                toolbar: [['bold', 'italic', 'underline'], ['link', 'image'], [{'list': 'ordered'}, {'list': 'bullet'}]]
            },
            formats: ['bold', 'italic', 'underline', 'link', 'image', 'list', 'bullet'],
            placeholder: '請輸入題目內容'
        });

        var initialContent = document.getElementById('editor-container').innerHTML.trim();
        console.log('Initial Quill content:', initialContent);
        if (!initialContent || initialContent === '<p>請輸入題目內容</p>' || initialContent === '<p><br></p>') {
            quill.setContents([{ insert: '\n' }]);
        } else {
            quill.root.innerHTML = initialContent;
        }
        document.getElementById('hidden_question').value = quill.root.innerHTML;

        quill.on('text-change', function () {
            document.getElementById('hidden_question').value = quill.root.innerHTML;
            console.log('Text changed:', quill.root.innerHTML);
        });
    } catch (e) {
        console.error('Quill initialization failed:', e);
    }

    // 表單類型更新函數
    function updateForm() {
        const questionType = document.getElementById('question_type').value;
        console.log('Updating form for type:', questionType);
        const optionsContainer = document.getElementById('options_container');
        const trueFalseContainer = document.getElementById('true_false_container');
        const shortAnswerContainer = document.getElementById('short_answer_container');
        const optionInputs = document.querySelectorAll('.option-input');
        const scAnswers = document.querySelectorAll('.sc-answer');
        const mcqAnswers = document.querySelectorAll('.mcq-answer');
        
        optionsContainer.style.display = 'none';
        trueFalseContainer.style.display = 'none';
        shortAnswerContainer.style.display = 'none';
        
        optionInputs.forEach(input => {
            input.removeAttribute('required');
            input.disabled = true;
        });

        if (questionType === 'sa') {
            shortAnswerContainer.style.display = 'block';
        } else if (questionType === 'tf') {
            trueFalseContainer.style.display = 'block';
        } else if (questionType === 'sc') {
            optionsContainer.style.display = 'block';
            scAnswers.forEach(radio => radio.style.display = 'inline');
            mcqAnswers.forEach(checkbox => checkbox.style.display = 'none');
            optionInputs.forEach(input => {
                input.setAttribute('required', '');
                input.disabled = false;
            });
        } else if (questionType === 'mcq') {
            optionsContainer.style.display = 'block';
            scAnswers.forEach(radio => radio.style.display = 'none');
            mcqAnswers.forEach(checkbox => checkbox.style.display = 'inline');
            optionInputs.forEach(input => {
                input.setAttribute('required', '');
                input.disabled = false;
            });
        }
    }

    updateForm();
    document.getElementById('question_type').addEventListener('change', updateForm);
    window.updateForm = updateForm;
});

// 表單驗證
function validateForm() {
    const questionType = document.getElementById('question_type').value;
    const questionText = document.getElementById('hidden_question').value.trim();
    console.log('Validating form:', { questionType, questionText });

    if (!questionText || questionText === '<p></p>' || questionText === '<p><br></p>') {
        console.log('Validation failed: Empty question content');
        alert('請輸入題目內容！');
        return false;
    }

    if (questionType === 'sc' || questionType === 'mcq') {
        const optionInputs = document.querySelectorAll('.option-input');
        let hasValue = false;
        optionInputs.forEach(input => {
            if (input.value.trim()) {
                hasValue = true;
            }
        });
        if (!hasValue) {
            console.log('Validation failed: No options provided');
            alert('請至少填寫一個選項！');
            return false;
        }

        if (questionType === 'sc') {
            const checkedRadio = document.querySelector('input[name="correct_option"]:checked');
            if (!checkedRadio) {
                console.log('Validation failed: No correct option selected for SC');
                alert('請選擇單選題的正確答案！');
                return false;
            }
        } else if (questionType === 'mcq') {
            const checkedCheckboxes = document.querySelectorAll('input[name="correct_options"]:checked');
            if (checkedCheckboxes.length === 0) {
                console.log('Validation failed: No correct options selected for MCQ');
                alert('請選擇至少一個多選題的正確答案！');
                return false;
            }
        }
    } else if (questionType === 'tf') {
        const tfRadios = document.querySelectorAll('input[name="correct_answer"]:checked');
        console.log('TF radios checked:', tfRadios.length);
        if (tfRadios.length === 0) {
            console.log('Validation failed: No TF answer selected');
            alert('請選擇是非題的正確答案！');
            return false;
        }
    } else if (questionType === 'sa') {
        const saAnswer = document.querySelector('textarea[name="correct_answer"]').value.trim();
        console.log('SA answer:', saAnswer);
        if (!saAnswer && !confirm('簡答題未填寫參考答案，確定繼續？')) {
            console.log('Validation failed: SA answer confirmation cancelled');
            return false;
        }
    }

    console.log('Validation passed');
    return true;
}