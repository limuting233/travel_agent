import { http } from '@/utils/request'

export interface TripOverview {
  title: string
  total_distance_km?: number
  tags?: string[]
}

export interface TripScheduleItem {
  seq: number
  time_window?: string
  poi_id?: string
  poi_name?: string
  category?: string
  action: string
  duration_hour?: number
  cost?: number
  reason?: string
  photo?: string
  location?: string
  transport_mode?: string
  distance_meter?: number
  commute_time_min?: number
  from_poi?: string
  to_poi?: string
}

export interface DailyItinerary {
  day: number
  date?: string
  weather_label?: string
  schedule: TripScheduleItem[]
}

export interface TripContent {
  trip_overview: TripOverview
  daily_itinerary: DailyItinerary[]
}

export interface TripDetail {
  id: string
  title: string
  location: string
  days: number
  start_date: string | null
  end_date: string | null
  preferences: string[]
  status: 'planning' | 'completed' | 'failed'
  latest_version: {
    version_no: number
    source: string
    content: TripContent
    created_at: number
  } | null
  created_at: number
  updated_at: number
}

export type TripStatus = 'planning' | 'completed' | 'failed'

export interface TripListItem {
  id: string
  title: string
  location: string
  days: number
  start_date: string | null
  end_date: string | null
  status: TripStatus
  latest_version_no: number
  created_at: number
  updated_at: number
}

export interface TripListParams {
  page?: number
  page_size?: number
  status?: TripStatus
}

export interface TripListResult {
  items: TripListItem[]
  page: number
  page_size: number
  total: number
}

export function getTripList(params: TripListParams = {}) {
  const searchParams = new URLSearchParams()

  if (params.page) searchParams.set('page', String(params.page))
  if (params.page_size) searchParams.set('page_size', String(params.page_size))
  if (params.status) searchParams.set('status', params.status)

  const query = searchParams.toString()

  return http.get<TripListResult>(query ? `/trips?${query}` : '/trips')
}

export function getTripDetail(tripId: string) {
  return http.get<TripDetail>(`/trips/${tripId}`)
}
