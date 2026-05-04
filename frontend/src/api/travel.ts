import { streamRequest, type SseMessage } from '@/utils/request'

export interface CreateTravelPlanParams {
  location: string
  days: number
  start_date: string | null
  end_date: string | null
  preferences: string | null
}

export type TravelPlanAgent =
  | 'manager_agent'
  | 'environment_agent'
  | 'resource_agent'
  | 'planner_agent'

export type TravelPlanAgentStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface TravelPlanStartEvent {
  thread_id: string
  trip_id: string
  start_at: number
}

export interface TravelPlanAgentStepEvent {
  agent: TravelPlanAgent
  status: TravelPlanAgentStatus
  message: string
}

export interface TravelPlanToolCallEvent {
  agent: TravelPlanAgent
  tool_name: string
  status: TravelPlanAgentStatus
  message: string
  latency_ms: number
}

export interface TravelPlanMessageEvent {
  content: string
}

export interface TravelPlanDoneEvent {
  trip_id: string
  thread_id: string
  version_no: number
  end_at: number
}

export interface TravelPlanErrorEvent {
  trip_id?: string
  thread_id?: string
  error_code: string
  error_message: string
  failed_agent?: TravelPlanAgent
  end_at?: number
}

export type TravelPlanEventData =
  | TravelPlanStartEvent
  | TravelPlanAgentStepEvent
  | TravelPlanToolCallEvent
  | TravelPlanMessageEvent
  | TravelPlanDoneEvent
  | TravelPlanErrorEvent

export type TravelPlanStreamMessage = SseMessage<TravelPlanEventData>

export interface CreateTravelPlanOptions {
  signal?: AbortSignal
  onEvent?: (message: TravelPlanStreamMessage) => void
}

export function createTravelPlan(params: CreateTravelPlanParams, options: CreateTravelPlanOptions = {}) {
  return streamRequest<TravelPlanEventData, CreateTravelPlanParams>({
    url: '/travel/plan',
    method: 'POST',
    data: params,
    signal: options.signal,
    onEvent: options.onEvent,
  })
}
