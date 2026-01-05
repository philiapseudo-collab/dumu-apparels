"""
Database models for Dumu Apparels Instagram Bot.

All models use SQLAlchemy 2.0 async syntax and inherit from Base.
"""

from sqlalchemy import (
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    Index,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from typing import Optional, List

from database import Base


class User(Base):
    """
    User model representing Instagram users interacting with the bot.
    
    Attributes:
        id: Primary key
        instagram_id: Unique Instagram user ID (indexed for fast lookups)
        name: User's display name (optional)
        phone_number: User's phone number for M-Pesa payments (optional)
        location: User's location for delivery estimates (optional)
        created_at: Timestamp when user record was created
    """
    
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    instagram_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Unique Instagram user ID"
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    conversation_logs: Mapped[List["ConversationLog"]] = relationship(
        "ConversationLog",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Product(Base):
    """
    Product model representing items available for sale.
    
    Attributes:
        id: Primary key
        name: Product name
        description: Product description for AI context (optional)
        category: Product category ('men' or 'women')
        type: Product type ('shoe' or 'clothing')
        price: Price in KES (DECIMAL(10, 2))
        image_url: URL to product image
        sizes: Available sizes as JSON array (e.g., ["40", "41", "42"])
        is_active: Whether product is active/visible (default: True)
    """
    
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Product category: 'men' or 'women'"
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Product type: 'shoe' or 'clothing'"
    )
    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Price in KES"
    )
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    sizes: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Available sizes as JSON array"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true"
    )
    
    # Relationships
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="product",
        cascade="all, delete-orphan"
    )


class Order(Base):
    """
    Order model representing customer purchases.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        product_id: Foreign key to Product
        amount: Total amount in KES (DECIMAL(10, 2))
        status: Order status ('pending', 'paid', 'failed')
        payment_provider: Payment provider used ('intasend' or 'pesapal')
        transaction_ref: Unique transaction reference from payment provider
        created_at: Timestamp when order was created
    """
    
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False
    )
    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Total amount in KES"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        server_default="pending",
        comment="Order status: 'pending', 'paid', 'failed'"
    )
    payment_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Payment provider: 'intasend' or 'pesapal'"
    )
    transaction_ref: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        comment="Unique transaction reference from payment provider"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="orders")
    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    
    # Indexes
    __table_args__ = (
        Index("idx_order_status", "status"),
        Index("idx_order_created_at", "created_at"),
    )


class ConversationLog(Base):
    """
    Conversation log model for tracking all bot interactions.
    
    Used for debugging AI responses and analyzing user behavior.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        message: Message content
        sender: Message sender ('user' or 'bot')
        timestamp: Timestamp when message was logged
    """
    
    __tablename__ = "conversation_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sender: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Message sender: 'user' or 'bot'"
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversation_logs")
    
    # Indexes
    __table_args__ = (
        Index("idx_conversation_user_timestamp", "user_id", "timestamp"),
    )

