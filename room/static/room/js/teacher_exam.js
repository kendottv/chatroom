// static/room/js/teacher_exam.js

let selectedQuestions = [];
let quill;

/** 切換標籤頁 */
function switchTab(tabId) {
  try {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
    const tab = document.getElementById(tabId);
    if (!tab) return;
    tab.classList.add('active');
    const btn = document.querySelector(`button[onclick="switchTab('${tabId}')"]`);
    if (btn) btn.classList.add('active');
    if (tabId === 'question-bank' || tabId === 'edit-exam') updateSelection();
  } catch (e) { console.error(e); }
}

function selectAll() {
  document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = true);
  updateSelection();
}

function clearSelection() {
  document.querySelectorAll('.question-checkbox').forEach(cb => cb.checked = false);
  updateSelection();
}

/** 更新選擇摘要與隱藏欄位 */
function updateSelection() {
  try {
    const checkboxes = document.querySelectorAll('.question-checkbox:checked');
    selectedQuestions = [];
    let totalPoints = 0, totalAiLimit = 0;
    checkboxes.forEach(cb => {
      const item = cb.closest('.question-item');
      selectedQuestions.push({
        id: cb.value,
        title: item.dataset.title,
        type: item.dataset.type,
        points: parseInt(item.dataset.points) || 0,
        ai_limit: parseInt(item.dataset.aiLimit) || 1,
      });
      totalPoints += parseInt(item.dataset.points) || 0;
      totalAiLimit += parseInt(item.dataset.aiLimit) || 1;
    });

    // 題庫總結
    const idMap1 = ['selected-count', 'total-questions'];
    idMap1.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = selectedQuestions.length; });
    const idMap2 = ['total-points']; idMap2.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = totalPoints; });
    const idMap3 = ['total-ai-limit']; idMap3.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = totalAiLimit; });

    // 創建/編輯考試總結
    const idMap4 = ['total-questions-exam', 'total-questions-edit-exam'];
    idMap4.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = selectedQuestions.length; });
    const idMap5 = ['total-points-exam', 'total-points-edit-exam'];
    idMap5.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = totalPoints; });
    const idMap6 = ['total-ai-limit-exam', 'total-ai-limit-edit-exam'];
    idMap6.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = totalAiLimit; });

    // 已選題目列表
    const selectedList = document.getElementById('selected-list');
    if (selectedList) {
      selectedList.innerHTML = selectedQuestions.map(q => `<p>題目: ${q.title} (${q.type}, ${q.points} 分, AI 次數: ${q.ai_limit})</p>`).join('');
    }

    // 隱藏欄位
    const createInput = document.getElementById('selected_questions_input');
    if (createInput) createInput.value = selectedQuestions.map(q => q.id).join(',');
    const editInput = document.getElementById('edit_selected_questions_input');
    if (editInput) editInput.value = selectedQuestions.map(q => q.id).join(',');

    // 按鈕狀態
    const createBtn = document.getElementById('create-exam-btn');
    if (createBtn) createBtn.disabled = selectedQuestions.length === 0;
    const editBtn = document.getElementById('edit-exam-btn');
    if (editBtn) editBtn.disabled = selectedQuestions.length === 0;
  } catch (e) { console.error(e); }
}

function showSelectedQuestions() {
  const summary = document.getElementById('selected-summary');
  if (summary) summary.style.display = selectedQuestions.length > 0 ? 'block' : 'none';
}

function confirmDelete() {
  return selectedQuestions.length > 0 && confirm('確定要刪除選定的題目嗎？');
}

/** 題型切換顯示 */
function updateForm() {
  try {
    const questionType = document.getElementById('question_type').value;
    const containers = { 'options_container': ['sc', 'mcq'], 'true_false_container': ['tf'], 'short_answer_container': ['sa'] };
    Object.entries(containers).forEach(([id, types]) => {
      const el = document.getElementById(id);
      if (el) el.style.display = types.includes(questionType) ? 'block' : 'none';
    });
    // 顯示/隱藏正確答案元件
    document.querySelectorAll('.sc-answer').forEach(el => el.style.display = (questionType === 'sc') ? 'inline' : 'none');
    document.querySelectorAll('.mcq-answer').forEach(el => el.style.display = (questionType === 'mcq') ? 'inline' : 'none');
    // 啟用/停用選項輸入
    document.querySelectorAll('.option-input').forEach(input => input.disabled = !['sc', 'mcq'].includes(questionType));
    // 是非 / 簡答輸入可用性
    document.querySelectorAll('#true_false_container input[type="radio"]').forEach(input => input.disabled = questionType !== 'tf');
    const saInput = document.querySelector('#short_answer_container textarea');
    if (saInput) saInput.disabled = questionType !== 'sa';
  } catch (e) { console.error(e); }
}

/** 表單驗證（新增/編輯題目用） */
function validateForm() {
  try {
    const questionType = document.getElementById('question_type').value;
    if (!quill) throw new Error('Quill not initialized');
    const editorContent = quill.root.innerHTML.trim();
    const textContent = quill.getText().trim();
    if (!textContent || textContent === '請輸入題目內容') {
      alert('請輸入題目內容！');
      return false;
    }

    const optionInputs = document.querySelectorAll('.option-input');
    const scAnswers = document.querySelectorAll('.sc-answer:checked');
    const mcqAnswers = document.querySelectorAll('.mcq-answer:checked');
    const tfAnswers = document.querySelectorAll('input[name="correct_answer"]:checked');
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

    if (parseInt(points) < 0 || parseInt(points) > 100) { alert('配分必須在 0 到 100 之間！'); return false; }
    if (parseInt(aiLimit) < 1) { alert('AI 問答次數限制必須至少為 1！'); return false; }

    document.getElementById('hidden_question').value = editorContent;
    return true;
  } catch (e) {
    console.error(e);
    alert('表單驗證失敗，請檢查控制台以獲取詳細資訊。');
    return false;
  }
}

/** 初始化 Quill */
function initializeQuill() {
  const editorContainer = document.getElementById('editor-container');
  if (!editorContainer) return;
  quill = new Quill('#editor-container', {
    theme: 'snow',
    modules: { toolbar: [['bold','italic','underline'], ['image','code-block'], [{'list':'ordered'},{'list':'bullet'}], ['clean']] }
  });
  quill.on('text-change', () => {
    const hiddenInput = document.getElementById('hidden_question');
    if (hiddenInput) hiddenInput.value = quill.root.innerHTML;
  });
  const editContent = editorContainer.innerHTML.trim();
  if (editContent && editContent !== '<p><br></p>') {
    quill.setContents(quill.clipboard.convert(editContent));
  }
}

/** 初始化「編輯考卷」已選題目 */
function initializeExamSelection() {
  const editInput = document.getElementById('edit_selected_questions_input');
  if (editInput && editInput.dataset.initialQuestions) {
    try {
      const ids = JSON.parse(editInput.dataset.initialQuestions).map(String);
      // 勾選題庫中的 checkbox
      document.querySelectorAll('.question-checkbox').forEach(cb => { cb.checked = ids.includes(cb.value); });
    } catch (e) { console.warn('initialQuestions 解析失敗', e); }
    updateSelection();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initializeQuill();
  updateForm();
  initializeExamSelection();
  updateSelection();

  // 表單驗證（題目建立/更新）
  document.querySelectorAll('form').forEach(form => {
    if (form.querySelector('#hidden_question') || form.querySelector('[name="action"]')) {
      form.addEventListener('submit', (ev) => {
        const action = form.querySelector('[name="action"]');
        if (!action || (action.value !== 'create_exam' && action.value !== 'edit_exam')) {
          if (!validateForm()) ev.preventDefault();
        } else {
          const selectedInput = form.querySelector('[name="selected_questions"]') || document.getElementById('edit_selected_questions_input');
          if (selectedInput && !selectedInput.value) {
            alert('請選擇至少一個題目！');
            ev.preventDefault();
          }
        }
      });
    }
  });

  document.querySelectorAll('.question-checkbox').forEach(cb => cb.addEventListener('change', updateSelection));
});
