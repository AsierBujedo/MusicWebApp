import type { MusicApi } from "@/lib/api-types"
import { mockApi } from "@/lib/mock/mock-api"
import { realApi } from "@/lib/real-api"

// Toggle with NEXT_PUBLIC_MOCK_API. Defaults to mock so the app runs with no backend.
export const MOCK_MODE = process.env.NEXT_PUBLIC_MOCK_API !== "false"

export const api: MusicApi = MOCK_MODE ? mockApi : realApi

export { ApiError } from "@/lib/api-types"
export type { CreateRequestInput, CreateUserInput } from "@/lib/api-types"
