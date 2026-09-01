export class GoldProvider {
  constructor(name) {
    this.name = name;
  }

  async getSpotPrice() {
    throw new Error("provider_not_implemented");
  }

  getTimestamp(raw) {
    return raw?.sourceUpdatedAt ?? raw?.updatedAt ?? "";
  }

  getSource() {
    return this.name;
  }

  getStatus() {
    return "live";
  }
}

export class GoldApiProvider extends GoldProvider {
  constructor(url) {
    super("gold-api.com");
    this.url = url;
  }

  async getSpotPrice({ signal } = {}) {
    const response = await fetch(this.url, {
      headers: { Accept: "application/json" },
      signal,
      cf: { cacheTtl: 0 },
    });
    if (!response.ok) throw new Error(`source_${response.status}`);
    return response.json();
  }
}

export function createGoldProvider(env = {}) {
  const url = String(env.GOLD_PROVIDER_URL || "https://api.gold-api.com/price/XAU/USD");
  return new GoldApiProvider(url);
}
