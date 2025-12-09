"""WSGI entry point for production deployment."""

from src.flask_munkireport.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
