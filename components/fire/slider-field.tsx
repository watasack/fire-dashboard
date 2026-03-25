"use client"

import { useState } from "react"
import { Info, ChevronRight } from "lucide-react"
import { Slider } from "@/components/ui/slider"
import { BottomSheet, BottomSheetTrigger, BottomSheetContent } from "@/components/ui/bottom-sheet"
import { cn } from "@/lib/utils"

interface SliderFieldProps {
  label: string
  tooltip: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  format: (value: number) => string
  /** ラベルを小さくしたい場合（入れ子のスライダー等） */
  small?: boolean
  className?: string
}

function InlineSliderField({
  label, tooltip, value, onChange, min, max, step, format, small, className,
}: SliderFieldProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false)

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <span className="flex flex-col gap-0">
          <span className="flex items-center gap-1">
            <span className={cn("font-medium", small ? "text-xs" : "text-sm")}>{label}</span>
            {tooltip && (
              <button
                type="button"
                aria-expanded={tooltipOpen}
                onClick={() => setTooltipOpen((p) => !p)}
                className="inline-flex p-2.5 -m-2.5 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
              >
                <Info className="h-4 w-4 shrink-0" />
              </button>
            )}
          </span>
          {tooltipOpen && tooltip && (
            <span className="mt-1 text-xs text-muted-foreground leading-relaxed">{tooltip}</span>
          )}
        </span>
        <span className={cn("font-mono text-muted-foreground", small ? "text-xs" : "text-sm")}>
          {format(value)}
        </span>
      </div>
      <Slider
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
      />
    </div>
  )
}

function BottomSheetSliderField({
  label, tooltip, value, onChange, min, max, step, format, small, className,
}: SliderFieldProps) {
  const [tooltipOpen, setTooltipOpen] = useState(false)

  return (
    <BottomSheet>
      {/* トリガー行: タップで開く */}
      <BottomSheetTrigger asChild>
        <button
          type="button"
          className={cn(
            "w-full flex items-center justify-between py-3 text-left",
            "active:bg-muted/50 transition-colors rounded-md -mx-1 px-1",
            className
          )}
        >
          <span className={cn("font-medium", small ? "text-xs" : "text-sm")}>{label}</span>
          <span className="flex items-center gap-1 text-muted-foreground">
            <span className={cn("font-mono", small ? "text-xs" : "text-sm")}>{format(value)}</span>
            <ChevronRight className="h-4 w-4 shrink-0 opacity-40" />
          </span>
        </button>
      </BottomSheetTrigger>

      {/* ボトムシート本体 */}
      <BottomSheetContent title={label}>
        <div className="px-6 pb-8 pt-4 space-y-6">
          {/* ラベル + ツールチップ */}
          <div className="space-y-1">
            <div className="flex items-center gap-1">
              <span className="text-base font-semibold">{label}</span>
              {tooltip && (
                <button
                  type="button"
                  aria-expanded={tooltipOpen}
                  onClick={() => setTooltipOpen((p) => !p)}
                  className="inline-flex p-2 -m-2 text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                >
                  <Info className="h-4 w-4 shrink-0" />
                </button>
              )}
            </div>
            {tooltipOpen && tooltip && (
              <p className="text-sm text-muted-foreground leading-relaxed">{tooltip}</p>
            )}
          </div>

          {/* 現在値（大きく表示） */}
          <p className="text-3xl font-bold text-center tabular-nums">{format(value)}</p>

          {/* スライダー */}
          <div className="space-y-2">
            <Slider
              value={[value]}
              onValueChange={([v]) => onChange(v)}
              min={min}
              max={max}
              step={step}
              className="py-2"
            />
            {/* 最小・最大ラベル */}
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{format(min)}</span>
              <span>{format(max)}</span>
            </div>
          </div>
        </div>
      </BottomSheetContent>
    </BottomSheet>
  )
}

/**
 * PC (lg+): インラインスライダー
 * モバイル (<lg): タップ行 + ボトムシートスライダー
 */
export function SliderField(props: SliderFieldProps) {
  return (
    <>
      {/* PC 表示 */}
      <div className="not-lg:hidden">
        <InlineSliderField {...props} />
      </div>
      {/* モバイル表示 */}
      <div className="lg:hidden">
        <BottomSheetSliderField {...props} />
      </div>
    </>
  )
}