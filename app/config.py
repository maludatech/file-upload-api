from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    rate_limit_storage_uri: str = "memory://"
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    s3_endpoint_url: str | None = None
    s3_bucket_name: str
    s3_region: str = "us-east-1"
    s3_access_key_id: str
    s3_secret_access_key: str

    max_upload_size_mb: int = 25

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()  # type: ignore[call-arg]
