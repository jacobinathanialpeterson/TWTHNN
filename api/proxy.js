// api/proxy.js
import fetch from "node-fetch";

export default async function handler(req, res) {
  const target = "https://twthnn.pythonanywhere.com";

  // Construct the target URL
  const url = `${target}${req.url}`;

  // Forward the request
  const response = await fetch(url, {
    method: req.method,
    headers: req.headers,
    body: req.method !== "GET" && req.method !== "HEAD" ? await req.text() : undefined,
  });

  // Copy headers
  response.headers.forEach((value, key) => {
    if (key.toLowerCase() !== "content-encoding" && key.toLowerCase() !== "content-length") {
      res.setHeader(key, value);
    }
  });

  // Return response
  const text = await response.text();
  res.status(response.status);
  res.send(text);
}
