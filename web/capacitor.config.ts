import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.jvindustries.oms",
  appName: "JV-OMS",
  webDir: "dist",
  server: {
    androidScheme: "https",
  },
  plugins: {
    Camera: {
      permissions: ["camera"],
    },
    Geolocation: {
      permissions: ["location"],
    },
  },
};

export default config;
