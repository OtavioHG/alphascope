type MetricCard = {
  label: string;
  value: string;
};

type MetricCardGridProps = {
  items: MetricCard[];
};

export function MetricCardGrid({ items }: MetricCardGridProps) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 16,
      }}
    >
      {items.map((item) => (
        <article
          key={item.label}
          style={{
            padding: 18,
            borderRadius: 22,
            background: "rgba(15,23,42,0.68)",
            border: "1px solid rgba(56,189,248,0.22)",
          }}
        >
          <div style={{ color: "#94a3b8", fontSize: ".85rem", textTransform: "uppercase", letterSpacing: ".12em" }}>
            {item.label}
          </div>
          <div style={{ marginTop: 10, fontSize: "1.6rem", fontWeight: 700 }}>{item.value}</div>
        </article>
      ))}
    </div>
  );
}
