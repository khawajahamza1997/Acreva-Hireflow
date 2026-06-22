"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Log = {
  id: string;
  action: string;
  user_email: string;
  entity_type: string;
  created_at: string;
  details: Record<string, unknown>;
};

export default function AuditPage() {
  const [logs, setLogs] = useState<Log[]>([]);

  useEffect(() => {
    api<Log[]>("/api/v1/audit-logs").then(setLogs);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Audit log</h1>
      <p className="text-sm text-slate-500 mt-1">Who scored, shortlisted, or emailed whom.</p>
      <div className="card mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">When</th>
              <th className="pb-2">User</th>
              <th className="pb-2">Action</th>
              <th className="pb-2">Entity</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-slate-50">
                <td className="py-3">{new Date(l.created_at).toLocaleString()}</td>
                <td className="py-3">{l.user_email}</td>
                <td className="py-3 font-semibold">{l.action.replace(/_/g, " ")}</td>
                <td className="py-3">{l.entity_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
