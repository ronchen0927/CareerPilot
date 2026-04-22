from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    """搜尋職缺的請求參數"""

    keyword: str = Field(min_length=1, description="搜尋關鍵字")
    pages: int = Field(default=5, ge=1, le=20, description="爬取頁數")
    areas: list[str] = Field(default_factory=list, description="地區代碼清單")
    experience: list[str] = Field(default_factory=list, description="經歷要求代碼清單（104 用）")
    sources: list[str] = Field(default_factory=lambda: ["104"], description="搜尋來源")
    categories: list[str] = Field(default_factory=list, description="職缺類別（Yourator 用）")
    salary_min: int = Field(default=0, ge=0, description="月薪下限篩選（元，Yourator 用）")
    salary_max: int = Field(default=0, ge=0, description="月薪上限篩選（元，Yourator 用）")
    cake_seniority: list[str] = Field(
        default_factory=list,
        description="年資等級（CakeResume 用，e.g. entry_level, mid_senior_level）",
    )
    cake_salary_min: int = Field(default=0, ge=0, description="月薪下限篩選（元，CakeResume 用）")
    cake_salary_max: int = Field(default=0, ge=0, description="月薪上限篩選（元，CakeResume 用）")


class JobListing(BaseModel):
    """單一職缺資料"""

    job: str = Field(description="職位名稱")
    date: str = Field(description="刊登日期")
    link: str = Field(description="職缺連結")
    company: str = Field(description="公司名稱")
    city: str = Field(description="城市")
    experience: str = Field(description="經歷要求")
    education: str = Field(description="最低學歷")
    salary: str = Field(description="薪水")
    salary_low: int = Field(default=0, description="薪水下限（元/月）")
    salary_high: int = Field(default=0, description="薪水上限（元/月）")
    is_featured: bool = Field(default=False, description="是否為精選職缺")
    source: str = Field(default="104", description="職缺來源")


class AlertCreateRequest(BaseModel):
    """建立新職缺提醒的請求參數"""

    keyword: str = Field(min_length=1, description="搜尋關鍵字")
    areas: list[str] = Field(default_factory=list, description="地區代碼清單")
    experience: list[str] = Field(default_factory=list, description="經歷要求代碼清單")
    pages: int = Field(default=3, ge=1, le=10, description="爬取頁數")
    min_salary: int = Field(default=0, ge=0, description="最低月薪篩選（元）")
    notify_type: str = Field(description="通知方式：line | webhook")
    notify_target: str = Field(min_length=1, description="Line Notify Token 或 Webhook URL")
    interval_minutes: int = Field(default=60, ge=30, le=1440, description="檢查間隔（分鐘）")


class JobSearchResponse(BaseModel):
    """搜尋結果回應"""

    results: list[JobListing] = Field(default=[], description="職缺列表")
    count: int = Field(default=0, description="搜尋結果數量")
    elapsed_time: float = Field(default=0.0, description="搜尋耗時（秒）")


class JobEvaluateRequest(BaseModel):
    """AI 評分請求"""

    job: JobListing = Field(description="要評分的職缺")
    user_cv: str = Field(default="", description="求職者履歷或背景描述（選填）")
    job_description: str = Field(default="", description="職缺內文全文（選填）")


class JobEvaluateTextRequest(BaseModel):
    """AI 評分請求（純文字模式）"""

    job_text: str = Field(min_length=10, description="貼上的職缺描述文字")
    user_cv: str = Field(default="", description="求職者履歷或背景描述（選填）")


class EvaluationDimensions(BaseModel):
    """AI 評分多維度細項"""

    job_category: str = Field(description="職位分類")
    level_move: str = Field(description="職級策略：升遷 | 平調 | 後退")
    skill_match: float = Field(ge=1, le=5, description="技能匹配度 (1-5)")
    salary_fairness: float = Field(ge=1, le=5, description="薪資合理性 (1-5)")
    growth_potential: float = Field(ge=1, le=5, description="成長空間 (1-5)")
    location_flexibility: float = Field(ge=1, le=5, description="地理/遠端彈性 (1-5)")
    overall_score: float = Field(ge=1, le=5, description="綜合推薦度 (1-5)")


class JobEvaluateResponse(BaseModel):
    """AI 評分結果"""

    score: str = Field(description="評分（A/B+/C- 等）")
    summary: str = Field(description="一句話總結")
    match_points: list[str] = Field(default=[], description="優勢/符合點")
    gap_points: list[str] = Field(default=[], description="落差或風險")
    recommendation: str = Field(description="投遞建議")
    from_cache: bool = Field(default=False, description="是否來自快取（未重新呼叫 AI）")
    dimensions: EvaluationDimensions | None = Field(default=None, description="多維度評分細項")


class CoverLetterRequest(BaseModel):
    """AI 推薦信請求"""

    job_text: str = Field(min_length=10, description="職缺描述文字")
    user_cv: str = Field(default="", description="求職者履歷或背景描述")


class CoverLetterResponse(BaseModel):
    """AI 推薦信結果"""

    id: int = Field(description="資料庫記錄 ID")
    letter: str = Field(description="推薦信內文")


class CoverLetterRecord(BaseModel):
    """推薦信歷史紀錄（單筆）"""

    id: int = Field(description="記錄 ID")
    job_text_snippet: str = Field(description="職缺描述前 80 字")
    job_text: str = Field(description="職缺描述全文")
    letter: str = Field(description="推薦信內文")
    created_at: str = Field(description="生成時間")


class ResumeRewriteRequest(BaseModel):
    """AI 履歷改寫請求"""

    job_text: str = Field(min_length=10, description="職缺描述文字")
    user_cv: str = Field(min_length=1, description="原始履歷內容")
    job_url: str | None = Field(default=None, description="職缺原始網址（選填）")


class ResumeRewriteResponse(BaseModel):
    """AI 履歷改寫結果"""

    id: int = Field(description="資料庫記錄 ID")
    result: str = Field(description="改寫後的履歷全文（語言與原始履歷一致）")


class ResumeRewriteRecord(BaseModel):
    """履歷改寫歷史紀錄（單筆）"""

    id: int = Field(description="記錄 ID")
    job_text_snippet: str = Field(description="職缺描述前 80 字")
    job_text: str = Field(description="職缺描述全文")
    job_url: str | None = Field(default=None, description="職缺網址（若有）")
    original_cv: str = Field(description="原始履歷內容")
    result: str = Field(description="改寫後的履歷全文")
    created_at: str = Field(description="建立時間")


class EvaluationRecord(BaseModel):
    """評分歷史紀錄（單筆）"""

    id: int = Field(description="記錄 ID")
    job_text_snippet: str = Field(description="職缺描述前 80 字")
    job_text: str = Field(description="職缺描述全文")
    job_url: str | None = Field(default=None, description="職缺網址（若有）")
    score: str = Field(description="評分")
    summary: str = Field(description="一句話總結")
    match_points: list[str] = Field(default=[], description="優勢/符合點")
    gap_points: list[str] = Field(default=[], description="落差或風險")
    recommendation: str = Field(description="投遞建議")
    created_at: str = Field(description="評分時間")
    dimensions: EvaluationDimensions | None = Field(default=None, description="多維度評分細項")


class CVSuggestKeywordsRequest(BaseModel):
    """AI 關鍵字建議請求"""

    cv_text: str = Field(min_length=10, max_length=20000, description="履歷純文字")


class CVSuggestKeywordsResponse(BaseModel):
    """AI 關鍵字建議結果"""

    keywords: list[str] = Field(description="3-5 組建議職位關鍵字")


# ── RAG Models ────────────────────────────────────────────────────────────────


class RagDocumentCreate(BaseModel):
    doc_type: str = Field(description="文件類型: project | interview_question | experience | other")
    content: str = Field(min_length=10, description="文件內容")


class RagDocumentResponse(BaseModel):
    id: int
    doc_type: str
    content: str
    created_at: str


class MockInterviewRequest(BaseModel):
    job_text: str = Field(description="職缺描述全文")


class MockInterviewResponse(BaseModel):
    technical_questions: list[str] = Field(description="技術面試題")
    behavioral_questions: list[str] = Field(description="行為面試題")
    tips: str = Field(description="準備建議")


class ResumeMatchRequest(BaseModel):
    job_text: str = Field(description="職缺描述全文")
    user_cv: str = Field(default="", description="求職者履歷或背景描述")


class ResumeMatchResponse(BaseModel):
    gap_analysis: str = Field(description="能力缺口分析")
    answer_strategy: str = Field(description="答題策略")
    match_score: int = Field(ge=0, le=100, description="契合度分數")
