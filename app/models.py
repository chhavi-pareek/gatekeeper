"""
Database models for the gaas-gateway application.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.sql import func
from typing import Optional
from app.database import Base


class Gateway(Base):
    """
    Gateway model representing a gateway instance.
    """
    __tablename__ = "gateways"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Route(Base):
    """
    Route model representing API routes.
    """
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False)  # GET, POST, PUT, DELETE, etc.
    gateway_id = Column(Integer, nullable=False, index=True)
    target_url = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    """
    User model representing a user in the system.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True, nullable=False)
    api_key_revealed = Column(Boolean, default=False, nullable=False)


class Service(Base):
    """
    Service model representing a service endpoint.
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)


class ApiKey(Base):
    """
    ApiKey model representing API keys for services.
    Supports multiple API keys per service.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    rate_limit_override = Column(Integer, nullable=True)  # Optional override for rate limit (legacy)
    rate_limit_requests = Column(Integer, nullable=True)  # Optional override: max requests per window
    rate_limit_window_seconds = Column(Integer, nullable=True)  # Optional override: time window in seconds
    price_per_request = Column(Float, default=0.001, nullable=False)  # Billing: price per request in dollars
    total_cost = Column(Float, default=0.0, nullable=False)  # Billing: total cost accumulated for this API key


class UsageLog(Base):
    """
    UsageLog model representing API usage logs.
    """
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    api_key = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BotDetectionLog(Base):
    """
    BotDetectionLog model for tracking bot detection results.
    """
    __tablename__ = "bot_detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, index=True)
    api_key = Column(String, nullable=False, index=True)
    bot_score = Column(Float, nullable=False)  # 0.0 to 1.0
    classification = Column(String, nullable=False)  # human, suspicious, bot
    user_agent = Column(String, nullable=True)
    action_taken = Column(String, nullable=False)  # allowed, flagged, blocked
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ServiceConfig(Base):
    """
    ServiceConfig model for service-level configuration.
    """
    __tablename__ = "service_configs"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False, unique=True, index=True)
    block_bots_enabled = Column(Boolean, default=False, nullable=False)
    bot_threshold = Column(Float, default=0.7, nullable=False)  # Score threshold for blocking

