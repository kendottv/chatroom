// 當前題目索引（每個考卷獨立）
const currentIndices = {};

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
            switchQuestion(paperId, 0); // 初始化顯示第一題
            updateNavigationButtons(paperId);
            setupEventListeners(paperId);
        }
    });
});

// 設置事件監聽器
function setupEventListeners(paperId) {
    const prevBtn = document.getElementById(`prev-question-${paperId}`);
    const nextBtn = document.getElementById(`next-question-${paperId}`);

    if (prevBtn) {
        prevBtn.addEventListener('click', () => handlePrevQuestion(paperId));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => handleNextQuestion(paperId));
    }

    // 表單提交事件
    const form = document.getElementById(`exam-form-${paperId}`);
    if (form) {
        form.addEventListener('submit', (event) => {
            event.preventDefault();
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
        });
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
        console.error(`Invalid question index: ${index} for paper ${paperId}`);
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

    const currentIndex = currentIndices[paperId] || 0;
    prevBtn.disabled = currentIndex === 0;
    nextBtn.disabled = currentIndex === totalQuestions - 1;
    currentQuestionDisplay.textContent = `第 ${currentIndex + 1} 題 / ${totalQuestions} 題`;
    nextBtn.textContent = currentIndex === totalQuestions - 1 ? '提交並結束' : '下一題';
}

// 獲取答案
function getAnswer(container) {
    const questionId = container.getAttribute('data-question-id');
    let answer = null;

    // 檢查多選題
    const checkboxes = container.querySelectorAll(`input[name="answer-${questionId}[]"]:checked`);
    if (checkboxes.length > 0) {
        answer = Array.from(checkboxes).map(cb => cb.value);
    }
    // 檢查單選題
    else {
        const radio = container.querySelector(`input[name="answer-${questionId}"]:checked`);
        if (radio) {
            answer = radio.value;
        }
        // 檢查文本域
        else {
            const textarea = container.querySelector(`textarea[name="answer-${questionId}"]`);
            if (textarea) {
                answer = textarea.value.trim() || '';
            }
            // 檢查文本輸入框
            else {
                const textInput = container.querySelector(`input[name="answer-${questionId}"]`);
                if (textInput) {
                    answer = textInput.value.trim() || '';
                }
            }
        }
    }

    return answer;
}

// 提交單題答案
async function submitSingleAnswer(paperId, questionId) {
    const currentQuestion = document.querySelector(`.exam-paper[data-paper-id="${paperId}"] .question-container[style*="display: block"]`);
    if (!currentQuestion) {
        console.error('No active question found');
        return false;
    }

    const answer = getAnswer(currentQuestion);
    const csrfToken = getCookie('csrftoken');

    try {
        const response = await fetch('/submit_single_answer/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                paper_id: paperId,
                question_id: questionId || currentQuestion.getAttribute('data-question-id'),
                answer: answer
            }),
        });

        const data = await response.json();
        if (data.status === 'success') {
            console.log(`Submission successful for question ${questionId}, score: ${data.score}`);
            return true;
        } else {
            console.error(`Submission failed: ${data.message}`);
            alert(data.message || '提交失敗，請重試。');
            return false;
        }
    } catch (error) {
        console.error('Error submitting answer:', error);
        alert('提交答案時發生錯誤，請重試。');
        return false;
    }
}

// 處理下一題
async function handleNextQuestion(paperId) {
    const questions = document.querySelectorAll(`.exam-paper[data-paper-id="${paperId}"] .question-container`);
    if (!questions.length) {
        console.error(`No questions found for paper ${paperId}`);
        alert('無可用題目，請聯繫管理員。');
        return;
    }

    const currentIndex = currentIndices[paperId] || 0;
    if (currentIndex < 0 || currentIndex >= questions.length) {
        console.error(`Invalid current index: ${currentIndex} for paper ${paperId}`);
        alert('題目索引錯誤，請重新載入頁面。');
        return;
    }

    const currentQuestion = questions[currentIndex];
    const questionId = currentQuestion.getAttribute('data-question-id');

    // 自動提交當前答案
    const success = await submitSingleAnswer(paperId, questionId);
    if (!success) return;

    // 如果是最後一題，直接提交考卷
    if (currentIndex === questions.length - 1) {
        const form = document.getElementById(`exam-form-${paperId}`);
        if (form) {
            form.submit();
        }
    } else {
        // 切換到下一題
        const nextIndex = currentIndex + 1;
        switchQuestion(paperId, nextIndex);
    }
}

// 處理上一題
function handlePrevQuestion(paperId) {
    const currentIndex = currentIndices[paperId] || 0;
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
function askAI() {
    const question = document.getElementById('ai_question').value.trim();
    if (!question) {
      alert('請輸入問題');
      return;
    }
  
    const responseDiv = document.getElementById('ai-response');
    responseDiv.innerHTML = '🤖 正在處理您的問題，請稍候...';
  
    fetch('/webhooks/ai/', {
      method: 'POST',
      credentials: 'include', // ★ 同網域帶 cookie，後端才能用 request.session
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
      },
      body: JSON.stringify({ prompt: question }) // 同網域不必傳 session_key
    })
    .then(r => r.json())
    .then(data => {
      responseDiv.innerHTML = data.response || '無法獲得回應，請稍後再試。';
    })
    .catch(err => {
      console.error('Error:', err);
      responseDiv.innerHTML = '❌ 發生錯誤，請稍後再試。';
    });
  }