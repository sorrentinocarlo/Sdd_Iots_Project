import logging
from flask import jsonify, request

def configure_error_handlers(app):

    @app.errorhandler(400)
    def bad_request(e):
        logging.error(f'Bad Request: {request.url} - {e}')
        return jsonify(error="Bad request."), 400

    @app.errorhandler(401)
    def unauthorized(e):
        logging.warning(f'Unauthorized: {request.url} - {e}')
        return jsonify(error="Unauthorized access."), 401

    @app.errorhandler(403)
    def forbidden(e):
        logging.warning(f'Forbidden: {request.url} - {e}')
        return jsonify(error="You don't have permission to access this resource."), 403

    @app.errorhandler(404)
    def resource_not_found(e):
        logging.error(f'404 Not Found: {request.url} - {e}')
        return jsonify(error=str(e)), 404

    @app.errorhandler(408)
    def request_timeout(e):
        logging.warning(f'Request Timeout: {request.url} - {e}')
        return jsonify(error="Request timeout."), 408

    @app.errorhandler(500)
    def internal_server_error(e):
        logging.error(f'500 Internal Server Error: {e}')
        return jsonify(error="An internal server error occurred."), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        logging.error(f'Unhandled Exception: {e}')
        return jsonify(error="An unexpected error occurred."), 500
