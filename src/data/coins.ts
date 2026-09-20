import catalog from "./coins.generated.json";

export type Coin = {
  id: string;
  country: string;
  countryCode: string;
  flag: string;
  denomination: string;
  valueCents: number;
  motif: string;
  series: string;
  kind: "regular" | "commemorative";
  issueYear?: number;
  info?: string;
  issuingVolume?: string;
  issuingDate?: string;
  imageUrl: string;
  sourceUrl: string;
  imageSourceUrl: string;
};

type CatalogRecord = Omit<Coin, "imageUrl"> & { imagePath: string };

export const coins: Coin[] = (catalog as CatalogRecord[]).map(({ imagePath, ...coin }) => ({
  ...coin,
  imageUrl: `${import.meta.env.BASE_URL}${imagePath}`,
}));
