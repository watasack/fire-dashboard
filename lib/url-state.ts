import { SimulationConfig } from "@/lib/simulator"

export function encodeConfig(config: SimulationConfig): string {
  return btoa(JSON.stringify(config))
}

export function decodeConfig(encoded: string): SimulationConfig | null {
  try {
    return JSON.parse(atob(encoded)) as SimulationConfig
  } catch {
    return null
  }
}
