from pydantic import BaseModel, Field


class JobSearchRequest(BaseModel):
    """搜尋職缺的請求參數"""

    keyword: str = Field(min_length=1, description="搜尋關鍵字")
    pages: int = Field(default=5, ge=1, le=20, description="爬取頁數")
    areas: list[str] = Field(default_factory=list, description="地區代碼清單")
    experience: list[str] = Field(default_factory=list, description="經歷要求代碼清單")


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
