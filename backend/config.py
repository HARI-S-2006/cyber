"""Configuration management for the Cyber Threat Visualizer."""
import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Redis
    redis_host: str = Field(default="localhost", description="Redis server host")
    redis_port: int = Field(default=6379, description="Redis server port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    
    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Sniffer
    sniffer_interface: str = Field(
        default="",
        description="Network interface to sniff (empty for auto-detect)"
    )
    sniffer_bpf_filter: str = Field(
        default="ip",
        description="BPF filter for packet capture"
    )
    sniffer_packet_buffer_size: int = Field(
        default=10000,
        description="Maximum packets to buffer in memory"
    )
    
    # Feature Extraction
    feature_window_seconds: int = Field(
        default=60,
        description="Time window for feature aggregation"
    )
    feature_min_packets: int = Field(
        default=10,
        description="Minimum packets per flow for feature extraction"
    )

    # ML Model
    ml_model_path: str = Field(
        default="./ml/models/anomaly_detector.pkl",
        description="Path to trained ML model"
    )
    ml_contamination: float = Field(
        default=0.001,
        description="Expected anomaly ratio (0.001 = 0.1%)"
    )
    ml_n_estimators: int = Field(
        default=100,
        description="Number of trees in Isolation Forest"
    )
    ml_max_samples: str = Field(
        default="auto",
        description="Max samples for training"
    )
    ml_retrain_interval_hours: int = Field(
        default=24,
        description="Hours between model retraining"
    )

    # API
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_workers: int = Field(default=1, description="Number of API workers")
    api_cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins"
    )

    # Frontend
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for CORS"
    )

    # GeoIP
    geoip_cache_ttl: int = Field(
        default=86400,
        description="GeoIP cache TTL in seconds (24 hours)"
    )
    geoip_api_url: str = Field(
        default="http://ip-api.com/json/",
        description="GeoIP API endpoint"
    )
    geoip_rate_limit: int = Field(
        default=45,
        description="Requests per minute limit for GeoIP API"
    )

    # Redis Channels
    channel_raw_packets: str = Field(default="network:raw", description="Raw packet channel")
    channel_features: str = Field(default="network:features", description="Extracted features channel")
    channel_threats: str = Field(default="network:threats", description="Detected threats channel")
    channel_stats: str = Field(default="network:stats", description="Statistics channel")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Log format"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()