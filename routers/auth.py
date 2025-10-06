"""
認証ルーター

ユーザー認証関連のAPIエンドポイント
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, TokenResponse, UserResponse, SuccessResponse
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["認証"])


@router.post("/register", response_model=UserResponse, summary="ユーザー登録")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    新しいユーザーを登録
    
    - **username**: ユーザー名（3-50文字、一意）
    - **email**: メールアドレス（一意）
    - **password**: パスワード（6文字以上）
    - **full_name**: 氏名
    - **role**: ロール（customer または store）
    """
    # ユーザー名の重複チェック
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # メールアドレスの重複チェック
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # パスワードをハッシュ化
    hashed_password = get_password_hash(user.password)
    
    # ユーザーを作成
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=TokenResponse, summary="ログイン")
def login_for_access_token(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    ユーザーログインしてアクセストークンを取得
    
    - **username**: ユーザー名
    - **password**: パスワード
    
    成功時は、アクセストークンとユーザー情報を返します。
    """
    print(f"Login attempt - Username: {user_credentials.username}")
    
    # ユーザーを検索
    user = db.query(User).filter(User.username == user_credentials.username).first()
    
    if not user:
        print(f"User not found: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"User found: {user.username}, checking password...")
    
    # パスワード検証
    if not verify_password(user_credentials.password, user.hashed_password):
        print(f"Password verification failed for user: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Password verified for user: {user_credentials.username}")
    
    # ユーザーがアクティブか確認
    if not user.is_active:
        print(f"User is inactive: {user_credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    print(f"User is active: {user_credentials.username}")
    
    # アクセストークンを作成
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    print(f"Login successful for user: {user_credentials.username}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.post("/logout", response_model=SuccessResponse, summary="ログアウト")
def logout():
    """
    ログアウト
    
    注意: JWTはステートレスなため、サーバー側では特別な処理は行いません。
    クライアント側でトークンを削除してください。
    """
    return {"success": True, "message": "Successfully logged out"}