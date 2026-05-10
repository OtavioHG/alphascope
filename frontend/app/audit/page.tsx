import { DataPanel } from "../../components/DataPanel";
import { NavigationBar } from "../../components/NavigationBar";
import { PageShell } from "../../components/PageShell";
import { SimpleTable } from "../../components/SimpleTable";
import { fetchAuditPayload } from "../../lib/alphascope-api";

export default async function AuditPage() {
  const payload = await fetchAuditPayload();
  const events = (payload?.events as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <PageShell title="Audit" subtitle="Eventos de auditoria recentes para investigação operacional e rastreabilidade.">
      <NavigationBar />
      <DataPanel title="Eventos recentes">
        <SimpleTable rows={events.slice(0, 50)} titleKeyOrder={["created_at", "action", "target", "status", "details"]} />
      </DataPanel>
    </PageShell>
  );
}
