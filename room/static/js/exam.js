// 當前題目索引（每個考卷獨立）
const currentIndices = {};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    try {
        const examRecordsElement = document.getElementById('exam-records');
        if (examRecordsElement) {
            const examRecords = JSON.parse(examRecordsElement.textContent);
        }
    } catch (error) {
        console.warn('Failed to parse exam records:', error);
    }

    document.querySelectorAll('.exam-paper').forEach(paper => {
        const paperId = paper.getAttribute('data-paper-id');
        if (paperId) {
            currentIndices[paperId] = 0;
            updateNavigationButtons(paperId);
            setupEventListeners(paperId);
        }
    });
});

// 設置事件監聽器
function setupEventListeners(paperId) {
    const prevBtn = document.getElementById(`prev-question-${paperId}`);
    const nextBtn = document.getElementById(`next-question-${paperId}`);
    const submitBtn = document.getElementById(`submit-answer-${paperId}`);

    if (prevBtn) {
        prevBtn.addEventListener('click', () => handlePrevQuestion(paperId));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const totalQuestions = document.querySelectorAll(`.exam-paper[data-paper-id="${paperId}"] .question-container`).length;
            handleNextQuestion(paperId, totalQuestions);
        });
    }
    if (submitBtn) {
        submitBtn.addEventListener('click', async () => {
            const currentQuestion = document.querySelector(`.exam-paper[data-paper-id="${paperId}"] .question-container[style*="display: block"]`);
            if (currentQuestion) {
                const questionId = currentQuestion.getAttribute('data-question-id');
                const answer = getAnswer(currentQuestion);
                await submitSingleAnswer(paperId, questionId, answer);
            }
        });
    }

    // 表單提交事件
    const form = document.getElementById(`exam-form-${paperId}`);
    if (form) {
        form.addEventListener('submit', (event) => confirmAction(event, form));
    }
}

// 切換題目
function switchQuestion(paperId, index) {
    const questions = document.querySelectorAll(`.exam-paper[data-paper-id="${paperId}"] .question-container`);
    if (!questions.length) {
        console.error(`No questions found for paper ${paperId}`);
        return false;
    }

    if (index < 0 || index >= questions.length) {
        console.error(`Invalid question index: ${index} for paper ${paperId}. Total questions: ${questions.length}`);
        return false;
    }

    questions.forEach((q, i) => {
        q.style.display = i === index ? 'block' : 'none';
    });

    currentIndices[paperId] = index;
    updateNavigationButtons(paperId);
    console.log(`Switched to question index: ${index} for paper ${paperId}`);
    return true;
}

// 更新導航按鈕狀態
function updateNavigationButtons(paperId) {
    const totalQuestions = document.querySelectorAll(`.exam-paper[data-paper-id="${paperId}"] .question-container`).length;
    const prevBtn = document.getElementById(`prev-question-${paperId}`);
    const nextBtn = document.getElementById(`next-question-${paperId}`);
    const currentQuestionDisplay = document.getElementById(`current-question-${paperId}`);
    
    if (!prevBtn || !nextBtn || !currentQuestionDisplay) {
        console.warn(`Navigation elements not found for paper ${paperId}`);
        return;
    }

    if (!currentIndices.hasOwnProperty(paperId) || currentIndices[paperId] < 0 || currentIndices[paperId] >= totalQuestions) {
        currentIndices[paperId] = 0;
    }

    const currentIndex = currentIndices[paperId];
    prevBtn.disabled = currentIndex === 0;
    
    if (totalQuestions > 0) {
        nextBtn.textContent = currentIndex === totalQuestions - 1 ? '提交並結束' : '下一題';
        currentQuestionDisplay.textContent = `第 ${currentIndex + 1} 題 / ${totalQuestions} 題`;
        nextBtn.disabled = false;
    } else {
        nextBtn.textContent = '無題目';
        currentQuestionDisplay.textContent = '無可用題目';
        nextBtn.disabled = true;
    }
}

// 提交確認
function confirmAction(event, form) {
    event.preventDefault();
    const paperId = form.querySelector('input[name="paper_id"]').value;
    const answers = {};
    form.querySelectorAll('.question-container').forEach(container => {
        const questionId = container.getAttribute('data-question-id');
        const answer = getAnswer(container);
        if (answer !== null) {
            answers[questionId] = answer;
        }
    });

    document.getElementById(`answers-${paperId}`).value = JSON.stringify(answers);
    if (confirm('確定提交考卷？')) {
        form.submit();
    }
}

// 獲取答案
function getAnswer(container) {
    const questionId = container.getAttribute('data-question-id');
    let answer = null;

    if (container.querySelector(`input[name="answer-${questionId}"]:checked`)) {
        if (container.querySelector(`input[name="answer-${questionId}[]"]:checked`)) {
            const checked = container.querySelectorAll(`input[name="answer-${questionId}[]"]:checked`);
            answer = Array.from(checked).map(cb => cb.value);
        } else {
            const checked = container.querySelector(`input[name="answer-${questionId}"]:checked`);
            answer = checked ? checked.value : null;
        }
    } else if (container.querySelector(`textarea[name="answer-${questionId}"]`)) {
        answer = container.querySelector(`textarea[name="answer-${questionId}"]`).value.trim() || null;
    } else if (container.querySelector(`input[name="answer-${questionId}"]`)) {
        answer = container.querySelector(`input[name="answer-${questionId}"]`).value.trim() || null;
    }

    return answer;
}

// 提交單題答案
async function submitSingleAnswer(paperId, questionId, answer) {
    const nextBtn = document.getElementById(`next-question-${paperId}`);
    if (!nextBtn) {
        console.error(`Next button not found for paper ${paperId}`);
        return false;
    }

    nextBtn.classList.add('loading');
    nextBtn.disabled = true;

    try {
        const response = await fetch('/room/submit_single_answer/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ paper_id: paperId, question_id: questionId, answer: answer }),
        });

        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message || `答案提交成功！得分: ${data.score}`);
            return true;
        } else {
            alert(data.message || '提交失敗，請重試。');
            return false;
        }
    } catch (error) {
        console.error('Error submitting answer:', error);
        alert('提交答案時發生錯誤，請重試。');
        return false;
    } finally {
        nextBtn.classList.remove('loading');
        nextBtn.disabled = false;
    }
}

// 完成考試
async function completeExam(paperId) {
    try {
        const response = await fetch('/room/complete_exam/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ paper_id: paperId }),
        });

        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message || '考試已完成！');
            return true;
        } else {
            alert(data.message || '完成考試失敗，請重試。');
            return false;
        }
    } catch (error) {
        console.error('Error completing exam:', error);
        alert('完成考試時發生錯誤，請重試。');
        return false;
    }
}

// 結束考試（管理員）
async function endExam(paperId) {
    if (!confirm('確定結束此考試？此操作無法撤銷。')) return;

    const endBtn = document.querySelector(`.submit-btn.end-btn`);
    if (!endBtn) {
        console.error('End exam button not found');
        return;
    }

    endBtn.classList.add('loading');
    endBtn.disabled = true;

    try {
        const response = await fetch('/room/end_exam/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ paper_id: paperId }),
        });

        const data = await response.json();
        if (data.status === 'success') {
            alert(data.message || '考試已結束！');
            location.reload();
        } else {
            alert(data.message || '結束考試失敗，請重試。');
        }
    } catch (error) {
        console.error('Error ending exam:', error);
        alert('結束考試時發生錯誤，請重試。');
    } finally {
        endBtn.classList.remove('loading');
        endBtn.disabled = false;
    }
}

// 處理下一題
async function handleNextQuestion(paperId, totalQuestions) {
    console.log(`handleNextQuestion called: paperId=${paperId}, totalQuestions=${totalQuestions}`);
    
    if (!paperId) {
        console.error('Paper ID is required');
        alert('考卷 ID 缺失，請重新載入頁面。');
        return;
    }

    if (totalQuestions === 0) {
        alert('此考卷無題目，無法繼續。請聯繫管理員。');
        return;
    }

    const questions = document.querySelectorAll(`.exam-paper[data-paper-id="${paperId}"] .question-container`);
    if (!questions.length) {
        console.error(`No questions found for paper ${paperId}`);
        alert('無可用題目，請聯繫管理員。');
        return;
    }

    if (!currentIndices.hasOwnProperty(paperId)) {
        console.warn(`Current index not initialized for paper ${paperId}, initializing to 0`);
        currentIndices[paperId] = 0;
    }

    const currentIndex = currentIndices[paperId];
    
    if (currentIndex < 0 || currentIndex >= questions.length) {
        console.error(`Invalid current index: ${currentIndex} for paper ${paperId}. Total questions: ${questions.length}`);
        alert('題目索引錯誤，請重新載入頁面。');
        return;
    }

    const currentQuestion = questions[currentIndex];
    if (!currentQuestion) {
        console.error(`Current question is undefined for index ${currentIndex}`);
        alert('無法獲取當前題目，請重新載入頁面。');
        return;
    }

    const questionId = currentQuestion.getAttribute('data-question-id');
    if (!questionId) {
        console.error('Question ID not found');
        alert('題目 ID 缺失，請聯繫管理員。');
        return;
    }

    // 收集答案
    let answer = getAnswer(currentQuestion);

    if (answer === null || (typeof answer === 'string' && !answer) || (Array.isArray(answer) && answer.length === 0)) {
        if (!confirm('答案為空，確定繼續？')) return;
    }

    // 提交答案
    const success = await submitSingleAnswer(paperId, questionId, answer);
    if (!success) return;

    // 如果是最後一題，完成考試
    if (currentIndex === totalQuestions - 1) {
        if (confirmSubmit()) {
            const completed = await completeExam(paperId);
            if (completed) {
                location.reload();
            }
        }
    } else {
        // 切換到下一題
        const nextIndex = currentIndex + 1;
        if (nextIndex < questions.length) {
            switchQuestion(paperId, nextIndex);
        } else {
            console.error(`Cannot switch to question ${nextIndex}, out of bounds`);
            alert('無法切換到下一題，請重新載入頁面。');
        }
    }
}

// 處理上一題
function handlePrevQuestion(paperId) {
    if (!paperId) {
        console.error('Paper ID is required');
        return;
    }

    if (!currentIndices.hasOwnProperty(paperId)) {
        console.warn(`Current index not initialized for paper ${paperId}`);
        return;
    }

    const currentIndex = currentIndices[paperId];
    if (currentIndex > 0) {
        switchQuestion(paperId, currentIndex - 1);
    }
}

// 獲取 CSRF Token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// AI 問答
async function askAI() {
    const questionInput = document.getElementById('ai_question');
    const responseDiv = document.getElementById('ai-response');
    const remainingDisplay = document.getElementById('ai-remaining-display');
    const paperIdInput = document.getElementById('current-paper-id');

    if (!questionInput || !responseDiv || !remainingDisplay || !paperIdInput) {
        console.error('Required AI elements not found');
        alert('頁面元素缺失，請重新載入頁面。');
        return;
    }

    const paperId = paperIdInput.value;
    const question = questionInput.value.trim();

    if (!question) {
        alert('請輸入問題！');
        questionInput.focus();
        return;
    }

    const aiBtn = document.querySelector('.ai-btn');
    if (!aiBtn) {
        console.error('AI button not found');
        return;
    }

    aiBtn.classList.add('loading');
    aiBtn.disabled = true;

    try {
        const response = await fetch('/room/ask_ai/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ paper_id: paperId, question: question }),
        });

        const data = await response.json();
        if (data.status === 'success') {
            responseDiv.innerHTML = data.response || 'AI 回應：無內容';
            if (data.remaining_limit !== undefined) {
                remainingDisplay.textContent = data.remaining_limit;
            }
            questionInput.value = '';
        } else {
            responseDiv.innerHTML = `❌ 錯誤：${data.message || '無法獲取 AI 回應'}`;
        }
    } catch (error) {
        console.error('Error asking AI:', error);
        responseDiv.innerHTML = '❌ 錯誤：無法連接到 AI 服務，請檢查網路連接。';
    } finally {
        aiBtn.classList.remove('loading');
        aiBtn.disabled = false;
    }
}