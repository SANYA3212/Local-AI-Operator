from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from app.database.database import engine, Base
from app.api.routes import api as api_blueprint

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create the SocketIO instance
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    # Correctly configure Flask to serve static files from app/static
    # The static_folder path is relative to the instance_path, so an absolute path is safer.
    # However, for this project structure, a simple relative path works.
    app = Flask(__name__, static_folder='static')

    # Register the API blueprint with a URL prefix
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # Import socket handlers to register them
    from app.api import sockets

    # Serve the main index.html
    @app.route('/')
    def index():
        return app.send_static_file('index.html')

    # Initialize the app with the SocketIO instance
    socketio.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
