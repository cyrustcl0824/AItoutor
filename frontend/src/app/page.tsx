"use client";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, Course, Student } from "@/lib/api";
import { useUiStore } from "@/lib/store";

export default function Home() {
  const students = useQuery({ queryKey:["students"], queryFn:()=>api<Student[]>("/students"), retry:false });
  const studentId = useUiStore(s=>s.studentId); const setStudentId=useUiStore(s=>s.setStudentId);
  const active = students.data?.find(s=>s.id===studentId) || students.data?.[0];
  const courses = useQuery({ queryKey:["courses",active?.grade], queryFn:()=>api<Course[]>(`/curriculum/courses?grade=${active!.grade}`), enabled:!!active });
  if(students.error) return <section className="hero"><h1>欢迎回来</h1><p>登录家长账户后，为孩子选择 PEP 英语教材。</p><Link className="button" href="/login">登录 / 注册</Link></section>;
  return <><section className="hero"><h1>Hi, {active?.display_name || "同学"}!</h1><p>今天从一小步开始，让英语越来越自然。</p>{students.data?.length ? <select value={active?.id} onChange={e=>setStudentId(e.target.value)}>{students.data.map(s=><option key={s.id} value={s.id}>{s.display_name} · {s.grade}年级</option>)}</select>:null}</section>
  <div className="grid">{courses.data?.map(c=><Link className="card" key={c.id} href={`/book/${c.id}?student=${active?.id}`}><h2>{c.name}</h2><p className="muted">{c.grade}年级 · {c.semester}</p><span className="button secondary">进入学习路径</span></Link>)}</div></>;
}
