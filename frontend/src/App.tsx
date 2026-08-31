import { FormEvent, useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom'
import { api, type Student, type TutorDecision } from './api'
import { useAppStore } from './store'

type User = { id: string; email: string }

function Shell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  return <><header><Link to="/" className="brand">🌟 Emma Tutor</Link><nav><Link to="/talk">英语对话</Link><Link to="/books">课本听读</Link><Link to="/review">每日复习</Link><Link to="/parent">家长报告</Link><button className="link" onClick={async () => { await api('/auth/logout', { method: 'POST' }); navigate('/login') }}>退出</button></nav></header><main>{children}</main></>
}

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [register, setRegister] = useState(false), [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    const form = new FormData(event.currentTarget)
    try {
      const body = register ? { email: form.get('email'), password: form.get('password'), family_name: form.get('family') } : { email: form.get('email'), password: form.get('password') }
      onLogin(await api<User>(`/auth/${register ? 'register' : 'login'}`, { method: 'POST', body: JSON.stringify(body) }))
    } catch (e) { setError(e instanceof Error ? e.message : '登录失败') }
  }
  return <main className="auth"><section className="card auth-card"><div className="mascot">👩🏻‍🏫</div><h1>{register ? '创建家庭账号' : '欢迎回来'}</h1><p>让 Emma 陪孩子每天开口说英语</p><form onSubmit={submit}>{register && <label>家庭名称<input name="family" required /></label>}<label>邮箱<input name="email" type="email" required /></label><label>密码<input name="password" type="password" minLength={10} required /></label>{error && <p className="error">{error}</p>}<button className="primary" type="submit">{register ? '开始使用' : '登录'}</button></form><button className="link" onClick={() => setRegister(!register)}>{register ? '已有账号？去登录' : '第一次使用？创建账号'}</button></section></main>
}

function Dashboard() {
  const [students, setStudents] = useState<Student[]>([]), [showAdd, setShowAdd] = useState(false)
  const { currentStudent, setStudent } = useAppStore()
  const load = () => api<Student[]>('/students').then(items => { setStudents(items); if (!currentStudent && items[0]) setStudent(items[0]) })
  useEffect(() => { load() }, [])
  async function add(event: FormEvent<HTMLFormElement>) { event.preventDefault(); const f = new FormData(event.currentTarget); await api('/students', { method: 'POST', body: JSON.stringify({ name: f.get('name'), display_name: f.get('name'), grade: Number(f.get('grade')), preferences: {} }) }); setShowAdd(false); load() }
  return <Shell><section className="hero"><div><span className="eyebrow">今日英语探险</span><h1>{currentStudent ? `${currentStudent.display_name}，准备好了吗？` : '先创建孩子档案'}</h1><p>每天十分钟，勇敢开口、及时复习。</p></div><div className="mascot large">👩🏻‍🏫</div></section><section><div className="section-title"><h2>选择学习档案</h2><button onClick={() => setShowAdd(!showAdd)}>＋ 添加孩子</button></div><div className="student-row">{students.map(s => <button key={s.id} className={`student-chip ${currentStudent?.id === s.id ? 'active' : ''}`} onClick={() => setStudent(s)}><span>🧒</span>{s.display_name}<small>{s.grade}年级</small></button>)}</div>{showAdd && <form className="inline-form card" onSubmit={add}><input name="name" placeholder="孩子昵称" required /><select name="grade" defaultValue="3">{[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}年级</option>)}</select><button className="primary">保存</button></form>}</section><section className="mode-grid"><Link className="mode talk" to="/talk"><b>🎙️ 和 Emma 对话</b><span>用英语聊喜欢的话题</span></Link><Link className="mode words" to="/review"><b>🧠 每日复习</b><span>复习易错词和句型</span></Link><Link className="mode books" to="/books"><b>📖 课本听读</b><span>看原页，逐句跟读</span></Link><Link className="mode report" to="/parent"><b>📊 学习进度</b><span>查看掌握度和周报</span></Link></section></Shell>
}

function Talk() {
  const student = useAppStore(s => s.currentStudent), [session, setSession] = useState(''), [text, setText] = useState(''), [messages, setMessages] = useState<{role:string;text:string}[]>([{ role: 'assistant', text: "Hi! I'm Emma. What do you like?" }]), [busy, setBusy] = useState(false)
  useEffect(() => { if (student) api<{id:string}>('/sessions', { method: 'POST', body: JSON.stringify({ student_id: student.id, mode: 'conversation' }) }).then(s => setSession(s.id)) }, [student?.id])
  async function send() { if (!text.trim() || !session || busy) return; const value = text; setText(''); setMessages(m => [...m, { role: 'user', text: value }]); setBusy(true); try { const answer = await api<TutorDecision>('/tutor/message', { method: 'POST', body: JSON.stringify({ session_id: session, text: value }) }); setMessages(m => [...m, { role: 'assistant', text: answer.reply }]); const speech = new FormData(); speech.append('text', answer.reply); const audio = await api<{url:string}>('/audio/speech', { method: 'POST', body: speech }); new Audio(audio.url).play().catch(() => {}) } finally { setBusy(false) } }
  async function record() { if (!navigator.mediaDevices) return; const stream = await navigator.mediaDevices.getUserMedia({ audio: true }); const recorder = new MediaRecorder(stream), chunks: Blob[] = []; recorder.ondataavailable = e => chunks.push(e.data); recorder.onstop = async () => { stream.getTracks().forEach(t => t.stop()); const form = new FormData(); form.append('file', new Blob(chunks, { type: recorder.mimeType }), 'speech.webm'); form.append('language', 'en'); const result = await api<{text:string}>('/audio/transcribe', { method: 'POST', body: form }); setText(result.text) }; recorder.start(); setTimeout(() => recorder.stop(), 5000) }
  if (!student) return <Shell><EmptyStudent /></Shell>
  return <Shell><section className="chat card"><div className="chat-title"><div className="mascot">👩🏻‍🏫</div><div><h1>和 Emma 说英语</h1><p>{busy ? 'Emma 正在想…' : '一次说一句短句就很好'}</p></div></div><div className="messages">{messages.map((m,i) => <div key={i} className={`bubble ${m.role}`}>{m.text}</div>)}</div><div className="composer"><button aria-label="录音五秒" className="mic" onClick={record}>🎙️</button><input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="输入或录下英语短句…"/><button className="primary" onClick={send} disabled={busy}>发送</button></div></section></Shell>
}

function Books() {
  const student = useAppStore(s => s.currentStudent), [books, setBooks] = useState<{id:string;title:string;grade:number;semester:string}[]>([])
  useEffect(() => { if (student) api<typeof books>(`/textbooks?grade=${student.grade}`).then(setBooks) }, [student?.id])
  return <Shell><h1>📖 课本听读</h1><p>选择课本，查看清晰原页。</p><div className="book-grid">{books.map(book => <Link to={`/books/${book.id}`} className="book card" key={book.id}><span>PEP</span><b>{book.title}</b><small>{book.grade}年级 · {book.semester}</small></Link>)}</div>{books.length === 0 && <div className="empty card">尚未导入教材。运行 curriculum/import_textbooks.py 后会显示在这里。</div>}</Shell>
}

function BookReader() {
  type Sentence = {id:string;position:number;text:string;page_id?:string;audio_url?:string;duration_ms?:number}
  const { editionId } = useParams(), student = useAppStore(s=>s.currentStudent)
  const [pages, setPages] = useState<{id:string;position:number;image_url:string}[]>([]), [contents,setContents]=useState<{id:string;title:string;lessons:{id:string;title:string}[]}[]>([]), [sentences,setSentences]=useState<Sentence[]>([]), [passageId,setPassageId]=useState(''), [index, setIndex] = useState(0), [zoom, setZoom] = useState(1), [active,setActive]=useState(-1), audioRef=useRef<HTMLAudioElement|null>(null)
  useEffect(() => { api<typeof pages>(`/textbooks/${editionId}/pages`).then(setPages); api<typeof contents>(`/textbooks/${editionId}/contents`).then(items=>{setContents(items); const lesson=items[0]?.lessons[0]; if(lesson) loadLesson(lesson.id)}) }, [editionId])
  async function loadLesson(lessonId:string){ const reading=await api<{passage?:{id:string};sentences:Sentence[]}>(`/textbooks/lessons/${lessonId}/reading`); setSentences(reading.sentences); setPassageId(reading.passage?.id||''); setActive(-1) }
  async function playSentence(position:number, continueAfter=false){ const sentence=sentences[position]; if(!sentence)return; setActive(position); if(sentence.page_id){const found=pages.findIndex(p=>p.id===sentence.page_id);if(found>=0)setIndex(found)}; let url=sentence.audio_url; if(!url){const generated=await api<{url:string}>(`/textbooks/sentences/${sentence.id}/speech`,{method:'POST'});url=generated.url;setSentences(items=>items.map((s,i)=>i===position?{...s,audio_url:url}:s))}; const audio=new Audio(url); audioRef.current=audio; audio.onended=()=>{if(continueAfter&&position+1<sentences.length)playSentence(position+1,true);else saveProgress(position,position+1===sentences.length)}; await audio.play() }
  function saveProgress(position:number,completed=false){if(student&&passageId)api(`/textbooks/passages/${passageId}/progress`,{method:'PUT',body:JSON.stringify({student_id:student.id,page_id:pages[index]?.id,sentence_position:position,completed})}).catch(()=>{})}
  const page = pages[index]
  return <Shell><section className="reader"><div className="reader-toolbar"><button onClick={() => setIndex(Math.max(0,index-1))}>← 上一页</button><b>{pages.length ? `${index+1} / ${pages.length}` : '加载中'}</b><button onClick={() => setIndex(Math.min(pages.length-1,index+1))}>下一页 →</button><button onClick={() => setZoom(z => z >= 1.8 ? 1 : z + .2)}>🔍 {Math.round(zoom*100)}%</button></div><div className="page-stage">{page && <img src={page.image_url} alt={`课本第 ${index+1} 页`} style={{ transform: `scale(${zoom})` }}/>}</div><aside className="sentence-panel"><h2>逐句听读</h2><select aria-label="选择课时" onChange={e=>loadLesson(e.target.value)}>{contents.flatMap(unit=>unit.lessons.map(lesson=><option key={lesson.id} value={lesson.id}>{unit.title} · {lesson.title}</option>))}</select>{sentences.length>0&&<button className="primary play-all" onClick={()=>playSentence(0,true)}>▶ 朗读全文</button>}<div className="sentence-list">{sentences.map((sentence,i)=><button key={sentence.id} className={active===i?'active':''} onClick={()=>playSentence(i)}><span>{i+1}</span>{sentence.text}</button>)}</div>{sentences.length===0&&<p>本课暂无逐句数据，仍可浏览原页。</p>}</aside></section></Shell>
}

function Review() { const student = useAppStore(s => s.currentStudent), [tasks,setTasks] = useState<{id:string;knowledge_point:string}[]>([]); useEffect(() => { if(student) api<typeof tasks>(`/learning/${student.id}/review/today`).then(setTasks) }, [student?.id]); return <Shell><h1>🧠 今日复习</h1><div className="stack">{tasks.map(t => <div className="card task" key={t.id}><b>{t.knowledge_point}</b><span>跟 Emma 练一练这个知识点</span><Link to="/talk">开始练习 →</Link></div>)}{tasks.length===0 && <div className="empty card">今天没有到期任务，去和 Emma 聊几句吧！</div>}</div></Shell> }

function Parent() { const student = useAppStore(s=>s.currentStudent), [report,setReport]=useState<any>(); useEffect(()=>{if(student) api(`/learning/${student.id}/weekly-report`).then(setReport)},[student?.id]); return <Shell><h1>📊 家长周报</h1>{report && <div className="stats"><div className="card"><b>{report.learning_seconds/60|0}</b><span>学习分钟</span></div><div className="card"><b>{report.attempts}</b><span>练习次数</span></div><div className="card"><b>{Math.round(report.accuracy*100)}%</b><span>正确率</span></div></div>}<section className="card"><h2>需要多练</h2>{report?.weak_points?.map((p:any)=><div className="progress" key={p.name}><span>{p.name}</span><meter min="0" max="1" value={p.score}/></div>) || <p>完成练习后这里会出现趋势。</p>}</section></Shell> }

function EmptyStudent() { return <div className="empty card">请先回到首页创建并选择孩子档案。<br/><Link to="/">返回首页</Link></div> }

export default function App() {
  const [user, setUser] = useState<User|null|undefined>(undefined)
  useEffect(() => { api<User>('/auth/me').then(setUser).catch(() => setUser(null)) }, [])
  if (user === undefined) return <div className="splash">🌟</div>
  if (!user) return <Routes><Route path="*" element={<Login onLogin={setUser}/>} /></Routes>
  return <Routes><Route path="/" element={<Dashboard/>}/><Route path="/talk" element={<Talk/>}/><Route path="/books" element={<Books/>}/><Route path="/books/:editionId" element={<BookReader/>}/><Route path="/review" element={<Review/>}/><Route path="/parent" element={<Parent/>}/><Route path="*" element={<Navigate to="/"/>}/></Routes>
}
