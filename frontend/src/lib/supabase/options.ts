import type { SupabaseClientOptions } from "@supabase/supabase-js";

type WebSocketLikeConstructor = NonNullable<NonNullable<SupabaseClientOptions<"public">["realtime"]>["transport"]>;

/**
 * Options shared by every Supabase client in this app.
 *
 * The app uses Supabase Auth only. supabase-js also builds a Realtime client, and on Node 20 (and below) that throws
 * "native WebSocket not found" the moment a client is created, which would break the server and the proxy. A transport
 * that is never constructed keeps Realtime switched off everywhere (the browser would never use it either).
 */
class RealtimeNotUsed {
  constructor() {
    throw new Error("KrishiMitra does not use Supabase Realtime.");
  }
}

export const SUPABASE_CLIENT_OPTIONS = {
  realtime: { transport: RealtimeNotUsed as unknown as WebSocketLikeConstructor },
} as const;
