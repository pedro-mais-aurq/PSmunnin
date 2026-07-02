
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from leadhunter_api.config.settings import settings
from leadhunter_api.infrastructure.database.models.base import Base

engine = create_async_engine(settings.database_url, echo=settings.environment == "development")
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session() as session:
        yield session
