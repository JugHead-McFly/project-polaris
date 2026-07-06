from app.database.database import Base
from app.database.database import engine

# Import all models before creating tables
from app.models import Capture

Base.metadata.create_all(bind=engine)

print("✅ Project Polaris database initialized.")