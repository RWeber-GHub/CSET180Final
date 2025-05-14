@app.after_request
def after_request(response):
    if request.path.startswith('/products/') and 'application/json' not in response.content_type:
        if response.status_code >= 400:
            return jsonify({
                'success': False,
                'message': response.status
            }), response.status_code
    return response