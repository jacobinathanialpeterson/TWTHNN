// api/[...path].js

export default async function handler(req, res) {
  const target = "https://twthnn.pythonanywhere.com";
  const path = req.params.path ? req.params.path.join("/") : "";
  const url = `${target}/${path}`;

  const init = {
    method: req.method,
    headers: req.headers,
    body: req.method !== "GET" && req.method !== "HEAD" ? await req.text() : undefined,
  };

  // Use Stormkit's fetch
  const response = await fetch(url, init);

  // Copy headers (exclude some that break proxy)
  response.headers.forEach((value, key) => {
    if (!["content-encoding", "content-length", "transfer-encoding"].includes(key.toLowerCase())) {
      res.setHeader(key, value);
    }
  });

  // Return raw data as Buffer instead of text
  const buffer = Buffer.from(await response.arrayBuffer());
  res.status(response.status);
  res.send(buffer);
}
