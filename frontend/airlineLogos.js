export function getAirlineLogoPath(airlineCode) {
  if (!airlineCode) return null;
  const key = String(airlineCode).trim().toUpperCase();
  if (!key) return null;
  return `./assets/logos/flightaware_logos/${key}.png`;
}
