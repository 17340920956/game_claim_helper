import os

REPLACEMENTS = {
    "from config.settings": "from app.core.config",
    "import config.settings": "import app.core.config",
    "from core.logger": "from app.core.logger",
    "import core.logger": "import app.core.logger",
    "from core.security": "from app.core.security",
    "import core.security": "import app.core.security",
    "from core.scheduler": "from app.core.scheduler",
    "import core.scheduler": "import app.core.scheduler",
    "from db.connection": "from app.db.session",
    "import db.connection": "import app.db.session",
    "from db.redis": "from app.db.redis",
    "import db.redis": "import app.db.redis",
    "from db.models": "from app.models.base",
    "import db.models": "import app.models.base",
    "from db.schemas": "from app.schemas.base",
    "import db.schemas": "import app.schemas.base",
    "from repository.": "from app.repositories.",
    "import repository.": "import app.repositories.",
    "from service.": "from app.services.",
    "import service.": "import app.services.",
    "from client.": "from app.clients.",
    "import client.": "import app.clients.",
    "from common.": "from app.utils.",
    "import common.": "import app.utils.",
    "from security.": "from app.security.",
    "import security.": "import app.security.",
    "from controller.": "from app.api.endpoints.",
    "import controller.": "import app.api.endpoints.",
}

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in REPLACEMENTS.items():
        new_content = new_content.replace(old, new)
    
    if new_content != content:
        print(f"Updating {filepath}")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

def main():
    base_dir = os.path.join(os.getcwd(), "app")
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                replace_in_file(os.path.join(root, file))

if __name__ == "__main__":
    main()
