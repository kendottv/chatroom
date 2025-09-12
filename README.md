ChatRoom – README

一個具備「出題、組卷、作答、批改、AI 提問額度控管」的教學評量系統（Django）。

目錄

    功能總覽

    系統架構與資料流

    資料模型（models）

    頁面與 API（views）

    AI 提問額度（Session）與非同步流程

    權限與身分



---功能總覽---

    使用者系統（自訂 CustomUser，附學號、頭像、班級）

    題目管理：單選（SC）／多選（MCQ）／是非（TF）／簡答（SA），支援圖片、配分、AI 問答次數

    考卷管理：選題組卷、發佈時間/作答時間/截止時間/試卷描述與時長

    學生作答：支援單題提交（自動判分）、整卷提交（計總分、產生成績）

    AI 問答：以每題 ai_limit 加總為該卷可用額度；提供同步（頁面）與非同步 webhook

    紀錄與審閱：InteractionLog 互動紀錄、StudentExamHistory 歷史、student_exam_history 調分

    基本頁面：首頁、登入/註冊、個人檔案（頭像更新）、歷史紀錄

---系統架構與資料流---
1) 出題與組卷（教師）

    教師登入 → 進入 /teacher_exam

    新增題目（POST）→ 寫入 ExamQuestion

    建立考卷（POST）→ 寫入 ExamPaper 並設定 Many-to-Many 題目

（可後續編輯考卷、題目；支援刪題）

2) 學生選卷與作答

    學生登入 → /select_exam 顯示可作答清單

    選定考卷 → session 記錄 selected_exam_paper_id → 導向 /exam

在 /exam：

    單題作答（AJAX/JSON）→ submit_single_answer 自動判分、更新總分

    整卷提交（POST）→ exam 內的提交分支，計算總分、更新 StudentExamHistory 與 ExamRecord

3) AI 問答（配額）

    題目 ai_limit 加總成「此卷可用 AI 次數」

    實作兩條路徑：

    頁面內同步提問：exam（action=ai_question）

    外部/非同步 webhook：ai_webhook（JSON POST），可帶 paper_id 以消耗額度

    皆會寫入 InteractionLog

---資料模型（models）---
#CustomUser
欄位	型態	說明
student_id	CharField(unique=True, null=True)	學號，多處做 FK 參照
avatar	ImageField	頭像
class_name	CharField	班級

注意：多處使用 to_field='student_id' 做關聯，因此建立使用者時務必填入 student_id。

#ExamQuestion
欄位	型態	說明
title	CharField	題目標題
content	TextField	題目內容（HTML <p> 已做簡易清洗）
question_type	CharField(choices=SC/MCQ/TF/SA)	題型
options	JSONField(null=True)	SC/MCQ 選項
is_correct	BooleanField(null=True)	TF 正解
correct_option_indices	TextField(null=True)	SC 單一索引字串；MCQ 逗號分隔
points	Integer(0~100)	配分
ai_limit	PositiveInteger	該題 AI 問答配額（0=無限制）
image	ImageField(null=True)	題目圖
created_by	FK(CustomUser)	建立者

#ExamPaper
欄位	型態	說明
title	CharField	考卷名稱
questions	M2M ExamQuestion	題目清單
total_points	Integer	總分（通常=題目配分總和）
created_by	FK(CustomUser)	建立者
publish_time/start_time/end_time	DateTime	發佈/開始/截止
duration_minutes	Integer(>=1)	時長（分鐘）
pdf_file	FileField(null=True)	試卷 PDF（選擇性）
description	TextField	描述

#InteractionLog
欄位	型態	說明
user	FK(CustomUser)	操作者
question / response	TextField	互動內容（含 AI 問答、作答紀錄摘要）
exam_question	FK(ExamQuestion,null=True)	關聯題目
exam_paper	FK(ExamPaper,null=True)	關聯考卷
score	Integer	此次互動得分（如單題得分）

#ExamRecord
|代表「某學生 × 某考卷」的一次作答紀錄（總分、是否完成）。|

欄位	型態	說明
student	FK(CustomUser, to_field='student_id')	注意以 student_id 做 FK
exam_paper	FK(ExamPaper)	考卷
score	Integer(0~100)	總分
submitted_at	DateTime(null=True)	提交時間
is_completed	Boolean	是否已完成
唯一性	unique_together(student, exam_paper)	同一學生每卷僅一筆總紀錄

#ExamAnswer
|代表「ExamRecord × 題目」的單題作答結果（答案內容、是否正確、得分）。|

欄位	型態	說明
exam_record	FK(ExamRecord, related_name='answer_details')	對應一份作答
exam_question	FK(ExamQuestion)	題目
student_answer	TextField(null=True)	學生答案（文字/逗號分隔/JSON 原樣字串化）
score	Integer(0~100)	此題得分
is_correct	Boolean	是否正確
唯一性	unique_together(exam_record, exam_question)	一題一筆

#StudentExamHistory
|彙整層級的歷史紀錄，便於列表瀏覽與人工調分後的總覽。|
特別：這裡以 student_id 與 exam_paper 建唯一；並冗餘儲存 student_name、exam_paper_name、question_content（摘要）。

---頁面與 API（views）---

URL 以範例表示，實際以你的 urls.py 為準（文中使用命名路由如 room:exam）。

公開/一般頁

home(request) → home.html

readme(request) → readme.html

身分/檔案

custom_login(request)：自訂登入（表單 CustomLoginForm），成功導向 room:home

register(request)：註冊（表單 CustomUserCreationForm），成功導向 room:home

profile(request)：顯示個人資料、作答紀錄；支援頭像更新（AvatarUpdateForm）

logout(request)：登出並導回 room:home

互動歷程

history(request)：登入者的 InteractionLog 列表

學生流程

select_exam(request) (GET/POST)

GET：列出「已發佈、未截止、且尚未完成」的考卷

POST：選定考卷 → 把 selected_exam_paper_id 寫入 session → 導向 room:exam

exam(request) (GET/POST, 登入限制)

GET：依 session 的 selected_exam_paper_id 或時間條件動態取卷；同時計算與初始化 AI 剩餘額度

POST JSON（content_type=application/json；action=submit_answer）：單題保存（教師端同步版）

POST 表單（action=ai_question）：頁面內 AI 提問，扣額度、記錄互動

POST 表單（整卷提交）：計總分、寫入 ExamRecord / ExamAnswer，更新 StudentExamHistory，導回 room:exam

submit_single_answer(request) (POST JSON)

給前端逐題 AJAX 使用

參數：paper_id, question_id, answer

自動判分、更新 ExamRecord.score 與 StudentExamHistory

回傳：{'status':'success','score':<int>}

---教師流程---

teacher_exam(request) (GET/POST, 需 staff)

新增/編輯題目（含 options、正解、配分、ai_limit、圖片）

建立/編輯考卷（時間、題目集合、總分）

刪題（多選）

student_exam_history(request) (GET/POST, 需 staff)

GET：列出所有學生在各卷的答案細節

POST（update_scores）：教師可逐題「調分」，系統同步重算總分並更新 History/Record

---AI 啟動與 Webhook---

ask_ai(request) (POST, 登入，csrf_exempt, async)

頁面內 AI 問答的非同步實作（透過 GeminiAPIWrapper.async_get_response）

把回覆渲染進 exam.html 的 TemplateResponse

ai_webhook(request) (POST JSON, csrf_exempt, async)

外部服務可呼叫

參數：

prompt（必填）

paper_id（選填；若提供會先扣額度）

session_key（選填；外部攜帶會避免觸發 request.user）

成功回傳：{"response": "...", "remaining": <int 可選>}

額度用盡：HTTP 429 + {"response":"已達 AI 提問上限！","remaining":0}

---AI 提問額度（Session）與非同步流程---
額度邏輯

每一張考卷的 AI 總額度 = 該卷所有題目的 ai_limit 加總

Session Key：ai_remaining_{paper_id}

扣點流程：

第一次使用時初始化（加總後寫入 session）

每次提問前先檢查並扣 1 次

若 AI 服務失敗 → 回補 1 次（見 _rollback_once_sync）

相關同步/輔助函式：

_sum_ai_limit_sync(paper_id)

_consume_once_sync(session, paper_id)

_rollback_once_sync(session, paper_id)

_session_touch(session)

非同步重點（Django async view）

ask_ai、ai_webhook 以 async def 實作，透過 asgiref.sync.sync_to_async(...) 包住：

session 存取（初始化/觸碰）

ORM 查詢/寫入（避免阻塞 event loop）

ask_ai 使用 TemplateResponse 並預先在 thread 渲染（await sync_to_async(resp.render)()），確保在 async 環境安全輸出 HTML。

---權限與身分---

學生：可見 select_exam → exam → 單題提交/整卷提交、AI 提問（受額度限制）、歷史（僅自己）

教師（is_staff=True）：可見 teacher_exam、student_exam_history，可新增題目/考卷、編輯、刪題、調分、強制結束考卷

未登入者：訪問 home/login/register/readme 等無限制頁