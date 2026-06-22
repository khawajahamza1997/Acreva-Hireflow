"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Member = { id: string; email: string; full_name: string; role: string };

export default function TeamPage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invite, setInvite] = useState({ email: "", role: "recruiter" });
  const [message, setMessage] = useState("");

  async function load() {
    setMembers(await api<Member[]>("/api/v1/team"));
  }

  useEffect(() => {
    load();
  }, []);

  async function sendInvite(e: React.FormEvent) {
    e.preventDefault();
    const res = await api<{ message: string }>("/api/v1/team/invite", {
      method: "POST",
      body: JSON.stringify(invite),
    });
    setMessage(res.message);
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Team</h1>
      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <form onSubmit={sendInvite} className="card space-y-4">
          <h2 className="font-bold">Invite member</h2>
          <input className="input" type="email" placeholder="Email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} required />
          <select className="input" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
            <option value="recruiter">Recruiter</option>
            <option value="viewer">Viewer (read-only)</option>
          </select>
          <button className="btn-primary">Send invite</button>
          {message && <p className="text-sm text-green-700">{message}</p>}
        </form>
        <div className="card">
          <h2 className="font-bold mb-4">Members</h2>
          {members.map((m) => (
            <div key={m.id} className="flex justify-between border-b border-slate-100 py-3 text-sm">
              <div>
                <div className="font-semibold">{m.full_name || m.email}</div>
                <div className="text-slate-500">{m.email}</div>
              </div>
              <span className="text-xs font-bold uppercase text-electric">{m.role}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
