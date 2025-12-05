from flask_smorest import Blueprint
from flask.views import MethodView

blp = Blueprint("Health", "health", url_prefix="/", description="Health check route")


@blp.route("", methods=["GET"])
class HealthCheck(MethodView):
    """
    PUBLIC_INTERFACE
    Simple health-check endpoint to verify the API is running.

    Returns a JSON payload indicating service health.
    """

    def get(self):
        """Return static healthy response."""
        return {"message": "Healthy"}
