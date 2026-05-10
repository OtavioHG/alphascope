import { ReactNode } from "react";

type PageShellProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function PageShell({ title, subtitle, children }: PageShellProps) {
  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "40px 24px 80px",
        color: "#f8fafc",
        background:
          "radial-gradient(circle at top left, rgba(34,197,94,0.18), transparent 30%), radial-gradient(circle at top right, rgba(56,189,248,0.16), transparent 28%), linear-gradient(180deg, #07111f 0%, #0f172a 45%, #111827 100%)",
        fontFamily: "Georgia, 'Times New Roman', serif",
      }}
    >
      <section style={{ maxWidth: 1200, margin: "0 auto", display: "grid", gap: 24 }}>
        <div
          style={{
            padding: 28,
            borderRadius: 28,
            border: "1px solid rgba(148,163,184,0.22)",
            background: "rgba(15,23,42,0.72)",
            backdropFilter: "blur(18px)",
            boxShadow: "0 40px 100px rgba(8,15,30,0.45)",
          }}
        >
          <p style={{ letterSpacing: "0.25em", textTransform: "uppercase", color: "#86efac", margin: 0 }}>
            AlphaScope Control Center
          </p>
          <h1 style={{ fontSize: "clamp(2.1rem, 5vw, 4rem)", lineHeight: 1, margin: "12px 0 16px" }}>{title}</h1>
          <p style={{ maxWidth: 780, fontSize: "1.05rem", color: "#cbd5e1", margin: 0 }}>{subtitle}</p>
        </div>
        {children}
      </section>
    </main>
  );
}
