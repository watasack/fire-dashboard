import { SimulationConfig, DEFAULT_CONFIG } from "@/lib/simulator"

export function encodeConfig(config: SimulationConfig): string {
  return btoa(JSON.stringify(config))
}

export function decodeConfig(encoded: string): SimulationConfig | null {
  try {
    const decoded = JSON.parse(atob(encoded)) as Partial<SimulationConfig>
    return {
      ...DEFAULT_CONFIG,
      ...decoded,
      person1: { ...DEFAULT_CONFIG.person1, ...(decoded.person1 ?? {}) },
      person2: decoded.person2 != null
        ? { ...DEFAULT_CONFIG.person2!, ...decoded.person2 }
        : Object.prototype.hasOwnProperty.call(decoded, 'person2') ? null : DEFAULT_CONFIG.person2,
    } as SimulationConfig
  } catch {
    return null
  }
}
