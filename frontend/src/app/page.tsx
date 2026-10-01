import { redirect } from "next/navigation";
import { HOME, LOGIN_PATH } from "@/lib/auth/routing";
import { getSession } from "@/lib/auth/server";

/** "/" has no content of its own (the proxy normally redirects first): send people to their home or to sign-in. */
export default async function RootPage() {
  const session = await getSession();
  redirect(session ? HOME[session.role] : LOGIN_PATH);
}
