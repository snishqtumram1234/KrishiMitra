/**
 * Demo samples for the crop-check form: one click fills the whole form with a sample photo and example answers, then
 * submits it through the normal flow (same API calls and quality checks as a real check, nothing is faked).
 *
 * The photos are shrunk copies from the public Maharashtra soybean dataset (public/demo/). The example text names what a
 * farmer would see, never the answer, and contains no treatment or product words. Its wording lives in the i18n files
 * (check.demo.<id>.*), so it follows the chosen language.
 */
export type DemoId = "rust" | "insect" | "leafSpot" | "healthy";

export type DemoSample = {
  id: DemoId;
  photo: string;
  stage: string;
  /** how many days ago the farmer says it started */
  daysAgo: number;
};

export const DEMO_SAMPLES: readonly DemoSample[] = [
  { id: "rust", photo: "/demo/rust.jpg", stage: "R3", daysAgo: 6 },
  { id: "insect", photo: "/demo/insect.jpg", stage: "R2", daysAgo: 4 },
  { id: "leafSpot", photo: "/demo/leaf-spot.jpg", stage: "R1", daysAgo: 5 },
  { id: "healthy", photo: "/demo/healthy.jpg", stage: "V3", daysAgo: 2 },
];

/** `today` is YYYY-MM-DD (India); returns the date `days` earlier, in the same format. */
export function daysBefore(today: string, days: number): string {
  const d = new Date(`${today}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

/** Reads a sample photo from this site's /demo folder as a File, so it goes through the same upload path as a real photo. */
export async function loadDemoPhoto(sample: DemoSample): Promise<File> {
  const response = await fetch(sample.photo);
  if (!response.ok) throw new Error(`demo photo ${sample.photo}: HTTP ${response.status}`);
  return new File([await response.blob()], `${sample.id}.jpg`, { type: "image/jpeg" });
}
