import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // Every backend call goes through ONE module: src/lib/api-client.ts. Nothing else may call fetch or XHR directly.
    // (The Supabase SDK makes its own auth requests; that is the one other network path, and it is not our backend.)
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Call the backend through src/lib/api-client.ts, never with fetch directly." },
        { name: "XMLHttpRequest", message: "Call the backend through src/lib/api-client.ts." },
      ],
      "no-restricted-properties": [
        "error",
        { object: "window", property: "fetch", message: "Call the backend through src/lib/api-client.ts." },
        { object: "globalThis", property: "fetch", message: "Call the backend through src/lib/api-client.ts." },
      ],
    },
  },
  {
    // src/lib/checks/demo.ts reads a static sample photo from this site's own /demo folder (not the backend).
    files: ["src/lib/api-client.ts", "src/lib/checks/demo.ts", "**/*.test.{ts,tsx}", "scripts/**"],
    rules: { "no-restricted-globals": "off", "no-restricted-properties": "off" },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "src/lib/api-schema.d.ts"]),
]);

export default eslintConfig;
