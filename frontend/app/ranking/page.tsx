import { DataPanel } from "../../components/DataPanel";
import { NavigationBar } from "../../components/NavigationBar";
import { PageShell } from "../../components/PageShell";
import { SimpleTable } from "../../components/SimpleTable";
import { fetchRankingPayload } from "../../lib/alphascope-api";

export default async function RankingPage() {
  const payload = await fetchRankingPayload();
  const latest = (payload?.latest as Array<Record<string, unknown>> | undefined) ?? [];
  const history = (payload?.history as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <PageShell title="Ranking" subtitle="Leitura operacional do ranking atual e do histórico recente de ciclos.">
      <NavigationBar />
      <DataPanel title="Ranking atual">
        <SimpleTable rows={latest.slice(0, 20)} titleKeyOrder={["symbol", "score", "rank", "market_regime", "ml_probability"]} />
      </DataPanel>
      <DataPanel title="Histórico de ranking">
        <SimpleTable rows={history.slice(0, 20)} titleKeyOrder={["timestamp", "symbol", "score", "rank"]} />
      </DataPanel>
    </PageShell>
  );
}
