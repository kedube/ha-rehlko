// The snapshot shape pushed by the `rehlko_energy/subscribe` websocket command. These mirror
// sidebar/snapshot.py; payloads are the API's own (see docs/API.md), so most fields are typed
// loosely as the service can add more at any time.

export interface Address {
  address1?: string;
  address2?: string;
  city?: string;
  postalCode?: string;
  country?: string;
}

export interface ExerciseInfo {
  frequency?: string;
  mode?: string;
  runningMode?: string;
  durationMinutes?: number;
  nextStartTimestamp?: string;
  lastStartTimestamp?: string;
  lastEndTimestamp?: string;
  supportsNextExerciseDateTimeParam?: boolean;
}

export interface PeripheralParam {
  definitionId: number | string;
  displayName?: string;
  value?: unknown;
  isReadOnly?: boolean;
}

export interface Peripheral {
  isConnected?: boolean;
  parameters?: PeripheralParam[];
}

export interface EventItem {
  id?: number | string;
  name?: string;
  level?: string;
  deviceEventId?: string;
  event?: string;
  fmi?: string;
  parameterId?: number | string;
  parameter?: string;
  timestamp?: string;
  type?: string;
  isCriticalFault?: boolean;
  canRemoteResetFault?: boolean;
}

export interface NotificationItem {
  id?: number | string;
  tag?: string;
  type?: string;
  message?: string;
  timestamp?: string;
  ctaText?: string;
  ctaLink?: string;
  isEStopEvent?: boolean;
}

export interface MaintenanceNote {
  id?: number | string;
  timestamp?: string;
  contents?: string;
  authorIsDealer?: boolean;
  dealerAuthor?: string;
}

export interface Derived {
  is_connected: boolean;
  is_running: boolean;
  is_exercising: boolean;
  on_generator_power: boolean;
  utility_present: boolean | null;
  ready_to_run: boolean;
  has_schedule: boolean;
  e_stop_engaged: boolean;
  nominal_voltage: number;
  supports_exercise_scheduling: boolean;
  supports_next_exercise_datetime: boolean;
  /** `device.deviceIpAddress` as an address: the service reports the socket, `[::ffff:a.b.c.d]:port`. */
  ip_address: string | null;
}

export interface Generator {
  entry_id: string;
  device_id: number;
  available: boolean;
  ha_device_id: string | null;
  name: string;
  serial_number?: string;
  home: Record<string, unknown> & { weatherTempF?: number; weatherCondition?: string };
  device: Record<string, unknown> & {
    status?: string;
    model?: string;
    modelDisplayName?: string;
    address?: Address;
    dealerOrgs?: Array<Record<string, unknown>>;
  };
  details: Record<string, unknown> & {
    exercise?: ExerciseInfo;
    loadShed?: Peripheral;
    pim?: Peripheral;
    ats?: Record<string, unknown>;
    generators?: Array<Record<string, unknown>>;
  };
  alerts: EventItem[];
  events: EventItem[];
  maintenance_notes: MaintenanceNote[];
  notifications: NotificationItem[];
  cell_plan: Record<string, unknown> | null;
  derived: Derived;
  entities: Record<string, string>;
  details_updated: string | null;
  feeds_updated: string | null;
}

export interface Account {
  entry_id: string;
  title: string;
  loaded: boolean;
  last_update_success?: boolean;
  notification_settings?: Record<string, boolean> | null;
  notification_entities?: Record<string, string>;
  me?: { firstName?: string; lastName?: string; email?: string };
}

export interface Snapshot {
  generators: Generator[];
  accounts: Account[];
}

/** The bulky fields the subscription sends only when they change (sidebar/snapshot.py). */
export type SeldomChanged = "events" | "notifications" | "maintenance_notes" | "entities";

/** A snapshot as it arrives: a seldom-changed field left out means "same as last time". */
export interface SnapshotMessage {
  generators: Array<Omit<Generator, SeldomChanged> & Partial<Pick<Generator, SeldomChanged>>>;
  accounts: Account[];
}

// Minimal view of the Home Assistant frontend object injected into the panel.
export interface HomeAssistant {
  states: Record<string, { state: string; attributes: Record<string, unknown> }>;
  connection: {
    subscribeMessage<T>(callback: (msg: T) => void, subscription: Record<string, unknown>): Promise<() => void>;
    sendMessagePromise<T>(message: Record<string, unknown>): Promise<T>;
  };
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>,
    target?: Record<string, unknown>,
  ): Promise<void>;
  callWS<T>(message: Record<string, unknown>): Promise<T>;
  /** Home Assistant's own translations, including this integration's entity states. */
  localize?(key: string, values?: Record<string, unknown>): string;
  /** Ask the frontend to fetch a translation category; `localize` is replaced when it lands. */
  loadBackendTranslation?(category: string, integration?: string): Promise<unknown>;
  themes?: { darkMode?: boolean };
  language?: string;
  locale?: {
    language?: string;
    /** `language`, `system`, `comma_decimal`, `decimal_comma`, `space_comma`, `quote_decimal`, `none`. */
    number_format?: string;
    /** `language`, `system`, `12`, `24`. */
    time_format?: string;
    /** `local` (the browser's zone) or `server`. */
    time_zone?: string;
  };
  config?: {
    time_zone?: string;
    unit_system?: { temperature?: string; pressure?: string };
  };
  /** `docked`, `always_hidden` or `auto`. */
  dockedSidebar?: string;
}
