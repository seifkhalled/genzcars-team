'use client'

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { CarAnalysis } from '@/types/compare'

interface ScoreRadarProps {
  cars: CarAnalysis[]
}

const COLORS = ['#3b5bdb', '#f97316', '#16a34a']

const METRICS = [
  { key: 'valueForMoney', label: 'Value for Money' },
  { key: 'reliability', label: 'Reliability' },
  { key: 'runningCost', label: 'Running Cost' },
  { key: 'resaleValue', label: 'Resale Value' },
  { key: 'overall', label: 'Overall' },
]

export default function ScoreRadar({ cars }: ScoreRadarProps) {
  const chartData = METRICS.map((metric) => {
    const point: Record<string, string | number> = { metric: metric.label }
    cars.forEach((car, idx) => {
      point[car.carName] = car.scores[metric.key as keyof typeof car.scores]
    })
    return point
  })

  return (
    <ResponsiveContainer width="100%" height={320}>
      <RadarChart data={chartData}>
        <PolarGrid stroke="hsl(var(--border))" />
        <PolarAngleAxis
          dataKey="metric"
          tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 10]}
          tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
        />

        {cars.map((car, idx) => (
          <Radar
            key={car.carId}
            name={car.carName}
            dataKey={car.carName}
            stroke={COLORS[idx % COLORS.length]}
            fill={COLORS[idx % COLORS.length]}
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ))}

        <Legend
          wrapperStyle={{ fontSize: 13, paddingTop: 12 }}
          iconType="circle"
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
