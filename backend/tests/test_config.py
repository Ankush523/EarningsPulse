"""Settings and production configuration tests."""

from app.config import Settings


def test_frontend_url_merged_into_cors_origins():
    settings = Settings(
        frontend_url="https://earningspulse.vercel.app",
        cors_origins=["http://localhost:3000"],
    )
    assert "https://earningspulse.vercel.app" in settings.cors_origins
    assert "http://localhost:3000" in settings.cors_origins


def test_frontend_url_not_duplicated_in_cors():
    settings = Settings(
        frontend_url="https://earningspulse.vercel.app",
        cors_origins=[
            "http://localhost:3000",
            "https://earningspulse.vercel.app",
        ],
    )
    assert settings.cors_origins.count("https://earningspulse.vercel.app") == 1
