const currentIndices = {};

document.addEventListener('DOMContentLoaded', () => {
    const paper = document.querySelector('.exam-paper');
    if (paper) {
        const paperId = paper.getAttribute('data-paper-id');
        if (paperId) {
            currentIndices[paperId] = 0;
            switchQuestion(paperId, 0);
            updateNavigationButtons(paperId);
            setupEventListeners(paperId);
        }
    }

    const aiRemaining = parseInt(document.getElementById('ai-remaining-display')?.dataset.limit) || 0;
    const aiBtn = document.querySelector('.ai-btn');
    if (aiRemaining <= 0) {
        aiBtn.disabled = true;
        aiBtn.textContent = '已達上限';
    }
});

function setupEventListeners(paperId) {
    const prevBtn = document.getElementById(`prev-question-${paperId}`);
    const nextBtn = document.getElementById(`next-question-${paperId}`);

    if (prevBtn) {
        prevBtn.addEventListener('click', () => handlePrevQuestion(paperId));
    }
    if (nextBtn) {
        nextBtn.addEventListener('click', () => handleNextQuestion(paperId));
    }

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
    return true;
}

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

function getAnswer(container) {
    const questionId = container.getAttribute('data-question-id');
    let answer = null;

    const checkboxes = container.querySelectorAll(`input[name="answer-${questionId}[]"]:checked`);
    if (checkboxes.length > 0) {
        answer = Array.from(checkboxes).map(cb => cb.value);
    } else {
        const radio = container.querySelector(`input[name="answer-${questionId}"]:checked`);
        if (radio) {
            answer = radio.value;
        } else {
            const textarea = container.querySelector(`textarea[name="answer-${questionId}"]`);
            if (textarea) {
                answer = textarea.value.trim() || '';
            } else {
                const textInput = container.querySelector(`input[name="answer-${questionId}"]`);
                if (textInput) {
                    answer = textInput.value.trim() || '';
                }
            }
        }
    }

    return answer;
}

async function submitSingleAnswer(paperId, questionId) {
    const currentQuestion = document.querySelector(`.exam-paper[data-paper-id="${paperId}"] .question-container[style*="display: block"]`);
    if (!currentQuestion) {
        console.error('No active question found');
        return false;
    }

    const answer = getAnswer(currentQuestion);
    const csrfToken = getCookie('csrftoken');

    try {
        const response = await fetch(`/exam/${paperId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                action: 'submit_answer',
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

    const success = await submitSingleAnswer(paperId, questionId);
    if (!success) return;

    if (currentIndex === questions.length - 1) {
        const form = document.getElementById(`exam-form-${paperId}`);
        if (form) {
            form.submit();
        }
    } else {
        const nextIndex = currentIndex + 1;
        switchQuestion(paperId, nextIndex);
    }
}

function handlePrevQuestion(paperId) {
    const currentIndex = currentIndices[paperId] || 0;
    if (currentIndex > 0) {
        switchQuestion(paperId, currentIndex - 1);
    }
}

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

async function callWebhook(prompt, paperId) {
  const payload = paperId ? { prompt, paper_id: paperId } : { prompt };
  const res = await fetch('/webhooks/ai/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.response || data.error || `HTTP ${res.status}`;
    const err = new Error(msg); err.status = res.status; err.payload = data;
    throw err;
  }
  return data;
}

async function askAI() {
  const qEl  = document.getElementById('ai_question');
  const resp = document.getElementById('ai-response');
  const left = document.getElementById('ai-remaining-display');
  const btn  = document.querySelector('.ai-btn');
  const paperId = document.getElementById('current-paper-id')?.value || '';

  const question = (qEl?.value || '').trim();
  if (!question) { alert('請輸入問題'); return; }

  resp.innerHTML = '🤖 正在處理您的問題，請稍候...';
  if (btn) { btn.disabled = true; btn.dataset.originalText = btn.textContent; btn.textContent = '處理中…'; }

  try {
    const data = await callWebhook(question, paperId || null);
    resp.innerHTML = data.response || '無法獲得回應，請稍後再試。';

    if (typeof data.remaining === 'number' && left) {
      left.textContent = `${data.remaining} 次`;
      if (btn) {
        if (data.remaining <= 0) { btn.disabled = true; btn.textContent = '已達上限'; }
        else { btn.disabled = false; btn.textContent = btn.dataset.originalText || '💬 向 AI 提問'; }
      }
    } else if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.originalText || '💬 向 AI 提問';
    }
  } catch (err) {
    console.error(err);
    resp.innerHTML = err.message || '❌ 發生錯誤，請稍後再試。';

    const rem = err?.payload?.remaining;
    if (typeof rem === 'number' && left) {
      left.textContent = `${rem} 次`;
      if (btn) {
        if (rem <= 0) { btn.disabled = true; btn.textContent = '已達上限'; }
        else { btn.disabled = false; btn.textContent = btn.dataset.originalText || '💬 向 AI 提問'; }
      }
    } else if (btn) {
      btn.disabled = false;
      btn.textContent = btn.dataset.originalText || '💬 向 AI 提問';
    }
  }
}