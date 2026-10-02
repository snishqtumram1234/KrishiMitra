import type { Metadata } from "next";
import { Landing } from "@/components/landing/Landing";

export const metadata: Metadata = {
  title: "KrishiMitra",
  description: "A careful second opinion for your field. Preliminary answers, honest about what they do not know.",
};

/** The public landing page. Its copy is English (the design has no Marathi version), whatever the app language. */
export default function RootPage() {
  return (
    <div lang="en">
      <Landing />
    </div>
  );
}
