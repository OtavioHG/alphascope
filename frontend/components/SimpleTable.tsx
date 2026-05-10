type SimpleTableProps = {
  rows: Array<Record<string, unknown>>;
  titleKeyOrder?: string[];
};

export function SimpleTable({ rows, titleKeyOrder }: SimpleTableProps) {
  if (!rows.length) {
    return <p style={{ color: "#94a3b8" }}>Nenhum dado disponível.</p>;
  }

  const columns = titleKeyOrder?.filter((key) => key in rows[0]) ?? Object.keys(rows[0]).slice(0, 6);

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} style={{ textAlign: "left", padding: "10px 12px", color: "#94a3b8", fontSize: ".85rem" }}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column} style={{ padding: "10px 12px", borderTop: "1px solid rgba(148,163,184,0.12)" }}>
                  {String(row[column] ?? "-")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
