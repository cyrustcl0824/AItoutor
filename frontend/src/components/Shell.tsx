"use client";
import Link from "next/link";
import { BookOpen, Bot, House, RotateCcw, Settings, UserRound } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api, User } from "@/lib/api";

export function Shell({ children }: { children: React.ReactNode }) {
  const me = useQuery({queryKey:["me"],queryFn:()=>api<User>("/auth/me"),retry:false});
  return <><header><Link href="/" className="brand">星光英语</Link><span>PEP · AI 家教</span></header><main>{children}</main><nav className="bottom-nav">
    <Link href="/"><House/>首页</Link><Link href="/stories"><BookOpen/>故事</Link><Link href="/review"><RotateCcw/>复习</Link><Link href="/tutor"><Bot/>AI 老师</Link><Link href="/parent"><UserRound/>家长</Link>{me.data?.role==="admin"&&<Link href="/admin/settings"><Settings/>配置</Link>}
  </nav></>;
}
