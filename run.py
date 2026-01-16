import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, send_from_directory
from app.database.database import engine, Base
from app.api.routes import api as api_blueprint
from app.extensions import socketio # Import from the new central location

# Create all database tables
Base.metadata.create_all(bind=engine)

def create_app():
    app = Flask(__name__, static_folder='app/static', static_url_path='/static')
    app.register_blueprint(api_blueprint, url_prefix='/api')

    # Import handlers to ensure they are registered with the socketio instance
    from app.api import sockets

    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')

    # Initialize the app with the centralized socketio instance
    socketio.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, host='0.0.0.0', port=8000, debug=True, allow_unsafe_werkzeug=True)
