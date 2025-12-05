from flask import Flask, render_template
from flask_cors import CORS
from flask_smorest import Api

from app.error_handlers import register_error_handlers
from app.routes.health import blp as health_blp
from app.routes.run import blp as run_blp
from app.routes.progress import blp as progress_blp
from app.routes.stats import blp as stats_blp
from app.routes.logs import blp as logs_blp
from app.routes.case_status import blp as case_status_blp
from app.routes.current_case_info import blp as current_case_info_blp
from app.routes.ui_lock import blp as ui_lock_blp


app = Flask(__name__, static_folder="static", template_folder="templates")
app.url_map.strict_slashes = False

# Enable CORS for all origins (adjust if needed)
CORS(app, resources={r"/*": {"origins": "*"}})

# OpenAPI / Swagger configuration
app.config["API_TITLE"] = "Execution Session Management API"
app.config["API_VERSION"] = "v1"
app.config["OPENAPI_VERSION"] = "3.0.3"
app.config["OPENAPI_URL_PREFIX"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_PATH"] = ""
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

# Initialize smorest Api
api = Api(app)

# Register error handlers
register_error_handlers(app)

# Register blueprints
api.register_blueprint(health_blp)
api.register_blueprint(run_blp)
api.register_blueprint(progress_blp)
api.register_blueprint(stats_blp)
api.register_blueprint(logs_blp)
api.register_blueprint(case_status_blp)
api.register_blueprint(current_case_info_blp)
api.register_blueprint(ui_lock_blp)

# PUBLIC_INTERFACE
@app.get("/")
def index():
    """Render the minimal frontend UI for selecting tests and monitoring execution."""
    return render_template("index.html")
