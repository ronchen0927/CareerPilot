from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    """搜尋職缺的請求參數"""

    keyword: str = Field(min_length=1, description="搜尋關鍵字")
    pages: int = Field(default=5, ge=1, le=20, description="爬取頁數")
    areas: list[str] = Field(default_factory=list, description="地區代碼清單")
    experience: list[str] = Field(default_factory=list, description="經歷要求代碼清單")
    sources: list[str] = Field(
        default_factory=lambda: ["104"], description="搜尋來源：104 | CakeResume"
    )


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
    source: str = Field(default="104", description="職缺來源：104 | CakeResume")


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


class JobEvaluateTextRequest(BaseModel):
    """AI 評分請求（純文字模式）"""

    job_text: str = Field(min_length=10, description="貼上的職缺描述文字")
    user_cv: str = Field(default="", description="求職者履歷或背景描述（選填）")


class JobEvaluateResponse(BaseModel):
    """AI 評分結果"""

    score: str = Field(description="評分（A/B+/C- 等）")
    summary: str = Field(description="一句話總結")
    match_points: list[str] = Field(default=[], description="優勢/符合點")
    gap_points: list[str] = Field(default=[], description="落差或風險")
    recommendation: str = Field(description="投遞建議")
    from_cache: bool = Field(default=False, description="是否來自快取（未重新呼叫 AI）")


class EvaluationRecord(BaseModel):
    """評分歷史紀錄（單筆）"""

    id: int = Field(description="記錄 ID")
    job_text_snippet: str = Field(description="職缺描述前 80 字")
    job_url: str | None = Field(default=None, description="職缺網址（若有）")
    score: str = Field(description="評分")
    summary: str = Field(description="一句話總結")
    match_points: list[str] = Field(default=[], description="優勢/符合點")
    gap_points: list[str] = Field(default=[], description="落差或風險")
    recommendation: str = Field(description="投遞建議")
    created_at: str = Field(description="評分時間")
