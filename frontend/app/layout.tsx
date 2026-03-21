import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar, Shell } from "@/components/ui";

export const metadata: Metadata = {
  title: "FocusLedger",
  description: "聚焦公众号文章的采集、整理、浏览与日报输出。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <Shell>
            <Sidebar />
            {children}
          </Shell>
        </Providers>
      </body>
    </html>
  );
}
