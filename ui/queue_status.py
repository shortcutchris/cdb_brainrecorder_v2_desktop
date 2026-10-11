"""Honest queue status: elapsed phase time, FIFO order, no invented percentages."""
import time


def describe_queue(state, timestamp=None):
    timestamp=time.time() if timestamp is None else timestamp
    sessions={r.get('local_job_id'):r for r in state.get('sessions',[]) if r.get('local_job_id')}
    jobs=[j for j in state.get('jobs',[]) if j['id'] in sessions]
    active=next((j for j in jobs if j['state'] in ('transcribing','summarizing')),None)
    waiting=sorted((j for j in jobs if j['state']=='queued'),key=lambda j:(j.get('queued_at') or j['created'],j['created']))
    preparing=[j for j in jobs if j['state']=='importing']
    failed=[j for j in jobs if j['state']=='failed']
    def title(j):return sessions[j['id']]['title'][:65]
    parts=[]
    if active:
        seconds=max(0,int(timestamp-active['updated']))
        phase='Transkription' if active['state']=='transcribing' else 'Zusammenfassung'
        parts.append(f"{phase} läuft · {seconds//60:02d}:{seconds%60:02d} · {title(active)}")
    elif state.get('recording',{}).get('id'):parts.append('Aufnahme läuft · wird beim Stop hinten eingereiht')
    else:parts.append('Lokal bereit')
    parts.append(f"{len(waiting)} warten" + (' · '+ ' → '.join(f"{i+1}. {title(j)}" for i,j in enumerate(waiting[:4])) if waiting else ''))
    if len(waiting)>4:parts.append(f"weitere {len(waiting)-4}")
    if preparing:parts.append(f"{len(preparing)} werden für die Warteschlange vorbereitet")
    if failed:parts.append(f"{len(failed)} Fehler · KI-Ansicht öffnen für Details/Wiederholen")
    if state.get('recording',{}).get('id') and active:parts.append('Aufnahme läuft parallel')
    elif active or waiting:parts.append('Weitere Aufnahme möglich')
    return bool(active or preparing), ' | '.join(parts), bool(failed)
