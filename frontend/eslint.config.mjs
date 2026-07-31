import { dirname } from "path";
import { fileURLToPath } from "url";

import { FlatCompat } from "@eslint/eslintrc";

const currentFilename =
  fileURLToPath(import.meta.url);

const currentDirectory =
  dirname(currentFilename);

const compat = new FlatCompat({
  baseDirectory: currentDirectory,
});

const eslintConfig = [
  ...compat.extends(
    "next/core-web-vitals"
  ),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "coverage/**",
      "next-env.d.ts",
    ],
  },
];

export default eslintConfig;
