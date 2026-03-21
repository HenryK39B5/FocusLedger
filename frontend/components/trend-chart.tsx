import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function TrendChart({ data }: { data: Array<{ date: string; score: number }> }) {
  return (
    <div className="h-72 rounded-[28px] border border-white/10 bg-white/5 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{
              background: "rgba(10, 16, 30, 0.95)",
              border: "1px solid rgba(255,255,255,0.14)",
              borderRadius: 16,
              color: "#fff",
            }}
          />
          <Line type="monotone" dataKey="score" stroke="#f7c66b" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

