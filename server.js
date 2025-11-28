import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";

const app = express();
const PORT = process.env.PORT || 3000;

// Proxy all requests to PythonAnywhere
app.use(
  "/",
  createProxyMiddleware({
    target: "https://twthnn.pythonanywhere.com",
    changeOrigin: true,
    secure: true, // verify SSL
    logLevel: "debug",
    onProxyReq: (proxyReq, req, res) => {
      // Optional: modify headers if needed
    },
    onProxyRes: (proxyRes, req, res) => {
      // Optional: modify response headers
    }
  })
);

app.listen(PORT, () => {
  console.log(`Proxy server running on port ${PORT}`);
});
