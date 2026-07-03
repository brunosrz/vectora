//  @ts-check

import { tanstackConfig } from "@tanstack/eslint-config";

export default [
  ...tanstackConfig,
  {
    rules: {
      "import/no-cycle": "off",
      "import/order": "off",
      "sort-imports": "off",
      "@typescript-eslint/array-type": "off",
      "@typescript-eslint/require-await": "off",
      "pnpm/json-enforce-catalog": "off",
    },
  },
  {
    ignores: [
      ".output/**",
      ".nitro/**",
      ".tanstack/**",
      "dist/**",
      "eslint.config.js",
      "agent/**",
      "docs/**",
      "supabase/functions/**",
      "emails/**",
      "src/paraglide/**",
      // Gerado por `supabase gen types typescript` — a convenção de nomes dos
      // type params (TableName, EnumName, ...) vem do codegen do Supabase,
      // não é editável e se repete a cada regeneração.
      "src/lib/supabase/types.ts",
    ],
  },
];
