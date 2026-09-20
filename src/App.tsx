import {
  ArrowLeft,
  Check,
  Download,
  Info,
  RotateCcw,
  Upload,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { coins, type Coin } from "./data/coins";
import {
  clearCollection,
  loadCollection,
  normalizeCollection,
  saveCollection,
} from "./lib/storage";

const denominationOrder = [200, 100, 50, 20, 10, 5, 2, 1];
const knownIds = new Set(coins.map((coin) => coin.id));

const readCountryFromUrl = () =>
  new URLSearchParams(window.location.search).get("country")?.toUpperCase() ?? null;

export default function App() {
  const [collected, setCollected] = useState(
    () => new Set(loadCollection(knownIds).collectedIds),
  );
  const [selectedCountryCode, setSelectedCountryCode] = useState<string | null>(
    readCountryFromUrl,
  );
  const [infoCoin, setInfoCoin] = useState<Coin | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const countries = useMemo(() => {
    const byCode = new Map<string, { code: string; name: string; flag: string; coins: Coin[] }>();
    for (const coin of coins) {
      const country = byCode.get(coin.countryCode) ?? {
        code: coin.countryCode,
        name: coin.country,
        flag: coin.flag,
        coins: [],
      };
      country.coins.push(coin);
      byCode.set(coin.countryCode, country);
    }
    return [...byCode.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, []);

  const selectedCountry =
    countries.find((country) => country.code === selectedCountryCode) ?? null;

  useEffect(() => {
    const handlePopState = () => setSelectedCountryCode(readCountryFromUrl());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (!infoCoin) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setInfoCoin(null);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [infoCoin]);

  const chooseCountry = (code: string | null) => {
    const url = new URL(window.location.href);
    if (code) url.searchParams.set("country", code.toLowerCase());
    else url.searchParams.delete("country");
    window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
    setSelectedCountryCode(code);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const toggle = (id: string) => {
    const next = new Set(collected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    try {
      saveCollection(next);
      setNotice(null);
    } catch {
      setNotice("This browser blocked local saving. Export a backup before leaving.");
    }
    setCollected(next);
  };

  const exportCollection = () => {
    const snapshot = {
      version: 1 as const,
      updatedAt: new Date().toISOString(),
      collectedIds: [...collected].sort(),
    };
    const link = document.createElement("a");
    link.href = URL.createObjectURL(
      new Blob([JSON.stringify({ app: "Eurocase", ...snapshot }, null, 2)], {
        type: "application/json",
      }),
    );
    link.download = `eurocase-collection-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 0);
    setNotice("Backup downloaded.");
  };

  const importCollection = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const parsed = normalizeCollection(JSON.parse(await file.text()), knownIds);
      if (
        collected.size &&
        !window.confirm(
          `Replace your current collection with ${parsed.collectedIds.length} collected coins from this backup?`,
        )
      )
        return;
      const next = new Set(parsed.collectedIds);
      saveCollection(next);
      setCollected(next);
      setNotice(`Backup restored · ${next.size} collected coins.`);
    } catch {
      setNotice("That file is not a valid Eurocase backup.");
    }
  };

  const resetCollection = () => {
    if (!collected.size) {
      setNotice("Your collection is already empty.");
      return;
    }
    if (
      !window.confirm(
        `Remove all ${collected.size} collected coins from this device? Export a backup first if you may want them later.`,
      )
    )
      return;
    try {
      clearCollection();
    } catch {
      setNotice("This browser blocked local storage changes.");
      return;
    }
    setCollected(new Set());
    setNotice("Collection reset.");
  };

  const progress = coins.length ? Math.round((collected.size / coins.length) * 100) : 0;

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => chooseCountry(null)} aria-label="Show all countries">
          <span className="brand-mark" aria-hidden="true">€</span>
          <span>Eurocase</span>
        </button>
        <div className="topbar-progress" aria-label={`${collected.size} of ${coins.length} collected`}>
          <span>{collected.size} / {coins.length}</span>
          <span className="topbar-track"><span style={{ width: `${progress}%` }} /></span>
          <span className="local-pill"><span className="local-dot" /> Saved locally</span>
        </div>
      </header>

      <main>
        {selectedCountry ? (
          <CountryCollection
            country={selectedCountry}
            collected={collected}
            onBack={() => chooseCountry(null)}
            onToggle={toggle}
            onInfo={setInfoCoin}
          />
        ) : (
          <CountryOverview
            countries={countries}
            collected={collected}
            onChoose={(code) => chooseCountry(code)}
          />
        )}

        <section className="data-bar" aria-label="Collection backup">
          <div>
            <strong>Local collection</strong>
            <span>{notice ?? "Changes save automatically in this browser."}</span>
          </div>
          <div className="data-actions">
            <button onClick={exportCollection}><Download size={15} /> Export</button>
            <button onClick={() => fileInput.current?.click()}><Upload size={15} /> Import</button>
            <button className="danger-action" onClick={resetCollection}><RotateCcw size={15} /> Reset</button>
            <input ref={fileInput} type="file" accept="application/json,.json" onChange={importCollection} hidden />
          </div>
        </section>
      </main>

      <footer>
        <p>Official coin photographs and reference information: <a href="https://www.ecb.europa.eu/euro/coins/html/index.en.html" target="_blank" rel="noreferrer">European Central Bank</a>.</p>
        <p>Your progress never leaves this device.</p>
      </footer>

      {infoCoin && <CoinInfo coin={infoCoin} onClose={() => setInfoCoin(null)} />}
    </div>
  );
}

type CountrySummary = {
  code: string;
  name: string;
  flag: string;
  coins: Coin[];
};

function CountryOverview({
  countries,
  collected,
  onChoose,
}: {
  countries: CountrySummary[];
  collected: ReadonlySet<string>;
  onChoose: (code: string) => void;
}) {
  return (
    <section className="country-overview" aria-labelledby="country-overview-title">
      <div className="page-intro">
        <p className="eyebrow">Your euro collection</p>
        <h1 id="country-overview-title">Choose a country.</h1>
        <p>Open a country, then click the coin photographs you already own.</p>
      </div>
      <div className="country-grid">
        {countries.map((country) => {
          const found = country.coins.filter((coin) => collected.has(coin.id)).length;
          const percentage = Math.round((found / country.coins.length) * 100);
          return (
            <button className="country-card" key={country.code} onClick={() => onChoose(country.code)}>
              <span className="country-flag" aria-hidden="true">{country.flag}</span>
              <span className="country-card-copy">
                <strong>{country.name}</strong>
                <span>{found} of {country.coins.length} collected</span>
                <span className="country-progress"><span style={{ width: `${percentage}%` }} /></span>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function CountryCollection({
  country,
  collected,
  onBack,
  onToggle,
  onInfo,
}: {
  country: CountrySummary;
  collected: ReadonlySet<string>;
  onBack: () => void;
  onToggle: (id: string) => void;
  onInfo: (coin: Coin) => void;
}) {
  const found = country.coins.filter((coin) => collected.has(coin.id)).length;

  return (
    <section className="country-collection" aria-labelledby={`country-${country.code}`}>
      <button className="back-button" onClick={onBack}><ArrowLeft size={17} /> All countries</button>
      <div className="country-hero">
        <span className="hero-flag" aria-hidden="true">{country.flag}</span>
        <div>
          <p className="eyebrow">Collection</p>
          <h1 id={`country-${country.code}`}>{country.name}</h1>
          <p>Click a coin image to mark it collected. Click it again to undo.</p>
        </div>
        <div className="country-total"><strong>{found}</strong><span>of {country.coins.length}</span></div>
      </div>

      <div className="denomination-list">
        {denominationOrder.map((value) => {
          const variants = country.coins.filter((coin) => coin.valueCents === value);
          if (!variants.length) return null;
          const regular = variants.filter((coin) => coin.kind !== "commemorative");
          const commemorative = variants.filter((coin) => coin.kind === "commemorative");
          return (
            <section className="denomination-row" key={value} aria-labelledby={`${country.code}-${value}`}>
              <h2 id={`${country.code}-${value}`}>{variants[0].denomination}</h2>
              <div className="variant-groups">
                {!!regular.length && (
                  <VariantGroup title="Regular designs" coins={regular} collected={collected} onToggle={onToggle} onInfo={onInfo} />
                )}
                {!!commemorative.length && (
                  <VariantGroup title="Commemorative issues" coins={commemorative} collected={collected} onToggle={onToggle} onInfo={onInfo} />
                )}
              </div>
            </section>
          );
        })}
      </div>
    </section>
  );
}

function VariantGroup({
  title,
  coins: groupCoins,
  collected,
  onToggle,
  onInfo,
}: {
  title: string;
  coins: Coin[];
  collected: ReadonlySet<string>;
  onToggle: (id: string) => void;
  onInfo: (coin: Coin) => void;
}) {
  return (
    <div className="variant-group">
      <h3>{title}<span>{groupCoins.length}</span></h3>
      <div className="variant-grid">
        {groupCoins.map((coin) => {
          const isCollected = collected.has(coin.id);
          return (
            <article className={`variant-card ${isCollected ? "is-collected" : ""}`} key={coin.id}>
              <div className="variant-subheader">
                <span>
                  {coin.kind === "commemorative"
                    ? `${coin.issueYear} · €2 commemorative`
                    : coin.series}
                </span>
                <button onClick={() => onInfo(coin)} aria-label={`Information about ${coin.motif}`}><Info size={15} /></button>
              </div>
              <button
                className="coin-image-button"
                onClick={() => onToggle(coin.id)}
                aria-pressed={isCollected}
                aria-label={`${isCollected ? "Remove" : "Add"} ${coin.country} ${coin.denomination}, ${coin.motif} ${isCollected ? "from" : "to"} my collection`}
              >
                {/* oxlint-disable-next-line next/no-img-element -- bundled official ECB catalogue photographs */}
                <img src={coin.imageUrl} alt="" loading="lazy" />
                <span className="coin-check" aria-hidden="true">{isCollected && <Check size={18} strokeWidth={3} />}</span>
              </button>
              <div className="variant-copy">
                <strong>{coin.motif}</strong>
                <span>{isCollected ? "Collected" : "Not collected"}</span>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function CoinInfo({ coin, onClose }: { coin: Coin; onClose: () => void }) {
  return (
    <dialog open className="dialog-backdrop" aria-modal="true" aria-labelledby="coin-dialog-title">
      <section className="coin-dialog">
        <button className="dialog-close" onClick={onClose} aria-label="Close information"><X size={18} /></button>
        <p className="eyebrow">{coin.country} · {coin.denomination}</p>
        <h2 id="coin-dialog-title">{coin.motif}</h2>
        <p className="dialog-series">{coin.series}{coin.issueYear ? ` · ${coin.issueYear}` : ""}</p>
        {/* oxlint-disable-next-line next/no-img-element -- bundled official ECB catalogue photograph */}
        <img src={coin.imageUrl} alt={`${coin.country} ${coin.denomination}: ${coin.motif}`} />
        <p>{coin.info ?? `Official ${coin.series.toLowerCase()} design for ${coin.country}.`}</p>
        {(coin.issuingDate || coin.issuingVolume) && (
          <dl className="coin-facts">
            {coin.issuingDate && <><dt>Issued</dt><dd>{coin.issuingDate}</dd></>}
            {coin.issuingVolume && <><dt>Volume</dt><dd>{coin.issuingVolume}</dd></>}
          </dl>
        )}
        <a href={coin.sourceUrl} target="_blank" rel="noreferrer">View official source</a>
      </section>
    </dialog>
  );
}
