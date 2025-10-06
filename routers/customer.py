"""
お客様向けルーター

お客様専用のAPIエンドポイント
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from dependencies import get_current_customer
from models import User, Menu, Order
from schemas import (
    MenuResponse, MenuListResponse, MenuFilter,
    OrderCreate, OrderResponse, OrderListResponse,
    OrderHistoryResponse, OrderHistoryItem
)

router = APIRouter(prefix="/customer", tags=["お客様"])


@router.get("/menus", response_model=MenuListResponse, summary="メニュー一覧取得")
def get_menus(
    is_available: Optional[bool] = Query(None, description="利用可能フラグでフィルタ"),
    price_min: Optional[int] = Query(None, description="最低価格"),
    price_max: Optional[int] = Query(None, description="最高価格"),
    search: Optional[str] = Query(None, description="メニュー名で検索"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    メニュー一覧を取得
    
    - 利用可能なメニューのみ表示可能
    - 価格範囲やキーワードでフィルタリング
    - ページネーション対応
    """
    query = db.query(Menu)
    
    # フィルタリング
    if is_available is not None:
        query = query.filter(Menu.is_available == is_available)
    else:
        # お客様には利用可能なメニューのみ表示
        query = query.filter(Menu.is_available == True)
    
    if price_min is not None:
        query = query.filter(Menu.price >= price_min)
    
    if price_max is not None:
        query = query.filter(Menu.price <= price_max)
    
    if search:
        query = query.filter(Menu.name.contains(search))
    
    # 総件数を取得
    total = query.count()
    
    # ページネーション
    offset = (page - 1) * per_page
    menus = query.offset(offset).limit(per_page).all()
    
    return {"menus": menus, "total": total}


@router.get("/menus/{menu_id}", response_model=MenuResponse, summary="メニュー詳細取得")
def get_menu(
    menu_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    指定されたIDのメニュー詳細を取得
    """
    menu = db.query(Menu).filter(
        Menu.id == menu_id,
        Menu.is_available == True
    ).first()
    
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    return menu


@router.post("/orders", response_model=OrderResponse, summary="注文作成")
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    新しい注文を作成
    
    - **menu_id**: メニューID
    - **quantity**: 数量（1-10個）
    - **delivery_time**: 希望受取時間（任意）
    - **notes**: 備考（任意、500文字以内）
    """
    # メニューの存在確認
    menu = db.query(Menu).filter(
        Menu.id == order.menu_id,
        Menu.is_available == True
    ).first()
    
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found or not available"
        )
    
    # 合計金額を計算
    total_price = menu.price * order.quantity
    
    # 注文を作成
    db_order = Order(
        user_id=current_user.id,
        menu_id=order.menu_id,
        quantity=order.quantity,
        total_price=total_price,
        delivery_time=order.delivery_time,
        notes=order.notes
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    # メニュー情報も含めて返す
    db_order.menu = menu
    
    return db_order


@router.get("/orders", response_model=OrderHistoryResponse, summary="注文履歴取得")
def get_my_orders(
    status_filter: Optional[str] = Query(None, description="ステータスでフィルタ"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    自分の注文履歴を取得
    
    - JWT認証必須（current_userから取得）
    - 最新の注文から順に表示
    - ステータスでフィルタリング可能
    - ページネーション対応
    - パフォーマンス向上のためJOINを使用
    """
    # JOINを使用してメニュー情報を一度に取得
    query = db.query(
        Order.id,
        Order.quantity,
        Order.total_price,
        Order.status,
        Order.delivery_time,
        Order.notes,
        Order.ordered_at,
        Menu.name.label('menu_name'),
        Menu.image_url.label('menu_image_url')
    ).join(Menu, Order.menu_id == Menu.id).filter(
        Order.user_id == current_user.id
    )
    
    # ステータスフィルタ
    if status_filter:
        query = query.filter(Order.status == status_filter)
    
    # 最新順でソート
    query = query.order_by(desc(Order.ordered_at))
    
    # 総件数を取得
    total = query.count()
    
    # ページネーション
    offset = (page - 1) * per_page
    results = query.offset(offset).limit(per_page).all()
    
    # OrderHistoryItemオブジェクトに変換
    orders = []
    for result in results:
        order_item = OrderHistoryItem(
            id=result.id,
            quantity=result.quantity,
            total_price=result.total_price,
            status=result.status,
            delivery_time=result.delivery_time,
            notes=result.notes,
            ordered_at=result.ordered_at,
            menu_name=result.menu_name,
            menu_image_url=result.menu_image_url
        )
        orders.append(order_item)
    
    return OrderHistoryResponse(orders=orders, total=total)


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="注文詳細取得")
def get_my_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    指定された注文の詳細を取得
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # メニュー情報を含める
    order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()
    
    return order


@router.put("/orders/{order_id}/cancel", response_model=OrderResponse, summary="注文キャンセル")
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer)
):
    """
    注文をキャンセル
    
    注意: pendingステータスの注文のみキャンセル可能
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be cancelled"
        )
    
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    
    # メニュー情報を含める
    order.menu = db.query(Menu).filter(Menu.id == order.menu_id).first()
    
    return order