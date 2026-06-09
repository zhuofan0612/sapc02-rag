import express, { Request, Response, NextFunction } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import morgan from "morgan";
import rateLimit from "express-rate-limit";
import cors from "cors";

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// --- Middleware ---

// CORS
app.use(cors());

// Request logging
app.use(morgan("[:date[iso]] :method :url :status :response-time ms"));

// Parse JSON bodies
app.use(express.json());

// Rate limiting — 60 requests per minute per IP
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 60,
  message: { error: "Too many requests, please try again later." },
});
app.use("/ask", limiter);

// --- Health check (gateway itself) ---
app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "gateway" });
});

// --- Backend health check (proxied) ---
app.get("/backend/health", createProxyMiddleware({
  target: BACKEND_URL,
  changeOrigin: true,
  pathRewrite: { "^/backend/health": "/health" },
}));

// --- Proxy /ask and /ask/stream to FastAPI ---
app.use(
  ["/ask", "/ask/stream"],
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    // Streaming support
    on: {
      error: (err: Error, _req: Request, res: Response) => {
        console.error("Proxy error:", err.message);
        res.status(502).json({ error: "Backend unavailable" });
      },
    },
  })
);

// --- 404 handler ---
app.use((_req: Request, res: Response) => {
  res.status(404).json({ error: "Route not found" });
});

// --- Global error handler ---
app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error("Unhandled error:", err.message);
  res.status(500).json({ error: "Internal server error" });
});

app.listen(PORT, () => {
  console.log(`Gateway running on port ${PORT}`);
  console.log(`Proxying to backend: ${BACKEND_URL}`);
});
