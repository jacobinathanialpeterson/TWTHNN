from flask import Flask, request, Response
import requests

app = Flask(__name__)

# Base URL of the target server
TARGET_URL = "https://twthnn.pythonanywhere.com"

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    # Build the full URL to the target
    url = f"{TARGET_URL}/{path}"

    # Forward the request to the target
    resp = requests.request(
        method=request.method,
        url=url,
        headers={key: value for key, value in request.headers if key.lower() != 'host'},
        params=request.args,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False
    )

    # Build a response to return to the client
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    headers = [(name, value) for name, value in resp.raw.headers.items()
               if name.lower() not in excluded_headers]

    response = Response(resp.content, resp.status_code, headers)
    return response

if __name__ == "__main__":
    app.run(debug=True, port=5000)
