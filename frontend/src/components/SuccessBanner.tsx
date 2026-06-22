"use client";

import { useEffect } from "react";

export default function SuccessBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss?: () => void;
}) {
  useEffect(() => {
    if (!message || !onDismiss) return;
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div className="rounded-xl bg-green-50 border border-green-200 text-green-800 px-4 py-3 text-sm font-semibold">
      {message}
    </div>
  );
}
