type LatitudeLongitude = [number, number];

interface Trixel {
  name: string;
  vertices: [LatitudeLongitude, LatitudeLongitude, LatitudeLongitude];
}

type LayeredTrixels = Trixels[];
type Trixels = Trixel[];

type Datapoint = [number, number, number, number, number, number]; // lat, lon, alt, u, v, w

interface DetailedByTrixelName {
  [trixelName: string]: Datapoint[];
}
