"""
API契約定義 - Single Source of Truth

このファイルは、バックエンドAPI（FastAPI）とフロントエンドの間の
すべてのデータ構造を定義する唯一の信頼できる情報源です。

編集時のルール:
1. 頻繁にgit pullを実行してコンフリクトを避ける
2. 小さな変更単位でPull Requestを作成する
3. 変更前にチームメンバーに事前連絡する
4. 変更後は必ずTypeScript型定義を再生成する
"""

from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ===== 共通型定義 =====

class SuccessResponse(BaseModel):
    """成功時の共通レスポンス"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """エラー時の共通レスポンス"""
    success: bool = False
    message: str
    detail: Optional[str] = None


# ===== 認証関連 =====

class UserCreate(BaseModel):
    """ユーザー作成時のリクエスト"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(customer|store)$")


class UserLogin(BaseModel):
    """ログイン時のリクエスト"""
    username: str
    password: str


class UserResponse(BaseModel):
    """ユーザー情報のレスポンス"""
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """認証トークンのレスポンス"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ===== メニュー関連 =====

class MenuBase(BaseModel):
    """メニューの基本情報"""
    name: str = Field(..., min_length=1, max_length=255)
    price: int = Field(..., ge=1)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: bool = True


class MenuCreate(MenuBase):
    """メニュー作成時のリクエスト"""
    pass


class MenuUpdate(BaseModel):
    """メニュー更新時のリクエスト"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None


class MenuResponse(MenuBase):
    """メニュー情報のレスポンス"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuListResponse(BaseModel):
    """メニュー一覧のレスポンス"""
    menus: List[MenuResponse]
    total: int


# ===== 注文関連 =====

class OrderBase(BaseModel):
    """注文の基本情報"""
    menu_id: int = Field(..., ge=1)
    quantity: int = Field(..., ge=1, le=10)
    delivery_time: Optional[time] = None
    notes: Optional[str] = Field(None, max_length=500)


class OrderCreate(OrderBase):
    """注文作成時のリクエスト"""
    pass


class OrderStatusUpdate(BaseModel):
    """注文ステータス更新時のリクエスト"""
    status: str = Field(..., pattern="^(pending|confirmed|preparing|ready|completed|cancelled)$")


class OrderResponse(BaseModel):
    """注文情報のレスポンス"""
    id: int
    user_id: int
    menu_id: int
    quantity: int
    total_price: int
    status: str
    delivery_time: Optional[time]
    notes: Optional[str]
    ordered_at: datetime
    updated_at: datetime
    
    # メニュー情報も含める
    menu: MenuResponse
    
    # お客様情報（店舗向けのみ）
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """注文一覧のレスポンス"""
    orders: List[OrderResponse]
    total: int


class OrderSummary(BaseModel):
    """注文サマリー（ダッシュボード用）"""
    total_orders: int
    pending_orders: int
    confirmed_orders: int
    preparing_orders: int
    ready_orders: int
    completed_orders: int
    cancelled_orders: int
    total_sales: int


# ===== 注文履歴関連 =====

class OrderHistoryItem(BaseModel):
    """注文履歴の項目 - 軽量版"""
    id: int
    quantity: int
    total_price: int
    status: str
    delivery_time: Optional[time]
    notes: Optional[str]
    ordered_at: datetime
    
    # 関連メニュー情報
    menu_name: str
    menu_image_url: Optional[str]

    class Config:
        from_attributes = True


class OrderHistoryResponse(BaseModel):
    """注文履歴のレスポンス"""
    orders: List[OrderHistoryItem]
    total: int


# ===== レポート関連 =====

class DailySalesReport(BaseModel):
    """日別売上レポート"""
    date: str  # YYYY-MM-DD format
    total_orders: int
    total_sales: int
    popular_menu: Optional[str] = None


class MenuSalesReport(BaseModel):
    """メニュー別売上レポート"""
    menu_id: int
    menu_name: str
    total_quantity: int
    total_sales: int


class SalesReportResponse(BaseModel):
    """売上レポートのレスポンス"""
    period: str  # "daily", "weekly", "monthly"
    start_date: str
    end_date: str
    daily_reports: List[DailySalesReport]
    menu_reports: List[MenuSalesReport]
    total_sales: int
    total_orders: int


# ===== 検索・フィルタ関連 =====

class OrderFilter(BaseModel):
    """注文一覧フィルタ"""
    status: Optional[str] = None
    user_id: Optional[int] = None
    menu_id: Optional[int] = None
    start_date: Optional[str] = None  # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


class MenuFilter(BaseModel):
    """メニュー一覧フィルタ"""
    is_available: Optional[bool] = None
    price_min: Optional[int] = Field(None, ge=0)
    price_max: Optional[int] = Field(None, ge=0)
    search: Optional[str] = None
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


# ===== ページネーション =====

class PaginationInfo(BaseModel):
    """ページネーション情報"""
    page: int
    per_page: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel):
    """ページネーション付きレスポンスの基底クラス"""
    pagination: PaginationInfo