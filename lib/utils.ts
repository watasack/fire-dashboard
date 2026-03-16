import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, compact = false): string {
    if (compact) {
        if (value >= 100000000) {
            return `${(value / 100000000).toFixed(1)}億円`
        }
        if (value >= 10000) {
            return `${Math.round(value / 10000)}万円`
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
