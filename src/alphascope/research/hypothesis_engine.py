from __future__ import annotations

import pandas as pd


class HypothesisEngine:
    def generate(
        self,
        regimes: pd.DataFrame,
        anomalies: pd.DataFrame,
        ranked_alpha: pd.DataFrame,
        sector_rotation: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        hypotheses: list[dict[str, object]] = []
        if not regimes.empty:
            dominant_regime = str(regimes["regime_label"].mode().iloc[0])
            hypotheses.append(
                {
                    "hypothesis_id": "hyp_001",
                    "summary": f"O mercado atual favorece estrategias no regime {dominant_regime}.",
                    "evidence_score": float(regimes["regime_confidence"].mean()),
                }
            )
        if not anomalies.empty:
            top_anomaly = str(anomalies["anomaly_type"].mode().iloc[0])
            hypotheses.append(
                {
                    "hypothesis_id": "hyp_002",
                    "summary": f"Eventos do tipo {top_anomaly} estao antecedendo movimentos fora do padrao.",
                    "evidence_score": float(anomalies["anomaly_score"].mean()),
                }
            )
        if not ranked_alpha.empty:
            top = ranked_alpha.iloc[0]
            hypotheses.append(
                {
                    "hypothesis_id": "hyp_003",
                    "summary": f"A estrategia {top['strategy_id']} mostra melhor robustez na amostra atual.",
                    "evidence_score": float(top["alpha_discovery_score"]),
                }
            )
        if sector_rotation is not None and not sector_rotation.empty:
            sector = str(sector_rotation.iloc[0]["sector"])
            hypotheses.append(
                {
                    "hypothesis_id": "hyp_004",
                    "summary": f"O setor {sector} lidera a rotacao recente e merece monitoramento prioritario.",
                    "evidence_score": float(sector_rotation.iloc[0]["rotation_score"]),
                }
            )
        return pd.DataFrame(hypotheses)
