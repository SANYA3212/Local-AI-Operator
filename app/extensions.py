# app/extensions.py
from flask_socketio import SocketIO

# Create the SocketIO instance here, to be imported by the rest of the application.
# This avoids circular imports.
socketio = SocketIO(cors_allowed_origins="*",
                    async_mode='threading',
                    logger=True,
                    engineio_logger=True)
