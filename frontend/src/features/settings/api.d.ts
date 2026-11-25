export interface AccountSettings {
  first_name: string;
  middle_name: string;
  last_name: string;
  suffix: string;
  email: string;
}
export function getSettings(): Promise<AccountSettings>;
export function updateSettings(settings: Partial<AccountSettings>): Promise<AccountSettings>;
