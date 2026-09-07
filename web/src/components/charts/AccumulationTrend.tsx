import {
  CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CHART_AXIS, CHART_AXIS_LINE, CHART_GRID, STATUS } from "@/lib/theme";
import type { AccumulationCell } from "@/types/api";

const AXIS = CHART_AXIS;

/**
 * Two points per site: the previous window and the current one.
 *
 * A sparkline of two values is not a rich time series — it is exactly what the
 * API returns, and inventing intermediate points would be fabricating data.
 * The slope is the message.
 */
export function AccumulationTrend({ cells }: { cells: AccumulationCell[] }) {
  const top = cells.slice(0, 6);
  if (!top.length) return null;

  const data = [
    { window: "Previous", ...Object.fromEntries(top.map((c) => [`${c.site}·${c.energy_source}`, c.previous_index])) },
    { window: "Current", ...Object.fromEntries(top.map((c) => [`${c.site}·${c.energy_source}`, c.index])) },
  ];
  const palette = ["#3987e5", "#d95926", "#199e70", "#c98500", "#9085e9", "#d55181"];

  return (
    <div>
      <ResponsiveContainer width="100%" height={190}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: -18 }}>
          <CartesianGrid stroke={CHART_GRID} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="window" {...AXIS} axisLine={{ stroke: CHART_AXIS_LINE }} />
          <YAxis {...AXIS} axisLine={false} width={42} />
          <ReferenceLine y={20} stroke={STATUS.serious} strokeDasharray="4 4" strokeOpacity={0.6}
            label={{ value: "high", fill: STATUS.serious, fontSize: 11, position: "insideTopRight" }} />
          <ReferenceLine y={40} stroke={STATUS.critical} strokeDasharray="4 4" strokeOpacity={0.6}
            label={{ value: "critical", fill: STATUS.critical, fontSize: 11, position: "insideTopRight" }} />
          <Tooltip
            contentStyle={{
              background: "#1A2330", border: "1px solid #33425A",
              borderRadius: 6, fontSize: 11, color: "#E6EDF3",
            }}
            labelStyle={{ color: "#9FB0C0" }}
            formatter={(v: number) => v.toFixed(1)}
          />
          {top.map((c, i) => (
            <Line
              key={`${c.site}·${c.energy_source}`}
              type="linear"
              dataKey={`${c.site}·${c.energy_source}`}
              stroke={palette[i % palette.length]}
              strokeWidth={2}
              dot={{ r: 4, strokeWidth: 0, fill: palette[i % palette.length] }}
              activeDot={{ r: 6, stroke: "#131A22", strokeWidth: 2 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
        {top.map((c, i) => (
          <span key={`${c.site}·${c.energy_source}`} className="inline-flex items-center gap-1.5 text-2xs text-ink-muted">
            <span className="size-2 rounded-full" style={{ backgroundColor: palette[i % palette.length] }} />
            {c.site} · {c.energy_source}
          </span>
        ))}
      </div>
    </div>
  );
}
