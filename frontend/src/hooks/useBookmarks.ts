import type { BookmarkStatus, Bookmarks, JobListing } from '../types'
import { useLocalStorage } from './useLocalStorage'

export function useBookmarks() {
  const [bookmarks, setBookmarks] = useLocalStorage<Bookmarks>('careerpilot_bookmarks', {})

  function add(job: JobListing) {
    setBookmarks({
      ...bookmarks,
      [job.link]: {
        job: job.job,
        date: job.date,
        company: job.company,
        city: job.city,
        salary: job.salary,
        status: '想投',
      },
    })
  }

  function remove(link: string) {
    const next = { ...bookmarks }
    delete next[link]
    setBookmarks(next)
  }

  function setStatus(link: string, status: BookmarkStatus) {
    if (!bookmarks[link]) return
    setBookmarks({ ...bookmarks, [link]: { ...bookmarks[link], status } })
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
