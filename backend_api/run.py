import os
from app import app

if __name__ == "__main__":
    """
    PUBLIC_INTERFACE
    Development entrypoint for running the Flask app.

    Reads HOST and PORT from environment variables, defaults to 0.0.0.0:3001.
    """
    host = os.getenv("HOST", "0.0.0.0")
    port_str = os.getenv("PORT", "3001")
    try:
        port = int(port_str)
    except ValueError:
        port = 3001

    app.run(host=host, port=port)
