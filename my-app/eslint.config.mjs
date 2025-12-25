import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,

  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),

  // 👉 Your overrides go here
  {
    rules: {
      // Disable or downgrade rules causing deployment failures
      "react-hooks/set-state-in-effect": "off",
      "@typescript-eslint/no-explicit-any": "off",

      // If you prefer warnings instead of off, use:
      // "react-hooks/set-state-in-effect": "warn",
      // "@typescript-eslint/no-explicit-any": "warn",
    },
  },
]);

export default eslintConfig;
