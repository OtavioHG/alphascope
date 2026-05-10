import os

dirs = [
    "src/alphascope/config",
    "src/alphascope/core",
    "src/alphascope/domain",
    "src/alphascope/infrastructure/db",
    "src/alphascope/infrastructure/repositories",
    "src/alphascope/ingestion",
    "src/alphascope/features",
    "src/alphascope/nlp",
    "src/alphascope/models",
    "src/alphascope/scoring",
    "src/alphascope/backtest",
    "src/alphascope/trading",
    "src/alphascope/alerts",
    "src/alphascope/utils",
    "tests/unit",
    "tests/integration",
    "sql/schema",
    "sql/views",
    "data/raw",
    "data/processed",
    "data/exports",
    "logs",
    "notebooks",
    "docs"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    # Create __init__.py in src subfolders to make them packages
    if d.startswith("src/"):
        with open(os.path.join(d, "__init__.py"), "w") as f:
            pass

print("Directory structure created successfully.")
