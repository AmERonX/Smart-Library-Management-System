"""
Authentication routes for user registration and login.
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import User
from schemas import UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse
from auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    try:
        logger.info(f"Registration request received for username: {request.username}, email: {request.email}, role: {request.role}")
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == request.username) | (User.email == request.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(request.password)
        
        # Ensure role is valid (database uses ENUM, so we need to validate)
        valid_roles = ['student', 'admin', 'librarian']
        user_role = (request.role or "student").lower()
        if user_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}. Must be one of: {', '.join(valid_roles)}"
            )
        
        # Use raw SQL to insert with explicit ENUM casting to avoid type mismatch
        # PostgreSQL ENUM requires explicit casting when using raw SQL
        from sqlalchemy import text
        try:
            # Insert user with explicit ENUM cast using CAST function for better compatibility
            # SQLAlchemy text() uses :param style binding
            result = db.execute(
                text("""
                    INSERT INTO lms_core.users (username, email, password_hash, role, created_at)
                    VALUES (:username, :email, :password_hash, CAST(:role AS lms_core.user_role), NOW())
                    RETURNING user_id, username, email, role, created_at, updated_at
                """),
                {
                    "username": request.username,
                    "email": request.email,
                    "password_hash": hashed_password,
                    "role": user_role
                }
            )
            user_row = result.fetchone()
            db.commit()
            
            logger.info(f"User registered: {user_row[1]}")
            
            # Create UserResponse from the returned row
            return UserResponse(
                user_id=user_row[0],
                username=user_row[1],
                email=user_row[2],
                role=user_row[3],
                created_at=user_row[4]
            )
        except Exception as insert_error:
            db.rollback()
            error_msg = str(insert_error)
            logger.error(f"Database insert error: {error_msg}", exc_info=True)
            
            # Check for specific error types
            if "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already registered"
                )
            elif "invalid input value for enum" in error_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid role: {user_role}. Must be one of: {', '.join(valid_roles)}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create user: {error_msg}"
                )
        
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Error registering user: {error_msg}", exc_info=True)
        # Include actual error in response for debugging (in development)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {error_msg}"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login user and return JWT token.
    """
    try:
        logger.info(f"Login request received for username: {request.username}")
        # Find user by username
        user = db.query(User).filter(User.username == request.username).first()
        
        if not user or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": user.user_id, "role": user.role},
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.username}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                role=user.role,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to login user"
        )

