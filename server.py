import threading
from flask import Flask
from lib.routes import create_routes
from lib.cli import start_cli
from lib.config import HOST, PORT
import logging, sys

logging.getLogger('werkzeug').disabled = True

app = Flask(__name__)
app.logger.disabled = True

create_routes(app)

if __name__ == "__main__":
    threading.Thread(target=start_cli, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
