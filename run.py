from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from app.database.database import engine, Base
from app.api.routes import api as api_blueprint

# Create all database tables
Base.metadata.create_all(bind=engine)

# Create the SocketIO instance with explicit settings for diagnostics
socketio = SocketIO(cors_allowed_origins="*",
                    async_mode='threading',
                    logger=True,
                    engineio_logger=True)

def create_app():
    # Correctly configure Flask to find static files in the 'app/static' directory.
    app = Flask(__name__, static_folder='app/static', static_url_path='/static')
    app.register_blueprint(api_blueprint, url_prefix='/api')
    from app.api import sockets

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    socketio.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    # Use host='0.0.0.0' to be accessible from the network if needed
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)
