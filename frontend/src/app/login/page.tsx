import LoginClient from "./LoginClient";

/** Skip static prerender — avoids Next.js CSR bailout on auth pages. */
export const dynamic = "force-dynamic";

export default function LoginPage() {
  return <LoginClient />;
}
