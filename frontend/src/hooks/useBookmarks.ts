import { useEffect, useState } from 'react'
import {
  addApplication,
  deleteApplication,
  importApplications,
  listApplications,
  setApplicationStatus,
} from '../api/client'
import type { BookmarkEntry, BookmarkStatus, Bookmarks, JobListing } from '../types'

const LEGACY_KEY = 'careerpilot_bookmarks'

// One-time move of localStorage bookmarks into SQLite; key is removed only after a successful import.
async function migrateLegacy(): Promise<void> {
  const raw = localStorage.getItem(LEGACY_KEY)
  if (!raw) return
  const legacy = JSON.parse(raw) as Bookmarks
  await importApplications(
    Object.entries(legacy).map(([url, b]) => ({ ...b, url, status: b.status ?? '想投' })),
  )
  localStorage.removeItem(LEGACY_KEY)
}

async function fetchBookmarks(): Promise<Bookmarks> {
  await migrateLegacy().catch(err => console.error('bookmark import failed', err))
  const rows = await listApplications()
  return Object.fromEntries(
    rows.map(r => [r.url, { job: r.job, date: r.date, company: r.company, city: r.city, salary: r.salary, status: r.status }]),
  )
}

export function useBookmarks() {
  const [bookmarks, setBookmarks] = useState<Bookmarks>({})

  function reload() {
    fetchBookmarks().then(setBookmarks).catch(err => console.error('load bookmarks failed', err))
  }

  useEffect(reload, [])

  // Optimistic update; on API failure resync from the server.
  function apply(next: Bookmarks, call: Promise<void>) {
    setBookmarks(next)
    call.catch(err => {
      console.error(err)
      reload()
    })
  }

  function add(job: JobListing) {
    const entry: BookmarkEntry = {
      job: job.job,
      date: job.date,
      company: job.company,
      city: job.city,
      salary: job.salary,
      status: '想投',
    }
    apply({ ...bookmarks, [job.link]: entry }, addApplication({ ...entry, url: job.link }))
  }

  function remove(link: string) {
    const next = { ...bookmarks }
    delete next[link]
    apply(next, deleteApplication(link))
  }

  function setStatus(link: string, status: BookmarkStatus) {
    if (!bookmarks[link]) return
    apply({ ...bookmarks, [link]: { ...bookmarks[link], status } }, setApplicationStatus(link, status))
  }

  function toggle(job: JobListing) {
    if (bookmarks[job.link]) remove(job.link)
    else add(job)
  }

  function isBookmarked(link: string): boolean {
    return !!bookmarks[link]
  }

  return { bookmarks, toggle, remove, setStatus, isBookmarked }
}
