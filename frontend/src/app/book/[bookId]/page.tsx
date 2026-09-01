"use client";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, Lesson, Unit } from "@/lib/api";

export default function Book(){const {bookId}=useParams<{bookId:string}>();const search=useSearchParams();const student=search.get("student")||"";const units=useQuery({queryKey:["units",bookId],queryFn:()=>api<Unit[]>(`/curriculum/courses/${bookId}/units?student_id=${student}`)});return <><h1>英语学习路径</h1><p className="muted">按单元完成课程，学习状态实时保存到家庭账户。</p><div className="stack">{units.data?.map(u=><UnitBlock key={u.id} unit={u} student={student}/>)}</div></>}
function UnitBlock({unit,student}:{unit:Unit;student:string}){const lessons=useQuery({queryKey:["lessons",unit.id,student],queryFn:()=>api<Lesson[]>(`/curriculum/units/${unit.id}/lessons?student_id=${student}`)});return <section className="card"><h2>{unit.title}</h2><div className="path">{lessons.data?.map(l=><Link className="lesson" key={l.id} href={`/lesson/${l.id}?student=${student}`}><span className="node">{l.position}</span><span><strong>{l.title}</strong><br/><span className="stars">{"★".repeat(l.progress?.stars||0)}{"☆".repeat(3-(l.progress?.stars||0))}</span></span></Link>)}</div></section>}
