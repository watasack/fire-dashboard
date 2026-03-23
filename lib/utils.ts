import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, compact = false): string {
    if (compact) {
        const abs = Math.abs(value)
        const sign = value < 0 ? "-" : ""
        if (abs >= 100000000) {
            return `${sign}${(abs / 100000000).toFixed(1)}億円`
        }
        if (abs >= 10000) {
            return `${sign}${Math.round(abs / 10000)}万円`
        }
    }
    return new Intl.NumberFormat("ja-JP", {
        style: "currency",
        currency: "JPY",
        maximumFractionDigits: 0,
    }).format(value)
}

export function formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`
}

export function formatAge(age: number): string {
    return `${Math.floor(age)}歳`
}
