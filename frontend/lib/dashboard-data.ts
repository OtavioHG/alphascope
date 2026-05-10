export type DashboardStat = {
  label: string;
  value: string;
};

export type RankingRow = {
  symbol: string;
  score: string;
  regime: string;
};

export const dashboardStats: DashboardStat[] = [
  { label: "Portfolio Value", value: "$125.45" },
  { label: "Available Cash", value: "$62.10" },
  { label: "Open Positions", value: "2" },
  { label: "Daily PnL", value: "+3.48%" },
  { label: "Win Rate", value: "68.2%" },
  { label: "Market Regime", value: "Bull Market" },
];

export const rankingRows: RankingRow[] = [
  { symbol: "SOLUSDT", score: "0.91", regime: "bull" },
  { symbol: "ETHUSDT", score: "0.87", regime: "bull" },
  { symbol: "XRPUSDT", score: "0.82", regime: "bull" },
  { symbol: "DOGEUSDT", score: "0.74", regime: "sideways" },
];
