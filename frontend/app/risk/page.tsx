import { DataPanel } from "../../components/DataPanel";
import { KeyValueList } from "../../components/KeyValueList";
import { NavigationBar } from "../../components/NavigationBar";
import { PageShell } from "../../components/PageShell";
import { SimpleTable } from "../../components/SimpleTable";
import { fetchRiskPayload } from "../../lib/alphascope-api";

export default async function RiskPage() {
  const payload = await fetchRiskPayload();
  const dailyPerformance = (payload?.daily_performance as Record<string, unknown> | undefined) ?? {};
  const config = (payload?.config as Record<string, unknown> | undefined) ?? {};
  const events = (payload?.risk_events as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <PageShell title="Risk" subtitle="Configuração, performance diária e eventos de risco da plataforma.">
      <NavigationBar />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20 }}>
        <DataPanel title="Performance diária">
          <KeyValueList data={dailyPerformance} />
        </DataPanel>
        <DataPanel title="Configuração de risco">
          <KeyValueList data={config} />
        </DataPanel>
      </div>
      <DataPanel title="Eventos de risco">
        <SimpleTable rows={events.slice(0, 30)} titleKeyOrder={["created_at", "event_type", "severity", "symbol", "message"]} />
      </DataPanel>
    </PageShell>
  );
}
