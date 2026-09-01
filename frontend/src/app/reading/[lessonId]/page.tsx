"use client";
import { useParams, useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Sentence = { id:string; position:number; text:string; audio_url?:string; page_id?:string };
type Reading = { lesson:{title:string}; page_ids:string[]; passage?:{id:string}; sentences:Sentence[] };

export default function Reader() {
  const { lessonId } = useParams<{lessonId:string}>();
  const student = useSearchParams().get("student") || "";
  const data = useQuery({ queryKey:["reading",lessonId], queryFn:()=>api<Reading>(`/textbooks/lessons/${lessonId}/reading`) });
  const [page,setPage] = useState(0); const [active,setActive] = useState(-1);
  const audio = useRef<HTMLAudioElement|null>(null);
  const speech = useMutation({ mutationFn:(id:string)=>api<{url:string}>(`/textbooks/sentences/${id}/speech`,{method:"POST"}) });
  async function play(index:number, continuous=true) { const sentence=data.data?.sentences[index]; if(!sentence)return; setActive(index); const url=sentence.audio_url||(await speech.mutateAsync(sentence.id)).url; const player=new Audio(url); audio.current=player; player.onended=()=>continuous&&play(index+1,true); await player.play(); }
  useEffect(()=>()=>audio.current?.pause(),[]);
  async function save(completed=false) { if(data.data?.passage) await api(`/textbooks/passages/${data.data.passage.id}/progress`,{method:"PUT",body:JSON.stringify({student_id:student,page_id:data.data.page_ids[page]||null,sentence_position:Math.max(active,0),completed})}); }
  return <><h1>{data.data?.lesson.title||"课本听读"}</h1><div className="reader"><section className="card">{data.data?.page_ids[page]?<img className="page-image" alt="课本原页" src={`/api/v1/textbooks/pages/${data.data.page_ids[page]}/image`}/>:<div className="feedback">本课原页资源尚未导入，仍可使用逐句听读。</div>}<div className="row"><button className="secondary" onClick={()=>setPage(Math.max(0,page-1))}>上一页</button><button className="secondary" onClick={()=>setPage(Math.min((data.data?.page_ids.length||1)-1,page+1))}>下一页</button><button onClick={()=>save(true)}>完成阅读</button></div></section><section className="card"><div className="row"><button onClick={()=>play(Math.max(active,0))}>播放全文</button><button className="secondary" onClick={()=>{audio.current?.pause();save()}}>暂停并保存</button></div>{data.data?.sentences.map((s,i)=><div key={s.id} className={`sentence ${active===i?"active":""}`} onClick={()=>play(i,false)}>{s.text}</div>)}</section></div></>;
}
