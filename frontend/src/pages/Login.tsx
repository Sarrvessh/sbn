import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Key, Radar, Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";

export default function Login() {
  const navigate = useNavigate();
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = key.trim();
    if (!trimmed) { setError("Enter an API key"); return; }

    setChecking(true);
    setError("");

    try {
      const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";
      const res = await fetch(`${BACKEND_URL}/api/v1/projects`, {
        headers: { "X-API-Key": trimmed, "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Invalid key" }));
        throw new Error(body.detail || "Invalid API key");
      }
      localStorage.setItem("sbn_api_key", trimmed);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const msg = err instanceof TypeError ? "Could not reach server. Check if the backend is running." : String(err);
      setError(msg);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f5f5f7 0%, #e8e8ed 100%)",
        padding: 24,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          top: "-30%",
          right: "-20%",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, rgba(0,113,227,0.08) 0%, rgba(0,113,227,0.02) 50%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "-30%",
          left: "-20%",
          width: 500,
          height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,113,227,0.06) 0%, transparent 60%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(rgba(0,0,0,0.03) 1px, transparent 1px)",
          backgroundSize: "24px 24px",
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          width: "100%",
          maxWidth: 400,
          background: "rgba(255,255,255,0.85)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderRadius: 16,
          border: "1px solid rgba(255,255,255,0.8)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)",
          padding: "48px 36px 36px",
          textAlign: "center",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div style={{ position: "relative", width: 72, height: 72, margin: "0 auto 20px" }}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: "50%",
              border: "2px solid rgba(0,113,227,0.12)",
              animation: "spin 8s linear infinite",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 4,
              borderRadius: "50%",
              border: "1.5px dashed rgba(0,113,227,0.08)",
              animation: "spin 12s linear infinite reverse",
            }}
          />
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #0071e3 0%, #0051a8 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              boxShadow: "0 4px 16px rgba(0,113,227,0.3)",
            }}
          >
            <Radar size={26} color="#ffffff" />
          </div>
        </div>

        <h1
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: "#1d1d1f",
            margin: "0 0 4px",
            letterSpacing: "-0.003em",
          }}
        >
          SBN <span style={{ fontWeight: 500, color: "#6e6e73" }}>- ARMS</span>
        </h1>
        <p
          style={{
            fontSize: 14,
            color: "#6e6e73",
            margin: "0 0 32px",
            lineHeight: 1.4,
          }}
        >
          Sign in to your observability platform
        </p>

        <form onSubmit={handleSubmit} style={{ textAlign: "left" }}>
          <label
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: "#6e6e73",
              display: "block",
              marginBottom: 6,
            }}
          >
            API Key
          </label>
          <div style={{ position: "relative", marginBottom: error ? 10 : 16 }}>
            <Key
              size={14}
              style={{
                position: "absolute",
                left: 12,
                top: "50%",
                transform: "translateY(-50%)",
                color: "#aeaeb2",
                pointerEvents: "none",
              }}
            />
            <input
              type={showKey ? "text" : "password"}
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-..."
              autoFocus
              style={{
                width: "100%",
                fontFamily: "'Inter', system-ui, sans-serif",
                fontSize: 14,
                padding: "12px 40px 12px 38px",
                border: error ? "1px solid #ff3b30" : "1px solid #d2d2d7",
                borderRadius: 10,
                background: "#ffffff",
                color: "#1d1d1f",
                outline: "none",
                transition: "border-color 0.15s ease, box-shadow 0.15s ease",
                appearance: "none",
                WebkitAppearance: "none",
                boxSizing: "border-box",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = error ? "#ff3b30" : "#0071e3";
                if (!error) e.target.style.boxShadow = "0 0 0 3px rgba(0,113,227,0.12)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = error ? "#ff3b30" : "#d2d2d7";
                e.target.style.boxShadow = "none";
              }}
            />
            <button
              type="button"
              onClick={() => setShowKey(!showKey)}
              style={{
                position: "absolute",
                right: 10,
                top: "50%",
                transform: "translateY(-50%)",
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#aeaeb2",
                padding: 4,
                display: "flex",
              }}
            >
              {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 12,
                color: "#ff3b30",
                margin: "0 0 16px",
                padding: "8px 12px",
                background: "#ffeeee",
                borderRadius: 8,
              }}
            >
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

          <button
            type="submit"
            disabled={checking || !key.trim()}
            style={{
              width: "100%",
              padding: "12px 20px",
              borderRadius: 10,
              border: "none",
              background:
                checking || !key.trim()
                  ? "#e8e8ed"
                  : "linear-gradient(135deg, #0071e3 0%, #0051a8 100%)",
              color: checking || !key.trim() ? "#aeaeb2" : "#ffffff",
              fontSize: 14,
              fontWeight: 500,
              cursor: checking || !key.trim() ? "not-allowed" : "pointer",
              transition: "opacity 0.15s ease, transform 0.1s ease",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              fontFamily: "'Inter', system-ui, sans-serif",
            }}
            onMouseEnter={(e) => {
              if (!checking && key.trim()) e.currentTarget.style.opacity = "0.9";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = "1";
            }}
          >
            {checking ? (
              <Loader2 size={16} style={{ animation: "spin 0.8s linear infinite" }} />
            ) : (
              <Key size={16} />
            )}
            {checking ? "Connecting\u2026" : "Connect to Platform"}
          </button>
        </form>

        <div
          style={{
            marginTop: 28,
            paddingTop: 20,
            borderTop: "1px solid #e8e8ed",
          }}
        >
          <p
            style={{
              fontSize: 11,
              color: "#aeaeb2",
              margin: 0,
              lineHeight: 1.5,
            }}
          >
            Your API key is stored locally and never shared.
            <br />
            Need a key? Contact your administrator.
          </p>
        </div>
      </div>
    </div>
  );
}
