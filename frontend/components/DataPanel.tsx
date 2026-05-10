import { ReactNode } from "react";

type DataPanelProps = {
  title: string;
  children: ReactNode;
};

export function DataPanel({ title, children }: DataPanelProps) {
  return (
    <section
      style={{
        padding: 22,
        borderRadius: 24,
        background: "rgba(17,24,39,0.78)",
        border: "1px solid rgba(148,163,184,0.16)",
      }}
    >
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {children}
    </section>
  );
}
