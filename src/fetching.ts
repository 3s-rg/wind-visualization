import { SERVER_URL } from "./constants";

/*
 * Fetches all simplified data points for the given dataset and layer
 */
export async function fetchSimplified(dataset: string, layer: string) {
  const response = await fetch(
    `${SERVER_URL}/simplified?dataset=${dataset}&layer=${layer}`
  );
  return response.json();
}

/*
 * Fetches all trixels for the given dataset and layer
 * This does not include any data points
 */
export async function fetchTrixelsInRadius(
  lat: number,
  lon: number,
  radius: number
): Promise<Trixel[]> {
  const response = await fetch(
    `${SERVER_URL}/trixels-in-radius?lat=${lat}&lon=${lon}&radius=${radius}`
  );
  return response.json();
}

/*
 * Fetches all data points for the given trixel names
 */
export async function fetchDetailedByTrixelNames(
  dataset: string,
  trixelNames: string[]
): Promise<DetailedByTrixelName> {
  if (trixelNames.length === 0) {
    return {};
  }

  const response = await fetch(`${SERVER_URL}/detailed-by-trixel-names`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      dataset: dataset,
      trixels: trixelNames,
    }),
  });
  return response.json();
}

/*
 * Fetches all datasets and their layers from the server
 */
export async function fetchDatasets(): Promise<Record<string, string[]>> {
  const response = await fetch(`${SERVER_URL}/datasets`);
  return response.json();
}
