import type { Metadata, Viewport } from "next";
import "./styles.css";
import "./features.css";
import { Providers } from "@/components/Providers";
import { Shell } from "@/components/Shell";
import { PwaRegistration } from "@/components/PwaRegistration";

export const metadata: Metadata = { title: "星光英语 AI 家教", description: "PEP 小学英语同步学习", manifest: "/manifest.webmanifest" };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#6757d9" };
export default function Layout({ children }: { children: React.ReactNode }) { return <html lang="zh-CN"><body><Providers><PwaRegistration/><Shell>{children}</Shell></Providers></body></html>; }
