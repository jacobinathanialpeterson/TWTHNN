import requests
from flask import Flask, request, Response

app = Flask(__name__)
application = app
BASE = "https://twthnn.pythonanywhere.com"


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def proxy(path):
    target_url = f"{BASE}/{path}"

    headers = {k: v for k, v in request.headers if k.lower() not in ["host", "content-length"]}

    r = requests.request(
        method=request.method,
        url=target_url,
        headers=headers,
        data=request.get_data(),
        params=request.args,
        allow_redirects=False
    )

    response = Response(
        r.content,
        status=r.status_code
    )

    # Copy headers, but remove Content-Encoding to avoid double decoding
    for k, v in r.headers.items():
        if k.lower() not in ["content-length", "transfer-encoding", "connection", "content-encoding"]:
            response.headers[k] = v

    return response


if __name__ == '__main__':
    app.run(debug=True)
