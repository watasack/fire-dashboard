"use client"

import * as React from "react"
import { Drawer } from "vaul"
import { cn } from "@/lib/utils"

const BottomSheet = Drawer.Root
const BottomSheetTrigger = Drawer.Trigger
const BottomSheetPortal = Drawer.Portal
const BottomSheetClose = Drawer.Close

function BottomSheetOverlay({ className, ...props }: React.ComponentProps<typeof Drawer.Overlay>) {
  return (
    <Drawer.Overlay
      className={cn("fixed inset-0 z-[60] bg-black/40", className)}
      {...props}
    />
  )
}

function BottomSheetContent({
  className,
  title,
  children,
  ...props
}: React.ComponentProps<typeof Drawer.Content> & { title?: string }) {
  return (
    <BottomSheetPortal>
      <BottomSheetOverlay />
      <Drawer.Content
        className={cn(
          "fixed inset-x-0 bottom-14 z-[60] flex flex-col rounded-t-2xl bg-background",
          className
        )}
        {...props}
      >
        {/* ドラッグハンドル */}
        <div className="mx-auto mt-3 h-1.5 w-12 rounded-full bg-muted-foreground/20" />
        {title && <Drawer.Title className="sr-only">{title}</Drawer.Title>}
        {children}
      </Drawer.Content>
    </BottomSheetPortal>
  )
}

export { BottomSheet, BottomSheetTrigger, BottomSheetContent, BottomSheetClose }