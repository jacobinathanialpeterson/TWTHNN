// api/[...path].js

export default async function handler(req, res) {
  const target = "https://twthnn.pythonanywhere.com";
  const path = req.params.path ? req.params.path.join("/") : "";
  const url = `${target}/${path}`;

  // Prepare request options
  const init = {
    method: req.method,
    headers: req.headers,
    body: req.method !== "GET" && req.method !== "HEAD" ? await req.text() : undefined,
  };

  // Use Stormkit's built-in fetch
  const response = await fetch(url, init);

  // Copy headers except forbidden ones
  response.headers.forEach((value, key) => {
    if (!["content-encoding", "content-length", "transfer-encoding"].includes(key.toLowerCase())) {
      res.setHeader(key, value);
    }
  });

  const text = await response.text();
  res.status(response.status);
  res.send(text);
}
