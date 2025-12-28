from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from app.database.database import engine, Base
from app.api.routes import api as api_blueprint

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create the SocketIO instance
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    # Correctly configure Flask to find static files in the 'app/static' directory.
    app = Flask(__name__, static_folder='app/static', static_url_path='/static')

    # Register the API blueprint with a URL prefix
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # Import socket handlers to register them
    from app.api import sockets

    # Serve the main index.html file from the static folder
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    # Initialize the app with the SocketIO instance
    socketio.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    # The user's log shows they are trying to run on port 8000, so I will update it.
    socketio.run(app, debug=True, port=8000, allow_unsafe_werkzeug=True)
