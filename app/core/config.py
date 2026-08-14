from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "DocTime API"
    APP_VERSION: str = "1.0.0"

    SECRET_KEY: str = "change-this-in-production-very-secure-key-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (60 * 24)

    DATABASE_URL: str = "sqlite:///./doctime.db"

    # Payment gateways
    PAYMENT_GATEWAY: str = "mellat"  # mellat | parsian
    PAYMENT_CALLBACK_BASE_URL: str = "http://localhost:8000"

    # Mellat
    MELLAT_TERMINAL_ID: str = ""
    MELLAT_USERNAME: str = ""
    MELLAT_PASSWORD: str = ""
    MELLAT_OPERATIONAL_WSDL: str = "https://bpm.shaparak.ir/pgwchannel/services/pgw?wsdl"
    MELLAT_STARTPAY_URL: str = "https://bpm.shaparak.ir/pgwchannel/startpay.mellat"

    # Parsian placeholders
    PARSIAN_MERCHANT_ID: str = ""
    PARSIAN_TERMINAL_ID: str = ""
    PARSIAN_API_KEY: str = ""
    PARSIAN_PAYMENT_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
