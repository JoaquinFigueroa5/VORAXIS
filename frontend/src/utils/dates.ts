export function toISODate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

export function daysAgoISO(days: number): string {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() - days);
  return toISODate(date);
}

export function todayISO(): string {
  return toISODate(new Date());
}
