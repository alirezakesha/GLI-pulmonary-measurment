/** API prefix; follows Vite `base` (e.g. `/api` at root, `/gli/api` when base is `/gli/`). */
export const API_BASE = `${import.meta.env.BASE_URL}api`.replace(/\/+$/, '')
