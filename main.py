import os

import uvicorn
from literature_helper import app

if __name__ == "__main__":
    DEFAULT_PORT = 8080
    port = os.getenv("PORT", DEFAULT_PORT)
    uvicorn.run(app, host="0.0.0.0", port=port)
