/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: [
    "@langchain/langgraph-sdk",
    "react-syntax-highlighter",
    "nuqs",
    "uuid",
    "framer-motion",
  ],
};

export default nextConfig;
