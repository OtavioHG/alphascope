type KeyValueListProps = {
  data: Record<string, unknown>;
};

export function KeyValueList({ data }: KeyValueListProps) {
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            padding: "10px 12px",
            borderRadius: 14,
            background: "rgba(30,41,59,0.6)",
          }}
        >
          <strong style={{ color: "#cbd5e1" }}>{key}</strong>
          <span style={{ color: "#94a3b8", textAlign: "right" }}>{String(value ?? "-")}</span>
        </div>
      ))}
    </div>
  );
}
