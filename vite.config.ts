import { defineConfig, loadEnv } from "vite";
import cesium from "vite-plugin-cesium";

export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return defineConfig({
    clearScreen: false,
    server: {
      port: parseInt(env.VITE_PORT),
    },
    plugins: [cesium()],
  });
};
