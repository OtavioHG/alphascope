import { DataPanel } from "../components/DataPanel";
import { KeyValueList } from "../components/KeyValueList";
import { MetricCardGrid } from "../components/MetricCardGrid";
import { NavigationBar } from "../components/NavigationBar";
import { PageShell } from "../components/PageShell";
import { SimpleTable } from "../components/SimpleTable";
import { fetchDashboardPayload, fetchPlatformHealth, API_BASE_URL } from "../lib/alphascope-api";
import { dashboardStats, rankingRows } from "../lib/dashboard-data";

export default async function Home() {
  const health = await fetchPlatformHealth();
  const dashboard = await fetchDashboardPayload();
  const account = (dashboard?.account as Record<string, unknown> | undefined) ?? {};
  const performance = (dashboard?.daily_performance as Record<string, unknown> | undefined) ?? {};
  const positions = (dashboard?.positions as Array<Record<string, unknown>> | undefined) ?? [];
  const ranking = (dashboard?.ranking as Array<Record<string, unknown>> | undefined) ?? rankingRows;

  return (
    <PageShell
      title="Quantitative Crypto Terminal"
      subtitle="Painel React para monitoramento, ranking, risco, auditoria e leitura rápida do estado operacional do AlphaScope via API."
    >
      <NavigationBar />
      <MetricCardGrid items={dashboardStats} />

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(320px, 420px)", gap: 20 }}>
        <DataPanel title="Top Ranking">
          <SimpleTable rows={ranking.slice(0, 8)} titleKeyOrder={["symbol", "score", "rank", "market_regime"]} />
        </DataPanel>
        <DataPanel title="Status da plataforma">
          <KeyValueList
            data={{
              api_base: API_BASE_URL,
              service: health?.service ?? "-",
              health_status: health?.health?.status ?? health?.status ?? "unavailable",
              best_coin: String(dashboard?.best_coin ?? "-"),
              positions_count: positions.length,
            }}
          />
        </DataPanel>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
        <DataPanel title="Conta">
          <KeyValueList data={account} />
        </DataPanel>
        <DataPanel title="Performance diária">
          <KeyValueList data={performance} />
        </DataPanel>
      </div>

      <DataPanel title="Posições abertas">
        <SimpleTable rows={positions} titleKeyOrder={["symbol", "quantity", "entry_price", "current_price", "unrealized_pnl"]} />
      </DataPanel>
    </PageShell>
  );
}
